// 📊 Campañas de Meta Ads desde el bot (Marketing API). TODO se crea EN PAUSA: Diego revisa y activa.
// Token: META_USER_TOKEN (usuario del sistema "Pixelia Bot", no vence) · Cuenta: META_AD_ACCOUNT (act_…)
const G = 'https://graph.facebook.com/v23.0';
const env = (k) => process.env[k] || '';
export const adsListos = () => !!(env('META_USER_TOKEN') && env('META_AD_ACCOUNT') && env('META_PAGE_ID'));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(method, path, params = {}) {
  const p = { ...params, access_token: env('META_USER_TOKEN') };
  for (const k of Object.keys(p)) if (typeof p[k] === 'object') p[k] = JSON.stringify(p[k]);
  const body = new URLSearchParams(p);
  const r = method === 'GET' ? await fetch(`${G}/${path}?${body}`) : await fetch(`${G}/${path}`, { method, body });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.error) throw new Error(j.error?.error_user_msg || j.error?.message || `HTTP ${r.status}`);
  return j;
}

export const PAISES = ['MX', 'CO', 'VE', 'PE', 'CL', 'AR', 'EC', 'US'];
// 📍 Dónde salen los anuncios (Diego 8-nov): SIN Audience Network ni Messenger (clics baratos que no compran) y con prioridad a Instagram:
// Instagram en todos sus lugares y Facebook solo en Feed, Reels e Historias. META_SOLO_INSTAGRAM=1 → solo Instagram.
export function ubicaciones() {
  if (env('META_SOLO_INSTAGRAM') === '1') return { publisher_platforms: ['instagram'], instagram_positions: ['stream', 'story', 'reels', 'explore', 'explore_home', 'profile_feed'] };
  return { publisher_platforms: ['instagram', 'facebook'], instagram_positions: ['stream', 'story', 'reels', 'explore', 'explore_home', 'profile_feed'],
    facebook_positions: ['feed', 'facebook_reels', 'story'] };
}
const INTERESES = { finanzas: ['Personal finance', 'Saving', 'Budget'], navidad: ['Christmas', 'Gift'], planner: ['Planners', 'Personal organizer', 'Stationery'],
  fiesta: ['Baby shower', 'Party'], general: ['Personal development', 'Productivity'] };
export function interesesPara(p) {
  const t = `${p.title} ${p.category} ${p.short}`.toLowerCase();
  if (/navide|navidad|regalo/.test(t) && /plan/.test(t)) return [...INTERESES.navidad, ...INTERESES.finanzas.slice(0, 1)];
  if (/ahorro|finanz|dinero|presupuesto|excel/.test(t)) return INTERESES.finanzas.concat('Microsoft Excel');
  if (/baby|loter|fiesta/.test(t)) return INTERESES.fiesta;
  if (/planner|agenda|organiz/.test(t)) return INTERESES.planner;
  return INTERESES.general;
}
async function idsIntereses(nombres) {
  const out = [];
  for (const n of nombres) {
    const r = await api('GET', 'search', { type: 'adinterest', q: n, limit: 1, locale: 'es_LA' }).catch(() => ({ data: [] }));
    if (r.data?.[0]) out.push({ id: r.data[0].id, name: r.data[0].name });
  }
  return out;
}

export async function cuenta() {
  return api('GET', env('META_AD_ACCOUNT'), { fields: 'name,currency,account_status,min_daily_budget' });
}

async function subirVideo(act, url, nombre) {
  const v = await api('POST', `${act}/advideos`, { file_url: url, name: nombre });
  for (let i = 0; i < 40; i++) {
    await sleep(6000);
    const s = await api('GET', v.id, { fields: 'status,picture' }).catch(() => ({}));
    if (s.status?.video_status === 'ready' && s.picture) return { id: v.id, thumb: s.picture };
    if (s.status?.video_status === 'error') throw new Error('Meta no pudo procesar el video');
  }
  const t = await api('GET', `${v.id}/thumbnails`, {}).catch(() => ({ data: [] }));
  const thumb = (t.data || []).find((x) => x.is_preferred)?.uri || t.data?.[0]?.uri;
  if (!thumb) throw new Error('el video sigue procesándose; prueba de nuevo en unos minutos');
  return { id: v.id, thumb };
}
async function subirImagen(act, url) {
  const buf = Buffer.from(await (await fetch(url)).arrayBuffer());
  const r = await api('POST', `${act}/adimages`, { bytes: buf.toString('base64') });
  return Object.values(r.images || {})[0]?.hash;
}

