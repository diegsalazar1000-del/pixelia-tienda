// Quita Audience Network y Messenger de las campañas YA creadas (activas o en pausa) y da prioridad a Instagram.
// Las campañas nuevas ya salen así. Uso: docker exec pixelia node --no-warnings /app/herramientas/sin-audience-network.mjs
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../src/config.js';
import { aplicarUbicaciones } from '../src/telegram/anuncios-meta.js';

const F = path.join(path.dirname(config.paths.files), '..', 'data', 'campanas.json');
let cs = []; try { cs = JSON.parse(fs.readFileSync(F, 'utf8')); } catch {}
const vivas = cs.filter((c) => c.estado !== 'borrada' && c.camp);
if (!vivas.length) console.log('No hay campañas guardadas.');
for (const c of vivas) {
  try { const h = await aplicarUbicaciones(c); console.log(`✔ ${c.titulo || c.camp} (${c.estado}): ${h.length} conjunto(s) sin Audience Network, Instagram primero`); }
  catch (e) { console.log(`⚠️ ${c.titulo || c.camp}: ${e.message}`); }
}
