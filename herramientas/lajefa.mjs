// Registra "La Jefa" (app web para emprendedoras) en la tienda. Queda OCULTA (active 0) hasta que Diego la active en /admin
// o se corra con --publicar. La app vive en src/apps/jefa/ y se abre en /app/jefa/ solo con licencia (enlace del pedido pagado).
// Uso: docker exec pixelia node --no-warnings /app/herramientas/lajefa.mjs [--publicar]
import { Products } from '../src/db.js';
import { config } from '../src/config.js';

const slug = 'la-jefa';
const old = Products.bySlug(slug);
const p = Products.upsert({ ...(old ? { id: old.id } : {}), slug, emoji: '👑', category: 'Emprendedoras',
  title: 'La Jefa: la app de tu negocio desde casa',
  gancho: 'Jefa… ¿sabes cuánto ganas de verdad en cada venta?',
  short: 'Para la que vende postres, hace uñas, tiene su tiendita o cocina para vender. Te dice la verdad de tus precios, te ayuda a conseguir clientas y a cobrarle a quien te debe. Todo en tu teléfono.',
  description: `Trabajas todo el día, vendes bastante… y a fin de mes la plata no aparece. 😩
No es mala suerte: casi siempre es que pones el precio "a ojo" y no cuentas el gas, la cajita, el delivery ni TU tiempo.

La Jefa te lo dice clarito:
• 💰 ¿Cuánto ganas de verdad? Pones lo que te cuesta hacerlo y te suelta la verdad: "Pierdes $1,20 en cada torta 😱". Y te da tu PRECIO JUSTO.
• 📋 Tu lista de precios bonita, lista para mandar por WhatsApp o poner en tu estado.
• 💬 Mensajes para conseguir clientas: postres, uñas, tiendita, comida, costura… copias y envías.
• 💸 Quién te debe: anotas, y le mandas un recordatorio amable, firme… o dramático 😂.

Se instala en tu teléfono como una app (sin Play Store), funciona sin internet y tus datos se quedan en TU teléfono.
Pagas una sola vez: $4.99 de por vida. Sin suscripción.
¿Dudas? Prueba la demo gratis (3 usos) y lo que hagas se queda guardado cuando la compres.`,
  faq: JSON.stringify([
    { q: '¿Cómo la recibo?', a: 'Al pagar te llega un enlace por correo (y por Telegram si compraste ahí). Lo abres y la agregas a la pantalla de inicio de tu teléfono: queda con su corona 👑 como cualquier app.' },
    { q: '¿Sirve para mi negocio?', a: 'Si vendes algo que tú haces o revendes desde casa (postres, comida, uñas, pestañas, costura, tiendita, manualidades…), sí.' },
    { q: '¿Hay que pagar mensualidad?', a: 'No. Pagas una vez y es tuya para siempre.' },
    { q: '¿Y si cambio de teléfono?', a: 'En ⚙️ guardas una copia de seguridad y la restauras en el teléfono nuevo con el mismo enlace.' }]),
  gallery: JSON.stringify([
    { url: '/img/galeria/jefa-precio.jpg', cap: '💰 Tu precio justo, con tu tiempo incluido' },
    { url: '/img/galeria/jefa-estado.jpg', cap: '🎨 Estados para WhatsApp con tu foto' },
    { url: '/img/galeria/jefa-lista.jpg', cap: '📋 Tu lista de precios lista para mandar' },
    { url: '/img/galeria/jefa-cobro.jpg', cap: '💸 Cobra sin pena (hasta en modo dramático 😂)' }]),
  video_url: '/video/lajefa-reel.mp4',
  price_cents: 499, compare_cents: 0, cover_url: config.baseUrl + '/img/portada-la-jefa.jpg', external_url: '/app/jefa/', file_name: '',
  license_type: 'Propio', license_note: 'Para uso personal de quien la compra. No se permite compartir el enlace.',
  regalo_url: '/jefa#demo', regalo_title: 'la demo de La Jefa (3 usos gratis)',
  active: process.argv.includes('--publicar') ? 1 : (old?.active ?? 0) });
console.log(`✔ ${p.emoji} ${p.title} · $${(p.price_cents / 100).toFixed(2)} · ${p.active ? 'PUBLICADA' : 'oculta (actívala con --publicar)'}`);
console.log(`Pruébala (abre antes la tienda con ?soy=dueno en ese teléfono): ${config.baseUrl}/app/jefa/`);
