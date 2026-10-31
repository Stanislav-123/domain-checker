"""Domain checking scheduler and coordinator."""

import asyncio
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from typing import List, Dict

from .sources.base import DomainSource
from .sources.keitaro import KeitaroSource
from .sources.binom import BinomSource
from .sources.custom import CustomSource
from .checker import DomainChecker
from .storage import Storage
from .notifier import Notifier
from .config import Config


class DomainCheckScheduler:
    """Coordinates domain checking, state tracking, and notifications."""
    
    def __init__(self, config: Config):
        """Initialize scheduler.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.scheduler = AsyncIOScheduler()
        
        self.source = self._create_source()
        self.checker = DomainChecker(
            timeout=config.request_timeout_seconds,
            max_concurrent=config.max_concurrent_checks
        )
        self.storage = Storage(config.database_path)
        self._source_failed = False
        self._ssl_warned_on = {}  # domain -> date of last SSL-expiry warning
        self.notifier = Notifier(
            config.telegram_bot_token,
            config.telegram_chat_id,
            config.consecutive_failures_threshold,
            config.ssl_warning_days
        )
    
    def _create_source(self) -> DomainSource:
        """Create domain source based on configuration.
        
        Returns:
            Domain source instance
        """
        tracker_type = self.config.tracker_type
        url = self.config.tracker_url
        api_key = self.config.tracker_api_key
        timeout = self.config.request_timeout_seconds
        
        if tracker_type == 'keitaro':
            return KeitaroSource(url, api_key, timeout)
        elif tracker_type == 'binom':
            return BinomSource(url, api_key, timeout)
        elif tracker_type == 'custom':
            return CustomSource(
                url,
                api_key,
                self.config.custom_header_name,
                self.config.custom_domains_path,
                timeout
            )
        else:
            raise ValueError(f"Unknown tracker type: {tracker_type}")
    
    async def initialize(self):
        """Initialize storage and components."""
        await self.storage.initialize()
    
    async def check_all_domains(self):
        """Check all domains from the tracker."""
        print(f"\n[{datetime.now(timezone.utc).isoformat()}] Starting domain check cycle...")
        
        try:
            try:
                domains = await self.source.fetch_domains()
            except Exception as e:
                print(f"Failed to fetch domains from tracker: {e}")
                if not self._source_failed:
                    self._source_failed = True
                    await self.notifier.notify_source_error(self.config.tracker_type, str(e))
                return
            if self._source_failed:
                self._source_failed = False
                await self.notifier.notify_source_recovered(self.config.tracker_type)
            # de-duplicate, keep order, normalise case
            domains = list(dict.fromkeys(d.lower() for d in domains if d))
            print(f"Fetched {len(domains)} domains from tracker")
            
            if not domains:
                print("No domains to check")
                return
            
            results = await self.checker.check_multiple_domains(domains)
            
            for result in results:
                await self._process_check_result(result)
            
            up_count = sum(1 for r in results if r.get('status') == 'up')
            down_count = len(results) - up_count
            
            print(f"Check cycle completed: {up_count} up, {down_count} down")
            
        except Exception as e:
            print(f"Error during check cycle: {e}")
    
    async def _process_check_result(self, result: Dict):
        """Process a single domain check result.
        
        Args:
            result: Check result dictionary
        """
        domain = result['domain']
        status = result['status']
        
        prev_state = await self.storage.get_domain_state(domain)
        
        if status == 'down':
            consecutive_failures = (prev_state.get('consecutive_failures', 0) + 1) if prev_state else 1
            
            new_state = {
                'last_status': status,
                'consecutive_failures': consecutive_failures,
                'last_alert_sent': prev_state.get('last_alert_sent') if prev_state else None,
                'last_recovery_sent': prev_state.get('last_recovery_sent') if prev_state else None
            }
            
            if consecutive_failures == self.config.consecutive_failures_threshold:
                await self.notifier.notify_domain_down(domain, result, consecutive_failures)
                new_state['last_alert_sent'] = datetime.now(timezone.utc).isoformat()
            
            await self.storage.update_domain_state(domain, new_state)
        
        elif status == 'up':
            was_down = bool(prev_state) and prev_state.get('consecutive_failures', 0) > 0
            # Only announce recovery for an outage we actually alerted about.
            alerted = bool(prev_state) and prev_state.get('consecutive_failures', 0) >= self.config.consecutive_failures_threshold

            new_state = {
                'last_status': status,
                'consecutive_failures': 0,
                # outage is over: clear alert marker so next blip is judged fresh
                'last_alert_sent': None,
                'last_recovery_sent': prev_state.get('last_recovery_sent') if prev_state else None
            }

            if was_down and alerted:
                await self.notifier.notify_domain_recovered(domain, result)
                new_state['last_recovery_sent'] = datetime.now(timezone.utc).isoformat()
            
            ssl_days = result.get('ssl_days_remaining')
            if ssl_days is not None and result.get('ssl_valid'):
                today = datetime.now(timezone.utc).date()
                if ssl_days <= self.config.ssl_warning_days and self._ssl_warned_on.get(domain) != today:
                    await self.notifier.notify_ssl_expiring(domain, ssl_days)
                    self._ssl_warned_on[domain] = today
            
            await self.storage.update_domain_state(domain, new_state)
        
        result['consecutive_failures'] = (await self.storage.get_domain_state(domain)).get('consecutive_failures', 0)
        await self.storage.save_check_result(domain, result)
    
    def start(self):
        """Start the scheduler."""
        trigger = IntervalTrigger(minutes=self.config.check_interval_minutes)
        self.scheduler.add_job(
            self.check_all_domains,
            trigger=trigger,
            id='domain_check',
            replace_existing=True,
            max_instances=1,   # never overlap a slow cycle with the next one
            coalesce=True
        )
        
        self.scheduler.start()
        print(f"Scheduler started: checking every {self.config.check_interval_minutes} minutes")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("Scheduler stopped")
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.notifier.close()
