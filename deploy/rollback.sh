#!/usr/bin/env bash
# Откат последнего деплоя Артотеки.
#
# Использует точку отката, сохранённую update.sh:
#   - deploy/.last_deploy_sha     — git SHA до того деплоя
#   - deploy/.last_alembic_rev    — alembic-ревизия до того деплоя
#   - MinIO local/backups/pre-deploy/  — pg_dump на тот момент (fallback)
#
# Порядок ВАЖЕН:
#   1. alembic downgrade — используем ещё активный новый код (он знает миграцию)
#   2. git checkout — возвращаемся к старому коду
#   3. rebuild — поднимаем старые контейнеры
#
# Если downgrade сломался — восстанавливать БД из pg_dump вручную (см. конец скрипта).
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE="docker compose -f deploy/docker-compose.vps.yml"

if [ ! -f deploy/.last_deploy_sha ]; then
  echo "❌ deploy/.last_deploy_sha не найден — нечего откатывать."
  echo "   Этот файл создаётся update.sh перед каждым деплоем."
  exit 1
fi

LAST_SHA="$(cat deploy/.last_deploy_sha)"
LAST_REV="$(cat deploy/.last_alembic_rev 2>/dev/null || echo "")"
CURRENT_SHA="$(git rev-parse HEAD)"

echo "==> Текущий HEAD:  $CURRENT_SHA"
echo "==> Откатиться на: $LAST_SHA"
if [ -n "$LAST_REV" ]; then
  echo "==> alembic ревизия: -> $LAST_REV"
else
  echo "==> alembic: <не было записано — миграции не трогаю>"
fi

if [ "$LAST_SHA" = "$CURRENT_SHA" ]; then
  echo "ℹ️  HEAD уже совпадает с точкой отката. Видимо update.sh падал до git pull."
  echo "   Если нужен только rebuild — запусти update.sh ещё раз."
  exit 0
fi

read -r -p "Подтверди откат [y/N]: " ANSWER
case "$ANSWER" in
  y|Y|yes|YES) ;;
  *) echo "Отменено."; exit 0 ;;
esac

if [ -n "$LAST_REV" ]; then
  echo "==> [1/3] alembic downgrade -> $LAST_REV"
  $COMPOSE exec -T backend alembic downgrade "$LAST_REV"
else
  echo "==> [1/3] пропускаю alembic downgrade (ревизия не записана)"
fi

echo "==> [2/3] git checkout $LAST_SHA"
git checkout "$LAST_SHA"

echo "==> [3/3] rebuild"
$COMPOSE up -d --build

echo "==> ps"
$COMPOSE ps --format 'table {{.Service}}\t{{.Status}}'

echo ""
echo "✅ Откат выполнен."
echo ""
echo "Если что-то пошло не так и БД повреждена — восстанови из pre-deploy dump:"
echo "   docker exec deploy-minio-1 mc ls local/backups/pre-deploy/"
echo "   docker exec deploy-minio-1 mc cp local/backups/pre-deploy/<FILE> /tmp/restore.gz"
echo "   docker cp deploy-minio-1:/tmp/restore.gz /tmp/restore.gz"
echo "   gunzip < /tmp/restore.gz | $COMPOSE exec -T postgres pg_restore -U artoteka -d artoteka --clean --if-exists"
