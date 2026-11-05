#!/usr/bin/env bash
# Guarda claves en .env preguntándolas una por una y reinicia la tienda.
# Uso: bash configurar.sh paypal | binance | correo | meta
cd "$(dirname "$0")"
read -r -t 1 -n 10000 _basura 2>/dev/null || true
clean() { printf %s "$1" | sed -e 's/\[20[01]~//g' -e 's/\x1b//g' | tr -d '~\r\n'; }
set_key() { # set_key NOMBRE VALOR
  local v; v=$(printf %s "$2" | sed 's/[&|]/\\&/g')
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$v|" .env; else echo "$1=$2" >> .env; fi
}
ask() { # ask NOMBRE "pregunta" secreto(1/0)
  local val
  echo; echo "$2"
  if [ "$3" = 1 ]; then read -rs val; echo; else read -r val; fi
  val=$(clean "$val"); val=$(printf %s "$val" | sed 's/^ *//;s/ *$//')
  if [ -z "$val" ]; then echo "   (vacío: no cambio nada)"; return; fi
  set_key "$1" "$val"
  if [ "$3" = 1 ]; then echo "   ✔ Guardado (${#val} caracteres, termina en …${val: -4})"; else echo "   ✔ Guardado: $val"; fi
}

case "$1" in
  paypal)
    ask PAYPAL_CLIENT_ID "Pega el Client ID de PayPal y pulsa Enter:" 0
    ask PAYPAL_CLIENT_SECRET "Pega el Secret de PayPal (no se verá) y pulsa Enter:" 1
    echo; echo "¿Son claves de PRUEBA (sandbox) o REALES (live)? Escribe sandbox o live y pulsa Enter:"
    read -r m; m=$(clean "$m" | tr 'A-Z' 'a-z' | tr -d ' ')
    [ "$m" = live ] && set_key PAYPAL_MODE live || set_key PAYPAL_MODE sandbox
    echo "   ✔ Modo: $(grep ^PAYPAL_MODE= .env | cut -d= -f2)";;
  binance)
    ask BINANCE_PAY_ID "Escribe tu Binance Pay ID (el número) y pulsa Enter:" 0
    ask BINANCE_API_KEY "Pega la API Key de Binance (solo lectura) y pulsa Enter (o Enter vacío para saltar):" 1
    ask BINANCE_API_SECRET "Pega la Secret Key de Binance (no se verá) y pulsa Enter (o Enter vacío para saltar):" 1;;
  correo)
    ask RESEND_API_KEY "Pega la API key de Resend (no se verá) y pulsa Enter:" 1
    ask EMAIL_FROM "Escribe el remitente, ej: Pixelia <hola@tudominio.com> y pulsa Enter:" 0;;
  meta)
    ask META_PIXEL_ID "Escribe el ID del píxel de Meta y pulsa Enter:" 0
    ask META_CAPI_TOKEN "Pega el token de la API de Conversiones (no se verá) y pulsa Enter:" 1;;
  *) echo "Uso: bash configurar.sh paypal | binance | correo | meta"; exit 1;;
esac

docker restart pixelia >/dev/null && sleep 3
if curl -s http://127.0.0.1:3000/api/config | grep -q store; then echo; echo "✅ Guardado y tienda reiniciada."; else echo "⚠️ La tienda no respondió. Mándale a Claude: docker logs --tail 30 pixelia"; fi
