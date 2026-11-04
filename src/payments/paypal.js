// PayPal Checkout (Orders v2). Automático: el servidor crea la orden y la captura.
import { config } from '../config.js';

const api = () => (config.paypal.mode === 'live' ? 'https://api-m.paypal.com' : 'https://api-m.sandbox.paypal.com');
export const paypalEnabled = () => !!(config.paypal.clientId && config.paypal.secret);

let cached = { token: '', exp: 0 };
async function token() {
  if (cached.token && cached.exp > Date.now()) return cached.token;
  const res = await fetch(`${api()}/v1/oauth2/token`, {
    method: 'POST',
    headers: {
      Authorization: 'Basic ' + Buffer.from(`${config.paypal.clientId}:${config.paypal.secret}`).toString('base64'),
      'content-type': 'application/x-www-form-urlencoded',
    },
    body: 'grant_type=client_credentials',
  });
  const data = await res.json();
  if (!res.ok) throw new Error('PayPal auth: ' + JSON.stringify(data));
  cached = { token: data.access_token, exp: Date.now() + (data.expires_in - 60) * 1000 };
  return cached.token;
}

export async function createPaypalOrder(order, product) {
  const res = await fetch(`${api()}/v2/checkout/orders`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${await token()}`, 'content-type': 'application/json', 'PayPal-Request-Id': order.id },
    body: JSON.stringify({
      intent: 'CAPTURE',
      purchase_units: [{
        reference_id: order.id,
        custom_id: order.id,
        description: product.title.slice(0, 120),
        amount: { currency_code: 'USD', value: (order.amount_cents / 100).toFixed(2) },
      }],
      application_context: { brand_name: config.storeName, shipping_preference: 'NO_SHIPPING', user_action: 'PAY_NOW' },
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error('PayPal create: ' + JSON.stringify(data));
  return data.id;
}

/** Captura y comprueba que el importe y la referencia coinciden con nuestro pedido. */
export async function capturePaypalOrder(paypalId, order) {
  const res = await fetch(`${api()}/v2/checkout/orders/${encodeURIComponent(paypalId)}/capture`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${await token()}`, 'content-type': 'application/json' },
  });
  const data = await res.json();
  if (!res.ok && data?.details?.[0]?.issue !== 'ORDER_ALREADY_CAPTURED') throw new Error('PayPal capture: ' + JSON.stringify(data));
  const unit = data.purchase_units?.[0];
  const cap = unit?.payments?.captures?.[0];
  const ok = data.status === 'COMPLETED' && unit?.reference_id === order.id &&
    cap?.status === 'COMPLETED' && Math.round(Number(cap.amount.value) * 100) === order.amount_cents;
  return { ok, captureId: cap?.id || '' };
}
