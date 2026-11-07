// 💬 Comentarios de Instagram y Facebook (cada 5 min, sin gastar Claude):
// - SOLO en publicaciones del REGALO (texto con /regalo o #regalo; decisión de Diego): quien comenta la palabra recibe respuesta pública con el link.
//   En las demás publicaciones no se responde solo: se le avisa a Diego.
// - Spam, estafas, enlaces raros e insultos se OCULTAN (no se borran) y se avisa a Diego con botones Eliminar / Mostrar.
// - Preguntas y demás comentarios: aviso a Diego para que responda él.
// Necesita en el token: instagram_manage_comments, pages_manage_engagement, pages_read_user_content.
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../config.js';
import { call, G, redesListas } from './redes.js';

const STATE = path.join(path.dirname(config.paths.db || 'data/tienda.db'), 'comentarios.json');
const env = (k) => process.env[k] || '';
let say = async () => {}, kb = async () => {};
const load = () => { try { return JSON.parse(fs.readFileSync(STATE, 'utf8')); } catch { return { seen: [], avisado: 0, start: Date.now() } } };
const save = (s) => { s.seen = s.seen.slice(-5000); fs.writeFileSync(STATE, JSON.stringify(s)); };

const SPAM = /(https?:\/\/|www\.|\.com\b|\.net\b|t\.me\/|wa\.me|bit\.ly|gana(r)?\s+dinero|ingresos?\s+extra|inversi[oó]n|bitcoin|cripto|forex|trading|escr[ií]beme|cont[aá]ctame|m[aá]ndame\s+(un\s+)?(dm|mensaje)|dm\s+me|check\s+(my|mi)\s+(bio|perfil)|seguidores\s+gratis|promociona|colaboraci[oó]n\s+pagada|sugar\s+(daddy|mommy)|onlyfans|xxx)/i;
const INSULTO = /\b(idiota|est[uú]pid[oa]s?|imb[eé]cil|pendej[oa]s?|marica|malparid[oa]|hijueputa|hdp|put[oa]s?|mierda|basura|cag[oó]n|gonorrea|culer[oa]|maldit[oa]s?)\b/i;
const PALABRA = /\b(regalo|regalos|ahorro|navidad|navide[nñ]o|quiero|lo quiero|yo quiero|gratis|me interesa|info|precio|cu[aá]nto (cuesta|vale|sale)|link|enlace|c[oó]mo lo (consigo|descargo|compro))\b/i;
const RESP_REGALO = [
  '¡Hecho! 🎁 Lo descargas gratis en el link de nuestra bio: pixeliadigital.app/regalo',
  '¡Es tuyo! 💜 Entra a pixeliadigital.app/regalo (también está en la bio) y descárgalo gratis.',
  '¡Claro que sí! ✨ Está gratis en pixeliadigital.app/regalo — el link también está en la bio.',
  '¡Te lo dejamos listo! 🎁 Búscalo en el link de la bio o directo en pixeliadigital.app/regalo',
];
const RESP_PRECIO = [
  '¡Hola! 💜 Todos los precios y la descarga inmediata están en pixeliadigital.app (link en la bio).',
  '¡Gracias por escribir! ✨ Lo encuentras en pixeliadigital.app — pagas con PayPal, tarjeta o Binance y lo descargas al momento.',
];
const esRegalo = (t) => /\/regalo|#regalo\b/i.test(String(t || ''));  // publicación del regalo gratis
const pick = (a) => a[Math.floor(Math.random() * a.length)];
const short = (t) => String(t || '').replace(/\s+/g, ' ').slice(0, 220);

