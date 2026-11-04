#!/usr/bin/env bash
# Instalador de Pixelia en el VPS (Docker). Uso: bash setup.sh
# Pregunta el token del bot, su usuario y la clave del panel; genera los secretos y enciende la tienda.
set -e
cd "$(dirname "$0")"

# Limpia los caracteres raros que a veces añade la terminal al pegar ([200~ ... [201~)
clean() { printf %s "$1" | sed -e 's/\[20[01]~//g' -e 's/\x1b//g' | tr -d '~\r\n '; }
ip() { curl -s -4 --max-time 5 ifconfig.me || hostname -I | awk '{print $1}'; }

echo
echo "=========================================="
echo "   Instalador de Pixelia"
echo "=========================================="

if [ -f .env ]; then
  cp .env ".env.respaldo.$(date +%s)"
  echo "(Ya había configuración: guardé una copia de respaldo.)"
fi

echo
echo "1/3  Pega el TOKEN del bot de Telegram (no se verá al pegarlo) y pulsa Enter:"
read -rs TOKEN; TOKEN=$(clean "$TOKEN")
echo
echo "2/3  Escribe el USUARIO del bot, sin @ (ej: PixeliaStoreBot) y pulsa Enter:"
read -r BOTUSER; BOTUSER=$(clean "$BOTUSER"); BOTUSER=${BOTUSER#@}
echo
echo "3/3  Inventa una CONTRASEÑA para el panel /admin (no se verá) y pulsa Enter:"
read -rs ADMINPW; ADMINPW=$(clean "$ADMINPW")
echo

if ! [[ "$TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]{30,}$ ]]; then
  echo "⚠️  El token no tiene el formato esperado (números:letras). Revísalo en @BotFather y vuelve a ejecutar: bash setup.sh"
  exit 1
fi
if [ ${#ADMINPW} -lt 8 ]; then echo "⚠️  La contraseña debe tener al menos 8 caracteres. Vuelve a ejecutar: bash setup.sh"; exit 1; fi

PUBLIC_IP=$(ip)
cat > .env <<EOF
PORT=3000
BASE_URL=http://${PUBLIC_IP}:3000
STORE_NAME=Pixelia
DEFAULT_LANG=es
APP_SECRET=$(openssl rand -hex 32)
ADMIN_PASSWORD=${ADMINPW}
MAX_DOWNLOADS=5
LINK_HOURS=72

TELEGRAM_BOT_TOKEN=${TOKEN}
TELEGRAM_BOT_USERNAME=${BOTUSER}
TELEGRAM_ADMIN_CHAT_ID=

PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=

BINANCE_PAY_ID=
BINANCE_API_KEY=
BINANCE_API_SECRET=

RESEND_API_KEY=
EMAIL_FROM=

N8N_API_KEY=$(openssl rand -hex 24)

META_PIXEL_ID=
META_CAPI_TOKEN=
META_TEST_EVENT_CODE=

WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_TEMPLATE=entrega_pedido
WHATSAPP_TEMPLATE_LANG=es
EOF
chmod 600 .env
mkdir -p data storage/products

echo "Encendiendo la tienda (la primera vez tarda 1 minuto)…"
docker rm -f pixelia >/dev/null 2>&1 || true
docker run -d --name pixelia --restart always -p 3000:3000 --memory 200m \
  -v "$PWD":/app -w /app node:22-alpine node --no-warnings src/server.js >/dev/null

# Productos de ejemplo para ver la tienda funcionando (se borran luego desde /admin)
sleep 4
if [ ! -s data/tienda.db ] || [ "$(docker exec pixelia node --no-warnings -e "const {DatabaseSync}=require('node:sqlite');console.log(new DatabaseSync('data/tienda.db').prepare('select count(*) n from products').get().n)" 2>/dev/null)" = "0" ]; then
  docker exec pixelia node --no-warnings src/seed.js >/dev/null 2>&1 || true
fi

sleep 2
if docker ps --format '{{.Names}}' | grep -q '^pixelia$' && curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/ | grep -q 200; then
  echo
  echo "✅ ¡Pixelia está funcionando!"
  echo "   Tienda:  http://${PUBLIC_IP}:3000"
  echo "   Panel:   http://${PUBLIC_IP}:3000/admin"
  echo "   Bot:     https://t.me/${BOTUSER}"
  echo
else
  echo "❌ Algo falló. Mándale a Claude lo que sale con este comando:"
  echo "   docker logs --tail 30 pixelia"
fi
