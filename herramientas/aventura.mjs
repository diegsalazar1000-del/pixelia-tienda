// Registra "Mi Gran Aventura" (libro de actividades personalizado por pedido, 2-8 años) en la tienda.
// El libro lo fabrica el estudio al pagar (herramientas/aventura/build.py + fabrica.py) y se entrega solo por correo.
// Uso: docker exec pixelia node --no-warnings /app/herramientas/aventura.mjs [--publicar]
import { Products } from '../src/db.js';
import { config } from '../src/config.js';

const slug = 'mi-gran-aventura';
const old = Products.bySlug(slug);
const p = Products.upsert({ ...(old ? { id: old.id } : {}), slug, emoji: '📚', category: 'Niños', form: 'aventura',
  title: 'Mi Gran Aventura: libro de actividades con su nombre',
  gancho: '¿Y si su tarea favorita fuera rescatar a su perrito?',
  short: 'Tu hijo es el protagonista: 12 misiones con su nombre, su compañero y su familia, de su edad (2 a 8 años). Aprende letras, números, trazos y lógica jugando, sin pantallas.',
  description: `Pones su nombre, su edad y su compañero de aventura… y en minutos te llega SU libro al correo, listo para imprimir. ✨

Cada página es una misión de su propia historia:
• 🐶 "¡Un perrito se perdió! Sofía, tú conoces el camino" → laberinto
• 🔍 "Sombras misteriosas en el bosque" → une cada dibujo con su sombra
• 🔤 "La llave mágica: la letra de tu nombre" → trazos
• 🎉 "La fiesta de la abuela Rosa" → contar y unir

Las actividades se eligen solas según su edad:
• 2-3 años: trazos, colorear, burbujas para pintar con el dedo, laberintos fáciles
• 4-5 años: letras en español (con Ñ), números, sombras, unir puntos
• 6-8 años: sopa de letras con SUS nombres, sumas, sudoku, la hora, contar hasta 100

🔊 Cada misión tiene un QR: al terminarla, escanéalo y una voz lo felicita con su nombre. ¡Ver su cara no tiene precio!

Incluye: portada con su nombre, "esta aventura es tuya", traza tu nombre, mapa de la aventura, 12 misiones, 2 páginas para colorear y diploma de héroe o heroína. 19 páginas tamaño carta.
Pago único. Lo imprimes las veces que quieras.`,
  faq: JSON.stringify([
    { q: '¿Cómo lo recibo?', a: 'Llenas los datos al comprar y en unos minutos te llega al correo un enlace para descargar el PDF de SU libro, listo para imprimir en casa o en cualquier papelería.' },
    { q: '¿Y si no tiene mascota?', a: 'Elige un compañero de aventura: perrito, gatito, dinosaurio, unicornio, dragón o robot, y ponle el nombre que quiera. Si no pones nombre, le damos uno.' },
    { q: '¿Qué aprende?', a: 'Según su edad: control del lápiz (trazos), letras, números, figuras, lógica (sombras, diferencias, sudoku), atención y la hora. Todo dentro de una historia, para que quiera seguir.' },
    { q: '¿Cómo funciona el QR?', a: 'Lo escaneas con la cámara del teléfono al terminar cada misión: se abre una página con estrellas y una voz que lo felicita por su nombre. No hay que instalar nada.' },
    { q: '¿Tengo varios hijos?', a: 'Compra uno por cada niño: cada libro sale con su nombre y sus actividades según su edad.' }]),
  gallery: JSON.stringify([
    { url: '/img/galeria/aventura-portada.jpg', cap: '📖 La portada lleva su nombre y su compañero' },
    { url: '/img/galeria/aventura-mision.jpg', cap: '🗺️ Cada actividad es una misión de su historia' },
    { url: '/img/galeria/aventura-mapa.jpg', cap: '⭐ El mapa: colorea una estrella por misión' },
    { url: '/img/galeria/aventura-diploma.jpg', cap: '🏆 Diploma de héroe o heroína con QR final' }]),
  price_cents: 499, compare_cents: 0, cover_url: config.baseUrl + '/img/portada-mi-gran-aventura.jpg', external_url: '', file_name: '',
  license_type: 'PLR (rehecho)', license_note: 'Para uso personal y familiar. Puedes imprimirlo las veces que quieras.',
  active: process.argv.includes('--publicar') ? 1 : (old?.active ?? 0) });
console.log(`✔ ${p.emoji} ${p.title} · $${(p.price_cents / 100).toFixed(2)} · ${p.active ? 'PUBLICADO' : 'oculto (actívalo con --publicar)'} · formulario: ${p.form}`);
