# Развертывание AI Мага на Railway

## 🚀 Пошаговое развертывание

### Шаг 1: Подготовка проекта
```bash
# Убедитесь, что у вас есть все файлы:
# - railway.json
# - docker/Dockerfile
# - docker/docker-compose.yml (для локальной разработки)
# - main.py (точка входа)
# - .env.example (шаблон переменных)
```

### Шаг 2: Регистрация на Railway
1. Перейдите на https://railway.app
2. Зарегистрируйтесь через GitHub/GitLab
3. Подтвердите email

### Шаг 3: Установка Railway CLI (опционально)
```bash
# Для удобства можно установить CLI
npm install -g @railway/cli
railway login
```

### Шаг 4: Создание проекта
**Вариант A: Через веб-интерфейс**
1. Нажмите "New Project"
2. Выберите "Deploy from GitHub"
3. Подключите ваш репозиторий с AI Магой

**Вариант B: Через CLI**
```bash
railway init
# Следуйте инструкциям
```

### Шаг 5: Настройка переменных окружения

В Railway Dashboard → Variables добавьте следующие переменные:

#### 🔑 ОБЯЗАТЕЛЬНЫЕ ПЕРЕМЕННЫЕ:

```
# === YANDEX CLOUD ===
YC_FOLDER_ID=ВАШ_YANDEX_FOLDER_ID
YC_OAUTH_TOKEN=ВАШ_YANDEX_OAUTH_TOKEN

# === TELEGRAM BOT ===
TG_BOT_TOKEN=ВАШ_ТЕЛЕГРАМ_ТОКЕН
```

#### 🟡 ВАЖНЫЕ (желательно настроить):

```
# === HH.RU API (если планируете использовать) ===
HH_API_TOKEN=ваш_hh_token

# === LINKEDIN (если планируете использовать) ===
LINKEDIN_CLIENT_ID=ваш_linkedin_client_id
LINKEDIN_CLIENT_SECRET=ваш_linkedin_secret
LINKEDIN_ACCESS_TOKEN=ваш_linkedin_token
```

#### 🟢 СТАНДАРТНЫЕ (можно оставить по умолчанию):

```
# === ОСНОВНЫЕ ===
APP_ENV=production
LOG_LEVEL=INFO

# === YANDEX GPT ===
YANDEX_GPT_MODEL=yandexgpt/latest

# === VOICE/АУДИО ===
VOICE_PIPELINE_TIMEOUT=30
VOICE_PIPELINE_BUFFER_SIZE=4096
VOICE_PIPELINE_SAMPLE_RATE=16000

# === LLM НАСТРОЙКИ ===
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.7
LLM_TIMEOUT=60

# === HTTP КЛИЕНТ ===
HTTP_TIMEOUT=30
HTTP_MAX_RETRIES=3
HTTP_BACKOFF_FACTOR=2.0

# === RATE LIMITING ===
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST_SIZE=10

# === METRICS ===
METRICS_PORT=9090

# === NLU ===
NLP_CONFIDENCE_THRESHOLD=0.5

# === ORCHESTRATOR ===
ORCH_MAX_STEPS=6
ORCH_TIME_BUDGET_MS=800

# === OCR ===
OCR_MAX_IMAGE_MB=5
OCR_RATE_PER_MIN=30

# === TRANSLATION ===
TRANSLATE_DEFAULT_LANG=en

# === HH.RU ===
HH_BASE_URL=https://api.hh.ru
HH_DEFAULT_AREA=1

# === SCHEDULER ===
SCHED_MAX_RETRIES=5
SCHED_JITTER_MS=250
```

### Шаг 6: Настройка базы данных и Redis

Railway автоматически предоставляет:
- **PostgreSQL** базу данных
- **Redis** для кэширования

Эти сервисы будут автоматически подключены через переменные окружения:
- `DATABASE_URL` для PostgreSQL
- Redis URL будет предоставлен автоматически

### Шаг 7: Развертывание

**Через веб-интерфейс:**
1. Railway автоматически обнаружит `railway.json`
2. Начнется сборка Docker образа
3. Приложение развернется автоматически

**Через CLI:**
```bash
railway up
```

### Шаг 8: Проверка развертывания

После развертывания проверьте:

```bash
# Получить URL приложения
railway domain

# Проверить логи
railway logs

# Проверить переменные
railway variables
```

### Шаг 9: Тестирование API

```bash
# Health check
curl https://your-app-url.railway.app/healthz

# Chat API
curl -X POST https://your-app-url.railway.app/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "Привет!", "session_id": "test"}'
```

## 🔧 Устранение проблем

### Проблема: Приложение не запускается
```bash
railway logs --tail 50
# Проверьте логи на ошибки
```

### Проблема: Переменные окружения не работают
```bash
railway variables list
# Убедитесь, что все переменные установлены
```

### Проблема: База данных не подключается
Railway автоматически предоставляет `DATABASE_URL`. Убедитесь, что в коде используется правильная переменная.

### Проблема: Yandex GPT не работает
Проверьте:
- Правильность `YC_FOLDER_ID`
- Валидность `YC_OAUTH_TOKEN`
- Правильность `YANDEX_GPT_MODEL`

## 💰 Цены Railway

| План | RAM | Диск | Цена |
|------|-----|------|------|
| **Starter** | 512MB | 1GB | $0 (бесплатно) |
| **Hobby** | 512MB | 1GB | $5/месяц |
| **Pro** | 4GB | 32GB | $10/месяц |
| **Teams** | 8GB+ | 128GB+ | От $20/месяц |

**Рекомендация:** Начните с Hobby плана ($5/месяц)

## 📊 Мониторинг

Railway предоставляет:
- Логи приложений
- Метрики использования
- Мониторинг uptime
- Автоматические бэкапы БД

## 🔄 Обновление приложения

```bash
# При пуше в main ветку Railway автоматически переразвернет
git add .
git commit -m "Update AI Maga"
git push origin main
```

## 🎯 Production готовность

Приложение готово к production с:
- ✅ Docker контейнеризацией
- ✅ Автоматическим масштабированием
- ✅ Переменными окружения
- ✅ Логированием и метриками
- ✅ Базой данных и Redis