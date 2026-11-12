// 🔍 REVISIÓN DE GASTO (Diego 12-nov: "¿cuál da seguidores, cuáles no funcionan y gastan más?")
// Todas las campañas de la cuenta con gasto en los últimos 7 días (incluye hoy): gasto, resultado principal, costo por resultado,
// CTR, frecuencia, y su veredicto. Al final: seguidores nuevos de Instagram por día (para cruzar con las campañas de seguidores).
// Uso: docker exec pixelia node --no-warnings /app/herramientas/revision.mjs   (en el bot: /revision)
import { api } from '../src/telegram/anuncios-meta.js';

const env = (k) => process.env[k] || '';
const dia = (n) => new Date(Date.now() - n * 864e5).toLocaleDateString('en-CA', { timeZone: 'America/Caracas' });
const R7 = JSON.stringify({ since: dia(6), until: dia(0) });
const act = env('META_AD_ACCOUNT');
if (!act) { console.log('Meta no está conectado (falta META_AD_ACCOUNT).'); process.exit(0); }

const accion = (acts, re) => (acts || []).filter((a) => re.test(a.action_type)).reduce((s, a) => s + Number(a.value || 0), 0);
const camps = (await api('GET', `${act}/campaigns`, { fields: 'name,objective,effective_status,daily_budget', limit: 100 })).data || [];
const filas = [];
for (const c of camps) {
  const i = (await api('GET', `${c.id}/insights`, { fields: 'spend,impressions,reach,frequency,ctr,actions', time_range: R7 })).data?.[0];
  if (!i || !Number(i.spend)) continue;
  let pres = Number(c.daily_budget || 0) / 100;
  if (!pres) {   // presupuesto en los conjuntos (ABO)
    const sets = (await api('GET', `${c.id}/adsets`, { fields: 'daily_budget,effective_status', limit: 50 })).data || [];
    pres = sets.filter((s) => s.effective_status === 'ACTIVE').reduce((s, a) => s + Number(a.daily_budget || 0) / 100, 0);
  }
  const lpv = accion(i.actions, /^landing_page_view$/), clic = accion(i.actions, /^link_click$/);
  const perfil = accion(i.actions, /profile_visit|profile_view/), seg = accion(i.actions, /follow|^like$/);
  const compras = accion(i.actions, /purchase/), leads = accion(i.actions, /^lead$|\.lead$/);
  const esSeguidores = /seguidor|perfil|follow|metas|reto/i.test(c.name) || /ENGAGEMENT|AWARENESS/.test(c.objective);
  let res, nom;
  if (compras) { res = compras; nom = 'compras'; }
  else if (esSeguidores && (perfil || seg)) { res = seg || perfil; nom = seg ? 'seguidores' : 'visitas al perfil'; }
  else if (esSeguidores) { res = 0; nom = 'perfil'; }   // Meta no separa las visitas al perfil en "actions": no juzgar por visitas a la página
  else if (lpv) { res = lpv; nom = 'visitas a la página'; }
  else { res = clic; nom = 'clics'; }
  filas.push({ n: c.name, st: c.effective_status, pres, g: Number(i.spend), res, nom, cpr: res ? Number(i.spend) / res : null, ctr: Number(i.ctr || 0), fr: Number(i.frequency || 0), leads, compras, seg, perfil, esSeguidores });
}

