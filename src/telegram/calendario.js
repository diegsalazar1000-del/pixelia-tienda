// 📅 Calendario de publicaciones automático en Instagram + Facebook (sin que Diego toque nada):
//   lunes 6 pm  → tarjeta con el CONSEJO de la semana (sale de la lección del lunes; la imagen la dibuja el estudio)
//   miércoles y viernes 6 pm → un reel que aún no se haya publicado (rota productos y regalos)
// A las 3 pm llega un aviso con ❌ No publicar / ✅ Publicar ya. Si no toca nada, se publica solo. /calendario on|off.
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../config.js';
import { Products } from '../db.js';
import { redesListas, igFoto, fbFoto, igReel, fbVideo } from './redes.js';
import { DATA, ANUNCIOS, leccionSemanal } from './aprendizaje.js';

const F = path.join(DATA, 'calendario.json'), PEND = path.join(DATA, 'ig-pendientes'), IMG = path.join(ANUNCIOS, 'ig-posts');
const esc = (s) => String(s ?? '').replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const leer = () => { try { return { activo: true, dias: {}, publicados: {}, ...JSON.parse(fs.readFileSync(F, 'utf8')) }; } catch { return { activo: true, dias: {}, publicados: {} }; } };
const guardar = (s) => { fs.mkdirSync(DATA, { recursive: true }); const ks = Object.keys(s.dias).sort().slice(-40); s.dias = Object.fromEntries(ks.map((k) => [k, s.dias[k]])); fs.writeFileSync(F, JSON.stringify(s, null, 1)); };
const HORA_AVISO = 19, HORA_PUBLICAR = 22;  // UTC = 3 pm y 6 pm en Caracas
const hoyUTC = (d = new Date()) => d.toISOString().slice(0, 10);
const base = () => config.baseUrl.replace(/\/$/, '');
let D = {};  // dependencias del bot del radar: { rtg, send, ultimoReel }

export const calendarioActivo = () => leer().activo;
export function marcarPublicado(pid, jobId) {
  const s = leer(); (s.publicados[pid] ||= []).push(Number(jobId)); s.publicados[pid] = s.publicados[pid].slice(-30);
  (s.fechas ||= {})[pid] = new Date().toISOString(); guardar(s);
}

/** El reel que toca: de un producto/regalo con reel que todavía no se haya publicado, el que hace más tiempo no sale. */
function elegirReel(s) {
  const ps = Products.list({ all: true }).filter((p) => (p.active || p.category === 'Regalo') && !p.bundle_ids);
  const c = ps.map((p) => D.ultimoReel(p.id)).filter((x) => x?.exists && !(s.publicados[x.p.id] || []).includes(Number(x.job.id)));
  c.sort((a, b) => String(s.fechas?.[a.p.id] || '').localeCompare(String(s.fechas?.[b.p.id] || '')));
  return c[0] || null;
}

const botones = (dia) => ({ inline_keyboard: [[{ text: '❌ No publicar', callback_data: `cal:${dia}:no` }, { text: '✅ Publicar ya', callback_data: `cal:${dia}:ya` }]] });

async function publicar(dia) {
  const s = leer(); const e = s.dias[dia]; if (!e || e.estado !== 'pendiente') return;
  e.estado = 'publicando'; guardar(s);
  const res = [];
  try {
    if (e.tipo === 'consejo') {
      const url = `${base()}/media/anuncios/ig-posts/${dia}.jpg`;
      if (!fs.existsSync(path.join(IMG, `${dia}.jpg`))) throw new Error('la imagen del consejo no está lista');
      try { await igFoto(url, e.caption); res.push('Instagram ✅'); } catch (x) { res.push(`Instagram ❌ ${esc(x.message)}`); }
      try { await fbFoto(url, e.caption); res.push('Facebook ✅'); } catch (x) { res.push(`Facebook ❌ ${esc(x.message)}`); }
    } else {
      const x = D.ultimoReel(e.pid);
      if (!x?.exists) throw new Error('ya no encuentro ese reel');
      try { await igReel(x.url, x.caption); res.push('Instagram ✅'); } catch (y) { res.push(`Instagram ❌ ${esc(y.message)}`); }
      try { await fbVideo(x.url, x.caption); res.push('Facebook ✅'); } catch (y) { res.push(`Facebook ❌ ${esc(y.message)}`); }
      marcarPublicado(e.pid, x.job.id);
    }
  } catch (x) { res.push(`❌ ${esc(x.message)}`); }
  const s2 = leer(); s2.dias[dia] = { ...s2.dias[dia], estado: res.some((r) => r.includes('✅')) ? 'publicado' : 'error' }; guardar(s2);
  await D.send(`📅 Publicación del día (${e.tipo === 'consejo' ? 'consejo' : 'reel de ' + esc(e.titulo || '')}): ${res.join(' · ')}`);
}

/** Pide al estudio la tarjeta del consejo y espera hasta ~6 min a que esté. */
async function tarjeta(dia, post) {
  fs.mkdirSync(PEND, { recursive: true });
  fs.writeFileSync(path.join(PEND, `${dia}.json`), JSON.stringify({ id: dia, titular: post.titular, puntos: post.puntos, cierre: post.cierre }));
  for (let i = 0; i < 36; i++) { if (fs.existsSync(path.join(IMG, `${dia}.jpg`))) return true; await new Promise((r) => setTimeout(r, 10e3)); }
  return false;
}

