// 💸 Gasto en Claude (API): cada llamada anota lo que consumió (la respuesta trae los tokens).
// Anthropic no deja consultar el saldo con la clave normal: el saldo es una ESTIMACIÓN = recargas anotadas − gasto desde la 1ª recarga.
import fs from 'node:fs';
import path from 'node:path';
import { config } from './config.js';

const DIR = path.dirname(config.paths.db);
const LOG = path.join(DIR, 'gasto-claude.jsonl');
const REC = path.join(DIR, 'gasto-recargas.json');
// Precios por millón de tokens (Sonnet 5.5) y por búsqueda web; se pueden cambiar en .env.
const P_IN = Number(process.env.PRECIO_IN || 2), P_OUT = Number(process.env.PRECIO_OUT || 10), P_WEB = Number(process.env.PRECIO_BUSQUEDA || 0.01);

/** Anota una respuesta de la API de Claude. `src` = para qué se usó (explorador, fusionar, plan…). */
export function registrarClaude(src, j) {
  try {
    const u = j?.usage; if (!u) return;
    const i = (u.input_tokens || 0) + (u.cache_creation_input_tokens || 0) * 1.25 + (u.cache_read_input_tokens || 0) * 0.1;
    const o = u.output_tokens || 0, w = u.server_tool_use?.web_search_requests || 0;
    const usd = i / 1e6 * P_IN + o / 1e6 * P_OUT + w * P_WEB;
    fs.appendFileSync(LOG, JSON.stringify({ t: new Date().toISOString(), s: src, i: Math.round(i), o, w, usd: +usd.toFixed(5) }) + '\n');
  } catch {}
}

const leer = () => { try { return fs.readFileSync(LOG, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l)); } catch { return []; } };
export const recargas = () => { try { return JSON.parse(fs.readFileSync(REC, 'utf8')); } catch { return []; } };
export function recargar(usd) { const r = recargas(); r.push({ t: new Date().toISOString(), usd: +usd }); fs.writeFileSync(REC, JSON.stringify(r)); return r; }

/** Resumen: gasto de hoy (hora de Caracas), 7 y 30 días, en qué se fue, y saldo estimado. */
export function resumenClaude() {
  const all = leer(), now = Date.now();
  const hoyCcs = new Date(now - 4 * 3600e3).toISOString().slice(0, 10);
  const dia = (x) => new Date(Date.parse(x.t) - 4 * 3600e3).toISOString().slice(0, 10);
  const sum = (a) => a.reduce((s, x) => s + x.usd, 0);
  const hoy = all.filter((x) => dia(x) === hoyCcs), d7 = all.filter((x) => now - Date.parse(x.t) < 7 * 864e5), d30 = all.filter((x) => now - Date.parse(x.t) < 30 * 864e5);
  const por = {}; for (const x of d7) por[x.s] = (por[x.s] || 0) + x.usd;
  const r = recargas(); let saldo = null;
  if (r.length) { const desde = r[0].t; saldo = sum(r) - sum(all.filter((x) => x.t >= desde)); }
  return { hoy: sum(hoy), llamadasHoy: hoy.length, d7: sum(d7), d30: sum(d30), por, saldo, desde: all[0]?.t || null, recargas: r };
}
