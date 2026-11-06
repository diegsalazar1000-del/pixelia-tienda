#!/usr/bin/env bash
# Instala (o reinstala) el estudio de anuncios en el VPS. Uso: bash instalar-estudio.sh
set -e
cd "$(dirname "$0")"
echo "Construyendo el estudio (la primera vez tarda 3–6 minutos: descarga ffmpeg y las voces)…"
docker build -q -t pixelia-estudio estudio >/dev/null
docker rm -f pixelia-estudio >/dev/null 2>&1 || true
docker run -d --name pixelia-estudio --restart always --network host --memory 700m \
  -v "$PWD":/pixelia pixelia-estudio >/dev/null
sleep 4
# prueba de la voz
if docker exec pixelia-estudio sh -c 'echo "Hola, soy la voz de Pixelia." | python3 -m piper -m /voces/es_MX-claude-high.onnx -f /tmp/t.wav' >/dev/null 2>&1; then
  echo "✔ Voces instaladas (femenina y masculina)"; else echo "⚠️ La voz no respondió; los anuncios saldrán sin voz. Mándale a Claude: docker logs --tail 30 pixelia-estudio"; fi
if docker ps --format '{{.Names}}' | grep -q '^pixelia-estudio$'; then
  echo; echo "✅ Estudio de anuncios funcionando."
  echo "   En @PixeliaRadarBot escribe /anuncios y elige un producto."
else
  echo "❌ El estudio no arrancó. Mándale a Claude: docker logs --tail 30 pixelia-estudio"
fi
