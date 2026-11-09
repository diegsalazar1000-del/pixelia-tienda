// ✉️ Secuencia automática para quien dejó su correo (regalo o cupón), sin gastar en anuncios ni en IA:
//   día 2-3 → un consejo útil del tema que le interesa (ahorro, fin de año/organización o hábitos) + mención suave de un producto
//   día 6-7 → el producto que más le sirve (o el que estaba viendo) con su cupón si no lo usó y opiniones reales si hay
// Siempre con enlace para darse de baja (/baja). Nada de urgencia falsa.
import { config } from './config.js';
import { db, Products, Reviews, Orders } from './db.js';
import { sendEmail } from './delivery/email.js';
import { makeToken, readToken } from './resenas.js';

for (const sql of ['ALTER TABLE subscribers ADD COLUMN seq_step INTEGER DEFAULT 0', 'ALTER TABLE subscribers ADD COLUMN unsub INTEGER DEFAULT 0']) { try { db.exec(sql); } catch {} }
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const base = () => config.baseUrl.replace(/\/$/, '');
export const bajaLink = (email) => `${base()}/baja?t=${makeToken({ k: 'b', e: email })}`;
export function darDeBaja(t) {
  const tok = readToken(t); if (tok?.k !== 'b' || !tok.e) return false;
  db.prepare('UPDATE subscribers SET unsub = 1 WHERE email = ?').run(String(tok.e).toLowerCase()); return true;
}

const tema = (s) => (/regalo:.*\bjefa\b/.test(s.source) ? 'jefa' : /ahorro/.test(s.source) ? 'ahorro' : /navidad/.test(s.source) ? 'navidad' : /regalo:.*\breto\b/.test(s.source) ? 'habitos' : 'general');
const PREF = { jefa: /jefa|emprend/i, ahorro: /financ|ahorro|dinero|presupuesto|gasto/i, navidad: /2027|planner|agenda|hábito|habito|año/i, habitos: /hábito|habito/i, general: /hábito|habito|planner|2027|financ/i };

/** Producto que más le sirve: el que estaba viendo (cupón desde una ficha) → el de su tema → el más vendido. Nunca uno que ya compró. */
function recomendar(s) {
  const compro = new Set(Orders.recent(3000).filter((o) => o.status === 'paid' && String(o.email || '').toLowerCase() === s.email).map((o) => o.product_id));
  const ps = Products.list().filter((p) => p.price_cents > 0 && !p.bundle_ids && (p.file_name || p.external_url) && !compro.has(p.id));
  return ps.find((p) => p.slug === s.source) || ps.find((p) => PREF[tema(s)].test(`${p.title} ${p.category} ${p.short}`)) || ps[0] || null;
}