/** Crea campaña + conjunto + anuncios A/B (reel, otra variante o imagen), TODO EN PAUSA. */
export async function crearCampana({ p, variantes, link, presupuesto, publico = {}, say }) {
  const act = env('META_AD_ACCOUNT');
  const c = await cuenta();
  if (c.account_status !== 1) throw new Error('la cuenta publicitaria no está activa (revisa Calidad de la cuenta o el método de pago)');
  const nombre = `Pixelia · ${p.title.slice(0, 40)} · ${new Date().toISOString().slice(0, 10)}`;
  await say(`⏳ 1/4 Creando la campaña (objetivo: visitas a la página)…`);
  const camp = await api('POST', `${act}/campaigns`, { name: nombre, objective: 'OUTCOME_TRAFFIC', status: 'PAUSED', special_ad_categories: [], buying_type: 'AUCTION',
    daily_budget: Math.round(presupuesto * 100), bid_strategy: 'LOWEST_COST_WITHOUT_CAP' });
  await say(publico.audiencias?.length ? '⏳ 2/4 Armando el público (tus interesados reales)…' : '⏳ 2/4 Armando el público (países, edad, intereses)…');
  const aud = (publico.audiencias || []).filter(Boolean);
  const ints = aud.length ? [] : await idsIntereses((publico.intereses?.length ? publico.intereses : interesesPara(p)).slice(0, 8));
  const targeting = aud.length ? {  // 🎯 remarketing / similares: el público ya está definido, sin intereses ni edad estrecha
    geo_locations: { countries: PAISES }, age_min: 18, age_max: 65, targeting_automation: { advantage_audience: 0 }, ...ubicaciones(),
    custom_audiences: aud.map((id) => ({ id })), ...((publico.excluir || []).filter(Boolean).length ? { excluded_custom_audiences: publico.excluir.filter(Boolean).map((id) => ({ id })) } : {}) } : { geo_locations: { countries: PAISES }, age_min: Math.max(18, Number(publico.edad_min) || 24), age_max: Math.min(65, Number(publico.edad_max) || 45),
    ...(publico.generos === 'mujeres' ? { genders: [2] } : publico.generos === 'hombres' ? { genders: [1] } : {}),  // sin indicación = todos
    targeting_automation: { advantage_audience: 0 }, ...ubicaciones(), ...(ints.length ? { flexible_spec: [{ interests: ints.map(({ id, name }) => ({ id, name })) }] } : {}) };
  const set = await api('POST', `${act}/adsets`, { name: `${nombre} · público`, campaign_id: camp.id, status: 'PAUSED', billing_event: 'IMPRESSIONS',
    optimization_goal: 'LANDING_PAGE_VIEWS', destination_type: 'WEBSITE', targeting });
  const ads = [], videos = {};
  let setImgs = null;
  try {
  for (const [k, v] of variantes.entries()) {
    const letra = 'ABCD'[k];
    await say(`⏳ 3/4 Subiendo el anuncio ${k + 1} (${v.nombre || (v.tipo === 'video' ? 'reel' : 'imagen')})…`);
    const cta = { type: p.price_cents ? 'SHOP_NOW' : 'DOWNLOAD', value: { link } };
    if (v.tipo === 'imagenes') {  // 🖼️×3 varias imágenes y textos en UN anuncio: Meta prueba las combinaciones (creativo dinámico, va en su propio conjunto)
      setImgs = await api('POST', `${act}/adsets`, { name: `${nombre} · imágenes`, campaign_id: camp.id, status: 'PAUSED', billing_event: 'IMPRESSIONS',
        optimization_goal: 'LANDING_PAGE_VIEWS', destination_type: 'WEBSITE', targeting, is_dynamic_creative: true });
      // cada imagen con sus 3 tamaños: 4:5 → Feed, vertical → Historias/Reels, cuadrada → otros lugares; Meta elige la mejor imagen en cada lugar
      const imgs = [];
      for (const it of v.items) for (const [t, u] of Object.entries(it.tamanos || { '4x5': it.url })) if (t !== '1x1') imgs.push({ hash: await subirImagen(act, u), nombre: it.nombre, t });
      const base = { bodies: (v.textos || [v.texto]).map((text) => ({ text })), titles: (v.titulos || [v.titulo]).map((t) => ({ text: String(t).slice(0, 40) })),
        link_urls: [{ website_url: link }], call_to_action_types: [cta.type], ad_formats: ['SINGLE_IMAGE'] };
      const actor = { page_id: env('META_PAGE_ID'), ...(env('META_IG_ID') ? { instagram_user_id: env('META_IG_ID') } : {}) };
      const lab = { '4x5': 'feed', '9x16': 'vertical', '1x1': 'cuadrada' };
      const reglas = [
        ...(imgs.some((i) => i.t === '9x16') ? [{ customization_spec: { publisher_platforms: ['facebook', 'instagram'], facebook_positions: ['story', 'facebook_reels'], instagram_positions: ['story', 'reels'] }, image_label: { name: 'vertical' } }] : []),
        { customization_spec: { publisher_platforms: ['facebook', 'instagram'] }, image_label: { name: 'feed' } }].map((r, i) => ({ ...r, priority: i + 1 }));
      let cr;
      try {
        cr = await api('POST', `${act}/adcreatives`, { name: `${nombre} · ${letra}`, object_story_spec: actor,
          asset_feed_spec: { ...base, images: imgs.map((i) => ({ hash: i.hash, adlabels: [{ name: lab[i.t] || 'feed' }] })), asset_customization_rules: reglas } });
      } catch (e) {  // si Meta no acepta tamaños por lugar en este modo, van solo las 4:5 (Meta adapta las Historias)
        console.error('[meta] imágenes con tamaños:', e.message); await say('ℹ️ Meta no aceptó los 3 tamaños en el anuncio de imágenes; van las 4:5 y Meta las adapta a Historias.');
        cr = await api('POST', `${act}/adcreatives`, { name: `${nombre} · ${letra}`, object_story_spec: actor, asset_feed_spec: { ...base, images: imgs.filter((i) => i.t === '4x5').map((i) => ({ hash: i.hash })) } });
      }
      const ad = await api('POST', `${act}/ads`, { name: `${nombre} · ${letra} · ${v.nombre}`, adset_id: setImgs.id, creative: { creative_id: cr.id }, status: 'PAUSED' });
      ads.push({ letra, id: ad.id, nombre: v.nombre, dinamico: true, imagenes: Object.fromEntries(imgs.map((i) => [i.hash, i.nombre])), textos: v.textos || [v.texto] });
      continue;
    }
    let spec;
    if (v.tipo === 'video') { const vid = videos[v.url] ||= await subirVideo(act, v.url, `${nombre} ${letra}`);  // el mismo reel se sube 1 sola vez
      spec = { video_data: { video_id: vid.id, image_url: vid.thumb, message: v.texto, title: v.titulo.slice(0, 40), call_to_action: cta } };
    }
    const actor = { page_id: env('META_PAGE_ID'), ...(env('META_IG_ID') ? { instagram_user_id: env('META_IG_ID') } : {}) };
    let cr = null;
    if (v.tipo !== 'video' && v.tamanos && Object.keys(v.tamanos).length > 1) {  // 🖼️ una imagen con sus tamaños: cada lugar usa el suyo
      try {
        const hs = {}; for (const [t, u] of Object.entries(v.tamanos)) if (t !== '1x1') hs[t] = await subirImagen(act, u);
        const reglas = [], imgs = [];
        if (hs['9x16']) { imgs.push({ hash: hs['9x16'], adlabels: [{ name: 'vertical' }] });
          reglas.push({ customization_spec: { publisher_platforms: ['facebook', 'instagram'], facebook_positions: ['story', 'facebook_reels'], instagram_positions: ['story', 'reels'] }, image_label: { name: 'vertical' }, priority: 1 }); }
        imgs.push({ hash: hs['4x5'] || Object.values(hs)[0], adlabels: [{ name: 'feed' }] });
        reglas.push({ customization_spec: { publisher_platforms: ['facebook', 'instagram'] }, image_label: { name: 'feed' }, priority: reglas.length + 1 });
        cr = await api('POST', `${act}/adcreatives`, { name: `${nombre} · ${letra}`, object_story_spec: actor,
          asset_feed_spec: { images: imgs, bodies: [{ text: v.texto }], titles: [{ text: v.titulo.slice(0, 40) }], link_urls: [{ website_url: link }],
            call_to_action_types: [cta.type], ad_formats: ['SINGLE_IMAGE'], asset_customization_rules: reglas } });
      } catch (e) { console.error('[meta] imagen con tamaños falló, uso solo la 4:5:', e.message); cr = null; }
    }
    if (!cr && v.tipo !== 'video') { const hash = await subirImagen(act, v.tamanos?.['4x5'] || v.url);
      spec = { link_data: { image_hash: hash, link, message: v.texto, name: v.titulo.slice(0, 40), call_to_action: cta } }; }
    if (!cr) cr = await api('POST', `${act}/adcreatives`, { name: `${nombre} · ${letra}`, object_story_spec: { ...actor, ...spec } });
    const ad = await api('POST', `${act}/ads`, { name: `${nombre} · ${letra} · ${v.nombre || v.tipo}`, adset_id: set.id, creative: { creative_id: cr.id }, status: 'PAUSED' });
    ads.push({ letra, id: ad.id, nombre: v.nombre || v.tipo });
  }
  } catch (e) { await api('DELETE', camp.id, {}).catch(() => {}); throw e; }  // si algo falla, no deja una campaña a medias en Meta
  await say('⏳ 4/4 Listo, revisando…');
  return { camp: camp.id, set: set.id, sets: [set.id, setImgs?.id].filter(Boolean), ads, moneda: c.currency, intereses: aud.length ? [publico.etiqueta || 'interesados reales'] : ints.map((i) => i.name),
    url: `https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=${act.replace('act_', '')}&selected_campaign_ids=${camp.id}` };
}

