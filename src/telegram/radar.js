// Bot del RADAR: la tienda escucha los botones 🛒 🛠️ ❌ que manda n8n (long polling, sin webhooks).
// Así n8n no necesita dirección pública: solo busca y avisa; la tienda ejecuta las decisiones.
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../config.js';
import { Products, Candidates, AdJobs } from '../db.js';

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
    reply_markup: { inline_keyboard: [[{ text: '🎬 Crear anuncios', callback_data: `ad:${p.id}:` }]] } });
}

// Opciones compactas del anuncio en callback_data: "ad:<id>:v=f,g=reggaeton,s=neon,n=1,x=4"
const parseOpts = (s) => Object.fromEntries(String(s || '').split(',').filter(Boolean).map((kv) => kv.split('=')));
const packOpts = (o) => Object.entries(o).filter(([, x]) => x !== undefined && x !== null && x !== '').map(([k, x]) => `${k}=${x}`).join(',');

// ===== Selector combinable (voz + música + estilo) =====
export const GENRES = { ia: '🎲 La IA elige', reggaeton: 'Reggaetón', pop: 'Pop', trap: 'Trap', cumbia: 'Cumbia', electronica: 'Electrónica', lofi: 'Lo-fi', acustica: 'Acústica', base: 'Suave', 0: '🔇 Sin música' };
export const STYLES = { ia: '🎲 La IA elige', color: '🌈 Color', neon: '🌃 Neón', minimal: '🤍 Minimal', tiktok: '📱 TikTok' };
const FORMATS = { clasico: '✨ Clásico', conversacion: '💬 Chat', vida_real: '🎬 Video real', pantalla: '📱 Pantalla móvil', tutorial: '✍️ Cómo se usa', comparacion: '🔀 Antes/después', lista: '🏆 Top 3' };
const VOICES = { ia: '🎲 IA', f: '👩 Mujer', m: '👨 Hombre', 0: '🔇 Sin voz' };
const MUSIC_DIR = path.join(path.dirname(config.paths?.files || path.resolve('storage/products')), 'musica');
const songs = (g) => { try { return fs.readdirSync(path.join(MUSIC_DIR, g)).filter((f) => /\.(mp3|wav|m4a|ogg|aac|flac)$/i.test(f)).length; } catch { return 0; } };

function pickerKb(pid, sel, sug = {}) {
  const mark = (on, txt, star) => `${on ? '✅ ' : ''}${txt}${star ? ' ⭐' : ''}`;
  const btn = (k, val, txt) => ({ text: mark(String(sel[k]) === String(val), txt, String(sug[k]) === String(val)), callback_data: `sel:${pid}:${packOpts({ ...sel, [k]: val })}` });
  const g = (x) => btn('g', x, GENRES[x] + (songs(x) ? ' 🎧' : ''));
  return [
    [{ text: '🎲 Otra variante (la IA elige otro formato)', callback_data: `ad:${pid}:${packOpts({ v: sel.v, g: sel.g, f: 'otro' })}` }],
    [{ text: '📸 Crear con fotos y videos de Pixabay', callback_data: `ad:${pid}:${packOpts({ v: sel.v, g: sel.g, s: sel.s, p: 1 })}` }],
    [{ text: '🧪 4 variantes con formatos distintos (≈20 min)', callback_data: `ad:${pid}:${packOpts({ v: sel.v, g: sel.g, x: 4 })}` }],
    Object.entries(VOICES).map(([k, t]) => btn('v', k, t)),
    [g('ia')], ['reggaeton', 'pop', 'trap'].map(g), ['cumbia', 'electronica', 'lofi'].map(g), ['acustica', 'base', '0'].map(g),
    [btn('s', 'ia', STYLES.ia)], ['color', 'neon'].map((x) => btn('s', x, STYLES[x])), ['minimal', 'tiktok'].map((x) => btn('s', x, STYLES[x])),
    [{ text: `🎬 Reel nuevo con lo marcado: ${VOICES[sel.v] || ''} · ${GENRES[sel.g] || ''}`.slice(0, 60), callback_data: `ad:${pid}:${packOpts(sel)}` }],
    [{ text: '🔊 Solo cambiar voz/música del último reel', callback_data: `ad:${pid}:${packOpts({ v: sel.v, g: sel.g, a: 1 })}` }],
    [{ text: '🔁 Rehacer público, colores y textos (IA)', callback_data: `ad:${pid}:${packOpts({ ...sel, n: 1 })}` }],
  ];
}