const CONSEJOS = {
  jefa: { asunto: '💡 Jefa: 3 errores que te hacen perder plata sin darte cuenta', titulo: '3 errores que se comen tu ganancia',
    puntos: ['<b>No cobrar tu tiempo:</b> si una torta te lleva 3 horas, esas horas valen. Si no las cuentas, estás trabajando gratis.',
      '<b>Olvidar los "pequeños" gastos:</b> el gas, la cajita, la bolsa, el pasaje. Sumados, a veces son toda tu ganancia.',
      '<b>Fiar sin anotar:</b> lo que no se anota, no se cobra. Anota quién te debe y cuánto el mismo día.'] },
  ahorro: { asunto: '💡 3 trucos para no abandonar tu reto de ahorro en marzo', titulo: '3 trucos para que tu ahorro sí llegue a diciembre',
    puntos: ['<b>Ahorra primero, gasta después:</b> aparta el monto de la semana el mismo día que cobras (quincena o fin de mes), no lo que sobre.',
      '<b>Si una semana te cuesta, no la saltes:</b> pon aunque sea la mitad. La racha importa más que el monto.',
      '<b>Caza los gastos hormiga una semana:</b> anota cada café, envío o antojo. Casi siempre ahí está el dinero de tu reto.'] },
  navidad: { asunto: '💡 Cómo llegar a enero sin estrés (ni deudas)', titulo: 'Diciembre tranquilo, enero sin sustos',
    puntos: ['<b>Primero el presupuesto, después los regalos:</b> decide cuánto vas a gastar en total y repártelo por persona.',
      '<b>Divide diciembre en 4 semanas:</b> regalos la 1ª, comida y compras la 2ª, decoración la 3ª y la última solo para disfrutar.',
      '<b>Elige 3 propósitos pequeños para enero</b>, no 10. Tres que sí cumplas valen más que una lista que se queda en la libreta.'] },
  general: { asunto: '💡 3 hábitos pequeños que cambian tu mes', titulo: 'Pequeños hábitos, mes distinto',
    puntos: ['<b>Empieza ridículamente fácil:</b> 1 página, 5 minutos, 1 vaso de agua. Lo difícil es empezar, no el tamaño.',
      '<b>Pégalo a algo que ya haces:</b> "después del café, leo 10 minutos". Así no dependes de acordarte.',
      '<b>Márcalo cada día:</b> ver tu racha crecer es la mejor motivación (y no romperla dos días seguidos).'] },
};
CONSEJOS.habitos = { ...CONSEJOS.general, asunto: '🔥 3 trucos para no romper tu racha del Reto 30 Días', titulo: 'Que tu reto llegue al día 30' };

const pre = (t) => `<div style="display:none;max-height:0;overflow:hidden;opacity:0">${esc(t)}</div>`;  // vista previa en la bandeja (no repite el asunto)
const marco = (s, cuerpo, preview = '') => `${preview ? pre(preview) : ''}<div style="font-family:system-ui,sans-serif;max-width:540px;margin:auto;padding:26px;background:#0f0f1a;color:#eee;border-radius:16px;line-height:1.55">${cuerpo}
  <p style="color:#8a87a6;font-size:12px;margin-top:26px;border-top:1px solid #2a2840;padding-top:12px">Recibes este correo porque ${/regalo/.test(s.source) ? 'descargaste un regalo' : 'pediste tu cupón'} en ${esc(config.storeName)}. ¿No quieres más correos? <a style="color:#b9a6ff" href="${bajaLink(s.email)}">Darme de baja</a>.</p></div>`;
const boton = (url, t) => `<p><a style="display:inline-block;background:#7c5cff;color:#fff;padding:12px 20px;border-radius:12px;text-decoration:none;font-weight:700" href="${url}">${t}</a></p>`;

function paso1(s) {
  const c = CONSEJOS[tema(s)], p = recomendar(s);
  const html = marco(s, `<h2 style="margin:0 0 12px">${c.titulo}</h2><ol style="padding-left:20px">${c.puntos.map((x) => `<li style="margin-bottom:10px">${x}</li>`).join('')}</ol>
    ${p ? `<p style="color:#cfcbe6">Y si quieres que todo se calcule solo, <a style="color:#b9a6ff" href="${base()}/p/${p.slug}">${esc(p.title)}</a> te lo deja listo en Excel o Google Sheets.</p>` : ''}
    <p style="color:#cfcbe6">¿Te sirvió? Respóndenos por Telegram y cuéntanos cómo vas 💜</p>`, 'Son 3 cambios pequeños. El segundo es el que más ayuda.');
  return { asunto: c.asunto, html, texto: c.puntos.map((x, i) => `${i + 1}. ${x.replace(/<[^>]+>/g, '')}`).join('\n') + `\n\nDarte de baja: ${bajaLink(s.email)}` };
}

