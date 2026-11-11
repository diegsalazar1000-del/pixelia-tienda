// Campaña del PLAN FINANCIERO 2027: tráfico a la landing /plan. DOS conjuntos segmentados por género (Diego 11-nov):
// hombres → reel con el hombre + imágenes A y B; mujeres → reel de las amigas + imágenes A y C. Presupuesto repartido. Queda EN PAUSA salvo --activar.
// Antes: en el estudio  python3 /pixelia/herramientas/plan2027/musica.py   (reels con música) y el producto registrado (herramientas/plan2027.mjs --publicar).
// Uso: docker exec pixelia node --no-warnings /app/herramientas/plan2027/campana.mjs [--usd 5] [--solo-ig] [--activar]
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../../src/config.js';
import { api, idsIntereses, cuenta, ubicaciones, subirVideo } from '../../src/telegram/anuncios-meta.js';

const A = process.argv.slice(2), opt = (k, d) => (A.includes(k) ? A[A.indexOf(k) + 1] : d);
const USD = Number(opt('--usd', 5)), ACTIVAR = A.includes('--activar');
const act = process.env.META_AD_ACCOUNT || '', page = process.env.META_PAGE_ID || '', ig = process.env.META_IG_ID || '';
if (!act || !page) throw new Error('Falta conectar Meta (cuenta publicitaria o página)');
const c = await cuenta(); if (c.account_status !== 1) throw new Error('La cuenta publicitaria no está activa');
const base = config.baseUrl.replace(/\/$/, '');
const DIR = path.join(path.dirname(config.paths.files), 'anuncios', 'plan-financiero-2027');
const IMG = path.join(path.dirname(new URL(import.meta.url).pathname), 'anuncios');
for (const r of ['reel-hombre.mp4', 'reel-mujeres.mp4']) if (!fs.existsSync(path.join(DIR, r))) throw new Error('Faltan los reels con música: corre antes musica.py en el estudio');

const PAISES = ['MX', 'CO', 'PE', 'CL', 'EC', 'VE', 'AR'];
const ints = (await idsIntereses(['Personal finance', 'Budget', 'Saving', 'Money management', 'Financial literacy', 'Debt']))
  .filter((i, k, a) => a.findIndex((x) => x.id === i.id) === k);
const lugares = A.includes('--solo-ig') ? { publisher_platforms: ['instagram'], instagram_positions: ['stream', 'story', 'reels', 'explore_home', 'profile_feed'] } : ubicaciones();
const tg = (g) => ({ geo_locations: { countries: PAISES }, age_min: 22, age_max: 50, genders: [g], targeting_automation: { advantage_audience: 0 },
  ...(ints.length ? { flexible_spec: [{ interests: ints }] } : {}), ...lugares });
console.log('🎯 Público: 22-50 · ' + PAISES.join(', ') + ' · ' + (ints.map((i) => i.name).join(', ') || 'sin intereses'));

const PIE = '\n\n📊 Lo haces en 1 minuto y te llega al correo en Excel y Google Sheets · $3.99 pago único\n🌎 Desde cualquier país, con tu moneda';
const GRUPOS = [
  { nom: 'hombres', g: 1, reel: 'reel-hombre.mp4', anuncios: [
    { letra: 'reel', titulo: 'Tu plan 2027 en 1 minuto 📊', texto: '¿Cobras y a los pocos días no sabes en qué se te fue? 😩\n\nEscribe a qué te dedicas y cuánto ganas, y te armamos tu plan de los 12 meses: cuánto gastar, cuánto ahorrar y en qué mes cumples tu meta.' + PIE },
    { letra: 'A', img: 'A-4x5.jpg', titulo: '¿Cuánto puedes ahorrar con lo que ganas?', texto: 'Ganas $500 → ahorras $61 al mes → tu fondo de emergencia listo en octubre ✅\n\nPon tus números y mira tu plan del año.' + PIE },
    { letra: 'B', img: 'B-4x5.jpg', titulo: 'No es que ganes poco', texto: '¿Cobras y a los 15 días ya no te queda nada? 😩\n\nNo es que ganes poco: es que nadie te enseñó a repartirlo. Tu plan te lo dice mes a mes.' + PIE }] },
  { nom: 'mujeres', g: 2, reel: 'reel-mujeres.mp4', anuncios: [
    { letra: 'reel', titulo: 'Tu plan 2027 en 1 minuto 📊', texto: '"Amiga, ¿cómo hiciste para llegar a fin de mes sin deudas?" 😳\n\nCon un plan hecho con TUS números: cuánto gastar, cuánto ahorrar, cuánto apartar para diciembre y en qué mes cumples tu meta.' + PIE },
    { letra: 'A', img: 'A-4x5.jpg', titulo: '¿Cuánto puedes ahorrar con lo que ganas?', texto: 'Ganas $500 → ahorras $61 al mes → tu fondo de emergencia listo en octubre ✅\n\nPon tus números y mira tu plan del año.' + PIE },
    { letra: 'C', img: 'C-4x5.jpg', titulo: 'El mensaje que todas quieren mandar 👀', texto: '¿Cómo hizo para llegar a fin de mes sin deudas? Se hizo un plan 🙌\n\nPones lo que ganas y te dice cuánto gastar y cuánto guardar, mes a mes.' + PIE }] }];

