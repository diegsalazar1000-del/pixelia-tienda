// 📊 PANEL en Telegram (Diego 11-nov: "mucho texto, muy feo"): UN solo mensaje con botones; cada botón REEMPLAZA
// el contenido del mismo mensaje (editMessageText) en vez de mandar mensajes nuevos.
// Vistas: inicio (resumen) · ventas · un producto (visitas, embudo paso a paso, ventas y su campaña) · campañas · una campaña.
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../config.js';
import { db } from '../db.js';
import { api } from './anuncios-meta.js';

const q = (sql, ...a) => { try { return db.prepare(sql).all(...a); } catch { return []; } };
const one = (sql, ...a) => q(sql, ...a)[0] || {};
const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const usd = (c) => '$' + (Number(c || 0) / 100).toFixed(2);
const pct = (n, d) => (d ? ` <i>(${Math.round((n || 0) / d * 100)}%)</i>` : '');
const hora = () => new Date().toLocaleTimeString('es-VE', { timeZone: 'America/Caracas', hour: '2-digit', minute: '2-digit' });

// Productos con landing/demo medida. Para agregar uno nuevo: una línea aquí.
export const PRODUCTOS = [
  { k: 'jefa', b: '👑 Jefa', t: '👑 La Jefa', slug: 'la-jefa', demo: 'jefa', camp: /jefa/i },
  { k: 'aventura', b: '📚 Aventura', t: '📚 Mi Gran Aventura', slug: 'mi-gran-aventura', w: 'aventura', camp: /aventura/i,
    pasos: [['vio', 'cargaron la página'], ['s5', 'se quedaron 5 s'], ['nombre', 'escribieron el nombre'], ['comp', 'eligieron compañero'], ['quiero', 'tocaron "Quiero su libro"'], ['correo', 'dejaron el correo']] },
  { k: 'plan', b: '📊 Plan', t: '📊 Plan 2027', slug: 'plan-financiero-2027', w: 'plan', camp: /plan financiero/i,
    pasos: [['vio', 'cargaron la página'], ['s5', 'se quedaron 5 s'], ['p1', 'eligieron a qué se dedican'], ['p2', 'pusieron su ingreso'], ['p3', 'pusieron sus gastos'], ['plan', 'vieron su plan'], ['quiero', 'tocaron "Quiero mi plan"'], ['correo', 'dejaron el correo']] },
];

export function teclado(v) {
  const b = (t, d) => ({ text: (v === d ? '• ' : '') + t, callback_data: 'pn:' + d });
  return [[b('🏠 Resumen', 'inicio'), b('🛒 Ventas', 'ventas')], PRODUCTOS.map((p) => b(p.b || p.t, p.k)),
    [b('📣 Campañas', 'camps'), { text: '🔄 Actualizar', callback_data: 'pn:' + v + ':r' }]];
}

// --- Meta (con caché de 3 min para que los botones respondan rápido) ---
const CACHE = new Map();
const dia = (n) => new Date(Date.now() - n * 864e5).toLocaleDateString('en-CA', { timeZone: 'America/Caracas' });
async function ins(id, preset, extra = {}) {
  const k = id + preset + JSON.stringify(extra), c = CACHE.get(k);
  if (c && Date.now() - c.t < 180e3) return c.v;
  const rango = preset === 'last_7d' ? { time_range: JSON.stringify({ since: dia(6), until: dia(0) }) } : { date_preset: preset };
  const v = await api('GET', `${id}/insights`, { fields: 'spend,impressions,reach,frequency,clicks,ctr,actions', ...rango, ...extra }).then((r) => r.data || []).catch(() => []);
  CACHE.set(k, { t: Date.now(), v }); return v;
}
const acc = (r, t) => Number((r?.actions || []).find((a) => a.action_type === t)?.value || 0);
const campanas = () => { try { return JSON.parse(fs.readFileSync(path.join(path.dirname(config.paths.db), 'campanas.json'), 'utf8')).filter((c) => c.camp && c.estado !== 'borrada'); } catch { return []; } };
async function estado(id) {
  const k = 'st' + id, c = CACHE.get(k); if (c && Date.now() - c.t < 180e3) return c.v;
  const v = await api('GET', id, { fields: 'name,effective_status,daily_budget' }).catch(() => null); CACHE.set(k, { t: Date.now(), v }); return v;
}
const EST = { ACTIVE: '🟢 activa', PAUSED: '⏸️ en pausa', CAMPAIGN_PAUSED: '⏸️ en pausa', IN_PROCESS: '⏳ revisándose', WITH_ISSUES: '⚠️ con problemas', DISAPPROVED: '❌ rechazada' };

