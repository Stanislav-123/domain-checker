"""Tests for Telegram bot commands."""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Chat, Message, User

from domain_checker.bot import DomainBot
from domain_checker.checker import DomainChecker
from domain_checker.notifier import Notifier
from domain_checker.scheduler import DomainCheckScheduler
from domain_checker.storage import Storage


@pytest.fixture
async def storage():
    """Create temporary storage for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    storage = Storage(path)
    await storage.initialize()

    # Add some test domains
    await storage.update_domain_state(
        "active.com",
        {
            "last_status": "up",
            "consecutive_failures": 0,
            "last_alert_sent": None,
            "last_recovery_sent": None,
        },
    )
    await storage.update_domain_state(
        "down.com",
        {
            "last_status": "down",
            "consecutive_failures": 3,
            "last_alert_sent": "2024-01-01T00:00:00",
            "last_recovery_sent": None,
        },
    )

    yield storage

    Path(path).unlink(missing_ok=True)


@pytest.fixture
def mock_message():
    """Create mock message."""
    message = MagicMock(spec=Message)
    message.chat = MagicMock(spec=Chat)
    message.chat.id = 123456
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 123456
    message.reply = AsyncMock()
    return message


@pytest.fixture
def checker():
    """Create domain checker."""
    return DomainChecker(timeout=5, max_concurrent=5)


@pytest.fixture
def notifier():
    """Create mock notifier."""
    notifier = MagicMock(spec=Notifier)
    notifier.bot = MagicMock()
    notifier.chat_id = 123456
    return notifier


@pytest.fixture
def mock_scheduler():
    """Create mock scheduler."""
    scheduler = MagicMock(spec=DomainCheckScheduler)
    scheduler.is_paused = False
    scheduler.check_interval_minutes = 15
    scheduler.pause = MagicMock()
    scheduler.resume = MagicMock()
    scheduler.set_interval = MagicMock()
    return scheduler


@pytest.mark.asyncio
async def test_status_command(storage, mock_message, checker, notifier):
    """Test /status command."""
    with patch("domain_checker.bot.make_bot"):
        bot = DomainBot(
            bot_token="test_token",
            allowed_chat_id=123456,
            checker=checker,
            storage=storage,
            notifier=notifier,
        )

        await bot.cmd_status(mock_message)

        assert mock_message.reply.call_count == 2
        response = mock_message.reply.call_args_list[1][0][0]
        assert "Всего доменов: 2" in response
        assert "Активных: 1" in response


@pytest.mark.asyncio
async def test_list_command(storage, mock_message, checker, notifier):
    """Test /list command."""
    with patch("domain_checker.bot.make_bot"):
        bot = DomainBot(
            bot_token="test_token",
            allowed_chat_id=123456,
            checker=checker,
            storage=storage,
            notifier=notifier,
        )

        await bot.cmd_list(mock_message)

        assert mock_message.reply.call_count == 2
        response = mock_message.reply.call_args_list[1][0][0]
        assert "active.com" in response
        assert "down.com" in response


@pytest.mark.asyncio
async def test_pause_command(
    storage, mock_message, checker, notifier, mock_scheduler
):
    """Test /pause command."""
    with patch("domain_checker.bot.make_bot"):
        bot = DomainBot(
            bot_token="test_token",
            allowed_chat_id=123456,
            checker=checker,
            storage=storage,
            notifier=notifier,
            scheduler=mock_scheduler,
        )

        await bot.cmd_pause(mock_message)

        mock_scheduler.pause.assert_called_once()
        assert mock_message.reply.call_count == 1


@pytest.mark.asyncio
async def test_resume_command(
    storage, mock_message, checker, notifier, mock_scheduler
):
    """Test /resume command."""
    with patch("domain_checker.bot.make_bot"):
        bot = DomainBot(
            bot_token="test_token",
            allowed_chat_id=123456,
            checker=checker,
            storage=storage,
            notifier=notifier,
            scheduler=mock_scheduler,
        )

        mock_scheduler.is_paused = True
        await bot.cmd_resume(mock_message)

        mock_scheduler.resume.assert_called_once()
        assert mock_message.reply.call_count == 1


@pytest.mark.asyncio
async def test_interval_command(
    storage, mock_message, checker, notifier, mock_scheduler
):
    """Test /interval command."""
    with patch("domain_checker.bot.make_bot"):
        bot = DomainBot(
            bot_token="test_token",
            allowed_chat_id=123456,
            checker=checker,
            storage=storage,
            notifier=notifier,
            scheduler=mock_scheduler,
        )

        # Test with valid interval
        mock_message.text = "/interval 30"
        await bot.cmd_interval(mock_message)

        mock_scheduler.set_interval.assert_called_once_with(30)
        assert mock_message.reply.call_count == 1


@pytest.mark.asyncio
async def test_interval_command_no_args(
    storage, mock_message, checker, notifier, mock_scheduler
):
    """Test /interval command without arguments."""
    with patch("domain_checker.bot.make_bot"):
        bot = DomainBot(
            bot_token="test_token",
            allowed_chat_id=123456,
            checker=checker,
            storage=storage,
            notifier=notifier,
            scheduler=mock_scheduler,
        )

        mock_message.text = "/interval"
        await bot.cmd_interval(mock_message)

        mock_scheduler.set_interval.assert_not_called()
        assert mock_message.reply.call_count == 1
        response = mock_message.reply.call_args[0][0]
        assert "Текущий интервал" in response


@pytest.mark.asyncio
async def test_unauthorized_access(storage, mock_message, checker, notifier):
    """Test unauthorized access."""
    with patch("domain_checker.bot.make_bot"):
        bot = DomainBot(
            bot_token="test_token",
            allowed_chat_id=999999,  # Different chat ID
            checker=checker,
            storage=storage,
            notifier=notifier,
        )

        await bot.cmd_status(mock_message)

        # Unauthorized users should not receive a reply
        assert mock_message.reply.call_count == 0


@pytest.mark.asyncio
async def test_check_command(storage, mock_message, checker, notifier):
    """Test /check command."""
    with patch("domain_checker.bot.make_bot"):
        bot = DomainBot(
            bot_token="test_token",
            allowed_chat_id=123456,
            checker=checker,
            storage=storage,
            notifier=notifier,
        )

        # Mock check_domain
        checker.check_domain = AsyncMock(
            return_value={
                "domain": "test.com",
                "status": "up",
                "dns_resolved": True,
                "http_code": 200,
                "response_time_ms": 100,
                "ssl_valid": True,
                "ssl_days_remaining": 30,
                "error_message": None,
            }
        )

        mock_message.text = "/check test.com"
        await bot.cmd_check(mock_message)

        assert mock_message.reply.call_count == 2
        response = mock_message.reply.call_args[0][0]
        assert "test.com" in response
        assert "UP" in response
