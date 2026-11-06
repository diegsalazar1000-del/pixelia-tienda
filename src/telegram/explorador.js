// 🌐 Explorador de tendencias 2.0 (corre en la tienda, no toca n8n).
// Claude busca en internet productos digitales que se venden AHORA (últimos 3 meses) en Etsy, TikTok Shop, Instagram,
// Hotmart, Gumroad, Pinterest y Google, de MUCHAS categorías (no solo planners), y propone ideas nuevas derivadas.
// Cada hallazgo llega al bot del radar con los botones de siempre (Comprar / Recrear / Descartar).
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../config.js';
import { Candidates, Products } from '../db.js';

const CATEGORIAS = [
  'planners, agendas y trackers digitales (con un enfoque nuevo o un nicho concreto)',
  'finanzas personales, ahorro y control de deudas',
  'mini cursos y cursos en video prácticos (enseñar a hacer algo concreto)',
  'plantillas de Notion, Canva o Excel/Google Sheets',
  'ebooks y guías prácticas cortas',
  'presets, filtros, LUTs y packs de efectos para fotos y videos',
  'packs de prompts y recursos de IA',
  'imprimibles y fichas de trabajo (niños, maestros, terapia, hogar)',
  'audios digitales: meditaciones, afirmaciones, música libre para contenido',
  'kits para emprendedores y pequeños negocios (catálogos, menús, contratos, plantillas de redes)',
  'recetarios y planes de comidas o entrenamiento (sin promesas de salud)',
  'patrones y archivos para manualidades: crochet, costura, bordado, SVG para Cricut, láminas',
  'recursos para creadores de contenido: plantillas de reels, ganchos, calendarios de contenido',
  'material educativo: idiomas, flashcards, material didáctico, preparación de exámenes',
  'bodas, fiestas y eventos: invitaciones editables, juegos, kits imprimibles',
  'mascotas, maternidad y familia: guías, registros, imprimibles',
];

