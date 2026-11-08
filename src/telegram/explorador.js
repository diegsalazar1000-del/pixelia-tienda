// 🌐 Explorador de tendencias 2.0 (corre en la tienda, no toca n8n).
// Claude busca en internet productos digitales que se venden AHORA (últimos 3 meses) en Etsy, TikTok Shop, Instagram,
// Hotmart, Gumroad, Pinterest y Google, de MUCHAS categorías (no solo planners), y propone ideas nuevas derivadas.
// Cada hallazgo llega al bot del radar con los botones de siempre (Comprar / Recrear / Descartar).
import fs from 'node:fs';
import path from 'node:path';
import { registrarClaude } from '../gasto.js';
import { config } from '../config.js';
import { Candidates, Products } from '../db.js';

const CATEGORIAS = [  // rota 4 por día; la mayoría NO son planners (pedido de Diego: buscar de TODO)
  'manualidades de papel imprimibles: papercraft, autómatas y juguetes de cartón (con motorcito o mecanismo), robots y maquetas para armar',
  'kits STEM imprimibles para niños: experimentos, circuitos sencillos, robótica de cartón, ciencia en casa',
  'mascotas: imprimibles, registros de salud y vacunas, guías de entrenamiento, juguetes y accesorios para hacer en casa',
  'presets de Lightroom, LUTs para video y filtros para celular',
  'recursos de Photoshop, Procreate y Canva: acciones, pinceles, mockups, texturas, plantillas editables',
  'packs de prompts y flujos para herramientas de IA NUEVAS de este mes (ChatGPT, Gemini, Midjourney, CapCut, Canva IA…)',
  'recursos para programas y apps que acaban de salir o se están poniendo de moda (plantillas, atajos, guías rápidas)',
  'archivos para cortadoras e impresoras 3D: SVG para Cricut, cortes láser, STL sencillos',
  'juegos imprimibles: escape room en casa, búsquedas del tesoro, trivias, juegos para fiestas y para parejas',
  'libros para colorear, láminas decorativas (wall art), stickers digitales y para imprimir',
  'mini cursos y cursos en video prácticos (enseñar a hacer algo concreto)',
  'ebooks y guías prácticas cortas de un problema concreto',
  'audios: meditaciones, afirmaciones, efectos de sonido y música libre para contenido',
  'kits para emprendedores y pequeños negocios (catálogos, menús, contratos, plantillas de redes, hojas de cálculo de inventario)',
  'recursos para creadores de contenido: plantillas de reels, ganchos, calendarios, overlays y transiciones',
  'material educativo: idiomas, flashcards, material didáctico para maestros, preparación de exámenes',
  'bodas, fiestas y eventos: invitaciones editables, juegos, kits imprimibles',
  'maternidad, bebés y familia: rutinas, actividades Montessori, registros',
  'recetarios, planes de comidas y de entrenamiento (sin promesas de salud)',
  'patrones de crochet, costura, bordado y punto de cruz',
  'hogar y DIY: planos de muebles sencillos, organización de espacios, jardinería y huerto en casa',
  'viajes: guías, itinerarios editables, checklists de equipaje y presupuesto de viaje',
  'plantillas de Notion, Excel/Google Sheets y GoodNotes con un uso nuevo (no planners genéricos)',
  'planners, trackers y finanzas (solo si es un enfoque o nicho muy distinto a lo que ya tenemos)',
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
  const soloMundo = /^mundo$/i.test(tema); const soloPlr = /^plr$/i.test(tema); if (soloMundo || soloPlr) tema = '';
  return `Hoy es ${hoy}. Eres buscador de oportunidades para una tienda de productos digitales en español (Latinoamérica) que vende a 3-10 USD.
Investiga en internet (varias búsquedas en español e inglés: Etsy best sellers, TikTok Shop, TikTok/Instagram virales, Hotmart, Gumroad, Pinterest, Google Trends, artículos recientes)
qué productos DIGITALES se están vendiendo o haciendo virales en los ÚLTIMOS 3 MESES (no clásicos de hace años).
${tema ? `Tema pedido: ${tema}.` : `Céntrate en estas categorías: ${cats.join('; ')}.`}
VARIEDAD OBLIGATORIA: ya tenemos planners, trackers de hábitos y finanzas, así que como MÁXIMO 1 hallazgo de planners/agendas/trackers/finanzas por búsqueda; el resto de OTROS mundos (manualidades de papel y juguetes de cartón con mecanismo, kits STEM, mascotas, presets, Photoshop/Procreate, prompts y recursos para programas o IA nuevas, SVG/3D, juegos imprimibles, cursos, audios, negocios, educación…). Piensa también en lo que salió NUEVO este mes (programas, apps, IA) y qué recursos digitales está comprando la gente para usarlos.
NO repitas nada parecido a esto (ya lo tenemos o ya lo vimos): ${JSON.stringify(ya)}.
Busca VARIEDAD: cada hallazgo de una categoría y un formato distinto (video, PDF, plantilla, audio, pack…).
Incluye cursos o videos que se vendan (la tienda los recrearía como curso propio con guion, diapositivas y ejercicios, sin copiar a la persona).
Evita: marcas registradas, personajes, "cómo ganar dinero rápido", promesas de salud o resultados, contenido para adultos.
PLR / MRR EN INGLÉS PARA REHACER (el mercado en español está mucho menos lleno: esa es nuestra ventaja): busca en Etsy, Gumroad, Payhip, Stan Store y tiendas PLR productos digitales en INGLÉS, específicos y bien hechos de CUALQUIER categoría (kits imprimibles, papercraft, juegos, recursos de diseño, prompts, cursos, ebooks, plantillas para negocios, mascotas, educación… máximo 1 planner/tracker/finanzas), cuya licencia diga CLARAMENTE que puedes MODIFICARLOS, ponerles TU MARCA y REVENDERLOS (PLR o "PLR + MRR" con rebranding). Descarta los "mega bundles" de miles de páginas a $1-5, los que solo permiten uso personal o revender sin modificar, y los de licencia dudosa. Para cada uno di cómo lo haríamos MEJOR en español (qué agregar) y si conviene una versión que se calcula sola en Excel/Google Sheets.
TENDENCIAS DEL MUNDO: revisa también qué está pasando ESTA SEMANA en el mundo y en Latinoamérica (noticias que cambian la vida diaria, temas y retos virales, estrenos, cambios de precios o de reglas, temporada, y las fechas especiales de los próximos 30-60 días: festivos, regreso a clases, Black Friday, Navidad, San Valentín, Día de la Madre, mundiales, etc.).
De ahí saca NECESIDADES NUEVAS que la gente tendrá y propón productos digitales que las resuelvan (ej. si sube el costo de la vida → plantilla para recortar gastos; si viene diciembre → planificador de regalos y cenas; si se viraliza un reto → kit para hacerlo).
No te aproveches de tragedias, guerras, enfermedades ni política; nada de marcas ni personajes con derechos.
Además de lo que encuentres, propone IDEAS NUEVAS derivadas. MÉTODO INVENTOR PIXELIA (obligatorio): no queremos lo "rayado" (planners, trackers o plantillas genéricas). Toma lo que encuentres como MATERIA PRIMA y haz lluvia de ideas: si algo solo ya es bueno y distinto, tómalo; si no, FUSIONA 2-3 hallazgos que nunca van juntos, agrega PERSONALIZACIÓN AUTOMÁTICA por pedido (nombre del niño, mascota, ciudad, fecha: cada compra única), mezcla FÍSICO + DIGITAL (se imprime y se desbloquea algo con QR: audio, pista, página), vende una EXPERIENCIA (una tarde en familia, una fiesta lista, un reto) y usa cultura latina (estampitas, lotería, fiestas). Nuestra ventaja: podemos fabricar productos interactivos (páginas web en la tienda, juegos) y productos que se generan solos por cada pedido, no solo PDFs. Si no ves nada bueno, INVENTA algo nuevo aunque suene raro: mejor 5 ideas audaces que 5 copias. Cada invento con nombre, frase gancho y qué se genera solo.
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
  "titulo_tienda":"...","publico":"...","frase_corta":"...","descripcion":"4-6 viñetas","precio_sugerido":número,"emoji":"...","nota":1-10,"anuncio":{"gancho":"...","texto":"...","titular":"..."}}],
 "plr":[{"titulo":"nombre original en inglés","url":"enlace real a la página del producto","plataforma":"etsy|gumroad|payhip|…","precio":número,"licencia":"lo que dice la licencia, resumido (≤ 25 palabras)","modificar":true,"marca_propia":true,"revender":true,
  "por_que":"señales de que se vende o pega (reseñas, ventas, novedad)","titulo_tienda":"cómo se llamaría nuestra versión en español","mejoras":"qué le agregaríamos para hacerlo mejor","excel":true|false,"publico":"...","precio_sugerido":número,"emoji":"...","nota":1-10}]}
Pon SIEMPRE la url real donde viste cada hallazgo (listado, video o artículo).
${soloPlr ? 'Esta vez céntrate en PLR: 0-2 hallazgos, 0 ideas, 0 mundo y 5-7 productos en "plr" de categorías distintas (máximo 1 planner/tracker/finanzas), solo con licencia clara.' : soloMundo ? 'Esta vez céntrate en el MUNDO: 1-3 hallazgos, 1-2 ideas y 5-7 productos en "mundo", cada uno de una tendencia distinta.' : 'Entre 6 y 10 hallazgos de categorías DISTINTAS entre sí, 4-5 INVENTOS en "ideas" (fusiones audaces de varios hallazgos, personalizados o físico+digital), 2-3 productos en "mundo" y 2-3 en "plr".'}`;
}

