#!/usr/bin/env bash
# Обновление Артотеки на VPS — снимок состояния, pull, миграции, пересборка.
#
# Использование (на сервере, в /opt/artoteka-crm):
#   ./deploy/update.sh                  # обновить всё
#   ./deploy/update.sh backend          # пересобрать только backend
#   ./deploy/update.sh backend bot      # backend + bot
#
# Точка отката:
#   - deploy/.last_deploy_sha     — git SHA до pull
#   - deploy/.last_alembic_rev    — ревизия БД до миграций
#   - MinIO local/backups/pre-deploy/  — pg_dump перед деплоем
# Значения снимаются ДО git pull (т.е. «код и ревизия, которые работали»),
# но в файлы пишутся только ПОСЛЕ успешного pull — иначе упавший pull
# затирал бы валидную точку отката. Откат: ./deploy/rollback.sh
#
# ВАЖНО по порядку: backend пересобираем ДО alembic — иначе в работающем
# (ещё старом) контейнере нет файлов новых миграций. Если alembic_version
# пуста (первый прогон после ввода alembic) — делаем stamp 0001_baseline.
#
# Уведомления в Telegram: при падении любого шага (trap ERR) и при успехе.
# Токен/получатель — TELEGRAM_BOT_TOKEN + первый id из ADMIN_TELEGRAM_IDS
# (читаются из deploy/.env). Сбой уведомления НЕ роняет деплой.
set -Eeuo pipefail

cd "$(dirname "$0")/.."

COMPOSE="docker compose -f deploy/docker-compose.vps.yml"
TS="$(date +%Y-%m-%d_%H-%M-%S)"

# --- Telegram-уведомления ----------------------------------------------------
TG_TOKEN="$(grep -m1 '^TELEGRAM_BOT_TOKEN=' deploy/.env 2>/dev/null | cut -d= -f2- | tr -d '"\r' || true)"
TG_CHAT="$(grep -m1 '^ADMIN_TELEGRAM_IDS=' deploy/.env 2>/dev/null | cut -d= -f2- | cut -d, -f1 | tr -d '"\r ' || true)"

notify() {
  [ -n "$TG_TOKEN" ] && [ -n "$TG_CHAT" ] || return 0
  curl -s --max-time 20 "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
    -d chat_id="$TG_CHAT" --data-urlencode "text=$1" >/dev/null 2>&1 || true
}

STEP="инициализация"
on_error() {
  local sha
  sha="$(git rev-parse --short HEAD 2>/dev/null || echo '?')"
  echo "❌ Деплой упал на шаге: $STEP (sha $sha)" >&2
  notify "❌ Деплой Артотеки упал на шаге «$STEP», sha $sha"
}
trap on_error ERR

# --- [1/8] снимок состояния (только в переменные, файлы — после pull) --------
STEP="snapshot"
echo "==> [1/8] snapshot current state"
OLD_SHA="$(git rev-parse HEAD)"
SHORT_SHA="${OLD_SHA:0:8}"
echo "    git SHA: $OLD_SHA"

# Текущая alembic-ревизия — берём напрямую из alembic_version, надёжнее парсинга stdout
CURRENT_REV="$($COMPOSE exec -T postgres psql -U artoteka -d artoteka -tAc \
  "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null | tr -d '[:space:]' || true)"
if [ -z "$CURRENT_REV" ]; then
  echo "    alembic: <empty> (БД ещё не stamp-нута — сделаем stamp 0001_baseline)"
else
  echo "    alembic ревизия: $CURRENT_REV"
fi

# --- [2/8] pre-deploy dump ----------------------------------------------------
STEP="pre-deploy dump БД"
echo "==> [2/8] pre-deploy dump БД"
mkdir -p deploy/backups
DUMP="deploy/backups/pre-deploy-${TS}-${SHORT_SHA}.dump.gz"
$COMPOSE exec -T postgres pg_dump -U artoteka -F c artoteka | gzip > "$DUMP"
echo "    локальный дамп: $(du -h "$DUMP" | cut -f1) -> $DUMP"
# Retention: держим последние 7 локальных дампов
ls -1t deploy/backups/pre-deploy-*.dump.gz 2>/dev/null | tail -n +8 | xargs -r rm -f

