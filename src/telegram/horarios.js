// ⏰ Horarios que aprenden: ¿qué días y a qué hora se mueve nuestra gente? (todo en hora de Caracas)
// Señales (se usan las que haya, con su peso):
//   1. La tienda: visitas a productos, correos dejados y pagos iniciados, por día y hora (tabla actividad_hora)   40%
//   2. Instagram: a qué hora están conectados los seguidores (online_followers; Meta lo da desde ~100 seguidores) 30%
//   3. Anuncios: clics por hora de las campañas (hora local de quien los vio ≈ Caracas − 1)                        20%
//   4. Nuestras publicaciones: alcance e interacciones de cada post según el día y la hora en que salió          10%
// Cada lunes arma el plan de la semana: 3 días (consejo + 2 reels) y la hora de cada uno (1 h antes del pico).
// Sin datos suficientes: lunes, miércoles y viernes a las 6 pm.
import fs from 'node:fs';
import path from 'node:path';
import { Actividad } from '../db.js';
import { G, call, redesListas } from './redes.js';
import { adsListos, horasAnuncios } from './anuncios-meta.js';
import { DATA } from './aprendizaje.js';

const F = path.join(DATA, 'horarios.json');
const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
export const PLAN_BASE = [{ dow: 1, hora: 18, tipo: 'consejo' }, { dow: 3, hora: 18, tipo: 'reel' }, { dow: 5, hora: 18, tipo: 'reel' }];
const leer = () => { try { return JSON.parse(fs.readFileSync(F, 'utf8')); } catch { return {}; } };
export const planSemana = () => leer().plan || PLAN_BASE;
export const textoHorarios = () => leer().texto || '';
const hh = (h) => `${h % 12 || 12} ${h < 12 ? 'am' : 'pm'}`;
export const fmtSlot = (x) => `${DIAS[x.dow]} ${hh(x.hora)}`;

const norm = (a) => { const m = Math.max(...a); return m > 0 ? a.map((x) => x / m) : a.map(() => 0); };
const suave = (a) => a.map((x, i) => 0.25 * a[(i + 23) % 24] + 0.5 * x + 0.25 * a[(i + 1) % 24]);  // ventana de 3 horas
const matriz = () => Array.from({ length: 7 }, () => Array(24).fill(0));

/** Hora de Caracas a partir de una fecha ISO. */
const caracas = (iso) => { const d = new Date(Date.parse(iso) - 4 * 3600e3); return { dow: d.getUTCDay(), hora: d.getUTCHours() }; };

async function seguidoresIG() {
  if (!redesListas() || !process.env.META_IG_ID) return null;
  const r = await call('GET', `${G}/${process.env.META_IG_ID}/insights`, { metric: 'online_followers', period: 'lifetime' }).catch(() => null);
  const vals = r?.data?.[0]?.values || []; if (!vals.length) return null;
  const m = matriz(); let total = 0;
  for (const v of vals) {
    const end = Date.parse(v.end_time || ''); if (!end || !v.value || !Object.keys(v.value).length) continue;
    // Meta da las horas en hora del Pacífico (del día anterior a end_time); se pasa cada hora a Caracas
    const dia = new Date(end - 86400e3), off = pacOffset(dia);
    for (const [h, n] of Object.entries(v.value)) {
      const utc = Date.UTC(dia.getUTCFullYear(), dia.getUTCMonth(), dia.getUTCDate(), Number(h)) - off * 3600e3;
      const c = new Date(utc - 4 * 3600e3); m[c.getUTCDay()][c.getUTCHours()] += Number(n) || 0; total += Number(n) || 0;
    }
  }
  return total ? m : null;
}
function pacOffset(d) {  // horas de diferencia del Pacífico con UTC ese día (−8 o −7)
  const s = new Intl.DateTimeFormat('en-US', { timeZone: 'America/Los_Angeles', timeZoneName: 'shortOffset' }).formatToParts(d).find((p) => p.type === 'timeZoneName')?.value || 'GMT-8';
  return Number(s.replace('GMT', '')) || -8;
}

/** Alcance e interacciones de lo que publicó el calendario (posts con id guardado). */
async function rendimientoPosts(posts) {
  const m = matriz(), c = matriz(); let n = 0;
  for (const p of posts.filter((x) => x.ig && Date.parse(x.fecha) < Date.now() - 48 * 3600e3).slice(-40)) {
    let r = await call('GET', `${G}/${p.ig}/insights`, { metric: 'reach,total_interactions' }).catch(() => null);
    let reach = 0, inter = 0;
    for (const d of r?.data || []) { const v = d.values?.[0]?.value || d.total_value?.value || 0; if (d.name === 'reach') reach = v; else inter = v; }
    if (!r) { const f = await call('GET', `${G}/${p.ig}`, { fields: 'like_count,comments_count' }).catch(() => null); if (!f) continue; inter = (f.like_count || 0) + (f.comments_count || 0); }
    const { dow, hora } = caracas(p.fecha); m[dow][hora] += reach + 10 * inter; c[dow][hora]++; n++;
  }
  if (n < 6) return null;  // con menos de 6 publicaciones es puro azar
  return m.map((row, d) => row.map((x, h) => (c[d][h] ? x / c[d][h] : 0)));
}