function paso2(s) {
  const p = recomendar(s); if (!p) return null;
  if (Orders.recent(3000).some((o) => o.status === 'paid' && String(o.email || '').toLowerCase() === s.email && Date.parse((o.paid_at || o.created_at) + 'Z') > Date.now() - 5 * 86400e3)) return null;  // acaba de comprar: no venderle encima
  const rv = Reviews.summary(p.id) || {}, una = Reviews.approved(p.id, 5).find((r) => r.stars >= 4 && r.text);
  const lista = String(p.description || '').split('\n').filter((l) => l.trim().startsWith('•')).slice(0, 5);
  const precio = `$${(p.price_cents / 100).toFixed(2)}`, cupon = s.used_order ? null : s.code;
  const url = `${base()}/p/${p.slug}${cupon ? `?cupon=${encodeURIComponent(cupon)}` : ''}`;
  const html = marco(s, `<p style="color:#b9a6ff;margin:0">${s.source === p.slug ? 'El que estabas viendo' : 'Elegido para ti'}</p>
    <h2 style="margin:4px 0 8px">${esc(p.emoji || '')} ${esc(p.title)}</h2><p style="color:#cfcbe6">${esc(p.short || '')}</p>
    ${p.cover_url ? `<p><img src="${esc(p.cover_url)}" alt="" style="width:100%;border-radius:12px"></p>` : ''}
    ${lista.length ? `<ul style="padding-left:18px;color:#ddd">${lista.map((l) => `<li>${esc(l.replace(/^•\s*/, ''))}</li>`).join('')}</ul>` : ''}
    ${rv.n ? `<p>⭐ ${rv.avg}/5 de ${rv.n} opinión${rv.n > 1 ? 'es' : ''} real${rv.n > 1 ? 'es' : ''}${una ? `: <i>"${esc(String(una.text).slice(0, 160))}"</i>` : ''}</p>` : ''}
    <p style="font-size:18px"><b>${precio}</b> · descarga inmediata · funciona en el celular</p>
    ${cupon ? `<p>Tu cupón de bienvenida sigue disponible: <b style="background:#7c5cff;padding:4px 10px;border-radius:8px;letter-spacing:1px">${esc(cupon)}</b> (15% en tu primera compra).</p>` : ''}
    ${boton(url, 'Ver ' + esc(p.title.split(':')[0]))}`, cupon ? 'Tu 15% de bienvenida sigue guardado para ti.' : String(p.short || '').slice(0, 90));
  return { asunto: `${p.emoji || '✨'} ${p.title.split(':')[0]}${cupon ? ' (con tu 15%)' : ''}`, html, texto: `${p.title}\n${p.short || ''}\n${precio}${cupon ? `\nCupón 15%: ${cupon}` : ''}\n${url}\n\nDarte de baja: ${bajaLink(s.email)}` };
}

export async function enviarSecuencia() {
  if (!config.email.resendKey) return 0;
  let n = 0;
  const q1 = db.prepare(`SELECT * FROM subscribers WHERE COALESCE(seq_step,0)=0 AND COALESCE(unsub,0)=0 AND created_at < datetime('now','-2 days') AND created_at > datetime('now','-10 days') LIMIT 40`).all();
  for (const s of q1) {
    db.prepare('UPDATE subscribers SET seq_step = 1 WHERE email = ?').run(s.email);
    const m = paso1(s); await sendEmail(s.email, m.asunto, m.texto, m.html).then(() => n++).catch((e) => console.error('[correos]', e.message));
  }
  const q2 = db.prepare(`SELECT * FROM subscribers WHERE seq_step=1 AND COALESCE(unsub,0)=0 AND created_at < datetime('now','-6 days') AND created_at > datetime('now','-20 days') LIMIT 40`).all();
  for (const s of q2) {
    db.prepare('UPDATE subscribers SET seq_step = 2 WHERE email = ?').run(s.email);
    const m = paso2(s); if (!m) continue;
    await sendEmail(s.email, m.asunto, m.texto, m.html).then(() => n++).catch((e) => console.error('[correos]', e.message));
  }
  return n;
}
export function startSecuencia() { setTimeout(() => enviarSecuencia().catch(() => {}), 120e3); setInterval(() => enviarSecuencia().catch(() => {}), 3600e3); }
export const _test = { paso1, paso2, recomendar };