export async function activar(ids) { for (const id of [...new Set([...(ids.ads || []).map((a) => a.id), ids.ad, ...(ids.sets || []), ids.set, ids.camp].filter(Boolean))]) await api('POST', id, { status: 'ACTIVE' }); }
export const pausarAnuncio = (adId) => api('POST', adId, { status: 'PAUSED' });
export const cambiarPresupuesto = (campId, usd) => api('POST', campId, { daily_budget: Math.round(usd * 100) });
/** Resultados por anuncio (A/B) de los últimos 7 días. */
export async function porAnuncio(campId) {
  const r = await api('GET', `${campId}/insights`, { level: 'ad', fields: 'ad_id,ad_name,spend,impressions,clicks,cpc,ctr,frequency,actions', date_preset: 'last_7d' });
  return (r.data || []).map((x) => ({ id: x.ad_id, nombre: x.ad_name, gasto: Number(x.spend || 0), vistas: Number(x.impressions || 0), clics: Number(x.clicks || 0), frecuencia: Number(x.frequency || 0),
    visitas: Number((x.actions || []).find((a) => a.action_type === 'landing_page_view')?.value || 0) }));
}
/** Pone las ubicaciones nuevas (sin Audience Network, prioridad Instagram) a los conjuntos de una campaña ya creada. */
export async function aplicarUbicaciones(ids) {
  const sets = [...new Set([...(ids.sets || []), ids.set].filter(Boolean))], hechos = [];
  for (const id of sets) {
    const { targeting = {} } = await api('GET', id, { fields: 'targeting' });
    for (const k of ['publisher_platforms', 'facebook_positions', 'instagram_positions', 'audience_network_positions', 'messenger_positions', 'device_platforms']) delete targeting[k];
    await api('POST', id, { targeting: { ...targeting, ...ubicaciones() } }); hechos.push(id);
  }
  return hechos;
}
export async function pausar(ids) { await api('POST', ids.camp, { status: 'PAUSED' }); }
export async function borrar(ids) { await api('DELETE', ids.camp, {}); }

