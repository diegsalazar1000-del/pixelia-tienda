// Bot del RADAR: la tienda escucha los botones 🛒 🛠️ ❌ que manda n8n (long polling, sin webhooks).
// Así n8n no necesita dirección pública: solo busca y avisa; la tienda ejecuta las decisiones.
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../config.js';
import { Products, Candidates, AdJobs } from '../db.js';
import { explorar } from './explorador.js';
import { redesListas, estadoRedes, publicarKit, igReel, fbVideo } from './redes.js';
import { startComentarios, ocultar, eliminar, revisarComentarios } from './comentarios.js';
import { adsListos, crearCampana, activar, pausar, borrar, resultados, interesesPara, PAISES, pausarAnuncio, cambiarPresupuesto, porAnuncio, crearPublicos, tamanos, crearSimilares, desgloseDinamico } from './anuncios-meta.js';
import { registrar, resumen, resumenTexto, recetasVariantes } from './aprendizaje.js';
import { startCalendario, leccion, onCalendario, estadoCalendario, marcarPublicado } from './calendario.js';
import { Subscribers, Orders } from '../db.js';

const esc = (s) => String(s ?? '').replace(/[&<>]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[ch]));
const parseC = (c) => c && { ...c, metrics: JSON.parse(c.metrics || '{}'), ai: JSON.parse(c.ai || '{}') };

/** Crea un producto en borrador (oculto) a partir de un candidato del radar. */
export function createDraft(candidate, extra = {}) {
  const c = parseC(candidate);
  if (c.product_id && Products.byId(c.product_id)) return Products.byId(c.product_id);
  const ai = { ...c.ai, ...extra };
  const title = String(ai.titulo || c.title).slice(0, 120);
  const base = title.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50) || 'producto';
  let slug = base; for (let i = 2; Products.bySlug(slug); i++) slug = `${base}-${i}`;
  const price = Number(ai.precio_sugerido) > 0 ? Number(ai.precio_sugerido) : 9.99;
  const product = Products.upsert({ slug, title, short: String(ai.frase_corta || '').slice(0, 200), description: String(ai.descripcion || c.snippet || ''),
    category: String(ai.categoria || 'General'), price_cents: Math.round(price * 100), compare_cents: Math.round(price * 2 * 100),
    stars: Math.ceil(price / 0.013), emoji: String(ai.emoji || '✨').slice(0, 4), color: '#7c5cff',
    license_type: ai.decision === 'buy' ? 'MRR' : 'Propio', license_note: `Radar #${c.id} · ${c.source} · ${c.url}`, active: 0, candidate_id: c.id });
  Candidates.update(c.id, { status: 'drafted', product_id: product.id });
  return product;
}

const token = () => config.radar.token;
async function rtg(method, params = {}) {
  const res = await fetch(`https://api.telegram.org/bot${token()}/${method}`, {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(params) });
  const data = await res.json();
  if (!data.ok) throw new Error(`Radar ${method}: ${data.description}`);
  return data.result;
}
const send = async (text) => {
  for (let i = 0; i < text.length; i += 3900)
    await rtg('sendMessage', { chat_id: config.telegram.adminChatId, text: text.slice(i, i + 3900), parse_mode: 'HTML', link_preview_options: { is_disabled: true } });
};

async function recreationPlan(c) {
  if (!config.anthropic.key) return '(Falta ANTHROPIC_API_KEY en la tienda: no pude generar el plan.)';
  const prompt = `Quiero crear mi PROPIA versión (original, no una copia) de este producto digital que está en tendencia, para venderla en español.
Datos: ${JSON.stringify({ fuente: c.source, titulo: c.title, texto: c.snippet, url: c.url, analisis: c.ai })}

Dame un plan práctico en español, en texto plano con viñetas (sin markdown con #), con estas partes:
1. CONCEPTO: nombre final, para quién es, qué problema resuelve, qué lo hace mejor que el original.
2. CONTENIDO EXACTO: lista de páginas/secciones/plantillas con lo que va en cada una (lo suficientemente detallado para producirlo).
3. CÓMO HACERLO: herramienta (Canva, Notion, Google Sheets, Word/PDF…), formato de entrega y tiempo estimado.
4. PORTADA: descripción de la portada y 3 mockups para las fotos de producto.
5. PRECIO y BONOS: precio, precio tachado y 1-2 bonos baratos de producir.
6. 3 ANUNCIOS para Meta: gancho de vídeo de 3 segundos, texto principal, titular.
No copies textos ni diseños del original; todo debe ser contenido nuevo. Sé concreto y completa las 6 partes (máximo unas 1.500 palabras).`;
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST', headers: { 'x-api-key': config.anthropic.key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
    body: JSON.stringify({ model: config.anthropic.model, max_tokens: 12000, messages: [{ role: 'user', content: prompt }] }) });
  const data = await res.json();
  if (!res.ok) throw new Error('IA: ' + (data.error?.message || res.status));
  return (data.content || []).map((b) => b.text || '').join('');
}

/** Ofrece crear anuncios de un producto recién publicado. */
export async function offerAds(p) {
  if (!token()) return;
  return rtg('sendMessage', { chat_id: config.telegram.adminChatId, parse_mode: 'HTML',
    text: `🚀 <b>Publicaste:</b> ${esc(p.title)}\n¿Creo los anuncios (imágenes + reel)?`,
    reply_markup: { inline_keyboard: [[{ text: '🎬 Crear anuncios', callback_data: `ad:${p.id}:` }], [{ text: '🎥 Prompt para Gemini', callback_data: `gem:${p.id}:` }]] } });
}

// Opciones compactas del anuncio en callback_data: "ad:<id>:v=f,g=reggaeton,s=neon,n=1,x=4"
const parseOpts = (s) => Object.fromEntries(String(s || '').split(',').filter(Boolean).map((kv) => kv.split('=')));
const packOpts = (o) => Object.entries(o).filter(([, x]) => x !== undefined && x !== null && x !== '').map(([k, x]) => `${k}=${x}`).join(',');

// ===== Selector combinable (voz + música + estilo) =====
export const GENRES = { ia: '🎲 La IA elige', reggaeton: 'Reggaetón', pop: 'Pop', trap: 'Trap', cumbia: 'Cumbia', electronica: 'Electrónica', lofi: 'Lo-fi', acustica: 'Acústica', base: 'Suave', 0: '🔇 Sin música' };
export const STYLES = { ia: '🎲 La IA elige', color: '🌈 Color', neon: '🌃 Neón', minimal: '🤍 Minimal', tiktok: '📱 TikTok' };
const FORMATS = { clasico: '✨ Clásico', conversacion: '💬 Chat', vida_real: '🎬 Video real', pantalla: '📱 Pantalla móvil', tutorial: '✍️ Cómo se usa', comedia: '😂 Comedia', comparacion: '🔀 Antes/después', lista: '🏆 Top 3' };
const VOICES = { ia: '🎲 IA', f: '👩 Mujer', m: '👨 Hombre', 0: '🔇 Sin voz' };
const MUSIC_DIR = path.join(path.dirname(config.paths?.files || path.resolve('storage/products')), 'musica');
const songs = (g) => { try { return fs.readdirSync(path.join(MUSIC_DIR, g)).filter((f) => /\.(mp3|wav|m4a|ogg|aac|flac)$/i.test(f)).length; } catch { return 0; } };

function pickerKb(pid, sel, sug = {}, full = false) {
  const mark = (on, txt, star) => `${on ? '✅ ' : ''}${txt}${star ? ' ⭐' : ''}`;
  sel = { ...sel }; delete sel.m;
  const btn = (k, val, txt) => ({ text: mark(String(sel[k]) === String(val), txt, String(sug[k]) === String(val)), callback_data: `sel:${pid}:${packOpts({ ...sel, [k]: val, m: full ? 1 : undefined })}` });
  const g = (x) => btn('g', x, GENRES[x] + (songs(x) ? ' 🎧' : ''));
  const principal = [
    ...(adsListos() ? [[{ text: '📊 Crear campaña con este reel', callback_data: `cp:${pid}:` }]] : []),
    ...(redesListas() ? [[{ text: '📤 Publicarlo en Instagram y Facebook', callback_data: `pr:${pid}:` }]] : []),
    [{ text: '🎲 Hacer otro reel distinto', callback_data: `ad:${pid}:${packOpts({ v: sel.v, g: sel.g, f: 'otro' })}` }],
  ];
  if (!full) return [...principal, [{ text: '⚙️ Más opciones (voz, música, estilo, tutorial, comedia…)', callback_data: `sel:${pid}:${packOpts({ ...sel, m: 1 })}` }]];
  return [
    ...principal,
    [{ text: '🎨 Reel diseñado (prueba)', callback_data: `ad:${pid}:${packOpts({ v: sel.v, g: sel.g, d: 1 })}` }],
    [{ text: '🎓 Tutorial', callback_data: `ad:${pid}:${packOpts({ v: sel.v, g: sel.g, s: sel.s, f: 'tutorial' })}` }, { text: '😂 Comedia', callback_data: `ad:${pid}:${packOpts({ v: sel.v, g: sel.g, s: sel.s, f: 'comedia' })}` }],
    [{ text: '📸 Con fotos de Pixabay', callback_data: `ad:${pid}:${packOpts({ v: sel.v, g: sel.g, s: sel.s, p: 1 })}` }, { text: '🎬 Prompt Gemini', callback_data: `gem:${pid}:` }],
    [{ text: '🧠 PRO (≈$0.25)', callback_data: `ad:${pid}:${packOpts({ v: sel.v, g: sel.g, s: sel.s, q: 1 })}` }, { text: '🧪 4 variantes', callback_data: `ad:${pid}:${packOpts({ v: sel.v, g: sel.g, x: 4 })}` }],
    [{ text: '— Voz —', callback_data: 'x:0' }], Object.entries(VOICES).map(([k, t]) => btn('v', k, t)),
    [{ text: '— Música —', callback_data: 'x:0' }], [g('ia')], ['reggaeton', 'pop', 'trap'].map(g), ['cumbia', 'electronica', 'lofi'].map(g), ['acustica', 'base', '0'].map(g),
    [{ text: '— Estilo —', callback_data: 'x:0' }], [btn('s', 'ia', STYLES.ia)], ['color', 'neon'].map((x) => btn('s', x, STYLES[x])), ['minimal', 'tiktok'].map((x) => btn('s', x, STYLES[x])),
    [{ text: `🎬 Reel nuevo con lo marcado: ${VOICES[sel.v] || ''} · ${GENRES[sel.g] || ''}`.slice(0, 60), callback_data: `ad:${pid}:${packOpts(sel)}` }],
    [{ text: '🔊 Solo cambiar voz/música del último reel', callback_data: `ad:${pid}:${packOpts({ v: sel.v, g: sel.g, a: 1 })}` }],
    [{ text: '🔁 Rehacer público, colores y textos (IA)', callback_data: `ad:${pid}:${packOpts({ ...sel, n: 1 })}` }],
    [{ text: '⬅️ Menos opciones', callback_data: `sel:${pid}:${packOpts(sel)}` }],
  ];
}

/** Mensaje para armar otra versión del anuncio combinando voz, música y estilo. */
const lastSug = new Map();  // sugerencias de la IA por producto (para marcar ⭐)
export async function sendAdPicker(p, sel = {}, sug = {}) {
  if (!token()) return;
  lastSug.set(p.id, sug);
  const lib = Object.keys(GENRES).filter((g) => songs(g)).map((g) => `${GENRES[g]} (${songs(g)})`).join(', ');
  return rtg('sendMessage', { chat_id: config.telegram.adminChatId, parse_mode: 'HTML',
    text: `🎛️ <b>¿Qué hacemos con este anuncio de ${esc(p.title)}?</b>\n📊 <b>Crear campaña</b>: te muestro exactamente qué se publica (A y B) antes de crearla.\n🎲 <b>Otro reel</b>: la IA hace uno distinto.\n⚙️ <b>Más opciones</b>: elegir voz, música, estilo, tutorial, comedia…`,
    reply_markup: { inline_keyboard: pickerKb(p.id, sel, sug) } });
}

