// Campaña de MI GRAN AVENTURA: tráfico a la ficha /p/mi-gran-aventura (allí se personaliza y se compra).
// Público: mamás y papás 24-45 de LatAm con intereses de crianza, preescolar y libros infantiles. Sin Audience Network.
// UN conjunto con 4 anuncios: el reel + las 3 imágenes neón (A "su nombre", B "menos pantallas", C "aprende jugando");
// Meta reparte el presupuesto hacia el que mejor funcione. Queda EN PAUSA salvo --activar.
// --pausar-habitos pausa la campaña del tracker de hábitos (Diego 11-nov: "cambiamos una por la otra").
// Antes, en el estudio:  python3 /pixelia/herramientas/aventura/reel.py --eleven   y   python3 /pixelia/herramientas/aventura/anuncios.py
// Uso: docker exec pixelia node --no-warnings /app/herramientas/aventura/campana.mjs [--usd 5] [--solo-ig] [--pausar-habitos] [--activar]
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
const DIR = path.join(path.dirname(config.paths.files), 'anuncios', 'mi-gran-aventura');
const reel = path.join(DIR, 'reel-aventura.mp4');
if (!fs.existsSync(reel)) throw new Error('Falta el reel: corre antes reel.py --eleven en el estudio');
for (const k of 'ABC') if (!fs.existsSync(path.join(DIR, `${k}-4x5.jpg`))) throw new Error('Faltan las imágenes: corre antes anuncios.py en el estudio');

if (A.includes('--pausar-habitos')) {
  const r = await api('GET', `${act}/campaigns`, { fields: 'name,effective_status', limit: 100 });
  for (const k of (r.data || []).filter((x) => x.effective_status === 'ACTIVE' && /h[aá]bitos/i.test(x.name) && !/reto/i.test(x.name))) {
    await api('POST', k.id, { status: 'PAUSED' }); console.log(`⏸️ Pausada: ${k.name}`);
  }
}

const PAISES = ['MX', 'CO', 'PE', 'CL', 'EC', 'VE', 'AR'];
const ints = (await idsIntereses(['Parenting', 'Preschool', 'Early childhood education', 'Toddler', "Children's literature", 'Coloring book', 'Homeschooling', 'Motherhood']))
  .filter((i, k, a) => a.findIndex((x) => x.id === i.id) === k);
const lugares = A.includes('--solo-ig') ? { publisher_platforms: ['instagram'], instagram_positions: ['stream', 'story', 'reels', 'explore_home', 'profile_feed'] } : ubicaciones();
const targeting = { geo_locations: { countries: PAISES }, age_min: 24, age_max: 45, targeting_automation: { advantage_audience: 0 },
  ...(ints.length ? { flexible_spec: [{ interests: ints }] } : {}), ...lugares };
console.log('🎯 Público: mamás y papás 24-45 · ' + PAISES.join(', ') + ' · ' + (ints.map((i) => i.name).join(', ') || 'sin intereses') + (A.includes('--solo-ig') ? ' · SOLO Instagram' : ''));

const PIE = '\n\n📩 Lo creas en 1 minuto y te llega al correo, listo para imprimir · $4.99 pago único\n🌎 Compra desde cualquier país';
const ANUNCIOS = [
  { letra: 'reel', titulo: 'Su nombre. Su aventura. 📚', texto: '¿Y si su tarea favorita fuera rescatar a su perrito? 🐶\n\nMi Gran Aventura es un libro de actividades con SU nombre, su compañero y su familia: 12 misiones de su edad (2 a 8 años) para aprender letras, números y lógica… sin pantallas ✏️\n\n🔊 Cada misión trae un QR: al terminarla, una voz lo felicita por su nombre.' + PIE },
  { letra: 'A', img: 'A-4x5.jpg', titulo: 'Un libro donde SU NOMBRE es el héroe', texto: '“¡Mamá, dice mi nombre!” 😍\n\nPones su nombre, su edad y su compañero de aventura… y se arma SU libro: portada, misiones y diploma con su nombre en cada página.' + PIE },
  { letra: 'B', img: 'B-4x5.jpg', titulo: 'Menos pantallas, más aventuras', texto: '¿Otra vez la tablet? 😩\n\nCámbiala por 12 misiones hechas para tu hijo: laberintos, letras, números y sombras… con su nombre y su perrito (o su dinosaurio 🦖).' + PIE },
  { letra: 'C', img: 'C-4x5.jpg', titulo: 'Aprende jugando, sin darse cuenta', texto: 'Trazos, letras con Ñ, números y lógica ✏️🔤🔢\n\nPero para tu hijo no es tarea: es SU aventura para rescatar a su compañero. Las actividades se eligen solas según su edad (2 a 8 años).' + PIE }];