/** Resumen de los últimos 7 días de una campaña. */
export async function resultados(campId) {
  const r = await api('GET', `${campId}/insights`, { fields: 'spend,impressions,reach,clicks,cpc,ctr,actions', date_preset: 'last_7d' });
  return r.data?.[0] || null;
}

// ===== 🎯 Públicos de interesados reales (según lo que hacen en la web y en Instagram/Facebook) =====
const DIAS = (d) => d * 86400;
const evento = (pixel, ev, dias) => ({ event_sources: [{ id: pixel, type: 'pixel' }], retention_seconds: DIAS(dias), filter: { operator: 'and', filters: [{ field: 'event', operator: 'eq', value: ev }] } });
export function definicionesPublicos() {
  const px = env('META_PIXEL_ID'), ig = env('META_IG_ID'), page = env('META_PAGE_ID'), out = [];
  if (px) {
    out.push({ clave: 'vieron', nombre: 'Pixelia · Vieron un producto (30 días)', rule: { inclusions: { operator: 'or', rules: [evento(px, 'ViewContent', 30)] } } });
    out.push({ clave: 'regalo', nombre: 'Pixelia · Bajaron el regalo (90 días)', rule: { inclusions: { operator: 'or', rules: [evento(px, 'Lead', 90)] } } });
    out.push({ clave: 'casi', nombre: 'Pixelia · Empezaron a pagar y no compraron (14 días)', rule: { inclusions: { operator: 'or', rules: [evento(px, 'InitiateCheckout', 14)] }, exclusions: { operator: 'or', rules: [evento(px, 'Purchase', 14)] } } });
    out.push({ clave: 'compradores', nombre: 'Pixelia · Compradores (180 días)', rule: { inclusions: { operator: 'or', rules: [evento(px, 'Purchase', 180)] } } });
  }
  if (ig) out.push({ clave: 'ig', nombre: 'Pixelia · Interactuaron en Instagram (365 días)', rule: { inclusions: { operator: 'or', rules: [{ event_sources: [{ id: ig, type: 'ig_business' }], retention_seconds: DIAS(365), filter: { operator: 'and', filters: [{ field: 'event', operator: 'eq', value: 'ig_business_profile_all' }] } }] } } });
  if (page) out.push({ clave: 'fb', nombre: 'Pixelia · Interactuaron en Facebook (365 días)', rule: { inclusions: { operator: 'or', rules: [{ event_sources: [{ id: page, type: 'page' }], retention_seconds: DIAS(365), filter: { operator: 'and', filters: [{ field: 'event', operator: 'eq', value: 'page_engaged' }] } }] } } });
  return out;
}
/** Crea los públicos que falten; devuelve {clave: id}. */
export async function crearPublicos(existentes = {}) {
  const act = env('META_AD_ACCOUNT'), res = { ...existentes }, errores = [];
  for (const d of definicionesPublicos()) {
    if (res[d.clave]) continue;
    try { res[d.clave] = (await api('POST', `${act}/customaudiences`, { name: d.nombre, rule: d.rule, prefill: true, ...(d.clave === 'ig' || d.clave === 'fb' ? {} : {}) })).id; }
    catch (e) { errores.push(`${d.nombre}: ${e.message}`); }
  }
  return { ids: res, errores };
}
/** Tamaño aproximado de cada público (Meta da rangos; < 1000 suele mostrarse como "menos de 1000"). */
export async function tamanos(ids) {
  const out = {};
  for (const [k, id] of Object.entries(ids)) {
    const r = await api('GET', id, { fields: 'name,approximate_count_lower_bound,approximate_count_upper_bound,operation_status' }).catch(() => null);
    if (r) out[k] = { nombre: r.name, min: r.approximate_count_lower_bound, max: r.approximate_count_upper_bound };
  }
  return out;
}

