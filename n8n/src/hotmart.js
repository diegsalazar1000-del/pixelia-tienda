// 🔥 HOTMART — productos "calientes" del marketplace por palabra clave (Apify).
const C = $('Config').first().json;
const prev = $input.first().json; const items = prev.items || [], log = prev.log || [];
const day = Math.floor(Date.now() / 86400000);
const pick = (list, n) => { if (!list?.length) return []; const s = (day * n) % list.length; return Array.from({ length: Math.min(n, list.length) }, (_, i) => list[(s + i) % list.length]); };

if (!C.APIFY_TOKEN || C.APIFY_TOKEN.startsWith('apify_api_...')) {
  log.push('Hotmart: sin token de Apify, se omite');
} else {
  try {
    const kws = pick(C.HOTMART_BUSQUEDAS, C.POR_DIA.hotmart);
    const res = await this.helpers.httpRequest({
      method: 'POST',
      url: `https://api.apify.com/v2/acts/jungle_synthesizer~hotmart-marketplace-product-catalog-scraper/run-sync-get-dataset-items?token=${C.APIFY_TOKEN}&timeout=280`,
      body: { keywords: kws, maxItems: kws.length * 24 }, json: true, timeout: 300000,
    });
    for (const p of res || []) {
      const url = p.product_url || p.url || p.marketplace_url || '';
      const id = p.product_id || p.id || p.ucode || url;
      if (!id) continue;
      // Hotmart no da fecha de publicación: priorizamos "hot_score" alto con pocas reseñas (señal de producto nuevo que despega).
      const reviews = p.rating_count || 0, hot = p.hot_score || 0;
      items.push({
        source: 'hotmart', external_id: String(id), url, keyword: p.search_keyword || '',
        title: p.name || p.product_name || p.title || '', snippet: String(p.description_short || p.description || '').slice(0, 700),
        price: p.price || p.price_brl || 0, currency: p.currency || (p.price_brl ? 'BRL' : ''), image: p.thumbnail_url || '',
        published_at: '', metrics: { hot_score: hot, reseñas: reviews, nota: p.rating_avg || 0, formato: p.format || '', autor: p.producer_name || '' },
        trend_score: Math.round(hot / Math.log10(reviews + 10)),
      });
    }
    log.push(`Hotmart: ${(res || []).length} productos revisados`);
  } catch (e) { log.push(`Hotmart: error ${e.message}`); }
}
return [{ json: { items, log } }];
