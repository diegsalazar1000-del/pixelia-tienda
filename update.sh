#!/usr/bin/env bash
# Actualiza Pixelia con la última versión de GitHub y la reinicia. Uso: bash update.sh
set -e
cd "$(dirname "$0")"
git pull --ff-only
docker restart pixelia >/dev/null
sleep 3
docker ps --format '{{.Names}} {{.Status}}' | grep pixelia && echo "✅ Actualizado"
