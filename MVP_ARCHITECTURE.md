# Артотека — Архитектура MVP

## Стек технологий

### Backend
- **Python 3.13 + FastAPI** — быстрый API, async, автодокументация OpenAPI
- **PostgreSQL 16** — основная БД (JSONB для гибких полей, полнотекстовый поиск на русском)
- **SQLAlchemy 2 + Alembic** — ORM + миграции
- **Redis** — кеш, очередь задач, сессии
- **Celery** — фоновые задачи (уведомления, рассылки)
- **MinIO / S3** — хранение фото произведений

### Frontend
- **Next.js 15 (App Router)** — SSR, быстрый UI
- **TypeScript**
- **Tailwind CSS + shadcn/ui** — готовые компоненты, быстрая вёрстка
- **TanStack Query** — управление серверным состоянием

### Telegram
- **aiogram 3** — async Telegram-бот на Python

### Инфраструктура
- **Docker + Docker Compose** — локальная разработка и деплой
- **Nginx** — reverse proxy, раздача статики
- **Caddy** (альтернатива) — авто-SSL

---

## Схема базы данных (MVP)

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│    artists       │     │    artworks       │     │    images        │
├─────────────────┤     ├──────────────────┤     ├─────────────────┤
│ id               │◄───┤ artist_id (FK)    │───►│ artwork_id (FK)  │
│ name_ru          │     │ id                │     │ url              │
│ name_en          │     │ inventory_number  │     │ is_primary       │
│ is_group         │     │ title             │     │ sort_order       │
│ bio              │     │ year              │     └─────────────────┘
└─────────────────┘     │ edition           │
                        │ description       │
                        │ condition         │
                        │ has_expertise     │
                        │ status            │◄── enum: draft/review/
                        │ location          │     for_sale/reserved/
                        │ purchase_price    │     collection/sold
                        │ sale_price        │
                        │ notes             │
                        │ created_at        │
                        └──────┬───────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
┌─────────────────────┐   ┌──────────────────┐    ┌─────────────────┐
│ artwork_techniques   │   │     sales         │    │   clients        │
├─────────────────────┤   ├──────────────────┤    ├─────────────────┤
│ artwork_id (FK)      │   │ id                │    │ id               │
│ technique_id (FK)    │   │ artwork_id (FK)   │    │ name             │
└─────────────────────┘   │ client_id (FK)    │◄───┤ phone            │
                          │ referral_id (FK)  │    │ email            │
┌─────────────────┐      │ sold_price        │    │ telegram         │
│  techniques      │      │ referral_fee      │    │ type             │◄── buyer/dealer/
├─────────────────┤      │ sold_at           │    │                  │    referral
│ id               │      │ notes             │    │ preferences      │◄── JSONB
│ name             │      └──────────────────┘    │ description      │
│ category         │                               │ created_at       │
└─────────────────┘                               └─────────────────┘
                                                          │
                                                  ┌───────┴────────┐
                                                  │ client_artists  │
                                                  ├────────────────┤
                                                  │ client_id (FK)  │
                                                  │ artist_id (FK)  │◄── "любит Русецкого"
                                                  └────────────────┘

