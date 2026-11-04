// Carga .env sin dependencias y expone la configuración.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const envFile = path.join(ROOT, '.env');
if (fs.existsSync(envFile)) {
  for (const line of fs.readFileSync(envFile, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (!m || line.trim().startsWith('#')) continue;
    let v = m[2];
    if (/^".*"$|^'.*'$/.test(v)) v = v.slice(1, -1);
    if (process.env[m[1]] === undefined) process.env[m[1]] = v;
  }
}

const e = (k, d = '') => process.env[k] ?? d;

export const config = {
  port: Number(e('PORT', '3000')),
  baseUrl: e('BASE_URL', 'http://localhost:3000').replace(/\/$/, ''),
  storeName: e('STORE_NAME', 'Tienda Digital'),
  defaultLang: e('DEFAULT_LANG', 'es'),
  secret: e('APP_SECRET', 'dev-secret'),
  adminPassword: e('ADMIN_PASSWORD', ''),
  maxDownloads: Number(e('MAX_DOWNLOADS', '5')),
  linkHours: Number(e('LINK_HOURS', '72')),
  telegram: {
    token: e('TELEGRAM_BOT_TOKEN'),
    username: e('TELEGRAM_BOT_USERNAME'),
    adminChatId: e('TELEGRAM_ADMIN_CHAT_ID'),
  },
  paypal: {
    mode: e('PAYPAL_MODE', 'sandbox'),
    clientId: e('PAYPAL_CLIENT_ID'),
    secret: e('PAYPAL_CLIENT_SECRET'),
  },
  binance: {
    payId: e('BINANCE_PAY_ID'),
    apiKey: e('BINANCE_API_KEY'),
    apiSecret: e('BINANCE_API_SECRET'),
  },
  email: { resendKey: e('RESEND_API_KEY'), from: e('EMAIL_FROM') },
  whatsapp: {
    token: e('WHATSAPP_TOKEN'),
    phoneId: e('WHATSAPP_PHONE_NUMBER_ID'),
    template: e('WHATSAPP_TEMPLATE', 'entrega_pedido'),
    templateLang: e('WHATSAPP_TEMPLATE_LANG', 'es'),
  },
  paths: {
    db: path.join(ROOT, 'data', 'tienda.db'),
    files: path.join(ROOT, 'storage', 'products'),
    public: path.join(ROOT, 'public'),
  },
};

if (config.secret === 'dev-secret' || config.secret.startsWith('cambia')) {
  console.warn('[aviso] APP_SECRET no está configurado: cámbialo antes de vender.');
}
