// 🧠 Aprendizaje: guarda la "receta" de cada anuncio (formato, gancho, texto, público) y cuánto costó cada visita.
// Con eso arma un resumen que usan los guiones nuevos (estudio/brief.py) y los textos de campaña (radar.planCampana).
// También escribe la LECCIÓN DEL LUNES: un consejo para Diego (negocio) + una publicación de consejo para Instagram,
// según la fecha, lo que se vive en Latinoamérica y los datos reales de la tienda.
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../config.js';
import { Products, Subscribers, Orders } from '../db.js';
import { askClaude } from './explorador.js';

export const DATA = path.join(path.dirname(config.paths.files), '..', 'data');
export const ANUNCIOS = path.join(path.dirname(config.paths.files), 'anuncios');
const F = path.join(DATA, 'aprendizaje.json'), RES = path.join(DATA, 'aprendizaje-resumen.json');
const leer = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };
const guardar = (f, x) => { fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, JSON.stringify(x, null, 1)); };

/** Receta de un reel: 'ultimo' = guion.json; 'anterior' = el reel anterior del historial. */
export function recetaDe(slug, cual = 'ultimo') {
  const dir = path.join(ANUNCIOS, slug);
  if (cual === 'ultimo') {
    const s = leer(path.join(dir, 'guion.json'), {}).story || {};
    const esc = s.escenas || [];
    return { formato: s.formato || '', concepto: s.concepto || '', estilo: s.estilo || '', gancho: (esc.find((e) => e.voz)?.voz || '').slice(0, 140) };
  }
  const h = leer(path.join(dir, 'historial.json'), []); const x = h[h.length - 2] || {};
  return { formato: x.formato || '', concepto: x.concepto || '', estilo: '', gancho: String((x.frases || []).find(Boolean) || '').slice(0, 140) };
}
/** Recetas de las variantes A/B al crear la campaña (se guardan en la campaña). */
export function recetasVariantes(p, variantes) {
  return variantes.map((v, k) => ({
    ...(v.tipo === 'imagen' ? { formato: 'imagen', concepto: '', estilo: '', gancho: '' } : recetaDe(p.slug, k === 0 ? 'ultimo' : 'anterior')),
    tipo: v.tipo, texto1: String(v.texto || '').split('\n')[0].slice(0, 140), titular: v.titulo || '' }));
}

/** Guarda los resultados de 7 días de cada anuncio de una campaña (se llama desde el reporte). */
export function registrar(c, ads) {
  const db = leer(F, { resultados: [] });
  for (const x of ads) {
    const k = (c.ads || []).findIndex((a) => a.id === x.id); if (k < 0) continue;
    const p = Products.byId(c.pid) || {};
    const fila = { ad: x.id, camp: c.camp, fecha: new Date().toISOString().slice(0, 10), pid: c.pid, producto: c.titulo, categoria: p.category || '',
      gratis: !p.price_cents, remarketing: !!c.remarketing, letra: c.ads[k].letra, receta: (c.recetas || [])[k] || {}, publico: c.publico || {},
      gasto: x.gasto, visitas: x.visitas, clics: x.clics, impresiones: x.vistas };
    const i = db.resultados.findIndex((r) => r.ad === x.id);
    if (i >= 0) { const o = db.resultados[i]; if (x.gasto >= o.gasto) db.resultados[i] = { ...fila, gasto: Math.max(x.gasto, o.gasto) }; }  // ventana de 7 días: se queda con lo más completo
    else db.resultados.push(fila);
  }
  db.resultados = db.resultados.slice(-300);
  guardar(F, db);
}

