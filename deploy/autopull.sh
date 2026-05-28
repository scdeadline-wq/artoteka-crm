#!/usr/bin/env bash
# Авто-деплой по cron: если origin/main ушёл вперёд — подтянуть и задеплоить.
#
# Ставится в cron (раз в N минут), напр.:
#   */2 * * * * /opt/artoteka-crm/deploy/autopull.sh
#
# Никакого входящего SSH не нужно — сервер сам опрашивает GitHub по исходящему HTTPS.
# flock защищает от наложения, если деплой идёт дольше интервала cron.
set -euo pipefail

LOG=/var/log/artoteka-autopull.log
REPO=/opt/artoteka-crm

# Единственный экземпляр за раз
exec 9>/tmp/artoteka-autopull.lock
if ! flock -n 9; then
  exit 0
fi

cd "$REPO"

git fetch origin main --quiet
LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse origin/main)"

if [ "$LOCAL" = "$REMOTE" ]; then
  exit 0  # нечего деплоить
fi

echo "=== $(date '+%F %T') deploy ${LOCAL:0:8} -> ${REMOTE:0:8} ===" >> "$LOG"
if ./deploy/update.sh >> "$LOG" 2>&1; then
  echo "=== $(date '+%F %T') OK ===" >> "$LOG"
else
  echo "=== $(date '+%F %T') FAILED (см. выше) ===" >> "$LOG"
fi
