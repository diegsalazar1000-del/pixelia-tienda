// 🟠 ETSY — listados digitales populares y publicados hace poco (API oficial, gratis).
const C = $('Config').first().json;
const items = [], log = [];
const day = Math.floor(Date.now() / 86400000);
const pick = (list, n) => { if (!list?.length) return []; const s = (day * n) % list.length; return Array.from({ length: Math.min(n, list.length) }, (_, i) => list[(s + i) % list.length]); };
const ageDays = (ts) => Math.max(1, (Date.now() / 1000 - ts) / 86400);

if (!C.ETSY_API_KEY || C.ETSY_API_KEY.startsWith('keystring')) {
  log.push('Etsy: sin API key, se omite');
} else {
  for (const kw of pick(C.ETSY_BUSQUEDAS, C.POR_DIA.etsy)) {
    try {
      const r = await this.helpers.httpRequest({
        method: 'GET', url: 'https://openapi.etsy.com/v3/application/listings/active',
        qs: { keywords: kw, sort_on: 'score', limit: 100 }, headers: { 'x-api-key': C.ETSY_API_KEY }, json: true, timeout: 60000,
      });
      let n = 0;
      for (const l of r.results || []) {
        const digital = l.listing_type === 'download' || (l.tags || []).some((t) => /digital|printable|download|template/i.test(t));
        const age = ageDays(l.original_creation_timestamp || l.created_timestamp);
        const favs = l.num_favorers || 0;
        if (!digital || age > C.MAX_DIAS_ETSY || favs < C.MIN_FAVORITOS_ETSY) continue;
        n++;
        items.push({
          source: 'etsy', external_id: String(l.listing_id), url: l.url, title: l.title, keyword: kw,
          snippet: String(l.description || '').slice(0, 700),
          price: l.price ? l.price.amount / l.price.divisor : 0, currency: l.price?.currency_code || '',
          published_at: new Date((l.original_creation_timestamp || l.created_timestamp) * 1000).toISOString(),
          metrics: { favoritos: favs, vistas: l.views || 0, dias: Math.round(age), tags: (l.tags || []).slice(0, 8) },
          trend_score: Math.round((favs * 10 + (l.views || 0)) / age),
        });
      }
      log.push(`Etsy "${kw}": ${n} recientes`);
    } catch (e) { log.push(`Etsy "${kw}": error ${e.message}`); }
  }
}
return [{ json: { items, log } }];
