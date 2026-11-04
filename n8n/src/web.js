// 🌐 EXPLORADOR WEB CON IA — Claude busca en internet productos digitales en tendencia (TikTok, Etsy, Hotmart, Instagram…).
// Usa el saldo de la API de Claude: unas 6 búsquedas al día (~0,06 $ + texto).
const C = $('Config').first().json;
const prev = $input.first().json; const items = prev.items || [], log = prev.log || [];
const hash = (s) => { let h = 0; for (const ch of String(s)) h = (Math.imul(31, h) + ch.charCodeAt(0)) | 0; return 'w' + (h >>> 0).toString(36); };

if (!C.EXPLORADOR_WEB || !C.ANTHROPIC_API_KEY || C.ANTHROPIC_API_KEY.startsWith('sk-ant-...')) {
  log.push('Explorador web: desactivado');
} else {
  const hoy = new Date().toISOString().slice(0, 10);
  const prompt = `Hoy es ${hoy}. Investiga en internet qué PRODUCTOS DIGITALES (plantillas, planners, ebooks, prompts, presets, imprimibles, hojas de cálculo, packs, mini cursos, etc.)
se están volviendo tendencia AHORA (lanzados o virales en los últimos 1-3 meses, no clásicos de hace años) en TikTok, Etsy, Hotmart, Instagram, Pinterest o Gumroad.
Prioriza lo que puede venderse a público hispanohablante por 3-10 USD. Usa varias búsquedas distintas (en español e inglés). Evita marcas registradas y "cursos para ganar dinero".
Devuelve SOLO un JSON (sin texto antes ni después) con esta forma:
[{"titulo":"nombre del producto o tipo de producto","url":"enlace donde lo viste (listado, vídeo o artículo)","plataforma":"tiktok|etsy|hotmart|instagram|pinterest|gumroad|otro",
"evidencia":"qué indica que es tendencia: cifras, ranking, fecha","fecha_aprox":"AAAA-MM o vacío","precio":número o 0,"publico":"para quién es"}]
Entre 8 y 15 elementos, sin repetir.`;
  try {
    const body = { model: C.MODELO_EXPLORADOR || C.MODELO_RAPIDO, max_tokens: 8000,
      tools: [{ type: 'web_search_20250305', name: 'web_search', max_uses: C.BUSQUEDAS_WEB_MAX || 6 }],
      messages: [{ role: 'user', content: prompt }] };
    let r, searches = 0, text = '';
    // Las búsquedas largas pueden "pausarse": se continúa hasta 4 veces
    for (let turn = 0; turn < 4; turn++) {
      r = await this.helpers.httpRequest({ method: 'POST', url: 'https://api.anthropic.com/v1/messages', json: true, timeout: 240000,
        headers: { 'x-api-key': C.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' }, body });
      searches += r.usage?.server_tool_use?.web_search_requests || 0;
      text += (r.content || []).filter((b) => b.type === 'text').map((b) => b.text).join('');
      if (r.stop_reason !== 'pause_turn') break;
      body.messages = [...body.messages, { role: 'assistant', content: r.content }];
    }
    const t = text.replace(/```json|```/g, '');
    if (t.indexOf('[') < 0) throw new Error(`sin lista (stop: ${r.stop_reason}) ${t.slice(0, 80)}`);
    const list = JSON.parse(t.slice(t.indexOf('['), t.lastIndexOf(']') + 1));
    for (const p of list) {
      if (!p?.titulo) continue;
      items.push({
        source: 'web', external_id: hash((p.url || '') + '|' + p.titulo.toLowerCase()), url: p.url || '', keyword: p.plataforma || '',
        title: p.titulo, snippet: `${p.evidencia || ''}\nPúblico: ${p.publico || ''}`, price: Number(p.precio) || 0, currency: 'USD',
        published_at: p.fecha_aprox || '', metrics: { plataforma: p.plataforma || '', evidencia: String(p.evidencia || '').slice(0, 200) },
        trend_score: 100,
      });
    }
    log.push(`Explorador web: ${list.length} tendencias encontradas (${searches} búsquedas)`);
  } catch (e) { log.push(`Explorador web: error ${e.message}`); }
}
return [{ json: { items, log } }];
