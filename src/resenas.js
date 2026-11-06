// Reseñas reales: enlace firmado por cliente (compra, regalo o producto regalado para opinar), moderación del admin en Telegram.
import crypto from 'node:crypto';
import { config } from './config.js';
import { Products, Orders, Reviews } from './db.js';
import { sendEmail } from './delivery/email.js';
import { tg, tgEnabled, esc } from './telegram/api.js';

export const GIFT_SLUGS = { ahorro: 'regalo-reto-de-ahorro-52-semanas-2027', navidad: 'regalo-planificador-navideno' };
const sig = (s) => crypto.createHmac('sha256', config.secret).update('resena:' + s).digest('base64url').slice(0, 22);
export const makeToken = (o) => { const s = Buffer.from(JSON.stringify(o)).toString('base64url'); return `${s}.${sig(s)}`; };
export function readToken(t) {
  const [s, h] = String(t || '').split('.');
  if (!s || !h || sig(s) !== h) return null;
  try { return JSON.parse(Buffer.from(s, 'base64url').toString()); } catch { return null; }
}
export const reviewLink = (o) => `${config.baseUrl}/resena?t=${makeToken(o)}`;

/** Qué productos puede reseñar quien tiene este enlace. */
export function targets(tok) {
  if (tok?.k === 'o') { const o = Orders.get(tok.id); if (!o || o.status !== 'paid') return []; return [{ p: Products.byId(o.product_id), ref: 'o:' + o.id, source: 'compra' }]; }
  if (tok?.k === 's') return (tok.g || []).map((g) => Products.bySlug(GIFT_SLUGS[g])).filter(Boolean).map((p) => ({ p, ref: 's:' + tok.e, source: 'regalo' }));
  if (tok?.k === 'g') { const p = Products.byId(tok.p); return p ? [{ p, ref: 'g:' + tok.c, source: 'gratis' }] : []; }
  return [];
}

export function notifyReview(r, p) {
  if (!tgEnabled() || !config.telegram.adminChatId) return;
  const lab = { compra: '✅ Compra verificada', regalo: '🎁 Descargó el regalo', gratis: '🎁 Recibió el producto gratis' }[r.source];
  tg('sendMessage', { chat_id: config.telegram.adminChatId, parse_mode: 'HTML',
    text: `⭐ <b>Reseña nueva</b> · ${esc(p.title)}\n${'★'.repeat(r.stars)}${'☆'.repeat(5 - r.stars)} · ${esc(r.name || 'Anónimo')} · ${lab}\n\n${esc(r.text || '(sin comentario)')}\n\n<i>Publica todas las opiniones reales, también las regulares o malas (responderlas da confianza). Rechaza solo spam, insultos, datos personales o lo que no tenga que ver con el producto.</i>`,
    reply_markup: { inline_keyboard: [[{ text: '✅ Publicar', callback_data: `rv:ok:${r.id}` }, { text: '🚫 Rechazar (spam/insulto)', callback_data: `rv:no:${r.id}` }]] } }).catch(() => {});
}

const mail = (to, title, link, extra = '') => sendEmail(to, `⭐ ¿Qué te pareció ${title}?`, `Cuéntanos en 1 minuto: ${link}`,
  `<div style="font-family:system-ui,sans-serif;max-width:520px;margin:auto;padding:24px;background:#0f0f1a;color:#eee;border-radius:16px">
   <h2 style="margin:0 0 10px">¿Qué te pareció ${esc(title)}? ⭐</h2>
   <p>Tu opinión nos ayuda a mejorar y ayuda a otras personas a decidir. Es 1 minuto: toca las estrellas y, si quieres, deja un comentario.</p>
   <p><a style="display:inline-block;background:#ff4fa3;color:#fff;padding:12px 18px;border-radius:12px;text-decoration:none;font-weight:700" href="${link}">⭐⭐⭐⭐⭐ Dejar mi opinión</a></p>${extra}
   <p style="color:#aab;font-size:13px">¿Algún problema con tu archivo? Escríbenos por Telegram: https://t.me/${config.telegram.username || ''}?start=soporte</p></div>`);

/** Cada hora: pide opinión a compras de hace 2+ días y a quienes descargaron un regalo ayer. */
export async function askReviews() {
  for (const o of Reviews.ordersToAsk()) {
    Reviews.markOrderAsked(o.id);
    const p = Products.byId(o.product_id); if (!p) continue;
    const link = reviewLink({ k: 'o', id: o.id });
    if (o.email && config.email.resendKey) await mail(o.email, p.title, link).catch((e) => console.error('[reseñas]', e.message));
    if (o.telegram_chat_id && tgEnabled()) await tg('sendMessage', { chat_id: o.telegram_chat_id, text: `⭐ ¿Qué te pareció <b>${esc(p.title)}</b>? Cuéntanos en 1 minuto: ${link}`, parse_mode: 'HTML' }).catch(() => {});
  }
  if (!config.email.resendKey) return;
  for (const s of Reviews.subsToAsk()) {
    Reviews.markSubAsked(s.email);
    const g = s.source.replace('regalo:', '').split('+').filter((x) => GIFT_SLUGS[x]);
    if (!g.length) continue;
    await mail(s.email, g.length > 1 ? 'tus regalos' : 'tu regalo', reviewLink({ k: 's', e: s.email, g }),
      s.used_order ? '' : `<p>Recuerda que tu cupón <b>${s.code}</b> te da 15% en tu primera compra 💜</p>`).catch((e) => console.error('[reseñas]', e.message));
  }
}
export function startReviews() { setTimeout(() => askReviews().catch(() => {}), 60e3); setInterval(() => askReviews().catch(() => {}), 3600e3); }
