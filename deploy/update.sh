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
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE="docker compose -f deploy/docker-compose.vps.yml"
TS="$(date +%Y-%m-%d_%H-%M-%S)"

echo "==> [1/5] snapshot current state"
git rev-parse HEAD > deploy/.last_deploy_sha
SHORT_SHA="$(cut -c1-8 deploy/.last_deploy_sha)"
echo "    git SHA: $(cat deploy/.last_deploy_sha)"

# Текущая alembic-ревизия — берём напрямую из alembic_version, надёжнее парсинга stdout
CURRENT_REV="$($COMPOSE exec -T postgres psql -U artoteka -d artoteka -tAc \
  "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null | tr -d '[:space:]' || true)"
if [ -z "$CURRENT_REV" ]; then
  echo "    alembic: <empty> (БД ещё не stamp-нута — откат миграций будет невозможен)"
  : > deploy/.last_alembic_rev
else
  echo "$CURRENT_REV" > deploy/.last_alembic_rev
  echo "    alembic ревизия: $CURRENT_REV"
fi

echo "==> [2/5] pre-deploy dump БД -> MinIO pre-deploy/"
TMP="/tmp/artoteka-pre-deploy-${TS}-${SHORT_SHA}.dump.gz"
cleanup() { rm -f "$TMP"; }
trap cleanup EXIT

$COMPOSE exec -T postgres pg_dump -U artoteka -F c artoteka | gzip > "$TMP"
SIZE=$(du -h "$TMP" | cut -f1)
echo "    dump: $SIZE -> $(basename "$TMP")"

docker cp "$TMP" deploy-minio-1:/tmp/pre-deploy.gz
docker exec deploy-minio-1 mc cp /tmp/pre-deploy.gz \
  "local/backups/pre-deploy/$(basename "$TMP")"
docker exec deploy-minio-1 rm -f /tmp/pre-deploy.gz
# Retention: pre-deploy дампы храним 7 дней
docker exec deploy-minio-1 mc rm --recursive --force --older-than "7d" \
  "local/backups/pre-deploy/" >/dev/null 2>&1 || true

echo "==> [3/5] git pull"
git pull --ff-only

echo "==> [4/5] alembic upgrade head"
$COMPOSE exec -T backend alembic upgrade head

if [ $# -eq 0 ]; then
  echo "==> [5/5] rebuild all"
  $COMPOSE up -d --build
else
  echo "==> [5/5] rebuild: $*"
  $COMPOSE up -d --build "$@"
fi

echo "==> ps"
$COMPOSE ps --format 'table {{.Service}}\t{{.Status}}'

echo ""
echo "✅ Готово. Точка отката: deploy/.last_deploy_sha + .last_alembic_rev"
echo "   Если что-то сломалось: ./deploy/rollback.sh"
