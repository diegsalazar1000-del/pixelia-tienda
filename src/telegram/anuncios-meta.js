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

/** Crea campaña + conjunto + anuncio con el reel, TODO EN PAUSA. */
export async function crearCampana({ p, videoUrl, texto, titulo, link, presupuesto, say }) {
  const act = env('META_AD_ACCOUNT');
  const c = await cuenta();
  if (c.account_status !== 1) throw new Error('la cuenta publicitaria no está activa (revisa Calidad de la cuenta o el método de pago)');
  const nombre = `Pixelia · ${p.title.slice(0, 40)} · ${new Date().toISOString().slice(0, 10)}`;
  await say('⏳ 1/5 Subiendo el reel a la cuenta publicitaria…');
  const v = await api('POST', `${act}/advideos`, { file_url: videoUrl, name: nombre });
  let thumb = '';
  for (let i = 0; i < 40; i++) {
    await sleep(6000);
    const s = await api('GET', v.id, { fields: 'status,picture' }).catch(() => ({}));
    if (s.status?.video_status === 'ready') { thumb = s.picture || ''; break; }
    if (s.status?.video_status === 'error') throw new Error('Meta no pudo procesar el video');
  }
  if (!thumb) { const t = await api('GET', `${v.id}/thumbnails`, {}).catch(() => ({ data: [] })); thumb = (t.data || []).find((x) => x.is_preferred)?.uri || t.data?.[0]?.uri || ''; }
  if (!thumb) throw new Error('el video sigue procesándose; prueba de nuevo en unos minutos');
  await say('⏳ 2/5 Creando la campaña (objetivo: tráfico)…');
  const camp = await api('POST', `${act}/campaigns`, { name: nombre, objective: 'OUTCOME_TRAFFIC', status: 'PAUSED', special_ad_categories: [], buying_type: 'AUCTION',
    daily_budget: Math.round(presupuesto * 100), bid_strategy: 'LOWEST_COST_WITHOUT_CAP' });
  await say('⏳ 3/5 Armando el público (países, edad, intereses)…');
  const ints = await idsIntereses(interesesPara(p));
  const targeting = { geo_locations: { countries: PAISES }, age_min: 24, age_max: 45, genders: [2], targeting_automation: { advantage_audience: 0 },
    ...(ints.length ? { flexible_spec: [{ interests: ints.map(({ id, name }) => ({ id, name })) }] } : {}) };
  const set = await api('POST', `${act}/adsets`, { name: `${nombre} · público`, campaign_id: camp.id, status: 'PAUSED', billing_event: 'IMPRESSIONS',
    optimization_goal: 'LANDING_PAGE_VIEWS', destination_type: 'WEBSITE', targeting });
  await say('⏳ 4/5 Creando el anuncio con tu reel…');
  const cr = await api('POST', `${act}/adcreatives`, { name: `${nombre} · creativo`, object_story_spec: { page_id: env('META_PAGE_ID'),
    ...(env('META_IG_ID') ? { instagram_user_id: env('META_IG_ID') } : {}),
    video_data: { video_id: v.id, image_url: thumb, message: texto, title: titulo.slice(0, 40),
      call_to_action: { type: p.price_cents ? 'SHOP_NOW' : 'DOWNLOAD', value: { link } } } } });
  const ad = await api('POST', `${act}/ads`, { name: `${nombre} · anuncio`, adset_id: set.id, creative: { creative_id: cr.id }, status: 'PAUSED' });
  await say('⏳ 5/5 Listo, revisando…');
  return { camp: camp.id, set: set.id, ad: ad.id, moneda: c.currency, intereses: ints.map((i) => i.name),
    url: `https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=${act.replace('act_', '')}&selected_campaign_ids=${camp.id}` };
}

export async function activar(ids) { for (const id of [ids.ad, ids.set, ids.camp]) await api('POST', id, { status: 'ACTIVE' }); }
export async function pausar(ids) { await api('POST', ids.camp, { status: 'PAUSED' }); }
export async function borrar(ids) { await api('DELETE', ids.camp, {}); }

/** Resumen de los últimos 7 días de una campaña. */
export async function resultados(campId) {
  const r = await api('GET', `${campId}/insights`, { fields: 'spend,impressions,reach,clicks,cpc,ctr,actions', date_preset: 'last_7d' });
  return r.data?.[0] || null;
}
