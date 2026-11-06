// Bot de Telegram (long polling: no necesita dominio ni webhook).
// Dentro de Telegram los productos digitales se cobran SOLO con Telegram Stars (norma de Telegram).
import { config } from '../config.js';
import { Products, Orders, Reviews } from '../db.js';
import { reviewLink } from '../resenas.js';
import crypto from 'node:crypto';
import { tg, tgEnabled, notifyAdmin, esc } from './api.js';
import { deliver, downloadLink } from '../delivery/index.js';

const isAdmin = (chatId) => String(chatId) === String(config.telegram.adminChatId);
const httpsStore = () => config.baseUrl.startsWith('https://');
const usd = (c) => '$' + (c / 100).toFixed(2);

function mainMenu() {
  const rows = [[{ text: '🛍️ Ver catálogo', callback_data: 'cats' }], [{ text: '📦 Mis compras', callback_data: 'mine' }]];
  if (httpsStore()) rows.unshift([{ text: '✨ Abrir tienda', web_app: { url: config.baseUrl + '/?tg=1' } }]);
  return { inline_keyboard: rows };
}

async function send(chatId, text, reply_markup) {
  return tg('sendMessage', { chat_id: chatId, text, parse_mode: 'HTML', reply_markup, link_preview_options: { is_disabled: true } });
}

