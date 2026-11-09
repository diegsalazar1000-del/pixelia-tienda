// Publica el reel de LA JEFA en Instagram (Reels + cuadrícula). El texto pide "Comenta DEMO": comentarios.js responde solo con el link (#lajefa).
// Antes: docker exec pixelia-estudio python3 /pixelia/herramientas/lajefa/reel.py
// Uso:   docker exec pixelia node --no-warnings /app/herramientas/lajefa/publicar.mjs
import fs from 'node:fs';
import path from 'node:path';
import { config } from '../../src/config.js';
import { igReel } from '../../src/telegram/redes.js';

const base = config.baseUrl.replace(/\/$/, '');
const f = path.join(path.dirname(config.paths.files), 'anuncios', 'la-jefa', 'reel-lajefa.mp4');
if (!fs.existsSync(f)) { console.log('❌ Falta el reel: corre antes reel.py en el estudio'); process.exit(1); }
const TEXTO = `¿Vendes postres, uñas o tienes tu tiendita? 🧁💅🏪
¿Sabes cuánto ganas DE VERDAD en cada venta? 😳

👑 La Jefa te lo dice en segundos… y además:
📋 tu lista de precios para WhatsApp
🎨 estados bonitos con la foto de tu producto
👥 tus clientas y 💸 quién te debe

💬 Comenta DEMO y pruébala gratis
📲 o entra al link del perfil: pixeliadigital.app/jefa

#lajefa #emprendedora #negociodesdecasa #reposteria #manicurista #emprendimiento`;
console.log('Subiendo el reel… tarda 1-2 minutos');
const r = await igReel(`${base}/media/anuncios/la-jefa/reel-lajefa.mp4`, TEXTO, { feed: true });
console.log(`✔ Reel de La Jefa publicado en Instagram. id: ${r?.id}`);
