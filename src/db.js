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

-- Visitas diarias por producto (para saber qué se mira y no se compra)
CREATE TABLE IF NOT EXISTS product_views (
  product_id INTEGER NOT NULL, day TEXT NOT NULL, views INTEGER DEFAULT 0,
  PRIMARY KEY (product_id, day)
);

-- Radar: productos en tendencia encontrados por n8n
CREATE TABLE IF NOT EXISTS candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,                  -- etsy / tiktok / instagram / hotmart
  external_id TEXT NOT NULL,
  url TEXT DEFAULT '',
  title TEXT DEFAULT '',
  snippet TEXT DEFAULT '',
  price REAL DEFAULT 0,
  currency TEXT DEFAULT '',
  image TEXT DEFAULT '',
  keyword TEXT DEFAULT '',
  published_at TEXT DEFAULT '',          -- fecha de publicación en la fuente
  metrics TEXT DEFAULT '{}',             -- vistas, likes, favoritos, etc.
  trend_score REAL DEFAULT 0,            -- velocidad (interacción por día)
  ai_score REAL DEFAULT 0,               -- nota 1-10 de la IA
  ai TEXT DEFAULT '{}',                  -- análisis de la IA (idea, derechos, copy, anuncio)
  status TEXT DEFAULT 'new',             -- new / notified / buy / recreate / discarded / drafted / live
  product_id INTEGER,
  found_at TEXT DEFAULT (datetime('now')),
  UNIQUE(source, external_id)
);
`);

db.exec(`
CREATE TABLE IF NOT EXISTS ad_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL,
  options TEXT DEFAULT '{}',
  status TEXT DEFAULT 'queued',          -- queued / running / done / error
  result TEXT DEFAULT '{}',
  error TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);`);

// Migraciones suaves (columnas nuevas en tablas existentes)
for (const sql of [
  "ALTER TABLE products ADD COLUMN launched_at TEXT",
  "ALTER TABLE products ADD COLUMN retired_at TEXT",
  "ALTER TABLE products ADD COLUMN candidate_id INTEGER",
  "ALTER TABLE products ADD COLUMN bundle_ids TEXT DEFAULT ''",   // pack: ids de los productos incluidos, ej "3,5,8"
  // Página de producto que vende (8-nov): gancho emocional, galería, video, cuenta regresiva, muestra gratis y preguntas propias.
  "ALTER TABLE products ADD COLUMN gancho TEXT DEFAULT ''",
  "ALTER TABLE products ADD COLUMN gallery TEXT DEFAULT ''",        // JSON [{"url":"/img/..","cap":"texto"}]
  "ALTER TABLE products ADD COLUMN video_url TEXT DEFAULT ''",
  "ALTER TABLE products ADD COLUMN countdown TEXT DEFAULT ''",      // AAAA-MM-DD: "Faltan N días para…"
  "ALTER TABLE products ADD COLUMN countdown_label TEXT DEFAULT ''",
  "ALTER TABLE products ADD COLUMN sample_url TEXT DEFAULT ''",     // muestra gratis a cambio del correo
  "ALTER TABLE products ADD COLUMN sample_title TEXT DEFAULT ''",
  "ALTER TABLE products ADD COLUMN regalo_url TEXT DEFAULT ''",
  "ALTER TABLE products ADD COLUMN regalo_title TEXT DEFAULT ''",
  "ALTER TABLE products ADD COLUMN faq TEXT DEFAULT ''",            // JSON [{"q":"..","a":".."}] (se suman a las generales)
  "ALTER TABLE orders ADD COLUMN coupon TEXT DEFAULT ''",
  "ALTER TABLE orders ADD COLUMN upsell_of TEXT DEFAULT ''",
  "ALTER TABLE orders ADD COLUMN bump_id INTEGER",
  "ALTER TABLE orders ADD COLUMN prueba INTEGER DEFAULT 0",          // compra hecha en "modo dueño" (no cuenta en estadísticas)                  // "agrega también" en el pago (2º producto con descuento)      // pedido original cuando es "completa tu pack"
]) { try { db.exec(sql); } catch {} }
// Productos publicados por script sin precio en Stars (no salían para pagar con Telegram)
try { db.exec("UPDATE products SET stars = CAST((price_cents / 100.0 / 0.013) + 0.999 AS INTEGER) WHERE stars = 0 AND price_cents > 0"); } catch {}

// Suscriptores: dejan su correo a cambio de un cupón de primera compra
db.exec(`CREATE TABLE IF NOT EXISTS subscribers (
  email TEXT PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  source TEXT DEFAULT '',
  used_order TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);`);

export const COUPON_OFF = 0.15;  // 15 % en productos sueltos, una sola vez

export const Subscribers = {
  /** Devuelve el cupón del correo (lo crea si es nuevo). */
  add(email, source = '') {
    const e = String(email).trim().toLowerCase();
    const old = db.prepare('SELECT * FROM subscribers WHERE email = ?').get(e);
    if (old) return { ...old, existed: true };
    let code;
    do { code = 'HOLA-' + crypto.randomBytes(3).toString('hex').toUpperCase(); }
    while (db.prepare('SELECT 1 FROM subscribers WHERE code = ?').get(code));
    db.prepare('INSERT INTO subscribers (email, code, source) VALUES (?, ?, ?)').run(e, code, String(source).slice(0, 60));
    actividad('correo');
    return db.prepare('SELECT * FROM subscribers WHERE email = ?').get(e);
  },
  /** Cupón válido y sin usar (ignora mayúsculas y espacios). */
  valid(code) {
    const c = String(code || '').trim().toUpperCase();
    return c ? db.prepare('SELECT * FROM subscribers WHERE code = ? AND used_order IS NULL').get(c) || null : null;
  },
  count: () => db.prepare('SELECT COUNT(*) n, SUM(used_order IS NOT NULL) used FROM subscribers').get(),
  list: (limit = 500) => db.prepare('SELECT email, code, source, used_order, created_at FROM subscribers ORDER BY created_at DESC LIMIT ?').all(limit),
};

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
      'color', 'cover_url', 'file_name', 'external_url', 'license_type', 'license_note', 'i18n', 'featured', 'active',
      'launched_at', 'retired_at', 'candidate_id', 'bundle_ids',
      'gancho', 'gallery', 'video_url', 'countdown', 'countdown_label', 'sample_url', 'sample_title', 'faq', 'regalo_url', 'regalo_title'];
    // Al activarse por primera vez queda registrada la fecha de lanzamiento.
    if (p.active === 1 && !(p.id && Products.byId(p.id)?.launched_at)) p.launched_at = new Date().toISOString().slice(0, 19).replace('T', ' ');
    if (p.active === 1) p.retired_at = null;
    // Precio en Telegram Stars automático si no se puso (misma regla que el panel: 1 ⭐ ≈ $0,013)
    if (!Number(p.stars) && Number(p.price_cents) > 0 && !(p.id && Products.byId(p.id)?.stars)) p.stars = Math.ceil(p.price_cents / 100 / 0.013);
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
  /** Productos incluidos en un pack (vacío si no es pack). */
  bundleItems(p) {
    const ids = String(p?.bundle_ids || '').split(',').map(Number).filter(Boolean);
    return ids.map((i) => Products.byId(i)).filter(Boolean);
  },
  /** "Comprados juntos habitualmente": lo que más compran quienes compraron este; si no hay datos, misma categoría o el más vendido. */
  bumpFor(p) {
    const ok = (x) => x && x.id !== p.id && x.active && !x.bundle_ids && x.price_cents > 0 && (x.file_name || x.external_url);
    const co = db.prepare(`SELECT o2.product_id id, COUNT(*) n FROM orders o1 JOIN orders o2 ON o1.email = o2.email AND o1.email != '' AND o2.product_id != o1.product_id
      WHERE o1.product_id = ? AND o1.status = 'paid' AND o2.status = 'paid' AND o1.prueba = 0 AND o2.prueba = 0 GROUP BY o2.product_id ORDER BY n DESC LIMIT 5`).all(p.id);
    for (const r of co) { const x = Products.byId(r.id); if (ok(x)) return x; }
    const all = Products.list().filter(ok);
    return all.find((x) => x.category === p.category) || all.sort((a, b) => b.sales - a.sales)[0] || null;
  },
  /** Packs activos que incluyen este producto. */
  bundlesWith: (id) => db.prepare("SELECT * FROM products WHERE active = 1 AND bundle_ids != '' AND (',' || bundle_ids || ',') LIKE ?").all(`%,${Number(id)},%`),
  remove: (id) => db.prepare("UPDATE products SET active = 0, retired_at = datetime('now') WHERE id = ?").run(id),
  view: (id) => (actividad('visita'), db.prepare(`INSERT INTO product_views (product_id, day, views) VALUES (?, date('now'), 1)
    ON CONFLICT(product_id, day) DO UPDATE SET views = views + 1`).run(id)),
  /** Rendimiento de cada producto activo en los últimos N días. */
  performance(days = 7) {
    const since = `-${Number(days) || 7} days`;
    return db.prepare(`SELECT p.id, p.slug, p.title, p.price_cents, p.launched_at, p.candidate_id,
        CAST(julianday('now') - julianday(COALESCE(p.launched_at, p.created_at)) AS INTEGER) AS days_live,
        (SELECT COALESCE(SUM(views),0) FROM product_views v WHERE v.product_id = p.id AND v.day >= date('now', :since)) AS views,
        (SELECT COUNT(*) FROM orders o WHERE o.product_id = p.id AND o.created_at >= datetime('now', :since)) AS checkouts,
        (SELECT COUNT(*) FROM orders o WHERE o.product_id = p.id AND o.status = 'paid' AND o.prueba = 0 AND o.paid_at >= datetime('now', :since)) AS sales,
        (SELECT COALESCE(SUM(CASE WHEN o.currency = 'XTR' THEN o.amount_cents * 1.3 ELSE o.amount_cents END),0) FROM orders o
          WHERE o.product_id = p.id AND o.status = 'paid' AND o.prueba = 0 AND o.paid_at >= datetime('now', :since)) AS revenue_cents,
        p.sales AS sales_total
      FROM products p WHERE p.active = 1 ORDER BY sales DESC, views DESC`).all({ since });
  },
};

export const AdJobs = {
  /** Quita de la fila los trabajos que aún no empezaron. */
  cancelQueued: () => db.prepare("UPDATE ad_jobs SET status = 'cancelled', updated_at = datetime('now') WHERE status = 'queued'").run().changes,
  pending: () => db.prepare("SELECT status, COUNT(*) n FROM ad_jobs WHERE status IN ('queued','running') GROUP BY status").all(),
  enqueue(productId, options = {}) {
    const dup = db.prepare("SELECT id FROM ad_jobs WHERE product_id = ? AND status IN ('queued','running') AND options = ?").get(productId, JSON.stringify(options));
    if (dup) return { id: dup.id, duplicated: true };
    const r = db.prepare('INSERT INTO ad_jobs (product_id, options) VALUES (?, ?)').run(productId, JSON.stringify(options));
    return { id: Number(r.lastInsertRowid) };
  },
  /** Toma el trabajo más antiguo en cola (y recupera los que se quedaron colgados más de 30 min). */
  claim() {
    db.prepare("UPDATE ad_jobs SET status = 'queued' WHERE status = 'running' AND updated_at < datetime('now','-30 minutes')").run();
    const j = db.prepare("SELECT * FROM ad_jobs WHERE status = 'queued' ORDER BY id LIMIT 1").get();
    if (!j) return null;
    db.prepare("UPDATE ad_jobs SET status = 'running', updated_at = datetime('now') WHERE id = ?").run(j.id);
    return { ...j, options: JSON.parse(j.options || '{}') };
  },
  finish(id, status, result = {}, error = '') {
    db.prepare("UPDATE ad_jobs SET status = ?, result = ?, error = ?, updated_at = datetime('now') WHERE id = ?").run(status, JSON.stringify(result), String(error).slice(0, 1000), id);
  },
  last: (productId) => db.prepare("SELECT * FROM ad_jobs WHERE product_id = ? AND status = 'done' ORDER BY id DESC LIMIT 1").get(productId),
};

export const Candidates = {
  /** Guarda candidatos y devuelve solo los que no habíamos visto antes. */
  addMany(items) {
    const ins = db.prepare(`INSERT OR IGNORE INTO candidates (source, external_id, url, title, snippet, price, currency, image, keyword, published_at, metrics, trend_score)
      VALUES (:source, :external_id, :url, :title, :snippet, :price, :currency, :image, :keyword, :published_at, :metrics, :trend_score)`);
    const fresh = [];
    for (const i of items) {
      if (!i?.source || !i?.external_id) continue;
      const r = ins.run({ source: String(i.source), external_id: String(i.external_id), url: String(i.url || ''), title: String(i.title || '').slice(0, 300),
        snippet: String(i.snippet || '').slice(0, 1500), price: Number(i.price) || 0, currency: String(i.currency || ''), image: String(i.image || ''),
        keyword: String(i.keyword || ''), published_at: String(i.published_at || ''), metrics: JSON.stringify(i.metrics || {}), trend_score: Number(i.trend_score) || 0 });
      if (r.changes) fresh.push(Candidates.get(r.lastInsertRowid));
    }
    return fresh;
  },
  get: (id) => db.prepare('SELECT * FROM candidates WHERE id = ?').get(Number(id)),
  list: (status, limit = 100) => status
    ? db.prepare('SELECT * FROM candidates WHERE status = ? ORDER BY ai_score DESC, trend_score DESC LIMIT ?').all(status, limit)
    : db.prepare('SELECT * FROM candidates ORDER BY found_at DESC, ai_score DESC LIMIT ?').all(limit),
  /** Mejores candidatos aún sin usar, para reemplazar productos que no venden. */
  best: (limit = 3) => db.prepare(`SELECT * FROM candidates WHERE status IN ('notified','new') AND ai_score >= 7
    AND found_at >= datetime('now','-21 days') ORDER BY ai_score DESC, trend_score DESC LIMIT ?`).all(limit),
  update(id, data) {
    const allowed = ['ai_score', 'ai', 'status', 'product_id', 'title'];
    const d = Object.fromEntries(Object.entries(data).filter(([k]) => allowed.includes(k)).map(([k, v]) => [k, typeof v === 'object' && v !== null ? JSON.stringify(v) : v]));
    if (!Object.keys(d).length) return Candidates.get(id);
    db.prepare(`UPDATE candidates SET ${Object.keys(d).map((k) => `${k} = :${k}`).join(', ')} WHERE id = :id`).run({ ...d, id: Number(id) });
    return Candidates.get(id);
  },
};

export const Orders = {
  create(o) {
    const id = newOrderId(); if (!o.prueba) actividad('pago');
    db.prepare(`INSERT INTO orders (id, product_id, email, whatsapp, telegram_chat_id, lang, method, amount_cents, currency, status, provider_ref, coupon, upsell_of, bump_id, prueba)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).run(id, o.product_id, o.email || '', o.whatsapp || '', String(o.telegram_chat_id || ''),
      o.lang || 'es', o.method, o.amount_cents, o.currency, o.status || 'pending', o.provider_ref || '', o.coupon || '', o.upsell_of || '', o.bump_id || null, o.prueba ? 1 : 0);
    return Orders.get(id);
  },
  get: (id) => db.prepare('SELECT * FROM orders WHERE id = ?').get(String(id || '').toUpperCase()),
  withProduct: (id) => db.prepare(`SELECT o.*, CASE WHEN o.bump_id THEN p.title || ' + ' || (SELECT title FROM products WHERE id = o.bump_id) ELSE p.title END AS title,
    p.slug, p.file_name, p.external_url, p.emoji, CASE WHEN o.bump_id THEN p.id || ',' || o.bump_id ELSE p.bundle_ids END AS bundle_ids
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
    if (r.changes) {
      db.prepare('UPDATE products SET sales = sales + 1 WHERE id = (SELECT product_id FROM orders WHERE id = ?)').run(id);
      const c = db.prepare('SELECT coupon FROM orders WHERE id = ?').get(id)?.coupon;
      if (c) db.prepare('UPDATE subscribers SET used_order = ? WHERE code = ? AND used_order IS NULL').run(id, c);
    }
    return r.changes > 0;
  },
  /** ¿Ya se pagó un "completa tu pack" de este pedido? */
  upsellPaid: (orderId) => !!db.prepare("SELECT 1 FROM orders WHERE upsell_of = ? AND status = 'paid'").get(orderId),
  recent: (limit = 50) => db.prepare(`SELECT o.*, p.title FROM orders o JOIN products p ON p.id = o.product_id
    ORDER BY o.created_at DESC LIMIT ?`).all(limit),
  byStatus: (status) => db.prepare(`SELECT o.*, p.title FROM orders o JOIN products p ON p.id = o.product_id
    WHERE o.status = ? ORDER BY o.created_at`).all(status),
  /** Importe pendiente ya usado (para que cada pedido Binance tenga un importe único). */
  amountTaken: (cents) => !!db.prepare(`SELECT 1 FROM orders WHERE method='binance' AND status IN ('pending','review')
    AND amount_cents = ? AND created_at > datetime('now','-2 days')`).get(cents),
  stats: () => db.prepare(`SELECT COUNT(*) orders, COALESCE(SUM(CASE WHEN currency!='XTR' THEN amount_cents END),0) usd_cents,
    COALESCE(SUM(CASE WHEN currency='XTR' THEN amount_cents END),0) stars FROM orders WHERE status='paid' AND prueba=0`).get(),
};

// ===== Reseñas reales (verificadas): se piden después de comprar o de descargar un regalo; el admin modera =====
db.exec(`CREATE TABLE IF NOT EXISTS reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL,
  ref TEXT NOT NULL,                     -- pedido, correo del regalo o código del enlace regalado
  source TEXT NOT NULL,                  -- compra / regalo / gratis (recibió el producto gratis para opinar)
  name TEXT DEFAULT '', stars INTEGER NOT NULL, text TEXT DEFAULT '',
  status TEXT DEFAULT 'pending',         -- pending / approved / rejected
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(product_id, ref)
);`);
for (const sql of ["ALTER TABLE orders ADD COLUMN review_asked INTEGER DEFAULT 0", "ALTER TABLE subscribers ADD COLUMN review_asked INTEGER DEFAULT 0"]) { try { db.exec(sql); } catch {} }

export const Reviews = {
  add: (r) => db.prepare(`INSERT INTO reviews (product_id, ref, source, name, stars, text) VALUES (?,?,?,?,?,?)
    ON CONFLICT(product_id, ref) DO UPDATE SET name=excluded.name, stars=excluded.stars, text=excluded.text, status='pending', created_at=datetime('now')`)
    .run(r.product_id, r.ref, r.source, r.name, r.stars, r.text),
  get: (id) => db.prepare('SELECT * FROM reviews WHERE id = ?').get(id),
  byRef: (pid, ref) => db.prepare('SELECT * FROM reviews WHERE product_id = ? AND ref = ?').get(pid, ref),
  setStatus: (id, s) => db.prepare('UPDATE reviews SET status = ? WHERE id = ?').run(s, id),
  approved: (pid, limit = 30) => db.prepare(`SELECT name, stars, text, source, created_at FROM reviews WHERE product_id = ? AND status = 'approved' ORDER BY created_at DESC LIMIT ?`).all(pid, limit),
  summary: (pid) => db.prepare(`SELECT COUNT(*) n, ROUND(AVG(stars),1) avg FROM reviews WHERE product_id = ? AND status = 'approved'`).get(pid),
  ordersToAsk: () => db.prepare(`SELECT * FROM orders WHERE status='paid' AND prueba=0 AND review_asked=0 AND paid_at < datetime('now','-2 days') AND paid_at > datetime('now','-10 days')`).all(),
  subsToAsk: () => db.prepare(`SELECT * FROM subscribers WHERE review_asked=0 AND COALESCE(unsub,0)=0 AND source LIKE 'regalo:%' AND created_at < datetime('now','-1 day') AND created_at > datetime('now','-7 days')`).all(),
  markOrderAsked: (id) => db.prepare('UPDATE orders SET review_asked=1 WHERE id=?').run(id),
  markSubAsked: (email) => db.prepare('UPDATE subscribers SET review_asked=1 WHERE email=?').run(email),
};

// ⏰ Actividad por día de la semana y hora (hora de Caracas, UTC-4) para aprender cuándo se mueve la gente
db.exec(`CREATE TABLE IF NOT EXISTS actividad_hora (tipo TEXT, dow INTEGER, hora INTEGER, n INTEGER DEFAULT 0, PRIMARY KEY (tipo, dow, hora))`);
export function actividad(tipo) {
  try { const d = new Date(Date.now() - 4 * 3600e3);
    db.prepare('INSERT INTO actividad_hora (tipo, dow, hora, n) VALUES (?, ?, ?, 1) ON CONFLICT(tipo, dow, hora) DO UPDATE SET n = n + 1').run(tipo, d.getUTCDay(), d.getUTCHours()); } catch {}
}
export const Actividad = { todas: () => db.prepare('SELECT tipo, dow, hora, n FROM actividad_hora').all() };
