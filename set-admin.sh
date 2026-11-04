#!/usr/bin/env bash
# Guarda tu chat id de Telegram como dueño de la tienda. Uso: bash set-admin.sh
cd "$(dirname "$0")"
read -r -t 1 -n 10000 _basura 2>/dev/null || true
echo
echo "Escribe el número que te dio el bot con /id y pulsa Enter:"
read -r ID; ID=$(printf %s "$ID" | sed 's/\[20[01]~//g' | tr -cd '0-9-')
if [ -z "$ID" ]; then echo "✖ No recibí ningún número. Vuelve a ejecutar: bash set-admin.sh"; exit 1; fi
sed -i "s/^TELEGRAM_ADMIN_CHAT_ID=.*/TELEGRAM_ADMIN_CHAT_ID=${ID}/" .env
docker restart pixelia >/dev/null && sleep 3
echo "✅ Listo: el bot ya te reconoce como dueño (${ID}). Escríbele /ventas para comprobarlo."