// ===== Créditos de ElevenLabs =====
async function creditos() {
  const key = process.env.ELEVENLABS_API_KEY;
  if (!key) return send('No hay clave de ElevenLabs configurada.');
  try {
    const r = await fetch('https://api.elevenlabs.io/v1/user/subscription', { headers: { 'xi-api-key': key } });
    const j = await r.json();
    if (!r.ok) return send(`No pude leer los créditos (${esc(j.detail?.message || j.detail?.status || r.status)}).\nSi dice "missing permissions", en ElevenLabs edita la clave y activa <b>User → Read</b>. Mientras, míralos en elevenlabs.io (barra "Credits used").`);
    const used = j.character_count || 0, lim = j.character_limit || 0, left = Math.max(0, lim - used);
    const reset = j.next_character_count_reset_unix ? new Date(j.next_character_count_reset_unix * 1000).toLocaleDateString('es') : '—';
    const ahorro = fs.existsSync(path.join(path.dirname(MUSIC_DIR), 'ahorro'));
    return send(`🎙️ <b>ElevenLabs</b> · plan ${esc(j.tier || '')}\nGastados: <b>${used.toLocaleString('es')}</b> de ${lim.toLocaleString('es')} (${lim ? Math.round(used / lim * 100) : 0}%)\nQuedan: <b>${left.toLocaleString('es')}</b> ≈ ${Math.floor(left / 180)} reels con voz nueva\nSe renuevan: ${reset}\nModo ahorro: ${ahorro ? '🟢 activado' : '⚪ desactivado'}`);
  } catch (e) { return send('No pude consultar ElevenLabs: ' + esc(e.message)); }
}

// ===== 🧬 Fusionar ideas del radar =====
const fusions = new Map();  // propuestas recientes (token → propuesta)
const slugify = (t) => String(t).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50) || 'producto';
const freeSlug = (t) => { const b = slugify(t); let s = b; for (let i = 2; Products.bySlug(s); i++) s = `${b}-${i}`; return s; };

async function askJson(prompt, maxTokens = 6000) {
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST', headers: { 'x-api-key': config.anthropic.key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
    body: JSON.stringify({ model: process.env.FUSION_MODEL || 'claude-sonnet-5-5', max_tokens: maxTokens, messages: [{ role: 'user', content: prompt }] }) });
  const data = await res.json();
  if (!res.ok) throw new Error('IA: ' + (data.error?.message || res.status));
  const t = (data.content || []).map((b) => b.text || '').join('').replace(/```json|```/g, '');
  return JSON.parse(t.slice(t.indexOf('{'), t.lastIndexOf('}') + 1));
}

async function fuse() {
  if (!config.anthropic.key) return send('Falta ANTHROPIC_API_KEY en la tienda.');
  const pool = Candidates.list('', 200).map(parseC)
    .filter((c) => !['discarded', 'retired'].includes(c.status) && (c.ai_score || 0) >= 5).slice(0, 45)
    .map((c) => ({ id: c.id, fuente: c.source, titulo: c.title.slice(0, 110), nota: c.ai_score, idea: String(c.ai?.idea || c.ai?.nicho || c.ai?.resumen || c.snippet || '').slice(0, 160) }));
  if (pool.length < 3) return send('Todavía hay pocos productos en el radar para fusionar (mínimo 3 con nota ≥ 5). Espera unos días de búsquedas.');
  const mine = Products.list().filter((p) => !p.bundle_ids).map((p) => p.title);
  await send(`🧬 Analizando ${pool.length} productos del radar para combinarlos… (1 min)`);
  const out = await askJson(`Eres estratega de productos digitales para una tienda en español (Latinoamérica) que vende productos a $4.99 y packs de 3 a $9.99.
Productos en tendencia que encontró el radar:
${JSON.stringify(pool)}
Productos que la tienda YA vende: ${JSON.stringify(mine)}

Propón 3 ideas, cada una de uno de estos tipos:
- "fusion": UN producto nuevo y mejor que combina lo mejor de 2-3 productos de la lista (para el mismo público).
- "pack": 3 productos que se complementan para el MISMO público (pueden incluir alguno que la tienda ya vende), para vender a $4.99 cada uno o los 3 a $9.99.
Todo debe ser contenido ORIGINAL (inspirado en la idea, nunca copiar diseños ni textos). Productos que se puedan fabricar como PDF, planner, plantillas, hojas de cálculo o guías.
Devuelve SOLO JSON:
{"propuestas":[{"tipo":"fusion|pack","nombre":"nombre comercial","publico":"para quién","por_que":"por qué va a vender (1-2 frases)","basado_en":[ids del radar],
"productos":[{"titulo":"...","emoji":"1 emoji","frase_corta":"máx 90 caracteres","descripcion":"qué incluye, en 4-6 viñetas","contenido":"lista de páginas/secciones para fabricarlo","ya_existe":false}],
"precio_pack":9.99}]}
En "fusion" pon 1 producto en "productos"; en "pack" pon 3 (marca "ya_existe": true si es uno que la tienda ya vende, con su título exacto).`);
  const props = (out.propuestas || []).slice(0, 3);
  if (!props.length) return send('La IA no devolvió propuestas. Prueba de nuevo con /fusionar.');
  for (const p of props) {
    const tok = Math.random().toString(36).slice(2, 10); fusions.set(tok, p);
    if (fusions.size > 60) fusions.delete(fusions.keys().next().value);
    const items = (p.productos || []).map((x) => `${esc(x.emoji || '✨')} <b>${esc(x.titulo)}</b>${x.ya_existe ? ' <i>(ya lo vendes)</i>' : ''}\n   ${esc(x.frase_corta || '')}`).join('\n');
    await rtg('sendMessage', { chat_id: config.telegram.adminChatId, parse_mode: 'HTML', link_preview_options: { is_disabled: true },
      text: `${p.tipo === 'pack' ? '📦 <b>PACK</b>' : '🧬 <b>FUSIÓN</b>'}: <b>${esc(p.nombre)}</b>\n👥 ${esc(p.publico)}\n💡 ${esc(p.por_que)}\n\n${items}${p.tipo === 'pack' ? `\n\n💰 $4.99 c/u · los 3 por $${Number(p.precio_pack || 9.99).toFixed(2)}` : '\n\n💰 $4.99'}\n🔎 Basado en radar #${(p.basado_en || []).join(', #')}`,
      reply_markup: { inline_keyboard: [[{ text: '🛠️ Crear borradores + plan', callback_data: `fz:ok:${tok}` }, { text: '❌ No', callback_data: `fz:no:${tok}` }]] } });
  }
}

async function createFusion(p) {
  const created = [];
  for (const x of p.productos || []) {
    if (x.ya_existe) { const ex = Products.list({ all: true }).find((q) => q.title.toLowerCase() === String(x.titulo).toLowerCase()); if (ex) { created.push(ex); continue; } }
    created.push(Products.upsert({ slug: freeSlug(x.titulo), title: String(x.titulo).slice(0, 120), short: String(x.frase_corta || '').slice(0, 200),
      description: String(x.descripcion || ''), category: 'General', price_cents: 499, compare_cents: 999, stars: Math.ceil(4.99 / 0.013),
      emoji: String(x.emoji || '✨').slice(0, 4), color: '#7c5cff', license_type: 'Propio', license_note: `Fusión del radar #${(p.basado_en || []).join(', #')}`, active: 0 }));
  }
  let pack = null;
  if (p.tipo === 'pack' && created.length >= 2) {
    pack = Products.upsert({ slug: freeSlug('pack ' + p.nombre), title: String(p.nombre).slice(0, 120), short: `Los ${created.length} juntos con descuento`,
      description: created.map((c) => `• ${c.emoji} ${c.title}`).join('\n'), category: 'Packs', price_cents: Math.round(Number(p.precio_pack || 9.99) * 100),
      compare_cents: created.reduce((t, c) => t + c.price_cents, 0), stars: Math.ceil(Number(p.precio_pack || 9.99) / 0.013), emoji: '📦', color: '#ff4fa3',
      license_type: 'Propio', bundle_ids: created.map((c) => c.id).join(','), active: 0 });
  }
  for (const id of p.basado_en || []) { const c = Candidates.get(id); if (c && ['new', 'notified'].includes(c.status)) Candidates.update(id, { status: 'recreate' }); }
  // plan de fabricación de cada producto nuevo
  const nuevos = (p.productos || []).filter((x) => !x.ya_existe);
  const plan = await askJson(`Para cada producto digital, escribe un plan de fabricación concreto en español (texto plano, sin markdown):
${JSON.stringify(nuevos.map((x) => ({ titulo: x.titulo, publico: p.publico, contenido: x.contenido, descripcion: x.descripcion })))}
Devuelve SOLO JSON: {"planes":[{"titulo":"...","plan":"1) Páginas exactas y qué va en cada una 2) Estilo visual (colores, tipografía) 3) Formato (PDF tablet/móvil, imprimible…) 4) Bono barato 5) Gancho de anuncio"}]}`, 8000).catch((e) => ({ planes: [], error: e.message }));
  return { created, pack, plan };
}
// ===== Biblioteca de música real (canciones libres de derechos enviadas al bot) =====
const GENRE_ALIAS = { reggaeton: 'reggaeton', 'reggaetón': 'reggaeton', regueton: 'reggaeton', pop: 'pop', trap: 'trap', cumbia: 'cumbia',
  electronica: 'electronica', 'electrónica': 'electronica', edm: 'electronica', house: 'electronica', lofi: 'lofi', 'lo-fi': 'lofi',
  acustica: 'acustica', 'acústica': 'acustica', acustico: 'acustica', 'acústico': 'acustica', suave: 'base', base: 'base' };
const MUSIC_HELP = `🎵 <b>Música real para los anuncios</b>
Es automático: cuando un género tiene menos de 3 canciones, el estudio busca canciones reales con licencia para uso comercial y te manda un pedacito del coro. Tú solo tocas ✅ Usar o ❌ Descartar.

• <code>/musica buscar reggaeton</code> — pedir sugerencias ya (géneros: reggaeton, pop, trap, cumbia, electronica, lofi, acustica, suave)
• También puedes enviarme un MP3 libre de derechos con el género en el pie.

Además, cada anuncio trae una versión <b>sin música</b> para que Meta le ponga una canción de su biblioteca automáticamente.`;

async function saveSong(m) {
  const f = m.audio || m.document;
  const genre = GENRE_ALIAS[String(m.caption || '').trim().toLowerCase().split(/\s+/)[0]];
  if (!genre) return send(`¿De qué género es esta canción? Reenvíamela escribiendo en el pie uno de: reggaeton, pop, trap, cumbia, electronica, lofi, acustica, suave.`);
  if (f.file_size > 20e6) return send('El archivo pesa más de 20 MB; Telegram no me deja bajarlo. Usa un MP3 más liviano.');
  const info = await rtg('getFile', { file_id: f.file_id });
  const r = await fetch(`https://api.telegram.org/file/bot${token()}/${info.file_path}`);
  if (!r.ok) throw new Error('no pude descargar el archivo');
  const dir = path.join(MUSIC_DIR, genre); fs.mkdirSync(dir, { recursive: true });
  const ext = (path.extname(f.file_name || info.file_path) || '.mp3').toLowerCase();
  const name = String(f.title || f.file_name || 'cancion').replace(/\.[a-z0-9]+$/i, '').replace(/[^\w\- ]+/g, '').trim().slice(0, 50) || 'cancion';
  fs.writeFileSync(path.join(dir, `${name}-${Date.now() % 1e6}${ext}`), Buffer.from(await r.arrayBuffer()));
  return send(`✅ Guardada en <b>${GENRES[genre]}</b> (${songs(genre)} canciones). Los próximos anuncios con ese ritmo la usarán.`);
}