/** 👥 Públicos similares (lookalike 1%) a partir de los interesados reales, en los mismos países. Meta pide ~100 personas en el público de origen. */
export async function crearSimilares(ids) {
  const act = env('META_AD_ACCOUNT'), res = {}, errores = [];
  for (const [clave, nombre] of [['regalo', 'bajaron el regalo'], ['vieron', 'vieron un producto'], ['compradores', 'compradores']]) {
    if (!ids[clave] || ids['sim_' + clave]) { if (ids['sim_' + clave]) res['sim_' + clave] = ids['sim_' + clave]; continue; }
    try {
      res['sim_' + clave] = (await api('POST', `${act}/customaudiences`, { name: `Pixelia · Similares a quienes ${nombre} (1%)`, subtype: 'LOOKALIKE', origin_audience_id: ids[clave],
        lookalike_spec: { type: 'similarity', ratio: 0.01, location_spec: { geo_locations: { countries: PAISES } } } })).id;
    } catch (e) { errores.push(`${nombre}: ${/at least|100|too small|pequeñ/i.test(e.message) ? 'todavía tiene muy poca gente (Meta pide ~100)' : e.message}`); }
  }
  return { ids: res, errores };
}

/** ⏰ Impresiones y clics por hora del día (hora local de quien vio el anuncio) de las campañas, últimos 28 días. */
export async function horasAnuncios(campIds) {
  const h = Array.from({ length: 24 }, () => ({ impresiones: 0, clics: 0 }));
  for (const id of campIds) {
    const r = await api('GET', `${id}/insights`, { fields: 'impressions,clicks', breakdowns: 'hourly_stats_aggregated_by_audience_time_zone', date_preset: 'last_28d', limit: 100 }).catch(() => ({ data: [] }));
    for (const x of r.data || []) { const k = parseInt(String(x.hourly_stats_aggregated_by_audience_time_zone || ''), 10); if (k >= 0 && k < 24) { h[k].impresiones += Number(x.impressions || 0); h[k].clics += Number(x.clicks || 0); } }
  }
  return h;
}

