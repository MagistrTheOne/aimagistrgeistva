# AI Мага

Голосовой ассистент с интеграциями для различных платформ.

## Особенности

- Голосовое взаимодействие через Yandex SpeechKit
- Интеграция с Telegram
- Поиск вакансий на HH.ru
- Перевод текста через Yandex Translate
- Распознавание текста через Yandex Vision OCR
- LLM через Yandex GPT

## Установка

### Требования

- Python 3.11+
- PostgreSQL
- Redis

### Установка зависимостей

```bash
pip install -e .
```

### Настройка переменных окружения

Скопируйте `.env.example` в `.env` и заполните необходимые значения:

```bash
cp .env.example .env
```

## Запуск

### В Docker

```bash
cd docker
docker-compose up -d
```

### Локально

```bash
# Запуск API сервера
uvicorn app.api.http.app:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

- `GET /healthz` - Проверка здоровья
- `GET /metrics` - Prometheus метрики
- `POST /v1/chat` - Чат с AI
- `POST /v1/intent/detect` - Распознавание намерений
- `POST /v1/orchestrate` - Оркестрация действий

## Разработка

### Запуск тестов

```bash
pytest
```

### Линтинг

```bash
ruff check .
mypy app
```

## Лицензия

MIT