// Binance Pay (cuenta personal), semiautomático.
// 1) Cada pedido recibe un importe único en USDT (ej. 9.99 → 10.03) para identificarlo.
// 2) El cliente paga a tu Binance Pay ID y pega el "ID de orden" de Binance en la web.
// 3a) Si configuras una API key de solo lectura, se verifica sola contra tu historial de Binance Pay.
// 3b) Si no, te llega un aviso a Telegram con botones Confirmar / Rechazar.
import crypto from 'node:crypto';
import { config } from '../config.js';
import { Orders } from '../db.js';

export const binanceEnabled = () => !!config.binance.payId;
export const binanceAutoVerify = () => !!(config.binance.apiKey && config.binance.apiSecret);

/** Calcula un importe único (céntimos extra 1–49) para no confundir pagos simultáneos. */
export function uniqueAmount(baseCents) {
  for (let i = 0; i < 60; i++) {
    const c = baseCents + 1 + Math.floor(Math.random() * 49);
    if (!Orders.amountTaken(c)) return c;
  }
  return baseCents + 50;
}

async function payHistory() {
  const qs = `timestamp=${Date.now()}&recvWindow=10000&limit=100`;
  const sig = crypto.createHmac('sha256', config.binance.apiSecret).update(qs).digest('hex');
  const res = await fetch(`https://api.binance.com/sapi/v1/pay/transactions?${qs}&signature=${sig}`, {
    headers: { 'X-MBX-APIKEY': config.binance.apiKey },
  });
  const data = await res.json();
  if (!res.ok) throw new Error('Binance: ' + JSON.stringify(data));
  return data.data || [];
}

/** Busca un pago recibido que coincida con el pedido. Devuelve el id de la transacción o ''. */
export async function findBinancePayment(order) {
  if (!binanceAutoVerify()) return '';
  const since = new Date(order.created_at + 'Z').getTime() - 60_000;
  const tx = await payHistory();
  const hit = tx.find((t) => {
    const amount = Math.round(Number(t.amount) * 100);
    const received = amount > 0 && ['USDT', 'USDC', 'FDUSD'].includes(t.currency);
    const sameRef = order.provider_ref && [t.orderId, t.transactionId].map(String).includes(order.provider_ref);
    return received && Number(t.transactionTime) >= since && ((sameRef && amount >= order.amount_cents) || amount === order.amount_cents);
  });
  return hit ? String(hit.transactionId) : '';
}
