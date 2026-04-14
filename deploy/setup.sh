#!/bin/bash
set -e

echo "=== Артотека: первый запуск на VPS ==="

# 1. Установка Docker (если нет)
if ! command -v docker &> /dev/null; then
    echo "Устанавливаем Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# 2. Копируем .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "!!! ВАЖНО: отредактируй .env перед продолжением !!!"
    echo "    nano .env"
    exit 1
fi

# 3. Получаем SSL (первый раз без SSL, потом с ним)
echo "Получаем SSL сертификат..."
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot --webroot-path=/var/www/certbot \
    -d artoteka.ru -d api.artoteka.ru \
    --email admin@artoteka.ru --agree-tos --no-eff-email

# 4. Запускаем всё
echo "Запускаем сервисы..."
docker compose -f docker-compose.prod.yml up -d --build

# 5. Seed базы
echo "Наполняем справочники..."
docker compose -f docker-compose.prod.yml exec backend python -m app.seed

echo "=== Готово! ==="
echo "Фронт: https://artoteka.ru"
echo "API:   https://api.artoteka.ru"
echo "API docs: https://api.artoteka.ru/docs"
