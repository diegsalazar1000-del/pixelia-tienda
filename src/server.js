// Servidor HTTP: web app + API + descargas + bot. Sin dependencias externas.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { config } from './config.js';
import { Products, Orders, Subscribers, COUPON_OFF } from './db.js';
import { sendEmail } from './delivery/email.js';
import { deliver, verifyDownload, downloadLink, appLicense, verifyApp } from './delivery/index.js';
import { whatsappEnabled } from './delivery/whatsapp.js';
import { paypalEnabled, createPaypalOrder, capturePaypalOrder } from './payments/paypal.js';
import { binanceEnabled, binanceAutoVerify, uniqueAmount, findBinancePayment } from './payments/binance.js';
import { tg, tgEnabled, verifyInitData, notifyAdmin, esc } from './telegram/api.js';
import { startBot, starsInvoice, askBinance } from './telegram/bot.js';
import { Candidates, AdJobs } from './db.js';
import { pixelSnippet } from './meta.js';
import { startRadarBot, createDraft, offerAds, sendAdPicker } from './telegram/radar.js';
import { startExplorador } from './telegram/explorador.js';
import { Reviews } from './db.js';
import { readToken, targets, notifyReview, startReviews, GIFT_SLUGS } from './resenas.js';
import { startSecuencia, darDeBaja } from './correos.js';

const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.ico': 'image/x-icon', '.mp4': 'video/mp4',
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
    cover: p.cover_url || `/cover/${p.slug}.svg`, license: p.license_type, featured: !!p.featured, sales: p.sales,
    pack: p.bundle_ids ? Products.bundleItems(p).map((i) => ({ slug: i.slug, title: i.title, emoji: i.emoji, price: i.price_cents / 100 })) : null,
    gancho: tr.gancho || p.gancho || '', gallery: jsonList(p.gallery), video: p.video_url || '', faq: jsonList(tr.faq || p.faq),
    countdown: p.countdown ? { date: p.countdown, label: tr.countdown_label || p.countdown_label || '' } : null,
    sample: p.sample_url ? { title: tr.sample_title || p.sample_title || 'Muestra gratis' } : null,
    regalo: p.regalo_url ? { url: p.regalo_url, title: p.regalo_title || 'un regalo gratis' } : null };  // "¿Todavía no te decides? Empieza gratis con…"
}
function jsonList(v) { if (Array.isArray(v)) return v; try { const a = JSON.parse(v || '[]'); return Array.isArray(a) ? a : []; } catch { return []; } }

/** Datos extra de la página de producto: packs que lo incluyen (para la caja "Llévate los 3"). */
function packOffers(p) {
  if (p.bundle_ids) return [];
  return Products.bundlesWith(p.id).map((b) => {
    const items = Products.bundleItems(b); const normal = items.reduce((t, i) => t + i.price_cents, 0);
    return { slug: b.slug, title: b.title, price: b.price_cents / 100, normal: normal / 100, save: Math.max(0, normal - b.price_cents) / 100,
      items: items.map((i) => ({ title: i.title, emoji: i.emoji })) };
  });
}

/** Oferta "completa tu pack" después de comprar un producto suelto. */
function upsellFor(o) {
  if (o.status !== 'paid' || o.bundle_ids || o.currency === 'XTR' || Orders.upsellPaid(o.id)) return null;
  const b = Products.bundlesWith(o.product_id)[0]; if (!b) return null;
  const price = Math.max(100, b.price_cents - o.amount_cents);
  const others = Products.bundleItems(b).filter((i) => i.id !== o.product_id);
  return { slug: b.slug, title: b.title, price: price / 100, items: others.map((i) => ({ title: i.title, emoji: i.emoji })),
    normal: others.reduce((t, i) => t + i.price_cents, 0) / 100 };
}

