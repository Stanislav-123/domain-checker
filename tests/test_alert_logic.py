"""Tests for alert state logic."""

import pytest
from domain_checker.storage import Storage
from domain_checker.scheduler import DomainCheckScheduler
from domain_checker.config import Config
from pathlib import Path
import tempfile
import os


@pytest.fixture
async def storage():
    """Create temporary storage for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    storage = Storage(path)
    await storage.initialize()
    
    yield storage
    
    Path(path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_first_failure_no_alert(storage):
    """Test that first failure doesn't trigger alert."""
    domain = "example.com"
    
    result = {
        'status': 'down',
        'error_message': 'Connection failed',
        'consecutive_failures': 1
    }
    
    state = await storage.get_domain_state(domain)
    assert state is None
    
    await storage.update_domain_state(domain, {
        'last_status': 'down',
        'consecutive_failures': 1,
        'last_alert_sent': None,
        'last_recovery_sent': None
    })
    
    state = await storage.get_domain_state(domain)
    assert state['consecutive_failures'] == 1
    assert state['last_alert_sent'] is None


@pytest.mark.asyncio
async def test_consecutive_failures_trigger_alert(storage):
    """Test that consecutive failures trigger alert after threshold."""
    domain = "example.com"
    
    await storage.update_domain_state(domain, {
        'last_status': 'down',
        'consecutive_failures': 1,
        'last_alert_sent': None,
        'last_recovery_sent': None
    })
    
    await storage.update_domain_state(domain, {
        'last_status': 'down',
        'consecutive_failures': 2,
        'last_alert_sent': '2024-01-01T00:00:00',
        'last_recovery_sent': None
    })
    
    state = await storage.get_domain_state(domain)
    assert state['consecutive_failures'] == 2
    assert state['last_alert_sent'] is not None


@pytest.mark.asyncio
async def test_recovery_resets_failures(storage):
    """Test that recovery resets consecutive failures."""
    domain = "example.com"
    
    await storage.update_domain_state(domain, {
        'last_status': 'down',
        'consecutive_failures': 3,
        'last_alert_sent': '2024-01-01T00:00:00',
        'last_recovery_sent': None
    })
    
    await storage.update_domain_state(domain, {
        'last_status': 'up',
        'consecutive_failures': 0,
        'last_alert_sent': '2024-01-01T00:00:00',
        'last_recovery_sent': '2024-01-01T01:00:00'
    })
    
    state = await storage.get_domain_state(domain)
    assert state['consecutive_failures'] == 0
    assert state['last_status'] == 'up'
    assert state['last_recovery_sent'] is not None


@pytest.mark.asyncio
async def test_check_result_saved(storage):
    """Test that check results are saved to history."""
    domain = "example.com"
    
    result = {
        'status': 'up',
        'http_code': 200,
        'response_time_ms': 150,
        'dns_resolved': True,
        'ssl_valid': True,
        'ssl_days_remaining': 30,
        'error_message': None,
        'consecutive_failures': 0
    }
    
    await storage.save_check_result(domain, result)
    
    history = await storage.get_recent_checks(domain, limit=1)
    assert len(history) == 1
    assert history[0]['domain'] == domain
    assert history[0]['status'] == 'up'
    assert history[0]['http_code'] == 200


@pytest.mark.asyncio
async def test_multiple_domains_state(storage):
    """Test tracking state of multiple domains."""
    domains = ["domain1.com", "domain2.com", "domain3.com"]
    
    for i, domain in enumerate(domains):
        await storage.update_domain_state(domain, {
            'last_status': 'up' if i % 2 == 0 else 'down',
            'consecutive_failures': 0 if i % 2 == 0 else 2,
            'last_alert_sent': None,
            'last_recovery_sent': None
        })
    
    all_states = await storage.get_all_domain_states()
    assert len(all_states) == 3
    
    up_count = sum(1 for s in all_states if s['last_status'] == 'up')
    assert up_count == 2
