"""Telegram bot for domain monitoring."""

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from typing import Optional
from .checker import DomainChecker
from .storage import Storage
from .notifier import Notifier, make_bot


class DomainBot:
    """Telegram bot for domain monitoring commands."""
    
    def __init__(
        self,
        bot_token: str,
        allowed_chat_id: int,
        checker: DomainChecker,
        storage: Storage,
        notifier: Notifier
    ):
        """Initialize bot.
        
        Args:
            bot_token: Telegram bot token
            allowed_chat_id: Allowed chat ID for commands
            checker: Domain checker instance
            storage: Storage instance
            notifier: Notifier instance
        """
        self.bot = make_bot(bot_token)
        self.dp = Dispatcher()
        self.allowed_chat_id = allowed_chat_id
        self.checker = checker
        self.storage = storage
        self.notifier = notifier
        
        self._register_handlers()
    
    def _register_handlers(self):
        """Register command handlers."""
        self.dp.message(Command("start"))(self.cmd_start)
        self.dp.message(Command("status"))(self.cmd_status)
        self.dp.message(Command("check"))(self.cmd_check)
        self.dp.message(Command("list"))(self.cmd_list)
        self.dp.message(Command("help"))(self.cmd_help)
    
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
            "/help - справка",
            parse_mode="HTML"
        )
    
    async def cmd_help(self, message: Message):
        """Handle /help command."""
        if not self._is_authorized(message):
            return
        
        await message.reply(
            "📖 <b>Справка Domain Checker</b>\n\n"
            "<b>/status</b>\n"
            "Показывает сводку по всем доменам: сколько активных, сколько упало.\n\n"
            "<b>/check &lt;домен&gt;</b>\n"
            "Проверяет конкретный домен прямо сейчас.\n"
            "Пример: /check example.com\n\n"
            "<b>/list</b>\n"
            "Показывает список всех отслеживаемых доменов с их текущим статусом.\n\n"
            "Бот автоматически отправляет уведомления, когда домен падает или восстанавливается.",
            parse_mode="HTML"
        )
    
    async def cmd_status(self, message: Message):
        """Handle /status command."""
        if not self._is_authorized(message):
            return
        
        await message.reply("🔄 Получаю статус доменов...")
        
        try:
            states = await self.storage.get_all_domain_states()
            
            if not states:
                await message.reply("📭 Пока нет данных о доменах.")
                return
            
            total = len(states)
            up_count = sum(1 for s in states if s.get('last_status') == 'up')
            down_count = sum(1 for s in states if s.get('consecutive_failures', 0) > 0)
            
            text = f"📊 <b>Статус доменов</b>\n\n"
            text += f"Всего доменов: {total}\n"
            text += f"✅ Активных: {up_count}\n"
            text += f"❌ С проблемами: {down_count}\n"
            
            if down_count > 0:
                text += f"\n<b>Проблемные домены:</b>\n"
                for state in states:
                    if state.get('consecutive_failures', 0) > 0:
                        domain = state['domain']
                        failures = state['consecutive_failures']
                        text += f"• <code>{domain}</code> (попыток: {failures})\n"
            
            await message.reply(text, parse_mode="HTML")
            
        except Exception as e:
            await message.reply(f"❌ Ошибка: {str(e)}")
    
    async def cmd_check(self, message: Message):
        """Handle /check <domain> command."""
        if not self._is_authorized(message):
            return
        
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply(
                "⚠️ Укажите домен для проверки.\n"
                "Пример: /check example.com"
            )
            return
        
        domain = parts[1].strip()
        await message.reply(f"🔄 Проверяю домен {domain}...")
        
        try:
            result = await self.checker.check_domain(domain)
            
            status_emoji = "✅" if result['status'] == 'up' else "❌"
            text = f"{status_emoji} <b>Результат проверки</b>\n\n"
            text += f"🌐 Домен: <code>{domain}</code>\n"
            text += f"📊 Статус: <b>{result['status'].upper()}</b>\n"
            
            if result.get('dns_resolved') is not None:
                dns_emoji = "✅" if result['dns_resolved'] else "❌"
                text += f"{dns_emoji} DNS: {'разрешается' if result['dns_resolved'] else 'не разрешается'}\n"
            
            if result.get('http_code'):
                text += f"🔢 HTTP код: {result['http_code']}\n"
            
            if result.get('response_time_ms'):
                text += f"⏱ Время ответа: {result['response_time_ms']} мс\n"
            
            if result.get('ssl_valid') is not None:
                ssl_emoji = "✅" if result['ssl_valid'] else "❌"
                text += f"{ssl_emoji} SSL: {'валиден' if result['ssl_valid'] else 'не валиден'}\n"
                
                if result.get('ssl_days_remaining') is not None:
                    days = result['ssl_days_remaining']
                    text += f"📅 До истечения SSL: {days} дн.\n"
            
            if result.get('error_message'):
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
            states = await self.storage.get_all_domain_states()
            
            if not states:
                await message.reply("📭 Список доменов пуст.")
                return
            
            text = f"📋 <b>Отслеживаемые домены ({len(states)})</b>\n\n"
            
            for state in sorted(states, key=lambda x: x['domain']):
                domain = state['domain']
                status = state.get('last_status', 'unknown')
                failures = state.get('consecutive_failures', 0)
                
                emoji = "✅" if status == 'up' and failures == 0 else "❌"
                text += f"{emoji} <code>{domain}</code>"
                
                if failures > 0:
                    text += f" (попыток: {failures})"
                
                text += "\n"
            
            await message.reply(text, parse_mode="HTML")
            
        except Exception as e:
            await message.reply(f"❌ Ошибка: {str(e)}")
    
    async def start_polling(self):
        """Start bot polling."""
        await self.dp.start_polling(self.bot, handle_signals=False)
    
    async def stop(self):
        """Stop bot."""
        await self.bot.session.close()