const token = () => config.radar.token;
const rtg = async (method, params) => {
  const r = await fetch(`https://api.telegram.org/bot${token()}/${method}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(params) });
  const j = await r.json(); if (!j.ok) throw new Error(j.description); return j.result;
};
const esc = (s) => String(s ?? '').replace(/[&<>]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[ch]));
const say = (text, extra = {}) => rtg('sendMessage', { chat_id: config.telegram.adminChatId, text: text.slice(0, 4000), parse_mode: 'HTML', link_preview_options: { is_disabled: true }, ...extra });
const hash = (s) => { let h = 0; for (const ch of String(s)) h = (Math.imul(31, h) + ch.charCodeAt(0)) | 0; return 'x' + (h >>> 0).toString(36); };
const STATE = path.join(path.dirname(config.paths.db), 'explorador.json');
const state = () => { try { return JSON.parse(fs.readFileSync(STATE, 'utf8')); } catch { return {}; } };

function prompt(cats, tema, ya) {
  const hoy = new Date().toISOString().slice(0, 10);
  const soloMundo = /^mundo$/i.test(tema); if (soloMundo) tema = '';
  return `Hoy es ${hoy}. Eres buscador de oportunidades para una tienda de productos digitales en español (Latinoamérica) que vende a 3-10 USD.
Investiga en internet (varias búsquedas en español e inglés: Etsy best sellers, TikTok Shop, TikTok/Instagram virales, Hotmart, Gumroad, Pinterest, Google Trends, artículos recientes)
qué productos DIGITALES se están vendiendo o haciendo virales en los ÚLTIMOS 3 MESES (no clásicos de hace años).
${tema ? `Tema pedido: ${tema}.` : `Céntrate en estas categorías: ${cats.join('; ')}.`}
Planners y finanzas también valen, pero solo si es algo distinto a lo que ya tenemos.
NO repitas nada parecido a esto (ya lo tenemos o ya lo vimos): ${JSON.stringify(ya)}.
Busca VARIEDAD: cada hallazgo de una categoría y un formato distinto (video, PDF, plantilla, audio, pack…).
Incluye cursos o videos que se vendan (la tienda los recrearía como curso propio con guion, diapositivas y ejercicios, sin copiar a la persona).
Evita: marcas registradas, personajes, "cómo ganar dinero rápido", promesas de salud o resultados, contenido para adultos.
TENDENCIAS DEL MUNDO: revisa también qué está pasando ESTA SEMANA en el mundo y en Latinoamérica (noticias que cambian la vida diaria, temas y retos virales, estrenos, cambios de precios o de reglas, temporada, y las fechas especiales de los próximos 30-60 días: festivos, regreso a clases, Black Friday, Navidad, San Valentín, Día de la Madre, mundiales, etc.).
De ahí saca NECESIDADES NUEVAS que la gente tendrá y propón productos digitales que las resuelvan (ej. si sube el costo de la vida → plantilla para recortar gastos; si viene diciembre → planificador de regalos y cenas; si se viraliza un reto → kit para hacerlo).
No te aproveches de tragedias, guerras, enfermedades ni política; nada de marcas ni personajes con derechos.
Además de lo que encuentres, propone IDEAS NUEVAS derivadas: productos que se puedan sacar a partir de esas tendencias y que nadie esté vendiendo igual.
Devuelve SOLO un JSON:
{"hallazgos":[{"titulo":"nombre del producto/tipo de producto visto","url":"enlace donde lo viste","plataforma":"etsy|tiktok|instagram|hotmart|gumroad|pinterest|google|otro",
 "evidencia":"por qué es tendencia ahora: ventas, reseñas, vistas, fecha","fecha_aprox":"AAAA-MM","precio":número o 0,"categoria":"...","publico":"para quién",
 "nota":1-10 (potencial para nosotros: demanda, facilidad de crearlo, margen, fácil de anunciar),"decision":"recrear|comprar_reventa",
 "titulo_tienda":"título atractivo en español para nuestra tienda (máx 70)","frase_corta":"máx 110 caracteres","descripcion":"qué incluiría nuestra versión, 4-6 viñetas",
 "precio_sugerido":número 3-10,"emoji":"1 emoji","como_recrear":["3 ideas para hacer una versión propia MEJOR"],"derechos":"si menciona PLR/MRR dilo; si no, 'recrear con contenido propio'",
 "anuncio":{"gancho":"frase de 3 segundos para el video","texto":"texto principal para Meta con 2-3 viñetas","titular":"máx 40 caracteres"}}],
 "ideas":[{"titulo_tienda":"...","basada_en":"qué tendencia la inspira","publico":"...","frase_corta":"...","descripcion":"4-6 viñetas","precio_sugerido":número,"emoji":"...","nota":1-10,"por_que":"breve",
  "anuncio":{"gancho":"...","texto":"...","titular":"..."}}],
 "mundo":[{"tendencia":"qué está pasando (noticia, tema viral o fecha que viene)","url":"fuente real","necesidad":"qué necesitará la gente por eso","cuando":"desde cuándo/hasta cuándo sirve",
  "titulo_tienda":"...","publico":"...","frase_corta":"...","descripcion":"4-6 viñetas","precio_sugerido":número,"emoji":"...","nota":1-10,"anuncio":{"gancho":"...","texto":"...","titular":"..."}}]}
Pon SIEMPRE la url real donde viste cada hallazgo (listado, video o artículo).
${soloMundo ? 'Esta vez céntrate en el MUNDO: 1-3 hallazgos, 1-2 ideas y 5-7 productos en "mundo", cada uno de una tendencia distinta.' : 'Entre 6 y 10 hallazgos de categorías DISTINTAS entre sí, 3-4 ideas nuevas y 2-3 productos en "mundo".'}`;
}

async function askClaude(text) {
  const body = { model: process.env.EXPLORER_MODEL || 'claude-sonnet-5-5', max_tokens: 12000,
    tools: [{ type: 'web_search_20250305', name: 'web_search', max_uses: Number(process.env.EXPLORER_SEARCHES || 10) }],
    messages: [{ role: 'user', content: text }] };
  let out = '', searches = 0;
  for (let turn = 0; turn < 5; turn++) {  // las búsquedas largas pueden "pausarse": se continúa
    const r = await fetch('https://api.anthropic.com/v1/messages', { method: 'POST',
      headers: { 'x-api-key': config.anthropic.key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' }, body: JSON.stringify(body) });
    const j = await r.json(); if (!r.ok) throw new Error(j.error?.message || r.status);
    searches += j.usage?.server_tool_use?.web_search_requests || 0;
    out += (j.content || []).filter((b) => b.type === 'text').map((b) => b.text).join('');
    if (j.stop_reason !== 'pause_turn') break;
    body.messages = [...body.messages, { role: 'assistant', content: j.content }];
  }
  return { data: await parseLoose(out), searches };
}

/** Lee el JSON de la IA aunque venga con pequeños errores; si no se puede, le pide a la IA que lo corrija (sin buscar de nuevo). */
async function parseLoose(text) {
  const t = String(text).replace(/```json|```/g, '');
  let s = t.slice(t.indexOf('{'), t.lastIndexOf('}') + 1);
  const tries = [(x) => x,
    (x) => x.replace(/,\s*([}\]])/g, '$1'),                                   // comas sobrantes
    (x) => x.replace(/[\u0000-\u001f]+/g, ' ').replace(/,\s*([}\]])/g, '$1'),  // saltos de línea dentro de textos
    (x) => x.replace(/"\s*\n\s*"/g, '",\n"').replace(/}\s*{/g, '},{').replace(/]\s*"/g, '],"').replace(/,\s*([}\]])/g, '$1')]; // comas que faltan
  for (const f of tries) { try { return JSON.parse(f(s)); } catch {} }
  const r = await fetch('https://api.anthropic.com/v1/messages', { method: 'POST',
    headers: { 'x-api-key': config.anthropic.key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
    body: JSON.stringify({ model: process.env.ANTHROPIC_MODEL || config.anthropic.model, max_tokens: 12000,
      messages: [{ role: 'user', content: 'Corrige este JSON para que sea válido (comas, comillas, corchetes). No cambies el contenido. Devuelve SOLO el JSON:\n\n' + s.slice(0, 60000) }] }) });
  const j = await r.json(); if (!r.ok) throw new Error('no pude leer la respuesta de la IA');
  const fixed = (j.content || []).map((b) => b.text || '').join('').replace(/```json|```/g, '');
  return JSON.parse(fixed.slice(fixed.indexOf('{'), fixed.lastIndexOf('}') + 1));
}

const kb = (c) => ({ inline_keyboard: [
  [{ text: '🛒 Comprar y revender', callback_data: `buy:${c.id}` }, { text: '🛠️ Recrear', callback_data: `rec:${c.id}` }],
  [{ text: '❌ Descartar', callback_data: `no:${c.id}` }, ...(c.url ? [{ text: '🔗 Ver original', url: c.url }] : [])]] });

/** Busca tendencias y avisa al bot del radar. tema = opcional (ej. "cursos de cocina"). */
export async function explorar(tema = '') {
  if (!config.anthropic.key || !token()) return;
  const day = Math.floor(Date.now() / 864e5);
  const cats = [0, 1, 2, 3].map((k) => CATEGORIAS[(day * 4 + k) % CATEGORIAS.length]);  // rota categorías cada día
  if (/^mundo$/i.test(tema)) await say('🌍 <b>Revisando las tendencias del mundo</b> (noticias, virales y fechas que vienen) para proponer productos… (2-4 min)'); else
  await say(`🌐 <b>Explorando tendencias</b>${tema ? ` sobre <i>${esc(tema)}</i>` : `: ${esc(cats.map((c) => c.split(' (')[0].split(':')[0]).join(' · '))}`}… (2-4 min)`);
  let res;
  const ya = [...Products.list({ all: true }).map((p) => p.title), ...Candidates.list('', 80).map((c) => c.title)].map((t) => String(t).slice(0, 60)).slice(0, 100);
  try { res = await askClaude(prompt(cats, tema, ya)); }
  catch (e) { return say(`⚠️ El explorador falló: ${esc(e.message)}`); }
  const { hallazgos = [], ideas = [], mundo = [] } = res.data || {};
  const items = [
    ...hallazgos.map((h) => ({ ...h, _tipo: 'hallazgo' })),
    ...ideas.map((i) => ({ ...i, titulo: i.titulo_tienda, plataforma: 'idea-ia', evidencia: `Idea nueva basada en: ${i.basada_en || ''}. ${i.por_que || ''}`, decision: 'recrear', _tipo: 'idea' })),
    ...mundo.map((m) => ({ ...m, titulo: m.titulo_tienda, plataforma: 'idea-mundo', categoria: 'tendencia mundial',
      evidencia: `🌍 ${m.tendencia || ''}\n🧩 Necesidad: ${m.necesidad || ''}${m.cuando ? `\n🗓️ ${m.cuando}` : ''}`, decision: 'recrear', _tipo: 'mundo' })),
  ].filter((x) => x.titulo || x.titulo_tienda);
  const fresh = Candidates.addMany(items.map((x) => ({ source: String(x.plataforma || 'web').slice(0, 20), external_id: hash((x.url || '') + (x.titulo || x.titulo_tienda)),
    url: x.url || '', title: x.titulo || x.titulo_tienda, snippet: x.evidencia || '', price: Number(x.precio) || 0, currency: 'USD',
    keyword: x.categoria || tema || 'explorador', published_at: x.fecha_aprox || '', metrics: { publico: x.publico || '' }, trend_score: Number(x.nota) || 0 })));
  let sent = 0;
  for (const c of fresh) {
    const x = items.find((i) => hash((i.url || '') + (i.titulo || i.titulo_tienda)) === c.external_id) || {};
    const nota = Math.max(1, Math.min(10, Number(x.nota) || 5));
    const ai = { titulo: x.titulo_tienda || x.titulo, frase_corta: x.frase_corta, descripcion: x.descripcion, precio_sugerido: x.precio_sugerido, emoji: x.emoji,
      categoria: x.categoria, decision: x.decision === 'comprar_reventa' ? 'buy' : 'recreate', como_recrear: x.como_recrear, derechos: x.derechos, idea: x.frase_corta, publico: x.publico,
      anuncio: x.anuncio && typeof x.anuncio === 'object' ? x.anuncio : undefined };
    Candidates.update(c.id, { ai_score: nota, ai, status: 'notified' });
    const titulo = x._tipo === 'mundo' ? `🌍 <b>TENDENCIA MUNDIAL</b> · ${esc(ai.titulo)}` : x._tipo === 'idea' ? `💡 <b>IDEA NUEVA</b> · ${esc(ai.titulo)}` : `${esc(x.emoji || '✨')} <b>${esc(ai.titulo)}</b>`;
    await say(`${titulo}\n⭐ ${nota}/10 · ${esc(x.plataforma || '')}${x.precio ? ` · visto a $${esc(x.precio)}` : ''}\n👥 ${esc(x.publico || '')}\n📈 ${esc(x.evidencia || '')}\n\n${esc(x.frase_corta || '')}\n💰 Nuestro precio: $${esc(ai.precio_sugerido || 4.99)}`,
      { reply_markup: x._tipo === 'idea' || x._tipo === 'mundo' ? { inline_keyboard: [[{ text: '🛠️ Crear este producto', callback_data: `rec:${c.id}` }, { text: '❌ Descartar', callback_data: `no:${c.id}` }],
        ...(x._tipo === 'mundo' && x.url ? [[{ text: '📰 Ver la noticia/tendencia', url: x.url }]] : [])] } : kb(c) }).catch(() => {});
    sent++;
  }
  const st = state(); st.last = new Date().toISOString().slice(0, 10); fs.writeFileSync(STATE, JSON.stringify(st));
  return say(sent ? `✅ Explorador: ${sent} oportunidades nuevas (${hallazgos.length} tendencias + ${ideas.length} ideas + ${mundo.length} del mundo) · ${res.searches} búsquedas.\nToca 🛠️ Recrear en las que te gusten o usa /fusionar para combinarlas.`
    : 'El explorador no encontró nada nuevo hoy (todo lo que vio ya estaba en el radar). Prueba con /explorar y un tema, ej. <code>/explorar cursos de cocina</code>.');
}

/** Una vez al día (por defecto 10:00 hora de Caracas = 14:00 UTC). */
export function startExplorador() {
  if (process.env.EXPLORER_DAILY === '0') return;
  const hour = Number(process.env.EXPLORER_HOUR_UTC || 14);
  setInterval(() => {
    const now = new Date(); const today = now.toISOString().slice(0, 10);
    if (now.getUTCHours() === hour && state().last !== today) explorar().catch((e) => console.error('[explorador]', e.message));
  }, 10 * 60 * 1000);
}
