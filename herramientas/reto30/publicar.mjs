// Publica los reels del Reto 30 Días SOLO en Instagram, en la pestaña Reels (NO salen en la cuadrícula), con su descripción,
// y sube la historia (imagen con "link en el perfil": la API no permite el sticker de enlace).
// Antes borra los reels del Reto que ya se habían publicado (los busca por #reto30dias).
// Antes: docker exec pixelia-estudio python3 /pixelia/herramientas/reto30/voz.py
// Uso:   docker exec pixelia node --no-warnings /app/herramientas/reto30/publicar.mjs [--sin-borrar] [--sin-historia] [masculina|femenina]
//        … femenina --facebook                    → sube ese reel SOLO a la página de Facebook
//        … masculina --reemplazar --sin-historia  → cambia SOLO ese reel (borra el anterior de esa voz y sube el nuevo)
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../../src/config.js';
import { Products, AdJobs } from '../../src/db.js';
import { igReel, igHistoria, igRecientes, igBorrar, fbVideo } from '../../src/telegram/redes.js';
import { marcarPublicado } from '../../src/telegram/calendario.js';

const SLUG = 'regalo-reto-30-dias', A = process.argv.slice(2);
const REG = path.join(path.dirname(config.paths.files), '..', 'data', 'reto30-publicados.json');   // ids de lo publicado (para reemplazar uno solo)
const reg = (() => { try { return JSON.parse(fs.readFileSync(REG, 'utf8')); } catch { return {}; } })();
const guardarReg = () => fs.writeFileSync(REG, JSON.stringify(reg, null, 1));
const p = Products.bySlug(SLUG); if (!p) throw new Error('Falta el regalo: corre herramientas/regalos.mjs');
const dir = path.join(path.dirname(config.paths.files), 'anuncios', SLUG);
const base = config.baseUrl.replace(/\/$/, '');
const g = JSON.parse(fs.readFileSync(path.join(dir, 'guion.json'), 'utf8'));
const generos = A.filter((x) => ['masculina', 'femenina'].includes(x)); if (!generos.length) generos.push('masculina', 'femenina');

// --facebook: SOLO sube el/los reel(s) a la página de Facebook (no toca Instagram)
if (A.includes('--facebook')) {
  for (const genero of generos) {
    const file = `reel-reto30-${genero}.mp4`;
    if (!fs.existsSync(path.join(dir, file))) { console.log(`⚠️ No encuentro ${file}`); continue; }
    try { const r = await fbVideo(`${base}/media/anuncios/${SLUG}/${file}`, g.story.copy.texto); console.log(`✔ Reel ${genero} subido a la página de Facebook. id: ${r?.id}`); }
    catch (e) { console.log(`❌ Facebook (${genero}): ${e.message}`); }
  }
  process.exit(0);
}
// 1a) --reemplazar: borra SOLO el reel de esa voz (si tenemos su id guardado) y sube el nuevo
if (A.includes('--reemplazar')) {
  for (const genero of generos) {
    if (!reg[genero]) { console.log(`⚠️ No tengo guardado cuál es el reel ${genero}: bórralo a mano desde la app (tres puntos → Eliminar).`); continue; }
    try { await igBorrar(reg[genero]); console.log(`🗑️ Borré el reel ${genero} anterior.`); delete reg[genero]; guardarReg(); }
    catch (e) { console.log(`⚠️ No pude borrar el reel ${genero} (${e.message}). Bórralo a mano desde la app.`); }
  }
}
// 1b) Borrar todos los reels del Reto que ya estaban publicados
if (!A.includes('--sin-borrar') && !A.includes('--reemplazar')) {
  const viejos = (await igRecientes(30)).filter((m) => /#reto30dias/i.test(m.caption || '') && m.media_product_type !== 'STORY');
  for (const m of viejos) {
    try { await igBorrar(m.id); console.log('🗑️ Borré el reel anterior:', m.permalink || m.id); }
    catch (e) { console.log(`⚠️ No pude borrar ${m.permalink || m.id} (${e.message}). Bórralo a mano desde la app: tres puntos → Eliminar.`); }
  }
  if (!viejos.length) console.log('ℹ️ No había reels anteriores del Reto publicados.');
}

// 2) Publicar los reels nuevos (solo pestaña Reels)
for (const genero of generos) {
  const file = `reel-reto30-${genero}.mp4`;
  if (!fs.existsSync(path.join(dir, file))) { console.log(`⚠️ No encuentro ${file}: corre primero voz.py`); continue; }
  console.log(`⏳ Subiendo el reel con voz ${genero} (solo Reels, sin cuadrícula). Puede tardar hasta 5 minutos…`);
  try {
    const res = await igReel(`${base}/media/anuncios/${SLUG}/${file}`, g.story.copy.texto,
      { feed: false, cover: fs.existsSync(path.join(dir, 'portada-reel.jpg')) ? `${base}/media/anuncios/${SLUG}/portada-reel.jpg` : '' });
    console.log(`✔ Reel ${genero} publicado. id: ${res?.id}`); if (res?.id) { reg[genero] = res.id; guardarReg(); }
  } catch (e) { console.log(`❌ Reel ${genero}: ${e.message}`); }
}
const ult = AdJobs.last(p.id); if (ult) marcarPublicado(p.id, ult.id);   // que el calendario automático no lo vuelva a subir

// 3) Historia
if (!A.includes('--sin-historia')) {
  try { const h = await igHistoria(`${base}/regalos/reto-30-dias-historia-perfil.jpg`); console.log('✔ Historia publicada. id:', h?.id); }
  catch (e) { console.log('❌ Historia:', e.message); }
}
console.log('Listo. Recuerda: agregar la historia a tu destacada "Regalo" desde la app (la API no deja hacerlo).');
