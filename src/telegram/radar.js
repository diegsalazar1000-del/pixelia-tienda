// Bot del RADAR: la tienda escucha los botones 🛒 🛠️ ❌ que manda n8n (long polling, sin webhooks).
// Así n8n no necesita dirección pública: solo busca y avisa; la tienda ejecuta las decisiones.
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

// Opciones compactas del anuncio en callback_data: "ad:<id>:v=f,g=reggaeton,n=1"
const parseOpts = (s) => Object.fromEntries(String(s || '').split(',').filter(Boolean).map((kv) => kv.split('=')));

async function onMessage(m) {
  if (String(m.chat?.id) !== String(config.telegram.adminChatId)) return;
  const text = (m.text || '').trim();
  if (text.startsWith('/anuncios')) {
    const list = Products.list().slice(0, 20);
    if (!list.length) return send('No hay productos publicados.');
    return rtg('sendMessage', { chat_id: m.chat.id, text: '🎬 ¿De qué producto creo anuncios?',
      reply_markup: { inline_keyboard: list.map((p) => [{ text: `${p.emoji} ${p.title}`.slice(0, 60), callback_data: `ad:${p.id}:` }]) } });
  }
  if (text.startsWith('/start') || text.startsWith('/ayuda')) return send('📡 Bot del radar de Pixelia.\n/anuncios — crear anuncios de un producto');
}

export async function onCallback(q) {
  const [action, id, opts] = String(q.data || '').split(':');
  if (action === 'ad' && String(q.from?.id) === String(config.telegram.adminChatId)) {
    const p = Products.byId(Number(id));
    if (!p) return rtg('answerCallbackQuery', { callback_query_id: q.id, text: 'Producto no encontrado' });
    const options = parseOpts(opts);
    const r = AdJobs.enqueue(p.id, options);
    await rtg('answerCallbackQuery', { callback_query_id: q.id, text: r.duplicated ? 'Ya se está creando' : 'En marcha 🎬' }).catch(() => {});
    if (!r.duplicated) await send(`🎬 Creando anuncios de <b>${esc(p.title)}</b>${options.v && options.v !== '0' ? ' · con voz' : ''}${options.g ? ' · ritmo ' + esc(options.g) : ''}.\nTe los mando aquí en unos minutos.`);
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