const hoy = new Date().toISOString().slice(0, 10), nombre = `Pixelia · Plan financiero 2027 · ${hoy}`;
const link = `${base}/plan?utm_source=meta&utm_campaign=plan2027`;
const camp = await api('POST', `${act}/campaigns`, { name: nombre, objective: 'OUTCOME_TRAFFIC', status: 'PAUSED', special_ad_categories: [], buying_type: 'AUCTION', is_adset_budget_sharing_enabled: false });
const actor = { page_id: page, ...(ig ? { instagram_user_id: ig } : {}) };
const ads = [], sets = [];
for (const G of GRUPOS) {
  console.log(`⏫ Subiendo el reel de ${G.nom} (1-3 minutos)…`);
  const vid = await subirVideo(act, `${base}/media/anuncios/plan-financiero-2027/${G.reel}`, `${nombre} · ${G.nom}`);
  const set = await api('POST', `${act}/adsets`, { name: `${nombre} · ${G.nom}`, campaign_id: camp.id, status: 'PAUSED', billing_event: 'IMPRESSIONS', bid_strategy: 'LOWEST_COST_WITHOUT_CAP',
    daily_budget: Math.round(USD * 50), destination_type: 'WEBSITE', optimization_goal: 'LANDING_PAGE_VIEWS', targeting: tg(G.g) });
  sets.push(set.id);
  for (const t of G.anuncios) {
    try {
      let spec;
      if (t.img) {
        const r = await api('POST', `${act}/adimages`, { bytes: fs.readFileSync(path.join(IMG, t.img)).toString('base64') });
        const hash = Object.values(r.images || {})[0]?.hash; if (!hash) throw new Error('no se subió la imagen');
        spec = { link_data: { image_hash: hash, link, message: t.texto, name: t.titulo, call_to_action: { type: 'LEARN_MORE', value: { link } } } };
      } else spec = { video_data: { video_id: vid.id, image_url: vid.thumb, message: t.texto, title: t.titulo, call_to_action: { type: 'LEARN_MORE', value: { link } } } };
      const cr = await api('POST', `${act}/adcreatives`, { name: `${nombre} · ${G.nom} · ${t.letra}`, object_story_spec: { ...actor, ...spec } });
      const ad = await api('POST', `${act}/ads`, { name: `${nombre} · ${G.nom} · ${t.letra}`, adset_id: set.id, creative: { creative_id: cr.id }, status: ACTIVAR ? 'ACTIVE' : 'PAUSED' });
      ads.push({ letra: `${G.nom}-${t.letra}`, id: ad.id, nombre: `${G.nom} · ${t.img ? 'imagen ' + t.letra : 'reel'}` }); console.log(`✔ ${G.nom}: anuncio ${t.letra} listo`);
    } catch (e) { console.log(`❌ ${G.nom} ${t.letra}: ${e.message}`); }
  }
  if (ACTIVAR) await api('POST', set.id, { status: 'ACTIVE' });
}
if (!ads.length) { await api('DELETE', camp.id, {}).catch(() => {}); throw new Error('No se pudo crear ningún anuncio; borré la campaña vacía.'); }
if (ACTIVAR) await api('POST', camp.id, { status: 'ACTIVE' });

const F = path.join(path.dirname(config.paths.files), '..', 'data', 'campanas.json');
let cs = []; try { cs = JSON.parse(fs.readFileSync(F, 'utf8')); } catch {}
cs.push({ camp: camp.id, set: sets[0], sets, ads, titulo: '📊 Plan financiero 2027', presupuesto: USD, estado: ACTIVAR ? 'activa' : 'pausada',
  fecha: new Date().toISOString(), modo: 'web', publico: { paises: PAISES, edad: '22-50', genero: 'hombres y mujeres por separado', intereses: ints.map((x) => x.name) } });
fs.writeFileSync(F, JSON.stringify(cs.slice(-50), null, 1));
console.log(`\n✅ Campaña ${ACTIVAR ? 'ACTIVA' : 'creada EN PAUSA'}: $${USD}/día ($${USD / 2} hombres + $${USD / 2} mujeres) → ${link}`);
console.log(`https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=${act.replace('act_', '')}&selected_campaign_ids=${camp.id}`);
