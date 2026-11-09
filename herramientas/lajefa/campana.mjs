// Campaña de LA JEFA (lanzamiento): tráfico a la landing /jefa (demo gratis a cambio del correo → luego compra $4.99).
// Público: MUJERES 22-50 de LatAm con intereses de emprendimiento, repostería, uñas y negocio desde casa. Instagram + Facebook (sin Audience Network).
// 2 anuncios con el MISMO reel (versión anuncio) y textos A/B. $10/día por defecto. Queda EN PAUSA salvo --activar.
// Antes: docker exec pixelia-estudio python3 /pixelia/herramientas/lajefa/reel.py --anuncio
// Uso:   docker exec pixelia node --no-warnings /app/herramientas/lajefa/campana.mjs [--usd 10] [--activar]
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../../src/config.js';
import { api, idsIntereses, cuenta, ubicaciones, subirVideo } from '../../src/telegram/anuncios-meta.js';

const A = process.argv.slice(2), opt = (k, d) => (A.includes(k) ? A[A.indexOf(k) + 1] : d);
const USD = Number(opt('--usd', 10)), ACTIVAR = A.includes('--activar');
const env = (k) => process.env[k] || '';
const act = env('META_AD_ACCOUNT'), page = env('META_PAGE_ID'), ig = env('META_IG_ID');
if (!act || !page) throw new Error('Falta conectar Meta (cuenta publicitaria o página)');
const c = await cuenta(); if (c.account_status !== 1) throw new Error('La cuenta publicitaria no está activa');
const base = config.baseUrl.replace(/\/$/, '');
const archivo = path.join(path.dirname(config.paths.files), 'anuncios', 'la-jefa', 'reel-lajefa-anuncio.mp4');
if (!fs.existsSync(archivo)) throw new Error('Falta el reel: corre antes reel.py --anuncio en el estudio');

const PAISES = ['MX', 'CO', 'PE', 'CL', 'EC', 'VE'];
const ints = (await idsIntereses(['Entrepreneurship', 'Small business', 'Baking', 'Cake decorating', 'Nail art', 'Manicure', 'Self-employment', 'Home business']))
  .filter((i, k, a) => a.findIndex((x) => x.id === i.id) === k);
const targeting = { geo_locations: { countries: PAISES }, genders: [2], age_min: 22, age_max: 50, targeting_automation: { advantage_audience: 0 },
  ...(ints.length ? { flexible_spec: [{ interests: ints }] } : {}), ...ubicaciones() };
console.log('🎯 Público: mujeres 22-50 · ' + PAISES.join(', ') + ' · ' + (ints.map((i) => i.name).join(', ') || 'sin intereses'));

const TEXTOS = [
  { letra: 'A', titulo: 'Pruébala gratis 👑', texto: '¿Vendes postres, uñas o tienes tu tiendita? 🧁💅\nLa mayoría pone el precio "a ojo"… y pierde plata sin saberlo 😱\n\n👑 La Jefa te dice cuánto ganas DE VERDAD, te arma tus estados para WhatsApp y te ayuda a cobrar.\n\n🎁 Pruébala GRATIS (3 usos). Si te gusta: $4.99 de por vida.\n🌎 Compra desde cualquier país' },
  { letra: 'B', titulo: '¿Cuánto ganas de verdad?', texto: 'Jefa, ¿cuánto te queda de verdad en cada torta? 🎂\nSi no cuentas el gas, la cajita y tu tiempo… estás trabajando gratis 🙈\n\n👑 La Jefa: precio justo, lista de precios, estados bonitos, tus clientas y quién te debe. Todo en tu teléfono.\n\n🎁 Demo gratis aquí 👇 · luego $4.99 de por vida, sin mensualidad' }];

const hoy = new Date().toISOString().slice(0, 10), nombre = `Pixelia · La Jefa · lanzamiento · ${hoy}`;
const link = `${base}/jefa?utm_source=meta&utm_campaign=lajefa`;
console.log('⏫ Subiendo el reel a Meta (1-3 minutos)…');
const vid = await subirVideo(act, `${base}/media/anuncios/la-jefa/reel-lajefa-anuncio.mp4`, nombre);
const camp = await api('POST', `${act}/campaigns`, { name: nombre, objective: 'OUTCOME_TRAFFIC', status: 'PAUSED', special_ad_categories: [], buying_type: 'AUCTION', is_adset_budget_sharing_enabled: false });
const set = await api('POST', `${act}/adsets`, { name: `${nombre} · mujeres`, campaign_id: camp.id, status: 'PAUSED', billing_event: 'IMPRESSIONS', bid_strategy: 'LOWEST_COST_WITHOUT_CAP',
  daily_budget: Math.round(USD * 100), destination_type: 'WEBSITE', optimization_goal: 'LANDING_PAGE_VIEWS', targeting });
const actor = { page_id: page, ...(ig ? { instagram_user_id: ig } : {}) };
const ads = [];
for (const t of TEXTOS) {
  try {
    const cr = await api('POST', `${act}/adcreatives`, { name: `${nombre} · ${t.letra}`, object_story_spec: { ...actor,
      video_data: { video_id: vid.id, image_url: vid.thumb, message: t.texto, title: t.titulo, call_to_action: { type: 'LEARN_MORE', value: { link } } } } });
    const ad = await api('POST', `${act}/ads`, { name: `${nombre} · ${t.letra}`, adset_id: set.id, creative: { creative_id: cr.id }, status: ACTIVAR ? 'ACTIVE' : 'PAUSED' });
    ads.push({ letra: t.letra, id: ad.id, nombre: `reel + texto ${t.letra}` }); console.log(`✔ Anuncio ${t.letra} listo`);
  } catch (e) { console.log(`❌ Anuncio ${t.letra}: ${e.message}`); }
}
if (!ads.length) { await api('DELETE', camp.id, {}).catch(() => {}); throw new Error('No se pudo crear ningún anuncio; borré la campaña vacía.'); }
if (ACTIVAR) { await api('POST', set.id, { status: 'ACTIVE' }); await api('POST', camp.id, { status: 'ACTIVE' }); }

const F = path.join(path.dirname(config.paths.files), '..', 'data', 'campanas.json');
let cs = []; try { cs = JSON.parse(fs.readFileSync(F, 'utf8')); } catch {}
cs.push({ camp: camp.id, set: set.id, sets: [set.id], ads, titulo: '👑 La Jefa (lanzamiento)', presupuesto: USD, estado: ACTIVAR ? 'activa' : 'pausada',
  fecha: new Date().toISOString(), modo: 'web', publico: { paises: PAISES, edad: '22-50', genero: 'mujeres', intereses: ints.map((x) => x.name) } });
fs.writeFileSync(F, JSON.stringify(cs.slice(-50), null, 1));
console.log(`\n✅ Campaña ${ACTIVAR ? 'ACTIVA' : 'creada EN PAUSA'}: $${USD}/día · visitas a ${base}/jefa`);
if (!ACTIVAR) console.log('Para lanzarla: vuelve a correr con --activar… o actívala en el Administrador de anuncios:');
console.log(`https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=${act.replace('act_', '')}&selected_campaign_ids=${camp.id}`);