┌─────────────────┐
│     users        │  ◄── пользователи системы (Паруер, Андрей)
├─────────────────┤
│ id               │
│ name             │
│ role             │  ◄── owner / manager / viewer
│ telegram_id      │
│ password_hash    │
└─────────────────┘
```

---

## Приоритеты (фазы MVP)

### Фаза 1 — Ядро (2-3 недели)
> Паруер может работать вместо Excel/головы

1. **Карточка произведения** — CRUD, фото, все поля из совещания
2. **Справочник художников** — кириллица + латиница, группы
3. **Справочник техник** — предзаполненный, мультиселект
4. **Инвентарный номер** — автоинкремент, печать этикетки (QR)
5. **Статусы** — draft → review → for_sale → reserved → sold / collection
6. **Поиск и фильтры** — по художнику, технике, статусу, цене
7. **Авторизация** — JWT, роли (owner / manager)

### Фаза 2 — CRM (2 недели)
> Клиенты, продажи, рефералы

8. **Карточка клиента** — контакты, тип, предпочтения по художникам
9. **Продажи** — привязка работа → клиент → реферал, маржа
10. **Рефералы** — кто привёл, реферальный %, эффективность
11. **Дашборд** — доходы/расходы, маржинальность, топ художников

### Фаза 3 — Автоматизация (1-2 недели)
> Telegram-бот, уведомления

12. **Telegram-бот** (для Паруера) — быстрое добавление работ, статусы
13. **Автоуведомления** — новый Русецкий → уведомить подписчиков
14. **Workflow входящих** — загрузка фото → статус «На рассмотрении» → одобрение

### Фаза 4 — AI и масштабирование (после MVP)
> Не в MVP, но архитектура должна это поддержать

- AI-автозаполнение техники по фото
- AI-бот для клиентов (подбор по запросу)
- Закрытый Telegram-канал для дилеров
- Обмен базами между галереями
- MCP-доступ для AI-агентов
- Маркетплейс-надстройка

---

## Структура проекта

```
ArtSpace-CRM/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── artist.py
│   │   │   ├── artwork.py
│   │   │   ├── client.py
│   │   │   ├── sale.py
│   │   │   ├── technique.py
│   │   │   └── user.py
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── api/                 # Роуты
│   │   │   ├── artworks.py
│   │   │   ├── artists.py
│   │   │   ├── clients.py
│   │   │   ├── sales.py
│   │   │   ├── dashboard.py
│   │   │   └── auth.py
│   │   ├── services/            # Бизнес-логика
│   │   └── tasks/               # Celery tasks (уведомления)
│   ├── alembic/                 # Миграции
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router
│   │   │   ├── (dashboard)/     # Дашборд layout
│   │   │   ├── artworks/        # Произведения
│   │   │   ├── artists/         # Художники
│   │   │   ├── clients/         # Клиенты
│   │   │   ├── sales/           # Продажи
│   │   │   └── login/
│   │   ├── components/          # UI компоненты
│   │   └── lib/                 # API клиент, утилиты
│   ├── package.json
│   └── Dockerfile
├── bot/
│   ├── bot.py                   # Telegram-бот (aiogram 3)
│   ├── handlers/
│   └── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── MEETING_SUMMARY.md
└── MVP_ARCHITECTURE.md
```

---

## Необходимое ПО для разработки

### На машине (уже есть / нужно поставить)
```bash
# Проверить / установить
brew install python@3.13      # скорее всего есть
brew install node              # для фронта
brew install postgresql@16     # или через Docker
brew install redis             # или через Docker
brew install docker            # Docker Desktop
```

### Python-пакеты (backend/requirements.txt)
```
fastapi>=0.115
uvicorn[standard]>=0.34
sqlalchemy>=2.0
alembic>=1.15
asyncpg                       # async PostgreSQL драйвер
pydantic>=2.0
pydantic-settings
python-jose[cryptography]     # JWT
passlib[bcrypt]               # пароли
python-multipart              # загрузка файлов
pillow                        # обработка изображений
boto3                         # S3/MinIO
celery[redis]                 # фоновые задачи
redis                         # кеш
```

### Node-пакеты (frontend/package.json)
```
next
react
typescript
tailwindcss
@tanstack/react-query
axios
zustand                       # стейт-менеджмент
next-auth                     # авторизация
lucide-react                  # иконки
```

### Telegram-бот (bot/requirements.txt)
```
aiogram>=3.0
aiohttp
```

---

## Серверы (продакшен)

| Параметр | Россия (основной) | Зарубежный (бэкап) |
|----------|-------------------|---------------------|
| Провайдер | Selectel / Timeweb Cloud | Hetzner (Финляндия) |
| CPU | 4 vCPU | 2 vCPU |
| RAM | 8 GB | 4 GB |
| SSD | 80 GB + Object Storage для фото | 40 GB |
| Стоимость | ~3000-5000 ₽/мес | ~€10-15/мес |
| Роль | API + БД + фронт | Replica БД + бэкап фото |

**Итого: ~$50-80/мес** (сильно дешевле $3000, которые обсуждали)

Бэкап: PostgreSQL streaming replication + ежедневный pg_dump в Object Storage.

---

## API-эндпоинты (MVP, Фаза 1-2)

```
POST   /auth/login
POST   /auth/refresh

GET    /artworks                  # список + фильтры + поиск
POST   /artworks                  # создать
GET    /artworks/{id}             # карточка
PUT    /artworks/{id}             # редактировать
PATCH  /artworks/{id}/status      # сменить статус
POST   /artworks/{id}/images      # загрузить фото
DELETE /artworks/{id}/images/{id} # удалить фото

GET    /artists
POST   /artists
GET    /artists/{id}
PUT    /artists/{id}

GET    /techniques                # справочник

GET    /clients
POST   /clients
GET    /clients/{id}
PUT    /clients/{id}
GET    /clients/{id}/history      # история покупок

POST   /sales                     # оформить продажу
GET    /sales                     # список продаж

GET    /dashboard/summary         # доходы, расходы, маржа
GET    /dashboard/top-artists     # топ продаваемых
GET    /dashboard/referrals       # эффективность рефералов
```

---

## С чего начать прямо сейчас

```bash
# 1. Инициализировать проект
cd /Users/aleksnuts/Desktop/ArtSpace-CRM
git init

# 2. Docker Compose с PostgreSQL + Redis
# 3. Backend: FastAPI + модели + первые эндпоинты (artworks CRUD)
# 4. Frontend: Next.js + страница каталога
# 5. Наполнить справочник техник
```

Готов начать с п.1?
