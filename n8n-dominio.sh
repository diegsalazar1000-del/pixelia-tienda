#!/usr/bin/env bash
# Recrea el contenedor de n8n con su dirección pública https (WEBHOOK_URL) y sin exponer el puerto 5678 a internet.
# Los flujos y credenciales están en /root/.n8n y NO se tocan. Si algo falla, vuelve al contenedor anterior.
# Uso: bash n8n-dominio.sh n8n.pixeliadigital.app
H=$(printf %s "$1" | sed 's/\[20[01]~//g' | tr -d '~ ')
[ -z "$H" ] && { echo "Uso: bash n8n-dominio.sh n8n.tudominio.com"; exit 1; }

IMG=$(docker inspect n8n -f '{{.Config.Image}}') || { echo "✖ No encontré el contenedor n8n"; exit 1; }
DATA=$(docker inspect n8n -f '{{range .Mounts}}{{if eq .Destination "/home/node/.n8n"}}{{.Source}}{{end}}{{end}}')
[ -d "$DATA" ] || { echo "✖ No encontré la carpeta de datos de n8n"; exit 1; }
# Conserva las variables que ya tenía, salvo las que vamos a cambiar
EXTRA=$(docker inspect n8n -f '{{range .Config.Env}}{{println .}}{{end}}' | grep -vE '^(WEBHOOK_URL|N8N_PROXY_HOPS|N8N_EDITOR_BASE_URL|PATH|NODE_VERSION|NODE_PATH|NODE_ENV|YARN_VERSION|NPM_CONFIG_UPDATE_NOTIFIER|N8N_RELEASE_TYPE|SHELL|HOME)=' | sed '/^$/d')

echo "Copia de seguridad de los datos de n8n…"
tar -czf "/root/n8n-respaldo-$(date +%Y%m%d-%H%M).tar.gz" -C "$(dirname "$DATA")" "$(basename "$DATA")" && echo "✔ Respaldo guardado en /root"

docker rm -f n8n-anterior >/dev/null 2>&1
docker stop n8n >/dev/null && docker rename n8n n8n-anterior

ARGS=()
while IFS= read -r line; do [ -n "$line" ] && ARGS+=(-e "$line"); done <<< "$EXTRA"
docker run -d --name n8n --restart unless-stopped -p 127.0.0.1:5678:5678 \
  "${ARGS[@]}" -e "WEBHOOK_URL=https://$H/" -e "N8N_EDITOR_BASE_URL=https://$H/" -e N8N_PROXY_HOPS=1 \
  -v "$DATA":/home/node/.n8n "$IMG" >/dev/null

echo "Arrancando n8n (hasta 60 s)…"
for i in $(seq 1 12); do
  sleep 5
  if curl -s -o /dev/null -w '%{http_code}' "https://$H/healthz" | grep -q 200; then
    docker rm n8n-anterior >/dev/null
    echo; echo "✅ ¡n8n listo en https://$H !"
    echo "   Desde ahora entra siempre por esa dirección (la de :5678 ya no se usa)."
    exit 0
  fi
done

echo "✖ n8n no respondió. Vuelvo a dejarlo como estaba…"
docker rm -f n8n >/dev/null; docker rename n8n-anterior n8n; docker start n8n >/dev/null
echo "↩️  Restaurado. Mándale a Claude esto: docker logs --tail 30 n8n"
exit 1