const hoy = new Date().toISOString().slice(0, 10), nombre = `Pixelia · Mi Gran Aventura · ${hoy}`;
const link = `${base}/p/mi-gran-aventura?utm_source=meta&utm_campaign=aventura`;
console.log('⏫ Subiendo el reel a Meta (1-3 minutos)…');
const vid = await subirVideo(act, `${base}/media/anuncios/mi-gran-aventura/reel-aventura.mp4`, nombre);
const camp = await api('POST', `${act}/campaigns`, { name: nombre, objective: 'OUTCOME_TRAFFIC', status: 'PAUSED', special_ad_categories: [], buying_type: 'AUCTION', is_adset_budget_sharing_enabled: false });
const set = await api('POST', `${act}/adsets`, { name: `${nombre} · papás`, campaign_id: camp.id, status: 'PAUSED', billing_event: 'IMPRESSIONS', bid_strategy: 'LOWEST_COST_WITHOUT_CAP',
  daily_budget: Math.round(USD * 100), destination_type: 'WEBSITE', optimization_goal: 'LANDING_PAGE_VIEWS', targeting });
const actor = { page_id: page, ...(ig ? { instagram_user_id: ig } : {}) };
const ads = [];
for (const t of ANUNCIOS) {
  try {
    let spec;
    if (t.img) {
      const r = await api('POST', `${act}/adimages`, { bytes: fs.readFileSync(path.join(DIR, t.img)).toString('base64') });
      const hash = Object.values(r.images || {})[0]?.hash; if (!hash) throw new Error('no se subió la imagen');
      spec = { link_data: { image_hash: hash, link, message: t.texto, name: t.titulo, call_to_action: { type: 'SHOP_NOW', value: { link } } } };
    } else spec = { video_data: { video_id: vid.id, image_url: vid.thumb, message: t.texto, title: t.titulo, call_to_action: { type: 'SHOP_NOW', value: { link } } } };
    const cr = await api('POST', `${act}/adcreatives`, { name: `${nombre} · ${t.letra}`, object_story_spec: { ...actor, ...spec } });
    const ad = await api('POST', `${act}/ads`, { name: `${nombre} · ${t.letra}`, adset_id: set.id, creative: { creative_id: cr.id }, status: ACTIVAR ? 'ACTIVE' : 'PAUSED' });
    ads.push({ letra: t.letra, id: ad.id, nombre: t.img ? `imagen ${t.letra}` : 'reel' }); console.log(`✔ Anuncio ${t.letra} listo`);
  } catch (e) { console.log(`❌ Anuncio ${t.letra}: ${e.message}`); }
}
if (!ads.length) { await api('DELETE', camp.id, {}).catch(() => {}); throw new Error('No se pudo crear ningún anuncio; borré la campaña vacía.'); }
if (ACTIVAR) { await api('POST', set.id, { status: 'ACTIVE' }); await api('POST', camp.id, { status: 'ACTIVE' }); }

const F = path.join(path.dirname(config.paths.files), '..', 'data', 'campanas.json');
let cs = []; try { cs = JSON.parse(fs.readFileSync(F, 'utf8')); } catch {}
cs.push({ camp: camp.id, set: set.id, sets: [set.id], ads, titulo: '📚 Mi Gran Aventura', presupuesto: USD, estado: ACTIVAR ? 'activa' : 'pausada',
  fecha: new Date().toISOString(), modo: 'web', publico: { paises: PAISES, edad: '24-45', genero: 'todos', intereses: ints.map((x) => x.name) } });
fs.writeFileSync(F, JSON.stringify(cs.slice(-50), null, 1));
console.log(`\n✅ Campaña ${ACTIVAR ? 'ACTIVA' : 'creada EN PAUSA'}: $${USD}/día · 4 anuncios (reel + 3 imágenes) → ${link}`);
console.log(`https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=${act.replace('act_', '')}&selected_campaign_ids=${camp.id}`);
