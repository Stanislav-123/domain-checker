# Domain Checker 🌐

**Open-source сервис мониторинга доменов для арбитражников (media buyers)**

Автоматически проверяет доступность доменов из трекера (Keitaro, Binom или кастомный API), отслеживает их состояние и отправляет уведомления в Telegram при недоступности или проблемах с SSL.

---

## 🚀 Возможности

- ✅ **Интеграция с трекерами**: Keitaro, Binom, Custom API
- 🔄 **Периодические проверки**: настраиваемый интервал (от 5 минут)
- 🔍 **Комплексные проверки**:
  - DNS резолв
  - HTTP/HTTPS доступность
  - Валидность SSL сертификата
  - Предупреждения об истечении SSL
- 📱 **Telegram уведомления**: умная система алертов без спама
- 🤖 **Telegram бот**: команды `/status`, `/check`, `/list`
- 💾 **История проверок**: SQLite база данных
- 🐳 **Docker готов**: полная поддержка контейнеризации
- ⚙️ **Интерактивная настройка**: setup wizard для первого запуска

---

## 📋 Требования

- Python 3.10+
- Telegram бот (создается через @BotFather)
- Доступ к API трекера (Keitaro/Binom) или собственный API с доменами

---

## 🛠 Установка

### Вариант 1: Локальная установка

```bash
# Клонировать репозиторий
git clone https://github.com/Stanislav-123/domain-checker.git
cd domain-checker

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Запустить мастер настройки
python -m domain_checker setup

# Запустить сервис
python -m domain_checker
```

### Вариант 2: Docker

```bash
# Клонировать репозиторий
git clone https://github.com/Stanislav-123/domain-checker.git
cd domain-checker

# Скопировать пример конфигурации
cp .env.example .env

# Отредактировать .env файл
nano .env  # или любой другой редактор

# Запустить через docker-compose
docker-compose up -d

# Просмотр логов
docker-compose logs -f
```

---

## ⚙️ Конфигурация

### Интерактивная настройка (рекомендуется)

```bash
python -m domain_checker setup
```

Мастер настройки проведет вас через все шаги:
1. Выбор типа трекера (Keitaro/Binom/Custom)
2. URL трекера и API ключ
3. Telegram Bot Token и Chat ID
4. Интервал проверок
5. Настройки алертов

### Ручная настройка

Создайте файл `config.yaml`:

```yaml
tracker:
  type: keitaro  # keitaro, binom или custom
  url: https://your-tracker.com
  api_key: your-api-key-here
  
  # Только для custom трекера
  custom:
    header_name: Authorization
    domains_path: domains

telegram:
  bot_token: your-bot-token
  chat_id: your-chat-id

checker:
  interval_minutes: 15
  consecutive_failures_threshold: 2
  ssl_warning_days: 7
  max_concurrent_checks: 10
  request_timeout_seconds: 10

database:
  path: data/domain_checker.db
```

### Переменные окружения (для Docker)

Все параметры можно задать через `.env` файл:

```env
TRACKER_TYPE=keitaro
TRACKER_URL=https://your-tracker.com
TRACKER_API_KEY=your-api-key

TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=123456789

CHECK_INTERVAL_MINUTES=15
CONSECUTIVE_FAILURES_THRESHOLD=2
SSL_WARNING_DAYS=7
```

---

## 🚀 Production развёртывание

### Docker Production Setup (рекомендуется)

```bash
# 1. Клонировать и настроить
git clone https://github.com/Stanislav-123/domain-checker.git
cd domain-checker
cp .env.example .env
nano .env  # заполнить все переменные

# 2. Создать необходимые директории
mkdir -p data logs

# 3. Установить правильные права
chmod 600 .env
chown -R 1000:1000 data logs

# 4. Запустить
docker-compose up -d

# 5. Проверить логи
docker-compose logs -f domain-checker

# 6. Проверить статус
docker-compose ps
```

#### Docker healthcheck

Контейнер автоматически проверяет работоспособность каждые 60 секунд:

```bash
# Проверить статус
docker inspect --format='{{.State.Health.Status}}' domain-checker

# Посмотреть историю health checks
docker inspect domain-checker | jq '.[0].State.Health'
```

### Systemd Service (без Docker)

