"""Telegram notification manager."""

import asyncio
from typing import Dict, List
from aiogram import Bot
from aiogram.enums import ParseMode


class Notifier:
    """Manages Telegram notifications with anti-spam logic."""
    
    def __init__(
        self,
        bot_token: str,
        chat_id: int,
        consecutive_failures_threshold: int = 2,
        ssl_warning_days: int = 7
    ):
        """Initialize notifier.
        
        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID to send notifications to
            consecutive_failures_threshold: Number of consecutive failures before alerting
            ssl_warning_days: Days before SSL expiry to warn
        """
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id
        self.consecutive_failures_threshold = consecutive_failures_threshold
        self.ssl_warning_days = ssl_warning_days
    
    async def send_test_message(self) -> bool:
        """Send a test message to verify configuration.
        
        Returns:
            True if message sent successfully
        """
        try:
            await self.bot.send_message(
                self.chat_id,
                "✅ Domain Checker тестовое сообщение\n\n"
                "Бот успешно настроен и готов к работе!"
            )
            return True
        except Exception as e:
            print(f"Failed to send test message: {e}")
            return False
    
    async def notify_domain_down(self, domain: str, result: Dict, consecutive_failures: int):
        """Send notification when domain is down.
        
        Args:
            domain: Domain name
            result: Check result dictionary
            consecutive_failures: Number of consecutive failures
        """
        if consecutive_failures < self.consecutive_failures_threshold:
            return
        
        error_msg = result.get('error_message', 'Unknown error')
        http_code = result.get('http_code')
        
        message = f"🔴 <b>Домен недоступен</b>\n\n"
        message += f"🌐 Домен: <code>{domain}</code>\n"
        message += f"❌ Статус: <b>DOWN</b>\n"
        message += f"🔢 Попыток подряд: {consecutive_failures}\n"
        
        if http_code:
            message += f"📊 HTTP код: {http_code}\n"
        
        if not result.get('dns_resolved'):
            message += f"🔍 DNS: не разрешается\n"
        
        message += f"💬 Ошибка: <code>{error_msg}</code>"
        
        await self._send_message(message)
    
    async def notify_domain_recovered(self, domain: str, result: Dict):
        """Send notification when domain recovers.
        
        Args:
            domain: Domain name
            result: Check result dictionary
        """
        http_code = result.get('http_code', 'N/A')
        response_time = result.get('response_time_ms', 'N/A')
        
        message = f"✅ <b>Домен восстановлен</b>\n\n"
        message += f"🌐 Домен: <code>{domain}</code>\n"
        message += f"✅ Статус: <b>UP</b>\n"
        message += f"📊 HTTP код: {http_code}\n"
        
        if response_time != 'N/A':
            message += f"⏱ Время ответа: {response_time} мс"
        
        await self._send_message(message)
    
    async def notify_ssl_expiring(self, domain: str, days_remaining: int):
        """Send notification when SSL certificate is expiring soon.
        
        Args:
            domain: Domain name
            days_remaining: Days until SSL expiry
        """
        if days_remaining > self.ssl_warning_days:
            return
        
        emoji = "⚠️" if days_remaining > 3 else "🔴"
        
        message = f"{emoji} <b>SSL сертификат истекает</b>\n\n"
        message += f"🌐 Домен: <code>{domain}</code>\n"
        message += f"📅 Дней до истечения: <b>{days_remaining}</b>\n"
        message += f"🔒 Требуется обновление сертификата"
        
        await self._send_message(message)
    
    async def send_status_summary(self, domains_status: List[Dict]) -> str:
        """Send status summary of all domains.
        
        Args:
            domains_status: List of domain status dictionaries
            
        Returns:
            Status summary as string
        """
        total = len(domains_status)
        up_count = sum(1 for d in domains_status if d.get('status') == 'up')
        down_count = total - up_count
        
        message = f"📊 <b>Статус доменов</b>\n\n"
        message += f"Всего доменов: {total}\n"
        message += f"✅ Активных: {up_count}\n"
        message += f"❌ Недоступных: {down_count}\n\n"
        
        if down_count > 0:
            message += "<b>Недоступные домены:</b>\n"
            for domain_info in domains_status:
                if domain_info.get('status') == 'down':
                    domain = domain_info.get('domain', 'unknown')
                    message += f"• <code>{domain}</code>\n"
        
        return message
    
    async def _send_message(self, text: str):
        """Send message to Telegram.
        
        Args:
            text: Message text (HTML formatted)
        """
        try:
            await self.bot.send_message(
                self.chat_id,
                text,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            print(f"Failed to send notification: {e}")
    
    async def close(self):
        """Close bot session."""
        await self.bot.session.close()
