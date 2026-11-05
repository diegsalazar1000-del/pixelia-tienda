#!/usr/bin/env bash
# Guarda claves en .env preguntándolas una por una y reinicia la tienda.
# Uso: bash configurar.sh paypal | binance | correo | meta | radar | admin | probar-admin | probar-correo
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
  admin)
    echo; echo "Escribe la NUEVA contraseña del panel /admin (mín. 8, sin espacios) y pulsa Enter."
    echo "(Esta vez SÍ se verá mientras la escribes, para que no te equivoques. Apúntala.)"
    read -r PW; PW=$(clean "$PW" | tr -d ' ')
    if [ ${#PW} -lt 8 ]; then echo "✖ Muy corta (${#PW}). Vuelve a ejecutar: bash configurar.sh admin"; exit 1; fi
    set_key ADMIN_PASSWORD "$PW"; echo "   ✔ Contraseña cambiada (${#PW} caracteres)";;
  probar-admin)
    echo; echo "Escribe la contraseña del panel tal como la pondrías en la web y pulsa Enter (se verá):"
    read -r PW; PW=$(clean "$PW")
    ENC=$(node -e 'process.stdout.write(encodeURIComponent(process.argv[1]))' "$PW" 2>/dev/null || docker exec pixelia node -e 'process.stdout.write(encodeURIComponent(process.argv[1]))' "$PW")
    CODE=$(curl -s -o /dev/null -w '%{http_code}' -H "x-admin-key: $ENC" http://127.0.0.1:3000/api/admin/summary)
    SAVED=$(grep '^ADMIN_PASSWORD=' .env | cut -d= -f2-)
    echo "   Guardada en el servidor: ${#SAVED} caracteres · la que escribiste: ${#PW} caracteres"
    if [ "$CODE" = 200 ]; then echo "✅ La contraseña es correcta en el servidor. Si la web dice 'incorrecta', el navegador está rellenando otra: bórrala y escríbela a mano."
    else echo "✖ No coincide (código $CODE). Cámbiala con: bash configurar.sh admin"; fi
    exit 0;;
  radar)
    ask RADAR_BOT_TOKEN "Pega el token de @PixeliaRadarBot (no se verá) y pulsa Enter:" 1
    ask ANTHROPIC_API_KEY "Pega la clave de Claude sk-ant-... (no se verá) y pulsa Enter:" 1;;
  probar-correo)
    echo; echo "Escribe tu correo personal para enviarte un correo de prueba y pulsa Enter:"
    read -r TO; TO=$(clean "$TO" | tr -d ' ')
    docker exec pixelia node --no-warnings --input-type=module -e "
      const { sendEmail } = await import('/app/src/delivery/email.js');
      try { await sendEmail('$TO', '✅ Prueba de Pixelia', 'Si lees esto, los correos de la tienda funcionan.',
        '<div style=\"font-family:sans-serif;padding:24px\"><h2>✅ ¡Funciona!</h2><p>Los correos de <b>Pixelia</b> ya salen solos.</p></div>');
        console.log('✅ Enviado a $TO. Revisa tu bandeja (y la carpeta de spam).'); }
      catch (e) { console.log('✖ Error: ' + e.message); }"
    exit 0;;
  *) echo "Uso: bash configurar.sh paypal | binance | correo | meta"; exit 1;;
esac

docker restart pixelia >/dev/null && sleep 3
if curl -s http://127.0.0.1:3000/api/config | grep -q store; then echo; echo "✅ Guardado y tienda reiniciada."; else echo "⚠️ La tienda no respondió. Mándale a Claude: docker logs --tail 30 pixelia"; fi