// 💬 Soporte: lo que escribe el cliente te llega al admin; respondes "respondiendo" (deslizar) a ese mensaje y le llega al cliente.
const acked = new Map();
async function toSupport(m) {
  const chatId = m.chat.id, who = m.from?.username ? '@' + m.from.username : (m.from?.first_name || 'Cliente');
  const head = await tg('sendMessage', { chat_id: config.telegram.adminChatId, parse_mode: 'HTML',
    text: `💬 <b>Soporte</b> · ${esc(who)} #c${chatId}\n${m.text ? esc(m.text) : '(archivo o foto 👇)'}\n\n<i>Responde a este mensaje (deslízalo a la derecha) y se lo envío al cliente.</i>` });
  if (!m.text) await tg('copyMessage', { chat_id: config.telegram.adminChatId, from_chat_id: chatId, message_id: m.message_id, reply_parameters: { message_id: head.message_id } }).catch(() => {});
  if (Date.now() - (acked.get(chatId) || 0) > 10 * 60e3) {
    acked.set(chatId, Date.now()); if (acked.size > 5000) acked.clear();
    await send(chatId, '✅ Recibimos tu mensaje. Te respondemos por aquí lo antes posible (normalmente el mismo día). Si es sobre una compra, incluye tu número de pedido.');
  }
}
async function supportReply(m) {
  const id = ((m.reply_to_message?.text || m.reply_to_message?.caption || '').match(/#c(-?\d+)/) || [])[1];
  if (!id) return false;
  await tg('copyMessage', { chat_id: id, from_chat_id: m.chat.id, message_id: m.message_id });
  await send(m.chat.id, '✅ Enviado al cliente.');
  return true;
}

async function showCategories(chatId) {
  const cats = Products.categories();
  if (!cats.length) return send(chatId, 'Todavía no hay productos. ¡Vuelve pronto!');
  return send(chatId, '🛍️ <b>Elige una categoría</b>', {
    inline_keyboard: cats.map((c) => [{ text: `${c.category} (${c.n})`, callback_data: `cat:${c.category}`.slice(0, 64) }]),
  });
}

async function showCategory(chatId, cat) {
  const list = Products.list().filter((p) => p.category === cat).slice(0, 30);
  return send(chatId, `<b>${esc(cat)}</b>`, {
    inline_keyboard: [...list.map((p) => [{ text: `${p.emoji} ${p.title} · ${p.stars} ⭐`, callback_data: `prod:${p.id}` }]),
      [{ text: '⬅️ Categorías', callback_data: 'cats' }]],
  });
}

async function showProduct(chatId, p) {
  if (!p || !p.active) return send(chatId, 'Ese producto ya no está disponible.');
  const text = `${p.emoji} <b>${esc(p.title)}</b>\n\n${esc(p.short)}\n\n${esc(p.description).slice(0, 700)}\n\n💫 Precio: <b>${p.stars} ⭐</b>`;
  return send(chatId, text, {
    inline_keyboard: [[{ text: `Comprar por ${p.stars} ⭐`, callback_data: `buy:${p.id}` }],
      [{ text: '⬅️ Volver', callback_data: `cat:${p.category}`.slice(0, 64) }]],
  });
}

/** Crea pedido Stars y devuelve los parámetros de factura (sirve para el chat y para la Mini App). */
export function starsInvoice(product, chatId) {
  const order = Orders.create({ product_id: product.id, telegram_chat_id: chatId, method: 'stars', amount_cents: product.stars, currency: 'XTR' });
  return {
    order,
    params: {
      title: product.title.slice(0, 32),
      description: (product.short || product.title).slice(0, 255),
      payload: order.id,
      currency: 'XTR',
      prices: [{ label: product.title.slice(0, 32), amount: product.stars }],
    },
  };
}

async function myOrders(chatId) {
  const rows = Orders.recent(200).filter((o) => o.telegram_chat_id === String(chatId) && o.status === 'paid').slice(0, 10);
  if (!rows.length) return send(chatId, 'Aún no tienes compras.', mainMenu());
  return send(chatId, '📦 <b>Tus compras</b> (enlaces nuevos de descarga):', {
    inline_keyboard: rows.map((o) => [{ text: `⬇️ ${o.title}`, url: downloadLink(o.id) }]),
  });
}

async function onMessage(m) {
  const chatId = m.chat.id;
  if (m.successful_payment) {
    const sp = m.successful_payment;
    const order = Orders.get(sp.invoice_payload);
    if (order && Orders.markPaid(order.id, sp.telegram_payment_charge_id)) {
      Orders.update(order.id, { telegram_chat_id: String(chatId) });
      await deliver(order.id);
    }
    return;
  }
  const text = (m.text || '').trim();
  const [cmd, ...args] = text.split(/\s+/);
  const arg = args.join(' ');

  switch (cmd.split('@')[0]) {
    case '/start': {
      if (arg.startsWith('o_')) { // vincular un pedido hecho en la web
        const o = Orders.get(arg.slice(2));
        if (!o) return send(chatId, 'No encontré ese pedido.');
        Orders.update(o.id, { telegram_chat_id: String(chatId) });
        if (o.status === 'paid') return deliver(o.id);
        return send(chatId, `✅ Pedido <code>${o.id}</code> vinculado. Te enviaré el producto aquí en cuanto se confirme el pago.`);
      }
      if (arg.startsWith('p_')) return showProduct(chatId, Products.bySlug(arg.slice(2)));
      if (arg === 'soporte') return send(chatId, `👋 ¡Hola${m.from?.first_name ? ' ' + esc(m.from.first_name) : ''}! Este es el soporte de <b>${esc(config.storeName)}</b>.\n\nEscríbenos aquí tu pregunta (si es sobre una compra, con tu número de pedido) y te respondemos por este chat.`);
      return send(chatId, `👋 ¡Hola${m.from?.first_name ? ' ' + esc(m.from.first_name) : ''}! Bienvenido a <b>${esc(config.storeName)}</b>.\n\nProductos digitales con entrega inmediata. Paga con Telegram Stars ⭐ y recibe tu archivo aquí mismo.`, mainMenu());
    }
    case '/catalogo': return showCategories(chatId);
    case '/mispedidos': return myOrders(chatId);
    case '/id': return send(chatId, `Tu chat id: <code>${chatId}</code>`);
    case '/paysupport':
    case '/soporte':
      if (arg) return toSupport({ ...m, text: arg });
      return send(chatId, '💬 Escríbenos aquí mismo tu pregunta o problema (con tu número de pedido si es sobre una compra) y te respondemos por este chat.');
    case '/terminos':
      return send(chatId, `Términos y privacidad: ${config.baseUrl}/legal`);
  }

  if (!isAdmin(chatId)) {
    if (text.startsWith('/')) return send(chatId, 'Usa el menú 👇', mainMenu());
    return toSupport(m);  // cualquier mensaje normal del cliente va a soporte
  }
  if (m.reply_to_message && await supportReply(m).catch((e) => { send(chatId, `⚠️ No pude enviarlo: ${esc(e.message)}`); return true; })) return;

  // ===== Comandos de administrador =====
  switch (cmd) {
    case '/linkresena': {  // enlace para alguien a quien le regalaste el producto a cambio de su opinión sincera
      const p = Products.bySlug(arg) || Products.byId(Number(arg)) || Products.list({ all: true }).find((x) => arg && x.title.toLowerCase().includes(arg.toLowerCase()));
      if (!p) return send(chatId, 'Uso: <code>/linkresena panel</code> (parte del nombre del producto). Genera un enlace para que alguien a quien le regalaste el producto deje su opinión; saldrá marcada como "lo recibió gratis".');
      return send(chatId, `🎁 Enlace de opinión para <b>${esc(p.title)}</b> (uno por persona, mándaselo junto con el producto):\n${reviewLink({ k: 'g', p: p.id, c: crypto.randomBytes(4).toString('hex') })}`);
    }
    case '/pendientes': {
      const list = Orders.byStatus('review');
      if (!list.length) return send(chatId, 'No hay pagos Binance por revisar.');
      for (const o of list) await askBinance(o);
      return;
    }
    case '/ventas': {
      const s = Orders.stats();
      return send(chatId, `📊 Ventas pagadas: <b>${s.orders}</b>\nUSD: <b>${usd(s.usd_cents)}</b>\nStars: <b>${s.stars} ⭐</b>`);
    }
    case '/reembolso': {
      const o = Orders.get(arg);
      if (!o || o.method !== 'stars' || o.status !== 'paid') return send(chatId, 'Uso: /reembolso CODIGO (solo pedidos pagados con Stars)');
      await tg('refundStarPayment', { user_id: Number(o.telegram_chat_id), telegram_payment_charge_id: o.provider_ref });
      Orders.update(o.id, { status: 'rejected' });
      return send(chatId, `↩️ Reembolsado ${o.id}`);
    }
    case '/entregar': {
      const o = Orders.get(arg);
      if (!o) return send(chatId, 'Uso: /entregar CODIGO');
      const via = await deliver(o.id);
      return send(chatId, `Reenviado ${o.id} por: ${via.join(', ') || 'ningún canal'}`);
    }
    default:
      return send(chatId, 'Admin: /pendientes · /ventas · /entregar CODIGO · /reembolso CODIGO');
  }
}

export async function askBinance(o) {
  return notifyAdmin(
    `🟡 <b>Pago Binance por revisar</b>\nPedido <code>${o.id}</code> · ${esc(o.title || '')}\nImporte esperado: <b>${(o.amount_cents / 100).toFixed(2)} USDT</b>\nID de orden Binance del cliente: <code>${esc(o.provider_ref)}</code>\nContacto: ${esc(o.email || o.whatsapp || o.telegram_chat_id || '-')}`,
    { reply_markup: { inline_keyboard: [[{ text: '✅ Confirmar', callback_data: `bok:${o.id}` }, { text: '❌ Rechazar', callback_data: `bno:${o.id}` }]] } },
  );
}

async function onCallback(q) {
  const chatId = q.message?.chat.id ?? q.from.id;
  const [action, value] = q.data.split(/:(.*)/s);
  await tg('answerCallbackQuery', { callback_query_id: q.id }).catch(() => {});
  if (action === 'rv' && isAdmin(q.from.id)) {
    const [what, id] = value.split(':'); const r = Reviews.get(Number(id)); if (!r) return;
    Reviews.setStatus(r.id, what === 'ok' ? 'approved' : 'rejected');
    return tg('editMessageReplyMarkup', { chat_id: chatId, message_id: q.message.message_id,
      reply_markup: { inline_keyboard: [[{ text: what === 'ok' ? '✅ Publicada en la tienda' : '🚫 Rechazada', callback_data: 'x' }]] } }).catch(() => {});
  }
  if (action === 'cats') return showCategories(chatId);
  if (action === 'cat') return showCategory(chatId, value);
  if (action === 'prod') return showProduct(chatId, Products.byId(Number(value)));
  if (action === 'mine') return myOrders(chatId);
  if (action === 'buy') {
    const p = Products.byId(Number(value));
    if (!p?.active || !p.stars) return send(chatId, 'Producto no disponible.');
    const { params } = starsInvoice(p, chatId);
    return tg('sendInvoice', { chat_id: chatId, ...params });
  }
  if ((action === 'bok' || action === 'bno') && isAdmin(chatId)) {
    const o = Orders.get(value);
    if (!o) return;
    if (action === 'bok') {
      if (Orders.markPaid(o.id)) await deliver(o.id);
      return tg('editMessageText', { chat_id: chatId, message_id: q.message.message_id, text: `✅ Pedido ${o.id} confirmado y entregado.` });
    }
    Orders.update(o.id, { status: 'rejected' });
    if (o.telegram_chat_id) send(o.telegram_chat_id, `❌ No pudimos verificar el pago del pedido <code>${o.id}</code>. Escríbenos con /soporte.`).catch(() => {});
    return tg('editMessageText', { chat_id: chatId, message_id: q.message.message_id, text: `❌ Pedido ${o.id} rechazado.` });
  }
}

async function onPreCheckout(q) {
  const o = Orders.get(q.invoice_payload);
  const ok = !!o && o.status === 'pending' && o.method === 'stars' && q.total_amount === o.amount_cents && q.currency === 'XTR';
  return tg('answerPreCheckoutQuery', { pre_checkout_query_id: q.id, ok, ...(ok ? {} : { error_message: 'El pedido ya no es válido. Inténtalo de nuevo.' }) });
}

export async function startBot() {
  if (!tgEnabled()) { console.log('[bot] TELEGRAM_BOT_TOKEN vacío: bot desactivado.'); return; }
  await tg('deleteWebhook', {}).catch(() => {});
  await tg('setMyCommands', { commands: [
    { command: 'start', description: 'Inicio' },
    { command: 'catalogo', description: 'Ver productos' },
    { command: 'mispedidos', description: 'Mis compras y descargas' },
    { command: 'paysupport', description: 'Ayuda con un pago' }, { command: 'soporte', description: 'Hablar con soporte' },
    { command: 'terminos', description: 'Términos y privacidad' },
  ] }).catch((e) => console.error(e.message));
  console.log('[bot] escuchando mensajes…');
  let offset = 0;
  for (;;) {
    try {
      const updates = await tg('getUpdates', { offset, timeout: 30, allowed_updates: ['message', 'callback_query', 'pre_checkout_query'] });
      for (const u of updates) {
        offset = u.update_id + 1;
        try {
          if (u.pre_checkout_query) await onPreCheckout(u.pre_checkout_query);
          else if (u.callback_query) await onCallback(u.callback_query);
          else if (u.message) await onMessage(u.message);
        } catch (e) { console.error('[bot]', e.message); }
      }
    } catch (e) {
      console.error('[bot] polling:', e.message);
      await new Promise((r) => setTimeout(r, 5000));
    }
  }
}
