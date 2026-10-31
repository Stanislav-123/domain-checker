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
- `/list` - список всех отслеживаемых доменов
- `/help` - справка по командам

### Типы уведомлений

1. **🔴 Домен недоступен** - после N последовательных падений
2. **✅ Домен восстановлен** - когда домен снова доступен
3. **⚠️ SSL истекает** - предупреждение за N дней до истечения

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

- Проверьте токен бота и Chat ID
- Убедитесь что бот запущен: `docker-compose logs -f`
- Проверьте доступ к Telegram API

### Домены не проверяются

- Проверьте логи: `docker-compose logs domain-checker`
- Убедитесь в правильности API ключа трекера
- Проверьте доступность API трекера

### Ошибки SSL

- Проверьте что сервер имеет доступ к портам 443
- Убедитесь что firewall не блокирует исходящие соединения

### База данных

- БД создается автоматически в `data/domain_checker.db`
- При проблемах удалите БД - она пересоздастся

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
- `/list` - List all monitored domains

### Adding New Trackers

1. Create `domain_checker/sources/yourtracker.py`
2. Implement `DomainSource` interface
3. Add to factory in `scheduler.py`
4. Write tests

### Testing

```bash
pip install -r requirements-dev.txt
pytest
```

### License

MIT License

---

**Made with ❤️ for media buyers**
