"""Interactive setup wizard."""

import sys
from pathlib import Path
from typing import Dict, Any


class SetupWizard:
    """Interactive CLI setup wizard."""
    
    def __init__(self):
        """Initialize setup wizard."""
        self.config: Dict[str, Any] = {
            'tracker': {},
            'telegram': {},
            'checker': {},
            'database': {}
        }
    
    def run(self) -> Dict[str, Any]:
        """Run interactive setup wizard.
        
        Returns:
            Configuration dictionary
        """
        print("\n" + "=" * 60)
        print("  Domain Checker - Настройка")
        print("=" * 60 + "\n")
        
        self._setup_tracker()
        self._setup_telegram()
        self._setup_checker()
        self._setup_database()
        
        print("\n✅ Настройка завершена!\n")
        
        return self.config
    
    def _setup_tracker(self):
        """Setup tracker configuration."""
        print("📡 НАСТРОЙКА ТРЕКЕРА\n")
        
        print("Выберите тип трекера:")
        print("  1. Keitaro")
        print("  2. Binom")
        print("  3. Custom (собственный API)")
        
        choice = self._input_choice("Ваш выбор (1-3): ", ['1', '2', '3'])
        
        tracker_types = {'1': 'keitaro', '2': 'binom', '3': 'custom'}
        tracker_type = tracker_types[choice]
        
        self.config['tracker']['type'] = tracker_type
        
        if tracker_type == 'keitaro':
            print("\n📝 Keitaro использует Admin API")
            print("   Эндпоинт: /admin_api/v1/domains")
            print("   Документация: https://admin-api.docs.keitaro.io/\n")
            
            url = self._input_text("Базовый URL трекера (например, https://tracker.example.com): ")
            api_key = self._input_text("API ключ (Api-Key header): ", hide=True)
            
            self.config['tracker']['url'] = url.rstrip('/')
            self.config['tracker']['api_key'] = api_key
        
        elif tracker_type == 'binom':
            print("\n📝 Binom API")
            print("   Эндпоинт: /api.php?page=Domains&api_key=KEY")
            print("   Документация: https://docs.binom.org/api.php\n")
            
            url = self._input_text("Базовый URL трекера (например, https://tracker.example.com): ")
            api_key = self._input_text("API ключ: ", hide=True)
            
            self.config['tracker']['url'] = url.rstrip('/')
            self.config['tracker']['api_key'] = api_key
        
        elif tracker_type == 'custom':
            print("\n📝 Custom API")
            print("   Поддерживает JSON (список/объект) или plain text (построчно)\n")
            
            url = self._input_text("URL эндпоинта API: ")
            api_key = self._input_text("API ключ: ", hide=True)
            
            header_name = self._input_text(
                "Имя заголовка для API ключа (по умолчанию: Authorization): ",
                default="Authorization"
            )
            
            domains_path = self._input_text(
                "Путь к доменам в JSON (например: domains или data.domains): ",
                default="domains"
            )
            
            self.config['tracker']['url'] = url
            self.config['tracker']['api_key'] = api_key
            self.config['tracker']['custom'] = {
                'header_name': header_name,
                'domains_path': domains_path
            }
        
        print()
    
    def _setup_telegram(self):
        """Setup Telegram configuration."""
        print("💬 НАСТРОЙКА TELEGRAM\n")
        
        print("Для получения Bot Token:")
        print("  1. Напишите @BotFather в Telegram")
        print("  2. Создайте бота командой /newbot")
        print("  3. Скопируйте полученный токен\n")
        
        bot_token = self._input_text("Telegram Bot Token: ", hide=True)
        
        print("\nДля получения Chat ID:")
        print("  1. Напишите @userinfobot в Telegram")
        print("  2. Скопируйте ваш Chat ID\n")
        
        chat_id = self._input_text("Telegram Chat ID: ")
        
        self.config['telegram']['bot_token'] = bot_token
        self.config['telegram']['chat_id'] = int(chat_id)
        
        send_test = self._input_yes_no("\nОтправить тестовое сообщение? (y/n): ")
        
        if send_test:
            import asyncio
            from .notifier import Notifier
            
            notifier = Notifier(bot_token, int(chat_id))
            
            print("Отправка тестового сообщения...")
            success = asyncio.run(notifier.send_test_message())
            asyncio.run(notifier.close())
            
            if success:
                print("✅ Тестовое сообщение отправлено успешно!")
            else:
                print("❌ Ошибка отправки. Проверьте токен и Chat ID.")
        
        print()
    
    def _setup_checker(self):
        """Setup checker configuration."""
        print("⚙️  НАСТРОЙКА ПРОВЕРОК\n")
        
        print("Выберите интервал проверки:")
        print("  1. Каждые 5 минут")
        print("  2. Каждые 15 минут (рекомендуется)")
        print("  3. Каждые 30 минут")
        print("  4. Каждый час")
        print("  5. Каждые 3 часа")
        print("  6. Каждые 6 часов")
        print("  7. Свой интервал (в минутах)")
        
        choice = self._input_choice("Ваш выбор (1-7): ", ['1', '2', '3', '4', '5', '6', '7'])
        
        intervals = {
            '1': 5,
            '2': 15,
            '3': 30,
            '4': 60,
            '5': 180,
            '6': 360
        }
        
        if choice == '7':
            interval = int(self._input_text("Интервал в минутах: "))
        else:
            interval = intervals[choice]
        
        self.config['checker']['interval_minutes'] = interval
        
        threshold = self._input_text(
            "\nКоличество неудачных попыток перед алертом (по умолчанию: 2): ",
            default="2"
        )
        self.config['checker']['consecutive_failures_threshold'] = int(threshold)
        
        ssl_days = self._input_text(
            "Предупреждать об истечении SSL за N дней (по умолчанию: 7): ",
            default="7"
        )
        self.config['checker']['ssl_warning_days'] = int(ssl_days)
        
        concurrent = self._input_text(
            "Максимум одновременных проверок (по умолчанию: 10): ",
            default="10"
        )
        self.config['checker']['max_concurrent_checks'] = int(concurrent)
        
        timeout = self._input_text(
            "Таймаут запроса в секундах (по умолчанию: 10): ",
            default="10"
        )
        self.config['checker']['request_timeout_seconds'] = int(timeout)
        
        print()
    
    def _setup_database(self):
        """Setup database configuration."""
        print("💾 НАСТРОЙКА БАЗЫ ДАННЫХ\n")
        
        db_path = self._input_text(
            "Путь к базе данных SQLite (по умолчанию: data/domain_checker.db): ",
            default="data/domain_checker.db"
        )
        
        self.config['database']['path'] = db_path
        print()
    
    def _input_text(self, prompt: str, default: str = "", hide: bool = False) -> str:
        """Get text input from user.
        
        Args:
            prompt: Input prompt
            default: Default value
            hide: Hide input (for passwords)
            
        Returns:
            User input string
        """
        while True:
            if hide:
                import getpass
                value = getpass.getpass(prompt)
            else:
                value = input(prompt).strip()
            
            if value:
                return value
            elif default:
                return default
            else:
                print("❌ Это поле обязательно для заполнения.")
    
    def _input_choice(self, prompt: str, valid_choices: list) -> str:
        """Get choice input from user.
        
        Args:
            prompt: Input prompt
            valid_choices: List of valid choices
            
        Returns:
            User choice
        """
        while True:
            choice = input(prompt).strip()
            if choice in valid_choices:
                return choice
            print(f"❌ Выберите один из вариантов: {', '.join(valid_choices)}")
    
    def _input_yes_no(self, prompt: str) -> bool:
        """Get yes/no input from user.
        
        Args:
            prompt: Input prompt
            
        Returns:
            True for yes, False for no
        """
        while True:
            choice = input(prompt).strip().lower()
            if choice in ['y', 'yes', 'д', 'да']:
                return True
            elif choice in ['n', 'no', 'н', 'нет']:
                return False
            print("❌ Введите y (да) или n (нет)")
