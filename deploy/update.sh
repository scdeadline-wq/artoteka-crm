#!/usr/bin/env bash
# Обновление Артотеки на VPS — pull последний main, пересобрать сервис(ы).
#
# Использование (на сервере, в /opt/artoteka-crm):
#   ./deploy/update.sh                  # пересобрать всё
#   ./deploy/update.sh backend          # пересобрать только backend
#   ./deploy/update.sh backend bot      # пересобрать backend и bot
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE="docker compose -f deploy/docker-compose.vps.yml"

echo "==> git pull"
git pull --ff-only

if [ $# -eq 0 ]; then
  echo "==> rebuild all"
  $COMPOSE up -d --build
else
  echo "==> rebuild: $*"
  $COMPOSE up -d --build "$@"
fi

echo "==> ps"
$COMPOSE ps --format 'table {{.Service}}\t{{.Status}}'
