// Entrega de productos: genera enlace firmado y lo envía por correo, Telegram y/o WhatsApp.
import crypto from 'node:crypto';
import path from 'node:path';
import fs from 'node:fs';
import { config } from '../config.js';
import { Orders } from '../db.js';
import { tg, tgSendFile, tgEnabled, notifyAdmin, esc } from '../telegram/api.js';
import { sendEmail } from './email.js';
import { sendWhatsApp } from './whatsapp.js';
import { metaPurchase } from '../meta.js';

const sign = (data) => crypto.createHmac('sha256', config.secret).update(data).digest('base64url').slice(0, 32);

export function downloadLink(orderId) {
  const exp = Math.floor(Date.now() / 1000) + config.linkHours * 3600;
  return `${config.baseUrl}/d/${orderId}/${exp}/${sign(`${orderId}.${exp}`)}`;
}

export function verifyDownload(orderId, exp, sig) {
  const good = sign(`${orderId}.${exp}`);
  if (!sig || sig.length !== good.length || !crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(good))) return 'firma';
  if (Number(exp) < Date.now() / 1000) return 'caducado';
  return null;
}

/** Entrega un pedido pagado por todos los canales que tengamos del cliente. */
export async function deliver(orderId) {
  const o = Orders.withProduct(orderId);
  if (!o || o.status !== 'paid') return [];
  const link = downloadLink(o.id);
  const via = [];
  const msg = `¡Gracias por tu compra! 🎉\n\nProducto: ${o.title}\nPedido: ${o.id}\n\nDescarga: ${link}\n(El enlace dura ${config.linkHours} h y admite ${config.maxDownloads} descargas.)`;

  if (o.telegram_chat_id && tgEnabled()) {
    try {
      const file = o.file_name && path.join(config.paths.files, o.file_name);
      if (!o.bump_id && file && fs.existsSync(file) && fs.statSync(file).size < 49 * 1024 * 1024) {
        await tgSendFile(o.telegram_chat_id, file, `🎉 <b>${esc(o.title)}</b>\nPedido <code>${o.id}</code>. ¡Gracias por tu compra!`);
      } else {
        await tg('sendMessage', {
          chat_id: o.telegram_chat_id, parse_mode: 'HTML',
          text: `🎉 <b>¡Pago confirmado!</b>\n\n${esc(o.title)}\nPedido <code>${o.id}</code>`,
          reply_markup: { inline_keyboard: [[{ text: '⬇️ Descargar', url: link }]] },
        });
      }
      via.push('telegram');
    } catch (e) { console.error('[entrega telegram]', e.message); }
  }
  if (o.email) {
    try { await sendEmail(o.email, `Tu compra: ${o.title}`, msg, emailHtml(o, link)); via.push('email'); }
    catch (e) { console.error('[entrega email]', e.message); }
  }
  if (o.whatsapp) {
    try { await sendWhatsApp(o.whatsapp, link); via.push('whatsapp'); }
    catch (e) { console.error('[entrega whatsapp]', e.message); }
  }
  Orders.update(o.id, { delivered_via: via.join(',') });
  metaPurchase(o).catch((e) => console.error('[meta]', e.message));
  notifyAdmin(`💰 <b>Venta</b> ${esc(o.title)}\nPedido <code>${o.id}</code> · ${o.method} · ${o.currency === 'XTR' ? o.amount_cents + ' ⭐' : '$' + (o.amount_cents / 100).toFixed(2)}\nEntregado por: ${via.join(', ') || '⚠️ ningún canal (el cliente puede descargar desde la web)'}`);
  return via;
}

function emailHtml(o, link) {
  return `<div style="font-family:system-ui,sans-serif;max-width:520px;margin:auto;padding:24px;background:#0f0f1a;color:#eee;border-radius:16px">
  <h2 style="margin:0 0 8px">¡Gracias por tu compra! 🎉</h2>
  <p style="color:#aab">${esc(o.title)} · Pedido <b>${o.id}</b></p>
  <p><a href="${link}" style="display:inline-block;padding:14px 24px;background:#7c5cff;color:#fff;border-radius:12px;text-decoration:none;font-weight:600">Descargar ahora</a></p>
  <p style="color:#889;font-size:13px">El enlace dura ${config.linkHours} horas y admite ${config.maxDownloads} descargas.</p>
  <p style="color:#889;font-size:13px">${esc(config.storeName)}</p></div>`;
}
