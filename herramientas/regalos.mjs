// Registra los regalos gratis como productos OCULTOS (precio 0, categoría "Regalo") para poder crearles anuncios en el bot.
// No salen en el catálogo: se descargan en /regalo dejando el correo.  Uso: docker exec pixelia node --no-warnings /app/herramientas/regalos.mjs
import fs from 'node:fs';
import path from 'node:path';
import { Products } from '../src/db.js';
import { config } from '../src/config.js';

const R = [
  { slug: 'regalo-reto-de-ahorro-52-semanas-2027', title: 'Reto de Ahorro 52 Semanas 2027', emoji: '🐷', file: 'Reto-de-Ahorro-52-Semanas-Pixelia.zip', cover: '/regalos/portada-reto-ahorro.jpg',
    short: 'Colorea cada semana que ahorras y llega a fin de año con tu meta cumplida. Gratis.',
    description: '• Tabla imprimible de 52 semanas: versión creciente y versión fija\n• Fechas de 2027 en cada casilla\n• Cuánto juntas multiplicando (x1, x2, x5, x10)\n• Versión Excel / Google Sheets que suma sola y muestra tu avance\nGratis a cambio de tu correo.' },
  { slug: 'regalo-reto-30-dias', title: 'Reto 30 Días', emoji: '🔥', file: 'Reto-30-Dias-Pixelia.xlsx', cover: '/regalos/reto-30-dias.jpg', link: '/reto',
    short: 'Si tus propósitos se mueren en febrero: marca ✓ cada día y tu racha, tu % y tu barra se calculan solos. Gratis.',
    description: '• 30 días y hasta 5 hábitos (los cambias por los tuyos)\n• Racha actual 🔥 y mejor racha 🏆 que se calculan solas\n• % cumplido de cada hábito y barra de avance del reto\n• Mensajes que cambian según vas (día 1, semana 1, mitad, ¡lo lograste!)\n• Funciona en Google Sheets (gratis, también en el celular) y Excel\nGratis a cambio de tu correo en pixeliadigital.app/reto' },
  { slug: 'regalo-planificador-navideno', title: 'Planificador Navideño', emoji: '🎄', file: 'Planificador-Navideno-Pixelia.zip', cover: '/regalos/portada-planificador-navideno.jpg',
    short: 'Presupuesto, lista de regalos, cenas y checklist de diciembre para una Navidad sin estrés. Gratis.',
    description: '• Presupuesto navideño por categorías (planeado vs real)\n• Lista de regalos: para quién, idea, presupuesto, comprado y envuelto\n• Menú, lista del súper y quién trae qué para Navidad y Año Nuevo\n• Checklist de diciembre semana a semana\n• Versión Excel / Google Sheets que suma sola\nGratis a cambio de tu correo.' },
];
fs.mkdirSync(config.paths.files, { recursive: true });
for (const r of R) {
  fs.copyFileSync(path.join(config.paths.public, 'regalos', r.file), path.join(config.paths.files, r.file));
  const old = Products.bySlug(r.slug);
  const p = Products.upsert({ ...(old ? { id: old.id } : {}), slug: r.slug, title: r.title, short: r.short, description: r.description, emoji: r.emoji,
    category: 'Regalo', price_cents: 0, compare_cents: 0, cover_url: config.baseUrl + r.cover, file_name: r.file, active: 0 });
  console.log(`✔ ${p.emoji} ${p.title} (oculto, para anuncios)`);
}
