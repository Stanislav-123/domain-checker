"""Main application entry point."""

import sys
import asyncio
import signal
from pathlib import Path

from .config import Config
from .scheduler import DomainCheckScheduler
from .bot import DomainBot
from .setup import SetupWizard


def run_setup():
    """Run the setup wizard."""
    wizard = SetupWizard()
    config_dict = wizard.run()
    
    config = Config()
    config.update(config_dict)
    config.save()
    
    print(f"✅ Конфигурация сохранена в {config.config_path}")
    print("\nЗапустите приложение командой:")
    print("  python -m domain_checker")
    print("или")
    print("  domain-checker")


async def run_app():
    """Run the main application."""
    config_path = Path("config.yaml")
    
    if not config_path.exists() and not any(
        var in ['TRACKER_TYPE', 'TRACKER_URL', 'TELEGRAM_BOT_TOKEN']
        for var in __import__('os').environ
    ):
        print("⚠️  Конфигурация не найдена.")
        print("\nЗапустите настройку:")
        print("  python -m domain_checker setup")
        print("или")
        print("  domain-checker setup")
        sys.exit(1)
    
    config = Config(config_path)
    
    if not config.tracker_type or not config.telegram_bot_token:
        print("❌ Неполная конфигурация. Запустите setup.")
        sys.exit(1)
    
    print("=" * 60)
    print("  Domain Checker - Monitoring Service")
    print("=" * 60)
    print(f"\nTracker: {config.tracker_type}")
    print(f"Check interval: {config.check_interval_minutes} minutes")
    print(f"Failure threshold: {config.consecutive_failures_threshold}")
    print()
    
    scheduler = DomainCheckScheduler(config)
    await scheduler.initialize()
    
    bot = DomainBot(
        config.telegram_bot_token,
        config.telegram_chat_id,
        scheduler.checker,
        scheduler.storage,
        scheduler.notifier
    )
    
    print("✅ Service started")
    print("   Press Ctrl+C to stop\n")

    await scheduler.check_all_domains()
    scheduler.start()
    
    stop_event = asyncio.Event()
    
    def signal_handler():
        print("\n\n🛑 Stopping service...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:  # Windows
            signal.signal(sig, lambda *_: stop_event.set())
    
    bot_task = asyncio.create_task(bot.start_polling())
    
    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        print("Cleaning up...")
        scheduler.stop()
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
        await bot.stop()
        await scheduler.cleanup()
        print("✅ Service stopped")


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        run_setup()
    else:
        try:
            asyncio.run(run_app())
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")


if __name__ == '__main__':
    main()