// 📹 Video propio (ej. Gemini): se guarda y se arma el anuncio alrededor
const CLIPS_DIR = path.join(path.dirname(MUSIC_DIR), 'clips');
async function saveClip(m) {
  const f = m.video || m.document;
  if (f.file_size > 20e6) return send('El video pesa más de 20 MB; Telegram no me deja bajarlo. Mándalo con menos calidad (o recórtalo).');
  const info = await rtg('getFile', { file_id: f.file_id });
  const r = await fetch(`https://api.telegram.org/file/bot${token()}/${info.file_path}`);
  if (!r.ok) throw new Error('no pude descargar el video');
  fs.mkdirSync(CLIPS_DIR, { recursive: true });
  const cid = Date.now().toString(36);
  fs.writeFileSync(path.join(CLIPS_DIR, `${cid}.mp4`), Buffer.from(await r.arrayBuffer()));
  const list = [...Products.list(), ...Products.list({ all: true }).filter((p) => p.category === 'Regalo' && !p.active)].slice(0, 20);
  const cap = String(m.caption || '').toLowerCase();
  const guess = cap && list.find((p) => cap.split(/\s+/).filter((w) => w.length > 3 && w !== 'video').some((w) => p.title.toLowerCase().includes(w)));
  if (guess) return clipOptions(guess.id, cid);
  return rtg('sendMessage', { chat_id: config.telegram.adminChatId, text: '📹 Video recibido. ¿De qué producto es el anuncio?',
    reply_markup: { inline_keyboard: list.map((p) => [{ text: `${p.emoji} ${p.title}`.slice(0, 60), callback_data: `clp:${p.id}:${cid}` }]) } });
}
function clipOptions(pid, cid) {
  const p = Products.byId(Number(pid));
  const o = (v, g) => `ad:${pid}:${packOpts({ c: cid, v, g })}`;
  return rtg('sendMessage', { chat_id: config.telegram.adminChatId, text: `📹 Anuncio con tu video para <b>${esc(p?.title || '')}</b>\nTu clip va al inicio con su sonido; después el producto, los métodos de pago y el precio. ¿Qué le agrego?`, parse_mode: 'HTML',
    reply_markup: { inline_keyboard: [
      [{ text: '🎙️ Voz + 🎵 música (en la parte del producto)', callback_data: o('ia', 'ia') }],
      [{ text: '🎵 Solo música', callback_data: o('0', 'ia') }, { text: '🎙️ Solo voz', callback_data: o('ia', '0') }],
      [{ text: '🔇 Nada (solo el sonido del clip + efectos)', callback_data: o('0', '0') }]] } });
}

// 🎬 Prompts para Gemini (Veo): el clip realista que abre el anuncio. Diego lo pega en la app de Gemini y nos manda el video.
const GEMINI_EJEMPLOS = `Vertical 9:16 video, realistic, handheld smartphone look. Night, small kitchen table lit by a warm lamp. A Latina woman in her early 30s, wearing a hoodie, is surrounded by crumpled receipts, bills and an open wallet with only a few coins. Her phone keeps buzzing with notifications. She drops her head on the table in comic frustration, then looks straight at the camera and says in neutral Latin American Spanish: "¿En qué se me fue el sueldo… otra vez?" Then she slowly turns a laptop toward the camera; the screen glows with a colorful dashboard of charts, out of focus. She raises an eyebrow and smiles, relieved. Natural sounds: phone buzzing, paper rustling, a soft sigh. No music, only natural ambient sounds and voices. No on-screen text, no logos, no brand names.

Vertical 9:16 video, realistic, handheld party footage feel. A cheerful baby shower in a living room decorated with pastel pink, blue and beige balloons and a small cake. A group of women friends of different ages sit around a table holding printed game boards and using beans as markers, laughing. One woman reads a card aloud in a playful voice, everyone leans in with suspense. Suddenly the pregnant guest of honor jumps up, raises her board and shouts in neutral Latin American Spanish: "¡LOTERÍA!" Everyone screams, laughs and hugs her, then they all freeze smiling at the camera. Warm natural daylight, joyful atmosphere. Natural sounds: laughter, cheering, chairs moving. No music, only natural ambient sounds and voices. No on-screen text, no logos, no brand names.`;

async function geminiPrompts(pid) {
  const p = Products.byId(Number(pid));
  if (!p) return send('Producto no encontrado.');
  if (!config.anthropic.key) return send('Falta ANTHROPIC_API_KEY en la tienda.');
  const dir = path.join(path.dirname(MUSIC_DIR), 'anuncios', p.slug); fs.mkdirSync(dir, { recursive: true });
  let B = {}; try { B = JSON.parse(fs.readFileSync(path.join(dir, 'brief.json'), 'utf8')); } catch {}
  const histF = path.join(dir, 'gemini-prompts.json'); let hist = []; try { hist = JSON.parse(fs.readFileSync(histF, 'utf8')); } catch {}
  await send(`🎬 Escribiendo 2 prompts para Gemini de <b>${esc(p.title)}</b>…`);
  const R = await askJson(`Eres director de anuncios virales de Reels/TikTok. Escribe 2 prompts para generar con Veo (app de Gemini) el CLIP REALISTA de 8-10 segundos que abrirá el anuncio de este producto digital.
Producto: ${JSON.stringify({ titulo: p.title, frase: p.short, descripcion: String(p.description || '').slice(0, 1200), precio: p.price_cents / 100 })}
Público: ${JSON.stringify(B.publico || '')} ${B.investigacion ? 'Investigación real: ' + JSON.stringify(B.investigacion.publico_real || {}).slice(0, 1500) : ''}
Así de buenos tienen que ser (estos dos funcionaron perfecto, mismo nivel de detalle y estructura):
${GEMINI_EJEMPLOS}
Reglas (Veo se equivoca cuando pasan muchas cosas: menos es más):
- Prompt en INGLÉS (Veo lo entiende mejor); lo que se dice va entre comillas en español NEUTRO latinoamericano, 1 frase corta y natural (sin modismos de un país).
- Empieza con "Vertical 9:16 video, realistic, 8 seconds, one single continuous shot, no cuts." Cámara FIJA o un acercamiento lento (slow push-in); nada de movimientos bruscos.
- Máximo 2 ACCIONES simples y una sola emoción fuerte (ej. suspira frustrada → sonríe aliviada). 1 o 2 personas como máximo.
- PROHIBIDO lo que Veo hace mal: lanzar u objetos volando, vaciar o derramar cosas, monedas o líquidos cayendo, abrir/cerrar tapas, manos manipulando objetos pequeños, texto o números legibles, pantallas nítidas, cambios de ropa o de lugar.
- Describe el ESTADO FIJO de cada objeto y di que no cambia (ej. "an open glass jar without a lid that stays still on the table the whole time"). Describe el lugar con 3-4 detalles concretos y añade "the room and furniture stay exactly the same".
- Si aparece algo parecido al producto, que sea un PROP simple y DESENFOCADO o visto de lado, parecido a lo real: describe solo su forma y colores (ej. para un reto de ahorro "a printed letter-size sheet with a grid of small pastel circles, some colored in"; para un planner "a pastel printed planner page"; para una plantilla de Excel "a laptop screen softly glowing with colorful charts, out of focus"). Nunca texto legible.
- En los primeros 2 segundos pasa algo que frena el scroll (gesto exagerado, cara de sorpresa, frustración cómica, mirada a cámara).
- TERMINA en una pose quieta y feliz que dure el último segundo (para cortar ahí y que entre nuestro producto real).
- Termina siempre con "Natural sounds: …", "Consistent lighting and objects throughout." y "No on-screen text, no logos, no brand names."
- SONIDO: nada de música (Veo pone música triste o random): termina SIEMPRE con "No music, only natural ambient sounds and voices."
- Los 2 prompts son de ESTILOS distintos:
  1) "realista": persona real en un momento cotidiano de este público (como los ejemplos), gancho fuerte en el segundo 1.
  2) "impacto": usa las TÉCNICAS de los anuncios de juegos móviles que enganchan desde el primer cuadro (pero la imagen es REAL, no animación): el PRIMER FOTOGRAMA ya es raro o tenso (nada de presentaciones: arranca en medio de la acción), algo está a punto de salir mal o ya está saliendo mal de forma exagerada y visual (una pila enorme de recibos tambaleándose, una lista de regalos interminable desenrollándose hasta el piso, la alarma de "fin de mes" con la persona en pánico), la tensión sube en 2-3 segundos y luego llega un giro SATISFACTORIO y claro (todo se ordena, la persona respira, sonrisa de victoria). Cámara cercana tipo POV o primer plano, ritmo rápido pero en un solo plano continuo, reacciones exageradas creíbles, sonidos que llaman la atención (un golpe, un whoosh, un suspiro fuerte, un "ding"). Debe dar ganas de ver qué pasa al final. PERSONAJE LLAMATIVO y memorable (original, nunca un famoso): look que destaque al instante con color fuerte y rasgo divertido, ej. una abuela con rulos y bata fucsia súper expresiva, un papá con suéter navideño brillante y cara de pánico, una mamá con mascarilla facial verde y gafas enormes, un oficinista con corbata torcida y café en cada mano; caras muy expresivas y vestuario que contraste con el fondo.
- No repitas ideas parecidas a estas anteriores: ${JSON.stringify(hist.slice(-8).map((h) => h.idea))}
Devuelve SOLO JSON: {"prompts": [{"estilo": "realista|impacto", "idea": "la situación en 6-10 palabras en español", "gancho": "texto corto (≤ 5 palabras) que pondremos encima", "prompt": "..."}]}`, 3000);
  const ps = (R.prompts || []).filter((x) => x.prompt).slice(0, 2);
  if (!ps.length) return send('⚠️ No salieron prompts, prueba otra vez.');
  fs.writeFileSync(histF, JSON.stringify([...hist, ...ps.map((x) => ({ idea: x.idea }))].slice(-30)));
  for (const [k, x] of ps.entries())
    await rtg('sendMessage', { chat_id: config.telegram.adminChatId, parse_mode: 'HTML',
      text: `${x.estilo === 'impacto' ? '⚡ <b>Impacto (engancha desde el segundo 1)' : '🎥 <b>Realista'}: ${esc(x.idea || '')}</b>\nGancho sugerido: <i>${esc(x.gancho || '')}</i>\n(toca el texto para copiarlo)\n\n<code>${esc(x.prompt)}</code>` });
  return rtg('sendMessage', { chat_id: config.telegram.adminChatId, parse_mode: 'HTML',
    text: `1️⃣ Pega uno en Gemini → crear video (formato vertical).\n2️⃣ Descarga el video y mándamelo aquí escribiendo en el mensaje: <code>${esc(p.title.split(' ').slice(0, 2).join(' ').toLowerCase())}</code>\n3️⃣ Yo armo el anuncio con el producto, la voz, la música y el precio.`,
    reply_markup: { inline_keyboard: [[{ text: '🔄 Otros 2 prompts', callback_data: `gem:${p.id}:` }]] } });
}

