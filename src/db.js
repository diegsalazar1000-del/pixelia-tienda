// Base de datos SQLite integrada en Node (node:sqlite). Un solo archivo en data/tienda.db.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { DatabaseSync } from 'node:sqlite';
import { config } from './config.js';

fs.mkdirSync(path.dirname(config.paths.db), { recursive: true });
fs.mkdirSync(config.paths.files, { recursive: true });

export const db = new DatabaseSync(config.paths.db);
db.exec('PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;');

db.exec(`
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  short TEXT DEFAULT '',
  description TEXT DEFAULT '',
  category TEXT DEFAULT 'General',
  price_cents INTEGER NOT NULL,          -- precio en USD (centavos)
  compare_cents INTEGER DEFAULT 0,       -- precio tachado opcional
  stars INTEGER NOT NULL DEFAULT 0,      -- precio en Telegram Stars
  emoji TEXT DEFAULT '✨',
  color TEXT DEFAULT '#7c5cff',
  cover_url TEXT DEFAULT '',
  file_name TEXT DEFAULT '',             -- archivo en storage/products
  external_url TEXT DEFAULT '',          -- alternativa: enlace de entrega (Drive, Notion...)
  license_type TEXT DEFAULT 'PLR',       -- PLR / MRR / RR / Propio
  license_note TEXT DEFAULT '',          -- dónde compraste la licencia, condiciones
  i18n TEXT DEFAULT '{}',                -- traducciones: {"en":{"title":..,"short":..,"description":..}}
  featured INTEGER DEFAULT 0,
  active INTEGER DEFAULT 1,
  sales INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,                   -- código corto visible al cliente
  product_id INTEGER NOT NULL REFERENCES products(id),
  email TEXT DEFAULT '',
  whatsapp TEXT DEFAULT '',
  telegram_chat_id TEXT DEFAULT '',
  lang TEXT DEFAULT 'es',
  method TEXT NOT NULL,                  -- paypal / binance / stars
  amount_cents INTEGER NOT NULL,         -- importe exacto a cobrar (USD centavos o Stars)
  currency TEXT NOT NULL,                -- USD / USDT / XTR
  status TEXT NOT NULL DEFAULT 'pending',-- pending / review / paid / rejected
  provider_ref TEXT DEFAULT '',          -- id PayPal, id de orden Binance, charge id de Stars
  downloads INTEGER DEFAULT 0,
  delivered_via TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now')),
  paid_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
`);

export const newOrderId = () =>
  'P' + crypto.randomBytes(4).toString('hex').toUpperCase().slice(0, 7);

export const Products = {
  list: ({ all = false } = {}) =>
    db.prepare(`SELECT * FROM products ${all ? '' : 'WHERE active = 1'} ORDER BY featured DESC, sales DESC, id DESC`).all(),
  bySlug: (slug) => db.prepare('SELECT * FROM products WHERE slug = ?').get(slug),
  byId: (id) => db.prepare('SELECT * FROM products WHERE id = ?').get(id),
  categories: () => db.prepare('SELECT category, COUNT(*) n FROM products WHERE active = 1 GROUP BY category ORDER BY n DESC').all(),
  upsert(p) {
    const fields = ['slug', 'title', 'short', 'description', 'category', 'price_cents', 'compare_cents', 'stars', 'emoji',
      'color', 'cover_url', 'file_name', 'external_url', 'license_type', 'license_note', 'i18n', 'featured', 'active'];
    const data = Object.fromEntries(fields.filter((f) => p[f] !== undefined).map((f) => [f, p[f]]));
    if (p.id) {
      const sets = Object.keys(data).map((k) => `${k} = :${k}`).join(', ');
      db.prepare(`UPDATE products SET ${sets} WHERE id = :id`).run({ ...data, id: p.id });
      return Products.byId(p.id);
    }
    const keys = Object.keys(data);
    db.prepare(`INSERT INTO products (${keys.join(',')}) VALUES (${keys.map((k) => ':' + k).join(',')})`).run(data);
    return Products.bySlug(data.slug);
  },
  remove: (id) => db.prepare('UPDATE products SET active = 0 WHERE id = ?').run(id),
};

export const Orders = {
  create(o) {
    const id = newOrderId();
    db.prepare(`INSERT INTO orders (id, product_id, email, whatsapp, telegram_chat_id, lang, method, amount_cents, currency, status, provider_ref)
      VALUES (?,?,?,?,?,?,?,?,?,?,?)`).run(id, o.product_id, o.email || '', o.whatsapp || '', String(o.telegram_chat_id || ''),
      o.lang || 'es', o.method, o.amount_cents, o.currency, o.status || 'pending', o.provider_ref || '');
    return Orders.get(id);
  },
  get: (id) => db.prepare('SELECT * FROM orders WHERE id = ?').get(String(id || '').toUpperCase()),
  withProduct: (id) => db.prepare(`SELECT o.*, p.title, p.slug, p.file_name, p.external_url, p.emoji
    FROM orders o JOIN products p ON p.id = o.product_id WHERE o.id = ?`).get(String(id || '').toUpperCase()),
  update(id, data) {
    const sets = Object.keys(data).map((k) => `${k} = :${k}`).join(', ');
    db.prepare(`UPDATE orders SET ${sets} WHERE id = :id`).run({ ...data, id });
    return Orders.get(id);
  },
  /** Marca como pagado una sola vez (idempotente). Devuelve true si cambió. */
  markPaid(id, ref = '') {
    const r = db.prepare(`UPDATE orders SET status = 'paid', paid_at = datetime('now'), provider_ref = COALESCE(NULLIF(?, ''), provider_ref)
      WHERE id = ? AND status IN ('pending','review')`).run(ref, id);
    if (r.changes) db.prepare('UPDATE products SET sales = sales + 1 WHERE id = (SELECT product_id FROM orders WHERE id = ?)').run(id);
    return r.changes > 0;
  },
  recent: (limit = 50) => db.prepare(`SELECT o.*, p.title FROM orders o JOIN products p ON p.id = o.product_id
    ORDER BY o.created_at DESC LIMIT ?`).all(limit),
  byStatus: (status) => db.prepare(`SELECT o.*, p.title FROM orders o JOIN products p ON p.id = o.product_id
    WHERE o.status = ? ORDER BY o.created_at`).all(status),
  /** Importe pendiente ya usado (para que cada pedido Binance tenga un importe único). */
  amountTaken: (cents) => !!db.prepare(`SELECT 1 FROM orders WHERE method='binance' AND status IN ('pending','review')
    AND amount_cents = ? AND created_at > datetime('now','-2 days')`).get(cents),
  stats: () => db.prepare(`SELECT COUNT(*) orders, COALESCE(SUM(CASE WHEN currency!='XTR' THEN amount_cents END),0) usd_cents,
    COALESCE(SUM(CASE WHEN currency='XTR' THEN amount_cents END),0) stars FROM orders WHERE status='paid'`).get(),
};