/** Recalcula el plan de la semana. posts = publicaciones del calendario con su id de Instagram. */
export async function actualizarHorarios({ posts = [], campanas = [] } = {}) {
  const act = Actividad.todas(), web = matriz(); let eventos = 0;
  for (const a of act) { const w = a.tipo === 'pago' ? 3 : a.tipo === 'correo' ? 2 : 1; web[a.dow][a.hora] += w * a.n; eventos += a.n; }
  const ig = await seguidoresIG().catch(() => null);
  const ads = adsListos() && campanas.length ? await horasAnuncios(campanas).catch(() => null) : null;
  const adsH = ads && ads.reduce((s, x) => s + x.clics, 0) >= 30 ? ads.map((_, h) => ads[(h + 23) % 24].clics) : null;  // su hora local ≈ Caracas − 1
  const pst = await rendimientoPosts(posts).catch(() => null);

  const señales = [];
  if (eventos >= 80) señales.push({ w: 0.4, m: web, n: 'la tienda' });
  if (ig) señales.push({ w: 0.3, m: ig, n: 'Instagram' });
  if (adsH) señales.push({ w: 0.2, m: Array.from({ length: 7 }, () => adsH), n: 'los anuncios' });
  if (pst) señales.push({ w: 0.1, m: pst, n: 'tus publicaciones' });
  if (!señales.length) {
    const d = { plan: PLAN_BASE, texto: `Todavía hay pocos datos para saber a qué hora se mueve tu gente (${eventos} visitas/acciones registradas). Publico lunes, miércoles y viernes a las 6 pm y lo ajusto solo cuando haya más.`, fecha: new Date().toISOString() };
    fs.mkdirSync(DATA, { recursive: true }); fs.writeFileSync(F, JSON.stringify(d, null, 1)); return d;
  }
  // puntaje por día y hora: cada señal mezcla su patrón del día (si tiene datos ese día) con el promedio de todos los días
  const W = señales.reduce((s, x) => s + x.w, 0), score = matriz();
  for (const s of señales) {
    const todas = suave(norm(Array.from({ length: 24 }, (_, h) => s.m.reduce((t, row) => t + row[h], 0))));
    for (let d = 0; d < 7; d++) {
      const tot = s.m[d].reduce((a, b) => a + b, 0), dia = tot ? suave(norm(s.m[d])) : todas;
      for (let h = 0; h < 24; h++) score[d][h] += (s.w / W) * (0.5 * dia[h] + 0.5 * todas[h]);
    }
  }
  // fuerza de cada día (solo si la tienda tiene bastantes datos para comparar días); si no, lunes/miércoles/viernes
  const fuerzaDia = web.map((row) => row.reduce((a, b) => a + b, 0));
  let dias = [1, 3, 5];
  if (eventos >= 300) {
    const orden = [0, 1, 2, 3, 4, 5, 6].sort((a, b) => fuerzaDia[b] - fuerzaDia[a]);
    dias = []; for (const d of orden) { if (dias.length < 3 && !dias.some((x) => Math.abs(x - d) === 1 || Math.abs(x - d) === 6)) dias.push(d); }  // sin días seguidos
    for (const d of orden) if (dias.length < 3 && !dias.includes(d)) dias.push(d);
    dias.sort((a, b) => ((a + 6) % 7) - ((b + 6) % 7));  // de lunes a domingo
  }
  const plan = dias.map((d, i) => {
    let pico = 18, best = -1;
    for (let h = 9; h <= 22; h++) if (score[d][h] > best) { best = score[d][h]; pico = h; }
    return { dow: d, hora: Math.max(8, pico - 1), pico, tipo: i === 0 ? 'consejo' : 'reel' };
  });
  const texto = `Según ${señales.map((s) => s.n).join(', ')}: ${eventos >= 300 ? 'los días con más movimiento son ' + plan.map((x) => DIAS[x.dow]).join(', ').replace(/, ([^,]*)$/, ' y $1') + ', y ' : ''}tu gente se conecta más ${plan.map((x) => `${DIAS[x.dow]} ~${hh(x.pico)}`).join(', ')}. Esta semana publico ${plan.map(fmtSlot).join(', ')} (1 hora antes del pico, para que Instagram la vaya repartiendo).`;
  const d = { plan, texto, señales: señales.map((s) => s.n), eventos, fecha: new Date().toISOString() };
  fs.mkdirSync(DATA, { recursive: true }); fs.writeFileSync(F, JSON.stringify(d, null, 1));
  return d;
}
