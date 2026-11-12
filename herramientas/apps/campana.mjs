// 🧰 Herramientas gratis de Pixelia (12-nov): carrusel de 4 láminas → /apps, /racha, /dinero, /invitacion.
// --publicar: sube el carrusel al perfil de Instagram (orgánico).  Campaña: tráfico, PÚBLICO ABIERTO (sin intereses), 18-55,
// todos los países latinos, 18-45, $3/día repartidos en 2 conjuntos (Instagram $1.50 + Facebook $1.50), cada tarjeta lleva a SU app. Queda EN PAUSA salvo --activar.
// Uso: docker exec pixelia node --no-warnings /app/herramientas/apps/campana.mjs [--publicar] [--usd 3] [--activar] [--sin-campana]
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../../src/config.js';
import { api, cuenta } from '../../src/telegram/anuncios-meta.js';
import { G, call } from '../../src/telegram/redes.js';

const A = process.argv.slice(2), opt = (k, d) => (A.includes(k) ? A[A.indexOf(k) + 1] : d);
const USD = Number(opt('--usd', 3)), ACTIVAR = A.includes('--activar'), EDAD = [18, Number(opt('--edad-max', 45))];
const base = config.baseUrl.replace(/\/$/, '');
const dirImg = path.join(config.paths.public, 'img', 'apps');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const CAPTION = `✨ 3 mini apps que puedes usar GRATIS 👇

🔥 Mi Racha de 30 días: elige tu hábito y no rompas la racha
💸 Mi mes en dinero: cuánto entró, cuánto gastaste y en qué se te fue
💌 Tu invitación bonita: asado, cumple o reunión, directo a WhatsApp

Sin registrarte y sin descargar nada 🙌
👉 pixeliadigital.app/apps (enlace en el perfil)

Guárdalo para cuando lo necesites 📌

#apps #gratis #habitos #finanzaspersonales #ahorro #invitaciones #productividad #pixelia`;

const TARJETAS = [
  { img: 'c1.jpg', ruta: '/apps', titulo: '3 mini apps GRATIS ✨', desc: 'Sin registrarte' },
  { img: 'c2.jpg', ruta: '/racha', titulo: '🔥 Mi Racha de 30 días', desc: 'Gratis' },
  { img: 'c3.jpg', ruta: '/dinero', titulo: '💸 Mi mes en dinero', desc: 'Gratis' },
  { img: 'c4.jpg', ruta: '/invitacion', titulo: '💌 Tu invitación bonita', desc: 'Gratis' },
];

// 1) Carrusel orgánico en Instagram
if (A.includes('--publicar')) {
  const ig = process.env.META_IG_ID; if (!ig) throw new Error('Falta META_IG_ID');
  console.log('📸 Publicando el carrusel en Instagram…');
  const hijos = [];
  for (const t of TARJETAS) hijos.push((await call('POST', `${G}/${ig}/media`, { image_url: `${base}/img/apps/${t.img}`, is_carousel_item: 'true' })).id);
  const c = await call('POST', `${G}/${ig}/media`, { media_type: 'CAROUSEL', children: hijos.join(','), caption: CAPTION });
  for (let i = 0; i < 20; i++) { const s = await call('GET', `${G}/${c.id}`, { fields: 'status_code' }).catch(() => ({})); if (s.status_code === 'FINISHED') break; if (s.status_code === 'ERROR') throw new Error('Instagram no pudo procesar el carrusel'); await sleep(3000); }
  const p = await call('POST', `${G}/${ig}/media_publish`, { creation_id: c.id });
  console.log('✅ Carrusel publicado en Instagram: ' + p.id);
}

