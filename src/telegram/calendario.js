// 📅 Calendario de publicaciones automático en Instagram + Facebook (sin que Diego toque nada):
//   1er día del plan → tarjeta con el CONSEJO de la semana (sale de la lección del lunes; la imagen la dibuja el estudio)
//   2º y 3er día     → un reel que aún no se haya publicado (rota productos y regalos)
// Días y horas los decide horarios.js con lo que aprende (al inicio: lunes, miércoles y viernes 6 pm).
// 3 horas antes llega un aviso con ❌ No publicar / ✅ Publicar ya. Si no toca nada, se publica solo. /calendario on|off.
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../config.js';
import { Products } from '../db.js';
import { redesListas, igFoto, fbFoto, igReel, fbVideo } from './redes.js';
import { DATA, ANUNCIOS, leccionSemanal } from './aprendizaje.js';
import { planSemana, actualizarHorarios, fmtSlot } from './horarios.js';

const F = path.join(DATA, 'calendario.json'), PEND = path.join(DATA, 'ig-pendientes'), IMG = path.join(ANUNCIOS, 'ig-posts');
const esc = (s) => String(s ?? '').replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const leer = () => { try { return { activo: true, dias: {}, publicados: {}, ...JSON.parse(fs.readFileSync(F, 'utf8')) }; } catch { return { activo: true, dias: {}, publicados: {} }; } };
const guardar = (s) => { fs.mkdirSync(DATA, { recursive: true }); const ks = Object.keys(s.dias).sort().slice(-40); s.dias = Object.fromEntries(ks.map((k) => [k, s.dias[k]])); fs.writeFileSync(F, JSON.stringify(s, null, 1)); };
// Todo en hora de Caracas (UTC-4, sin horario de verano)
const local = (d = new Date()) => new Date(d.getTime() - 4 * 3600e3);
const hoyCcs = (d = new Date()) => local(d).toISOString().slice(0, 10);
const avisoDe = (hora) => Math.max(7, hora - 3);
const hh = (h) => `${h % 12 || 12} ${h < 12 ? 'am' : 'pm'}`;
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
      try { e.ig = (await igFoto(url, e.caption))?.id; res.push('Instagram ✅'); } catch (x) { res.push(`Instagram ❌ ${esc(x.message)}`); }
      try { await fbFoto(url, e.caption); res.push('Facebook ✅'); } catch (x) { res.push(`Facebook ❌ ${esc(x.message)}`); }
    } else {
      const x = D.ultimoReel(e.pid);
      if (!x?.exists) throw new Error('ya no encuentro ese reel');
      try { e.ig = (await igReel(x.url, x.caption))?.id; res.push('Instagram ✅'); } catch (y) { res.push(`Instagram ❌ ${esc(y.message)}`); }
      try { await fbVideo(x.url, x.caption); res.push('Facebook ✅'); } catch (y) { res.push(`Facebook ❌ ${esc(y.message)}`); }
      marcarPublicado(e.pid, x.job.id);
    }
  } catch (x) { res.push(`❌ ${esc(x.message)}`); }
  const ok = res.some((r) => r.includes('✅')), s2 = leer();
  s2.dias[dia] = { ...s2.dias[dia], estado: ok ? 'publicado' : 'error' };
  if (ok) (s2.posts ||= []).push({ ig: e.ig || null, tipo: e.tipo, fecha: new Date().toISOString() }), s2.posts = s2.posts.slice(-80);  // para aprender a qué hora funciona mejor
  guardar(s2);
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
  const s0 = leer();
  const H = await actualizarHorarios({ posts: s0.posts || [], campanas: extra.campIds || [] }).catch((e) => ({ plan: planSemana(), texto: '', error: e.message }));
  const L = await leccionSemanal({ ...extra, horarios: H.texto });
  const l = L.leccion;
  await D.send(`🎓 <b>Lección de la semana · ${esc(l.titulo)}</b>\n\n${esc(l.texto)}\n\n<b>Esta semana:</b>\n${(l.acciones || []).map((a) => `✅ ${esc(a)}`).join('\n')}${H.texto ? `\n\n⏰ <b>Horarios</b>: ${esc(H.texto)}` : ''}`);
  // el consejo sale en el primer día del plan que todavía no pasó (con al menos 2 horas de margen)
  const ahora = local(), slot = H.plan.find((x) => x.tipo === 'consejo') || H.plan[0];
  let dia = null, hora = slot.hora;
  for (let k = 0; k < 8 && !dia; k++) {
    const d = new Date(ahora.getTime() + k * 86400e3);
    if (d.getUTCDay() !== slot.dow) continue;
    if (k === 0 && ahora.getUTCHours() + 2 > hora) { if (ahora.getUTCHours() + 2 <= 21) hora = ahora.getUTCHours() + 2; else continue; }
    dia = d.toISOString().slice(0, 10);
  }
  const s = leer(); s.semana = H.plan;
  s.dias[dia] = { tipo: 'consejo', hora, caption: L.post.caption, post: L.post, estado: s.activo ? 'pendiente' : 'manual' }; guardar(s);
  const ok = await tarjeta(dia, L.post);
  if (!ok) return D.send('⚠️ El estudio no dibujó la tarjeta del consejo (¿está encendido <code>pixelia-estudio</code>?). No se publicará hasta que esté.');
  const cuando = `${dia === hoyCcs() ? 'hoy' : fmtSlot({ dow: new Date(dia + 'T12:00:00Z').getUTCDay(), hora }).split(' ')[0]} a las ${hh(hora)}`;
  return D.rtg('sendPhoto', { chat_id: config.telegram.adminChatId, photo: `${base()}/media/anuncios/ig-posts/${dia}.jpg?v=${Date.now()}`, parse_mode: 'HTML',
    caption: `📲 <b>Consejo para Instagram y Facebook</b> · ${s.activo ? `se publica solo ${cuando}` : 'calendario apagado: tócalo para publicar'}\n\n${esc(L.post.caption).slice(0, 850)}`,
    reply_markup: s.activo ? botones(dia) : { inline_keyboard: [[{ text: '✅ Publicar ahora', callback_data: `cal:${dia}:ya` }]] } });
}

