// Servidor HTTP: web app + API + descargas + bot. Sin dependencias externas.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { config } from './config.js';
import { Products, Orders } from './db.js';
import { deliver, verifyDownload, downloadLink } from './delivery/index.js';
import { whatsappEnabled } from './delivery/whatsapp.js';
import { paypalEnabled, createPaypalOrder, capturePaypalOrder } from './payments/paypal.js';
import { binanceEnabled, binanceAutoVerify, uniqueAmount, findBinancePayment } from './payments/binance.js';
import { tg, tgEnabled, verifyInitData, notifyAdmin, esc } from './telegram/api.js';
import { startBot, starsInvoice, askBinance } from './telegram/bot.js';
import { Candidates } from './db.js';
import { pixelSnippet } from './meta.js';
import { startRadarBot, createDraft } from './telegram/radar.js';

const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.ico': 'image/x-icon',
  '.pdf': 'application/pdf', '.zip': 'application/zip', '.woff2': 'font/woff2' };

// Clave de acceso de cada pedido (para que nadie vea pedidos ajenos adivinando el código).
const orderKey = (id) => crypto.createHmac('sha256', config.secret).update('order:' + id).digest('base64url').slice(0, 16);
const keyOk = (id, k) => !!k && k.length === 16 && crypto.timingSafeEqual(Buffer.from(k), Buffer.from(orderKey(id)));

const json = (res, code, data) => { res.writeHead(code, { 'content-type': 'application/json' }); res.end(JSON.stringify(data)); };
const fail = (res, code, error) => json(res, code, { error });

async function body(req, limit = 80 * 1024 * 1024) {
  const chunks = []; let size = 0;
  for await (const c of req) { size += c.length; if (size > limit) throw new Error('Archivo demasiado grande'); chunks.push(c); }
  try { return JSON.parse(Buffer.concat(chunks).toString() || '{}'); } catch { return {}; }
}

function publicProduct(p, lang = 'es') {
  let tr = {}; try { tr = JSON.parse(p.i18n || '{}')[lang] || {}; } catch {}
  return { id: p.id, slug: p.slug, title: tr.title || p.title, short: tr.short || p.short, description: tr.description || p.description,
    category: p.category, price: p.price_cents / 100, compare: p.compare_cents / 100, stars: p.stars, emoji: p.emoji, color: p.color,
    cover: p.cover_url || `/cover/${p.slug}.svg`, license: p.license_type, featured: !!p.featured, sales: p.sales };
}

function serveFile(res, file, headers = {}) {
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404); return res.end('No encontrado'); }
  res.writeHead(200, { 'content-type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream', ...headers });
  fs.createReadStream(file).pipe(res);
}

