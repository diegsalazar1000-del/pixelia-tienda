// Resumen rápido: visitas a la tienda y a /reto (hoy y 7 días), correos nuevos, pedidos reales y lo que dice Meta de las campañas activas.
// Uso: docker exec pixelia node --no-warnings /app/herramientas/visitas.mjs
import fs from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { config } from '../src/config.js';
const db = new DatabaseSync(config.paths.db);
const q = (sql, ...a) => db.prepare(sql).all(...a);
console.log('👀 VISITAS (hora del servidor, UTC)');
for (const r of q(`SELECT p.title t, SUM(CASE WHEN v.day = date('now') THEN v.views ELSE 0 END) hoy, SUM(v.views) sem
  FROM product_views v JOIN products p ON p.id = v.product_id WHERE v.day >= date('now','-6 day') GROUP BY p.id ORDER BY sem DESC`))
  console.log(`  ${r.t.slice(0, 45)}: hoy ${r.hoy} · 7 días ${r.sem}`);
console.log('\n📩 CORREOS NUEVOS');
for (const r of q(`SELECT source s, SUM(created_at >= date('now')) hoy, COUNT(*) sem FROM subscribers WHERE created_at >= date('now','-6 day') GROUP BY source ORDER BY sem DESC`))
  console.log(`  ${r.s || '(cupón)'}: hoy ${r.hoy} · 7 días ${r.sem}`);
const ped = q(`SELECT status, COUNT(*) n FROM orders WHERE created_at >= date('now','-6 day') AND COALESCE(prueba,0) = 0 GROUP BY status`);
console.log('\n🛒 PEDIDOS (7 días, sin pruebas): ' + (ped.map((r) => `${r.status} ${r.n}`).join(' · ') || 'ninguno'));
try {
  const { resultados } = await import('../src/telegram/anuncios-meta.js');
  const cs = JSON.parse(fs.readFileSync(path.join(path.dirname(config.paths.db), 'campanas.json'), 'utf8')).filter((c) => c.estado === 'activa');
  console.log('\n📊 META (últimos 7 días)');
  for (const c of cs) {
    const r = await resultados(c.camp).catch((e) => ({ error: e.message }));
    const act = (t) => (r?.actions || []).filter((a) => a.action_type === t).reduce((s, a) => s + Number(a.value), 0);
    console.log(`  ${c.titulo}: ${r?.error ? '⚠️ ' + r.error : r ? `gastado $${r.spend} · alcance ${r.reach} · clics ${r.clicks} · visitas a la página ${act('landing_page_view')} · visitas al perfil ${act('profile_visit') || act('instagram_profile_visit') || '—'}` : 'todavía sin datos (Meta la está revisando o empezando)'}`);
  }
} catch (e) { console.log('\n📊 Meta: ' + e.message); }
