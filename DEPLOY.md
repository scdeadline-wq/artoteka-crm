# Артотека — Деплой и инфраструктура

## VPS

| Параметр | Значение |
|----------|----------|
| Провайдер | (из скриншота — вероятно Timeweb/Selectel) |
| IP | 185.152.94.51 |
| IPv6 | 2a03:6f00:a::1:e3da |
| ОС | Ubuntu 24.04.3 LTS |
| CPU | 1 vCPU (x86_64) |
| RAM | 1.9 GB |
| Диск | 29 GB SSD (19 GB свободно) |
| SSH | `ssh root@185.152.94.51` |
| Закрытые порты | 587, 2525, 389, 465, 53413, 25, 3389 |

## Доступы

### CRM (Артотека)
- **Фронт:** http://185.152.94.51
- **API:** http://185.152.94.51:8000
- **Swagger (API docs):** http://185.152.94.51:8000/docs
- **Логин:** `paruer@artoteka.ru` / `artoteka2026`

### MinIO (хранилище фото)
- Консоль: http://185.152.94.51:9001 (только изнутри Docker-сети)
- Credentials: см. `/opt/artoteka-crm/deploy/.env` на сервере

### Другие сервисы на VPS
- **n8n** — уже был развёрнут до нас, занимает ~94 MB RAM

## Структура на сервере

```
/opt/artoteka-crm/
├── backend/          # FastAPI приложение
├── frontend/         # Next.js приложение
├── deploy/
│   ├── .env                    # Продакшн-переменные (НЕ в git)
│   ├── docker-compose.vps.yml  # Оптимизированный под 2GB RAM
│   ├── docker-compose.prod.yml # Полный (с nginx + SSL, для будущего)
│   ├── nginx.conf              # Конфиг nginx (для будущего SSL)
│   └── setup.sh                # Скрипт первого запуска
├── docker-compose.yml          # Для локальной разработки
└── ...
```

## Docker-контейнеры

| Контейнер | Image | Порт | RAM (лимит) | RAM (факт) |
|-----------|-------|------|-------------|------------|
| deploy-backend-1 | deploy-backend | 8000 | 300 MB | ~74 MB |
| deploy-frontend-1 | deploy-frontend | 80 → 3000 | 256 MB | ~34 MB |
| deploy-postgres-1 | postgres:16-alpine | internal | 400 MB | ~58 MB |
| deploy-redis-1 | redis:7-alpine | internal | 96 MB | ~4 MB |
| deploy-minio-1 | minio/minio | internal | 256 MB | ~116 MB |
| **Итого Артотека** | | | **1308 MB** | **~285 MB** |

## Оптимизации под 2GB RAM

- PostgreSQL: `shared_buffers=128MB`, `work_mem=4MB`, `max_connections=50`
- Redis: `maxmemory 64mb`, политика `allkeys-lru`
- Uvicorn: 1 воркер (не 2-4)
- Next.js: standalone-сборка (~34 MB vs ~150 MB обычная)
- Все контейнеры с `deploy.resources.limits.memory`

## Обновление

Используем единый скрипт `deploy/update.sh` — он делает `git pull` и пересобирает указанные сервисы (или все, если без аргументов).

```bash
# На VPS, из /opt/artoteka-crm:
./deploy/update.sh                  # подтянуть main и пересобрать всё
./deploy/update.sh backend          # только backend
./deploy/update.sh backend bot      # backend + bot
```

С локалки одной командой:
```bash
ssh root@185.152.94.51 "cd /opt/artoteka-crm && ./deploy/update.sh backend"
```

## Сетевая особенность: IPv6 отключён

На VPS IPv6 принудительно отключён через `/etc/sysctl.d/99-disable-ipv6.conf`,
потому что DNS `api.telegram.org` отдаёт AAAA первым, а IPv6-маршрут до Telegram
с этого VPS не работает (Python/httpx уходил в TimedOut). После отключения IPv6
весь трафик идёт через IPv4, который к Telegram доступен напрямую.

Если IPv6 нужно вернуть — удалить `/etc/sysctl.d/99-disable-ipv6.conf` и
`sysctl --system`.

## Бэкап базы

```bash
# Ручной бэкап:
docker compose -f docker-compose.vps.yml exec postgres pg_dump -U artoteka artoteka > backup_$(date +%Y%m%d).sql

# Восстановление:
cat backup_YYYYMMDD.sql | docker compose -f docker-compose.vps.yml exec -T postgres psql -U artoteka artoteka
```

## Логи

```bash
cd /opt/artoteka-crm/deploy
docker compose -f docker-compose.vps.yml logs -f backend    # логи API
docker compose -f docker-compose.vps.yml logs -f frontend   # логи фронта
docker compose -f docker-compose.vps.yml logs -f postgres   # логи БД
```

## TODO: когда будет домен

1. Привязать домен `artoteka.ru` → A-запись на 185.152.94.51
2. Переключиться на `docker-compose.prod.yml` (с nginx + certbot)
3. Обновить `PUBLIC_API_URL` в `.env` на `https://api.artoteka.ru`
4. Пересобрать frontend

## OpenRouter API — справка

### Image Generation (мокапы)
Используем стандартный chat completions endpoint с обязательным параметром `modalities`:

```bash
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-5-image",
    "modalities": ["image", "text"],   # <-- ОБЯЗАТЕЛЬНО для генерации изображений
    "messages": [{"role": "user", "content": "Generate..."}]
  }'
```

Ответ: `choices[0].message.images[0].image_url.url` — base64 data URI.

### Модели генерации изображений (по стоимости)
| Модель | Цена | Качество |
|--------|------|----------|
| `google/gemini-2.5-flash-image` | ~бесплатно | хорошее |
| `openai/gpt-5-image-mini` | ~$0.003 | хорошее |
| `openai/gpt-5-image` | ~$0.01 | топ |
| `black-forest-labs/flux.2-pro` | ~$0.03 | топ |

### Vision/анализ (карточки произведений)
Модель: `google/gemini-2.0-flash-001` — дешёвый, быстрый, хорошо определяет технику/стиль.

### Доступные модели с image output
```bash
curl "https://openrouter.ai/api/v1/models?output_modalities=image"
```

## Рекомендации по апгрейду

- **При 1000+ произведений с фото:** апгрейд до 4 GB RAM, вынести фото в Object Storage
- **При подключении Telegram-бота:** +1 контейнер (~50 MB)
- **При подключении AI:** нужен внешний API (OpenRouter/Anthropic), RAM на сервере не вырастет