function coverSvg(p) {
  const words = p.title.split(' '); const lines = [''];
  for (const w of words) { if ((lines.at(-1) + ' ' + w).trim().length > 18) lines.push(w); else lines[lines.length - 1] = (lines.at(-1) + ' ' + w).trim(); }
  const t = lines.slice(0, 3).map((l, i) => `<text x="60" y="${560 + i * 64}" font-size="54" font-weight="800" fill="#fff" font-family="system-ui,sans-serif">${esc(l)}</text>`).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="${esc(p.color)}"/><stop offset="1" stop-color="#120d2b"/></linearGradient>
<radialGradient id="r" cx=".8" cy=".2" r=".6"><stop offset="0" stop-color="#fff" stop-opacity=".35"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient></defs>
<rect width="800" height="800" fill="url(#g)"/><rect width="800" height="800" fill="url(#r)"/>
<text x="60" y="330" font-size="220">${esc(p.emoji)}</text>
<text x="60" y="470" font-size="26" letter-spacing="6" fill="#ffffffaa" font-family="system-ui,sans-serif">${esc(p.category.toUpperCase())}</text>${t}</svg>`;
}

function renderPage(name, vars = {}) {
  let html = fs.readFileSync(path.join(config.paths.public, name), 'utf8');
  const all = { STORE: esc(config.storeName), BASE: config.baseUrl, TITLE: esc(config.storeName), DESC: 'Productos digitales con entrega inmediata.', IMAGE: '', DATA: 'null', PIXEL: pixelSnippet(), ...vars };
  return html.replace(/\{\{(\w+)\}\}/g, (_, k) => all[k] ?? '');
}

const routes = [];
const on = (method, pattern, fn) => routes.push({ method, re: new RegExp('^' + pattern.replace(/:(\w+)/g, '(?<$1>[^/]+)') + '$'), fn });

// ===== Páginas =====
on('GET', '/', (req, res) => { res.writeHead(200, { 'content-type': MIME['.html'] }); res.end(renderPage('index.html')); });
on('GET', '/p/:slug', (req, res, { slug }) => {
  const p = Products.bySlug(slug);
  if (!p || !p.active) { res.writeHead(404, { 'content-type': MIME['.html'] }); return res.end(renderPage('index.html')); }
  const pp = publicProduct(p);
  if (!/bot|crawl|spider|facebookexternalhit|preview/i.test(req.headers['user-agent'] || '')) Products.view(p.id);
  res.writeHead(200, { 'content-type': MIME['.html'] });
  res.end(renderPage('product.html', { TITLE: esc(pp.title) + ' · ' + esc(config.storeName), DESC: esc(pp.short),
    IMAGE: pp.cover.startsWith('http') ? pp.cover : config.baseUrl + pp.cover,
    DATA: JSON.stringify(pp).replace(/</g, '\\u003c') }));
});
on('GET', '/pedido/:id', (req, res) => { res.writeHead(200, { 'content-type': MIME['.html'] }); res.end(renderPage('order.html')); });
on('GET', '/legal', (req, res) => { res.writeHead(200, { 'content-type': MIME['.html'] }); res.end(renderPage('legal.html')); });
on('GET', '/admin', (req, res) => serveFile(res, path.join(config.paths.public, 'admin', 'index.html')));
on('GET', '/cover/:file', (req, res, { file }) => {
  const p = Products.bySlug(file.replace(/\.svg$/, ''));
  if (!p) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': MIME['.svg'], 'cache-control': 'public, max-age=3600' }); res.end(coverSvg(p));
});

// ===== API pública =====
on('GET', '/api/config', (req, res) => json(res, 200, {
  store: config.storeName, lang: config.defaultLang,
  paypal: paypalEnabled() ? { clientId: config.paypal.clientId } : null,
  binance: binanceEnabled() ? { payId: config.binance.payId, auto: binanceAutoVerify() } : null,
  bot: config.telegram.username || null, whatsapp: whatsappEnabled(), email: !!config.email.resendKey,
}));
on('GET', '/api/products', (req, res, _, url) => json(res, 200, {
  products: Products.list().map((p) => publicProduct(p, url.searchParams.get('lang') || 'es')), categories: Products.categories() }));
on('GET', '/api/products/:slug', (req, res, { slug }) => {
  const p = Products.bySlug(slug); return p?.active ? json(res, 200, publicProduct(p)) : fail(res, 404, 'No existe');
});

on('POST', '/api/orders', async (req, res) => {
  const b = await body(req, 1e5);
  const p = Products.bySlug(String(b.slug || ''));
  if (!p?.active) return fail(res, 404, 'Producto no disponible');
  const email = String(b.email || '').trim().slice(0, 120);
  const whatsapp = String(b.whatsapp || '').replace(/[^\d+]/g, '').slice(0, 20);
  if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return fail(res, 400, 'Correo no válido');
  if (!email && !whatsapp) return fail(res, 400, 'Indica tu correo o WhatsApp para enviarte el producto');
  if (b.method === 'paypal') {
    if (!paypalEnabled()) return fail(res, 400, 'PayPal no está activo');
    const o = Orders.create({ product_id: p.id, email, whatsapp, method: 'paypal', amount_cents: p.price_cents, currency: 'USD', lang: b.lang });
    try {
      const paypalId = await createPaypalOrder(o, p);
      Orders.update(o.id, { provider_ref: paypalId });
      return json(res, 200, { id: o.id, key: orderKey(o.id), paypalId });
    } catch (e) { console.error(e.message); return fail(res, 502, 'No se pudo iniciar el pago con PayPal'); }
  }
  if (b.method === 'binance') {
    if (!binanceEnabled()) return fail(res, 400, 'Binance no está activo');
    const o = Orders.create({ product_id: p.id, email, whatsapp, method: 'binance', amount_cents: uniqueAmount(p.price_cents), currency: 'USDT', lang: b.lang });
    return json(res, 200, { id: o.id, key: orderKey(o.id), amount: (o.amount_cents / 100).toFixed(2), payId: config.binance.payId });
  }
  return fail(res, 400, 'Método de pago no válido');
});

on('POST', '/api/paypal/capture', async (req, res) => {
  const b = await body(req, 1e4);
  const o = Orders.get(b.id);
  if (!o || !keyOk(o.id, b.key) || o.method !== 'paypal') return fail(res, 404, 'Pedido no encontrado');
  if (o.status === 'paid') return json(res, 200, { status: 'paid' });
  try {
    const r = await capturePaypalOrder(o.provider_ref, o);
    if (!r.ok) return fail(res, 402, 'El pago no se completó');
    if (Orders.markPaid(o.id, r.captureId)) deliver(o.id).catch((e) => console.error(e));
    return json(res, 200, { status: 'paid' });
  } catch (e) { console.error(e.message); return fail(res, 502, 'Error al confirmar con PayPal'); }
});

on('POST', '/api/binance/submit', async (req, res) => {
  const b = await body(req, 1e4);
  const o = Orders.get(b.id);
  if (!o || !keyOk(o.id, b.key) || o.method !== 'binance') return fail(res, 404, 'Pedido no encontrado');
  if (o.status !== 'pending') return json(res, 200, { status: o.status });
  const ref = String(b.ref || '').replace(/[^\w-]/g, '').slice(0, 40);
  if (ref.length < 6) return fail(res, 400, 'Pega el ID de orden que te muestra Binance');
  Orders.update(o.id, { status: 'review', provider_ref: ref });
  const tx = await findBinancePayment(Orders.get(o.id)).catch((e) => { console.error(e.message); return ''; });
  if (tx && Orders.markPaid(o.id, tx)) { await deliver(o.id); return json(res, 200, { status: 'paid' }); }
  await askBinance(Orders.withProduct(o.id));
  return json(res, 200, { status: 'review' });
});

on('GET', '/api/orders/:id', (req, res, { id }, url) => {
  const o = Orders.withProduct(id);
  if (!o || !keyOk(o.id, url.searchParams.get('k'))) return fail(res, 404, 'Pedido no encontrado');
  json(res, 200, { id: o.id, status: o.status, method: o.method, title: o.title, emoji: o.emoji, slug: o.slug,
    amount: o.currency === 'XTR' ? o.amount_cents : (o.amount_cents / 100).toFixed(2), currency: o.currency,
    payId: o.method === 'binance' ? config.binance.payId : undefined,
    download: o.status === 'paid' ? downloadLink(o.id) : null,
    telegram: config.telegram.username ? `https://t.me/${config.telegram.username}?start=o_${o.id}` : null });
});

