// Cliente mínimo de la Bot API de Telegram (usa fetch nativo).
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { config } from '../config.js';

const base = () => `https://api.telegram.org/bot${config.telegram.token}`;
export const tgEnabled = () => !!config.telegram.token;

export async function tg(method, params = {}) {
  if (!tgEnabled()) throw new Error('TELEGRAM_BOT_TOKEN no configurado');
  const res = await fetch(`${base()}/${method}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(params),
  });
  const data = await res.json();
  if (!data.ok) throw new Error(`Telegram ${method}: ${data.description}`);
  return data.result;
}

/** Envía un archivo local como documento (máx. 50 MB por la Bot API). */
export async function tgSendFile(chatId, filePath, caption = '') {
  const form = new FormData();
  form.append('chat_id', String(chatId));
  if (caption) { form.append('caption', caption); form.append('parse_mode', 'HTML'); }
  const buf = await fs.promises.readFile(filePath);
  form.append('document', new Blob([buf]), path.basename(filePath));
  const res = await fetch(`${base()}/sendDocument`, { method: 'POST', body: form });
  const data = await res.json();
  if (!data.ok) throw new Error(`Telegram sendDocument: ${data.description}`);
  return data.result;
}

export const notifyAdmin = (text, extra = {}) =>
  config.telegram.adminChatId && tgEnabled()
    ? tg('sendMessage', { chat_id: config.telegram.adminChatId, text, parse_mode: 'HTML', ...extra }).catch((e) => console.error(e.message))
    : Promise.resolve();

/** Valida el initData que envía una Mini App de Telegram. Devuelve el usuario o null. */
export function verifyInitData(initData) {
  if (!initData || !config.telegram.token) return null;
  const params = new URLSearchParams(initData);
  const hash = params.get('hash');
  params.delete('hash');
  const check = [...params.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${k}=${v}`).join('\n');
  const secret = crypto.createHmac('sha256', 'WebAppData').update(config.telegram.token).digest();
  const calc = crypto.createHmac('sha256', secret).update(check).digest('hex');
  if (!hash || calc.length !== hash.length || !crypto.timingSafeEqual(Buffer.from(calc), Buffer.from(hash))) return null;
  if (Date.now() / 1000 - Number(params.get('auth_date') || 0) > 86400) return null;
  try { return JSON.parse(params.get('user') || 'null'); } catch { return null; }
}

export const esc = (s) => String(s ?? '').replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
