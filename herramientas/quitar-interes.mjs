// Quita de una campaña los intereses que Meta asignó mal (ej. "Películas de comedia" en La Jefa). Sirve para cualquier campaña.
// Uso: docker exec pixelia node --no-warnings /app/herramientas/quitar-interes.mjs <id de campaña> "<palabra del interés>"
import '../src/config.js';   // carga el .env (claves de Meta)
import { api } from '../src/telegram/anuncios-meta.js';
const [camp, palabra] = process.argv.slice(2);
if (!camp || !palabra) { console.log('Uso: quitar-interes.mjs <id campaña> "<palabra>"'); process.exit(1); }
const re = new RegExp(palabra, 'i');
const sets = (await api('GET', `${camp}/adsets`, { fields: 'id,name,targeting', limit: 50 })).data || [];
for (const s of sets) {
  const t = s.targeting || {}; let quitados = [];
  for (const f of t.flexible_spec || []) if (f.interests) { quitados.push(...f.interests.filter((i) => re.test(i.name)).map((i) => i.name)); f.interests = f.interests.filter((i) => !re.test(i.name)); }
  if (!quitados.length) { console.log(`· ${s.name}: no tenía "${palabra}"`); continue; }
  await api('POST', s.id, { targeting: t });
  console.log(`✔ ${s.name}: quité ${quitados.join(', ')}`);
}
