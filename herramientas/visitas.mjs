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
try {   // 👑 uso de las demos: abrieron → 1er uso → 3 usos (vieron la oferta)
  const ev = q(`SELECT app, evento, SUM(CASE WHEN day = date('now') THEN n ELSE 0 END) hoy, SUM(n) sem FROM app_eventos WHERE day >= date('now','-6 day') GROUP BY app, evento`);
  for (const app of [...new Set(ev.map((e) => e.app))]) {
    const g = (k, c = 'sem') => ev.find((e) => e.app === app && e.evento === k)?.[c] || 0;
    console.log(`\n👑 DEMO ${app.toUpperCase()} (hoy / 7 días)`);
    console.log(`  abrieron ${g('abrio', 'hoy')} / ${g('abrio')} · usaron 1 vez ${g('uso1', 'hoy')} / ${g('uso1')} · llegaron a 3 usos ${g('uso3', 'hoy')} / ${g('uso3')} · dejaron correo ${g('correo', 'hoy')} / ${g('correo')}`);
    if (g('abrio')) console.log(`  → de cada 10 que abren, ${Math.round(g('uso1') / g('abrio') * 10)} la usan`);
    const tabs = ev.filter((e) => e.app === app && e.evento.startsWith('tab_')).sort((a, b) => b.sem - a.sem);
    if (tabs.length) console.log('  pestañas que más abren (7 días): ' + tabs.map((e) => `${e.evento.slice(4)} ${e.sem}`).join(' · '));
    const NOM = { caro: '💸 cara', pago: '💳 no sabe pagar', nosirve: '🤷 no es para su negocio', dificil: '😵 difícil', luego: '⏳ después' };
    const mot = ev.filter((e) => e.app === app && e.evento.startsWith('no_')).sort((a, b) => b.sem - a.sem);
    if (mot.length) console.log('  ¿por qué no compran? (7 días): ' + mot.map((e) => `${NOM[e.evento.slice(3)] || e.evento} ${e.sem}`).join(' · '));
  }
} catch {}
console.log('\n📩 CORREOS NUEVOS');
for (const r of q(`SELECT source s, SUM(created_at >= date('now')) hoy, COUNT(*) sem FROM subscribers WHERE created_at >= date('now','-6 day') GROUP BY source ORDER BY sem DESC`))
  console.log(`  ${r.s || '(cupón)'}: hoy ${r.hoy} · 7 días ${r.sem}`);
const ped = q(`SELECT status, COUNT(*) n FROM orders WHERE created_at >= date('now','-6 day') AND COALESCE(prueba,0) = 0 GROUP BY status`);
console.log('\n🛒 PEDIDOS (7 días, sin pruebas): ' + (ped.map((r) => `${r.status} ${r.n}`).join(' · ') || 'ninguno'));
try {
  const { api } = await import('../src/telegram/anuncios-meta.js');
  const cs = JSON.parse(fs.readFileSync(path.join(path.dirname(config.paths.db), 'campanas.json'), 'utf8')).filter((c) => c.estado !== 'borrada' && c.camp);
  const ACC = { landing_page_view: 'visitas a la página', link_click: 'clics al enlace', profile_visit: 'visitas al perfil', onsite_conversion_profile_visit: 'visitas al perfil',
    'offsite_conversion.fb_pixel_lead': 'correos (Lead)', 'offsite_conversion.fb_pixel_purchase': 'compras', video_view: 'reproducciones 3 s', post_engagement: 'interacciones', like: 'me gusta', follow: 'seguidores' };
  const acc = (r) => (r?.actions || []).filter((a) => ACC[a.action_type]).map((a) => `${ACC[a.action_type]} ${a.value}`).join(' · ');
  const ins = (id, preset) => api('GET', `${id}/insights`, { fields: 'spend,impressions,reach,frequency,clicks,ctr,cpc,actions', date_preset: preset }).then((r) => r.data?.[0]).catch(() => null);
  console.log('\n📊 META');
  for (const c of cs) {
    const st = await api('GET', c.camp, { fields: 'name,effective_status' }).catch((e) => ({ error: e.message }));
    if (st.error) { if (!/#10|does not exist/i.test(st.error)) console.log(`  ${c.titulo}: ⚠️ ${st.error}`); continue; }   // campañas de la cuenta vieja bloqueada: no se muestran
    console.log(`\n▶ ${c.titulo} — ${st.effective_status}`);
    for (const [nom, pr] of [['hoy', 'today'], ['ayer', 'yesterday'], ['7 días', 'last_7d']]) {
      const r = await ins(c.camp, pr);
      console.log(r ? `  ${nom}: $${r.spend} · alcance ${r.reach} · frec. ${Number(r.frequency || 0).toFixed(1)} · CTR ${Number(r.ctr || 0).toFixed(2)}% · ${acc(r) || 'sin acciones'}` : `  ${nom}: sin datos`);
    }
    const ads = await api('GET', `${c.camp}/ads`, { fields: 'name,effective_status,ad_review_feedback', limit: 20 }).then((r) => r.data || []).catch(() => []);
    for (const a of ads) {
      const r = await ins(a.id, 'last_7d');
      const rev = a.ad_review_feedback ? ' · ⚠️ ' + JSON.stringify(a.ad_review_feedback).slice(0, 120) : '';
      console.log(`   • ${a.name.split('·').slice(-1)[0].trim()} [${a.effective_status}]: ${r ? `$${r.spend} · CTR ${Number(r.ctr || 0).toFixed(2)}% · ${acc(r) || 'sin acciones'}` : 'sin datos'}${rev}`);
    }
    // 🌎 por país (7 días): resultado principal y cuánto costó cada uno → para quedarnos con los países que rinden
    const pais = await api('GET', `${c.camp}/insights`, { fields: 'spend,ctr,actions', date_preset: 'last_7d', breakdowns: 'country', limit: 50 }).then((r) => r.data || []).catch(() => []);
    if (pais.length) {
      const BAND = (cc) => String.fromCodePoint(...[...cc.toUpperCase()].map((ch) => 0x1F1A5 + ch.charCodeAt(0)));
      const res = (r) => { const a = r.actions || []; for (const t of ['offsite_conversion.fb_pixel_purchase', 'offsite_conversion.fb_pixel_lead', 'landing_page_view', 'onsite_conversion_profile_visit', 'profile_visit', 'link_click']) { const x = a.find((y) => y.action_type === t); if (x) return [ACC[t], Number(x.value)]; } return ['', 0]; };
      console.log('   🌎 Por país (7 días):');
      for (const r of pais.sort((a, b) => b.spend - a.spend)) {
        const [nom, v] = res(r);
        console.log(`     ${BAND(r.country)} ${r.country}: $${Number(r.spend).toFixed(2)} · ${v ? `${v} ${nom} · $${(r.spend / v).toFixed(3)} c/u` : 'sin resultados'} · CTR ${Number(r.ctr || 0).toFixed(1)}%`);
      }
    }
  }
} catch (e) { console.log('\n📊 Meta: ' + e.message); }