// 2) Campaña (anuncio carrusel, cada tarjeta a su app)
if (!A.includes('--sin-campana')) {
  const act = process.env.META_AD_ACCOUNT || '', page = process.env.META_PAGE_ID || '', ig = process.env.META_IG_ID || '';
  if (!act || !page) throw new Error('Falta conectar Meta (cuenta publicitaria o página)');
  const cu = await cuenta(); if (cu.account_status !== 1) throw new Error('La cuenta publicitaria no está activa');
  const PAISES = ['MX', 'CO', 'PE', 'CL', 'EC', 'VE', 'AR', 'UY', 'PY', 'BO', 'GT', 'DO', 'CR', 'PA', 'SV', 'HN', 'NI'];
  const hoy = new Date().toISOString().slice(0, 10), nombre = `Pixelia · 3 apps gratis · ${hoy}`;
  const utm = (r) => `${base}${r}?utm_source=meta&utm_campaign=apps`;
  const cards = [];
  for (const t of TARJETAS) {
    const r = await api('POST', `${act}/adimages`, { bytes: fs.readFileSync(path.join(dirImg, t.img)).toString('base64') });
    const hash = Object.values(r.images || {})[0]?.hash; if (!hash) throw new Error('no se subió ' + t.img);
    cards.push({ image_hash: hash, link: utm(t.ruta), name: t.titulo, description: t.desc, call_to_action: { type: 'LEARN_MORE', value: { link: utm(t.ruta) } } });
  }
  // limpia intentos anteriores que quedaron vacíos (sin conjuntos)
  const viejas = await api('GET', `${act}/campaigns`, { fields: 'id,name,adsets.limit(1){id}', limit: 50 }).catch(() => ({ data: [] }));
  for (const v of viejas.data || []) if (v.name.startsWith('Pixelia · 3 apps gratis') && !(v.adsets && v.adsets.data && v.adsets.data.length)) { await api('DELETE', v.id, {}).catch(() => {}); console.log('🧹 Borré una campaña vacía de un intento anterior'); }
  const camp = await api('POST', `${act}/campaigns`, { name: nombre, objective: 'OUTCOME_TRAFFIC', status: 'PAUSED', special_ad_categories: [], buying_type: 'AUCTION', is_adset_budget_sharing_enabled: false });
  // 2 conjuntos (Diego 12-nov): Instagram y Facebook por separado, mitad del presupuesto cada uno → se ve cuál rinde más
  const msg = CAPTION.replace('(enlace en el perfil)', '').replace(/\n\n#.*$/s, '');
  const cr = await api('POST', `${act}/adcreatives`, { name: `${nombre} · carrusel`, object_story_spec: { page_id: page, ...(ig ? { instagram_user_id: ig } : {}),
    link_data: { link: utm('/apps'), message: msg, child_attachments: cards, multi_share_optimized: false, multi_share_end_card: false } } });
  const LUGARES = [
    { nom: 'Instagram', p: { publisher_platforms: ['instagram'], instagram_positions: ['stream', 'story', 'explore_home', 'profile_feed'] } },
    { nom: 'Facebook', p: { publisher_platforms: ['facebook'], facebook_positions: ['feed', 'story'] } }];
  const sets = [], ads = [];
  try { for (const L of LUGARES) {
    const set = await api('POST', `${act}/adsets`, { name: `${nombre} · ${L.nom}`, campaign_id: camp.id, status: 'PAUSED', billing_event: 'IMPRESSIONS', bid_strategy: 'LOWEST_COST_WITHOUT_CAP',
      daily_budget: Math.round(USD * 100 / LUGARES.length), destination_type: 'WEBSITE', optimization_goal: 'LANDING_PAGE_VIEWS',
      targeting: { geo_locations: { countries: PAISES }, age_min: EDAD[0], age_max: EDAD[1], targeting_automation: { advantage_audience: 0 }, ...L.p } });
    const ad = await api('POST', `${act}/ads`, { name: `${nombre} · ${L.nom}`, adset_id: set.id, creative: { creative_id: cr.id }, status: ACTIVAR ? 'ACTIVE' : 'PAUSED' });
    if (ACTIVAR) await api('POST', set.id, { status: 'ACTIVE' });
    sets.push(set.id); ads.push({ letra: L.nom, id: ad.id, nombre: 'carrusel · ' + L.nom }); console.log(`✔ Conjunto ${L.nom}: $${(USD / LUGARES.length).toFixed(2)}/día`);
  } } catch (e) { if (!sets.length) await api('DELETE', camp.id, {}).catch(() => {}); throw e; }
  if (ACTIVAR) await api('POST', camp.id, { status: 'ACTIVE' });
  const F = path.join(path.dirname(config.paths.files), '..', 'data', 'campanas.json');
  let cs = []; try { cs = JSON.parse(fs.readFileSync(F, 'utf8')); } catch {}
  cs.push({ camp: camp.id, set: sets[0], sets, ads, titulo: '🧰 3 apps gratis', presupuesto: USD,
    estado: ACTIVAR ? 'activa' : 'pausada', fecha: new Date().toISOString(), modo: 'web', publico: { paises: PAISES, edad: EDAD.join('-'), genero: 'todos', intereses: [], lugares: 'Instagram y Facebook por separado' } });
  fs.writeFileSync(F, JSON.stringify(cs.slice(-50), null, 1));
  console.log(`\n✅ Campaña ${ACTIVAR ? 'ACTIVA' : 'creada EN PAUSA'}: $${USD}/día ($${USD / 2} Instagram + $${USD / 2} Facebook) · público abierto ${EDAD.join('-')} · ${PAISES.length} países latinos`);
  console.log(`https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=${act.replace('act_', '')}&selected_campaign_ids=${camp.id}`);
}
