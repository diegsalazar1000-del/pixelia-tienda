// Publica una parte de la serie "Cumple tus metas" en Instagram (Reels + cuadrícula del perfil, para que el perfil se vea con contenido).
// Antes: docker exec pixelia-estudio python3 /pixelia/herramientas/serie/reel.py <n> masculina
// Uso:   docker exec pixelia node --no-warnings /app/herramientas/serie/publicar.mjs <n> [masculina|femenina] [--solo-reels]
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../../src/config.js';
import { igReel } from '../../src/telegram/redes.js';

const A = process.argv.slice(2);
const n = Number(A.find((x) => /^\d$/.test(x)) || 1);
const genero = A.find((x) => ['masculina', 'femenina'].includes(x)) || 'masculina';
const serie = JSON.parse(fs.readFileSync(new URL('./serie.json', import.meta.url), 'utf8'));
const P = serie.partes.find((p) => p.n === n); if (!P) throw new Error(`No existe la parte ${n}`);
const dir = path.join(path.dirname(config.paths.files), 'anuncios', 'serie-metas');
const file = `parte${n}-${genero}.mp4`;
if (!fs.existsSync(path.join(dir, file))) { console.log(`❌ No encuentro ${file}: créalo antes con reel.py ${n} ${genero}`); process.exit(1); }
const base = config.baseUrl.replace(/\/$/, '');
const cover = fs.existsSync(path.join(dir, `parte${n}-portada.jpg`)) ? `${base}/media/anuncios/serie-metas/parte${n}-portada.jpg` : '';
const REG = path.join(path.dirname(config.paths.files), '..', 'data', 'serie-publicados.json');
const reg = (() => { try { return JSON.parse(fs.readFileSync(REG, 'utf8')); } catch { return {}; } })();
if (reg[n] && !A.includes('--otra-vez')) { console.log(`⚠️ La parte ${n} ya se publicó (id ${reg[n].id}). Si de verdad quieres subirla otra vez: --otra-vez`); process.exit(0); }

console.log(`Subiendo la parte ${n} (${genero})… tarda 1-2 minutos`);
const r = await igReel(`${base}/media/anuncios/serie-metas/${file}`, P.copy, { feed: !A.includes('--solo-reels'), cover });
reg[n] = { id: r?.id, genero, fecha: new Date().toISOString() }; fs.writeFileSync(REG, JSON.stringify(reg, null, 1));
console.log(`✔ Parte ${n} publicada en Instagram. id: ${r?.id}`);
