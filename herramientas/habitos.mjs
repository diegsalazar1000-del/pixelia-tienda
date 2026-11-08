// Publica "Mi 2027 en Hábitos" (PLR rehecho en español) con su archivo, portada y textos ES/EN.
// Uso en el servidor: docker exec pixelia node --no-warnings /app/herramientas/habitos.mjs
// Licencia PLR/MRR del original: precio mínimo USD 3.86, NO se puede regalar, no mencionar a la creadora original.
import fs from 'node:fs';
import path from 'node:path';
import { Products } from '../src/db.js';
import { config } from '../src/config.js';

const FILE = 'Mi-2027-en-Habitos-Pixelia.zip';
fs.mkdirSync(config.paths.files, { recursive: true });
fs.copyFileSync(path.join(path.dirname(new URL(import.meta.url).pathname), 'archivos', FILE), path.join(config.paths.files, FILE));
const slug = 'mi-2027-en-habitos';
const old = Products.bySlug(slug);
const p = Products.upsert({ ...(old ? { id: old.id } : {}), slug, emoji: '✨', category: 'Hábitos y productividad',
  title: 'Mi 2027 en Hábitos: Tracker de Hábitos Excel y Google Sheets',
  gancho: 'Este año, tus propósitos no se mueren en febrero.',
  short: 'Todos empezamos enero con ganas… y para el 14 de febrero ya nadie se acuerda del gimnasio. Aquí solo marcas ✓ y la hoja te celebra, te regaña y te muestra tu racha creciendo sola.',
  description: `Seamos honestos: tu lista de propósitos de 2026 está en algún lado, abandonada, junto a la bicicleta estática que hoy es perchero. 🫠

No te faltó fuerza de voluntad. Te faltó ver tu avance. Cuando ves tu racha de 23 días seguidos, ya no la quieres romper ni por un pastelito.

Lo que recibes:
• 12 meses de 2027 listos: solo marcas ✓ cada día
• 🔥 Rachas que siguen aunque cambie el mes y 🚀 niveles según tu ritmo (de "Arrancando" a "Imparable")
• "¿Cómo voy?": te dice si vas bien o cuántos días te faltan, sin juzgarte (bueno, un poquito)
• Registro de ánimo diario con caritas 😊
• Resumen "Mi Año": mejor mes, racha récord, mapa de calor y en qué área de tu vida vas mejor
• Mis 3 metas grandes, reflexión del mes y "¿qué me hizo fallar?"
• Archivo en blanco + uno de EJEMPLO lleno + versión IMPRIMIBLE en PDF + guía rápida

Funciona en Excel y Google Sheets (gratis), también en el celular. Pagas una vez, es tuyo para siempre.`,
  gallery: JSON.stringify([
    { url: '/img/galeria/habitos-1-mes.jpg', cap: 'Cada mes: marcas ✓ y listo' },
    { url: '/img/galeria/habitos-2-como-voy.jpg', cap: '"¿Cómo voy?" te lo dice clarito' },
    { url: '/img/galeria/habitos-3-animo.jpg', cap: 'Tu reflexión de cada mes 📝' },
    { url: '/img/galeria/habitos-4-mi-ano.jpg', cap: 'Mi Año: tu récord y tu mapa de calor' },
    { url: '/img/galeria/habitos-6-imprimible.jpg', cap: 'Versión imprimible para la nevera' }]),
  video_url: '/video/habitos-demo.mp4',
  countdown: '2027-01-01', countdown_label: 'para el 2027. Empieza preparado.',
  sample_url: '', sample_title: '', // licencia PLR: NO se puede regalar ninguna parte (ni de muestra)
  faq: JSON.stringify([
    { q: '¿Necesito tener Excel?', a: 'No. Funciona perfecto en Google Sheets, que es gratis, y también desde el celular. Si tienes Excel, también va.' },
    { q: '¿Y si ya empezó el año cuando lo compre?', a: 'Empiezas el día que quieras. Las rachas y los niveles cuentan desde tu primer ✓.' },
    { q: '¿Puedo cambiar los hábitos?', a: 'Sí. Escribes los tuyos (hasta 7 por mes) y todo se recalcula solo.' }]),
  price_cents: 599, compare_cents: 0, cover_url: config.baseUrl + '/img/portada-habitos-2027.jpg', file_name: FILE,
  license_type: 'Propio', license_note: 'Para uso personal. No se permite revender ni compartir el archivo.', active: 1,
  i18n: JSON.stringify({ en: { title: 'My 2027 in Habits: Habit Tracker for Excel & Google Sheets',
    gancho: 'This year, your resolutions won\'t die in February.', countdown_label: 'until 2027. Start ready.',
    short: 'Tick ✓ each day and watch your streaks, level and progress calculate themselves. All 12 months of 2027 ready.',
    description: `• All 12 months of 2027 ready: just tick ✓ each day
• 🔥 Streaks that carry over between months and 🚀 levels based on your pace
• "How am I doing?": tells you if you're on track or how many days you need
• Daily mood tracker 😊
• "My Year" summary: best month, record streak, heat map and life areas
• My 3 big goals, monthly reflection and "what made me fail?"
• Blank file + filled EXAMPLE + PRINTABLE PDF + quick guide
Works in Excel and Google Sheets, also on your phone (Spanish interface). Instant download.` } }) });
console.log(`✔ ${p.emoji} ${p.title} · $${(p.price_cents / 100).toFixed(2)} · publicado`);
