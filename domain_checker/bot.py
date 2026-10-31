"""Telegram bot for domain monitoring."""

from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from .checker import DomainChecker
from .logging import get_logger
from .notifier import Notifier, make_bot
from .storage import Storage

logger = get_logger(__name__)


class DomainBot:
    """Telegram bot for domain monitoring commands."""

    def __init__(
        self,
        bot_token: str,
        allowed_chat_id: int,
        checker: DomainChecker,
        storage: Storage,
        notifier: Notifier,
        scheduler=None,
    ):
        """Initialize bot.

        Args:
            bot_token: Telegram bot token
            allowed_chat_id: Allowed chat ID for commands
            checker: Domain checker instance
            storage: Storage instance
            notifier: Notifier instance
            scheduler: Domain check scheduler instance (optional, for /pause and /interval)
        """
        self.bot = make_bot(bot_token)
        self.dp = Dispatcher()
        self.allowed_chat_id = allowed_chat_id
        self.checker = checker
        self.storage = storage
        self.notifier = notifier
        self.scheduler = scheduler

        self._register_handlers()

    def _register_handlers(self):
        """Register command handlers."""
        self.dp.message(Command("start"))(self.cmd_start)
        self.dp.message(Command("status"))(self.cmd_status)
        self.dp.message(Command("check"))(self.cmd_check)
        self.dp.message(Command("list"))(self.cmd_list)
        self.dp.message(Command("help"))(self.cmd_help)
        self.dp.message(Command("pause"))(self.cmd_pause)
        self.dp.message(Command("resume"))(self.cmd_resume)
        self.dp.message(Command("interval"))(self.cmd_interval)

    def _is_authorized(self, message: Message) -> bool:
        """Check if message is from authorized chat.

        Args:
            message: Telegram message

        Returns:
            True if authorized
        """
        return message.chat.id == self.allowed_chat_id

    async def cmd_start(self, message: Message):
        """Handle /start command."""
        if not self._is_authorized(message):
            await message.reply("⛔️ У вас нет доступа к этому боту.")
            return

        await message.reply(
            "👋 <b>Domain Checker Bot</b>\n\n"
            "Доступные команды:\n"
            "/status - общий статус всех доменов\n"
            "/check <домен> - проверить конкретный домен\n"
            "/list - список всех отслеживаемых доменов\n"
            "/pause - приостановить проверки\n"
            "/resume - возобновить проверки\n"
            "/interval <минуты> - изменить интервал проверок\n"
            "/help - справка",
            parse_mode="HTML",
        )

    async def cmd_help(self, message: Message):
        """Handle /help command."""
        if not self._is_authorized(message):
            return

        help_text = (
            "📖 <b>Справка Domain Checker</b>\n\n"
            "<b>/status</b>\n"
            "Показывает сводку по всем доменам: сколько активных, сколько упало.\n\n"
            "<b>/check &lt;домен&gt;</b>\n"
            "Проверяет конкретный домен прямо сейчас.\n"
            "Пример: /check example.com\n\n"
            "<b>/list</b>\n"
            "Показывает список всех отслеживаемых активных доменов с их текущим статусом.\n\n"
        )

        if self.scheduler:
            help_text += (
                "<b>/pause</b>\n"
                "Приостанавливает автоматические проверки доменов.\n\n"
                "<b>/resume</b>\n"
                "Возобновляет автоматические проверки доменов.\n\n"
                "<b>/interval &lt;минуты&gt;</b>\n"
                "Изменяет интервал между проверками.\n"
                "Пример: /interval 30\n\n"
            )

        help_text += (
            "Бот автоматически отправляет уведомления:\n"
            "• 🔴 Когда домен падает\n"
            "• ✅ Когда домен восстанавливается\n"
            "• ⚠️ Когда SSL сертификат скоро истекает\n\n"
            "При множественных проблемах отправляется сводный отчёт."
        )

        await message.reply(help_text, parse_mode="HTML")

    async def cmd_status(self, message: Message):
        """Handle /status command."""
        if not self._is_authorized(message):
            return

        await message.reply("🔄 Получаю статус доменов...")

        try:
            states = await self.storage.get_all_domain_states(active_only=True)

            if not states:
                await message.reply("📭 Пока нет данных о доменах.")
                return

            total = len(states)
            up_count = sum(1 for s in states if s.get("last_status") == "up")
            down_count = sum(1 for s in states if s.get("consecutive_failures", 0) > 0)

            text = "📊 <b>Статус доменов</b>\n\n"
            text += f"Всего доменов: {total}\n"
            text += f"✅ Активных: {up_count}\n"
            text += f"❌ С проблемами: {down_count}\n"

            if self.scheduler:
                status = "⏸ Приостановлен" if self.scheduler.is_paused else "▶️ Активен"
                text += f"🔄 Статус мониторинга: {status}\n"
                text += f"⏱ Интервал: {self.scheduler.check_interval_minutes} мин.\n"

            if down_count > 0:
                text += "\n<b>Проблемные домены:</b>\n"
                for state in states:
                    if state.get("consecutive_failures", 0) > 0:
                        domain = state["domain"]
                        failures = state["consecutive_failures"]
                        text += f"• <code>{domain}</code> (попыток: {failures})\n"

            await message.reply(text, parse_mode="HTML")

        except Exception as e:
            logger.error("status_command_error", error=str(e))
            await message.reply(f"❌ Ошибка: {str(e)}")

    async def cmd_check(self, message: Message):
        """Handle /check <domain> command."""
        if not self._is_authorized(message):
            return

        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply(
                "⚠️ Укажите домен для проверки.\nПример: /check example.com"
            )
            return

        domain = parts[1].strip()
        await message.reply(f"🔄 Проверяю домен {domain}...")

        try:
            result = await self.checker.check_domain(domain)

            status_emoji = "✅" if result["status"] == "up" else "❌"
            text = f"{status_emoji} <b>Результат проверки</b>\n\n"
            text += f"🌐 Домен: <code>{domain}</code>\n"
            text += f"📊 Статус: <b>{result['status'].upper()}</b>\n"

            if result.get("dns_resolved") is not None:
                dns_emoji = "✅" if result["dns_resolved"] else "❌"
                text += f"{dns_emoji} DNS: {'разрешается' if result['dns_resolved'] else 'не разрешается'}\n"

            if result.get("http_code"):
                text += f"🔢 HTTP код: {result['http_code']}\n"

            if result.get("response_time_ms"):
                text += f"⏱ Время ответа: {result['response_time_ms']} мс\n"

            if result.get("ssl_valid") is not None:
                ssl_emoji = "✅" if result["ssl_valid"] else "❌"
                text += f"{ssl_emoji} SSL: {'валиден' if result['ssl_valid'] else 'не валиден'}\n"

                if result.get("ssl_days_remaining") is not None:
                    days = result["ssl_days_remaining"]
                    text += f"📅 До истечения SSL: {days} дн.\n"

            if result.get("error_message"):
                text += f"\n💬 Ошибка: <code>{result['error_message']}</code>"

            await message.reply(text, parse_mode="HTML")

        except Exception as e:
            await message.reply(f"❌ Ошибка при проверке: {str(e)}")

    async def cmd_list(self, message: Message):
        """Handle /list command."""
        if not self._is_authorized(message):
            return

        await message.reply("🔄 Получаю список доменов...")

        try:
            states = await self.storage.get_all_domain_states(active_only=True)

            if not states:
                await message.reply("📭 Список активных доменов пуст.")
                return

            text = f"📋 <b>Отслеживаемые домены ({len(states)})</b>\n\n"

            for state in sorted(states, key=lambda x: x["domain"]):
                domain = state["domain"]
                status = state.get("last_status", "unknown")
                failures = state.get("consecutive_failures", 0)

                emoji = "✅" if status == "up" and failures == 0 else "❌"
                text += f"{emoji} <code>{domain}</code>"

                if failures > 0:
                    text += f" (попыток: {failures})"

                text += "\n"

            await message.reply(text, parse_mode="HTML")

        except Exception as e:
            logger.error("list_command_error", error=str(e))
            await message.reply(f"❌ Ошибка: {str(e)}")

    async def start_polling(self):
        """Start bot polling."""
        # handle_as_tasks=False: process commands in the order they were sent,
        # so "/pause" then "/resume" can't end up applied in reverse.
        await self.dp.start_polling(
            self.bot, handle_signals=False, handle_as_tasks=False
        )

    async def cmd_pause(self, message: Message):
        """Handle /pause command."""
        if not self._is_authorized(message):
            return

        if not self.scheduler:
            await message.reply("⚠️ Эта команда недоступна.")
            return

        if self.scheduler.is_paused:
            await message.reply("⏸ Мониторинг уже приостановлен.")
        else:
            self.scheduler.pause()
            await message.reply(
                "⏸ Мониторинг приостановлен. Используйте /resume для возобновления."
            )
            logger.info("monitoring_paused_via_bot", chat_id=message.chat.id)

    async def cmd_resume(self, message: Message):
        """Handle /resume command."""
        if not self._is_authorized(message):
            return

        if not self.scheduler:
            await message.reply("⚠️ Эта команда недоступна.")
            return

        if not self.scheduler.is_paused:
            await message.reply("▶️ Мониторинг уже активен.")
        else:
            self.scheduler.resume()
            await message.reply("▶️ Мониторинг возобновлён.")
            logger.info("monitoring_resumed_via_bot", chat_id=message.chat.id)

    async def cmd_interval(self, message: Message):
        """Handle /interval <minutes> command."""
        if not self._is_authorized(message):
            return

        if not self.scheduler:
            await message.reply("⚠️ Эта команда недоступна.")
            return

        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            current = self.scheduler.check_interval_minutes
            await message.reply(
                f"⏱ Текущий интервал: <b>{current}</b> мин.\n\n"
                "Для изменения укажите новое значение:\n"
                "/interval &lt;минуты&gt;\n"
                "Пример: /interval 30",
                parse_mode="HTML",
            )
            return

        try:
            minutes = int(parts[1])
            if minutes < 1:
                await message.reply("❌ Интервал должен быть не менее 1 минуты.")
                return

            if minutes > 1440:
                await message.reply(
                    "❌ Интервал не может быть больше 1440 минут (24 часа)."
                )
                return

            old_interval = self.scheduler.check_interval_minutes
            self.scheduler.set_interval(minutes)
            await message.reply(
                f"✅ Интервал изменён: <b>{old_interval}</b> → <b>{minutes}</b> мин.",
                parse_mode="HTML",
            )
            logger.info(
                "interval_changed_via_bot",
                old=old_interval,
                new=minutes,
                chat_id=message.chat.id,
            )

        except ValueError:
            await message.reply(
                "❌ Неверный формат. Укажите число минут.\nПример: /interval 30"
            )
        except Exception as e:
            logger.error("interval_command_error", error=str(e))
            await message.reply(f"❌ Ошибка: {str(e)}")

    async def stop(self):
        """Stop bot."""
        await self.bot.session.close()