/** En el anuncio de varias imágenes: qué imagen y qué texto consiguieron más visitas (últimos 7 días). */
export async function desgloseDinamico(ad) {
  const out = {};
  for (const [b, campo] of [['image_asset', 'imagenes'], ['body_asset', 'textos']]) {
    const r = await api('GET', `${ad.id}/insights`, { fields: 'spend,impressions,actions', breakdowns: b, date_preset: 'last_7d' }).catch(() => ({ data: [] }));
    const filas = (r.data || []).map((x) => {
      const a = x[b] || {}, nombre = campo === 'imagenes' ? (ad.imagenes || {})[a.hash] || 'imagen' : (() => { const i = (ad.textos || []).findIndex((t) => String(t).slice(0, 40) === String(a.text || '').slice(0, 40)); return i >= 0 ? `texto ${'AB'[i] || i + 1}` : 'texto'; })();
      return { nombre, gasto: Number(x.spend || 0), vistas: Number(x.impressions || 0), visitas: Number((x.actions || []).find((y) => y.action_type === 'landing_page_view')?.value || 0) };
    });
    const g = {}; for (const f of filas) { const o = (g[f.nombre] ||= { nombre: f.nombre, gasto: 0, vistas: 0, visitas: 0 }); o.gasto += f.gasto; o.vistas += f.vistas; o.visitas += f.visitas; }
    out[campo] = Object.values(g);
  }
  return out;
}
