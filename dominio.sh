#!/usr/bin/env bash
# Conecta el dominio a la tienda y a n8n a través de Caddy (https automático).
# Uso: bash dominio.sh pixeliadigital.app
set -e
cd "$(dirname "$0")"
D=$(printf %s "$1" | sed 's/\[20[01]~//g' | tr -d '~ ' | tr 'A-Z' 'a-z')
[ -z "$D" ] && { echo "Uso: bash dominio.sh tudominio.com"; exit 1; }

CF=$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/etc/caddy/Caddyfile"}}{{.Source}}{{end}}{{end}}' caddy)
[ -f "$CF" ] || { echo "✖ No encontré el Caddyfile"; exit 1; }

IP=$(curl -s -4 --max-time 5 ifconfig.me || true)
for h in "$D" "n8n.$D"; do
  R=$(getent ahostsv4 "$h" | awk 'NR==1{print $1}')
  if [ "$R" = "$IP" ]; then echo "✔ $h apunta a este servidor"; else echo "⚠️  $h todavía no apunta a $IP (ahora: ${R:-nada}). Revisa los registros DNS en Cloudflare; puede tardar unos minutos."; fi
done

if grep -q "^$D {" "$CF"; then
  echo "(El dominio ya estaba en Caddy, no lo repito.)"
else
  cp "$CF" "$CF.respaldo.$(date +%s)"
  cat >> "$CF" <<EOF

# --- Pixelia (añadido por dominio.sh) ---
$D, www.$D {
	@www host www.$D
	redir @www https://$D{uri} permanent
	reverse_proxy localhost:3000
}

n8n.$D {
	reverse_proxy localhost:5678
}
EOF
  if ! docker exec caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null 2>&1; then
    cp "$(ls -t "$CF".respaldo.* | head -1)" "$CF"
    echo "✖ La configuración no era válida; dejé todo como estaba."; exit 1
  fi
fi
docker exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null 2>&1 && echo "✔ Caddy recargado"

# La tienda pasa a usar el dominio en enlaces de descarga, correos y Telegram
sed -i "s|^BASE_URL=.*|BASE_URL=https://$D|" .env
docker restart pixelia >/dev/null && echo "✔ Tienda reiniciada con BASE_URL=https://$D"

echo "Esperando el certificado del candado (hasta 60 s)…"
for i in $(seq 1 12); do
  sleep 5
  if curl -s -o /dev/null -w '%{http_code}' "https://$D/" | grep -q 200; then
    echo; echo "✅ ¡Listo!"; echo "   Tienda: https://$D"; echo "   Panel:  https://$D/admin"; echo "   n8n:    https://n8n.$D"; exit 0
  fi
done
echo "⏳ El candado aún no está listo. Si los DNS se acaban de crear, espera 5 minutos y prueba https://$D en el navegador."
echo "   Si sigue sin abrir, mándale a Claude: docker logs --tail 30 caddy"