async function bloqueCampana(c) {
  const st = await estado(c.camp); if (!st) return null;
  const [h] = await ins(c.camp, 'today'), [s] = await ins(c.camp, 'last_7d');
  const lv = (r) => acc(r, 'landing_page_view'), g = (r) => Number(r?.spend || 0);
  const l = [`📣 <b>${esc(c.titulo)}</b> · ${EST[st.effective_status] || st.effective_status}`,
    `   Hoy: $${g(h).toFixed(2)} · ${lv(h)} visitas${lv(h) ? ` · $${(g(h) / lv(h)).toFixed(3)} c/u` : ''}`,
    `   7 días: $${g(s).toFixed(2)} · ${lv(s)} visitas${lv(s) ? ` · $${(g(s) / lv(s)).toFixed(3)} c/u` : ''} · CTR ${Number(s?.ctr || 0).toFixed(1)}%`];
  const ads = await api('GET', `${c.camp}/ads`, { fields: 'name,effective_status', limit: 20 }).then((r) => r.data || []).catch(() => []);
  const fil = [];
  for (const a of ads) { const [r] = await ins(a.id, 'last_7d'); if (r && g(r) > 0) fil.push({ n: a.name.split('·').slice(-2).join('·').trim(), g: g(r), v: lv(r) }); }
  fil.sort((a, b) => (a.v ? a.g / a.v : 1e9) - (b.v ? b.g / b.v : 1e9));
  if (fil.length) l.push('   🏆 Mejor anuncio: ' + esc(fil[0].n) + (fil[0].v ? ` ($${(fil[0].g / fil[0].v).toFixed(3)} por visita)` : ''));
  if (fil.length > 1) l.push('   🐢 El más caro: ' + esc(fil[fil.length - 1].n) + (fil.at(-1).v ? ` ($${(fil.at(-1).g / fil.at(-1).v).toFixed(3)})` : ' (sin visitas)'));
  return l.join('\n');
}

// --- Vistas ---
async function inicio() {
  const vis = one(`SELECT SUM(CASE WHEN day = date('now') THEN views ELSE 0 END) h, SUM(views) s FROM product_views WHERE day >= date('now','-6 day')`);
  const cor = one(`SELECT SUM(created_at >= date('now')) h, COUNT(*) s FROM subscribers WHERE created_at >= date('now','-6 day')`);
  const ven = (d) => one(`SELECT COUNT(*) n, SUM(amount_cents) c FROM orders WHERE status = 'paid' AND COALESCE(prueba,0) = 0 AND currency != 'XTR' AND paid_at >= ${d}`);
  const vh = ven("date('now')"), vs = ven("date('now','-6 day')");
  const act = process.env.META_AD_ACCOUNT || '';
  const [mh] = act ? await ins(act, 'today') : [], [ms] = act ? await ins(act, 'last_7d') : [];
  const gs = Number(ms?.spend || 0);
  return [`📊 <b>Cómo vamos</b> · ${hora()}`, '<i>hoy · últimos 7 días</i>', '',
    `👀 Visitas: <b>${vis.h || 0}</b> · ${vis.s || 0}`,
    `📩 Correos: <b>${cor.h || 0}</b> · ${cor.s || 0}`,
    `🛒 Ventas: <b>${vh.n || 0}</b> (${usd(vh.c)}) · ${vs.n || 0} (${usd(vs.c)})`,
    `💸 Anuncios: <b>$${Number(mh?.spend || 0).toFixed(2)}</b> · $${gs.toFixed(2)}`,
    vs.n ? `🎯 Cada venta costó en anuncios: $${(gs / vs.n).toFixed(2)}` : '🎯 Aún sin ventas esta semana',
    '', 'Toca un producto para ver su embudo 👇'].join('\n');
}