const LISTA = `📋 <b>Todos los comandos de Pixelia</b>

🎬 <b>Anuncios</b>
/anuncios — crear anuncios de un producto (imágenes + reel). Al terminar te salen botones para otra variante, tutorial, comedia, Pixabay, 4 variantes, Anuncio PRO, cambiar voz/música/estilo.
/gemini — 2 prompts listos para crear en Gemini el clip realista que abre el anuncio (cuesta menos de 1 centavo).
📹 <b>Mandar un video</b> (ej. el de Gemini) con el nombre del producto en el mensaje → arma el anuncio con tu clip + producto + precio.
/cancelar — quitar los anuncios que están esperando en la fila.

💸 <b>Créditos</b>
/creditos — cuántos créditos de ElevenLabs (voces y música) llevas gastados y cuántos quedan.
/ahorro on — no gastar ElevenLabs (reutiliza voces y canciones guardadas). /ahorro off para volver.

🔎 <b>Buscar productos</b>
/explorar — buscar ya productos digitales en tendencia (gasta Claude: unos $0.40-0.70).
/explorar <i>tema</i> — buscar de un tema, ej. <code>/explorar cursos de cocina</code>.
/explorar mundo — productos para lo que pasa en el mundo (noticias, virales, fechas que vienen).
/fusionar — combinar productos del radar en uno mejor o en un pack de 3.

🎵 <b>Música</b>
/musica — ver cuántas canciones hay por género.
/musica buscar <i>género</i> — pedir canciones reales con licencia (ej. <code>/musica buscar cumbia</code>).
🎧 Mandar un MP3 con el género en el mensaje → se guarda para los anuncios.\n🔳 Mandar la foto de tu QR de Binance Pay escribiendo <code>qr binance</code> → sale al pagar con Binance.

/publicar — subir las 9 publicaciones del kit a Instagram y Facebook (te pide confirmar).\n/campanas — ver tus campañas de anuncios (gasto, vistas, clics) y activarlas o pausarlas.\n/reporte — qué anuncio va ganando (A o B), embudo de interesados y qué te recomiendo (llega solo cada lunes).\n/publicos — crea en Meta los públicos de interesados reales (web, Instagram y Facebook).\n/calendario — publicaciones automáticas: 1 consejo + 2 reels por semana en los días y horas en que más se mueve tu gente (aprende solo; al inicio lun/mié/vie 6 pm). Avisa 3 h antes. <code>/calendario off</code> lo apaga.\n/leccion — la lección de la semana + consejo para Instagram ahora (llega sola cada lunes).\n/remarketing — campaña para quienes ya te conocen (visitaron, bajaron el regalo, te siguen), sin gastar en compradores.\n/similares — crea públicos parecidos a tus interesados y te deja hacerles una campaña.\n/comentarios — revisar ya los comentarios (lo hace solo cada 5 min: responde a quien pide el regalo y oculta spam/insultos).
/lista — esta lista.

🖥️ <b>En el servidor</b> (Termius o CMD: <code>ssh root@162.33.179.6</code>)
<code>echo inicio; cd /opt/pixelia && bash update.sh; echo fin</code>
→ instala los cambios nuevos que hace Claude (córrelo cada vez que te diga que hay cambios).
<code>cd /opt/pixelia && bash configurar.sh</code> → menú para guardar claves (voz, pixabay…) sin pegarlas en el chat.

🛍️ <b>Tienda</b>: https://pixeliadigital.app · admin: https://pixeliadigital.app/admin`;

