// Utilidades compartidas: idioma, API, tarjetas, animaciones, modo Telegram.
const DICT = {
  es: {
    catalog: 'Catálogo', how: 'Cómo funciona', support: 'Soporte', search: 'Buscar productos…', all: 'Todo',
    buy: 'Comprar ahora', instant: 'Entrega inmediata', bestseller: '🔥 Top', empty: 'No encontramos productos con ese filtro.',
    email: 'Correo electrónico', whatsapp: 'WhatsApp (opcional)', sendTo: '¿Dónde te enviamos el producto?',
    payWith: 'Elige cómo pagar', continue: 'Continuar', loading: 'Cargando…', copied: 'Copiado ✓', copy: 'Copiar',
    orderPaid: '¡Pago confirmado!', orderReview: 'Verificando tu pago', orderPending: 'Pedido pendiente de pago',
    orderRejected: 'No pudimos verificar el pago', download: 'Descargar ahora', getTelegram: 'Recibir también en Telegram',
    back: 'Volver a la tienda', stars: 'Pagar con Telegram Stars',
  },
  en: {
    catalog: 'Catalog', how: 'How it works', support: 'Support', search: 'Search products…', all: 'All',
    buy: 'Buy now', instant: 'Instant delivery', bestseller: '🔥 Top', empty: 'No products match that filter.',
    email: 'Email', whatsapp: 'WhatsApp (optional)', sendTo: 'Where should we send your product?',
    payWith: 'Choose how to pay', continue: 'Continue', loading: 'Loading…', copied: 'Copied ✓', copy: 'Copy',
    orderPaid: 'Payment confirmed!', orderReview: 'Checking your payment', orderPending: 'Order awaiting payment',
    orderRejected: 'We could not verify the payment', download: 'Download now', getTelegram: 'Also get it on Telegram',
    back: 'Back to the store', stars: 'Pay with Telegram Stars',
  },
};
let LANG = 'es';
try { LANG = localStorage.getItem('lang') || 'es'; } catch {}
const t = (k) => (DICT[LANG] && DICT[LANG][k]) || DICT.es[k] || k;

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const money = (n) => '$' + Number(n).toFixed(2);
const escH = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

async function api(path, opts = {}) {
  const res = await fetch(path, { ...opts, headers: { 'content-type': 'application/json', ...(opts.headers || {}) },
    body: opts.body && typeof opts.body !== 'string' ? JSON.stringify(opts.body) : opts.body });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Error');
  return data;
}

// Telegram Mini App
const TG = window.Telegram?.WebApp;
const inTelegram = !!(TG && TG.initData);
if (inTelegram) {
  document.documentElement.classList.add('tg');
  document.addEventListener('DOMContentLoaded', () => document.body.classList.add('tg'));
  TG.ready(); TG.expand();
  try { TG.setHeaderColor('#07060f'); TG.setBackgroundColor('#07060f'); } catch {}
}

function toast(msg) {
  let el = $('.toast');
  if (!el) { el = document.createElement('div'); el.className = 'toast'; document.body.appendChild(el); }
  el.textContent = msg; el.classList.add('show');
  clearTimeout(el._t); el._t = setTimeout(() => el.classList.remove('show'), 2200);
}

function copyText(text) { navigator.clipboard?.writeText(text).then(() => toast(t('copied'))); }

function productCard(p) {
  const off = p.compare > p.price ? Math.round((1 - p.price / p.compare) * 100) : 0;
  return `<a class="card reveal" href="/p/${encodeURIComponent(p.slug)}" data-tilt>
    <div class="cover"><img loading="lazy" src="${escH(p.cover)}" alt="${escH(p.title)}">
      <span class="tag">${escH(p.category)}</span>${p.featured ? `<span class="tag hot">${t('bestseller')}</span>` : ''}</div>
    <div class="body"><h3>${escH(p.title)}</h3><p>${escH(p.short)}</p>
      <div class="price"><b>${money(p.price)}</b>${off ? `<s>${money(p.compare)}</s>` : ''}<span class="stars">${inTelegram ? p.stars + ' ⭐' : ''}</span></div></div>
    <div class="shine"></div></a>`;
}

function enhance(root = document) {
  // Aparición al hacer scroll
  const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { threshold: .08 });
  $$('.reveal:not(.in)', root).forEach((el, i) => { el.style.transitionDelay = Math.min(i * 40, 300) + 'ms'; io.observe(el); });
  // Inclinación 3D y brillo que sigue al cursor
  if (matchMedia('(hover:hover)').matches) $$('[data-tilt]', root).forEach((card) => {
    card.addEventListener('pointermove', (e) => {
      const r = card.getBoundingClientRect(); const x = (e.clientX - r.left) / r.width; const y = (e.clientY - r.top) / r.height;
      card.style.transform = `perspective(900px) rotateX(${(0.5 - y) * 7}deg) rotateY(${(x - 0.5) * 7}deg) translateY(-4px)`;
      card.style.setProperty('--mx', x * 100 + '%'); card.style.setProperty('--my', y * 100 + '%');
    });
    card.addEventListener('pointerleave', () => { card.style.transform = ''; });
  });
}

function setupLang() {
  const b = $('.lang'); if (!b) return;
  b.textContent = LANG === 'es' ? 'EN' : 'ES';
  b.onclick = () => { try { localStorage.setItem('lang', LANG === 'es' ? 'en' : 'es'); } catch {} location.reload(); };
  $$('[data-t]').forEach((el) => { el.textContent = t(el.dataset.t); });
  $$('[data-tp]').forEach((el) => { el.placeholder = t(el.dataset.tp); });
}
document.addEventListener('DOMContentLoaded', setupLang);
