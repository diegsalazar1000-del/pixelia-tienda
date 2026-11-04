// Meta Pixel (navegador) + API de Conversiones (servidor) para que Meta Ads sepa qué anuncio vendió.
import crypto from 'node:crypto';
import { config } from './config.js';

const sha = (v) => crypto.createHash('sha256').update(String(v).trim().toLowerCase()).digest('hex');

/** Fragmento HTML del píxel para insertar en el <head>. */
export function pixelSnippet() {
  const id = config.meta.pixelId;
  if (!id) return '<script>window.fbq=function(){};</script>';
  return `<script>!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');
fbq('init','${id.replace(/\D/g, '')}');fbq('track','PageView');</script>`;
}

/** Envía la compra por el servidor (con el mismo event_id que el píxel para no contarla dos veces). */
export async function metaPurchase(order) {
  const { pixelId, capiToken, testCode } = config.meta;
  if (!pixelId || !capiToken || order.currency === 'XTR') return;
  const user_data = {};
  if (order.email) user_data.em = [sha(order.email)];
  const body = {
    data: [{
      event_name: 'Purchase', event_time: Math.floor(Date.now() / 1000), event_id: order.id, action_source: 'website',
      event_source_url: `${config.baseUrl}/p/${order.slug}`, user_data,
      custom_data: { currency: 'USD', value: order.amount_cents / 100, content_ids: [order.slug], content_type: 'product' },
    }],
    ...(testCode ? { test_event_code: testCode } : {}),
  };
  const res = await fetch(`https://graph.facebook.com/v21.0/${pixelId}/events?access_token=${encodeURIComponent(capiToken)}`, {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
  });
  if (!res.ok) console.error('[meta capi]', res.status, await res.text());
}
