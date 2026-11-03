#!/usr/bin/env bash
# Включение HTTPS на VPS (одноразово; повторный запуск безопасен).
#
# Использование (на сервере, в /opt/artoteka-crm):
#   ./deploy/https-setup.sh 176-124-219-38.sslip.io          # API на api.<домен>
#   ./deploy/https-setup.sh artoteka.ru crm-api.artoteka.ru  # API на своём имени
#   ./deploy/https-setup.sh crm.x.ru crm-api.x.ru old.sslip.io  # + старые адреса,
#        они остаются в сертификате и редиректят на новый домен
#
# Что делает:
#   1. Прописывает в deploy/.env: DOMAIN, API_DOMAIN, PUBLIC_API_URL,
#      PUBLIC_BASE_URL, CORS_ORIGINS (старые значения сохраняются в .env.bak-*).
#   2. Выпускает сертификат Let's Encrypt (certbot standalone; фронт на ~30 с
#      отпускает порт 80). Если сертификат на эти имена уже есть — пропускает.
#   3. Пересобирает frontend (адрес API зашивается в сборку), перезапускает
#      backend и поднимает nginx + certbot (продление каждые 12 ч).
#
# Переход на купленный домен = запустить скрипт ещё раз с новым именем.
# Выключить HTTPS: убрать строку DOMAIN= из deploy/.env, вернуть PUBLIC_API_URL
# и CORS_ORIGINS из .env.bak-*, затем ./deploy/update.sh
set -euo pipefail

cd "$(dirname "$0")/.."

DOMAIN="${1:?Укажи домен: ./deploy/https-setup.sh <домен> [api-домен]}"
API_DOMAIN="${2:-api.$DOMAIN}"
shift $(( $# < 2 ? $# : 2 ))
LEGACY="$*"   # старые домены через пробел (могут быть пустыми)
ENV_FILE=deploy/.env
CERT_NAME=artoteka
CERT_DIR=deploy/certbot/conf

# --- проверки ----------------------------------------------------------------
[ -f "$ENV_FILE" ] || { echo "❌ нет $ENV_FILE"; exit 1; }

COMPOSE_VER="$(docker compose version --short 2>/dev/null | sed 's/^v//')"
if [ "$(printf '%s\n2.24.0\n' "$COMPOSE_VER" | sort -V | head -1)" != "2.24.0" ]; then
  echo "❌ Docker Compose $COMPOSE_VER, нужен >= 2.24 (тег !reset в docker-compose.https.yml)."
  echo "   Обнови: apt-get install -y docker-compose-plugin"
  exit 1
fi

SERVER_IP="$(curl -s4 --max-time 10 https://ifconfig.me || true)"
for name in "$DOMAIN" "$API_DOMAIN" $LEGACY; do
  resolved="$(getent ahostsv4 "$name" | awk 'NR==1{print $1}')"
  if [ -z "$resolved" ]; then
    echo "❌ $name не резолвится. Проверь A-запись."; exit 1
  fi
  if [ -n "$SERVER_IP" ] && [ "$resolved" != "$SERVER_IP" ]; then
    echo "❌ $name -> $resolved, а IP сервера $SERVER_IP. Проверь A-запись."; exit 1
  fi
  echo "    $name -> $resolved ✓"
done

# --- [1/4] .env ----------------------------------------------------------------
echo "==> [1/4] прописываю домены в $ENV_FILE"
cp "$ENV_FILE" "$ENV_FILE.bak-$(date +%Y-%m-%d_%H-%M-%S)"

set_env() {
  local key="$1" val="$2" tmp
  tmp="$(mktemp)"
  awk -v k="$key" -v v="$val" '
    BEGIN { done = 0 }
    $0 ~ "^" k "=" { if (!done) { print k "=" v; done = 1 }; next }
    { print }
    END { if (!done) print k "=" v }
  ' "$ENV_FILE" > "$tmp"
  cat "$tmp" > "$ENV_FILE"   # cat, а не mv: сохраняем права файла
  rm -f "$tmp"
}

set_env DOMAIN "$DOMAIN"
set_env API_DOMAIN "$API_DOMAIN"
set_env LEGACY_DOMAINS "$LEGACY"
set_env PUBLIC_API_URL "https://$API_DOMAIN"
set_env PUBLIC_BASE_URL "https://$API_DOMAIN"
set_env CORS_ORIGINS "https://$DOMAIN,http://localhost:3000"

COMPOSE="docker compose -f deploy/docker-compose.vps.yml -f deploy/docker-compose.https.yml"

# --- [2/4] сертификат ----------------------------------------------------------
echo "==> [2/4] сертификат Let's Encrypt"
mkdir -p "$CERT_DIR" deploy/certbot/www

cert_covers() {
  local pem="$CERT_DIR/live/$CERT_NAME/fullchain.pem"
  [ -f "$pem" ] || return 1
  local sans
  sans="$(openssl x509 -in "$pem" -noout -ext subjectAltName 2>/dev/null || true)"
  sans="$(tr -d ' \n' <<<"$sans"),"   # "DNS:a,DNS:b," — чтобы сравнивать целиком
  local n
  for n in "$DOMAIN" "$API_DOMAIN" $LEGACY; do
    grep -qF "DNS:$n," <<<"$sans" || return 1
  done
}

if cert_covers; then
  echo "    сертификат на $DOMAIN и $API_DOMAIN уже есть, пропускаю"
else
  # Порт 80 держит либо фронт (до HTTPS), либо nginx (смена домена) — отпускаем оба
  docker compose -f deploy/docker-compose.vps.yml -f deploy/docker-compose.https.yml \
    stop nginx frontend 2>/dev/null || true
  restore_port80() {
    echo "    поднимаю обратно то, что было на порту 80"
    docker compose -f deploy/docker-compose.vps.yml up -d frontend || true
  }
  trap restore_port80 ERR

  docker run --rm -p 80:80 \
    -v "$PWD/$CERT_DIR:/etc/letsencrypt" \
    certbot/certbot:v2.11.0 certonly --standalone \
      --non-interactive --agree-tos --register-unsafely-without-email \
      --cert-name "$CERT_NAME" \
      -d "$DOMAIN" -d "$API_DOMAIN" $(for n in $LEGACY; do printf -- "-d %s " "$n"; done)

  trap - ERR
  echo "    сертификат выпущен ✓"
fi

# --- [3/4] сборка фронта с новым адресом API ------------------------------------
echo "==> [3/4] пересборка frontend (NEXT_PUBLIC_API_URL=https://$API_DOMAIN)"
$COMPOSE build frontend

# --- [4/4] запуск ---------------------------------------------------------------
echo "==> [4/4] поднимаю backend, frontend, nginx, certbot"
$COMPOSE up -d --force-recreate backend frontend nginx certbot
$COMPOSE ps --format 'table {{.Service}}\t{{.Status}}'

echo "==> проверка"
sleep 5
for url in "https://$DOMAIN/" "https://$API_DOMAIN/health"; do
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$url" || true)"
  echo "    $url -> $code"
done

echo ""
echo "✅ HTTPS включён: https://$DOMAIN (API https://$API_DOMAIN)"
echo "   Дальше update.sh сам подключает docker-compose.https.yml, пока в .env есть DOMAIN."