/** Precio final de un pedido web (cupón o "completa tu pack"). */
export const BUMP_OFF = 0.2;  // 2º producto en el pago: 20% menos
function bumpInfo(p) {
  if (!p || p.bundle_ids || !p.price_cents) return null;
  const x = Products.bumpFor(p); if (!x) return null;
  return { slug: x.slug, title: x.title, emoji: x.emoji, short: x.short, price: x.price_cents / 100, bumpPrice: Math.round(x.price_cents * (1 - BUMP_OFF)) / 100, cover: publicProduct(x).cover };
}
function priceFor(p, b) {
  if (b.upsell?.id) {
    const prev = Orders.withProduct(b.upsell.id);
    if (!prev || !keyOk(prev.id, b.upsell.key) || prev.status !== 'paid') throw new Error('La oferta no es válida');
    const up = upsellFor(prev);
    if (!up || up.slug !== p.slug) throw new Error('La oferta ya no está disponible');
    return { cents: Math.round(up.price * 100), upsell_of: prev.id };
  }
  if (b.coupon) {
    if (p.bundle_ids) throw new Error('El cupón es para productos sueltos (el pack ya tiene su descuento).');
    const s = Subscribers.valid(b.coupon); if (!s) throw new Error('Cupón no válido o ya usado.');
    return { cents: Math.max(100, Math.round(p.price_cents * (1 - COUPON_OFF))), coupon: s.code };
  }
  return { cents: p.price_cents };
}

function serveFile(res, file, headers = {}) {
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404); return res.end('No encontrado'); }
  const type = MIME[path.extname(file).toLowerCase()] || 'application/octet-stream', size = fs.statSync(file).size;
  const rg = /^bytes=(\d*)-(\d*)$/.exec(res.req?.headers?.range || '');
  if (rg && (rg[1] || rg[2])) { // iPhone/Safari solo reproduce videos si el servidor acepta pedazos (Range)
    let a = rg[1] ? Number(rg[1]) : size - Number(rg[2]), b = rg[1] && rg[2] ? Math.min(Number(rg[2]), size - 1) : size - 1;
    if (a < 0) a = 0;
    if (a > b || a >= size) { res.writeHead(416, { 'content-range': `bytes */${size}` }); return res.end(); }
    res.writeHead(206, { 'content-type': type, 'accept-ranges': 'bytes', 'content-range': `bytes ${a}-${b}/${size}`, 'content-length': b - a + 1, ...headers });
    return fs.createReadStream(file, { start: a, end: b }).pipe(res);
  }
  res.writeHead(200, { 'content-type': type, 'accept-ranges': 'bytes', 'content-length': size, ...headers });
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

/** Modo dueño: cookie pxd=1 (se pone con ?soy=dueno). Sus visitas y compras no cuentan en estadísticas. */
const esDueno = (req) => /(^|;\s*)pxd=1/.test(req.headers.cookie || '');

const routes = [];
const on = (method, pattern, fn) => routes.push({ method, re: new RegExp('^' + pattern.replace(/:(\w+)/g, '(?<$1>[^/]+)') + '$'), fn });