const cpv = (g, v) => (v ? g / v : Infinity);
/** Resume lo aprendido (solo anuncios con datos suficientes) y lo deja en data/aprendizaje-resumen.json para el estudio. */
export function resumen() {
  const rs = leer(F, { resultados: [] }).resultados.filter((r) => r.impresiones >= 300 && r.gasto > 0);
  if (!rs.length) { guardar(RES, { texto: '', formatos_ganadores: [], n: 0, fecha: new Date().toISOString() }); return { texto: '', n: 0 }; }
  const por = (key) => {
    const m = {};
    for (const r of rs) { const k = key(r); if (!k) continue; (m[k] ||= { g: 0, v: 0, n: 0 }); m[k].g += r.gasto; m[k].v += r.visitas; m[k].n++; }
    return Object.entries(m).map(([k, x]) => ({ k, c: cpv(x.g, x.v), n: x.n })).sort((a, b) => a.c - b.c);
  };
  const fmts = por((r) => r.receta.formato), tipos = por((r) => r.receta.tipo);
  const top = [...rs].sort((a, b) => cpv(a.gasto, a.visitas) - cpv(b.gasto, b.visitas));
  const din = (c) => (c === Infinity ? 'sin visitas' : `$${c.toFixed(2)} por visita`);
  const ganchos = top.filter((r) => r.receta.gancho || r.receta.texto1).slice(0, 3).map((r) => `"${r.receta.gancho || r.receta.texto1}" (${r.producto}, ${din(cpv(r.gasto, r.visitas))})`);
  const peores = top.slice(-2).filter((r) => top.length > 3).map((r) => `"${r.receta.gancho || r.receta.texto1}" (${din(cpv(r.gasto, r.visitas))})`);
  const intereses = [...new Set(top.slice(0, 3).flatMap((r) => r.publico?.intereses || []))].slice(0, 8);
  const texto = [
    `Datos reales de ${rs.length} anuncios de Pixelia en Meta (costo por visita a la página; más bajo = mejor).`,
    fmts.length ? `Formatos de reel, del mejor al peor: ${fmts.map((x) => `${x.k} (${din(x.c)}, ${x.n} anuncios)`).join('; ')}.` : '',
    tipos.length > 1 ? `Video vs imagen: ${tipos.map((x) => `${x.k} ${din(x.c)}`).join(' / ')}.` : '',
    ganchos.length ? `Ganchos/textos que mejor funcionaron: ${ganchos.join('; ')}.` : '',
    peores.length ? `Los que peor funcionaron (evita ese estilo): ${peores.join('; ')}.` : '',
    intereses.length ? `Intereses de los mejores públicos: ${intereses.join(', ')}.` : '',
  ].filter(Boolean).join('\n');
  const mejor = fmts.find((x) => x.k !== 'imagen')?.c ?? Infinity;  // solo los que de verdad ganaron (hasta 30% más caros que el mejor)
  const ganadores = fmts.filter((x) => x.k !== 'imagen' && x.c !== Infinity && x.c <= mejor * 1.3).slice(0, 2).map((x) => x.k);
  guardar(RES, { texto, formatos_ganadores: ganadores, n: rs.length, fecha: new Date().toISOString() });
  return { texto, n: rs.length };
}
export const resumenTexto = () => leer(RES, {}).texto || '';

// ===== 📅 Fechas que se viven en Latinoamérica (para entrar en contexto con tiempo) =====
const nth = (y, m, wd, n) => { const d = new Date(Date.UTC(y, m, 1)); let c = 0; for (;;) { if (d.getUTCDay() === wd && ++c === n) return new Date(d); d.setUTCDate(d.getUTCDate() + 1); } };
export function fechasProximas(hoy = new Date(), dias = 60) {
  const y = hoy.getUTCFullYear(), out = [];
  for (const yy of [y, y + 1]) {
    const bf = nth(yy, 10, 4, 4); bf.setUTCDate(bf.getUTCDate() + 1);
    const cm = new Date(bf); cm.setUTCDate(cm.getUTCDate() + 3);
    const fijas = [[0, 1, 'Año Nuevo y propósitos (hábitos, metas, ahorro)'], [0, 6, 'Día de Reyes'], [1, 14, 'San Valentín / Día del Amor y la Amistad'], [2, 8, 'Día de la Mujer'],
      [4, 10, 'Día de la Madre en México'], [9, 31, 'Halloween'], [10, 2, 'Día de Muertos'], [11, 24, 'Nochebuena'], [11, 25, 'Navidad'], [11, 31, 'Fin de año']];
    for (const [m, d, t] of fijas) out.push([new Date(Date.UTC(yy, m, d)), t]);
    out.push([bf, 'Black Friday'], [cm, 'Cyber Monday'], [nth(yy, 4, 0, 2), 'Día de la Madre (Colombia, Venezuela, Perú, Ecuador, Chile, EE. UU.)'],
      [nth(yy, 5, 0, 3), 'Día del Padre (casi toda Latinoamérica)'], [new Date(Date.UTC(yy, 0, 15)), 'Cuesta de enero (todos cuidan el dinero)'],
      [new Date(Date.UTC(yy, 1, 20)), 'Regreso a clases en Chile, Argentina y Perú (fines de feb–marzo)'], [new Date(Date.UTC(yy, 7, 20)), 'Regreso a clases en México (agosto)'],
      [new Date(Date.UTC(yy, 8, 15)), 'Regreso a clases en Venezuela y Colombia (septiembre)']);
  }
  const t0 = Date.UTC(y, hoy.getUTCMonth(), hoy.getUTCDate());
  return out.map(([d, t]) => ({ d, t, en: Math.round((d - t0) / 86400e3) })).filter((x) => x.en >= 0 && x.en <= dias).sort((a, b) => a.en - b.en)
    .map((x) => `${x.d.toISOString().slice(0, 10)} (${x.en === 0 ? 'hoy' : `en ${x.en} días`}): ${x.t}`);
}