// Mini App de Telegram: compra con Stars.
on('POST', '/api/stars/invoice', async (req, res) => {
  const b = await body(req, 1e5);
  const user = verifyInitData(b.initData);
  if (!user) return fail(res, 401, 'Abre la tienda desde Telegram');
  const p = Products.bySlug(String(b.slug || ''));
  if (!p?.active || !p.stars) return fail(res, 404, 'Producto no disponible');
  const { params } = starsInvoice(p, user.id);
  try { json(res, 200, { link: await tg('createInvoiceLink', params) }); }
  catch (e) { console.error(e.message); fail(res, 502, 'No se pudo crear la factura'); }
});

// ===== Descargas =====
on('GET', '/d/:id/:exp/:sig', (req, res, { id, exp, sig }) => {
  const problem = verifyDownload(id, exp, sig);
  const o = Orders.withProduct(id);
  const msg = (t) => { res.writeHead(403, { 'content-type': MIME['.html'] }); res.end(renderPage('order.html', { DATA: JSON.stringify({ error: t }) })); };
  if (problem || !o || o.status !== 'paid') return msg(problem === 'caducado' ? 'El enlace caducó. Pide uno nuevo en el bot con /mispedidos o escríbenos.' : 'Enlace no válido.');
  if (o.downloads >= config.maxDownloads) return msg('Llegaste al máximo de descargas de este pedido. Escríbenos si necesitas ayuda.');
  Orders.update(o.id, { downloads: o.downloads + 1 });
  if (o.external_url) { res.writeHead(302, { location: o.external_url }); return res.end(); }
  const file = path.join(config.paths.files, path.basename(o.file_name || ''));
  if (!o.file_name || !fs.existsSync(file)) return msg('El archivo no está disponible todavía. Te lo enviaremos pronto.');
  serveFile(res, file, { 'content-disposition': `attachment; filename="${encodeURIComponent(path.basename(file))}"` });
});