// 📤 Publicar el último reel de un producto en Instagram + Facebook (con confirmación)
function ultimoReel(pid) {
  const p = Products.byId(Number(pid)); const j = p && AdJobs.last(p.id);
  let r = {}; try { r = JSON.parse(j?.result || '{}'); } catch {}
  if (!p || !r.reel) return null;
  const dir = path.join(path.dirname(MUSIC_DIR), 'anuncios', p.slug);
  let story = {}; try { story = JSON.parse(fs.readFileSync(path.join(dir, 'guion.json'), 'utf8')).story || {}; } catch {}
  const base = String(story.copy?.texto || p.short || '').trim();
  const caption = p.price_cents ? `${base}\n\n💰 $${(p.price_cents / 100).toFixed(2)} · descarga inmediata\n👉 Link en la bio: pixeliadigital.app\n\n#productosdigitales #pixelia #descargainmediata`
    : `${base}\n\n🎁 GRATIS · descárgalo en el link de la bio: pixeliadigital.app/regalo\n💬 ¿Lo quieres? Coméntalo y compártelo con quien lo necesite\n\n#gratis #regalo #pixelia #productosdigitales`;
  return { p, job: j, file: r.reel, url: `${config.baseUrl.replace(/\/$/, '')}/media/anuncios/${p.slug}/${encodeURIComponent(r.reel)}`, caption, exists: fs.existsSync(path.join(dir, r.reel)) };
}
// 📊 Campañas en Meta (todo en pausa hasta que Diego toca Activar)
const PUB_F = path.join(path.dirname(MUSIC_DIR), '..', 'data', 'publicos.json');
const pubIds = () => { try { return JSON.parse(fs.readFileSync(PUB_F, 'utf8')); } catch { return {}; } };
/** Embudo de los últimos 7 días con datos de la tienda: quién bajó el regalo y qué hizo después. */
function embudo() {
  const desde = Date.now() - 7 * 86400e3, subs = Subscribers.list(5000).filter((x) => Date.parse(x.created_at + 'Z') > desde);
  const mails = new Set(subs.map((x) => x.email));
  const ords = Orders.recent(2000).filter((o) => o.email && mails.has(String(o.email).toLowerCase()));
  const iniciaron = new Set(ords.map((o) => o.email.toLowerCase())), pagaron = new Set(ords.filter((o) => o.status === 'paid').map((o) => o.email.toLowerCase()));
  return `🧲 <b>Embudo (7 días)</b>: ${subs.length} correos nuevos → ${iniciaron.size} entraron a comprar → ${pagaron.size} compraron${subs.length ? ` (${Math.round(100 * iniciaron.size / subs.length)}% muy interesados)` : ''}`;
}
async function textoPublicos() {
  const ids = pubIds(); if (!Object.keys(ids).length) return '';
  const t = await tamanos(ids).catch(() => ({}));
  return '🎯 <b>Interesados reales en Meta</b>\n' + Object.values(t).map((x) => `• ${esc(x.nombre.replace('Pixelia · ', ''))}: ${x.max > 1000 ? `${x.min}-${x.max}` : 'menos de 1.000 (Meta no da el número exacto hasta que pasen de 1.000)'}`).join('\n');
}
const resumenCamps = [];  // lo usa la lección del lunes
const lp_rm = (c) => !c.remarketing && !String(c.titulo || '').startsWith('🎯') && !!pubIds().vieron;
export async function reporteCampanas(chat) {
  await rtg('sendMessage', { chat_id: chat, parse_mode: 'HTML', text: [embudo(), await textoPublicos()].filter(Boolean).join('\n\n') }).catch(() => {});
  const all = camps().map((c, n) => ({ ...c, n })).filter((c) => c.estado === 'activa');
  resumenCamps.length = 0;
  if (!all.length) return false;
  for (const c of all) {
    const ads = await porAnuncio(c.camp).catch(() => []);
    try { registrar(c, ads); } catch (e) { console.error('[aprendizaje]', e.message); }
    resumenCamps.push(`${c.titulo}: ` + ads.map((x) => `${(c.ads || []).find((a) => a.id === x.id)?.letra || '•'} ${x.gasto.toFixed(2)} gastado, ${x.visitas} visitas`).join('; '));
    const tot = ads.reduce((a, x) => ({ g: a.g + x.gasto, v: a.v + x.visitas, k: a.k + x.clics }), { g: 0, v: 0, k: 0 });
    const lines = ads.map((x) => { const l = (c.ads || []).find((a) => a.id === x.id); return `${l?.letra || '•'} ${esc(l?.nombre || '')}: ${x.gasto.toFixed(2)} gastado · ${x.visitas} visitas · ${x.visitas ? (x.gasto / x.visitas).toFixed(2) + ' por visita' : 'sin visitas'}`; });
    const conV = ads.filter((x) => x.vistas >= 300);
    const rows = [];
    let rec = 'Aún hay pocos datos: déjalo correr unos días más.';
    if (conV.length >= 2) {
      const costo = (x) => x.visitas ? x.gasto / x.visitas : Infinity;
      const [mejor, peor] = [...conV].sort((a, b) => costo(a) - costo(b));
      const lm = (c.ads || []).find((a) => a.id === mejor.id), lp = (c.ads || []).findIndex((a) => a.id === peor.id);
      if (costo(peor) > costo(mejor) * 1.3 && lp >= 0) { rec = `Gana ${lm?.letra}: cada visita sale más barata. Te sugiero pausar ${c.ads[lp].letra} y hacer otra versión parecida a ${lm?.letra}.`; rows.push([{ text: `⏸️ Pausar ${c.ads[lp].letra}`, callback_data: `cpx:${c.n}:pa${lp}` }]); }
      else rec = 'A y B van parecidos: déjalos correr.';
    }
    if (tot.v >= 20 && tot.g / Math.max(1, tot.v) < 0.25) { rec += ' Las visitas salen baratas: puedes subir el presupuesto.'; rows.push([{ text: `⬆️ Subir a $${Math.min(10, c.presupuesto + 2)}/día`, callback_data: `cpx:${c.n}:b${Math.min(10, c.presupuesto + 2)}` }]); }
    for (const ad of (c.ads || []).filter((a) => a.dinamico)) {  // anuncio con varias imágenes: cuál imagen y cuál texto ganaron
      const d = await desgloseDinamico(ad).catch(() => null); if (!d) continue;
      const mejor = (xs) => xs.filter((x) => x.vistas >= 100).sort((a, b) => (a.visitas ? a.gasto / a.visitas : 1e9) - (b.visitas ? b.gasto / b.visitas : 1e9));
      const fila = (x) => `${esc(x.nombre)}: ${x.visitas} visitas${x.visitas ? ` · $${(x.gasto / x.visitas).toFixed(2)} c/u` : ''}`;
      const im = mejor(d.imagenes), tx = mejor(d.textos);
      if (im.length || tx.length) lines.push(`🖼️ Dentro de "${esc(ad.nombre)}":\n${im.map(fila).join('\n')}${tx.length ? '\n' + tx.map(fila).join('\n') : ''}${im[0] ? `\n🏆 Mejor imagen: ${esc(im[0].nombre)}` : ''}${tx[0] ? ` · mejor texto: ${esc(tx[0].nombre)}` : ''}`);
      try { registrar({ ...c, ads: [...(c.ads || []), ...im.map((x, i) => ({ letra: 'img', id: `${ad.id}:${x.nombre}` }))], recetas: [...(c.recetas || []), ...im.map((x) => ({ formato: 'imagen', concepto: x.nombre, tipo: 'imagen' }))] },
        im.map((x) => ({ id: `${ad.id}:${x.nombre}`, gasto: x.gasto, visitas: x.visitas, clics: 0, vistas: x.vistas }))); } catch {}
    }
    rows.push([{ text: '👀 Ver en Meta', url: c.url }, { text: '⏸️ Pausar campaña', callback_data: `cpa:${c.n}:pause` }]);
    if (lp_rm(c)) rows.push([{ text: '🎯 Crear remarketing de este producto', callback_data: `rm:${c.pid}:i` }]);
    await rtg('sendMessage', { chat_id: chat, parse_mode: 'HTML', text: `📈 <b>Reporte · ${esc(c.titulo)}</b> (7 días)\nTotal: ${tot.g.toFixed(2)} ${esc(c.moneda || '')} · ${tot.v} visitas a la página · ${tot.k} clics\n${lines.join('\n') || 'Sin datos todavía.'}\n\n🧠 ${esc(rec)}`, reply_markup: { inline_keyboard: rows } });
  }
  const ap = resumen();
  if (ap.n) await rtg('sendMessage', { chat_id: chat, parse_mode: 'HTML', text: `🧠 <b>Lo que vamos aprendiendo</b> (${ap.n} anuncios con datos)\n${esc(ap.texto.split('\n').slice(1).join('\n'))}\n\n<i>Los guiones y textos nuevos ya usan esto solos.</i>` }).catch(() => {});
  return true;
}
function startReporteSemanal() {
  const F = path.join(path.dirname(MUSIC_DIR), '..', 'data', 'reporte.json');
  setInterval(() => {
    const d = new Date(); if (d.getUTCDay() !== 1 || d.getUTCHours() !== 13) return;  // lunes ~9:00 Caracas
    let st = {}; try { st = JSON.parse(fs.readFileSync(F, 'utf8')); } catch {}
    const hoy = d.toISOString().slice(0, 10); if (st.last === hoy) return;
    fs.writeFileSync(F, JSON.stringify({ last: hoy }));
    reporteCampanas(config.telegram.adminChatId).catch((e) => console.error('[reporte]', e.message))
      .then(() => leccion({ campanas: resumenCamps.join(' | '), campIds: camps().filter((c) => c.estado !== 'borrada').map((c) => c.camp) })).catch((e) => send(`⚠️ No pude preparar la lección de la semana: ${esc(e.message)}`));
  }, 10 * 60e3);
}
const CAMP_F = path.join(path.dirname(MUSIC_DIR), '..', 'data', 'campanas.json');
const camps = () => { try { return JSON.parse(fs.readFileSync(CAMP_F, 'utf8')); } catch { return []; } };
const saveCamps = (c) => { fs.mkdirSync(path.dirname(CAMP_F), { recursive: true }); fs.writeFileSync(CAMP_F, JSON.stringify(c.slice(-50), null, 1)); };
function destino(p) { const b = config.baseUrl.replace(/\/$/, ''); return p.price_cents ? `${b}/p/${p.slug}` : `${b}/regalo`; }
const PLANES = new Map();
/** Variantes A/B: A = último reel; B = el reel anterior (otro formato) o la imagen estática del último anuncio. */
/** Opciones para el 3er anuncio: las 3 imágenes juntas (Meta elige la mejor), una sola imagen con sus tamaños, el reel anterior o nada. */
function opcionesB(x) {
  const dir = path.join(path.dirname(MUSIC_DIR), 'anuncios', x.p.slug), base = config.baseUrl.replace(/\/$/, '') + `/media/anuncios/${x.p.slug}/`;
  const una = ['A', 'B', 'C'].filter((c) => fs.existsSync(path.join(dir, `${c}-4x5.jpg`))).map((c) => ({ tipo: 'imagen', url: base + `${c}-4x5.jpg`, nombre: `solo imagen ${c}`,
    tamanos: Object.fromEntries(['4x5', '9x16', '1x1'].filter((t) => fs.existsSync(path.join(dir, `${c}-${t}.jpg`))).map((t) => [t, base + `${c}-${t}.jpg`])) }));
  const ops = una.length > 1 ? [{ tipo: 'imagenes', nombre: `las ${una.length} imágenes (Meta prueba cuál y con qué texto)`, items: una.map((u) => ({ url: u.url, nombre: u.nombre.replace('solo ', ''), tamanos: u.tamanos })) }, ...una] : una;
  let otros = []; try { otros = fs.readdirSync(dir).filter((f) => /\.mp4$/.test(f) && f !== x.file && !/sin-musica/.test(f)).map((f) => ({ f, t: fs.statSync(path.join(dir, f)).mtimeMs })).sort((a, b) => b.t - a.t); } catch {}
  if (otros[0]) ops.push({ tipo: 'video', url: base + encodeURIComponent(otros[0].f), nombre: 'reel anterior' });
  ops.push({ tipo: 'nada', nombre: 'nada (solo el reel)' });
  return ops;
}
/** 1️⃣ reel + texto A · 2️⃣ reel + texto B · 3️⃣ las imágenes con los 2 textos (o lo que elija con 🔄). */
function variantesDe(x, kB = 0) {
  const ops = opcionesB(x), b = ops[kB % ops.length];
  return [{ tipo: 'video', url: x.url, nombre: 'reel · texto A', t: 0 }, { tipo: 'video', url: x.url, nombre: 'reel · texto B', t: 1 },
    ...(b.tipo === 'nada' ? [] : [{ ...b, t: b.tipo === 'video' ? 1 : 0 }])];
}
async function planCampana(x, modo = '') {
  let story = {}; try { story = JSON.parse(fs.readFileSync(path.join(path.dirname(MUSIC_DIR), 'anuncios', x.p.slug, 'guion.json'), 'utf8')).story || {}; } catch {}
  let B = {}; try { B = JSON.parse(fs.readFileSync(path.join(path.dirname(MUSIC_DIR), 'anuncios', x.p.slug, 'brief.json'), 'utf8')); } catch {}
  const gratis = !x.p.price_cents;
  const R = await askJson(`Eres trafficker de Meta Ads para productos digitales en Latinoamérica (español neutro). Producto: ${JSON.stringify({ titulo: x.p.title, frase: x.p.short, descripcion: String(x.p.description || '').slice(0, 800), precio: gratis ? 'GRATIS a cambio del correo' : '$' + (x.p.price_cents / 100).toFixed(2) })}
Público que creemos: ${JSON.stringify(B.publico || '')}. Guion del reel: ${JSON.stringify((story.escenas || []).map((e) => e.voz).filter(Boolean)).slice(0, 600)}
${resumenTexto() ? `Lo que YA aprendimos con datos reales de nuestras campañas (apóyate en lo que ganó, evita lo que perdió, sin copiar literal):\n${resumenTexto()}\n` : ''}${modo === 'i' ? 'ESTE ANUNCIO ES DE REMARKETING: lo verán personas que YA nos conocen (visitaron la tienda, bajaron un regalo o nos siguen). Háblales como a alguien que ya nos vio: recuérdales el beneficio, resuelve la duda típica (¿sirve en el celular?, ¿es descarga inmediata?) y da una razón clara para decidirse hoy SIN inventar urgencia.\n' : modo === 's' ? 'ESTE ANUNCIO VA A UN PÚBLICO SIMILAR a nuestros interesados (no nos conocen): preséntate rápido y engancha desde la primera línea.\n' : ''}Escribe 2 textos de anuncio MUY distintos para probar A/B (A: empieza por el dolor o una pregunta que frena el scroll; B: empieza por el beneficio/resultado o curiosidad). Cada uno: 1ª línea gancho corto con emoji, 2-4 líneas con viñetas emoji de lo que incluye, cierre con llamada a la acción${gratis ? ' (descárgalo GRATIS)' : ''}, y 4-6 hashtags del nicho en español al final. Máx 450 caracteres cada uno. Nada de urgencia falsa ni promesas exageradas.
Sugiere también el público: 5-8 intereses de Meta (nombres EN INGLÉS tal como existen en Meta Ads, ej. "Personal finance", "Christmas"), edad mínima y máxima, y generos (mujeres|hombres|todos): usa "todos" salvo que el producto sea claramente para un solo género (ej. baby shower → mujeres); hábitos, finanzas, productividad o estudio → todos.
Devuelve SOLO JSON: {"textos":[{"texto":"...","titular":"≤ 40 caracteres"},{"texto":"...","titular":"..."}],"publico":{"intereses":[...],"edad_min":n,"edad_max":n,"generos":"mujeres|hombres|todos"},"por_que":"1 frase"}`, 2500).catch(() => null);
  const t = (R?.textos || []).filter((y) => y.texto).slice(0, 2);
  while (t.length < 2) t.push({ texto: x.caption, titular: gratis ? `GRATIS: ${x.p.title}` : x.p.title });
  return { textos: t, publico: R?.publico || {}, por_que: R?.por_que || '' };
}
async function previewCampana(pid, modo = '', kB = null) {
  const x = ultimoReel(pid);
  if (!x || !x.exists) return send('Primero crea un reel de ese producto (/anuncios) y luego toca 📊.');
  let aud = null;
  if (modo) {  // 🎯 remarketing (i) o 👥 similares (s)
    const ids = pubIds();
    aud = modo === 'i' ? { audiencias: ['vieron', 'regalo', 'casi', 'ig', 'fb'].map((k) => ids[k]).filter(Boolean), excluir: [ids.compradores].filter(Boolean), etiqueta: 'interesados reales (web, regalo, Instagram y Facebook), sin compradores' }
      : { audiencias: ['sim_regalo', 'sim_vieron', 'sim_compradores'].map((k) => ids[k]).filter(Boolean), excluir: [ids.compradores].filter(Boolean), etiqueta: 'similares a tus interesados (1%)' };
    if (!aud.audiencias.length) return send(modo === 'i' ? 'Primero crea los públicos con /publicos.' : 'Primero crea los públicos similares con /similares.');
  }
  let plan = PLANES.get(String(x.p.id));
  if (kB === null || !plan || plan.job !== x.job.id || (plan.publico?.modo || '') !== modo) {  // textos nuevos (al cambiar B se reutilizan)
    await send('🧠 Preparando la campaña: textos A/B con IA y público sugerido…');
    plan = await planCampana(x, modo); plan.job = x.job.id; kB = kB ?? 0;
    if (aud) plan.publico = { ...aud, modo };
  }
  plan.kB = kB; const ops = opcionesB(x), vs = variantesDe(x, kB);
  plan.variantes = vs.map((v) => ({ ...v, texto: plan.textos[v.t % plan.textos.length].texto, titulo: plan.textos[v.t % plan.textos.length].titular,
    ...(v.tipo === 'imagenes' ? { textos: plan.textos.map((t) => t.texto), titulos: plan.textos.map((t) => t.titular) } : {}) }));
  PLANES.set(String(x.p.id), plan);
  const chat = config.telegram.adminChatId, L3 = ['1️⃣', '2️⃣', '3️⃣'];
  const enviar = async (m, campo, url, caption) => rtg(m, { chat_id: chat, [campo]: url, caption: caption.slice(0, 1020), parse_mode: 'HTML' })
    .catch(() => rtg('sendMessage', { chat_id: chat, parse_mode: 'HTML', text: caption + `\n${esc(url)}` }));
  if (kB === 0 || plan.variantes.length < 3) {  // el reel una sola vez, con sus 2 textos
    await enviar('sendVideo', 'video', x.url, `🎬 <b>Tu reel</b> va en los anuncios 1 y 2 (Reels, Historias y Feed), cada uno con un texto distinto:\n\n1️⃣ <b>Texto A</b>\n${esc(plan.variantes[0].texto).slice(0, 420)}\n\n2️⃣ <b>Texto B</b>\n${esc(plan.variantes[1].texto).slice(0, 420)}`);
  }
  const v3 = plan.variantes[2];
  if (v3?.tipo === 'imagenes') {
    await rtg('sendMediaGroup', { chat_id: chat, media: v3.items.map((it, i) => ({ type: 'photo', media: it.url, ...(i === 0 ? { caption: `3️⃣ <b>Un solo anuncio con estas ${v3.items.length} imágenes (cada una con sus 3 tamaños: Feed, Historias/Reels y cuadrada) y los textos A y B</b>. Meta va mostrando cada combinación y le da más a la que mejor funciona. En el reporte del lunes te digo qué imagen y qué texto ganaron.`, parse_mode: 'HTML' } : { caption: it.nombre }) })) })
      .catch(() => send('3️⃣ ' + esc(v3.nombre)));
  } else if (v3?.tipo === 'imagen') {
    const t = v3.tamanos || {};
    const media = [['4x5', 'Feed (4:5)'], ['9x16', 'Historias y Reels (vertical)'], ['1x1', 'Otros lugares (cuadrada)']].filter(([k]) => t[k])
      .map(([k, lab], i) => ({ type: 'photo', media: t[k], ...(i === 0 ? { caption: `3️⃣ <b>${esc(v3.nombre)}</b> con sus ${Object.keys(t).length} tamaños (Meta pone cada uno donde va) + texto A`, parse_mode: 'HTML' } : { caption: lab }) }));
    await rtg('sendMediaGroup', { chat_id: chat, media }).catch(() => enviar('sendPhoto', 'photo', v3.url, `3️⃣ <b>${esc(v3.nombre)}</b> + texto A`));
  } else if (v3?.tipo === 'video') await enviar('sendVideo', 'video', v3.url, `3️⃣ <b>${esc(v3.nombre)}</b> + texto B`);
  const pub = plan.publico, sig = ops[(kB + 1) % ops.length];
  await rtg('sendMessage', { chat_id: chat, parse_mode: 'HTML',
    text: `📊 <b>${aud ? (modo === 'i' ? '🎯 Remarketing' : '👥 Similares') + ' · ' : ''}${esc(x.p.title)}</b>\n\n` + plan.variantes.map((v, i) => `${L3[i]} ${esc(v.nombre)}${v.tipo === 'imagen' ? ' (3 tamaños)' : v.tipo === 'imagenes' ? ' + textos A y B' : ''}`).join('\n') + `\n\nMeta le da más dinero al que mejor funcione.\n` +
      (aud ? `👥 ${esc(aud.etiqueta)}` : `👥 ${esc(pub.generos || 'todos')}, ${pub.edad_min || 24}-${pub.edad_max || 45} años · 🌎 8 países`) +
      `\n\nSe crea <b>EN PAUSA</b> (no gasta nada) hasta que toques ▶️ Activar. Elige cuánto al día:`,
    reply_markup: { inline_keyboard: [(aud ? [1, 2, 3] : [2, 3, 5]).map((u) => ({ text: `✅ $${u}/día`, callback_data: `cpb:${x.p.id}:${u}` })),
      [{ text: `🔄 Cambiar el 3º por: ${sig.nombre}`.slice(0, 60), callback_data: `cpv:${x.p.id}:${(kB + 1) % ops.length}${modo ? '.' + modo : ''}` }],
      [{ text: '🔁 Otros textos', callback_data: aud ? `rm:${x.p.id}:${modo}` : `cp:${x.p.id}:` }, { text: '❌ Cancelar', callback_data: 'x:0' }]] } });
}
async function previewPublicar(pid) {
  const x = ultimoReel(pid);
  if (!x || !x.exists) return send('No encontré un reel terminado de ese producto. Crea uno primero con /anuncios.');
  return rtg('sendMessage', { chat_id: config.telegram.adminChatId, parse_mode: 'HTML',
    text: `📤 Voy a publicar el <b>último reel</b> de <b>${esc(x.p.title)}</b> en Instagram (Reels) y en la página de Facebook con este texto:\n\n${esc(x.caption)}\n\n¿Lo publico?`,
    reply_markup: { inline_keyboard: [[{ text: '✅ Sí, publicar', callback_data: `prok:${x.p.id}:${x.job.id}` }, { text: '❌ No', callback_data: 'x:0' }]] } });
}

