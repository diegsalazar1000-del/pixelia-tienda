// 💾 RESPALDO de Pixelia (Diego 12-nov: "si cae todo, seguir desde otra cuenta").
// Lo valioso que NO es de Meta: base de datos (productos, pedidos, clientes), lista de correos, archivos de productos y configuración de campañas.
// El código ya vive en GitHub. Las claves (.env) NO se incluyen: se vuelven a poner con configurar.sh.
// Uso (dentro del contenedor): docker exec pixelia node --no-warnings /app/herramientas/respaldo.mjs
// Deja respaldos/pixelia-AAAA-MM-DD.tar.gz (guarda los 4 últimos) y manda a Telegram la lista de clientes (+ el respaldo si pesa < 48 MB).
import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { DatabaseSync } from 'node:sqlite';
import { config } from '../src/config.js';
import { tgSendFile, notifyAdmin } from '../src/telegram/api.js';

const raiz = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const hoy = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Caracas' });
const dir = path.join(raiz, 'respaldos'), tmp = path.join(dir, 'tmp-' + hoy);
fs.rmSync(tmp, { recursive: true, force: true }); fs.mkdirSync(tmp, { recursive: true });

// 1) Copia consistente de la base de datos (sin parar la tienda)
const db = new DatabaseSync(config.paths.db);
db.exec(`VACUUM INTO '${path.join(tmp, 'tienda.db').replace(/'/g, "''")}'`);

// 2) Lista de clientes y contactos (el "tesoro": se sube a Meta como público en una cuenta nueva)
const filas = new Map();
const add = (email, origen, fecha, compro = 0) => {
  email = String(email || '').trim().toLowerCase(); if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return;
  const f = filas.get(email) || { origen: new Set(), fecha, compro: 0 };
  f.origen.add(origen); if (fecha && (!f.fecha || fecha < f.fecha)) f.fecha = fecha; f.compro += compro; filas.set(email, f);
};
const q = (sql) => { try { return db.prepare(sql).all(); } catch { return []; } };
for (const r of q(`SELECT o.email, p.slug, o.paid_at FROM orders o JOIN products p ON p.id = o.product_id WHERE o.status = 'paid' AND COALESCE(o.prueba,0) = 0`)) add(r.email, 'compra:' + r.slug, r.paid_at, 1);
for (const r of q(`SELECT email, source, created_at FROM subscribers`)) add(r.email, r.source || 'correo', r.created_at);
for (const r of q(`SELECT email, created_at FROM aventura_leads`)) add(r.email, 'landing:aventura', r.created_at);
for (const r of q(`SELECT email, slug, created_at FROM form_leads`)) add(r.email, 'landing:' + r.slug, r.created_at);
const csv = ['email,compras,origen,primera_fecha', ...[...filas].map(([e, f]) => `${e},${f.compro},"${[...f.origen].join(' | ')}",${f.fecha || ''}`)].join('\n');
const csvPath = path.join(dir, `clientes-${hoy}.csv`);
fs.writeFileSync(csvPath, csv); fs.copyFileSync(csvPath, path.join(tmp, 'clientes.csv'));
const compradores = [...filas.values()].filter((f) => f.compro).length;

// 3) Empaquetar: base de datos + lista + data/ (campañas, públicos, aprendizaje…) + archivos de productos + imágenes propias
const LEEME = `RESPALDO PIXELIA ${hoy}
- tienda.db: copia completa de la base (productos, pedidos, clientes, eventos).
- clientes.csv: ${filas.size} contactos (${compradores} compradores). Para Meta: Públicos > Crear > Lista de clientes > subir este archivo.
- data/: campañas, públicos, calendario y demás estado.
- storage/products/: los archivos que se entregan a los clientes.
- public/img y public/regalos: portadas, imágenes de anuncios y regalos.
Restaurar en un servidor nuevo: clonar el repo de GitHub, copiar estas carpetas encima, poner tienda.db en data/, y correr configurar.sh para las claves.`;
fs.writeFileSync(path.join(tmp, 'LEEME.txt'), LEEME);
const out = path.join(dir, `pixelia-${hoy}.tar.gz`);
const incluir = ['data', 'storage/products', 'public/img', 'public/regalos', 'herramientas/plan2027/anuncios'].filter((p) => fs.existsSync(path.join(raiz, p)));
execSync(`tar -czf "${out}" --exclude='data/*.db' --exclude='data/*.db-*' -C "${raiz}" ${incluir.map((p) => `"${p}"`).join(' ')} -C "${tmp}" tienda.db clientes.csv LEEME.txt`);
fs.rmSync(tmp, { recursive: true, force: true });

// 4) Guardar solo los 4 últimos
const viejos = fs.readdirSync(dir).filter((f) => /^(pixelia|clientes)-\d{4}-\d\d-\d\d\./.test(f)).sort().reverse();
for (const pre of ['pixelia-', 'clientes-']) viejos.filter((f) => f.startsWith(pre)).slice(4).forEach((f) => fs.rmSync(path.join(dir, f)));

const mb = fs.statSync(out).size / 1048576;
console.log(`💾 Respaldo listo: respaldos/${path.basename(out)} (${mb.toFixed(1)} MB) · ${filas.size} contactos (${compradores} compradores)`);

// 5) Mandarlo a Telegram (fuera del servidor = respaldo de verdad)
const chat = config.telegram.adminChatId;
if (chat) {
  try {
    await tgSendFile(chat, csvPath, `💾 <b>Respaldo ${hoy}</b>\n👥 ${filas.size} contactos · ${compradores} compradores\nGuarda este archivo: es tu lista de clientes (se sube a Meta como público si algún día empiezas en otra cuenta).`);
    if (mb < 48) await tgSendFile(chat, out, `📦 Respaldo completo (${mb.toFixed(1)} MB): base de datos, archivos de productos, imágenes y campañas. Sin claves.`);
    else await notifyAdmin(`📦 El respaldo completo pesa ${mb.toFixed(0)} MB (Telegram acepta hasta 50): quedó en el servidor en /opt/pixelia/respaldos/.`);
    console.log('📲 Enviado a Telegram');
  } catch (e) { console.error('No se pudo mandar a Telegram:', e.message); }
}
