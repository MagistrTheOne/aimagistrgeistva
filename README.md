# AI Мага 🤖

**Голосовой ассистент с интеграциями** - лаконичный, практичный помощник с поддержкой Yandex Cloud, Telegram, HH.ru и LinkedIn.

## 🚀 Быстрый старт

### Требования
- Python 3.11+
- PostgreSQL
- Redis
- Yandex Cloud аккаунт (опционально для тестирования)

### Установка

1. **Клонировать репозиторий:**
```bash
git clone https://github.com/your-org/ai-maga.git
cd ai-maga
```

2. **Создать виртуальное окружение:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows
```

3. **Установить зависимости:**
```bash
pip install -e .[dev]
```

4. **Настроить переменные окружения:**
```bash
cp .env.example .env
# Отредактировать .env с вашими настройками
```

5. **Запустить сервисы:**
```bash
docker-compose -f docker/docker-compose.yml up -d
```

6. **Запустить приложение:**
```bash
# HTTP API
uvicorn app.api.http.app:app --host 0.0.0.0 --port 8000 --reload

# Или CLI
ai-maga chat "Привет!"
```

## 🏗️ Архитектура

```
ai-maga/
├── app/                    # Основной код
│   ├── api/               # API интерфейсы
│   │   ├── http/         # FastAPI endpoints
│   │   ├── cli/          # CLI интерфейс (Typer)
│   │   └── telegram/     # Telegram бот
│   ├── core/             # Ядро системы
│   │   ├── config.py     # Конфигурация
│   │   ├── di.py         # DI контейнер
│   │   ├── logging.py    # Структурированное логирование
│   │   ├── metrics.py    # Метрики (Prometheus)
│   │   ├── errors.py     # Обработка ошибок
│   │   └── utils/        # Утилиты
│   ├── domain/           # Доменные модели
│   │   ├── models.py     # Сущности и события
│   │   ├── commands.py   # Доменные команды
│   │   ├── policies.py   # Правила и политики
│   │   └── events.py     # Доменные события
│   ├── services/         # Бизнес-логика
│   │   ├── voice/        # Голосовой контур
│   │   ├── llm/          # LLM интеграции
│   │   ├── orchestrator.py # Оркестратор команд
│   │   └── integrations/ # Внешние интеграции
│   ├── adapters/         # Инфраструктурные адаптеры
│   │   ├── db.py         # PostgreSQL
│   │   ├── redis_client.py # Redis
│   │   ├── http_client.py # HTTP клиент
│   │   └── files.py      # Файловое хранилище
│   └── tests/            # Тесты
├── infra/                # Инфраструктура
├── docker/              # Docker конфигурации
└── docs/                # Документация
```

## ⚙️ Конфигурация

### Переменные окружения

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `APP_ENV` | Окружение | `dev` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `POSTGRES_DSN` | PostgreSQL DSN | - |
| `REDIS_URL` | Redis URL | `redis://localhost:6379/0` |
| `YC_FOLDER_ID` | Yandex Cloud folder ID | - |
| `YC_OAUTH_TOKEN` | Yandex Cloud OAuth token | - |
| `TG_BOT_TOKEN` | Telegram bot token | - |
| `TG_ALLOWED_USER_IDS` | Разрешенные Telegram user IDs | - |
| `HH_API_TOKEN` | HH.ru API token | - |
| `HOTWORD` | Ключевое слово активации | `Мага` |
| `AUDIO_INPUT_DEVICE` | Аудио устройство ввода | `default` |
| `AUDIO_OUTPUT_DEVICE` | Аудио устройство вывода | `default` |

### Полный список переменных в `.env.example`

## 🎯 API

### HTTP API (FastAPI)

#### Health Check
```http
GET /healthz
```

#### Metrics
```http
GET /metrics
```

#### Chat
```http
POST /v1/chat
Content-Type: application/json

{
  "text": "Привет, как дела?",
  "context": [],
  "session_id": "optional-session-id"
}
```

