"""Telegram notification manager."""

import asyncio
import html
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter


def make_bot(token: str):
    """Create aiogram Bot; honours TELEGRAM_API_URL (self-hosted Bot API server)."""
    import os

    api_url = os.getenv("TELEGRAM_API_URL")
    if api_url:
        from aiogram.client.session.aiohttp import AiohttpSession
        from aiogram.client.telegram import TelegramAPIServer

        return Bot(
            token=token,
            session=AiohttpSession(api=TelegramAPIServer.from_base(api_url)),
        )
    return Bot(token=token)


class Notifier:
    """Manages Telegram notifications with anti-spam logic."""

    def __init__(
        self,
        bot_token: str,
        chat_id: int,
        consecutive_failures_threshold: int = 2,
        ssl_warning_days: int = 7,
        batch_threshold: int = 5,
    ):
        """Initialize notifier.

        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID to send notifications to
            consecutive_failures_threshold: Number of consecutive failures before alerting
            ssl_warning_days: Days before SSL expiry to warn
            batch_threshold: Number of down domains to trigger batch notification
        """
        self.bot = make_bot(bot_token)
        self.chat_id = chat_id
        self.consecutive_failures_threshold = consecutive_failures_threshold
        self.ssl_warning_days = ssl_warning_days
        self.batch_threshold = batch_threshold
        self._pending_down_domains: list[dict] = []
        self._last_batch_sent: datetime = None

    async def send_test_message(self) -> bool:
        """Send a test message to verify configuration.

        Returns:
            True if message sent successfully
        """
        try:
            await self.bot.send_message(
                self.chat_id,
                "✅ Domain Checker тестовое сообщение\n\n"
                "Бот успешно настроен и готов к работе!",
            )
            return True
        except Exception as e:
            print(f"Failed to send test message: {e}")
            return False

    async def notify_domain_down(
        self, domain: str, result: dict, consecutive_failures: int
    ):
        """Send notification when domain is down.

        Args:
            domain: Domain name
            result: Check result dictionary
            consecutive_failures: Number of consecutive failures
        """
        if consecutive_failures < self.consecutive_failures_threshold:
            return

        self._pending_down_domains.append(
            {
                "domain": domain,
                "result": result,
                "consecutive_failures": consecutive_failures,
            }
        )

    async def flush_pending_alerts(self):
        """Send pending down domain alerts, batching if many domains are down."""
        if not self._pending_down_domains:
            return

        count = len(self._pending_down_domains)

        # If many domains are down, send a batch summary instead of individual alerts
        if count >= self.batch_threshold:
            message = "🔴 <b>Множественные проблемы с доменами</b>\n\n"
            message += f"❌ Недоступных доменов: <b>{count}</b>\n\n"
            message += "<b>Список:</b>\n"

            for item in self._pending_down_domains[:20]:  # Limit to 20 in message
                domain = item["domain"]
                error = item["result"].get("error_message", "Unknown")
                message += f"• <code>{domain}</code> - {html.escape(str(error)[:50])}\n"

            if count > 20:
                message += f"\n...и ещё {count - 20} доменов"

            await self._send_message(message)
        else:
            # Send individual alerts
            for item in self._pending_down_domains:
                await self._send_individual_down_alert(
                    item["domain"], item["result"], item["consecutive_failures"]
                )

        self._pending_down_domains = []
        self._last_batch_sent = datetime.now(timezone.utc)

    async def _send_individual_down_alert(
        self, domain: str, result: dict, consecutive_failures: int
    ):
        """Send individual down alert."""
        error_msg = result.get("error_message", "Unknown error")
        http_code = result.get("http_code")

        message = "🔴 <b>Домен недоступен</b>\n\n"
        message += f"🌐 Домен: <code>{domain}</code>\n"
        message += "❌ Статус: <b>DOWN</b>\n"
        message += f"🔢 Попыток подряд: {consecutive_failures}\n"

        if http_code:
            message += f"📊 HTTP код: {http_code}\n"

        if not result.get("dns_resolved"):
            message += "🔍 DNS: не разрешается\n"

        message += f"💬 Ошибка: <code>{html.escape(str(error_msg))}</code>"

        await self._send_message(message)

    async def notify_domain_recovered(self, domain: str, result: dict):
        """Send notification when domain recovers.

        Args:
            domain: Domain name
            result: Check result dictionary
        """
        http_code = result.get("http_code", "N/A")
        response_time = result.get("response_time_ms", "N/A")

        message = "✅ <b>Домен восстановлен</b>\n\n"
        message += f"🌐 Домен: <code>{domain}</code>\n"
        message += "✅ Статус: <b>UP</b>\n"
        message += f"📊 HTTP код: {http_code}\n"

        if response_time != "N/A":
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
        message += "🔒 Требуется обновление сертификата"

        await self._send_message(message)

    async def send_status_summary(self, domains_status: list[dict]) -> str:
        """Send status summary of all domains.

        Args:
            domains_status: List of domain status dictionaries

        Returns:
            Status summary as string
        """
        total = len(domains_status)
        up_count = sum(1 for d in domains_status if d.get("status") == "up")
        down_count = total - up_count

        message = "📊 <b>Статус доменов</b>\n\n"
        message += f"Всего доменов: {total}\n"
        message += f"✅ Активных: {up_count}\n"
        message += f"❌ Недоступных: {down_count}\n\n"

        if down_count > 0:
            message += "<b>Недоступные домены:</b>\n"
            for domain_info in domains_status:
                if domain_info.get("status") == "down":
                    domain = domain_info.get("domain", "unknown")
                    message += f"• <code>{domain}</code>\n"

        return message

    async def notify_source_error(self, tracker: str, error: str):
        """Tell the user the domain list could not be fetched."""
        await self._send_message(
            f"⚠️ <b>Не удалось получить домены из трекера</b>\n\n"
            f"📡 Трекер: <code>{tracker}</code>\n"
            f"💬 Ошибка: <code>{html.escape(error[:500])}</code>"
        )

    async def notify_source_recovered(self, tracker: str):
        """Tell the user the tracker API works again."""
        await self._send_message(
            f"✅ <b>Трекер снова отвечает</b>: <code>{tracker}</code>"
        )

    async def _send_message(self, text: str, retry_count: int = 0):
        """Send message to Telegram with rate limit handling.

        Args:
            text: Message text (HTML formatted)
            retry_count: Current retry attempt
        """
        try:
            await self.bot.send_message(self.chat_id, text, parse_mode=ParseMode.HTML)
        except TelegramRetryAfter as e:
            # Telegram rate limit hit - wait and retry
            wait_seconds = e.retry_after if hasattr(e, "retry_after") else 30
            if retry_count < 3:
                print(f"Telegram rate limit hit, waiting {wait_seconds}s...")
                await asyncio.sleep(wait_seconds)
                await self._send_message(text, retry_count + 1)
            else:
                print(f"Failed to send after {retry_count} retries due to rate limit")
        except TelegramAPIError as e:
            print(f"Telegram API error: {e}")
        except Exception as e:
            print(f"Failed to send notification: {e}")

    async def close(self):
        """Close bot session."""
        await self.bot.session.close()