async function tick() {
  if (!redesListas()) return;
  const ahora = local(), h = ahora.getUTCHours(), wd = ahora.getUTCDay(), dia = hoyCcs(), s = leer();
  if (!s.activo) return;
  const slot = (s.semana || planSemana()).find((x) => x.dow === wd);
  if (slot?.tipo === 'reel' && !s.dias[dia] && h >= avisoDe(slot.hora) && h < slot.hora) {
    const x = elegirReel(s);
    if (!x) { s.dias[dia] = { tipo: 'reel', estado: 'sin' }; guardar(s);
      return D.send('📅 Hoy tocaba publicar un reel, pero ya publiqué todos los que hay. Crea uno nuevo con /anuncios (o manda un clip de Gemini) y en la próxima fecha sale solo.'); }
    s.dias[dia] = { tipo: 'reel', pid: x.p.id, job: x.job.id, titulo: x.p.title, hora: slot.hora, estado: 'pendiente' }; guardar(s);
    return D.rtg('sendMessage', { chat_id: config.telegram.adminChatId, parse_mode: 'HTML', disable_web_page_preview: true,
      text: `📅 <b>Hoy a las ${hh(slot.hora)}</b> publico en Instagram y Facebook el reel de <b>${esc(x.p.title)}</b>:\n${esc(x.url)}\n\n${esc(x.caption)}`, reply_markup: botones(dia) });
  }
  const e = s.dias[dia];
  if (e?.estado === 'pendiente' && h >= (e.hora ?? 18)) return publicar(dia);
}

export async function onCalendario(dia, accion, say) {
  const s = leer();
  if (dia === 'on' || dia === 'off') { s.activo = dia === 'on'; guardar(s); return say(s.activo ? `🟢 Calendario <b>encendido</b>: ${(s.semana || planSemana()).map((x) => `${fmtSlot(x)} ${x.tipo}`).join(', ')} (con aviso 3 horas antes).` : '⚪ Calendario <b>apagado</b>: no publico nada solo.'); }
  const e = s.dias[dia]; if (!e) return say('No encontré esa publicación.');
  if (accion === 'no') { e.estado = 'cancelado'; guardar(s); return say('👌 Listo, esa no se publica.'); }
  if (accion === 'ya') { if (e.estado === 'publicado') return say('Esa ya se publicó.'); e.estado = 'pendiente'; guardar(s); return publicar(dia); }
}

export function estadoCalendario() {
  const s = leer(), plan = s.semana || planSemana();
  const prox = Object.entries(s.dias).filter(([d]) => d >= hoyCcs()).map(([d, e]) => `• ${d}${e.hora != null ? ' ' + hh(e.hora) : ''}: ${e.tipo === 'consejo' ? 'consejo' : 'reel ' + esc(e.titulo || '')} — ${e.estado}`);
  const ult = Object.entries(s.dias).filter(([, e]) => e.estado === 'publicado').slice(-4).map(([d, e]) => `• ${d}: ${e.tipo === 'consejo' ? 'consejo' : 'reel ' + esc(e.titulo || '')}`);
  return `📅 <b>Calendario de publicaciones</b>: ${s.activo ? '🟢 encendido' : '⚪ apagado'}\nEsta semana: ${plan.map((x) => `${fmtSlot(x)} (${x.tipo})`).join(' · ')}. Los días y las horas se ajustan solos cada lunes según cuándo se mueve tu gente; avisa 3 horas antes para cancelar.\n\n${prox.length ? '<b>Próximas</b>\n' + prox.join('\n') + '\n\n' : ''}${ult.length ? '<b>Últimas publicadas</b>\n' + ult.join('\n') : ''}`;
}

export function startCalendario(deps) {
  D = deps;
  setInterval(() => tick().catch((e) => console.error('[calendario]', e.message)), 10 * 60e3);
  setTimeout(() => tick().catch(() => {}), 90e3);
}
export const _tick = () => tick();  // para pruebas
