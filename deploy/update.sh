#!/usr/bin/env bash
# Обновление Артотеки на VPS — снимок состояния, pull, миграции, пересборка.
#
# Использование (на сервере, в /opt/artoteka-crm):
#   ./deploy/update.sh                  # обновить всё
#   ./deploy/update.sh backend          # пересобрать только backend
#   ./deploy/update.sh backend bot      # backend + bot
#
# Перед обновлением сохраняем точку отката:
#   - deploy/.last_deploy_sha     — git SHA до pull
#   - deploy/.last_alembic_rev    — текущая ревизия БД
#   - MinIO local/backups/pre-deploy/  — pg_dump перед деплоем
# Откат: ./deploy/rollback.sh
#
# ВАЖНО по порядку: backend пересобираем ДО alembic — иначе в работающем
# (ещё старом) контейнере нет файлов новых миграций. Если alembic_version
# пуста (первый прогон после ввода alembic) — делаем stamp 0001_baseline.
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE="docker compose -f deploy/docker-compose.vps.yml"
TS="$(date +%Y-%m-%d_%H-%M-%S)"

echo "==> [1/6] snapshot current state"
git rev-parse HEAD > deploy/.last_deploy_sha
SHORT_SHA="$(cut -c1-8 deploy/.last_deploy_sha)"
echo "    git SHA: $(cat deploy/.last_deploy_sha)"

# Текущая alembic-ревизия — берём напрямую из alembic_version, надёжнее парсинга stdout
CURRENT_REV="$($COMPOSE exec -T postgres psql -U artoteka -d artoteka -tAc \
  "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null | tr -d '[:space:]' || true)"
if [ -z "$CURRENT_REV" ]; then
  echo "    alembic: <empty> (БД ещё не stamp-нута — сделаем stamp 0001_baseline)"
  : > deploy/.last_alembic_rev
else
  echo "$CURRENT_REV" > deploy/.last_alembic_rev
  echo "    alembic ревизия: $CURRENT_REV"
fi

echo "==> [2/6] pre-deploy dump БД"
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

echo "==> [3/6] git pull"
git pull --ff-only

echo "==> [4/6] rebuild backend (чтобы образ содержал свежие миграции)"
$COMPOSE up -d --build backend
# Ждём, пока backend-контейнер начнёт принимать exec
for i in $(seq 1 30); do
  if $COMPOSE exec -T backend true 2>/dev/null; then
    break
  fi
  sleep 1
done

echo "==> [5/6] alembic migrations"
if [ -z "$CURRENT_REV" ]; then
  echo "    stamp 0001_baseline (первый прогон)"
  $COMPOSE exec -T backend alembic stamp 0001_baseline
fi
$COMPOSE exec -T backend alembic upgrade head

# Сборка ПОСЛЕДОВАТЕЛЬНО, по одному сервису: параллельная сборка всех разом
# давала пик памяти и OOM-kill именно на тяжёлом `next build` (frontend не обновлялся).
if [ $# -eq 0 ]; then
  SERVICES="backend bot frontend"
else
  SERVICES="$*"
fi
echo "==> [6/6] rebuild (последовательно): $SERVICES"
for svc in $SERVICES; do
  echo "    --- build $svc ---"
  $COMPOSE build "$svc"
done
$COMPOSE up -d

echo "==> ps"
$COMPOSE ps --format 'table {{.Service}}\t{{.Status}}'

echo ""
echo "✅ Готово. Точка отката: deploy/.last_deploy_sha + .last_alembic_rev"
echo "   Если что-то сломалось: ./deploy/rollback.sh"
