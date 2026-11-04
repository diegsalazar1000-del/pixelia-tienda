// 🧠 PROCESAR DECISIÓN — qué hacer cuando pulsas un botón del radar.
const C = $('Config').first().json;
const u = $('Telegram Trigger').first().json;
const q = u.callback_query;
if (!q || !q.data) return [{ json: { ignorado: true } }];

const tg = (method, body) => this.helpers.httpRequest({ method: 'POST', url: `https://api.telegram.org/bot${C.TELEGRAM_RADAR_TOKEN}/${method}`, body, json: true });
const store = (method, path, body) => this.helpers.httpRequest({ method, url: `${C.TIENDA_URL}${path}`, headers: { 'x-api-key': C.TIENDA_API_KEY }, body, json: true, timeout: 60000 });
const esc = (s) => String(s ?? '').replace(/[&<>]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[ch]));
const send = async (text) => { for (let i = 0; i < text.length; i += 3900) await tg('sendMessage', { chat_id: C.TELEGRAM_CHAT_ID, text: text.slice(i, i + 3900), parse_mode: 'HTML', link_preview_options: { is_disabled: true } }); };

// Solo tú puedes decidir
if (String(q.from?.id) !== String(C.TELEGRAM_CHAT_ID)) { await tg('answerCallbackQuery', { callback_query_id: q.id, text: 'No autorizado' }); return [{ json: { ignorado: true } }]; }

const [action, id] = q.data.split(':');
await tg('answerCallbackQuery', { callback_query_id: q.id, text: 'Procesando…' }).catch(() => {});
const c = await store('GET', `/api/n8n/candidates/${id}`);
const ai = c.ai || {};
const mark = (label) => tg('editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id,
  reply_markup: { inline_keyboard: [[{ text: label, callback_data: 'x:0' }]] } }).catch(() => {});

if (action === 'no') {
  await store('POST', `/api/n8n/candidates/${id}`, { status: 'discarded' });
  await mark('❌ Descartado');
  return [{ json: { action, id } }];
}

if (action === 'buy') {
  await store('POST', `/api/n8n/candidates/${id}`, { status: 'buy' });
  const { product } = await store('POST', `/api/n8n/candidates/${id}/draft`, { decision: 'buy' });
  await mark('🛒 Comprar · borrador creado');
  await send(`🛒 <b>Comprar para revender: ${esc(product.title)}</b>

1️⃣ Cómpralo aquí: ${esc(c.url)}
2️⃣ <b>Antes de pagar</b>, confirma que la licencia diga PLR, MRR o "Resell Rights" y guarda el comprobante.
3️⃣ Entra en ${esc(C.TIENDA_URL)}/admin → Productos → <b>${esc(product.title)}</b> → Editar → sube el archivo → Guardar. Al guardar se publica.

Ya dejé escritos el título, la descripción y el precio ($${(product.price_cents / 100).toFixed(2)}). Cámbiales la portada y el nombre para que se vean propios.

📣 <b>Anuncio sugerido</b>
Gancho: ${esc(ai.anuncio?.gancho)}
Texto: ${esc(ai.anuncio?.texto)}
Titular: ${esc(ai.anuncio?.titular)}
Nombre del anuncio en Meta: <code>[${product.slug}] v1</code>`);
  return [{ json: { action, id, product: product.slug } }];
}

if (action === 'rec') {
  await store('POST', `/api/n8n/candidates/${id}`, { status: 'recreate' });
  await mark('🛠️ Recreando…');
  const prompt = `Quiero crear mi PROPIA versión (original, no una copia) de este producto digital que está en tendencia, para venderla en español.
Datos: ${JSON.stringify({ fuente: c.source, titulo: c.title, texto: c.snippet, url: c.url, analisis: ai })}

Dame un plan práctico en español, en texto plano con viñetas (sin markdown con #), con estas partes:
1. CONCEPTO: nombre final, para quién es, qué problema resuelve, qué lo hace mejor que el original.
2. CONTENIDO EXACTO: lista de páginas/secciones/plantillas con lo que va en cada una (lo suficientemente detallado para producirlo).
3. CÓMO HACERLO: herramienta (Canva, Notion, Google Sheets, Word/PDF…), formato de entrega y tiempo estimado.
4. PORTADA: descripción de la portada y 3 mockups para las fotos de producto.
5. PRECIO y BONOS: precio, precio tachado y 1-2 bonos baratos de producir.
6. 3 ANUNCIOS para Meta: gancho de vídeo de 3 segundos, texto principal, titular.
No copies textos ni diseños del original; todo debe ser contenido nuevo.`;
  const r = await this.helpers.httpRequest({
    method: 'POST', url: 'https://api.anthropic.com/v1/messages', json: true, timeout: 180000,
    headers: { 'x-api-key': C.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
    body: { model: C.MODELO_POTENTE, max_tokens: 4000, messages: [{ role: 'user', content: prompt }] },
  });
  const plan = (r.content || []).map((b) => b.text || '').join('');
  const { product } = await store('POST', `/api/n8n/candidates/${id}/draft`, { decision: 'recreate' });
  await store('POST', `/api/n8n/candidates/${id}`, { status: 'drafted', ai: { ...ai, plan_recreacion: plan } });
  await mark('🛠️ Recrear · plan enviado');
  await send(`🛠️ <b>Plan para recrear: ${esc(product.title)}</b>\n\n${esc(plan)}\n\n✅ Borrador creado en la tienda. Cuando tengas el archivo: ${esc(C.TIENDA_URL)}/admin → Productos → Editar → subir archivo → Guardar.\nNombre del anuncio en Meta: <code>[${product.slug}] v1</code>`);
  return [{ json: { action, id, product: product.slug } }];
}

return [{ json: { ignorado: true, action } }];
