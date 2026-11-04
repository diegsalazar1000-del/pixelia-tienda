// Productos de ejemplo para ver la tienda funcionando. Bórralos u ocúltalos desde /admin.
import fs from 'node:fs';
import path from 'node:path';
import { config } from './config.js';
import { Products } from './db.js';

const demo = [
  { title: 'Pack 365 Plantillas Canva para Instagram', short: 'Posts, stories y carruseles editables para todo el año.', category: 'Plantillas', price: 9.99, compare: 19.99, emoji: '🎨', color: '#ff4fd8', featured: 1 },
  { title: 'Planner Digital 2027 para Notion', short: 'Organiza metas, hábitos y finanzas en un solo lugar.', category: 'Productividad', price: 7.99, compare: 14.99, emoji: '🗓️', color: '#22d3ee', featured: 1 },
  { title: 'Guía: Gana Dinero con IA desde Cero', short: 'Ebook paso a paso con 25 ideas de negocio con IA.', category: 'Ebooks', price: 12.99, compare: 24.99, emoji: '🤖', color: '#7c5cff', featured: 1 },
  { title: '1.000 Prompts para ChatGPT y Claude', short: 'Prompts listos para marketing, ventas, estudio y contenido.', category: 'IA', price: 5.99, compare: 0, emoji: '💬', color: '#34d399' },
  { title: 'Presets Lightroom Estética Cálida', short: '20 presets para móvil y escritorio, tono cinematográfico.', category: 'Fotografía', price: 6.99, compare: 12.99, emoji: '📸', color: '#fb923c' },
  { title: 'Plantilla Excel de Finanzas Personales', short: 'Presupuesto, deudas y ahorro con gráficos automáticos.', category: 'Productividad', price: 4.99, compare: 0, emoji: '💰', color: '#facc15' },
];

const sample = 'ejemplo-producto.txt';
fs.writeFileSync(path.join(config.paths.files, sample), 'Archivo de ejemplo. Sustitúyelo por tu producto real desde /admin.\n');

for (const d of demo) {
  const slug = d.title.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  if (Products.bySlug(slug)) continue;
  Products.upsert({ slug, title: d.title, short: d.short, category: d.category, emoji: d.emoji, color: d.color, featured: d.featured || 0,
    description: `${d.short}\n\nQué incluye:\n• Archivos listos para usar\n• Instrucciones paso a paso\n• Acceso de por vida a la descarga\n\n(Producto de ejemplo: edítalo en /admin.)`,
    price_cents: Math.round(d.price * 100), compare_cents: Math.round(d.compare * 100), stars: Math.ceil(d.price / 0.013),
    file_name: sample, license_type: 'PLR', license_note: 'DEMO' });
}
console.log('Productos de ejemplo listos:', Products.list().length);