export async function onMessage(m) {
  if (String(m.chat?.id) !== String(config.telegram.adminChatId)) return;
  const text = (m.text || '').trim();
  if (text.startsWith('/anuncios')) {
    const list = [...Products.list(), ...Products.list({ all: true }).filter((p) => p.category === 'Regalo' && !p.active)].slice(0, 20);
    if (!list.length) return send('No hay productos publicados.');
    return rtg('sendMessage', { chat_id: m.chat.id, text: '🎬 ¿De qué producto creo anuncios?',
      reply_markup: { inline_keyboard: list.map((p) => [{ text: `${p.emoji} ${p.title}`.slice(0, 60), callback_data: `ad:${p.id}:` }]) } });
  }
  if ((m.photo || (m.document && /^image\//i.test(m.document.mime_type || ''))) && /binance|qr/i.test(m.caption || '')) {  // QR de Binance Pay para el pago
    const f = m.photo ? m.photo[m.photo.length - 1] : m.document;
    const info = await rtg('getFile', { file_id: f.file_id });
    const r = await fetch(`https://api.telegram.org/file/bot${token()}/${info.file_path}`);
    fs.writeFileSync(path.join(path.dirname(MUSIC_DIR), 'binance-qr.jpg'), Buffer.from(await r.arrayBuffer()));
    return send(`✅ QR de Binance guardado. Ya aparece al pagar con Binance: ${esc(config.baseUrl)}/binance-qr.jpg`);
  }
  if (m.video || (m.document && /^video\//i.test(m.document.mime_type || ''))) return saveClip(m).catch((e) => send(`⚠️ No pude guardar el video: ${esc(e.message)}`));
  if (m.audio || (m.document && /audio|mpeg|ogg|wav|mp4a/i.test(m.document.mime_type || ''))) return saveSong(m);
  if (text.startsWith('/lista') || text.startsWith('/comandos')) return send(LISTA);
  if (text.startsWith('/publicos') || text.startsWith('/públicos')) {
    if (!adsListos()) return send('Falta conectar la cuenta publicitaria.');
    await send('🎯 Creando en Meta los públicos de interesados reales (vieron un producto, bajaron el regalo, empezaron a pagar, compraron, interactuaron en Instagram y Facebook)…');
    const r = await crearPublicos(pubIds()).catch((e) => ({ ids: pubIds(), errores: [e.message] }));
    fs.mkdirSync(path.dirname(PUB_F), { recursive: true }); fs.writeFileSync(PUB_F, JSON.stringify(r.ids));
    return send(`✅ ${Object.keys(r.ids).length} públicos listos en tu cuenta publicitaria. Se llenan solos con el píxel y con quien interactúa en tus redes.\n\n${await textoPublicos()}${r.errores.length ? `\n\n⚠️ ${esc(r.errores.join('\n'))}` : ''}\n\nCuando tengan gente, los usamos para mostrarles los productos de pago (los más calientes primero).`);
  }
  if (text.startsWith('/calendario')) {
    const arg = text.split(/\s+/)[1];
    if (arg === 'on' || arg === 'off') return onCalendario(arg, '', send);
    return rtg('sendMessage', { chat_id: m.chat.id, parse_mode: 'HTML', text: estadoCalendario(),
      reply_markup: { inline_keyboard: [[{ text: '🟢 Encender', callback_data: 'cal:on:' }, { text: '⚪ Apagar', callback_data: 'cal:off:' }]] } });
  }
  if (text.startsWith('/leccion') || text.startsWith('/lección')) {
    await send('🎓 Preparando la lección de la semana y el consejo para Instagram (busca en internet qué se está viviendo: unos centavos de Claude)…');
    return leccion({ campanas: resumenCamps.join(' | '), campIds: camps().filter((c) => c.estado !== 'borrada').map((c) => c.camp) }).catch((e) => send(`⚠️ ${esc(e.message)}`));
  }
  if (text.startsWith('/remarketing') || text.startsWith('/similares')) {
    if (!adsListos()) return send('Falta conectar la cuenta publicitaria.');
    const sim = text.startsWith('/similares');
    if (sim) {
      const ids = pubIds(); if (!ids.regalo && !ids.vieron) return send('Primero crea los públicos con /publicos.');
      await send('👥 Creando en Meta públicos SIMILARES (1%) a tus interesados reales en los 8 países…');
      const r = await crearSimilares(ids).catch((e) => ({ ids: {}, errores: [e.message] }));
      Object.assign(ids, r.ids); fs.writeFileSync(PUB_F, JSON.stringify(ids));
      const n = Object.keys(r.ids).length;
      await send(`${n ? `✅ ${n} público(s) similar(es) listo(s). Meta tarda unas horas en llenarlos.` : '⏳ Todavía no se pudo crear ninguno.'}${r.errores.length ? `\n\n${r.errores.map((e) => '• ' + esc(e)).join('\n')}` : ''}`);
      if (!n) return;
    } else {
      const t = await tamanos(pubIds()).catch(() => ({}));
      if (!Object.keys(t).length) return send('Primero crea los públicos con /publicos.');
      if (!Object.values(t).some((x) => x.max > 0)) return send('🎯 Tus públicos de interesados todavía están vacíos. Se llenan con visitas a la tienda y con quien interactúa en Instagram/Facebook. Te aviso en el reporte del lunes cuando tengan gente.');
    }
    const list = Products.list().filter((p) => !p.bundle_ids && ultimoReel(p.id)?.exists).slice(0, 15);
    if (!list.length) return send('Primero crea un reel del producto con /anuncios.');
    return rtg('sendMessage', { chat_id: m.chat.id, text: sim ? '👥 ¿Qué producto le muestro a los públicos similares?' : '🎯 ¿Qué producto le muestro a quienes ya te conocen? (sin gastar en quien ya compró)',
      reply_markup: { inline_keyboard: list.map((p) => [{ text: `${p.emoji} ${p.title}`.slice(0, 60), callback_data: `rm:${p.id}:${sim ? 's' : 'i'}` }]) } });
  }
  if (text.startsWith('/reporte')) return reporteCampanas(m.chat.id).then((ok) => ok || send('No hay campañas activas todavía.')).catch((e) => send(`⚠️ ${esc(e.message)}`));
  if (text.startsWith('/campanas') || text.startsWith('/campañas')) {
    const all = camps().map((c, n) => ({ ...c, n })).filter((c) => c.estado !== 'borrada').slice(-8);
    if (!all.length) return send('Aún no hay campañas. Crea un reel y toca 📊 Crear campaña.');
    for (const c of all) {
      const r = await resultados(c.camp).catch(() => null);
      const clics = r ? Number(r.clicks || 0) : 0, gasto = r ? Number(r.spend || 0) : 0;
      await rtg('sendMessage', { chat_id: m.chat.id, parse_mode: 'HTML',
        text: `📊 <b>${esc(c.titulo)}</b> · ${c.estado === 'activa' ? '▶️ activa' : '⏸️ en pausa'} · $${c.presupuesto}/día\nÚltimos 7 días: gasto ${gasto.toFixed(2)} ${esc(c.moneda || '')} · ${r?.impressions || 0} vistas · ${clics} clics${clics ? ` · ${(gasto / clics).toFixed(2)} por clic` : ''}`,
        reply_markup: { inline_keyboard: [[{ text: '👀 Ver en Meta', url: c.url }], c.estado === 'activa' ? [{ text: '⏸️ Pausar', callback_data: `cpa:${c.n}:pause` }] : [{ text: '▶️ Activar', callback_data: `cpa:${c.n}:act` }, { text: '🗑️ Borrar', callback_data: `cpa:${c.n}:del` }]] } });
    }
    return;
  }
  if (text.startsWith('/comentarios')) { await send('🔎 Revisando comentarios de Instagram y Facebook…'); return revisarComentarios().then(() => send('✅ Revisado.')).catch((e) => send(`⚠️ ${esc(e.message)}`)); }
  if (text.startsWith('/publicar')) {
    if (!redesListas()) return send('Todavía no está conectada la API de Meta. En el servidor: <code>cd /opt/pixelia && bash configurar.sh redes</code>');
    const desde = Math.max(1, Math.min(9, Number((text.match(/kit\s+(\d)/) || [])[1]) || 1));
    let st; try { st = await estadoRedes(); } catch (e) { return send(`⚠️ La conexión con Meta falló: ${esc(e.message)}\nPuede que el token haya vencido: vuelve a correr <code>bash configurar.sh redes</code>.`); }
    return rtg('sendMessage', { chat_id: m.chat.id, parse_mode: 'HTML',
      text: `📤 Conectado a la página <b>${esc(st.pagina)}</b>${st.instagram ? ` y a Instagram <b>@${esc(st.instagram)}</b>` : ' (⚠️ Instagram no aparece conectado a la página)'}.\n\n¿Publico las ${10 - desde} publicaciones del kit${desde > 1 ? ` (desde la ${desde})` : ''} en ${st.instagram ? 'Instagram y ' : ''}Facebook? Van en orden, una cada ~20 segundos.`,
      reply_markup: { inline_keyboard: [[{ text: '✅ Sí, publicar ahora', callback_data: `pub:kit:${desde}` }, { text: '❌ No', callback_data: 'x:0' }]] } });
  }
  if (text.startsWith('/gemini')) {
    const list = [...Products.list().filter((p) => !p.bundle_ids), ...Products.list({ all: true }).filter((p) => p.category === 'Regalo' && !p.active)].slice(0, 20);
    return rtg('sendMessage', { chat_id: m.chat.id, text: '🎬 ¿Para qué producto escribo los prompts de Gemini?',
      reply_markup: { inline_keyboard: list.map((p) => [{ text: `${p.emoji} ${p.title}`.slice(0, 60), callback_data: `gem:${p.id}:` }]) } });
  }
  if (text.startsWith('/creditos') || text.startsWith('/créditos')) return creditos();
  if (text.startsWith('/ahorro')) {
    const f = path.join(path.dirname(MUSIC_DIR), 'ahorro'); const arg = text.split(/\s+/)[1];
    if (arg === 'off' || arg === 'no') { try { fs.unlinkSync(f); } catch {} return send('💸 Modo ahorro <b>desactivado</b>: se crean voces y música nuevas con ElevenLabs cuando haga falta.'); }
    if (arg === 'on' || arg === 'si' || arg === 'sí') { fs.writeFileSync(f, '1'); return send('🟢 Modo ahorro <b>activado</b>: no se gasta nada en ElevenLabs. Se reutilizan las voces y canciones ya creadas; si una frase no está guardada, el reel sale sin voz.\nPara desactivarlo: <code>/ahorro off</code>'); }
    return send(`Modo ahorro: <b>${fs.existsSync(f) ? '🟢 activado' : '⚪ desactivado'}</b>\n<code>/ahorro on</code> = no gastar créditos de ElevenLabs\n<code>/ahorro off</code> = volver a crear voces y música nuevas`);
  }
  if (text.startsWith('/cancelar')) {
    const n = AdJobs.cancelQueued();
    return send(n ? `❌ Quité ${n} anuncio(s) de la fila. El que ya se está haciendo termina igual.` : 'No hay anuncios esperando en la fila (si uno ya se está haciendo, termina igual).');
  }
  if (text.startsWith('/explorar')) {
    const tema = text.replace(/^\/explorar(@\w+)?/, '').trim();
    explorar(tema).catch((e) => send(`⚠️ Explorador: ${esc(e.message)}`)); return;
  }
  if (text.startsWith('/fusionar')) return fuse().catch((e) => send(`⚠️ No pude fusionar: ${esc(e.message)}`));
  const mb = text.match(/^\/m[uú]sica\s+buscar\s+(\S+)/i);
  if (mb) {
    const g = GENRE_ALIAS[mb[1].toLowerCase()];
    if (!g) return send('Género no reconocido. Usa: reggaeton, pop, trap, cumbia, electronica, lofi, acustica o suave.');
    const d = path.join(MUSIC_DIR, 'pedidos'); fs.mkdirSync(d, { recursive: true }); fs.writeFileSync(path.join(d, g), '');
    return send(`🔎 Pedido: busco canciones de <b>${GENRES[g]}</b>. Te llegan en 1-3 minutos.`);
  }
  if (text.startsWith('/musica') || text.startsWith('/música')) {
    const lib = Object.keys(GENRES).filter((g) => songs(g)).map((g) => `• ${GENRES[g]}: ${songs(g)}`).join('\n');
    return send(`${MUSIC_HELP}\n\n<b>Ahora tienes:</b>\n${lib || '(ninguna todavía)'}`);
  }
  if (text.startsWith('/start') || text.startsWith('/ayuda')) return send('📡 Bot del radar de Pixelia. Escribe /lista para ver todos los comandos explicados.\n/anuncios — crear anuncios de un producto\n/explorar [tema] — buscar ya productos digitales en tendencia (o de un tema, ej. /explorar cursos de cocina)\n/explorar mundo — productos para lo que está pasando en el mundo (noticias, virales, fechas que vienen)\n/explorar plr — productos PLR en inglés con licencia clara para rehacerlos en español\n/fusionar — combinar productos del radar en uno mejor o en un pack de 3\n/creditos — créditos de ElevenLabs gastados y disponibles\n/ahorro on|off — no gastar créditos (reutiliza voces y música)\n/cancelar — quitar anuncios de la fila\n/musica — agregar canciones reales para los anuncios\n/gemini — prompts para crear el clip realista en Gemini\n📹 Mándame un video (ej. de Gemini) y armo el anuncio con él');
}

export async function onCallback(q) {
  const [action, id, opts] = String(q.data || '').split(':');
  const esAdmin = String(q.from?.id) === String(config.telegram.adminChatId);
  if (action === 'cal' && esAdmin) {  // 📅 calendario: cal:<día>:no|ya  ·  cal:on|off
    await rtg('answerCallbackQuery', { callback_query_id: q.id }).catch(() => {});
    if (opts === 'no' || opts === 'ya' || id === 'on' || id === 'off') rtg('editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id, reply_markup: { inline_keyboard: [] } }).catch(() => {});
    return onCalendario(id, opts, send).catch((e) => send(`⚠️ Calendario: ${esc(e.message)}`));
  }
  if (action === 'rm' && esAdmin) {  // 🎯 remarketing (i) / 👥 similares (s) de un producto
    await rtg('answerCallbackQuery', { callback_query_id: q.id }).catch(() => {});
    if (!adsListos()) return send('Falta conectar la cuenta publicitaria.');
    return previewCampana(id, opts === 's' ? 's' : 'i').catch((e) => send(`⚠️ ${esc(e.message)}`));
  }
  if (action === 'mus' && String(q.from?.id) === String(config.telegram.adminChatId)) {  // ✅/❌ de una canción sugerida
    const tok = String(opts || '').replace(/[^a-f0-9]/g, ''); const pend = path.join(MUSIC_DIR, 'pendientes');
    let meta; try { meta = JSON.parse(fs.readFileSync(path.join(pend, `${tok}.json`), 'utf8')); } catch { meta = null; }
    const done = (label) => rtg('editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id,
      reply_markup: { inline_keyboard: [[{ text: label, callback_data: 'x:0' }]] } }).catch(() => {});
    if (!meta) { await rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'Ya no está disponible' }).catch(() => {}); return done('—'); }
    const src = path.join(pend, meta.file);
    if (id === 'ok') {
      const dir = path.join(MUSIC_DIR, meta.genre); fs.mkdirSync(dir, { recursive: true });
      const name = `${String(meta.title || 'cancion').replace(/[^\w\- ]+/g, '').trim().slice(0, 40) || 'cancion'}-${tok}${path.extname(meta.file)}`;
      fs.renameSync(src, path.join(dir, name));
      if (meta.needs_credit) {
        const cf = path.join(MUSIC_DIR, 'creditos.json'); let c = {}; try { c = JSON.parse(fs.readFileSync(cf, 'utf8')); } catch {}
        c[`${meta.genre}/${name}`] = meta.credit; fs.writeFileSync(cf, JSON.stringify(c, null, 1));
      }
      await rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'Guardada 🎧' }).catch(() => {});
      await done(`✅ En ${GENRES[meta.genre]} (${songs(meta.genre)})`);
    } else {
      try { fs.unlinkSync(src); } catch {}
      await rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'Descartada' }).catch(() => {});
      await done('❌ Descartada');
    }
    try { fs.unlinkSync(path.join(pend, `${tok}.json`)); } catch {}
    return;
  }
  if (action === 'fz' && String(q.from?.id) === String(config.telegram.adminChatId)) {
    const p = fusions.get(String(opts)); const done = (label) => rtg('editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id,
      reply_markup: { inline_keyboard: [[{ text: label, callback_data: 'x:0' }]] } }).catch(() => {});
    if (!p) { await rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'Propuesta vencida: usa /fusionar otra vez' }).catch(() => {}); return done('—'); }
    if (id === 'no') { fusions.delete(String(opts)); await rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'Descartada' }).catch(() => {}); return done('❌ Descartada'); }
    await rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'Creando borradores y plan (1-2 min)…' }).catch(() => {});
    await done('🛠️ Creando…'); fusions.delete(String(opts));
    const { created, pack, plan } = await createFusion(p);
    await done('✅ Borradores creados');
    let msg = `✅ <b>${esc(p.nombre)}</b> · borradores creados (ocultos hasta que subas los archivos):\n` + created.map((c) => `• ${esc(c.emoji)} ${esc(c.title)}${c.active ? ' (ya en la tienda)' : ''}`).join('\n');
    if (pack) msg += `\n• 📦 Pack: ${esc(pack.title)} ($${(pack.price_cents / 100).toFixed(2)}) — actívalo cuando los 3 estén publicados`;
    msg += `\n\nEntra en ${esc(config.baseUrl)}/admin → Productos → Editar → sube el archivo → Guardar.\nO mándale este plan a Claude y te los fabrica.`;
    await send(msg);
    for (const pl of plan.planes || []) await send(`🛠️ <b>Plan: ${esc(pl.titulo)}</b>\n\n${esc(pl.plan)}`);
    if (plan.error) await send(`(No pude generar el plan detallado: ${esc(plan.error)})`);
    return;
  }
  if (action === 'sel' && String(q.from?.id) === String(config.telegram.adminChatId)) {  // marcar/desmarcar en el selector
    const sel = parseOpts(opts); const sug = lastSug.get(Number(id)) || {};
    await rtg('answerCallbackQuery', { callback_query_id: q.id }).catch(() => {});
    return rtg('editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id, reply_markup: { inline_keyboard: pickerKb(Number(id), sel, sug, sel.m === '1') } }).catch(() => {});
  }
  if ((action === 'cp' || action === 'cpv' || action === 'cpb' || action === 'cpa' || action === 'cpx') && String(q.from?.id) === String(config.telegram.adminChatId)) {
    await rtg('answerCallbackQuery', { callback_query_id: q.id }).catch(() => {});
    if (!adsListos()) return send('Falta conectar la cuenta publicitaria: <code>bash configurar.sh redes</code> con el token de Pixelia Bot.');
    if (action === 'cp') return previewCampana(id);
    if (action === 'cpv') { const [k, modo] = String(opts || '0').split('.'); return previewCampana(id, modo || '', Number(k) || 0); }
    if (action === 'cpx') {  // cpx:<n>:pa<adIndex> | b<usd>
      const all = camps(); const c = all[Number(id)]; if (!c) return send('No encontré esa campaña.');
      try {
        if (opts.startsWith('pa')) { const ad = (c.ads || [])[Number(opts.slice(2))]; await pausarAnuncio(ad.id); await send(`⏸️ Pausé el anuncio ${ad.letra}. El presupuesto se va al otro.`); }
        if (opts.startsWith('b')) { const u = Number(opts.slice(1)); await cambiarPresupuesto(c.camp, u); c.presupuesto = u; saveCamps(all); await send(`💵 Presupuesto cambiado a $${u}/día.`); }
      } catch (e) { await send(`⚠️ Meta: ${esc(e.message)}`); }
      return;
    }
    if (action === 'cpa') {  // cpa:<n>:act|pause|del
      const all = camps(); const c = all[Number(id)]; if (!c) return send('No encontré esa campaña.');
      try {
        if (opts === 'act') { await activar(c); c.estado = 'activa'; await send(`▶️ Campaña <b>activada</b>. Empieza a gastar ~$${c.presupuesto}/día. Revisa resultados en 2-3 días con /campanas.`); }
        if (opts === 'pause') { await pausar(c); c.estado = 'pausada'; await send('⏸️ Campaña en pausa.'); }
        if (opts === 'del') { await borrar(c); c.estado = 'borrada'; await send('🗑️ Campaña borrada.'); }
        saveCamps(all);
      } catch (e) { await send(`⚠️ Meta: ${esc(e.message)}`); }
      return;
    }
    const x = ultimoReel(id); if (!x?.exists) return send('No encontré el reel.');
    await rtg('editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id, reply_markup: { inline_keyboard: [[{ text: '⏳ Creando en pausa…', callback_data: 'x:0' }]] } }).catch(() => {});
    (async () => {
      const plan = PLANES.get(String(x.p.id)) || { variantes: [{ tipo: 'video', url: x.url, nombre: 'reel', texto: x.caption, titulo: x.p.title }], publico: {} };
      const r = await crearCampana({ p: x.p, variantes: plan.variantes, publico: plan.publico, link: destino(x.p), presupuesto: Number(opts) || 3, say: send });
      const all = camps(); all.push({ ...r, pid: x.p.id, titulo: (plan.publico?.modo === 'i' ? '🎯 ' : plan.publico?.modo === 's' ? '👥 ' : '') + x.p.title, presupuesto: Number(opts) || 3, estado: 'pausada', fecha: new Date().toISOString(),
        recetas: recetasVariantes(x.p, plan.variantes), publico: plan.publico || {}, remarketing: plan.publico?.modo === 'i' }); saveCamps(all);
      const n = all.length - 1;
      await rtg('sendMessage', { chat_id: config.telegram.adminChatId, parse_mode: 'HTML',
        text: `✅ <b>Campaña creada EN PAUSA</b> · ${esc(x.p.title)}\n💵 ${Number(opts) || 3} ${esc(r.moneda)}/día · 🅰️🅱️ ${r.ads.length} anuncios (${r.ads.map((a) => a.letra + ': ' + a.nombre).join(', ')})\n💡 ${esc(r.intereses.join(', ') || 'sin intereses (público amplio)')}\n\nRevísala en el Administrador de anuncios. Cuando estés conforme, toca ▶️ Activar.`,
        reply_markup: { inline_keyboard: [[{ text: '👀 Ver en Meta', url: r.url }], [{ text: '▶️ Activar', callback_data: `cpa:${n}:act` }, { text: '🗑️ Borrar', callback_data: `cpa:${n}:del` }]] } });
    })().catch((e) => send(`⚠️ No pude crear la campaña: ${esc(e.message)}`));
    return;
  }
  if (action === 'x') {  // botones "❌ No" / informativos: solo cerrar
    await rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'Listo, no hice nada.' }).catch(() => {});
    return rtg('editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id, reply_markup: { inline_keyboard: [] } }).catch(() => {});
  }
  if (action === 'cm' && String(q.from?.id) === String(config.telegram.adminChatId)) {  // cm:d|s:i|f:<id>
    const [, what, red, ...rest] = String(q.data).split(':'); const cid = rest.join(':');
    try {
      if (what === 'd') await eliminar(red, cid); else await ocultar(red, cid, false);
      await rtg('answerCallbackQuery', { callback_query_id: q.id, text: what === 'd' ? 'Eliminado' : 'Visible otra vez' }).catch(() => {});
      return rtg('editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id, reply_markup: { inline_keyboard: [[{ text: what === 'd' ? '🗑️ Eliminado' : '👁️ Visible otra vez', callback_data: 'x:0' }]] } }).catch(() => {});
    } catch (e) { return rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'No se pudo: ' + e.message.slice(0, 150), show_alert: true }).catch(() => {}); }
  }
  if ((action === 'pr' || action === 'prok') && String(q.from?.id) === String(config.telegram.adminChatId)) {
    await rtg('answerCallbackQuery', { callback_query_id: q.id, text: action === 'pr' ? '' : 'Publicando… (1-5 min)' }).catch(() => {});
    if (!redesListas()) return send('Falta conectar Meta: en el servidor <code>bash configurar.sh redes</code>');
    if (action === 'pr') return previewPublicar(id);
    const x = ultimoReel(id);
    if (!x || String(x.job.id) !== String(opts)) return send('Ese reel ya no es el último de este producto; toca 📤 de nuevo en el anuncio más reciente.');
    await rtg('editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id, reply_markup: { inline_keyboard: [[{ text: '📤 Publicando…', callback_data: 'x:0' }]] } }).catch(() => {});
    (async () => {  // en segundo plano: Instagram tarda unos minutos procesando el video y el bot sigue respondiendo
      const res = [];
      try { await igReel(x.url, x.caption); res.push('Instagram ✅'); } catch (e) { res.push(`Instagram ❌ ${esc(e.message)}`); }
      try { await fbVideo(x.url, x.caption); res.push('Facebook ✅'); } catch (e) { res.push(`Facebook ❌ ${esc(e.message)}`); }
      if (res.some((r) => r.includes('✅'))) marcarPublicado(x.p.id, x.job.id);  // el calendario no lo repite
      await send(`📤 Reel de <b>${esc(x.p.title)}</b>: ${res.join(' · ')}`);
    })().catch((e) => send(`⚠️ Publicar reel: ${esc(e.message)}`));
    return;
  }
  if (action === 'pub' && String(q.from?.id) === String(config.telegram.adminChatId)) {
    await rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'Publicando…' }).catch(() => {});
    await rtg('editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id, reply_markup: { inline_keyboard: [[{ text: '📤 Publicando…', callback_data: 'x:0' }]] } }).catch(() => {});
    publicarKit(send, Number(opts) || 1).then((n) => send(`✅ Listo: ${n} publicaciones subidas completas. Revisa tu Instagram y fija (📌) la 1, la 2 y la 6.`))
      .catch((e) => send(`⚠️ Publicar: ${esc(e.message)}`));
    return;
  }
  if (action === 'gem' && String(q.from?.id) === String(config.telegram.adminChatId)) {
    await rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'Escribiendo prompts…' }).catch(() => {});
    return geminiPrompts(id).catch((e) => send(`⚠️ Prompts para Gemini: ${esc(e.message)}`));
  }
  if (action === 'clp' && String(q.from?.id) === String(config.telegram.adminChatId)) {
    await rtg('answerCallbackQuery', { callback_query_id: q.id }).catch(() => {});
    return clipOptions(id, opts);
  }
  if (action === 'ad' && String(q.from?.id) === String(config.telegram.adminChatId)) {
    const p = Products.byId(Number(id));
    if (!p) return rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'Producto no encontrado' });
    const options = parseOpts(opts);
    const r = AdJobs.enqueue(p.id, options);
    await rtg('answerCallbackQuery', { callback_query_id: q.id, text: r.duplicated ? 'Ya se está creando' : 'En marcha 🎬' }).catch(() => {});
    const desc = [options.c ? '📹 con tu video' : '', options.p ? '📸 con Pixabay' : '', options.f ? (FORMATS[options.f] || '🎲 otro formato') : '', options.v && options.v !== 'ia' ? VOICES[options.v] : '', options.g && options.g !== 'ia' ? GENRES[options.g] : '', options.s && options.s !== 'ia' ? STYLES[options.s] : ''].filter(Boolean).join(' · ');
    if (!r.duplicated) await send(options.x
      ? `🧪 Creando <b>4 variantes</b> de <b>${esc(p.title)}</b> (estilos y ganchos distintos). Tarda unos 15-25 min; te aviso al terminar.`
      : `🎬 Creando anuncios de <b>${esc(p.title)}</b>${desc ? ' · ' + esc(desc) : ''}.\nTe los mando aquí en unos minutos.`);
    return;
  }
  if (String(q.from?.id) !== String(config.telegram.adminChatId)) return rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'No autorizado' });
  if (!['buy', 'rec', 'no'].includes(action)) return rtg('answerCallbackQuery', { callback_query_id: q.id });
  if (action === 'buy' && ['idea-ia', 'idea-mundo'].includes(Candidates.get(id)?.source))  // una idea nueva no tiene original que comprar: se recrea
    return rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'Es una idea nueva: no hay original que comprar. Usa 🛠️ Recrear o Crear este producto.', show_alert: true }).catch(() => {});
  await rtg('answerCallbackQuery', { callback_query_id: q.id, text: action === 'rec' ? 'Preparando el plan (1 min)…' : 'Hecho' }).catch(() => {});
  const raw = Candidates.get(id);
  if (!raw) return send('No encontré ese producto del radar.');
  const c = parseC(raw);
  const mark = (label) => rtg('editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id,
    reply_markup: { inline_keyboard: [[{ text: label, callback_data: 'x:0' }]] } }).catch(() => {});

  if (action === 'no') { Candidates.update(c.id, { status: 'discarded' }); return mark('❌ Descartado'); }

  if (action === 'buy' && String(Candidates.get(id)?.source || '').startsWith('plr-')) {  // PLR: se compra y Claude lo rehace en español
    await mark('🛒 Lo compro (PLR)');
    return send(`🛒 <b>PLR para rehacer: ${esc(c.title)}</b>\n\n1️⃣ Ábrelo: ${esc(c.url)}\n2️⃣ <b>Antes de pagar</b>, mándale el enlace a Claude (el chat donde construimos Pixelia) para que lea la licencia y la vista previa.\n3️⃣ Si Claude dice que sí: cómpralo y guarda el comprobante.\n4️⃣ Pásale el archivo a Claude: lo rehace en español con nuestro estilo y mejoras${/Excel/.test(c.snippet || '') ? ' (y la versión Excel/Sheets que se calcula sola)' : ''}, y te da el ZIP y la portada listos para subir en ${esc(config.baseUrl)}/admin.\n\n${esc(c.snippet || '')}`);
  }
  if (action === 'buy') {
    const product = createDraft(raw, { decision: 'buy' });
    await mark('🛒 Comprar · borrador creado');
    const busca = encodeURIComponent(c.title.slice(0, 80));
    const donde = c.url ? esc(c.url)
      : `no tengo el enlace exacto; búscalo por su nombre en <a href="https://www.etsy.com/search?q=${busca}">Etsy</a> o <a href="https://gumroad.com/discover?query=${busca}">Gumroad</a>`;
    const ad = c.ai.anuncio || {};
    const anuncio = ad.gancho || ad.texto
      ? `\n\n📣 <b>Anuncio sugerido</b>\nGancho: ${esc(ad.gancho)}\nTexto: ${esc(ad.texto)}\nTitular: ${esc(ad.titular)}`
      : '\n\n📣 Los anuncios los crea el estudio: cuando publiques el producto te pregunto si los hago.';
    return send(`🛒 <b>Comprar para revender: ${esc(product.title)}</b>

1️⃣ Dónde comprarlo: ${donde}
2️⃣ <b>Antes de pagar</b>, confirma que la licencia diga PLR, MRR o "Resell Rights" y guarda el comprobante. Si no lo dice, mejor 🛠️ Recrear.
3️⃣ Entra en ${esc(config.baseUrl)}/admin → Productos → <b>${esc(product.title)}</b> → Editar → sube el archivo → Guardar. Al guardar se publica.

Ya dejé escritos el título, la descripción y el precio ($${(product.price_cents / 100).toFixed(2)}). Cámbiales la portada y el nombre para que se vean propios.${anuncio}
Nombre del anuncio en Meta: <code>[${product.slug}] v1</code>`);
  }

  if (action === 'rec') {
    Candidates.update(c.id, { status: 'recreate' });
    await mark('🛠️ Recreando…');
    let plan;
    try { plan = await recreationPlan(c); } catch (e) { plan = `(No pude generar el plan: ${e.message})`; }
    const product = createDraft(raw, { decision: 'recreate' });
    Candidates.update(c.id, { ai: { ...c.ai, plan_recreacion: plan } });
    await mark('🛠️ Recrear · plan enviado');
    return send(`🛠️ <b>Plan para recrear: ${esc(product.title)}</b>\n\n${esc(plan)}\n\n✅ Borrador creado en la tienda. Cuando tengas el archivo: ${esc(config.baseUrl)}/admin → Productos → Editar → subir archivo → Guardar.\nNombre del anuncio en Meta: <code>[${product.slug}] v1</code>`);
  }
}