if (!filas.length) { console.log('Ninguna campaña gastó en los últimos 7 días en esta cuenta.'); }
const total = filas.reduce((s, f) => s + f.g, 0);
console.log(`🔍 REVISIÓN DE CAMPAÑAS · 7 días con hoy (${dia(6)} → ${dia(0)})`);
console.log(`💸 Gasto total: $${total.toFixed(2)} · activas hoy ≈ $${filas.filter((f) => f.st === 'ACTIVE').reduce((s, f) => s + f.pres, 0).toFixed(0)}/día\n`);
for (const f of filas.sort((a, b) => b.g - a.g)) {
  const est = f.st === 'ACTIVE' ? '🟢' : '⏸️';
  // Veredicto simple: visitas a la página ≤ $0.04 bien; perfil ≤ $0.10 bien; seguidor ≤ $0.30 bien; frecuencia ≥ 3 = cansancio.
  let v = '';
  if (f.nom === 'perfil') v = 'ℹ️ campaña de seguidores: Meta no da aquí las visitas al perfil → mira "Resultados" en el Administrador de anuncios';
  else if (!f.res) v = '🔴 gasta y no trae nada';
  else if (f.nom === 'visitas a la página') v = f.cpr <= 0.04 ? '✅ visitas baratas' : f.cpr <= 0.08 ? '🟡 visitas algo caras' : '🔴 visitas caras';
  else if (f.nom === 'visitas al perfil') v = f.cpr <= 0.10 ? '✅ perfil barato' : '🟡 perfil caro';
  else if (f.nom === 'seguidores') v = f.cpr <= 0.30 ? '✅ seguidores baratos' : '🟡 seguidores caros';
  if (f.fr >= 3) v += ' · 😴 la gente ya lo vio mucho (frecuencia ' + f.fr.toFixed(1) + ')';
  console.log(`${est} ${f.n}${f.pres ? ` · $${f.pres.toFixed(0)}/día` : ''}`);
  if (f.nom === 'perfil') console.log(`   $${f.g.toFixed(2)} gastados · CTR ${f.ctr.toFixed(1)}%`); else console.log(`   $${f.g.toFixed(2)} → ${Math.round(f.res)} ${f.nom}${f.cpr ? ` ($${f.cpr.toFixed(3)} c/u)` : ''} · CTR ${f.ctr.toFixed(1)}%`
    + (f.leads ? ` · ${f.leads} correos` : '') + (f.compras ? ` · 🛒 ${f.compras} compras` : '') + (f.esSeguidores && f.perfil && f.seg ? ` · ${f.perfil} visitas al perfil` : ''));
  console.log(`   ${v}`);
}

// 📈 Seguidores nuevos de Instagram por día (métrica de la cuenta, no de un anuncio: sirve para ver si suben cuando corre la de seguidores)
try {
  const ig = env('META_IG_ID'), tok = env('META_PAGE_TOKEN');
  if (ig && tok) {
    const u = new URL(`https://graph.facebook.com/v23.0/${ig}/insights`);
    Object.entries({ metric: 'follower_count', period: 'day', since: Math.floor(Date.now() / 1000) - 7 * 86400, until: Math.floor(Date.now() / 1000), access_token: tok }).forEach(([k, val]) => u.searchParams.set(k, val));
    const j = await (await fetch(u)).json();
    const vals = j.data?.[0]?.values || [];
    if (vals.length) {
      const tot = vals.reduce((s, x) => s + Number(x.value || 0), 0);
      console.log(`\n📈 Seguidores nuevos en Instagram (7 días): ${tot}`);
      console.log('   ' + vals.map((x) => `${x.end_time.slice(8, 10)}/${x.end_time.slice(5, 7)}: +${x.value}`).join(' · '));
      const seguidoras = filas.filter((f) => f.esSeguidores);
      const gS = seguidoras.reduce((s, f) => s + f.g, 0);
      if (tot && gS) console.log(`   Con lo gastado en campañas de seguidores ($${gS.toFixed(2)}) → ≈ $${(gS / tot).toFixed(2)} por seguidor (aprox.: también cuentan los orgánicos)`);
    } else if (j.error) console.log('\n📈 Seguidores: Meta no los dio (' + (j.error.message || '').slice(0, 90) + ')');
  }
} catch (e) { console.log('\n📈 Seguidores: no se pudo leer (' + e.message + ')'); }
console.log('\nℹ️ Las promociones hechas desde la app de Instagram solo salen aquí si usan esta misma cuenta publicitaria.');
