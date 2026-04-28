#!/usr/bin/env bash
# Бэкап БД artoteka в MinIO. Запускать на VPS из cron в 3:00.
# Daily: 7 дней. Weekly (вс): 4 недели. Monthly (1-е): 3 месяца.

set -euo pipefail

COMPOSE="/opt/artoteka-crm/deploy/docker-compose.vps.yml"
DATE="$(date +%F)"
TMP="/tmp/artoteka-${DATE}.dump.gz"

cleanup() { rm -f "$TMP"; }
trap cleanup EXIT

# 1. Дамп postgres -> gzip
docker compose -f "$COMPOSE" exec -T postgres \
  pg_dump -U artoteka -F c artoteka | gzip > "$TMP"

SIZE=$(du -h "$TMP" | cut -f1)
echo "$(date -Iseconds) dump created: $SIZE"

# 2. Заливаем daily
docker cp "$TMP" deploy-minio-1:/tmp/backup.gz
docker exec deploy-minio-1 mc cp /tmp/backup.gz \
  "local/backups/daily/artoteka-${DATE}.dump.gz"

# 3. Воскресенье — копия в weekly
if [ "$(date +%u)" = "7" ]; then
  WEEK="$(date +%G-W%V)"
  docker exec deploy-minio-1 mc cp \
    "local/backups/daily/artoteka-${DATE}.dump.gz" \
    "local/backups/weekly/artoteka-${WEEK}.dump.gz"
  echo "$(date -Iseconds) weekly snapshot: ${WEEK}"
fi

# 4. 1-е число — копия в monthly
if [ "$(date +%d)" = "01" ]; then
  MONTH="$(date +%Y-%m)"
  docker exec deploy-minio-1 mc cp \
    "local/backups/daily/artoteka-${DATE}.dump.gz" \
    "local/backups/monthly/artoteka-${MONTH}.dump.gz"
  echo "$(date -Iseconds) monthly snapshot: ${MONTH}"
fi

# 5. Чистим тmp в minio
docker exec deploy-minio-1 rm -f /tmp/backup.gz

# 6. Retention
docker exec deploy-minio-1 mc rm --recursive --force --older-than "8d"   "local/backups/daily/"   >/dev/null 2>&1 || true
docker exec deploy-minio-1 mc rm --recursive --force --older-than "29d"  "local/backups/weekly/"  >/dev/null 2>&1 || true
docker exec deploy-minio-1 mc rm --recursive --force --older-than "100d" "local/backups/monthly/" >/dev/null 2>&1 || true

echo "$(date -Iseconds) backup OK -> daily/artoteka-${DATE}.dump.gz ($SIZE)"