/** Una llamada a Claude que no se cae si la respuesta llega vacía o cortada: reintenta 2 veces si Anthropic está saturado o falla la red. */
async function claudeCall(body, fuente) {
  let last = '';
  for (let i = 0; i < 3; i++) {
    if (i) await new Promise((ok) => setTimeout(ok, 15000 * i));
    let r, raw = '';
    try {
      r = await fetch('https://api.anthropic.com/v1/messages', { method: 'POST', signal: AbortSignal.timeout(300000),
        headers: { 'x-api-key': config.anthropic.key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' }, body: JSON.stringify(body) });
      raw = await r.text();
    } catch (e) { last = `sin respuesta de Anthropic (${e.name === 'TimeoutError' ? 'tardó más de 5 min' : e.message})`; continue; }
    let j = null; try { j = JSON.parse(raw); } catch {}
    if (j) registrarClaude(fuente, j);
    if (r.ok && j) return j;
    last = j?.error?.message || `respuesta vacía o cortada de Anthropic (HTTP ${r.status})`;
    if (r.status && r.status < 500 && r.status !== 429 && j) break;   // error nuestro (clave, saldo, petición): no sirve reintentar
  }
  throw new Error(last);
}

export async function askClaude(text, maxBusquedas) {
  const body = { model: process.env.EXPLORER_MODEL || 'claude-sonnet-5-5', max_tokens: 16000,
    tools: [{ type: 'web_search_20250305', name: 'web_search', max_uses: Number(maxBusquedas || process.env.EXPLORER_SEARCHES || 10) }],
    messages: [{ role: 'user', content: text }] };
  let out = '', searches = 0, j = null;
  for (let turn = 0; turn < 5; turn++) {  // las búsquedas largas pueden "pausarse": se continúa
    j = await claudeCall(body, 'explorador / lecciones');
    searches += j.usage?.server_tool_use?.web_search_requests || 0;
    out += (j.content || []).filter((b) => b.type === 'text').map((b) => b.text).join('');
    body.messages = [...body.messages, { role: 'assistant', content: j.content }];
    if (j.stop_reason !== 'pause_turn') break;
  }
  if (!out.includes('{') || j?.stop_reason === 'max_tokens') {  // se le acabó el espacio buscando o no llegó al JSON: que lo entregue ya, sin buscar más
    console.error('[explorador] sin JSON completo, stop_reason =', j?.stop_reason, '· pido el resultado final');
    const k = await claudeCall({ ...body, tool_choice: { type: 'none' }, messages: [...body.messages,
      { role: 'user', content: 'Con lo que ya encontraste, responde AHORA solo con el JSON final pedido (completo y válido), sin buscar más y sin texto fuera del JSON.' }] }, 'explorador / lecciones');
    const fin = (k.content || []).filter((b) => b.type === 'text').map((b) => b.text).join('');
    if (fin.includes('{')) out = fin;
  }
  out = out.replace(/<\/?cite[^>]*>/g, '');  // la búsqueda web marca citas: no deben salir en Telegram
  if (!out.includes('{')) throw new Error(`la IA no devolvió resultados (${j?.stop_reason || 'sin motivo'}); prueba de nuevo en un rato`);
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
  const j = await claudeCall({ model: process.env.ANTHROPIC_MODEL || config.anthropic.model, max_tokens: 16000,
    messages: [{ role: 'user', content: 'Corrige este JSON para que sea válido (comas, comillas, corchetes). No cambies el contenido. Devuelve SOLO el JSON:\n\n' + s.slice(0, 60000) }] }, 'arreglar respuesta')
    .catch(() => { throw new Error('no pude leer la respuesta de la IA'); });
  const fixed = (j.content || []).map((b) => b.text || '').join('').replace(/```json|```/g, '');
  if (!fixed.includes('{')) throw new Error('no pude leer la respuesta de la IA (vino vacía)');
  return JSON.parse(fixed.slice(fixed.indexOf('{'), fixed.lastIndexOf('}') + 1));
}

const kb = (c) => ({ inline_keyboard: [
  [{ text: '🛒 Comprar y revender', callback_data: `buy:${c.id}` }, { text: '🛠️ Recrear', callback_data: `rec:${c.id}` }],
  [{ text: '❌ Descartar', callback_data: `no:${c.id}` }, ...(c.url ? [{ text: '🔗 Ver original', url: c.url }] : [])]] });

/** Busca tendencias y avisa al bot del radar. tema = opcional (ej. "cursos de cocina"). */
export async function explorar(tema = '') {
  if (!config.anthropic.key || !token()) return;
  if (/^cruce$/i.test(tema)) return cruce();
  const day = Math.floor(Date.now() / 864e5);
  const cats = [0, 1, 2, 3].map((k) => CATEGORIAS[(day * 4 + k) % CATEGORIAS.length]);  // rota categorías cada día
  if (/^plr$/i.test(tema)) await say('🛒 <b>Buscando productos PLR en inglés con licencia clara</b> (modificar, poner tu marca y revender) para rehacerlos en español… (2-4 min)'); else
  if (/^mundo$/i.test(tema)) await say('🌍 <b>Revisando las tendencias del mundo</b> (noticias, virales y fechas que vienen) para proponer productos… (2-4 min)'); else
  await say(`🌐 <b>Explorando tendencias</b>${tema ? ` sobre <i>${esc(tema)}</i>` : `: ${esc(cats.map((c) => c.split(' (')[0].split(':')[0]).join(' · '))}`}… (2-4 min)`);
  let res;
  const ya = [...Products.list({ all: true }).map((p) => p.title), ...Candidates.list('', 80).map((c) => c.title)].map((t) => String(t).slice(0, 60)).slice(0, 100);
  try { res = await askClaude(prompt(cats, tema, ya)); }
  catch (e) { return say(`⚠️ El explorador falló: ${esc(e.message)}`); }
  const { hallazgos = [], ideas = [], mundo = [], plr = [] } = JSON.parse(JSON.stringify(res.data || {}).replace(/<\\?\/?cite[^>]*>/g, ''));
  const items = [
    ...hallazgos.map((h) => ({ ...h, _tipo: 'hallazgo' })),
    ...ideas.map((i) => ({ ...i, titulo: i.titulo_tienda, plataforma: 'idea-ia', evidencia: `Idea nueva basada en: ${i.basada_en || ''}. ${i.por_que || ''}`, decision: 'recrear', _tipo: 'idea' })),
    ...mundo.map((m) => ({ ...m, titulo: m.titulo_tienda, plataforma: 'idea-mundo', categoria: 'tendencia mundial',
      evidencia: `🌍 ${m.tendencia || ''}\n🧩 Necesidad: ${m.necesidad || ''}${m.cuando ? `\n🗓️ ${m.cuando}` : ''}`, decision: 'recrear', _tipo: 'mundo' })),
    ...plr.filter((x) => x.url && x.modificar !== false && x.revender !== false).map((x) => ({ ...x, plataforma: ('plr-' + (x.plataforma || 'web')).slice(0, 20), categoria: 'PLR para rehacer', decision: 'comprar_reventa',
      evidencia: `📜 Licencia: ${x.licencia || '¿?'} (${[x.modificar && 'modificar', x.marca_propia && 'tu marca', x.revender && 'revender'].filter(Boolean).join(' · ')})\n📈 ${x.por_que || ''}\n🇪🇸 Nuestra versión: ${x.titulo_tienda || ''}\n✨ Mejoras: ${x.mejoras || ''}${x.excel ? '\n📊 Con versión Excel/Sheets que se calcula sola' : ''}`,
      derechos: x.licencia, _tipo: 'plr' })),
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
    const titulo = x._tipo === 'plr' ? `🛒 <b>PLR PARA REHACER</b> · ${esc(x.titulo || '')}` : x._tipo === 'mundo' ? `🌍 <b>TENDENCIA MUNDIAL</b> · ${esc(ai.titulo)}` : x._tipo === 'idea' ? `💡 <b>INVENTO</b> · ${esc(ai.titulo)}` : `${esc(x.emoji || '✨')} <b>${esc(ai.titulo)}</b>`;
    await say(`${titulo}\n⭐ ${nota}/10 · ${esc(x.plataforma || '')}${x.precio ? ` · visto a $${esc(x.precio)}` : ''}\n👥 ${esc(x.publico || '')}\n📈 ${esc(x.evidencia || '')}\n\n${esc(x.frase_corta || '')}\n💰 Nuestro precio: $${esc(ai.precio_sugerido || 4.99)}`,
      { reply_markup: x._tipo === 'idea' || x._tipo === 'mundo' ? { inline_keyboard: [[{ text: '🛠️ Crear este producto', callback_data: `rec:${c.id}` }, { text: '❌ Descartar', callback_data: `no:${c.id}` }],
        ...(x._tipo === 'mundo' && x.url ? [[{ text: '📰 Ver la noticia/tendencia', url: x.url }]] : [])] }
        : x._tipo === 'plr' ? { inline_keyboard: [[{ text: '🔗 Ver producto y licencia', url: x.url }], [{ text: '🛒 Lo compro', callback_data: `buy:${c.id}` }, { text: '❌ Descartar', callback_data: `no:${c.id}` }]] } : kb(c) }).catch(() => {});
    sent++;
  }
  const st = state(); st.last = new Date().toISOString().slice(0, 10); fs.writeFileSync(STATE, JSON.stringify(st));
  return say(sent ? `✅ Explorador: ${sent} oportunidades nuevas (${hallazgos.length} tendencias + ${ideas.length} ideas + ${mundo.length} del mundo + ${plr.length} PLR) · ${res.searches} búsquedas.\nToca 🛠️ Recrear en las que te gusten o usa /fusionar para combinarlas.`
    : 'El explorador no encontró nada nuevo hoy (todo lo que vio ya estaba en el radar). Prueba con /explorar y un tema, ej. <code>/explorar cursos de cocina</code>.');
}

/** Una vez al día (por defecto 10:00 hora de Caracas = 14:00 UTC). */
export function startExplorador() {
  if (process.env.EXPLORER_DAILY === '0') return;
  const hour = Number(process.env.EXPLORER_HOUR_UTC || 14);
  setInterval(() => {
    const now = new Date(); const today = now.toISOString().slice(0, 10);
    if (now.getUTCHours() === hour && state().last !== today) explorar().catch((e) => console.error('[explorador]', e.message));
    // 🧪 Cruce de tendencias: cada N días (por defecto 14), una hora después del explorador diario.
    const dias = Number(process.env.CRUCE_DAYS || 14), ult = state().lastCruce;
    if (dias > 0 && now.getUTCHours() === (hour + 1) % 24 && (!ult || (Date.parse(today) - Date.parse(ult)) / 864e5 >= dias)) cruce().catch((e) => console.error('[cruce]', e.message));
  }, 10 * 60 * 1000);
}

// ===== 🧪 Cruce de tendencias (método de Diego, 7-nov) =====
// Señales del momento (videos virales, búsquedas, lo que se vende, noticias) → PROBLEMAS y emociones → cruce con lo que
// se vende y con nuestra ventaja → filtros con búsquedas reales → solo 1-2 ideas que sobreviven + ganchos para vender lo nuestro.
const CULTURAS = ['Japón', 'Corea del Sur', 'China (Xiaohongshu, Douyin)', 'los países nórdicos', 'África (Nigeria, Kenia, Sudáfrica)', 'India', 'Brasil', 'Turquía y Medio Oriente', 'Europa del Este', 'Australia'];
function promptCruce(nuestros, ya) {
  const hoy = new Date().toISOString().slice(0, 10);
  const k = Math.floor(Date.now() / (14 * 864e5));  // rota 3 culturas en cada cruce
  const culturas = [0, 1, 2].map((i) => CULTURAS[(k * 3 + i) % CULTURAS.length]).join(', ');
  return `Hoy es ${hoy}. Eres el inventor de productos de Pixelia, tienda de productos DIGITALES en español neutro para Latinoamérica (precios de $3 a $10; la mayoría de clientes en Venezuela, pagan con Binance o PayPal).

NUESTRA VENTAJA (úsala): no solo PDFs; fabricamos productos interactivos (páginas web en nuestra tienda, juegos en el teléfono, códigos QR que desbloquean audio/video/pistas), productos GENERADOS AUTOMÁTICAMENTE por cada pedido con los datos del cliente (nombres, fotos, ciudad), mezclas de papel + teléfono, y experiencias para vivir en familia o en grupo.

MÉTODO (síguelo en orden, con búsquedas web reales):
0. MERCADOS DE OTRAS CULTURAS (obligatorio): esta vez revisa sobre todo ${culturas}. Busca qué productos, servicios, juguetes, apps, páginas o costumbres se están volviendo virales allá y POR QUÉ la gente los paga (emoción, identidad, alivio del estrés, humor, nostalgia). Ej. reales: en China se agotó un caballito de peluche defectuoso porque "se parece a mí un lunes"; en Corea los jóvenes usan páginas que simulan pedir comida sin pagar para desestresarse; en Japón volvieron los álbumes de stickers. Cruza eso con Latinoamérica: el producto tiene que ser FUNCIONAL, gustar aquí y dar ganas de decir "¡ese soy yo!" o "se lo tengo que mandar a fulano".
1. SEÑALES DE LAS ÚLTIMAS 2 SEMANAS: qué videos/audios/formatos crecen de golpe en TikTok, Instagram y YouTube (cuántos videos, cuánto crecen, PARA QUÉ los usa la gente), qué se busca más (Google Trends, Etsy), qué se vende en Etsy/Hotmart/Gumroad, y noticias que cambian la vida diaria. TODO EL AÑO: no te centres en Navidad ni en una sola fecha (máximo 1 idea de temporada).
2. De cada señal saca el PROBLEMA real y cotidiano y la EMOCIÓN que hay detrás (como hacen los fabricantes chinos con sus productos virales: un problema de todos los días + una solución que se entiende al instante). No saques "un producto por noticia".
3. CRUZA esos problemas con lo que ya se vende y con nuestra ventaja para crear productos digitales nuevos o poco comunes.
4. FILTROS (descarta si falla y dilo en "descartadas"):
   - ¿Ya existe? BÚSCALO de verdad (Etsy, Gumroad, Hotmart, apps; en inglés y en español). Puede existir algo parecido, pero el nuestro debe ser poco común y claramente mejor/distinto en español.
   - ¿Una IA de chat lo hace gratis en 10 segundos? Si sí, descártalo (cursos de habilidades que la IA reemplaza, plantillas simples, textos).
   - ¿Se entiende en 3 segundos en un reel? ¿Se fabrica barato (sin licencias de terceros ni personajes con derechos)? ¿Alguien pagaría $5?
5. LO QUE DIEGO YA DESCARTÓ (no lo propongas): planners/agendas/trackers genéricos, personajes con licencia, cosas que ya existen como app (amigo secreto, lotería con fotos, sorteos), cursos que la IA reemplaza (Excel), rifas, calculadoras de bolívares, ideas que solo sirven en Navidad. LE GUSTARON: cuento personalizado, fiesta en una caja con QR y álbum, escape room con QR, mascota de papel que crece, kit antiestafas familiar con palabra clave, anuario del grupo con votos.
6. NO repitas productos que ya tenemos o ya propusimos: ${JSON.stringify(ya)}.
7. GANCHOS: con las señales más fuertes, escribe ganchos cortos para VENDER productos que YA tenemos (lista abajo). Nada de tragedias, muertes, política, guerras ni famosos usados como si recomendaran. Usa emoción (ej.: "Amor, no queremos que te enfermes, queremos que nos dures toda la vida").
Productos que ya tenemos: ${JSON.stringify(nuestros)}.

Habla como PRODUCTO (qué recibe el cliente, por qué es distinto, precio), corto y claro, en español neutro sencillo, con EMOCIÓN y humor (nada de tono técnico). Lo que pega no es lo útil: es lo que hace decir "¡ese soy yo!" o "se lo tengo que mandar a fulano". Humor fuerte está bien, pero sin burlarse de grupos, sin política ni tragedias.
Devuelve SOLO un JSON válido con esta forma:
{"senales":[{"que":"qué está pasando (≤ 15 palabras)","dato":"número o hecho concreto","problema":"problema/emoción detrás (≤ 15 palabras)","url":"fuente real"}],
 "descartadas":[{"idea":"nombre corto","por_que":"ya existe X / la IA lo hace / no se entiende… (≤ 15 palabras)"}],
 "ideas":[{"titulo_tienda":"nombre comercial","emoji":"1 emoji","problema":"qué problema resuelve (≤ 20 palabras)","que_recibe":"qué recibe el cliente, concreto (≤ 40 palabras)","por_que_distinto":"por qué no es lo de siempre (≤ 25 palabras)","parecido":"lo más parecido que encontraste y en qué nos diferenciamos (≤ 25 palabras)","publico":"a quién","precio_sugerido":número,"cultura":"de qué país/cultura viene la inspiración y qué pasó allá (≤ 20 palabras)","gancho":"frase JOCOSA, irónica, dramática o sentimental para el anuncio, nada técnica (≤ 18 palabras)","como_promocionar":"idea de reel corto que haga reír o tocar el corazón (≤ 30 palabras)","prueba_minima":"versión mínima para probar (≤ 20 palabras)","temporada":false,"nota":1-10}],
 "ganchos":[{"producto":"uno de nuestros productos","gancho":"texto del anuncio (≤ 18 palabras)","de_donde":"señal que lo inspira (≤ 10 palabras)"}]}
Cantidades: 5-7 señales, 3-6 descartadas, SOLO 1-2 ideas (las que sobrevivan; si ninguna sobrevive, devuelve 0 y explica en descartadas), 3 ganchos.`;
}

export async function cruce() {
  if (!config.anthropic.key || !token()) return;
  await say('🧪 <b>Cruce de tendencias</b> (cada 2 semanas): revisando otras culturas, redes, búsquedas, lo que se vende y noticias, y filtrando lo que ya existe… (3-5 min)');
  const nuestros = Products.list().map((p) => p.title).slice(0, 40);
  const ya = [...Products.list({ all: true }).map((p) => p.title), ...Candidates.list('', 80).map((c) => c.title)].map((t) => String(t).slice(0, 60)).slice(0, 100);
  let res;
  try { res = await askClaude(promptCruce(nuestros, ya), Number(process.env.CRUCE_SEARCHES || 12)); }
  catch (e) { return say(`⚠️ El cruce falló: ${esc(e.message)}`); }
  const { senales = [], descartadas = [], ideas = [], ganchos = [] } = JSON.parse(JSON.stringify(res.data || {}).replace(/<\\?\/?cite[^>]*>/g, ''));
  const st = state(); st.lastCruce = new Date().toISOString().slice(0, 10); fs.writeFileSync(STATE, JSON.stringify(st));
  // 1) Lo que está pasando
  const lin = senales.slice(0, 7).map((x) => `• <b>${esc(x.que)}</b>${x.dato ? ` — ${esc(x.dato)}` : ''}\n   ↳ ${esc(x.problema || '')}${x.url ? ` · <a href="${esc(x.url)}">fuente</a>` : ''}`).join('\n');
  const mue = descartadas.slice(0, 6).map((x) => `✖️ ${esc(x.idea)}: <i>${esc(x.por_que)}</i>`).join('\n');
  await say(`🧪 <b>CRUCE DE TENDENCIAS</b>\n\n📡 <b>Lo que está pasando</b>\n${lin || '—'}${mue ? `\n\n🧹 <b>Murieron en el filtro</b>\n${mue}` : ''}`);
  // 2) Las ideas que sobreviven (con los botones de siempre)
  let n = 0;
  for (const x of ideas.slice(0, 2)) {
    if (!x.titulo_tienda) continue;
    const nota = Math.max(1, Math.min(10, Number(x.nota) || 6));
    const [c] = Candidates.addMany([{ source: 'cruce', external_id: hash('cruce' + x.titulo_tienda), url: '', title: x.titulo_tienda,
      snippet: `🧩 ${x.problema || ''}\n🎁 ${x.que_recibe || ''}`, price: 0, currency: 'USD', keyword: 'cruce de tendencias', published_at: '', metrics: { publico: x.publico || '' }, trend_score: nota }]);
    if (!c) continue;  // ya estaba en el radar
    Candidates.update(c.id, { ai_score: nota, status: 'notified', ai: { titulo: x.titulo_tienda, frase_corta: x.que_recibe, descripcion: `${x.problema || ''} ${x.que_recibe || ''}`,
      precio_sugerido: x.precio_sugerido, emoji: x.emoji, categoria: 'invento (cruce)', decision: 'recreate', como_recrear: x.prueba_minima, idea: x.que_recibe, publico: x.publico,
      anuncio: x.gancho ? { gancho: x.gancho } : undefined } });
    await say(`${esc(x.emoji || '💡')} <b>IDEA QUE SOBREVIVIÓ · ${esc(x.titulo_tienda)}</b>\n⭐ ${nota}/10 · 💰 $${esc(x.precio_sugerido || 4.99)}${x.temporada ? ' · 🗓️ de temporada' : ''}\n\n🧩 <b>Problema:</b> ${esc(x.problema || '')}\n🎁 <b>Qué recibe:</b> ${esc(x.que_recibe || '')}\n✨ <b>Por qué es distinto:</b> ${esc(x.por_que_distinto || '')}\n🔎 <b>Lo más parecido:</b> ${esc(x.parecido || '')}\n👥 ${esc(x.publico || '')}${x.cultura ? `\n🌏 <b>Inspiración:</b> ${esc(x.cultura)}` : ''}\n🧪 <b>Prueba mínima:</b> ${esc(x.prueba_minima || '')}${x.como_promocionar ? `\n🎬 <b>Cómo promocionarlo:</b> ${esc(x.como_promocionar)}` : ''}\n\n💬 <i>"${esc(x.gancho || '')}"</i>`,
      { reply_markup: { inline_keyboard: [[{ text: '🛠️ Crear este producto', callback_data: `rec:${c.id}` }, { text: '❌ Descartar', callback_data: `no:${c.id}` }]] } }).catch(() => {});
    n++;
  }
  // 3) Ganchos para vender lo que ya tenemos
  const gan = ganchos.slice(0, 3).map((g) => `• <b>${esc(g.producto)}</b>: "${esc(g.gancho)}"\n   <i>(${esc(g.de_donde || '')})</i>`).join('\n');
  return say(`🎣 <b>Ganchos para vender lo que ya tenemos</b>\n${gan || '—'}\n\n✅ Cruce listo: ${n} idea(s) nuevas · ${descartadas.length} descartadas · ${res.searches} búsquedas. El próximo, en 2 semanas (o cuando quieras con <code>/explorar cruce</code>).`);
}

// ===== 🧭 Buscador Exótico (idea de Diego, 7-nov) =====
// Busca qué se está volviendo viral en culturas lejanas (Japón, Nigeria, Islandia…), POR QUÉ la gente lo paga,
// y cómo lo convertimos o mejoramos como producto digital para Latinoamérica. Solo cuando se pide: /exotico [país].
const EXOTICAS = ['Japón', 'Corea del Sur', 'China (Xiaohongshu, Douyin)', 'Taiwán', 'Tailandia', 'Vietnam', 'Indonesia', 'Filipinas', 'India',
  'Nigeria', 'Kenia', 'Sudáfrica', 'Egipto', 'Marruecos', 'Turquía', 'Emiratos y Arabia Saudita', 'Islandia', 'Noruega', 'Suecia', 'Finlandia',
  'Polonia', 'Ucrania y Europa del Este', 'Grecia', 'Brasil', 'Australia', 'Nueva Zelanda'];
const banderas = { japón: '🇯🇵', corea: '🇰🇷', china: '🇨🇳', taiwán: '🇹🇼', tailandia: '🇹🇭', vietnam: '🇻🇳', indonesia: '🇮🇩', filipinas: '🇵🇭', india: '🇮🇳',
  nigeria: '🇳🇬', kenia: '🇰🇪', sudáfrica: '🇿🇦', egipto: '🇪🇬', marruecos: '🇲🇦', turquía: '🇹🇷', emiratos: '🇦🇪', arabia: '🇸🇦', islandia: '🇮🇸', noruega: '🇳🇴',
  suecia: '🇸🇪', finlandia: '🇫🇮', polonia: '🇵🇱', ucrania: '🇺🇦', grecia: '🇬🇷', brasil: '🇧🇷', australia: '🇦🇺', 'nueva zelanda': '🇳🇿', dinamarca: '🇩🇰' };
const bandera = (p) => { const t = String(p || '').toLowerCase(); for (const [k, v] of Object.entries(banderas)) if (t.includes(k)) return v; return '🌏'; };

function promptExotico(paises, nuestros, ya) {
  const hoy = new Date().toISOString().slice(0, 10);
  return `Hoy es ${hoy}. Eres el BUSCADOR EXÓTICO de Pixelia, tienda de productos DIGITALES en español neutro para Latinoamérica ($3-10; clientes sobre todo en Venezuela).
MISIÓN: encontrar qué se está volviendo viral o se vende mucho en culturas lejanas y convertirlo o mejorarlo como producto digital que guste AQUÍ.

1. Investiga con búsquedas web reales, en inglés y en el idioma local, en: ${paises}. Busca DOS cosas por separado:
   a) PRODUCTOS DIGITALES QUE SE ESTÁN VENDIENDO allá (lo principal): apps y juegos pagos, plantillas, imprimibles, stickers/emojis pagos, filtros, páginas o herramientas web, cursos, servicios digitales personalizados, productos en tiendas locales (Etsy, Gumroad, Booth/pixiv en Japón, Naver/Kakao en Corea, Taobao/Xiaohongshu en China, Shopee/Lazada en el sudeste asiático, Jumia en África, Hotmart en Brasil…). Dato concreto: dónde se vende, precio, cuánto vende o cuánto se comparte.
   b) TENDENCIAS, COSTUMBRES O PROBLEMAS de la gente allá (qué los estresa, qué los hace reír, qué ritual o moda tienen) que explican por qué compran.
2. CRUZA a) con b): toma un producto digital que se vende allá y una necesidad o emoción (de allá o de aquí) y crea un producto digital NUEVO o MEJORADO para Latinoamérica que resuelva algo y cree la necesidad ("necesito esto porque…"). Mejóralo con lo nuestro: personalización automática por pedido, papel + teléfono, página interactiva en nuestra tienda, QR, juego en grupo, humor latino. Tiene que ser FUNCIONAL (que sirva o se disfrute de verdad) y dar ganas de decir "¡ese soy yo!" o "se lo tengo que mandar a fulano".
3. Filtros: ¿ya existe en español/Latinoamérica? (búscalo); ¿una IA de chat lo hace gratis en 10 segundos? (descártalo); nada de personajes o marcas con derechos, promesas de salud o dinero, ni burlas de grupos o culturas (adaptamos con respeto).
4. No repitas: ${JSON.stringify(ya)}. Productos que ya tenemos: ${JSON.stringify(nuestros)}.
Tono: con emoción y humor, nada técnico, español neutro sencillo.
Devuelve SOLO un JSON válido:
{"se_vende":[{"pais":"país","que":"producto digital y dónde se vende (≤ 15 palabras)","dato":"precio, ventas o vistas (≤ 12 palabras)","por_que":"por qué lo compran (≤ 15 palabras)","url":"fuente real"}],
 "tendencias":[{"pais":"país","que":"tendencia, costumbre o problema (≤ 15 palabras)","por_que":"qué necesidad o emoción hay detrás (≤ 15 palabras)","url":"fuente real"}],
 "productos":[{"titulo_tienda":"nombre comercial","emoji":"1 emoji","pais":"de dónde viene la idea","original":"qué se vende allá + qué tendencia/necesidad cruzamos (≤ 25 palabras)","necesidad":"por qué alguien aquí lo necesita sí o sí (≤ 18 palabras)","nuestra_version":"qué recibe el cliente aquí, concreto (≤ 40 palabras)","mejora":"qué le agregamos o mejoramos (≤ 25 palabras)","existe_aqui":"lo que encontraste parecido en español/LatAm o 'no encontré' (≤ 20 palabras)","publico":"a quién","precio_sugerido":número,"gancho":"frase jocosa, irónica o sentimental para el anuncio (≤ 18 palabras)","como_promocionar":"idea de reel corto (≤ 30 palabras)","nota":1-10}]}
Cantidades: 4-6 en se_vende, 2-4 en tendencias (de países distintos) y 2-3 productos (solo los mejores, cada uno cruzando algo de se_vende con algo de tendencias).`;
}

export async function exotico(pais = '') {
  if (!config.anthropic.key || !token()) return;
  const k = Math.floor(Date.now() / 864e5);
  const paises = pais ? pais : [0, 1, 2].map((i) => EXOTICAS[(k * 7 + i * 9) % EXOTICAS.length]).join(', ');
  await say(`🧭 <b>Buscador Exótico</b>: buscando qué se está volviendo viral en <b>${esc(paises)}</b> y cómo lo traemos a Latinoamérica… (3-5 min)`);
  const nuestros = Products.list().map((p) => p.title).slice(0, 40);
  const ya = [...Products.list({ all: true }).map((p) => p.title), ...Candidates.list('', 80).map((c) => c.title)].map((t) => String(t).slice(0, 60)).slice(0, 100);
  let res;
  try { res = await askClaude(promptExotico(paises, nuestros, ya), Number(process.env.EXOTICO_SEARCHES || 12)); }
  catch (e) { return say(`⚠️ El Buscador Exótico falló: ${esc(e.message)}`); }
  const { se_vende = [], tendencias = [], hallazgos = [], productos = [] } = JSON.parse(JSON.stringify(res.data || {}).replace(/<\\?\/?cite[^>]*>/g, ''));
  const fila = (h) => `${bandera(h.pais)} <b>${esc(h.que)}</b>${h.dato ? ` — ${esc(h.dato)}` : ''}\n   ↳ ${esc(h.por_que || '')}${h.url ? ` · <a href="${esc(h.url)}">fuente</a>` : ''}`;
  const v = [...se_vende, ...hallazgos].slice(0, 6).map(fila).join('\n'), t = tendencias.slice(0, 4).map(fila).join('\n');
  await say(`🧭 <b>BUSCADOR EXÓTICO</b> · ${esc(paises)}\n\n💾 <b>Productos digitales que se venden allá</b>\n${v || '—'}${t ? `\n\n🔥 <b>Tendencias y necesidades</b>\n${t}` : ''}`);
  let n = 0;
  for (const x of productos.slice(0, 3)) {
    if (!x.titulo_tienda) continue;
    const nota = Math.max(1, Math.min(10, Number(x.nota) || 6));
    const [c] = Candidates.addMany([{ source: 'exotico', external_id: hash('exotico' + x.titulo_tienda), url: '', title: x.titulo_tienda,
      snippet: `${bandera(x.pais)} ${x.original || ''}\n🎁 ${x.nuestra_version || ''}`, price: 0, currency: 'USD', keyword: 'buscador exótico', published_at: '', metrics: { publico: x.publico || '' }, trend_score: nota }]);
    if (!c) continue;
    Candidates.update(c.id, { ai_score: nota, status: 'notified', ai: { titulo: x.titulo_tienda, frase_corta: x.nuestra_version, descripcion: `${x.original || ''} → ${x.nuestra_version || ''}`,
      precio_sugerido: x.precio_sugerido, emoji: x.emoji, categoria: 'invento (exótico)', decision: 'recreate', como_recrear: x.mejora, idea: x.nuestra_version, publico: x.publico,
      anuncio: x.gancho ? { gancho: x.gancho } : undefined } });
    await say(`${esc(x.emoji || '🧭')} <b>${esc(x.titulo_tienda)}</b>\n${bandera(x.pais)} Viene de ${esc(x.pais || '')} · ⭐ ${nota}/10 · 💰 $${esc(x.precio_sugerido || 4.99)}\n\n🏮 <b>Allá:</b> ${esc(x.original || '')}${x.necesidad ? `\n🎯 <b>La necesidad:</b> ${esc(x.necesidad)}` : ''}\n🎁 <b>Nuestra versión:</b> ${esc(x.nuestra_version || '')}\n✨ <b>Lo que le mejoramos:</b> ${esc(x.mejora || '')}\n🔎 <b>¿Existe aquí?</b> ${esc(x.existe_aqui || '')}\n👥 ${esc(x.publico || '')}\n🎬 <b>Cómo promocionarlo:</b> ${esc(x.como_promocionar || '')}\n\n💬 <i>"${esc(x.gancho || '')}"</i>`,
      { reply_markup: { inline_keyboard: [[{ text: '🛠️ Crear este producto', callback_data: `rec:${c.id}` }, { text: '❌ Descartar', callback_data: `no:${c.id}` }]] } }).catch(() => {});
    n++;
  }
  return say(`✅ Buscador Exótico: ${n} producto(s) para traer · ${se_vende.length + hallazgos.length} productos vistos allá + ${tendencias.length} tendencias · ${res.searches} búsquedas.\nOtro país cuando quieras: <code>/exotico Islandia</code> (o solo /exotico y elijo yo).`);
}