/** Lección de la semana: mensaje para Diego + publicación de consejo para Instagram (lunes, o cuando la pida con /leccion). */
export async function leccion(extra = {}) {
  const L = await leccionSemanal(extra);
  const l = L.leccion;
  await D.send(`🎓 <b>Lección de la semana · ${esc(l.titulo)}</b>\n\n${esc(l.texto)}\n\n<b>Esta semana:</b>\n${(l.acciones || []).map((a) => `✅ ${esc(a)}`).join('\n')}`);
  const ahora = new Date(); let dia = hoyUTC(ahora);
  if (ahora.getUTCHours() >= HORA_PUBLICAR) { const m = new Date(ahora); m.setUTCDate(m.getUTCDate() + 1); dia = hoyUTC(m); }
  const s = leer(); s.dias[dia] = { tipo: 'consejo', caption: L.post.caption, post: L.post, estado: s.activo ? 'pendiente' : 'manual' }; guardar(s);
  const ok = await tarjeta(dia, L.post);
  if (!ok) return D.send('⚠️ El estudio no dibujó la tarjeta del consejo (¿está encendido <code>pixelia-estudio</code>?). No se publicará hasta que esté.');
  const cuando = dia === hoyUTC(new Date(Date.now() - 4 * 3600e3)) ? 'hoy a las 6 pm' : 'mañana a las 6 pm';  // fecha de Caracas
  return D.rtg('sendPhoto', { chat_id: config.telegram.adminChatId, photo: `${base()}/media/anuncios/ig-posts/${dia}.jpg?v=${Date.now()}`, parse_mode: 'HTML',
    caption: `📲 <b>Consejo para Instagram y Facebook</b> · ${s.activo ? `se publica solo ${cuando}` : 'calendario apagado: tócalo para publicar'}\n\n${esc(L.post.caption).slice(0, 850)}`,
    reply_markup: s.activo ? botones(dia) : { inline_keyboard: [[{ text: '✅ Publicar ahora', callback_data: `cal:${dia}:ya` }]] } });
}

async function tick() {
  if (!redesListas()) return;
  const ahora = new Date(), h = ahora.getUTCHours(), wd = ahora.getUTCDay(), dia = hoyUTC(ahora), s = leer();
  if (!s.activo) return;
  if ((wd === 3 || wd === 5) && h >= HORA_AVISO && h < HORA_PUBLICAR && !s.dias[dia]) {
    const x = elegirReel(s);
    if (!x) { s.dias[dia] = { tipo: 'reel', estado: 'sin' }; guardar(s);
      return D.send('📅 Hoy tocaba publicar un reel, pero ya publiqué todos los que hay. Crea uno nuevo con /anuncios (o manda un clip de Gemini) y el viernes/miércoles sale solo.'); }
    s.dias[dia] = { tipo: 'reel', pid: x.p.id, job: x.job.id, titulo: x.p.title, estado: 'pendiente' }; guardar(s);
    return D.rtg('sendMessage', { chat_id: config.telegram.adminChatId, parse_mode: 'HTML', disable_web_page_preview: true,
      text: `📅 <b>Hoy a las 6 pm</b> publico en Instagram y Facebook el reel de <b>${esc(x.p.title)}</b>:\n${esc(x.url)}\n\n${esc(x.caption)}`, reply_markup: botones(dia) });
  }
  if (h >= HORA_PUBLICAR && s.dias[dia]?.estado === 'pendiente') return publicar(dia);
}

export async function onCalendario(dia, accion, say) {
  const s = leer();
  if (dia === 'on' || dia === 'off') { s.activo = dia === 'on'; guardar(s); return say(s.activo ? '🟢 Calendario <b>encendido</b>: lunes consejo, miércoles y viernes un reel (6 pm, con aviso a las 3 pm).' : '⚪ Calendario <b>apagado</b>: no publico nada solo.'); }
  const e = s.dias[dia]; if (!e) return say('No encontré esa publicación.');
  if (accion === 'no') { e.estado = 'cancelado'; guardar(s); return say('👌 Listo, esa no se publica.'); }
  if (accion === 'ya') { if (e.estado === 'publicado') return say('Esa ya se publicó.'); e.estado = 'pendiente'; guardar(s); return publicar(dia); }
}

export function estadoCalendario() {
  const s = leer();
  const prox = Object.entries(s.dias).filter(([d]) => d >= hoyUTC()).map(([d, e]) => `• ${d}: ${e.tipo === 'consejo' ? 'consejo' : 'reel ' + esc(e.titulo || '')} — ${e.estado}`);
  const ult = Object.entries(s.dias).filter(([, e]) => e.estado === 'publicado').slice(-4).map(([d, e]) => `• ${d}: ${e.tipo === 'consejo' ? 'consejo' : 'reel ' + esc(e.titulo || '')}`);
  return `📅 <b>Calendario de publicaciones</b>: ${s.activo ? '🟢 encendido' : '⚪ apagado'}\nLunes: consejo de la semana · Miércoles y viernes: un reel que no se haya publicado. Siempre a las 6 pm (Caracas), con aviso a las 3 pm para cancelar.\n\n${prox.length ? '<b>Próximas</b>\n' + prox.join('\n') + '\n\n' : ''}${ult.length ? '<b>Últimas publicadas</b>\n' + ult.join('\n') : ''}`;
}

export function startCalendario(deps) {
  D = deps;
  setInterval(() => tick().catch((e) => console.error('[calendario]', e.message)), 10 * 60e3);
  setTimeout(() => tick().catch(() => {}), 90e3);
}
export const _tick = () => tick();  // para pruebas
