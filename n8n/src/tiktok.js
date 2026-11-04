// ⚫ TIKTOK — vídeos recientes con mucho alcance sobre productos digitales (Apify).
const C = $('Config').first().json;
const prev = $input.first().json; const items = prev.items || [], log = prev.log || [];
const day = Math.floor(Date.now() / 86400000);
const pick = (list, n) => { if (!list?.length) return []; const s = (day * n) % list.length; return Array.from({ length: Math.min(n, list.length) }, (_, i) => list[(s + i) % list.length]); };

if (!C.APIFY_TOKEN || C.APIFY_TOKEN.startsWith('apify_api_...')) {
  log.push('TikTok: sin token de Apify, se omite');
} else {
  try {
    const input = {
      searchQueries: pick(C.TIKTOK_BUSQUEDAS, C.POR_DIA.tiktok), hashtags: pick(C.TIKTOK_HASHTAGS, C.POR_DIA.tiktok_hashtags),
      resultsPerPage: C.RESULTADOS_POR_BUSQUEDA, searchSection: '/video',
      shouldDownloadVideos: false, shouldDownloadCovers: false, shouldDownloadSubtitles: false, shouldDownloadSlideshowImages: false,
    };
    const res = await this.helpers.httpRequest({
      method: 'POST', url: `https://api.apify.com/v2/acts/clockworks~tiktok-scraper/run-sync-get-dataset-items?token=${C.APIFY_TOKEN}&timeout=280`,
      body: input, json: true, timeout: 300000,
    });
    let n = 0;
    for (const v of res || []) {
      const created = v.createTimeISO ? new Date(v.createTimeISO) : v.createTime ? new Date(v.createTime * 1000) : null;
      if (!created || !v.id) continue;
      const age = Math.max(1, (Date.now() - created) / 86400000);
      const plays = v.playCount || 0;
      if (age > C.MAX_DIAS_POST || plays < C.MIN_VISTAS_TIKTOK) continue;
      n++;
      items.push({
        source: 'tiktok', external_id: String(v.id), url: v.webVideoUrl || '', keyword: v.searchQuery || v.input || '',
        title: String(v.text || '').slice(0, 160), snippet: String(v.text || '').slice(0, 700),
        published_at: created.toISOString(), image: v.videoMeta?.coverUrl || '',
        metrics: { vistas: plays, likes: v.diggCount || 0, compartidos: v.shareCount || 0, guardados: v.collectCount || 0,
          comentarios: v.commentCount || 0, autor: v.authorMeta?.name || '', seguidores: v.authorMeta?.fans || 0, dias: Math.round(age) },
        trend_score: Math.round((plays + 20 * (v.shareCount || 0) + 10 * (v.collectCount || 0)) / age),
      });
    }
    log.push(`TikTok: ${(res || []).length} vídeos revisados, ${n} recientes y virales`);
  } catch (e) { log.push(`TikTok: error ${e.message}`); }
}
return [{ json: { items, log } }];