// ===== Admin =====
// La clave viaja codificada (encodeURIComponent) para admitir tildes, ñ y símbolos; se ignoran espacios al inicio/final.
const adminKeyFrom = (req) => { const raw = String(req.headers['x-admin-key'] || ''); try { return decodeURIComponent(raw).trim(); } catch { return raw.trim(); } };
const adminOk = (req) => { const k = adminKeyFrom(req), pw = String(config.adminPassword || '').trim();
  return !!pw && !!k && crypto.timingSafeEqual(crypto.createHash('sha256').update(k).digest(), crypto.createHash('sha256').update(pw).digest()); };

on('GET', '/api/admin/summary', (req, res) => adminOk(req) ? json(res, 200, {
  stats: Orders.stats(), products: Products.list({ all: true }), orders: Orders.recent(100),
  perf: Object.fromEntries(Products.performance(7).map((p) => [p.id, p])) }) : fail(res, 401, 'Clave incorrecta'));

on('POST', '/api/admin/products', async (req, res) => {
  if (!adminOk(req)) return fail(res, 401, 'Clave incorrecta');
  const b = await body(req);
  const slug = String(b.slug || b.title || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60);
  if (!slug || !b.title || !(b.price > 0)) return fail(res, 400, 'Faltan título o precio');
  const data = { id: b.id || undefined, slug, title: b.title, short: b.short || '', description: b.description || '', category: b.category || 'General',
    price_cents: Math.round(b.price * 100), compare_cents: Math.round((b.compare || 0) * 100),
    stars: Number(b.stars) || Math.ceil(b.price / 0.013), emoji: b.emoji || '✨', color: b.color || '#7c5cff', cover_url: b.cover_url || '',
    external_url: b.external_url || '', license_type: b.license_type || 'PLR', license_note: b.license_note || '',
    featured: b.featured ? 1 : 0, active: b.active === false ? 0 : 1 };
  if (b.fileBase64 && b.fileName) {
    const name = `${slug}-${Date.now()}${path.extname(b.fileName).toLowerCase().replace(/[^.\w]/g, '')}`;
    await fs.promises.writeFile(path.join(config.paths.files, name), Buffer.from(b.fileBase64, 'base64'));
    data.file_name = name;
  }
  try { json(res, 200, Products.upsert(data)); } catch (e) { fail(res, 400, e.message.includes('UNIQUE') ? 'Ya existe un producto con ese enlace (slug)' : e.message); }
});

on('POST', '/api/admin/products/:id/delete', (req, res, { id }) => { if (!adminOk(req)) return fail(res, 401, 'Clave incorrecta'); Products.remove(Number(id)); json(res, 200, { ok: true }); });

on('POST', '/api/admin/orders/:id/:action', async (req, res, { id, action }) => {
  if (!adminOk(req)) return fail(res, 401, 'Clave incorrecta');
  const o = Orders.get(id); if (!o) return fail(res, 404, 'No existe');
  if (action === 'confirm') { Orders.markPaid(o.id); return json(res, 200, { via: await deliver(o.id) }); }
  if (action === 'reject') { Orders.update(o.id, { status: 'rejected' }); return json(res, 200, { ok: true }); }
  if (action === 'resend') return json(res, 200, { via: await deliver(o.id) });
  fail(res, 400, 'Acción no válida');
});

// ===== API para n8n (cabecera x-api-key = N8N_API_KEY) =====
const n8nOk = (req) => config.n8nKey && req.headers['x-api-key'] &&
  crypto.timingSafeEqual(crypto.createHash('sha256').update(req.headers['x-api-key']).digest(), crypto.createHash('sha256').update(config.n8nKey).digest());
const parseC = (c) => c && { ...c, metrics: JSON.parse(c.metrics || '{}'), ai: JSON.parse(c.ai || '{}') };

