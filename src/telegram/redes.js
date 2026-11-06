// Publicar en Instagram y en la página de Facebook con la API oficial de Meta (Graph API).
// Claves en .env (las guarda `bash configurar.sh redes`): META_PAGE_ID, META_PAGE_TOKEN, META_IG_ID.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { config } from '../config.js';

const G = 'https://graph.facebook.com/v23.0';
const env = (k) => process.env[k] || '';
export const redesListas = () => !!(env('META_PAGE_TOKEN') && env('META_PAGE_ID'));
const KIT = path.join(path.dirname(fileURLToPath(import.meta.url)), 'kit-instagram.json');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function call(method, url, params = {}) {
  const body = new URLSearchParams({ ...params, access_token: env('META_PAGE_TOKEN') });
  const r = method === 'GET' ? await fetch(`${url}?${body}`) : await fetch(url, { method, body });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.error) throw new Error(j.error?.error_user_msg || j.error?.message || `HTTP ${r.status}`);
  return j;
}

/** Foto en Instagram: contenedor → esperar a que procese → publicar. */
export async function igFoto(imageUrl, caption) {
  const ig = env('META_IG_ID'); if (!ig) throw new Error('falta META_IG_ID (Instagram no está conectado a la página)');
  const c = await call('POST', `${G}/${ig}/media`, { image_url: imageUrl, caption });
  for (let i = 0; i < 20; i++) {
    const s = await call('GET', `${G}/${c.id}`, { fields: 'status_code' }).catch(() => ({}));
    if (s.status_code === 'FINISHED') break;
    if (s.status_code === 'ERROR') throw new Error('Instagram no pudo procesar la imagen');
    await sleep(3000);
  }
  return call('POST', `${G}/${ig}/media_publish`, { creation_id: c.id });
}

/** Foto en la página de Facebook. */
export const fbFoto = (imageUrl, message) => call('POST', `${G}/${env('META_PAGE_ID')}/photos`, { url: imageUrl, message });

/** Comprueba la conexión: nombre de la página y usuario de Instagram. */
export async function estadoRedes() {
  const p = await call('GET', `${G}/${env('META_PAGE_ID')}`, { fields: 'name' });
  const ig = env('META_IG_ID') ? await call('GET', `${G}/${env('META_IG_ID')}`, { fields: 'username' }).catch(() => null) : null;
  return { pagina: p.name, instagram: ig?.username || null };
}

/** Sube las 9 publicaciones del kit en orden (la 1 primero) a Instagram y Facebook. say(texto) informa el avance. */
export async function publicarKit(say, desde = 1) {
  const kit = JSON.parse(fs.readFileSync(KIT, 'utf8')).filter((k) => k.n >= desde);
  const base = config.baseUrl.replace(/\/$/, '');
  let ok = 0;
  for (const k of kit) {
    const url = `${base}${k.img}`; const res = [];
    try { await igFoto(url, k.caption); res.push('Instagram ✅'); } catch (e) { res.push(`Instagram ❌ ${e.message}`); }
    try { await fbFoto(url, k.caption); res.push('Facebook ✅'); } catch (e) { res.push(`Facebook ❌ ${e.message}`); }
    if (res.every((x) => x.includes('✅'))) ok++;
    await say(`📤 Publicación ${k.n}/9 · ${res.join(' · ')}`);
    if (res.every((x) => x.includes('❌'))) { await say(`⏸️ Me detuve en la ${k.n}. Cuando lo arreglemos: <code>/publicar kit ${k.n}</code> sigue desde ahí.`); return ok; }
    await sleep(15000);  // un poco de espacio entre publicaciones
  }
  return ok;
}
