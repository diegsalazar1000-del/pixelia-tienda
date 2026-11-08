// Promociona con la cuenta publicitaria de Pixelia (la conexión del bot, SIN poner pago en la app de Instagram) los reels del
// Reto 30 Días que ya están publicados en Instagram. Objetivo: VISITAS AL PERFIL de Instagram (ganar seguidores).
// Si Meta todavía no habilita "visitas al perfil" por API para la cuenta, lo arma como visitas a pixeliadigital.app/reto.
// Público: LatAm 20-45, intereses de productividad/hábitos, solo en Instagram. $1/día durante 3 días (≈ $3). Queda ACTIVA.
// Uso: docker exec pixelia node --no-warnings /app/herramientas/reto30/promocionar.mjs [--dias 3] [--usd 1] [--pausada]
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../../src/config.js';
import { api, idsIntereses, cuenta } from '../../src/telegram/anuncios-meta.js';
import { igRecientes, call, G } from '../../src/telegram/redes.js';

const A = process.argv.slice(2), opt = (k, d) => (A.includes(k) ? A[A.indexOf(k) + 1] : d);
const DIAS = Number(opt('--dias', 3)), USD = Number(opt('--usd', 1)), ESTADO = A.includes('--pausada') ? 'PAUSED' : 'ACTIVE';
const env = (k) => process.env[k] || '';
const act = env('META_AD_ACCOUNT'), page = env('META_PAGE_ID'), ig = env('META_IG_ID');
if (!act || !page || !ig) throw new Error('Falta conectar Meta (cuenta publicitaria, página o Instagram)');
const c = await cuenta(); if (c.account_status !== 1) throw new Error('La cuenta publicitaria no está activa');

// 1) Los reels del Reto que están publicados ahora mismo
const reels = (await igRecientes(30)).filter((m) => /#reto30dias/i.test(m.caption || '') && m.media_product_type === 'REELS');
if (!reels.length) throw new Error('No encuentro reels publicados del Reto (#reto30dias)');
const { username = 'pixelia.digitalstore' } = await call('GET', `${G}/${ig}`, { fields: 'username' }).catch(() => ({}));
console.log(`📌 Reels a promocionar: ${reels.length} (${reels.map((r) => r.permalink).join(' , ')})`);

// 2) Público
const PAISES = ['VE', 'CO', 'MX', 'PE', 'CL', 'AR', 'EC'];
const ints = await idsIntereses(['Productivity', 'Personal development', 'Goal setting', 'Habit', 'Self-improvement', 'Motivation']);
const targeting = { geo_locations: { countries: PAISES }, age_min: 20, age_max: 45, targeting_automation: { advantage_audience: 0 },
  ...(ints.length ? { flexible_spec: [{ interests: ints }] } : {}),
  publisher_platforms: ['instagram'], instagram_positions: ['stream', 'story', 'reels', 'explore_home', 'profile_feed'] };
console.log('🎯 Público: ' + PAISES.join(', ') + ' · 20-45 · ' + (ints.map((i) => i.name).join(', ') || 'sin intereses'));

const hoy = new Date().toISOString().slice(0, 10), nombre = `Pixelia · Reto 30 Días · seguidores · ${hoy}`;
const fin = new Date(Date.now() + DIAS * 864e5).toISOString();
const camp = await api('POST', `${act}/campaigns`, { name: nombre, objective: 'OUTCOME_TRAFFIC', status: 'PAUSED', special_ad_categories: [], buying_type: 'AUCTION' });

// 3) Conjunto: visitas al perfil de Instagram (si Meta lo permite por API) o, si no, visitas a /reto
let modo = 'perfil', set;
try {
  set = await api('POST', `${act}/adsets`, { name: `${nombre} · perfil`, campaign_id: camp.id, status: 'PAUSED', billing_event: 'IMPRESSIONS', bid_strategy: 'LOWEST_COST_WITHOUT_CAP',
    daily_budget: Math.round(USD * 100), end_time: fin, destination_type: 'INSTAGRAM_PROFILE', optimization_goal: 'PROFILE_VISIT', promoted_object: { page_id: page }, targeting });
} catch (e) {
  console.log(`ℹ️ Meta no deja "visitas al perfil" por API en esta cuenta (${e.message}). Lo armo como visitas a la página del regalo.`);
  modo = 'web';
  set = await api('POST', `${act}/adsets`, { name: `${nombre} · /reto`, campaign_id: camp.id, status: 'PAUSED', billing_event: 'IMPRESSIONS', bid_strategy: 'LOWEST_COST_WITHOUT_CAP',
    daily_budget: Math.round(USD * 100), end_time: fin, destination_type: 'WEBSITE', optimization_goal: 'LANDING_PAGE_VIEWS', targeting });
}
const link = config.baseUrl.replace(/\/$/, '') + '/reto';
const cta = modo === 'perfil'
  ? { type: 'VIEW_INSTAGRAM_PROFILE', value: { link: `https://www.instagram.com/${username}`, app_link: `instagram://user?username=${username}` } }
  : { type: 'DOWNLOAD', value: { link } };

// 4) Un anuncio por reel (el reel publicado, con sus likes y comentarios)
const ads = [];
for (const [i, r] of reels.entries()) {
  try {
    const cr = await api('POST', `${act}/adcreatives`, { name: `${nombre} · reel ${i + 1}`, object_id: page, instagram_user_id: ig, source_instagram_media_id: r.id, call_to_action: cta });
    const ad = await api('POST', `${act}/ads`, { name: `${nombre} · reel ${i + 1}`, adset_id: set.id, creative: { creative_id: cr.id }, status: ESTADO });
    ads.push({ letra: String.fromCharCode(65 + i), id: ad.id, nombre: `reel ${i + 1}` }); console.log(`✔ Anuncio con el reel ${i + 1} listo`);
  } catch (e) { console.log(`❌ Reel ${i + 1}: ${e.message}`); }
}
if (!ads.length) { await api('DELETE', camp.id, {}).catch(() => {}); throw new Error('No se pudo crear ningún anuncio; borré la campaña vacía.'); }
if (ESTADO === 'ACTIVE') { await api('POST', set.id, { status: 'ACTIVE' }); await api('POST', camp.id, { status: 'ACTIVE' }); }

// 5) Guardarla con las demás para que /campanas y el reporte del lunes la muestren
const F = path.join(path.dirname(config.paths.files), '..', 'data', 'campanas.json');
let cs = []; try { cs = JSON.parse(fs.readFileSync(F, 'utf8')); } catch {}
cs.push({ camp: camp.id, set: set.id, sets: [set.id], ads, titulo: '🔥 Reto 30 Días (seguidores)', presupuesto: USD, estado: ESTADO === 'ACTIVE' ? 'activa' : 'pausada',
  fecha: new Date().toISOString(), modo, publico: { paises: PAISES, edad: '20-45', intereses: ints.map((x) => x.name) } });
fs.writeFileSync(F, JSON.stringify(cs.slice(-50), null, 1));
console.log(`\n✅ Campaña ${ESTADO === 'ACTIVE' ? 'ACTIVA' : 'en pausa'}: $${USD}/día durante ${DIAS} días (termina sola) · objetivo: ${modo === 'perfil' ? 'visitas al perfil de Instagram' : 'visitas a ' + link}`);
console.log(`Ver en el Administrador de anuncios: https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=${act.replace('act_', '')}&selected_campaign_ids=${camp.id}`);