// Guarda lo encontrado hoy y devuelve solo lo nuevo (lo ya visto se ignora).
on('POST', '/api/n8n/candidates', async (req, res) => {
  if (!n8nOk(req)) return fail(res, 401, 'x-api-key incorrecta');
  const b = await body(req, 20e6);
  const fresh = Candidates.addMany(Array.isArray(b.items) ? b.items : []);
  json(res, 200, { received: (b.items || []).length, new: fresh.length, items: fresh.map(parseC) });
});
on('GET', '/api/n8n/candidates', (req, res, _, url) => {
  if (!n8nOk(req)) return fail(res, 401, 'x-api-key incorrecta');
  json(res, 200, { items: Candidates.list(url.searchParams.get('status') || '', Number(url.searchParams.get('limit')) || 100).map(parseC) });
});
on('GET', '/api/n8n/candidates/best', (req, res, _, url) => {
  if (!n8nOk(req)) return fail(res, 401, 'x-api-key incorrecta');
  json(res, 200, { items: Candidates.best(Number(url.searchParams.get('limit')) || 3).map(parseC) });
});
on('GET', '/api/n8n/candidates/:id', (req, res, { id }) => {
  if (!n8nOk(req)) return fail(res, 401, 'x-api-key incorrecta');
  const c = Candidates.get(id); return c ? json(res, 200, parseC(c)) : fail(res, 404, 'No existe');
});
on('POST', '/api/n8n/candidates/:id', async (req, res, { id }) => {
  if (!n8nOk(req)) return fail(res, 401, 'x-api-key incorrecta');
  if (!Candidates.get(id)) return fail(res, 404, 'No existe');
  json(res, 200, parseC(Candidates.update(id, await body(req, 1e6))));
});
// Crea un producto en borrador (oculto) a partir de un candidato. Se activa al subir el archivo en /admin.
on('POST', '/api/n8n/candidates/:id/draft', async (req, res, { id }) => {
  if (!n8nOk(req)) return fail(res, 401, 'x-api-key incorrecta');
  const c = parseC(Candidates.get(id)); if (!c) return fail(res, 404, 'No existe');
  if (c.product_id && Products.byId(c.product_id)) return json(res, 200, { product: Products.byId(c.product_id), existed: true });
  const product = createDraft(Candidates.get(id), await body(req, 1e6));
  json(res, 200, { product, edit_url: `${config.baseUrl}/admin` });
});
on('GET', '/api/n8n/performance', (req, res, _, url) => {
  if (!n8nOk(req)) return fail(res, 401, 'x-api-key incorrecta');
  json(res, 200, { days: Number(url.searchParams.get('days')) || 7, products: Products.performance(url.searchParams.get('days')), totals: Orders.stats() });
});
on('POST', '/api/n8n/products/:id/retire', (req, res, { id }) => {
  if (!n8nOk(req)) return fail(res, 401, 'x-api-key incorrecta');
  const p = Products.byId(Number(id)); if (!p) return fail(res, 404, 'No existe');
  Products.remove(p.id);
  if (p.candidate_id) Candidates.update(p.candidate_id, { status: 'retired' });
  json(res, 200, { ok: true, retired: p.slug });
});

on('GET', '/api/admin/radar', (req, res) => adminOk(req) ? json(res, 200, { items: Candidates.list('', 150).map(parseC) }) : fail(res, 401, 'Clave incorrecta'));

// ===== Servidor =====
const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x');
  try {
    for (const r of routes) {
      if (r.method !== req.method) continue;
      const m = url.pathname.match(r.re);
      if (m) return await r.fn(req, res, Object.fromEntries(Object.entries(m.groups || {}).map(([k, v]) => [k, decodeURIComponent(v)])), url);
    }
    if (req.method === 'GET') {
      const file = path.join(config.paths.public, path.normalize(url.pathname).replace(/^(\.\.[/\\])+/, ''));
      if (file.startsWith(config.paths.public) && !file.includes(`${path.sep}admin${path.sep}`)) return serveFile(res, file, { 'cache-control': 'public, max-age=300' });
    }
    res.writeHead(404); res.end('No encontrado');
  } catch (e) {
    console.error(e);
    if (!res.headersSent) fail(res, 500, 'Error interno');
  }
});

server.listen(config.port, () => console.log(`🛍️  ${config.storeName} en ${config.baseUrl} (puerto ${config.port})`));

// Verificación automática de pagos Binance cada minuto (si hay API key).
if (binanceAutoVerify()) setInterval(async () => {
  // Revisa también los pedidos Binance que el cliente pagó pero no avisó (se reconocen por el importe único).
  const recent = (o) => o.method === 'binance' && new Date(o.created_at + 'Z') > Date.now() - 48 * 3600e3;
  for (const o of [...Orders.byStatus('review'), ...Orders.byStatus('pending').filter(recent)]) {
    const tx = await findBinancePayment(o).catch(() => '');
    if (tx && Orders.markPaid(o.id, tx)) deliver(o.id).catch(console.error);
  }
}, 60_000);

if (process.env.NO_BOT !== '1') { startBot(); startRadarBot(); }