/** Mensaje para armar otra versión del anuncio combinando voz, música y estilo. */
const lastSug = new Map();  // sugerencias de la IA por producto (para marcar ⭐)
export async function sendAdPicker(p, sel = {}, sug = {}) {
  if (!token()) return;
  lastSug.set(p.id, sug);
  const lib = Object.keys(GENRES).filter((g) => songs(g)).map((g) => `${GENRES[g]} (${songs(g)})`).join(', ');
  return rtg('sendMessage', { chat_id: config.telegram.adminChatId, parse_mode: 'HTML',
    text: `🎛️ <b>Más versiones de ${esc(p.title)}</b>\n<b>🎲 Otra variante</b>: la IA elige otro formato con su voz y música. <b>📸 Pixabay</b>: el anuncio usa fotos y videos reales.\nO marca tú voz, música y estilo y pulsa <b>🎬 Reel nuevo</b>. <b>🔊 Solo voz/música</b> = mismo video, otro audio (1 min).\n⭐ = sugerido por la IA para este público · 🎧 = hay canciones reales de ese género\n🎵 Biblioteca: ${lib ? esc(lib) : 'vacía — usa /musica para agregar canciones reales'}`,
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

async function onMessage(m) {
  if (String(m.chat?.id) !== String(config.telegram.adminChatId)) return;
  const text = (m.text || '').trim();
  if (text.startsWith('/anuncios')) {
    const list = Products.list().slice(0, 20);
    if (!list.length) return send('No hay productos publicados.');
    return rtg('sendMessage', { chat_id: m.chat.id, text: '🎬 ¿De qué producto creo anuncios?',
      reply_markup: { inline_keyboard: list.map((p) => [{ text: `${p.emoji} ${p.title}`.slice(0, 60), callback_data: `ad:${p.id}:` }]) } });
  }
  if (m.audio || (m.document && /audio|mpeg|ogg|wav|mp4a/i.test(m.document.mime_type || ''))) return saveSong(m);
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
  if (text.startsWith('/start') || text.startsWith('/ayuda')) return send('📡 Bot del radar de Pixelia.\n/anuncios — crear anuncios de un producto\n/fusionar — combinar productos del radar en uno mejor o en un pack de 3\n/creditos — créditos de ElevenLabs gastados y disponibles\n/ahorro on|off — no gastar créditos (reutiliza voces y música)\n/cancelar — quitar anuncios de la fila\n/musica — agregar canciones reales para los anuncios');
}

export async function onCallback(q) {
  const [action, id, opts] = String(q.data || '').split(':');
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
    return rtg('editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id, reply_markup: { inline_keyboard: pickerKb(Number(id), sel, sug) } }).catch(() => {});
  }
  if (action === 'ad' && String(q.from?.id) === String(config.telegram.adminChatId)) {
    const p = Products.byId(Number(id));
    if (!p) return rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'Producto no encontrado' });
    const options = parseOpts(opts);
    const r = AdJobs.enqueue(p.id, options);
    await rtg('answerCallbackQuery', { callback_query_id: q.id, text: r.duplicated ? 'Ya se está creando' : 'En marcha 🎬' }).catch(() => {});
    const desc = [options.p ? '📸 con Pixabay' : '', options.f ? (FORMATS[options.f] || '🎲 otro formato') : '', options.v && options.v !== 'ia' ? VOICES[options.v] : '', options.g && options.g !== 'ia' ? GENRES[options.g] : '', options.s && options.s !== 'ia' ? STYLES[options.s] : ''].filter(Boolean).join(' · ');
    if (!r.duplicated) await send(options.x
      ? `🧪 Creando <b>4 variantes</b> de <b>${esc(p.title)}</b> (estilos y ganchos distintos). Tarda unos 15-25 min; te aviso al terminar.`
      : `🎬 Creando anuncios de <b>${esc(p.title)}</b>${desc ? ' · ' + esc(desc) : ''}.\nTe los mando aquí en unos minutos.`);
    return;
  }
  if (String(q.from?.id) !== String(config.telegram.adminChatId)) return rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'No autorizado' });
  if (!['buy', 'rec', 'no'].includes(action)) return rtg('answerCallbackQuery', { callback_query_id: q.id });
  await rtg('answerCallbackQuery', { callback_query_id: q.id, text: action === 'rec' ? 'Preparando el plan (1 min)…' : 'Hecho' }).catch(() => {});
  const raw = Candidates.get(id);
  if (!raw) return send('No encontré ese producto del radar.');
  const c = parseC(raw);
  const mark = (label) => rtg('editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id,
    reply_markup: { inline_keyboard: [[{ text: label, callback_data: 'x:0' }]] } }).catch(() => {});

  if (action === 'no') { Candidates.update(c.id, { status: 'discarded' }); return mark('❌ Descartado'); }

  if (action === 'buy') {
    const product = createDraft(raw, { decision: 'buy' });
    await mark('🛒 Comprar · borrador creado');
    return send(`🛒 <b>Comprar para revender: ${esc(product.title)}</b>

1️⃣ Cómpralo aquí: ${esc(c.url)}
2️⃣ <b>Antes de pagar</b>, confirma que la licencia diga PLR, MRR o "Resell Rights" y guarda el comprobante.
3️⃣ Entra en ${esc(config.baseUrl)}/admin → Productos → <b>${esc(product.title)}</b> → Editar → sube el archivo → Guardar. Al guardar se publica.

Ya dejé escritos el título, la descripción y el precio ($${(product.price_cents / 100).toFixed(2)}). Cámbiales la portada y el nombre para que se vean propios.

📣 <b>Anuncio sugerido</b>
Gancho: ${esc(c.ai.anuncio?.gancho)}
Texto: ${esc(c.ai.anuncio?.texto)}
Titular: ${esc(c.ai.anuncio?.titular)}
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