Создайте файл `/etc/systemd/system/domain-checker.service`:

```ini
[Unit]
Description=Domain Checker Service
After=network.target

[Service]
Type=simple
User=domain-checker
Group=domain-checker
WorkingDirectory=/opt/domain-checker
Environment="PATH=/opt/domain-checker/venv/bin"
ExecStart=/opt/domain-checker/venv/bin/python -m domain_checker
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Безопасность
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/domain-checker/data /opt/domain-checker/logs

[Install]
WantedBy=multi-user.target
```

Настройка и запуск:

```bash
# Создать пользователя
sudo useradd -r -s /bin/false domain-checker

# Установить сервис
sudo mkdir -p /opt/domain-checker
sudo chown domain-checker:domain-checker /opt/domain-checker
cd /opt/domain-checker

# Установить Python окружение
python3 -m venv venv
source venv/bin/activate
git clone https://github.com/Stanislav-123/domain-checker.git .
pip install -r requirements.txt

# Настроить конфигурацию
cp .env.example .env
nano .env  # заполнить переменные
chmod 600 .env

# Создать директории
mkdir -p data logs
chown domain-checker:domain-checker data logs

# Активировать сервис
sudo systemctl daemon-reload
sudo systemctl enable domain-checker
sudo systemctl start domain-checker

# Проверить статус
sudo systemctl status domain-checker
sudo journalctl -u domain-checker -f
```

### Настройка логирования

#### Переменные окружения

```bash
# Уровень логирования
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Файл логов (опционально)
LOG_FILE=/app/logs/domain_checker.log

# Ротация логов
LOG_ROTATION_ENABLED=true  # 10MB per file, 5 backups
```

#### Логи в production

Все логи структурированы (JSON в не-TTY окружении):

```json
{
  "event": "check_cycle_completed",
  "up_count": 45,
  "down_count": 2,
  "total": 47,
  "timestamp": "2024-12-20T10:30:00.123Z",
  "level": "info"
}
```

**Важно:** API ключи и токены автоматически скрываются в логах (показываются только первые и последние 4 символа).

### Мониторинг

#### Проверка работоспособности

```bash
# Docker
docker-compose ps
docker-compose logs --tail=50 domain-checker

# Systemd
systemctl status domain-checker
journalctl -u domain-checker -n 50

# Проверка базы данных
sqlite3 data/domain_checker.db "SELECT COUNT(*) FROM domain_state;"
```

#### Метрики для мониторинга

1. **Healthcheck контейнера** - должен быть `healthy`
2. **Логи ошибок** - `grep ERROR logs/domain_checker.log`
3. **Размер БД** - `du -h data/domain_checker.db`
4. **Последняя проверка** - проверить timestamp в логах

### Резервное копирование

```bash
# Backup базы данных
cp data/domain_checker.db data/domain_checker.db.backup.$(date +%Y%m%d_%H%M%S)

# Автоматический backup через cron (каждый день в 3:00)
0 3 * * * cd /opt/domain-checker && cp data/domain_checker.db data/backups/db.$(date +\%Y\%m\%d).db

# Восстановление
cp data/backups/db.20241220.db data/domain_checker.db
# Перезапустить сервис
```

### Обновление версии

```bash
# Docker
cd /path/to/domain-checker
git pull
docker-compose build
docker-compose down
docker-compose up -d

# Systemd
sudo systemctl stop domain-checker
cd /opt/domain-checker
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl start domain-checker
```

### Безопасность в production

1. **Файлы конфигурации** - автоматически устанавливаются права 600
2. **Секреты** - всегда используйте переменные окружения, никогда не коммитьте `.env` или `config.yaml`
3. **Docker** - контейнер работает от непривилегированного пользователя (UID 1000)
4. **Логи** - API ключи автоматически редактируются в логах
5. **Сеть** - используйте изолированную Docker сеть или firewall правила

### Масштабирование

Для мониторинга большого количества доменов (1000+):

```yaml
# config.yaml или environment variables
checker:
  max_concurrent_checks: 50  # увеличить параллельные проверки
  request_timeout_seconds: 5  # уменьшить таймаут
  interval_minutes: 10        # уменьшить интервал проверок
```

**Рекомендации по ресурсам:**

