// 🧮 FILTRAR Y GUARDAR — se queda con lo mejor de cada fuente y lo guarda en la tienda.
// La tienda devuelve solo lo NUEVO (lo que ya vimos otro día no se repite).
const C = $('Config').first().json;
const { items = [], log = [] } = $input.first().json;

const bySource = {};
for (const it of items) (bySource[it.source] ||= []).push(it);
const top = [];
for (const [src, list] of Object.entries(bySource)) {
  const seen = new Set();
  const uniq = list.filter((i) => !seen.has(i.external_id) && seen.add(i.external_id));
  uniq.sort((a, b) => b.trend_score - a.trend_score);
  top.push(...uniq.slice(0, C.TOP_POR_FUENTE[src] || 10));
}

let fresh = [];
if (top.length) {
  const r = await this.helpers.httpRequest({
    method: 'POST', url: `${C.TIENDA_URL}/api/n8n/candidates`, headers: { 'x-api-key': C.TIENDA_API_KEY },
    body: { items: top }, json: true, timeout: 60000,
  });
  fresh = r.items || [];
}
log.push(`Total encontrado: ${items.length} · mejores: ${top.length} · nuevos hoy: ${fresh.length}`);
return [{ json: { fresh, log, found: items.length } }];