async function igComments() {
  const ig = env('META_IG_ID'); if (!ig) return [];
  const media = (await call('GET', `${G}/${ig}/media`, { fields: 'id,permalink,caption', limit: '15' })).data || [];
  const out = [];
  for (const m of media) {
    const cs = (await call('GET', `${G}/${m.id}/comments`, { fields: 'id,text,username,timestamp,hidden', limit: '50' }).catch(() => ({ data: [] }))).data || [];
    for (const c of cs) out.push({ red: 'i', id: c.id, text: c.text, user: c.username, ts: c.timestamp, link: m.permalink, post: short(m.caption).slice(0, 40), hidden: c.hidden, regalo: esRegalo(m.caption) });
  }
  return out;
}
async function fbComments() {
  const page = env('META_PAGE_ID');
  const posts = (await call('GET', `${G}/${page}/posts`, { fields: 'id,permalink_url,message', limit: '15' })).data || [];
  const out = [];
  for (const p of posts) {
    const cs = (await call('GET', `${G}/${p.id}/comments`, { fields: 'id,message,from,created_time,is_hidden', filter: 'stream', limit: '50' }).catch(() => ({ data: [] }))).data || [];
    for (const c of cs) if (c.from?.id !== page) out.push({ red: 'f', id: c.id, text: c.message, user: c.from?.name || 'alguien', ts: c.created_time, link: p.permalink_url, post: short(p.message).slice(0, 40), hidden: c.is_hidden, regalo: esRegalo(p.message) });
  }
  return out;
}

const reply = (c, message) => c.red === 'i' ? call('POST', `${G}/${c.id}/replies`, { message }) : call('POST', `${G}/${c.id}/comments`, { message });
export const ocultar = (red, id, h = true) => red === 'i' ? call('POST', `${G}/${id}`, { hide: String(h) }) : call('POST', `${G}/${id}`, { is_hidden: String(h) });
export const eliminar = (red, id) => call('DELETE', `${G}/${id}`);

export async function revisarComentarios() {
  if (!redesListas()) return;
  const s = load(); const seen = new Set(s.seen);
  let all = [];
  try { all = [...await igComments(), ...await fbComments()]; } catch (e) {
    if ([10, 200, 190].includes(e.code) || /permission|permiso/i.test(e.message)) {
      if (Date.now() - (s.avisado || 0) > 3 * 86400e3) { s.avisado = Date.now(); save(s);
        await say('💬 Los comentarios automáticos están listos, pero el token de Meta aún no tiene los permisos de comentarios.\nCuando puedas: genera un token nuevo con <code>instagram_manage_comments</code>, <code>pages_manage_engagement</code> y <code>pages_read_user_content</code> (además de los de antes) y corre <code>bash configurar.sh redes</code>.'); }
      return;
    }
    console.error('[comentarios]', e.message); return;
  }
  const primeraVez = !s.seen.length;  // la primera vez solo marca lo viejo como visto
  let respuestas = 0;
  for (const c of all.sort((a, b) => String(a.ts).localeCompare(String(b.ts)))) {
    if (seen.has(c.id)) continue;
    seen.add(c.id); s.seen.push(c.id);
    if (primeraVez || c.hidden) continue;
    const red = c.red === 'i' ? '📸 Instagram' : '📘 Facebook', who = `<b>${esc(c.user)}</b>`;
    try {
      if (SPAM.test(c.text) || INSULTO.test(c.text)) {
        await ocultar(c.red, c.id);
        await kb(`🛡️ ${red} · Oculté un comentario de ${who} (${SPAM.test(c.text) ? 'spam/enlace' : 'insulto'}):\n«${esc(short(c.text))}»`,
          [[{ text: '🗑️ Eliminar', callback_data: `cm:d:${c.red}:${c.id}` }, { text: '👁️ Volver a mostrar', callback_data: `cm:s:${c.red}:${c.id}` }]]);
      } else if (c.regalo && PALABRA.test(c.text) && respuestas < 20) {
        const precio = /precio|cu[aá]nto|info|compr/i.test(c.text) && !/regalo|gratis|ahorro|navidad/i.test(c.text);
        await reply(c, pick(precio ? RESP_PRECIO : RESP_REGALO)); respuestas++;
        await say(`💬 ${red} · Respondí a ${who}: «${esc(short(c.text))}»`);
      } else {
        await kb(`💬 ${red} · Comentario de ${who} en «${esc(c.post)}…»:\n«${esc(short(c.text))}»${c.text?.includes('?') ? '\n❓ Parece una pregunta: respóndele tú.' : ''}`, c.link ? [[{ text: '↗️ Abrir y responder', url: c.link }]] : []);
      }
    } catch (e) { console.error('[comentarios]', c.id, e.message); }
  }
  save(s);
}
const esc = (t) => String(t ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export function startComentarios(sayFn, kbFn) {
  say = sayFn; kb = kbFn;
  const run = () => revisarComentarios().catch((e) => console.error('[comentarios]', e.message));
  setTimeout(run, 90e3); setInterval(run, 5 * 60e3);
}
