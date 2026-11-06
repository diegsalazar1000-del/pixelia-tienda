#!/usr/bin/env bash
# Guarda claves en .env preguntándolas una por una y reinicia la tienda.
# Uso: bash configurar.sh redes | voz | probar-voz | pixabay | pexels | paypal | binance | correo | meta | radar | admin | nueva-clave | probar-admin | gemini | probar-gemini | probar-binance | probar-correo
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
  redes)
    echo "Conectar Instagram + Facebook para publicar desde el bot."
    ask META_APP_ID "Escribe el ID de la app de Meta (App ID, el número) y pulsa Enter:" 0
    ask META_APP_SECRET "Pega la clave secreta de la app (App Secret, no se verá) y pulsa Enter:" 1
    echo; echo "Pega el token del Explorador de la API Graph (no se verá) y pulsa Enter:"
    read -rs TOK; echo; TOK=$(clean "$TOK" | tr -d ' ')
    AID=$(grep '^META_APP_ID=' .env | cut -d= -f2-); ASEC=$(grep '^META_APP_SECRET=' .env | cut -d= -f2-)
    OUT=$(docker exec -e AID="$AID" -e ASEC="$ASEC" -e TOK="$TOK" pixelia node --input-type=module -e '
      const G = "https://graph.facebook.com/v23.0"; const j = async (u) => { const r = await fetch(u); const x = await r.json(); if (x.error) throw new Error(x.error.message); return x; };
      try {
        const ll = await j(`${G}/oauth/access_token?grant_type=fb_exchange_token&client_id=${process.env.AID}&client_secret=${process.env.ASEC}&fb_exchange_token=${process.env.TOK}`);
        const pages = (await j(`${G}/me/accounts?fields=id,name,access_token,instagram_business_account&access_token=${ll.access_token}`)).data || [];
        const p = pages.find((x) => /pixelia/i.test(x.name)) || pages[0];
        if (!p) throw new Error("el token no ve ninguna página (marca la página de Pixelia al generar el token)");
        let ad = ""; try { const a = (await j(`${G}/me/adaccounts?fields=account_id,name,account_status&access_token=${ll.access_token}`)).data || [];
          const x = a.find((y) => y.account_status === 1) || a[0]; if (x) ad = `act_${x.account_id}~${x.name}`; } catch {}
        console.log(`OK|${p.id}|${p.access_token}|${p.instagram_business_account?.id || ""}|${ll.access_token}|${ad.replace(/[|]/g, "-")}|${p.name}`);
      } catch (e) { console.log("ERR|" + e.message); }' 2>/dev/null)
    case "$OUT" in
      OK\|*) IFS='|' read -r _ PID PTOK IGID UTOK AD PNAME <<< "$OUT"
        set_key META_PAGE_ID "$PID"; set_key META_PAGE_TOKEN "$PTOK"; set_key META_IG_ID "$IGID"
        set_key META_USER_TOKEN "$UTOK"; set_key META_USER_TOKEN_AT "$(date +%Y-%m-%d)"
        if [ -n "$AD" ]; then set_key META_AD_ACCOUNT "${AD%%~*}"; echo "   ✔ Cuenta publicitaria: ${AD#*~}"; else echo "   ⚠️ No vi cuenta publicitaria (¿marcaste ads_management y ads_read?)"; fi
        echo "   ✔ Página: $PNAME"; [ -n "$IGID" ] && echo "   ✔ Instagram conectado" || echo "   ⚠️ La página no tiene Instagram conectado: conéctalo en Facebook y repite esto.";;
      *) echo "   ✖ No pude conectar: ${OUT#ERR|}"; exit 1;;
    esac;;
  nueva-clave)
    PW="Pixelia-$(tr -dc 'a-z0-9' </dev/urandom | head -c 8)"
    set_key ADMIN_PASSWORD "$PW"
    docker restart pixelia >/dev/null && sleep 4
    CODE=$(curl -s -o /dev/null -w '%{http_code}' -H "x-admin-key: $PW" http://127.0.0.1:3000/api/admin/summary)
    echo; echo "=============================================="
    echo "   TU CONTRASEÑA DEL PANEL ES:   $PW"
    echo "=============================================="
    [ "$CODE" = 200 ] && echo "✅ Comprobada: el servidor la acepta." || echo "✖ El servidor respondió $CODE. Mándale captura a Claude."
    echo "Cópiala (selecciónala y clic derecho) y pégala en https://pixeliadigital.app/admin"
    exit 0;;
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
  gemini)
    ask GEMINI_API_KEY "Pega la clave de Gemini AIza... (no se verá) y pulsa Enter:" 1;;
  probar-gemini)
    docker exec pixelia node --no-warnings --input-type=module -e "
      const { config } = await import('/app/src/config.js');
      const key = process.env.GEMINI_API_KEY || (await import('node:fs')).readFileSync('/app/.env','utf8').match(/^GEMINI_API_KEY=(.*)$/m)?.[1];
      if (!key) { console.log('✖ Falta GEMINI_API_KEY: ejecuta bash configurar.sh gemini'); process.exit(0); }
      const r = await fetch('https://generativelanguage.googleapis.com/v1beta/models?pageSize=200', { headers: { 'x-goog-api-key': key } });
      const j = await r.json();
      if (!r.ok) { console.log('✖ Gemini respondió: ' + (j.error?.message || r.status)); process.exit(0); }
      const names = (j.models || []).map(m => m.name.replace('models/',''));
      const pick = (re) => names.filter(n => re.test(n)).slice(0, 4).join(', ') || '—';
      console.log('✅ Clave de Gemini correcta. Modelos disponibles:');
      console.log('   Voz:     ' + pick(/tts/));
      console.log('   Imagen:  ' + pick(/image|banana/));
      console.log('   Video:   ' + pick(/omni|veo/));
      console.log('   Música:  ' + pick(/lyria/));"
    exit 0;;
  voz)
    ask ELEVENLABS_API_KEY "Pega la API key de ElevenLabs (no se verá) y pulsa Enter:" 1
    docker restart pixelia-estudio >/dev/null 2>&1 && echo "   ✔ Estudio reiniciado con la voz nueva";;
  pixabay)
    ask PIXABAY_API_KEY "Pega la API key de Pixabay (no se verá) y pulsa Enter:" 1
    docker restart pixelia-estudio >/dev/null 2>&1 && echo "   ✔ Estudio reiniciado: ya puede usar videos reales de fondo";;
  pexels)
    ask PEXELS_API_KEY "Pega la API key de Pexels (no se verá) y pulsa Enter:" 1
    docker restart pixelia-estudio >/dev/null 2>&1 && echo "   ✔ Estudio reiniciado: ya puede usar videos reales de fondo";;
  probar-voz)
    echo "Generando una frase de prueba con voz femenina y masculina… (llega a @PixeliaRadarBot)"
    docker exec pixelia-estudio python3 /pixelia/estudio/prueba_voz.py --reset
    exit 0;;
  radar)
    ask RADAR_BOT_TOKEN "Pega el token de @PixeliaRadarBot (no se verá) y pulsa Enter:" 1
    ask ANTHROPIC_API_KEY "Pega la clave de Claude sk-ant-... (no se verá) y pulsa Enter:" 1;;
  probar-binance)
    docker exec pixelia node --no-warnings --input-type=module -e "
      const { config } = await import('/app/src/config.js');
      const crypto = await import('node:crypto');
      const b = config.binance;
      console.log('Pay ID:', b.payId || '✖ falta');
      if (!b.apiKey || !b.apiSecret) { console.log('Sin API key: Binance funcionará en modo manual (confirmas con botón en Telegram).'); process.exit(0); }
      const qs = 'timestamp=' + Date.now() + '&recvWindow=10000&limit=10';
      const sig = crypto.createHmac('sha256', b.apiSecret).update(qs).digest('hex');
      const r = await fetch('https://api.binance.com/sapi/v1/pay/transactions?' + qs + '&signature=' + sig, { headers: { 'X-MBX-APIKEY': b.apiKey } });
      const j = await r.json();
      if (r.ok) console.log('✅ Conexión con Binance correcta. Movimientos de Binance Pay recientes visibles: ' + (j.data || []).length);
      else console.log('✖ Binance respondió: ' + (j.msg || JSON.stringify(j)) + '  (código ' + j.code + ')');"
    exit 0;;
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
