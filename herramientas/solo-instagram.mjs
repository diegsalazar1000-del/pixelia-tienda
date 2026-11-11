// Deja una campaña SOLO en Instagram (feed, historias, reels, explorar, perfil). Quita Facebook, Messenger y Audience Network.
// Uso: docker exec pixelia node --no-warnings /app/herramientas/solo-instagram.mjs <id de campaña>
import '../src/config.js';   // carga el .env (claves de Meta)
import { api } from '../src/telegram/anuncios-meta.js';
const [camp] = process.argv.slice(2);
if (!camp) { console.log('Uso: solo-instagram.mjs <id campaña>'); process.exit(1); }
const sets = (await api('GET', `${camp}/adsets`, { fields: 'id,name,targeting', limit: 50 })).data || [];
for (const s of sets) {
  const t = s.targeting || {};
  t.publisher_platforms = ['instagram'];
  t.instagram_positions = ['stream', 'story', 'reels', 'explore', 'explore_home', 'profile_feed'];
  delete t.facebook_positions; delete t.messenger_positions; delete t.audience_network_positions;
  await api('POST', s.id, { targeting: t });
  console.log(`✔ ${s.name}: ahora solo Instagram`);
}