# Дубль в MinIO — НЕ критично: при неудаче (нет прав/бакета) продолжаем,
# локальный дамп уже снят и является основной точкой восстановления.
if docker cp "$DUMP" deploy-minio-1:/tmp/pre-deploy.gz 2>/dev/null \
   && docker exec deploy-minio-1 mc cp /tmp/pre-deploy.gz \
        "local/backups/pre-deploy/$(basename "$DUMP")" 2>/dev/null; then
  docker exec deploy-minio-1 rm -f /tmp/pre-deploy.gz 2>/dev/null || true
  docker exec deploy-minio-1 mc rm --recursive --force --older-than "7d" \
    "local/backups/pre-deploy/" >/dev/null 2>&1 || true
  echo "    + залит в MinIO ✓"
else
  echo "    ⚠️  MinIO-загрузка не удалась — оставляю только локальный дамп в deploy/backups/"
fi

# --- [3/8] git pull -----------------------------------------------------------
STEP="git pull"
echo "==> [3/8] git pull"
git pull --ff-only

# --- [4/8] запись точки отката: pull прошёл, миграции ещё не катились ---------
STEP="запись точки отката"
echo "==> [4/8] записываю точку отката (значения, снятые до pull)"
echo "$OLD_SHA" > deploy/.last_deploy_sha
if [ -n "$CURRENT_REV" ]; then
  echo "$CURRENT_REV" > deploy/.last_alembic_rev
else
  : > deploy/.last_alembic_rev
fi

# --- [5/8] rebuild backend ----------------------------------------------------
STEP="rebuild backend"
echo "==> [5/8] rebuild backend (чтобы образ содержал свежие миграции)"
$COMPOSE up -d --build backend
# Ждём, пока backend-контейнер начнёт принимать exec
for i in $(seq 1 30); do
  if $COMPOSE exec -T backend true 2>/dev/null; then
    break
  fi
  sleep 1
done

# --- [6/8] alembic ------------------------------------------------------------
STEP="alembic migrations"
echo "==> [6/8] alembic migrations"
if [ -z "$CURRENT_REV" ]; then
  echo "    stamp 0001_baseline (первый прогон)"
  $COMPOSE exec -T backend alembic stamp 0001_baseline
fi
$COMPOSE exec -T backend alembic upgrade head

# --- [7/8] rebuild остальных --------------------------------------------------
# Сборка ПОСЛЕДОВАТЕЛЬНО, по одному сервису: параллельная сборка всех разом
# давала пик памяти и OOM-kill именно на тяжёлом `next build` (frontend не обновлялся).
if [ $# -eq 0 ]; then
  SERVICES="backend bot frontend"
else
  SERVICES="$*"
fi
STEP="rebuild ($SERVICES)"
echo "==> [7/8] rebuild (последовательно): $SERVICES"
for svc in $SERVICES; do
  echo "    --- build $svc ---"
  $COMPOSE build "$svc"
done
$COMPOSE up -d

echo "==> ps"
$COMPOSE ps --format 'table {{.Service}}\t{{.Status}}'

# --- [8/8] smoke-check --------------------------------------------------------
STEP="smoke-check /health"
echo "==> [8/8] smoke-check http://localhost:8000/health"
HEALTH_OK=0
for i in $(seq 1 5); do
  if curl -sf --max-time 5 http://localhost:8000/health >/dev/null 2>&1; then
    HEALTH_OK=1
    break
  fi
  echo "    попытка $i/5 не удалась, жду 3с..."
  sleep 3
done
if [ "$HEALTH_OK" -ne 1 ]; then
  echo "❌ backend не отвечает на /health после 5 попыток" >&2
  false  # триггерит ERR-trap (уведомление в Telegram), set -e завершает скрипт
fi
echo "    /health отвечает ✓"

# Чистка неиспользуемых образов: диск всего 29GB, dangling-слои копятся с каждого пуша
echo "==> docker image prune"
docker image prune -f || true

NEW_SHA="$(git rev-parse --short HEAD)"
notify "✅ Деплой Артотеки: sha $NEW_SHA"

echo ""
echo "✅ Готово. Точка отката: deploy/.last_deploy_sha + .last_alembic_rev"
echo "   Если что-то сломалось: ./deploy/rollback.sh"