function ventas() {
  const L = q(`SELECT o.paid_at, o.method, o.amount_cents, o.currency, p.emoji, p.title FROM orders o JOIN products p ON p.id = o.product_id
    WHERE o.status = 'paid' AND COALESCE(o.prueba,0) = 0 ORDER BY o.paid_at DESC LIMIT 8`);
  const tot = q(`SELECT p.emoji, p.title, COUNT(*) n, SUM(o.amount_cents) c FROM orders o JOIN products p ON p.id = o.product_id
    WHERE o.status = 'paid' AND COALESCE(o.prueba,0) = 0 AND o.currency != 'XTR' AND o.paid_at >= date('now','-6 day') GROUP BY p.id ORDER BY n DESC`);
  const MET = { pagomovil: 'Pago Móvil', paypal: 'PayPal', binance: 'Binance', stars: 'Stars' };
  const f = (t) => new Date(t.replace(' ', 'T') + 'Z').toLocaleString('es-VE', { timeZone: 'America/Caracas', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  return ['🛒 <b>Ventas</b>', '', '<b>Últimas:</b>', ...(L.length ? L.map((o) => `• ${f(o.paid_at)} · ${esc(o.emoji)} ${esc(o.title.slice(0, 28))} · ${MET[o.method] || o.method} · ${o.currency === 'XTR' ? o.amount_cents + '⭐' : usd(o.amount_cents)}`) : ['Todavía ninguna 🙏']),
    '', '<b>7 días por producto:</b>', ...(tot.length ? tot.map((t) => `${esc(t.emoji)} ${esc(t.title.slice(0, 30))}: ${t.n} · ${usd(t.c)}`) : ['—'])].join('\n');
}

async function producto(P) {
  const pr = one('SELECT id FROM products WHERE slug = ?', P.slug);
  const vis = pr.id ? one(`SELECT SUM(CASE WHEN day = date('now') THEN views ELSE 0 END) h, SUM(views) s FROM product_views WHERE product_id = ? AND day >= date('now','-6 day')`, pr.id) : {};
  const ven = pr.id ? one(`SELECT COUNT(*) n, SUM(amount_cents) c FROM orders WHERE product_id = ? AND status = 'paid' AND COALESCE(prueba,0) = 0 AND paid_at >= date('now','-6 day')`, pr.id) : {};
  const l = [`${P.t} · ${hora()}`, `<i>7 días</i>`, '', `👀 Visitas: hoy <b>${vis.h || 0}</b> · semana ${vis.s || 0}`, ''];
  const ev = (app) => Object.fromEntries(q(`SELECT evento, SUM(n) n FROM app_eventos WHERE app = ? AND day >= date('now','-6 day') GROUP BY evento`, app).map((r) => [r.evento, r.n]));
  if (P.demo) {
    const e = ev(P.demo), w = ev('w:' + P.demo), ab = e.abrio || 0;
    // medir.js dentro de la demo: "abrio" cuenta el toque (el servidor recibe el pedido); "vio" = la página de verdad cargó en el celular
    l.push('🧭 <b>Qué hacen en la demo</b>', `▸ Tocaron el enlace: <b>${ab}</b>`, `▸ Cargó la página: <b>${w.vio || 0}</b>${pct(w.vio, ab)}`, `▸ Se quedaron 5 s: <b>${w.s5 || 0}</b>${pct(w.s5, ab)}`, `▸ Se quedaron 15 s: <b>${w.s15 || 0}</b>${pct(w.s15, ab)}`);
    const of = Object.entries(e).filter(([k]) => k.startsWith('of_')).reduce((a, [, n]) => a + n, 0);
    l.push(`▸ Eligieron oficio: <b>${of}</b>${pct(of, ab)}`, `▸ La usaron 1 vez: <b>${e.uso1 || 0}</b>${pct(e.uso1, ab)}`, `▸ Llegaron a 3 usos: <b>${e.uso3 || 0}</b>${pct(e.uso3, ab)}`,
      `▸ Tocaron comprar: <b>${e.compra || 0}</b>${pct(e.compra, ab)}`, `▸ Dejaron correo: <b>${e.correo || 0}</b>${pct(e.correo, ab)}`);
    const ofs = Object.entries(e).filter(([k]) => k.startsWith('of_')).sort((a, b) => b[1] - a[1]).slice(0, 4);
    if (ofs.length) l.push('', '💼 Oficios (demo): ' + ofs.map(([k, n]) => `${k.slice(3)} ${n}`).join(' · '));
    const cof = Object.entries(e).filter(([k]) => k.startsWith('c_of_')).sort((a, b) => b[1] - a[1]);
    if (cof.length) l.push('🛍️ Clientes la usan para: ' + cof.map(([k, n]) => `${k.slice(5)} ${n}`).join(' · '));
    const NOM = { caro: '💸 cara', pago: '💳 no sabe pagar', nosirve: '🤷 no le sirve', dificil: '😵 difícil', luego: '⏳ después' };
    const no = Object.entries(e).filter(([k]) => k.startsWith('no_')).sort((a, b) => b[1] - a[1]);
    if (no.length) l.push('🚧 Qué las frenó: ' + no.map(([k, n]) => `${NOM[k.slice(3)] || k} ${n}`).join(' · '));
  } else {
    const e = ev('w:' + P.w), base = e.vio || 0;
    l.push('🧭 <b>Hasta dónde llegan</b>');
    let peor = null, ant = base;
    for (const [k, t] of P.pasos) {
      const n = e[k] || 0; l.push(`▸ ${t}: <b>${n}</b>${k === 'vio' ? '' : pct(n, base)}`);
      if (k !== 'vio' && ant > 4) { const caida = 1 - n / ant; if (!peor || caida > peor.c) peor = { t, c: caida }; }
      ant = n;
    }
    if (peor && peor.c > 0.3) l.push('', `🎯 Donde más se van: antes de "<b>${esc(peor.t)}</b>" (se pierde el ${Math.round(peor.c * 100)}%)`);
  }
  l.push('', `🛒 Ventas: <b>${ven.n || 0}</b> · ${usd(ven.c)}`);
  const cs = campanas().filter((c) => P.camp.test(c.titulo || ''));
  for (const c of cs.slice(-2)) { const b = await bloqueCampana(c).catch(() => null); if (b) l.push('', b); }
  return l.join('\n');
}

async function camps() {
  const L = []; const rows = [];
  for (const [i, c] of campanas().entries()) {
    const st = await estado(c.camp); if (!st || !/ACTIVE|PAUSED|IN_PROCESS|ISSUES/.test(st.effective_status)) continue;
    const [s] = await ins(c.camp, 'last_7d');
    L.push(`${EST[st.effective_status] || st.effective_status} · <b>${esc(c.titulo)}</b> · $${Number(s?.spend || 0).toFixed(2)} en 7 días · ${acc(s, 'landing_page_view') || acc(s, 'onsite_conversion_profile_visit') || 0} visitas`);
    rows.push([{ text: (c.titulo || 'Campaña').slice(0, 30), callback_data: 'pn:c' + i }]);
  }
  return { text: ['📣 <b>Campañas</b> · ' + hora(), '', ...(L.length ? L : ['Ninguna activa.']), '', 'Toca una para ver el detalle 👇'].join('\n'), extra: rows };
}

export async function vistaPanel(v = 'inicio') {
  let text, extra = [];
  if (v === 'ventas') text = ventas();
  else if (v === 'camps') ({ text, extra } = await camps());
  else if (/^c\d+$/.test(v)) { const c = campanas()[Number(v.slice(1))]; text = (c && await bloqueCampana(c).catch(() => null)) || 'Esa campaña ya no está.'; extra = [[{ text: '⬅️ Campañas', callback_data: 'pn:camps' }]]; }
  else if (PRODUCTOS.find((p) => p.k === v)) text = await producto(PRODUCTOS.find((p) => p.k === v));
  else { v = 'inicio'; text = await inicio(); }
  return { text: text.slice(0, 4000), reply_markup: { inline_keyboard: [...extra, ...teclado(v)] } };
}
export const limpiarCache = () => CACHE.clear();