/** Lección del lunes: 1 llamada a Claude con hasta 3 búsquedas web (≈ unos centavos por semana). */
export async function leccionSemanal(extra = {}) {
  const hoy = new Date();
  const perf = Products.performance(30).filter((p) => !p.bundle_ids).slice(0, 12).map((p) => ({ titulo: p.title, slug: p.slug, precio: p.price_cents / 100, visitas_30d: p.views, intentos: p.checkouts, ventas_30d: p.sales }));
  const regalos = Products.list({ all: true }).filter((p) => p.category === 'Regalo').map((p) => ({ titulo: p.title, slug: p.slug, precio: 0 }));
  const subs = Subscribers.list(5000), sem = subs.filter((s) => Date.parse(s.created_at + 'Z') > Date.now() - 7 * 86400e3).length;
  const pagadas = Orders.recent(500).filter((o) => o.status === 'paid' && Date.parse((o.paid_at || o.created_at) + 'Z') > Date.now() - 7 * 86400e3).length;
  const prompt = `Eres el estratega de marketing de Pixelia, una tienda de productos digitales (planners, plantillas de Excel/Google Sheets, imprimibles) que vende en Latinoamérica en español neutro. El dueño, Diego, NO es técnico: háblale simple, cercano y concreto.
HOY es ${hoy.toISOString().slice(0, 10)} (${['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'][hoy.getUTCDay()]}).
Fechas que vienen (hay que prepararse con 2-6 semanas de anticipación): ${JSON.stringify(fechasProximas(hoy))}.
Datos reales de la tienda: productos (30 días) ${JSON.stringify(perf)}; regalos gratis ${JSON.stringify(regalos)}; correos nuevos esta semana ${sem} (total ${subs.length}); ventas esta semana ${pagadas}.
${extra.campanas ? `Campañas activas esta semana: ${extra.campanas}` : 'Todavía no hay campañas activas con datos.'}
${resumenTexto() ? `Lo que ya aprendimos de los anuncios:\n${resumenTexto()}` : ''}
${extra.horarios ? `Cuándo se mueve nuestra gente (ya calculado, menciónalo en la lección si es útil): ${extra.horarios}` : ''}
Busca en internet (máx. 3 búsquedas) qué se está viviendo AHORA en Latinoamérica que afecte lo que compra la gente (temporada, fechas, tendencias de esta semana en redes sobre organización, ahorro, hábitos, fiestas) y qué tipo de anuncios/publicaciones está funcionando en este nicho.
Devuelve SOLO JSON:
{"leccion":{"titulo":"≤ 60 caracteres","texto":"≤ 650 caracteres: qué está pasando, qué aprendimos con NUESTROS datos (si hay) y por qué importa ahora","acciones":["2-3 acciones concretas para ESTA semana, cada una ≤ 110 caracteres, usando los comandos del bot cuando aplique (/anuncios, /gemini, /remarketing, /publicos)"]},
 "post":{"titular":"consejo para Instagram ≤ 48 caracteres, SIN emojis, que haga parar el scroll y esté ligado a la fecha o temporada","puntos":["3 consejos cortos y útiles, ≤ 70 caracteres cada uno, SIN emojis"],"cierre":"≤ 45 caracteres, SIN emojis, invita a guardar o compartir","caption":"texto de la publicación (≤ 900 caracteres): gancho con emoji, el consejo explicado en 3 viñetas con emoji, una mención natural (no vendedora) de UN producto o regalo nuestro que ayude con eso y 'link en la bio', y 5-7 hashtags en español","producto_slug":"slug del producto o regalo mencionado o null"}}
Reglas: español neutro (nada de modismos de un solo país), cero urgencia falsa, cero promesas exageradas, solo fechas reales.`;
  const { data } = await askClaude(prompt);
  if (!data?.leccion || !data?.post) throw new Error('la IA no devolvió la lección');
  return data;
}
