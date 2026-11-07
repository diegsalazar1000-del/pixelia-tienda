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
  short: 'Marca ✓ cada día y mira tus rachas, tu nivel y tu progreso calcularse solos. Los 12 meses de 2027 ya listos.',
  description: `• 12 meses de 2027 listos: solo marcas ✓ cada día
• 🔥 Rachas que siguen aunque cambie el mes y 🚀 niveles según tu ritmo
• "¿Cómo voy?": te dice si vas a buen ritmo o cuántos días te faltan
• Registro de ánimo diario con caritas 😊
• Resumen "Mi Año": mejor mes, racha récord, mapa de calor y en qué área de tu vida vas mejor
• Mis 3 metas grandes, reflexión del mes y "¿qué me hizo fallar?"
• Archivo en blanco + uno de EJEMPLO lleno + versión IMPRIMIBLE en PDF + guía rápida
Funciona en Excel y Google Sheets, también en el celular. Descarga inmediata.`,
  price_cents: 599, compare_cents: 0, cover_url: config.baseUrl + '/img/portada-habitos-2027.jpg', file_name: FILE,
  license_type: 'Propio', license_note: 'Para uso personal. No se permite revender ni compartir el archivo.', active: 1,
  i18n: JSON.stringify({ en: { title: 'My 2027 in Habits: Habit Tracker for Excel & Google Sheets',
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
