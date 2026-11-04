#!/usr/bin/env bash
# Diagnóstico de Apify: comprueba el token y si puede usar los lectores del radar. Uso: bash diag-apify.sh
read -r -t 1 -n 10000 _basura 2>/dev/null || true
echo
echo "Pega el token de Apify (no se verá) y pulsa Enter:"
read -rs T; T=$(printf %s "$T" | sed 's/\[20[01]~//g' | tr -d '~ \r\n'); echo
echo "Recibido: ${#T} caracteres, empieza por ${T:0:10}"
echo
echo "== Cuenta =="
curl -s "https://api.apify.com/v2/users/me?token=$T" | head -c 400; echo; echo
for A in clockworks~tiktok-scraper apify~instagram-hashtag-scraper jungle_synthesizer~hotmart-marketplace-product-catalog-scraper; do
  echo "== $A =="
  curl -s -X POST "https://api.apify.com/v2/acts/$A/runs?token=$T&timeout=30&maxItems=1" -H 'content-type: application/json' -d '{}' | head -c 400; echo; echo
done
