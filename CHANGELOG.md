# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-11-01

### Added
- Автоматическая миграция БД, созданной версией 1.0.x
- **Structured logging** with `structlog` for production-grade log management
  - Automatic log sanitization to prevent API key leakage
  - JSON output for non-TTY environments (Docker, systemd)
  - Configurable log levels via `LOG_LEVEL` environment variable
  - Log rotation support for file-based logging
- **Enhanced Telegram bot commands**
  - `/help` - Comprehensive command documentation
  - `/pause` - Pause automatic domain checking
  - `/resume` - Resume automatic domain checking
  - `/interval <minutes>` - Change check interval at runtime
- **Domain lifecycle management**
  - Automatic tracking of active/inactive domains
  - Domains removed from tracker are marked inactive
  - Inactive domains excluded from `/list` and alerts
- **Message batching for Telegram**
  - Batch summary when many domains (5+) fail simultaneously
  - Prevents Telegram rate limiting during mass outages
  - Individual alerts for small-scale issues
- **Retry logic with exponential backoff**
  - Automatic retries for tracker API calls (up to 3 attempts)
  - Graceful handling of temporary network failures
  - Uses `tenacity` library for robust retry patterns
- **Rate limit handling for Telegram API**
  - Automatic detection and handling of rate limits
  - Respects `retry_after` headers from Telegram
  - Prevents message loss during rate limiting
- **Enhanced Docker support**
  - Non-root user (UID 1000) for security
  - Health check for container monitoring
  - Separate volumes for data and logs
  - Support for self-hosted Telegram Bot API via `TELEGRAM_API_URL`
- **GitHub Actions CI/CD**
  - Automated linting with `ruff`
  - Test suite on Python 3.10, 3.11, 3.12
  - Optional Docker build verification
  - Code coverage reporting
- **Configuration security improvements**
  - File permissions (600) automatically set on `config.yaml`
  - Full support for environment variable configuration
  - Secrets never logged (automatic sanitization)
- **Binom API improvements**
  - Clear documentation of multi-endpoint fallback strategy
  - Better error messages for endpoint discovery
  - Comprehensive support for v1 and v2 APIs

### Changed
- **Docker Compose** now includes healthcheck and proper volume mounts
- **Bot commands** now show monitoring status (paused/active) in `/status`
- **Domain list** (`/list`) now only shows active domains by default
- **Logging** migrated from print statements to structured logging
- **Storage schema** extended with `is_active` and `last_seen` fields
- **Notifier** now queues alerts and flushes in batches

### Fixed
- Race conditions in concurrent domain checking
- Memory leaks in long-running deployments
- Telegram API errors now handled gracefully
- Database migrations handled automatically

### Security
- Sensitive values (API keys, tokens) automatically redacted in logs
- Configuration files created with restrictive permissions (600)
- Docker container runs as non-root user by default
- Environment variable validation and sanitization

## [1.0.0] - 2024-11-15

### Added
- Initial release
- Keitaro, Binom, and Custom API tracker support
- Telegram notifications for domain failures and SSL expiry
- SQLite-based storage for domain state and history
- Configurable check intervals and thresholds
- Docker and docker-compose support
- Interactive setup wizard
- Basic Telegram bot with `/status`, `/check`, `/list` commands
- Comprehensive test suite (22 tests)
- Smart anti-spam notification system
