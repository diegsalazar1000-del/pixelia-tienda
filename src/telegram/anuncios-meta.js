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
  await say('⏳ 2/4 Armando el público (países, edad, intereses)…');
  const ints = await idsIntereses((publico.intereses?.length ? publico.intereses : interesesPara(p)).slice(0, 8));
  const targeting = { geo_locations: { countries: PAISES }, age_min: Math.max(18, Number(publico.edad_min) || 24), age_max: Math.min(65, Number(publico.edad_max) || 45),
    ...(publico.generos === 'mujeres' || !publico.generos ? { genders: [2] } : publico.generos === 'hombres' ? { genders: [1] } : {}),
    targeting_automation: { advantage_audience: 0 }, ...(ints.length ? { flexible_spec: [{ interests: ints.map(({ id, name }) => ({ id, name })) }] } : {}) };
  const set = await api('POST', `${act}/adsets`, { name: `${nombre} · público`, campaign_id: camp.id, status: 'PAUSED', billing_event: 'IMPRESSIONS',
    optimization_goal: 'LANDING_PAGE_VIEWS', destination_type: 'WEBSITE', targeting });
  const ads = [];
  for (const [k, v] of variantes.entries()) {
    const letra = 'ABCD'[k];
    await say(`⏳ 3/4 Subiendo el anuncio ${letra} (${v.tipo === 'video' ? 'reel' : 'imagen'})…`);
    const cta = { type: p.price_cents ? 'SHOP_NOW' : 'DOWNLOAD', value: { link } };
    let spec;
    if (v.tipo === 'video') { const vid = await subirVideo(act, v.url, `${nombre} ${letra}`);
      spec = { video_data: { video_id: vid.id, image_url: vid.thumb, message: v.texto, title: v.titulo.slice(0, 40), call_to_action: cta } };
    } else { const hash = await subirImagen(act, v.url);
      spec = { link_data: { image_hash: hash, link, message: v.texto, name: v.titulo.slice(0, 40), call_to_action: cta } }; }
    const cr = await api('POST', `${act}/adcreatives`, { name: `${nombre} · ${letra}`, object_story_spec: { page_id: env('META_PAGE_ID'), ...(env('META_IG_ID') ? { instagram_user_id: env('META_IG_ID') } : {}), ...spec } });
    const ad = await api('POST', `${act}/ads`, { name: `${nombre} · ${letra} · ${v.nombre || v.tipo}`, adset_id: set.id, creative: { creative_id: cr.id }, status: 'PAUSED' });
    ads.push({ letra, id: ad.id, nombre: v.nombre || v.tipo });
  }
  await say('⏳ 4/4 Listo, revisando…');
  return { camp: camp.id, set: set.id, ads, moneda: c.currency, intereses: ints.map((i) => i.name),
    url: `https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=${act.replace('act_', '')}&selected_campaign_ids=${camp.id}` };
}

export async function activar(ids) { for (const id of [...(ids.ads || []).map((a) => a.id), ids.ad, ids.set, ids.camp].filter(Boolean)) await api('POST', id, { status: 'ACTIVE' }); }
export const pausarAnuncio = (adId) => api('POST', adId, { status: 'PAUSED' });
export const cambiarPresupuesto = (campId, usd) => api('POST', campId, { daily_budget: Math.round(usd * 100) });
/** Resultados por anuncio (A/B) de los últimos 7 días. */
export async function porAnuncio(campId) {
  const r = await api('GET', `${campId}/insights`, { level: 'ad', fields: 'ad_id,ad_name,spend,impressions,clicks,cpc,ctr,actions', date_preset: 'last_7d' });
  return (r.data || []).map((x) => ({ id: x.ad_id, nombre: x.ad_name, gasto: Number(x.spend || 0), vistas: Number(x.impressions || 0), clics: Number(x.clicks || 0),
    visitas: Number((x.actions || []).find((a) => a.action_type === 'landing_page_view')?.value || 0) }));
}
export async function pausar(ids) { await api('POST', ids.camp, { status: 'PAUSED' }); }
export async function borrar(ids) { await api('DELETE', ids.camp, {}); }

/** Resumen de los últimos 7 días de una campaña. */
export async function resultados(campId) {
  const r = await api('GET', `${campId}/insights`, { fields: 'spend,impressions,reach,clicks,cpc,ctr,actions', date_preset: 'last_7d' });
  return r.data?.[0] || null;
}