// ===== Visitas reales (sin robots, sin recargas, sin el dueño) =====
// Solo cuenta navegadores de verdad (Mozilla + idioma + cabeceras de navegador), nada de robots/previsualizadores/scripts,
// y UNA visita por persona (IP) por producto por día: recargar la página no suma.
const ROBOT = /bot|crawl|spider|slurp|preview|headless|lighthouse|facebookexternalhit|meta-external|whatsapp|telegram|python|curl|wget|node|axios|go-http|java|okhttp|scrapy|ahrefs|semrush|bytespider|gptbot|claude|petalbot|bingpreview/i;
const vistos = new Map();   // "día|producto|ip" → 1 (se limpia cada día)
function visitaReal(req, productId) {
  const ua = req.headers['user-agent'] || '';
  if (!/Mozilla\//.test(ua) || ROBOT.test(ua) || !req.headers['accept-language'] || esDueno(req) || /[?&]soy=dueno/.test(req.url)) return false;
  if (req.headers['purpose'] === 'prefetch' || req.headers['sec-purpose']?.includes('prefetch')) return false;
  const ip = String(req.headers['x-forwarded-for'] || req.socket.remoteAddress || '').split(',')[0].trim();
  const dia = new Date().toISOString().slice(0, 10), k = `${dia}|${productId}|${ip}`;
  if (vistos.has(k)) return false;
  if (vistos.size > 50000 || ![...vistos.keys()].slice(0, 1).every((x) => x.startsWith(dia))) vistos.clear();
  vistos.set(k, 1); return true;
}

// ===== Páginas =====
on('GET', '/', (req, res) => { res.writeHead(200, { 'content-type': MIME['.html'] }); res.end(renderPage('index.html')); });
on('GET', '/p/:slug', (req, res, { slug }) => {
  const p = Products.bySlug(slug);
  if (!p || !p.active) { res.writeHead(404, { 'content-type': MIME['.html'] }); return res.end(renderPage('index.html')); }
  const pp = publicProduct(p);
  if (visitaReal(req, p.id)) Products.view(p.id);
  res.writeHead(200, { 'content-type': MIME['.html'] });
  res.end(renderPage('product.html', { TITLE: esc(pp.title) + ' · ' + esc(config.storeName), DESC: esc(pp.short),
    IMAGE: pp.cover.startsWith('http') ? pp.cover : config.baseUrl + pp.cover,
    DATA: JSON.stringify({ ...pp, packs: packOffers(p), bump: bumpInfo(p), reviews: Reviews.approved(p.id), rating: Reviews.summary(p.id) }).replace(/</g, '\\u003c') }));
});
// 🎁 Regalos gratis a cambio del correo (lead magnet)
const REGALOS = {
  jefa: { title: 'la demo de La Jefa (3 usos gratis)', file: '/app/jefa/demo', app: true,
    next: { slug: 'la-jefa', text: '¿Te gustó? Llévatela completa, sin límites y para siempre:' } },
  ahorro: { title: 'Reto de Ahorro 52 Semanas 2027', file: '/regalos/Reto-de-Ahorro-52-Semanas-Pixelia.zip' },
  navidad: { title: 'Planificador Navideño', file: '/regalos/Planificador-Navideno-Pixelia.zip' },
  reto: { title: 'Reto 30 Días (Google Sheets / Excel)', file: '/regalos/Reto-30-Dias-Pixelia.xlsx',
    next: { slug: 'mi-2027-en-habitos', text: '¿Te gustó? Imagina TODO tu 2027 así: 12 meses, niveles, ánimo diario y tu resumen del año.' } },
};
// ⭐ Reseñas reales con enlace firmado
on('GET', '/baja', (req, res, _, url) => {  // darse de baja de los correos (enlace firmado)
  const ok = darDeBaja(url.searchParams.get('t'));
  res.writeHead(ok ? 200 : 400, { 'content-type': 'text/html; charset=utf-8' });
  res.end(`<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><body style="font-family:system-ui;background:#07060f;color:#eee;display:grid;place-items:center;min-height:90vh;text-align:center;padding:20px"><div><h2>${ok ? '✅ Listo, ya no te enviaremos correos' : 'Enlace no válido'}</h2><p style="color:#a29fc0">${ok ? 'Tus descargas y tu cupón siguen funcionando. Si cambias de idea, vuelve cuando quieras 💜' : 'Escríbenos por Telegram desde la tienda y te ayudamos.'}</p><p><a style="color:#b9a6ff" href="/">Ir a la tienda</a></p></div>`);
});
on('GET', '/resena', (req, res) => { res.writeHead(200, { 'content-type': MIME['.html'] }); res.end(renderPage('resena.html')); });
on('GET', '/api/resena', (req, res, _p, url) => {
  const ts = targets(readToken(url.searchParams.get('t')));
  if (!ts.length) return fail(res, 404, 'Este enlace no es válido o ya venció');
  json(res, 200, { items: ts.map((x) => ({ id: x.p.id, title: x.p.title, emoji: x.p.emoji, cover: publicProduct(x.p).cover, source: x.source, done: !!Reviews.byRef(x.p.id, x.ref) })) });
});
on('POST', '/api/resena', async (req, res) => {
  const b = await body(req, 2e4); const ts = targets(readToken(b.t));
  const x = ts.find((t) => t.p.id === Number(b.product_id));
  if (!x) return fail(res, 404, 'Este enlace no es válido');
  const stars = Math.round(Number(b.stars)); if (!(stars >= 1 && stars <= 5)) return fail(res, 400, 'Elige de 1 a 5 estrellas');
  const name = String(b.name || '').replace(/[<>]/g, '').trim().slice(0, 40), text = String(b.text || '').replace(/[<>]/g, '').trim().slice(0, 800);
  Reviews.add({ product_id: x.p.id, ref: x.ref, source: x.source, name, stars, text });
  notifyReview(Reviews.byRef(x.p.id, x.ref), x.p);
  json(res, 200, { ok: true });
});
on('GET', '/api/regalo/resenas', (req, res) => json(res, 200, { reviews: Object.values(GIFT_SLUGS).flatMap((s) => { const p = Products.bySlug(s); return p ? Reviews.approved(p.id, 10).map((r) => ({ ...r, product: p.title })) : []; }) }));
on('GET', '/binance-qr.jpg', (req, res) => { const f = path.join(path.dirname(config.paths.files), 'binance-qr.jpg');
  serveFile(res, fs.existsSync(f) ? f : path.join(config.paths.public, 'img', 'binance-qr.jpg'), { 'cache-control': 'public, max-age=600' }); });
on('GET', '/regalo', (req, res) => { res.writeHead(200, { 'content-type': MIME['.html'] }); res.end(renderPage('regalo.html')); });
// ===== Apps web de pago (La Jefa…): solo con licencia (?k= del pedido pagado) o en modo dueño. El código NO está en public/.
const APPS = { jefa: { dir: 'jefa', nombre: 'La Jefa', corto: 'La Jefa', color: '#E8337A', slug: 'la-jefa' } };
const licOk = (req, k) => { const id = verifyApp(k); if (id) { const o = Orders.withProduct(id); return !!o && o.status === 'paid'; } return esDueno(req); };
on('GET', '/app/:app', (req, res, { app }) => { if (!APPS[app]) return fail(res, 404, 'No existe'); res.writeHead(301, { location: `/app/${app}/${req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : ''}` }); res.end(); });
on('GET', '/app/:app/', (req, res, { app }, url) => {
  const A = APPS[app]; if (!A) return fail(res, 404, 'No existe');
  const k = url.searchParams.get('k') || '';
  if (!licOk(req, k)) { res.writeHead(302, { location: `/p/${A.slug}` }); return res.end(); }   // sin licencia → a la página de venta
  let html = fs.readFileSync(path.join(path.dirname(new URL(import.meta.url).pathname), 'apps', A.dir, 'index.html'), 'utf8');
  res.writeHead(200, { 'content-type': MIME['.html'], 'cache-control': 'no-cache' });
  res.end(html.replaceAll('{{LIC}}', encodeURIComponent(k)));
});
on('GET', '/app/:app/demo', (req, res, { app }) => {   // DEMO gratis: la app completa con 3 usos (los cuenta la propia app); sin instalar
  const A = APPS[app]; if (!A) return fail(res, 404, 'No existe');
  let html = fs.readFileSync(path.join(path.dirname(new URL(import.meta.url).pathname), 'apps', A.dir, 'index.html'), 'utf8');
  html = html.replace(/<link rel="manifest"[^>]*>/, '').replace('<head>', `<head><script>window.APP_DEMO={usos:${Number(process.env.APP_DEMO_USOS || 3)},comprar:'/p/${A.slug}?ref=demo'}</script>${esDueno(req) ? '' : pixelSnippet()}`);
  res.writeHead(200, { 'content-type': MIME['.html'], 'cache-control': 'no-cache' }); res.end(html);
});
on('GET', '/app/:app/manifest.webmanifest', (req, res, { app }, url) => {
  const A = APPS[app]; if (!A) return fail(res, 404, 'No existe'); const k = encodeURIComponent(url.searchParams.get('k') || '');
  res.writeHead(200, { 'content-type': 'application/manifest+json' });
  res.end(JSON.stringify({ name: A.nombre, short_name: A.corto, start_url: `/app/${app}/?k=${k}`, scope: `/app/${app}/`, display: 'standalone',
    background_color: '#FFF6EE', theme_color: A.color, icons: [192, 512].map((n) => ({ src: `/img/app-${app}-${n}.png`, sizes: `${n}x${n}`, type: 'image/png', purpose: 'any maskable' })) }));
});
on('GET', '/app/:app/sw.js', (req, res, { app }) => {   // funciona sin internet: guarda la última versión de la app
  res.writeHead(200, { 'content-type': MIME['.js'], 'service-worker-allowed': `/app/${app}/` });
  res.end(`const C='app-${app}-v1';self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('activate',e=>self.clients.claim());
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).then(r=>{if(r.ok){const c=r.clone();caches.open(C).then(x=>x.put(e.request,c));}return r;}).catch(()=>caches.match(e.request,{ignoreSearch:true})));});`);
});

on('GET', '/jefa', (req, res) => {   // landing de La Jefa (link del perfil y anuncios): demo gratis a cambio del correo
  const p = Products.bySlug('la-jefa');
  if (p && visitaReal(req, p.id)) Products.view(p.id);
  res.writeHead(200, { 'content-type': MIME['.html'] }); res.end(renderPage('jefa.html'));
});
on('GET', '/reto', (req, res) => {   // las visitas cuentan en el regalo oculto (para saber cuánta gente llega desde los reels)
  const p = Products.bySlug('regalo-reto-30-dias');
  if (p && visitaReal(req, p.id)) Products.view(p.id);
  res.writeHead(200, { 'content-type': MIME['.html'] }); res.end(renderPage('reto.html'));
});  // página corta del Reto 30 Días (reel → bio)
on('POST', '/api/regalo', async (req, res) => {
  const ip = String(req.headers['x-forwarded-for'] || req.socket.remoteAddress || '').split(',')[0];
  const n = (subHits.get(ip) || 0) + 1; subHits.set(ip, n); if (subHits.size > 5000) subHits.clear();
  if (n > 8) return fail(res, 429, 'Demasiados intentos, prueba más tarde');
  const b = await body(req, 1e4); const email = String(b.email || '').trim().slice(0, 120);
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return fail(res, 400, 'Revisa tu correo');
  if (!b.consent) return fail(res, 400, 'Marca la casilla para poder enviarte el regalo');
  const ids = [...new Set((Array.isArray(b.regalos) ? b.regalos : []).filter((x) => REGALOS[x]))];
  if (!ids.length) return fail(res, 400, 'Elige al menos un regalo');
  const s = Subscribers.add(email, 'regalo:' + ids.join('+'));
  const links = ids.map((id) => ({ title: REGALOS[id].title, url: config.baseUrl + REGALOS[id].file, app: !!REGALOS[id].app }));
  const code = s.used_order ? null : s.code, off = Math.round(COUPON_OFF * 100);
  if (config.email.resendKey) {
    sendEmail(email, `🎁 Tu regalo de ${config.storeName}`, links.map((l) => `${l.title}: ${l.url}`).join('\n') + (code ? `\n\nTu cupón de ${off}%: ${code}` : ''),
      `<div style="font-family:system-ui,sans-serif;max-width:520px;margin:auto;padding:24px;background:#0f0f1a;color:#eee;border-radius:16px">
       <h2 style="margin:0 0 12px">🎁 ¡Aquí está tu regalo!</h2>
       ${links.map((l) => `<p><a style="display:inline-block;background:#ff4fa3;color:#fff;padding:12px 18px;border-radius:12px;text-decoration:none;font-weight:700" href="${l.url}">${l.app ? '👑 Abrir ' : '⬇️ Descargar '}${esc(l.title)}</a></p>`).join('')}
       ${code ? `<p style="margin-top:18px">Y para tu primera compra, <b>${off}% de descuento</b> con el cupón:</p><p style="font-size:26px;font-weight:800;letter-spacing:2px;background:#7c5cff;display:inline-block;padding:8px 16px;border-radius:12px">${code}</p>` : ''}
       ${ids.map((id) => REGALOS[id].next).filter(Boolean).map((n) => { const np = Products.bySlug(n.slug); return np && np.active ? `<p style="margin-top:18px">${esc(n.text)}</p><p><a style="color:#b9a6ff;font-weight:700" href="${config.baseUrl}/p/${np.slug}${code ? '?cupon=' + code : ''}">👉 ${esc(np.title)}${code ? ` con tu ${off}%` : ''}</a></p>` : ''; }).join('')}
       <p style="color:#aab">Mira todos los productos en <a style="color:#b9a6ff" href="${config.baseUrl}">${esc(config.baseUrl.replace(/^https?:\/\//, ''))}</a></p></div>`)
      .catch((e) => console.error('[regalo]', e.message));
  }
  json(res, 200, { links, code, off });
});
on('GET', '/pedido/:id', (req, res) => { res.writeHead(200, { 'content-type': MIME['.html'] }); res.end(renderPage('order.html')); });
on('GET', '/legal', (req, res) => { res.writeHead(200, { 'content-type': MIME['.html'] }); res.end(renderPage('legal.html')); });
// Reels e imágenes de anuncios terminados (públicos: Instagram/Facebook los descargan desde aquí para publicarlos)
on('GET', '/media/anuncios/:slug/:file', (req, res, { slug, file }) => {
  const s = String(slug).replace(/[^a-z0-9-]/gi, ''), f = path.basename(decodeURIComponent(String(file)));
  if (!/\.(mp4|jpg)$/i.test(f)) { res.writeHead(404); return res.end('No encontrado'); }
  serveFile(res, path.join(path.dirname(config.paths.files), 'anuncios', s, f), { 'cache-control': 'public, max-age=3600' });
});
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
  let pr; try { pr = priceFor(p, b); } catch (e) { return fail(res, 400, e.message); }
  const extra = { coupon: pr.coupon || '', upsell_of: pr.upsell_of || '' };
  if (b.bump && !pr.upsell_of) { const bi = bumpInfo(p); if (bi && bi.slug === b.bump) { pr.cents += Math.round(bi.bumpPrice * 100); extra.bump_id = Products.bySlug(bi.slug).id; } }
  if (b.method === 'paypal') {
    if (!paypalEnabled()) return fail(res, 400, 'PayPal no está activo');
    const o = Orders.create({ product_id: p.id, email, whatsapp, method: 'paypal', amount_cents: pr.cents, currency: 'USD', lang: b.lang, prueba: esDueno(req), ...extra });
    try {
      const paypalId = await createPaypalOrder(o, p);
      Orders.update(o.id, { provider_ref: paypalId });
      return json(res, 200, { id: o.id, key: orderKey(o.id), paypalId });
    } catch (e) { console.error(e.message); return fail(res, 502, 'No se pudo iniciar el pago con PayPal'); }
  }
  if (b.method === 'binance') {
    if (!binanceEnabled()) return fail(res, 400, 'Binance no está activo');
    const o = Orders.create({ product_id: p.id, email, whatsapp, method: 'binance', amount_cents: uniqueAmount(pr.cents), currency: 'USDT', lang: b.lang, prueba: esDueno(req), ...extra });
    return json(res, 200, { id: o.id, key: orderKey(o.id), amount: (o.amount_cents / 100).toFixed(2), payId: config.binance.payId });
  }
  return fail(res, 400, 'Método de pago no válido');
});

