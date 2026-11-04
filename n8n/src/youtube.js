// 🔴 YOUTUBE — vídeos y Shorts recientes que están explotando sobre productos digitales (API oficial, gratis).
const C = $('Config').first().json;
const prev = $input.first().json; const items = prev.items || [], log = prev.log || [];
const day = Math.floor(Date.now() / 86400000);
const pick = (list, n) => { if (!list?.length) return []; const s = (day * n) % list.length; return Array.from({ length: Math.min(n, list.length) }, (_, i) => list[(s + i) % list.length]); };

if (!C.YOUTUBE_API_KEY || C.YOUTUBE_API_KEY.startsWith('AIza...')) {
  log.push('YouTube: sin API key, se omite');
} else {
  const since = new Date(Date.now() - C.MAX_DIAS_POST * 86400000).toISOString();
  const ids = new Map();
  for (const q of pick(C.YOUTUBE_BUSQUEDAS, C.POR_DIA.youtube)) {
    try {
      const r = await this.helpers.httpRequest({ method: 'GET', url: 'https://www.googleapis.com/youtube/v3/search', json: true, timeout: 30000,
        qs: { key: C.YOUTUBE_API_KEY, part: 'snippet', q, type: 'video', order: 'viewCount', publishedAfter: since, maxResults: 25 } });
      for (const v of r.items || []) if (v.id?.videoId) ids.set(v.id.videoId, q);
    } catch (e) { log.push(`YouTube "${q}": error ${e.message}`); }
  }
  // Estadísticas en bloques de 50 (cuesta 1 unidad por bloque)
  const all = [...ids.keys()];
  let n = 0;
  for (let i = 0; i < all.length; i += 50) {
    try {
      const r = await this.helpers.httpRequest({ method: 'GET', url: 'https://www.googleapis.com/youtube/v3/videos', json: true, timeout: 30000,
        qs: { key: C.YOUTUBE_API_KEY, part: 'snippet,statistics', id: all.slice(i, i + 50).join(',') } });
      for (const v of r.items || []) {
        const views = Number(v.statistics?.viewCount || 0), likes = Number(v.statistics?.likeCount || 0), comments = Number(v.statistics?.commentCount || 0);
        const age = Math.max(1, (Date.now() - new Date(v.snippet.publishedAt)) / 86400000);
        if (views < C.MIN_VISTAS_YOUTUBE) continue;
        n++;
        items.push({
          source: 'youtube', external_id: v.id, url: `https://www.youtube.com/watch?v=${v.id}`, keyword: ids.get(v.id) || '',
          title: v.snippet.title, snippet: `${v.snippet.title}\n${String(v.snippet.description || '').slice(0, 600)}`,
          published_at: v.snippet.publishedAt, image: v.snippet.thumbnails?.high?.url || '',
          metrics: { vistas: views, likes, comentarios: comments, canal: v.snippet.channelTitle, dias: Math.round(age) },
          trend_score: Math.round((views + likes * 20 + comments * 30) / age),
        });
      }
    } catch (e) { log.push(`YouTube estadísticas: error ${e.message}`); }
  }
  log.push(`YouTube: ${all.length} vídeos recientes revisados, ${n} con tracción`);
}
return [{ json: { items, log } }];
