// Registra el "Plan financiero 2027" (Excel + Google Sheets hecho con los números de cada persona) en la tienda.
// Se vende desde la landing /plan (pasos cortos); el estudio fabrica el Excel al pagar (herramientas/plan2027/build.py + fabrica.py).
// Uso: docker exec pixelia node --no-warnings /app/herramientas/plan2027.mjs [--publicar]
import { Products } from '../src/db.js';
import { config } from '../src/config.js';

const slug = 'plan-financiero-2027';
const old = Products.bySlug(slug);
const p = Products.upsert({ ...(old ? { id: old.id } : {}), slug, emoji: '📊', category: 'Finanzas', form: 'plan',
  title: 'Mi plan financiero 2027 (hecho con tus números)',
  gancho: 'Que el nuevo año no te agarre desprevenido',
  short: 'Pones a qué te dedicas, cuánto ganas, tus gastos y tu meta, y te llega tu plan de los 12 meses de 2027 en Excel y Google Sheets: cuánto gastar, cuánto ahorrar y en qué mes cumples tu meta.',
  description: `Respondes 4 preguntas cortas en la página y ves tu plan al instante. Al comprarlo te llega al correo TU archivo, ya hecho con tus números. ✨

Qué trae:
• 🏠 Inicio: lo que ganas, lo necesario, cuánto ahorrar, cuánto apartar para diciembre y cuánto queda para gustos
• 📅 12 pestañas (Ene a Dic) con el presupuesto de cada mes ya puesto: escribes lo real y el semáforo 🟢🟡🔴 te avisa
• 🎒 Fechas que siempre se olvidan: útiles de enero, regreso a clases, regalos y cena de diciembre
• 📈 Mi año: tu ahorro subiendo mes a mes, con gráfica
• 🎯 Tu meta: barra de avance y el mes en que la cumples

Funciona en Excel y en Google Sheets (también desde el teléfono). Pago único, sin suscripción.`,
  faq: JSON.stringify([
    { q: '¿Cómo lo recibo?', a: 'Apenas pagas, en unos minutos te llega al correo el enlace para descargar TU plan en Excel. Lo abres en Excel o lo subes a Google Drive y se abre con Hojas de cálculo.' },
    { q: '¿Y si mi ingreso cambia cada mes?', a: 'Si trabajas por tu cuenta te pedimos un mes normal y uno flojo: el plan usa el promedio y te dice que en los meses buenos guardes la diferencia.' },
    { q: '¿Puedo cambiar los números después?', a: 'Sí. Las celdas amarillas se cambian y todo se recalcula solo: el reparto, los 12 meses y la fecha de tu meta.' },
    { q: '¿Sirve en mi país?', a: 'Sí: eliges tu moneda y el plan sale con ella. Sirve en cualquier país.' }]),
  price_cents: 399, compare_cents: 0, cover_url: config.baseUrl + '/img/portada-plan-financiero-2027.jpg', external_url: '', file_name: '',
  license_type: 'Propio', license_note: 'Para uso personal.',
  active: process.argv.includes('--publicar') ? 1 : (old?.active ?? 0) });
console.log(`✔ ${p.emoji} ${p.title} · $${(p.price_cents / 100).toFixed(2)} · ${p.active ? 'PUBLICADO' : 'oculto (actívalo con --publicar)'} · formulario: ${p.form}`);
