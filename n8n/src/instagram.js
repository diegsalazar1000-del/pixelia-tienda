// 🟣 INSTAGRAM — publicaciones/reels recientes de hashtags de productos digitales (Apify).
const C = $('Config').first().json;
const prev = $input.first().json; const items = prev.items || [], log = prev.log || [];
const day = Math.floor(Date.now() / 86400000);
const pick = (list, n) => { if (!list?.length) return []; const s = (day * n) % list.length; return Array.from({ length: Math.min(n, list.length) }, (_, i) => list[(s + i) % list.length]); };

if (!C.APIFY_TOKEN || C.APIFY_TOKEN.startsWith('apify_api_...')) {
  log.push('Instagram: sin token de Apify, se omite');
} else {
  try {
    const res = await this.helpers.httpRequest({
      method: 'POST', url: `https://api.apify.com/v2/acts/apify~instagram-hashtag-scraper/run-sync-get-dataset-items?token=${C.APIFY_TOKEN}&timeout=280`,
      body: { hashtags: pick(C.INSTAGRAM_HASHTAGS, C.POR_DIA.instagram), resultsLimit: C.RESULTADOS_POR_BUSQUEDA }, json: true, timeout: 300000,
    });
    let n = 0;
    for (const p of res || []) {
      const created = p.timestamp ? new Date(p.timestamp) : null;
      if (!created || !(p.id || p.shortCode)) continue;
      const age = Math.max(1, (Date.now() - created) / 86400000);
      if (age > C.MAX_DIAS_POST) continue;
      const likes = p.likesCount > 0 ? p.likesCount : 0, comments = p.commentsCount || 0, views = p.videoViewCount || p.videoPlayCount || 0;
      if (likes + comments * 3 + views / 10 < 300) continue;
      n++;
      items.push({
        source: 'instagram', external_id: String(p.id || p.shortCode), url: p.url || `https://www.instagram.com/p/${p.shortCode}/`,
        keyword: (p.inputUrl || '').split('/tags/')[1]?.replace(/\/$/, '') || '',
        title: String(p.caption || '').slice(0, 160), snippet: String(p.caption || '').slice(0, 700),
        published_at: created.toISOString(), image: p.displayUrl || '',
        metrics: { likes, comentarios: comments, vistas: views, autor: p.ownerUsername || '', dias: Math.round(age) },
        trend_score: Math.round((likes + 3 * comments + views / 10) / age),
      });
    }
    log.push(`Instagram: ${(res || []).length} publicaciones revisadas, ${n} recientes con tracción`);
  } catch (e) { log.push(`Instagram: error ${e.message}`); }
}
return [{ json: { items, log } }];