- До 100 доменов: 512MB RAM, 1 CPU
- 100-500 доменов: 1GB RAM, 2 CPU
- 500-1000 доменов: 2GB RAM, 2 CPU
- 1000+ доменов: 4GB RAM, 4 CPU

---

## 🔌 Интеграции с трекерами

### Keitaro

Использует Keitaro Admin API:
- **Эндпоинт**: `/admin_api/v1/domains`
- **Документация**: https://admin-api.docs.keitaro.io/
- **Заголовок**: `Api-Key: YOUR_KEY`

Получить API ключ:
1. Войти в админку Keitaro
2. Настройки → API
3. Создать новый ключ

### Binom

Binom v2 передаёт ключ в заголовке `api-key` (см. https://docs.binom.org/api-v2.php).
Точный путь списка доменов зависит от сборки трекера, поэтому чекер по очереди пробует:
1. `GET /public/api/v1/domain/list/all` (заголовок `api-key`)
2. `GET /api/v2/domain` (заголовок `api-key`)
3. legacy v1: `GET /api.php?page=Domains&api_key=KEY`

Если ни один не подошёл — сверьте путь в Swagger вашего трекера (`https://your-tracker.com/api/doc`)
и при необходимости используйте тип `custom` с нужным URL и заголовком `api-key`.

Получить API ключ: Settings → User → API key.

### Что считается «домен упал»

- DNS не резолвится, таймаут или ошибка соединения;
- HTTP 5xx или 4xx (кроме 401/403/429 — это «сайт жив, но закрыт/антибот/лимит»);
- SSL-сертификат просрочен, самоподписан или выписан на другой домен.

Алерт приходит после N неудач подряд (`consecutive_failures_threshold`), повторно не спамит,
при восстановлении приходит сообщение «Домен восстановлен». Предупреждение об истекающем SSL — не чаще раза в сутки.
Если API трекера недоступно — одно уведомление и одно при восстановлении.

Переменная `TELEGRAM_API_URL` позволяет указать свой (self-hosted) Bot API сервер.

### Custom API

Гибкая настройка для любого API:

**Поддерживаемые форматы ответа:**

1. JSON список:
```json
["domain1.com", "domain2.com"]
```

2. JSON объект:
```json
{
  "domains": ["domain1.com", "domain2.com"]
}
```

3. Вложенный JSON:
```json
{
  "data": {
    "domains": ["domain1.com", "domain2.com"]
  }
}
```

4. Plain text (построчно):
```
domain1.com
domain2.com
```

**Настройки:**
- `header_name`: имя заголовка для API ключа (по умолчанию `Authorization`)
- `domains_path`: путь к доменам в JSON (например: `domains` или `data.domains`)

---

## 🤖 Telegram бот

### Команды

- `/start` - приветствие и список команд
- `/status` - общая сводка по всем доменам
- `/check <домен>` - проверить конкретный домен прямо сейчас
- `/list` - список всех отслеживаемых активных доменов
- `/pause` - приостановить автоматические проверки
- `/resume` - возобновить автоматические проверки
- `/interval <минуты>` - изменить интервал проверок (например: `/interval 30`)
- `/help` - справка по командам

### Типы уведомлений

1. **🔴 Домен недоступен** - после N последовательных падений (индивидуально или батч-отчёт при массовых проблемах)
2. **✅ Домен восстановлен** - когда домен снова доступен
3. **⚠️ SSL истекает** - предупреждение за N дней до истечения
4. **⚠️ Трекер недоступен** - когда API трекера не отвечает
5. **✅ Трекер восстановлен** - когда API трекера снова работает

### Настройка Telegram

1. Создать бота через @BotFather
2. Получить Chat ID через @userinfobot
3. Указать токен и Chat ID в конфигурации
4. Отправить тестовое сообщение при setup

---

## 🏗 Архитектура

```
domain_checker/
├── sources/           # Интеграции с трекерами
│   ├── base.py       # Базовый интерфейс
│   ├── keitaro.py    # Keitaro источник
│   ├── binom.py      # Binom источник
│   └── custom.py     # Custom API источник
├── checker.py        # Логика проверок доменов
├── storage.py        # SQLite хранилище
├── notifier.py       # Telegram уведомления
├── bot.py            # Telegram бот
├── scheduler.py      # Координатор проверок
├── config.py         # Управление конфигурацией
├── setup.py          # Мастер настройки
└── main.py           # Точка входа
```

### Логика работы

1. **Scheduler** периодически запускает проверки по расписанию
2. **Source** получает список доменов из трекера
3. **Checker** асинхронно проверяет все домены (DNS, HTTP, SSL)
4. **Storage** сохраняет результаты и отслеживает состояние
5. **Notifier** отправляет алерты в Telegram по правилам:
   - Алерт только после N последовательных падений
   - Сообщение о восстановлении
   - Предупреждения об SSL
6. **Bot** обрабатывает команды пользователя

### Анти-спам система

- Уведомление отправляется только после `consecutive_failures_threshold` падений подряд (по умолчанию 2)
- После отправки алерта повторные не отправляются до восстановления
- Восстановление сбрасывает счетчик падений
- SSL предупреждения отправляются один раз

---

## 🧪 Тестирование

```bash
# Установить dev зависимости
pip install -r requirements-dev.txt

# Запустить все тесты
pytest

# С покрытием кода
pytest --cov=domain_checker --cov-report=html

# Только определенный файл
pytest tests/test_sources.py

# Verbose режим
pytest -v
```

Тесты покрывают:
- ✅ Парсинг ответов от всех типов трекеров
- ✅ Различные форматы данных (JSON, text)
- ✅ Логику алертов и состояний
- ✅ Хранилище и историю проверок

---

## 📦 Добавление нового трекера

1. Создать файл `domain_checker/sources/yourtracker.py`:

```python
from typing import List
from .base import DomainSource
import httpx


class YourTrackerSource(DomainSource):
    def __init__(self, base_url: str, api_key: str, timeout: int = 10):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout

    async def fetch_domains(self) -> List[str]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/your-endpoint",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            data = response.json()
            # Парсинг ответа
            return [domain for domain in data["domains"]]
```

2. Добавить в `domain_checker/sources/__init__.py`:

```python
from .yourtracker import YourTrackerSource

__all__ = [..., "YourTrackerSource"]
```

3. Добавить в `scheduler.py` метод `_create_source`:

```python
elif tracker_type == 'yourtracker':
    return YourTrackerSource(url, api_key, timeout)
```

4. Написать тесты в `tests/test_sources.py`

---

## 🐛 Troubleshooting

### Бот не отвечает

**Симптомы:** Команды в Telegram не работают

**Решения:**
1. Проверьте токен бота: `echo $TELEGRAM_BOT_TOKEN`
2. Проверьте Chat ID: убедитесь что ID правильный (получить через @userinfobot)
3. Проверьте логи бота:
   ```bash
   # Docker
   docker-compose logs -f domain-checker | grep -i telegram
   
   # Systemd
   journalctl -u domain-checker -f | grep -i telegram
   ```
4. Проверьте доступ к Telegram API:
   ```bash
   curl https://api.telegram.org/bot<TOKEN>/getMe
   ```
5. Если используете self-hosted Bot API, проверьте `TELEGRAM_API_URL`

### Домены не проверяются

**Симптомы:** Нет новых записей в БД, нет алертов

**Решения:**
1. Проверьте статус мониторинга через `/status` в боте (может быть на паузе)
2. Проверьте логи на ошибки трекера:
   ```bash
   docker-compose logs domain-checker | grep -i "tracker_fetch_failed"
   ```
3. Проверьте API ключ трекера:
   ```bash
   # Для Keitaro
   curl -H "Api-Key: $TRACKER_API_KEY" "$TRACKER_URL/admin_api/v1/domains"
   
   # Для Binom
   curl -H "api-key: $TRACKER_API_KEY" "$TRACKER_URL/public/api/v1/domain/list/all"
   ```
4. Проверьте интервал проверок: `/interval` в боте

### Контейнер unhealthy

**Симптомы:** `docker ps` показывает статус `unhealthy`

**Решения:**
1. Проверьте логи healthcheck:
   ```bash
   docker inspect domain-checker | jq '.[0].State.Health'
   ```
2. Проверьте доступ к БД:
   ```bash
   docker-compose exec domain-checker sqlite3 /app/data/domain_checker.db "SELECT 1"
   ```
3. Проверьте права на файлы:
   ```bash
   ls -la data/
   # Должен быть владелец 1000:1000
   ```

### Высокая загрузка CPU/памяти

**Симптомы:** Контейнер использует много ресурсов

**Решения:**
1. Уменьшите параллельные проверки:
   ```bash
   MAX_CONCURRENT_CHECKS=5
   ```
2. Увеличьте интервал проверок:
   ```bash
   CHECK_INTERVAL_MINUTES=30
   ```
3. Проверьте количество доменов:
   ```bash
   sqlite3 data/domain_checker.db "SELECT COUNT(*) FROM domain_state WHERE is_active=1"
   ```

### Ошибки SSL проверки

**Симптомы:** Все домены показывают ошибки SSL

**Решения:**
1. Проверьте что сервер имеет доступ к портам 443
2. Проверьте firewall:
   ```bash
   # Test SSL connectivity
   openssl s_client -connect example.com:443 -servername example.com
   ```
3. Если за прокси, убедитесь что SSL не перехватывается

### База данных заблокирована

**Симптомы:** `database is locked` в логах

**Решения:**
1. Проверьте что запущен только один экземпляр сервиса
2. Проверьте наличие `.db-wal` и `.db-shm` файлов - они должны быть доступны для записи
3. Перезапустите сервис:
   ```bash
   docker-compose restart domain-checker
   ```

### Telegram rate limiting

**Симптомы:** Сообщения не отправляются, в логах `rate limit`

**Решения:**
- Бот автоматически обрабатывает rate limits (ожидает и повторяет)
- При массовых проблемах отправляется один батч-отчёт вместо множества индивидуальных алертов
- Проверьте что не запущено несколько экземпляров бота с одним токеном

### Логи слишком большие

**Решения:**
1. Убедитесь что включена ротация:
   ```bash
   LOG_ROTATION_ENABLED=true
   ```
2. Уменьшите уровень логирования:
   ```bash
   LOG_LEVEL=WARNING  # вместо INFO или DEBUG
   ```
3. Настройте logrotate (systemd):
   ```bash
   # /etc/logrotate.d/domain-checker
   /opt/domain-checker/logs/*.log {
       daily
       rotate 7
       compress
       delaycompress
       missingok
       notifempty
   }
   ```

### Миграция между версиями

**При обновлении с 1.0.0 на 1.1.0:**

База данных автоматически мигрирует при первом запуске. Если возникают проблемы:

```bash
# Backup старой БД
cp data/domain_checker.db data/domain_checker.db.v1.0.0

# Добавить новые поля вручную (если автомиграция не сработала)
sqlite3 data/domain_checker.db << EOF
ALTER TABLE domain_state ADD COLUMN is_active BOOLEAN DEFAULT 1;
ALTER TABLE domain_state ADD COLUMN last_seen TEXT NOT NULL DEFAULT '';
UPDATE domain_state SET last_seen = updated_at;
EOF
```

### Получить детальную диагностику

```bash
# Docker
docker-compose logs domain-checker --tail=100 > diagnostic.log
docker inspect domain-checker >> diagnostic.log
docker stats domain-checker --no-stream >> diagnostic.log
sqlite3 data/domain_checker.db ".schema" >> diagnostic.log

# Systemd
journalctl -u domain-checker -n 200 > diagnostic.log
systemctl status domain-checker >> diagnostic.log
```

---

## 🔒 Безопасность

- ✅ Никогда не коммитьте `config.yaml` или `.env` с реальными ключами
- ✅ Используйте `.gitignore` (уже настроен)
- ✅ В Docker секреты передавайте через environment variables
- ✅ API ключи хранятся только локально
- ✅ Telegram бот ограничен одним Chat ID

---

## 📄 Лицензия

MIT License - смотрите [LICENSE](LICENSE) для деталей.

---

## 🤝 Вклад в проект

Вклады приветствуются! Пожалуйста:

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменений (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

---

## 🌟 Roadmap

- [ ] Web UI для просмотра статуса
- [ ] Графики истории проверок
- [ ] Поддержка Slack уведомлений
- [ ] Webhook уведомления
- [ ] Мультиязычность уведомлений
- [ ] Prometheus метрики
- [ ] Health check endpoint

---

## 💬 Поддержка

- 🐛 **Issues**: [GitHub Issues](https://github.com/Stanislav-123/domain-checker/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/Stanislav-123/domain-checker/discussions)

---

# English Section

## Domain Checker 🌐

Open-source domain monitoring service for media buyers and traffic arbitrage.

### Features

- Multi-tracker support (Keitaro, Binom, Custom API)
- Periodic health checks (DNS, HTTP, SSL)
- Smart Telegram alerts without spam
- Interactive setup wizard
- Docker support
- SQLite storage with history
- Telegram bot with commands

### Quick Start

```bash
# Clone
git clone https://github.com/Stanislav-123/domain-checker.git
cd domain-checker

# Install
pip install -r requirements.txt

# Setup
python -m domain_checker setup

# Run
python -m domain_checker
```

### Docker

```bash
# Copy environment file
cp .env.example .env

# Edit configuration
nano .env

# Start
docker-compose up -d
```

### Configuration

Edit `config.yaml` or use environment variables:

- `TRACKER_TYPE`: keitaro, binom, or custom
- `TRACKER_URL`: Your tracker URL
- `TRACKER_API_KEY`: API key
- `TELEGRAM_BOT_TOKEN`: Bot token from @BotFather
- `TELEGRAM_CHAT_ID`: Your chat ID
- `CHECK_INTERVAL_MINUTES`: Check frequency

### Telegram Bot Commands

- `/status` - Get domains summary
- `/check <domain>` - Check specific domain
- `/list` - List all monitored active domains
- `/pause` - Pause automatic checks
- `/resume` - Resume automatic checks
- `/interval <minutes>` - Change check interval (e.g. `/interval 30`)
- `/help` - Get help

### Adding New Trackers

1. Create `domain_checker/sources/yourtracker.py`
2. Implement `DomainSource` interface
3. Add to factory in `scheduler.py`
4. Write tests

### Production Deployment

**Docker (Recommended):**

```bash
git clone https://github.com/Stanislav-123/domain-checker.git
cd domain-checker
cp .env.example .env
# Edit .env with your settings
nano .env

# Set permissions
chmod 600 .env
mkdir -p data logs
chown -R 1000:1000 data logs

# Start
docker-compose up -d

# Check logs
docker-compose logs -f
```

**Systemd Service:**

```bash
# Create user
sudo useradd -r -s /bin/false domain-checker

# Install
sudo mkdir -p /opt/domain-checker
cd /opt/domain-checker
python3 -m venv venv
source venv/bin/activate
git clone . && pip install -r requirements.txt

# Configure
cp .env.example .env && nano .env
chmod 600 .env

# Create systemd service (see full example in Russian section)
sudo systemctl enable domain-checker
sudo systemctl start domain-checker
```

**Environment Variables:**

- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR (default: INFO)
- `LOG_FILE` - Path to log file (optional)
- `LOG_ROTATION_ENABLED` - Enable log rotation (default: true)

### Monitoring & Operations

**Health Check:**
```bash
# Docker
docker inspect --format='{{.State.Health.Status}}' domain-checker

# Check logs for errors
docker-compose logs domain-checker | grep ERROR
```

**Backup:**
```bash
cp data/domain_checker.db data/backups/db.$(date +%Y%m%d).db
```

**Update:**
```bash
git pull
docker-compose build && docker-compose up -d
```

### Testing

```bash
pip install -r requirements-dev.txt
pytest
pytest --cov=domain_checker --cov-report=html
```

All 30 tests pass (22 original + 8 new command tests)

### What's New in v1.1.0

- **Structured logging** with automatic secret sanitization
- **Retry logic** with exponential backoff for tracker APIs
- **Message batching** to prevent Telegram rate limiting
- **Domain lifecycle** management (active/inactive tracking)
- **New bot commands**: `/pause`, `/resume`, `/interval`
- **Enhanced Docker**: non-root user, healthcheck, volumes
- **Security improvements**: file permissions, env var support
- **GitHub Actions CI**: automated linting and testing

See [CHANGELOG.md](CHANGELOG.md) for full details.

### License

MIT License

---

**Made with ❤️ for media buyers**