// Cupón: comprobar antes de pagar
on('POST', '/api/coupon', async (req, res) => {
  const b = await body(req, 1e4); const p = Products.bySlug(String(b.slug || ''));
  if (!p?.active) return fail(res, 404, 'Producto no disponible');
  try { const pr = priceFor(p, { coupon: b.code }); json(res, 200, { code: pr.coupon, price: pr.cents / 100, off: Math.round(COUPON_OFF * 100) }); }
  catch (e) { fail(res, 400, e.message); }
});
// Correo a cambio de cupón (también suma a la lista para futuras ofertas)
const subHits = new Map();
on('POST', '/api/subscribe', async (req, res) => {
  const ip = String(req.headers['x-forwarded-for'] || req.socket.remoteAddress || '').split(',')[0];
  const n = (subHits.get(ip) || 0) + 1; subHits.set(ip, n); if (subHits.size > 5000) subHits.clear();
  if (n > 8) return fail(res, 429, 'Demasiados intentos, prueba más tarde');
  const b = await body(req, 1e4); const email = String(b.email || '').trim().slice(0, 120);
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return fail(res, 400, 'Revisa tu correo');
  const s = Subscribers.add(email, b.source);
  const mp = b.sample ? Products.bySlug(String(b.source || '')) : null;   // muestra gratis del producto
  const muestra = mp && mp.sample_url ? { title: mp.sample_title || 'Muestra gratis', url: mp.sample_url.startsWith('http') ? mp.sample_url : config.baseUrl + mp.sample_url } : null;
  if (s.used_order && !muestra) return fail(res, 400, 'Este correo ya usó su cupón de bienvenida 💜');
  if (muestra && config.email.resendKey && (s.existed || s.used_order))
    sendEmail(email, `🎁 Tu muestra gratis: ${muestra.title}`, `Aquí tienes tu muestra: ${muestra.url}`,
      `<div style="font-family:system-ui,sans-serif;max-width:520px;margin:auto;padding:24px;background:#0f0f1a;color:#eee;border-radius:16px"><h2 style="margin:0 0 8px">🎁 Tu muestra gratis</h2><p>${esc(muestra.title)}</p><p><a style="display:inline-block;background:#7c5cff;color:#fff;padding:12px 18px;border-radius:12px;text-decoration:none;font-weight:700" href="${muestra.url}">Descargar muestra</a></p></div>`).catch(() => {});
  if (s.used_order) return json(res, 200, { code: '', off: 0, sample: muestra });
  if (!s.existed && config.email.resendKey) {
    const off = Math.round(COUPON_OFF * 100);
    sendEmail(email, `🎁 Tu cupón de ${off}% en ${config.storeName}`, `Tu cupón: ${s.code} (${off}% en tu primera compra de un producto).`,
      `<div style="font-family:system-ui,sans-serif;max-width:520px;margin:auto;padding:24px;background:#0f0f1a;color:#eee;border-radius:16px">
       <h2 style="margin:0 0 8px">🎁 ¡Bienvenida/o a ${esc(config.storeName)}!</h2><p>Tu cupón de <b>${off}% de descuento</b> en tu primera compra:</p>
       <p style="font-size:28px;font-weight:800;letter-spacing:2px;background:#7c5cff;display:inline-block;padding:10px 18px;border-radius:12px">${s.code}</p>
       ${muestra ? `<p>🎁 Y tu muestra gratis: <a style="color:#b9a6ff" href="${muestra.url}">${esc(muestra.title)}</a></p>` : ''}
       <p style="color:#aab">Válido una vez, en cualquier producto suelto. <a style="color:#b9a6ff" href="${config.baseUrl}">Ver la tienda</a></p></div>`)
      .catch((e) => console.error('[cupón]', e.message));
  }
  json(res, 200, { code: s.code, off: Math.round(COUPON_OFF * 100), sample: muestra });
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
  json(res, 200, { id: o.id, status: o.status, method: o.method, title: o.title, emoji: o.emoji, slug: o.slug, email: o.email,
    upsell: upsellFor(o), pack: o.bundle_ids ? Products.bundleItems(o).map((i) => i.title) : null,
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
on('GET', '/d/:id/:exp/:sig', (req, res, { id, exp, sig }, url) => {
  const problem = verifyDownload(id, exp, sig);
  const o = Orders.withProduct(id);
  const msg = (t) => { res.writeHead(403, { 'content-type': MIME['.html'] }); res.end(renderPage('order.html', { DATA: JSON.stringify({ error: t }) })); };
  if (problem || !o || o.status !== 'paid') return msg(problem === 'caducado' ? 'El enlace caducó. Pide uno nuevo en el bot con /mispedidos o escríbenos.' : 'Enlace no válido.');
  let item = o;
  if (o.bundle_ids) {  // pack: página con un botón por producto
    const items = Products.bundleItems(o); const i = Number(url.searchParams.get('i'));
    if (!i) {
      res.writeHead(200, { 'content-type': MIME['.html'] });
      return res.end(renderPage('order.html', { DATA: JSON.stringify({ packDownload: { title: o.title, id: o.id,
        items: items.map((x) => ({ title: x.title, emoji: x.emoji, url: `${url.pathname}?i=${x.id}` })) } }).replace(/</g, '\\u003c') }));
    }
    item = items.find((x) => x.id === i); if (!item) return msg('Ese producto no está en tu pack.');
  }
  const limit = config.maxDownloads * (o.bundle_ids ? Math.max(1, Products.bundleItems(o).length) : 1);
  if (o.downloads >= limit) return msg('Llegaste al máximo de descargas de este pedido. Escríbenos si necesitas ayuda.');
  Orders.update(o.id, { downloads: o.downloads + 1 });
  if (item.external_url?.startsWith('/app/')) { res.writeHead(302, { location: `${item.external_url}?k=${appLicense(o.id)}` }); return res.end(); }  // app web: su enlace con licencia
  if (item.external_url) { res.writeHead(302, { location: item.external_url }); return res.end(); }
  const file = path.join(config.paths.files, path.basename(item.file_name || ''));
  if (!item.file_name || !fs.existsSync(file)) return msg('El archivo no está disponible todavía. Te lo enviaremos pronto.');
  serveFile(res, file, { 'content-disposition': `attachment; filename="${encodeURIComponent(path.basename(file))}"` });
});

// ===== Admin =====
// La clave viaja codificada (encodeURIComponent) para admitir tildes, ñ y símbolos; se ignoran espacios al inicio/final.
const adminKeyFrom = (req) => { const raw = String(req.headers['x-admin-key'] || ''); try { return decodeURIComponent(raw).trim(); } catch { return raw.trim(); } };
const adminOkKey = (raw) => { let k = String(raw || ''); try { k = decodeURIComponent(k); } catch {} k = k.trim(); const pw = String(config.adminPassword || '').trim();
  return !!pw && !!k && crypto.timingSafeEqual(crypto.createHash('sha256').update(k).digest(), crypto.createHash('sha256').update(pw).digest()); };
const adminOk = (req) => adminOkKey(req.headers['x-admin-key']);

on('GET', '/api/admin/summary', (req, res) => adminOk(req) ? json(res, 200, {
  stats: Orders.stats(), products: Products.list({ all: true }), orders: Orders.recent(100), subscribers: Subscribers.count(),
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
    featured: b.featured ? 1 : 0, active: b.active === false ? 0 : 1,
    bundle_ids: Array.isArray(b.bundle_ids) ? b.bundle_ids.map(Number).filter((x) => x && x !== Number(b.id)).join(',') : undefined };
  if (b.fileBase64 && b.fileName) {
    const name = `${slug}-${Date.now()}${path.extname(b.fileName).toLowerCase().replace(/[^.\w]/g, '')}`;
    await fs.promises.writeFile(path.join(config.paths.files, name), Buffer.from(b.fileBase64, 'base64'));
    data.file_name = name;
  }
  if (data.bundle_ids && data.active) {  // un pack solo se publica si todos sus productos tienen archivo
    const ids = data.bundle_ids.split(',').map(Number); const items = ids.map((i) => Products.byId(i)).filter(Boolean);
    const missing = items.filter((i) => !i.file_name && !i.external_url);
    if (items.length < 2) return fail(res, 400, 'Un pack necesita al menos 2 productos');
    if (missing.length) return fail(res, 400, 'Primero sube el archivo de: ' + missing.map((i) => i.title).join(', '));
  }
  const before = data.id ? Products.byId(data.id) : null;
  try {
    const saved = Products.upsert(data);
    if (saved.active && (!before || !before.active) && !saved.bundle_ids && (saved.file_name || saved.external_url)) offerAds(saved).catch(() => {});
    json(res, 200, saved);
  } catch (e) { fail(res, 400, e.message.includes('UNIQUE') ? 'Ya existe un producto con ese enlace (slug)' : e.message); }
});

on('GET', '/api/admin/subscribers.csv', (req, res, _, url) => {
  if (!adminOk(req) && !adminOkKey(url.searchParams.get('k'))) return fail(res, 401, 'Clave incorrecta');
  res.writeHead(200, { 'content-type': 'text/csv; charset=utf-8', 'content-disposition': 'attachment; filename="suscriptores.csv"' });
  res.end('email,cupon,usado_en_pedido,fecha\n' + Subscribers.list(100000).map((s) => [s.email, s.code, s.used_order || '', s.created_at].join(',')).join('\n'));
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

// ===== Estudio de anuncios (el contenedor "pixelia-estudio" pide trabajos aquí) =====
on('POST', '/api/studio/next', (req, res) => {
  if (!n8nOk(req)) return fail(res, 401, 'x-api-key incorrecta');
  const j = AdJobs.claim(); if (!j) { res.writeHead(204); return res.end(); }
  const p = Products.byId(j.product_id); if (!p) { AdJobs.finish(j.id, 'error', {}, 'producto no existe'); res.writeHead(204); return res.end(); }
  const prev = AdJobs.last(p.id);
  json(res, 200, { job: { id: j.id, options: j.options }, product: { ...publicProduct(p), file_name: p.file_name, external_url: p.external_url, dominio: config.baseUrl.replace(/^https?:\/\//, '') },
    previous: prev ? JSON.parse(prev.result || '{}') : null });
});
on('POST', '/api/studio/jobs/:id', async (req, res, { id }) => {
  if (!n8nOk(req)) return fail(res, 401, 'x-api-key incorrecta');
  const b = await body(req, 1e6); AdJobs.finish(Number(id), b.status === 'done' ? 'done' : 'error', b.result || {}, b.error || '');
  json(res, 200, { ok: true });
  const r = b.result || {}; const p = r.product_id && Products.byId(Number(r.product_id));
  if (b.status === 'done' && p) sendAdPicker(p, r.sel || {}, r.sug || {}).catch((e) => console.error('[estudio]', e.message));
});
on('POST', '/api/admin/products/:id/ads', async (req, res, { id }) => {
  if (!adminOk(req)) return fail(res, 401, 'Clave incorrecta');
  json(res, 200, AdJobs.enqueue(Number(id), (await body(req, 1e4)).options || {}));
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

if (process.env.NO_BOT !== '1') { startBot(); startRadarBot(); startExplorador(); startReviews(); startSecuencia(); }
