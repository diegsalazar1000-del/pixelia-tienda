// Corrige títulos, textos, categoría y precio tachado del Panel Financiero y la Lotería (sin entrar al admin).
// Uso en el servidor: docker exec pixelia node /app/herramientas/textos-productos.mjs
import { Products } from '../src/db.js';

const CAMBIOS = [
  { slug: 'plantilla-excel-de-finanzas-personales', emoji: '📊', category: 'Finanzas', compare_cents: 999,
    title: 'Panel Financiero Mensual: Excel y Google Sheets',
    short: 'Controla gastos, ingresos, facturas y ahorro en un solo panel que se calcula solo.',
    description: `• Panel con gráficos automáticos: en qué se te va el dinero
• Gastos e ingresos del mes por categoría
• Facturas con aviso de vencidas y calendario de pagos
• Metas de ahorro y hábitos financieros
• Archivo en blanco + uno de EJEMPLO para ver cómo funciona
• Guía de uso paso a paso (PDF)
Funciona en Excel y Google Sheets. Descarga inmediata.`,
    en: { title: 'Monthly Money Dashboard: Excel & Google Sheets',
      short: 'Track expenses, income, bills and savings in one dashboard that calculates itself.',
      description: `• Dashboard with automatic charts: see where your money goes
• Monthly expenses and income by category
• Bills with overdue alerts and a payment calendar
• Savings goals and money habits
• Blank file + an EXAMPLE file to see how it works
• Step-by-step user guide (PDF)
Works in Excel and Google Sheets (Spanish interface). Instant download.` } },
  { slug: 'loteria-de-baby-shower-imprimible-60-tablas-unicas', category: 'Fiestas y eventos', compare_cents: 999,
    short: 'El clásico juego de lotería con ilustraciones de bebé para que tu baby shower sea inolvidable.',
    description: `• 60 tablas DIFERENTES, una por invitada
• Escribe el nombre del bebé una vez y sale en todas las tablas
• 54 cartas ilustradas para recortar
• 54 versos divertidos para cantar cada carta
• Instrucciones, formas de ganar e ideas de premios
• Cartel "¡LOTERÍA!" y 72 fichas para marcar
PDF listo para imprimir en tamaño Carta. Descarga inmediata.`,
    en: { title: 'Printable Baby Shower Lotería: 60 Unique Boards',
      short: 'The classic Mexican lotería game with baby illustrations to make your baby shower unforgettable.',
      description: `• 60 DIFFERENT boards, one per guest
• Type the baby's name once and it appears on every board
• 54 illustrated cards to cut out
• 54 fun verses to call out each card (in Spanish)
• Instructions, ways to win and prize ideas
• "¡LOTERÍA!" winner sign and 72 markers
Print-ready PDF, Letter size. Instant download.` } },
];

for (const c of CAMBIOS) {
  const p = Products.bySlug(c.slug);
  if (!p) { console.log(`✖ No encontré ${c.slug}`); continue; }
  const { en, ...campos } = c;
  let i18n = {}; try { i18n = JSON.parse(p.i18n || '{}'); } catch {}
  i18n.en = en;
  Products.upsert({ id: p.id, ...campos, i18n: JSON.stringify(i18n) });
  console.log(`✔ ${Products.byId(p.id).title}`);
}