export async function startRadarBot() {
  if (!token()) { console.log('[radar] RADAR_BOT_TOKEN vacío: botones del radar desactivados.'); return; }
  await rtg('deleteWebhook', {}).catch(() => {});
  startReporteSemanal();
  startCalendario({ rtg, send, ultimoReel });
  startComentarios(send, (text, rows) => rtg('sendMessage', { chat_id: config.telegram.adminChatId, text, parse_mode: 'HTML', reply_markup: { inline_keyboard: rows } }));
  await rtg('setMyCommands', { commands: [  // menú que aparece al escribir "/"
    ['lista', 'Todos los comandos y para qué sirven'], ['publicar', 'Subir el kit a Instagram y Facebook'], ['campanas', 'Ver y activar campañas de anuncios'], ['reporte', 'Resultados A/B e interesados'], ['publicos', 'Públicos de interesados reales'], ['calendario', 'Publicaciones automáticas'], ['leccion', 'Lección de la semana'], ['remarketing', 'Campaña a quienes ya te conocen'], ['similares', 'Públicos similares'], ['anuncios', 'Crear anuncios de un producto'], ['gemini', 'Prompts para el clip realista en Gemini'],
    ['creditos', 'Créditos de ElevenLabs'], ['ahorro', 'Modo ahorro on/off'], ['explorar', 'Buscar productos en tendencia'], ['fusionar', 'Combinar productos del radar'],
    ['musica', 'Música para los anuncios'], ['cancelar', 'Quitar anuncios de la fila']].map(([command, description]) => ({ command, description })) }).catch(() => {});
  console.log('[radar] escuchando botones del radar…');
  let offset = 0;
  for (;;) {
    try {
      const updates = await rtg('getUpdates', { offset, timeout: 30, allowed_updates: ['callback_query', 'message'] });
      for (const u of updates) {
        offset = u.update_id + 1;
        if (u.callback_query) await onCallback(u.callback_query).catch((e) => console.error('[radar]', e.message));
        else if (u.message) await onMessage(u.message).catch((e) => console.error('[radar]', e.message));
      }
    } catch (e) {
      console.error('[radar] polling:', e.message);
      await new Promise((r) => setTimeout(r, 5000));
    }
  }
}
