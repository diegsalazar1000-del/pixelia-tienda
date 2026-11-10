// 📅 Plan de contenido 10-22 nov (Diego): historias diarias + feed (mar/jue esta semana, lun/mié/vie la siguiente).
// El servidor publica SOLO si plan.json tiene "aprobado": true. Feed 6:00 pm (IG + FB), historias 9:00 am solo si "historias_auto": true
// (la API no pone el sticker de enlace: si Diego quiere el enlace tocable, las sube él desde el teléfono).
// Manual:  docker exec pixelia node --no-warnings /app/herramientas/semana/publicar.mjs estado
//          docker exec pixelia node --no-warnings /app/herramientas/semana/publicar.mjs ahora <AAAA-MM-DD> feed|historia
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../../src/config.js';
import { igFoto, igHistoria, fbFoto, redesListas } from '../../src/telegram/redes.js';

const PLAN = new URL('./plan.json', import.meta.url);
const REG = path.join(path.dirname(config.paths.files), '..', 'data', 'semana-publicados.json');
const plan = () => JSON.parse(fs.readFileSync(PLAN, 'utf8'));
const reg = () => { try { return JSON.parse(fs.readFileSync(REG, 'utf8')); } catch { return {}; } };
const anotar = (k, v) => { const r = reg(); r[k] = v; fs.mkdirSync(path.dirname(REG), { recursive: true }); fs.writeFileSync(REG, JSON.stringify(r, null, 1)); };
const ccs = () => { const d = new Date(Date.now() - 4 * 3600e3); return { dia: d.toISOString().slice(0, 10), hora: d.getUTCHours() }; };
const url = (f) => `${config.baseUrl.replace(/\/$/, '')}/img/semana/${f}`;

export async function publicar(dia, tipo) {
  const p = plan(), k = `${dia}-${tipo}`;
  if (reg()[k]) return `ya estaba (${reg()[k].id})`;
  if (tipo === 'feed') {
    const f = p.feed[dia]; if (!f) return 'no hay feed ese día';
    const r = await igFoto(url(f.img), f.texto); await fbFoto(url(f.img), f.texto).catch((e) => console.error('[semana fb]', e.message));
    anotar(k, { id: r?.id, fecha: new Date().toISOString() }); return `feed publicado (${r?.id})`;
  }
  const h = p.historias[dia]; if (!h) return 'no hay historia ese día';
  const r = await igHistoria(url(h)); anotar(k, { id: r?.id, fecha: new Date().toISOString() }); return `historia publicada (${r?.id})`;
}

let ocupado = false;
async function revisar() {
  if (ocupado) return; ocupado = true;
  try {
    const p = plan(); if (!p.aprobado || !redesListas()) return;
    const { dia, hora } = ccs();
    if (p.historias_auto && hora >= 9 && p.historias[dia]) console.log('[semana]', await publicar(dia, 'historia'));
    if (hora >= 18 && p.feed[dia]) console.log('[semana]', await publicar(dia, 'feed'));
  } catch (e) { console.error('[semana]', e.message); } finally { ocupado = false; }
}
export function startSemana() { setTimeout(revisar, 60_000); setInterval(revisar, 10 * 60_000); }

if (process.argv[1] && process.argv[1].endsWith('publicar.mjs')) {
  const [cmd, dia, tipo] = process.argv.slice(2);
  if (cmd === 'ahora' && dia && tipo) console.log(await publicar(dia, tipo));
  else { const p = plan(), r = reg(); console.log(`aprobado: ${p.aprobado} · historias automáticas: ${p.historias_auto}`);
    for (const d of Object.keys(p.historias)) console.log(d, '📱', r[`${d}-historia`] ? '✅' : '·', p.feed[d] ? `🖼️ ${r[`${d}-feed`] ? '✅' : '·'}` : ''); }
}
