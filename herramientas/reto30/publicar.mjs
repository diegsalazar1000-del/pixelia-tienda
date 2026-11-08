// Publica el reel del Reto 30 Días SOLO en Instagram, en la pestaña Reels (NO sale en la cuadrícula de publicaciones),
// con su descripción. Lo marca como publicado para que el calendario automático no lo vuelva a subir.
// Antes: docker exec pixelia-estudio python3 /pixelia/herramientas/reto30/voz.py
// Uso:   docker exec pixelia node --no-warnings /app/herramientas/reto30/publicar.mjs
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../../src/config.js';
import { Products, AdJobs } from '../../src/db.js';
import { igReel } from '../../src/telegram/redes.js';
import { marcarPublicado } from '../../src/telegram/calendario.js';

const SLUG = 'regalo-reto-30-dias';
const p = Products.bySlug(SLUG); if (!p) throw new Error('Falta el regalo: corre herramientas/regalos.mjs');
const j = AdJobs.last(p.id); const r = JSON.parse(j?.result || '{}');
if (!r.reel) throw new Error('Todavía no hay reel: corre primero voz.py en el estudio');
const dir = path.join(path.dirname(config.paths.files), 'anuncios', SLUG);
const g = JSON.parse(fs.readFileSync(path.join(dir, 'guion.json'), 'utf8'));
const base = config.baseUrl.replace(/\/$/, '') + `/media/anuncios/${SLUG}/`;
const url = base + encodeURIComponent(r.reel), cover = fs.existsSync(path.join(dir, 'portada-reel.jpg')) ? base + 'portada-reel.jpg' : '';
console.log('⏳ Subiendo a Instagram (solo Reels, sin cuadrícula). Puede tardar hasta 5 minutos…');
const res = await igReel(url, g.story.copy.texto, { feed: false, cover });
marcarPublicado(p.id, j.id);
console.log('✔ Publicado en Instagram (pestaña Reels). id:', res?.id);