#### Voice Control
```http
POST /v1/voice/enable
POST /v1/voice/disable
```

#### Job Search (HH.ru)
```http
GET /v1/jobs/hh/search?query=python&location=Москва
```

#### OCR
```http
POST /v1/vision/ocr
Content-Type: application/json

{
  "image_data": "base64-encoded-image",
  "screenshot_region": {"x": 0, "y": 0, "width": 100, "height": 100}
}
```

#### Translation
```http
POST /v1/translate
Content-Type: application/json

{
  "text": "Hello world",
  "target_lang": "ru",
  "source_lang": "en"
}
```

### CLI

```bash
# Чат
ai-maga chat "Привет!"

# Интерактивный чат
ai-maga chat --interactive

# Тест голоса
ai-maga voice-test

# Статус системы
ai-maga status

# Конфигурация
ai-maga config

# Версия
ai-maga version
```

## 🗣️ Голосовые команды

- **"Мага, слушай"** - Включить прослушивание
- **"Мага, пауза"** - Выключить прослушивание
- **"Мага, найди вакансии Python в Москве"** - Поиск вакансий
- **"Мага, напомни о встрече завтра в 10"** - Создать напоминание
- **"Мага, переведи этот текст"** - Перевод текста
- **"Мага, прочитай это"** - Прочитать текст вслух

## 🔧 Разработка

### Запуск тестов
```bash
pytest
```

### Линтинг и типизация
```bash
ruff check .
mypy app
bandit -r app
```

### Pre-commit hooks
```bash
pre-commit install
pre-commit run --all-files
```

### Docker
```bash
# Сборка
docker build -f docker/Dockerfile -t ai-maga .

# Запуск
docker run -p 8000:8000 ai-maga
```

## 📊 Мониторинг

### Метрики (Prometheus)
- `ai_maga_requests_total` - Общее количество запросов
- `ai_maga_request_duration_seconds` - Длительность запросов
- `ai_maga_voice_commands_total` - Голосовые команды
- `ai_maga_llm_requests_total` - LLM запросы
- `ai_maga_errors_total` - Ошибки

### Логи
Структурированное логирование с уровнями INFO, ERROR, DEBUG.

## 🔒 Безопасность

- Секреты хранятся только в переменных окружения
- Rate limiting для всех API
- Валидация входных данных
- Circuit breaker для внешних сервисов
- PII фильтрация в логах

## 🤝 Интеграции

### Yandex Cloud
- **GPT** - Генерация текста
- **SpeechKit** - STT/TTS
- **Vision** - OCR
- **Translate** - Перевод текста

### Telegram
Бот для голосового и текстового общения.

### HH.ru
Поиск вакансий, подписки, дайджесты.

### LinkedIn
Официальный API при наличии токенов, операторский режим для остальных случаев.

## 🧪 Тестирование

### Unit тесты
```bash
pytest app/tests/unit/
```

### Integration тесты
```bash
pytest app/tests/integration/ -m integration
```

### Contract тесты
```bash
pytest app/tests/contracts/ -m contract
```

## 📈 CI/CD

GitHub Actions с:
- Автоматическими тестами
- Линтингом и типизацией
- Сборкой Docker образов
- Публикацией coverage

## 🎯 Acceptance Criteria (MVP)

- [x] Запуск одним `docker-compose`
- [x] Локальный голос→голос по хотворду
- [x] Telegram бот с чатом
- [x] HH поиск по запросу
- [x] OCR + Translate
- [x] Метрики, health, CI зелёный
- [x] Zero secrets in repo

## 📝 Лицензия

MIT License

## 🤝 Contributing

1. Fork репозиторий
2. Создать feature branch
3. Commit изменения
4. Push и создать PR
5. Дождаться review и merge

## 📞 Поддержка

- Issues: [GitHub Issues](https://github.com/your-org/ai-maga/issues)
- Docs: [Документация](./docs/)
- Wiki: [Wiki](https://github.com/your-org/ai-maga/wiki)
