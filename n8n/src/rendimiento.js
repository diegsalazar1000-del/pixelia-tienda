// 📊 RENDIMIENTO DIARIO — cruza ventas de la tienda con Meta Ads, pausa lo que pierde y propone reemplazos.
// Regla para enlazar anuncio ↔ producto: el NOMBRE del anuncio en Meta empieza con [slug-del-producto], ej. "[planner-de-bodas] v1".
const C = $('Config').first().json;
const tg = (method, body) => this.helpers.httpRequest({ method: 'POST', url: `https://api.telegram.org/bot${C.TELEGRAM_RADAR_TOKEN}/${method}`, body, json: true });
const store = (method, path, body) => this.helpers.httpRequest({ method, url: `${C.TIENDA_URL}${path}`, headers: { 'x-api-key': C.TIENDA_API_KEY }, body, json: true, timeout: 60000 });
const graph = (method, path, qs = {}) => this.helpers.httpRequest({ method, url: `https://graph.facebook.com/v21.0/${path}`, qs: { access_token: C.META_TOKEN, ...qs }, json: true, timeout: 60000 });
const esc = (s) => String(s ?? '').replace(/[&<>]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[ch]));
const usd = (n) => '$' + Number(n || 0).toFixed(2);
const log = [];

// 1) Ventas de la tienda (últimos 7 días)
const perf = await store('GET', '/api/n8n/performance?days=7');

// 2) Anuncios de Meta (últimos 7 días)
const ads = {};
const metaOn = C.META_TOKEN && !C.META_TOKEN.startsWith('EAAG...');
if (metaOn) {
  try {
    const list = await graph('GET', `${C.META_AD_ACCOUNT}/ads`, { fields: 'id,name,effective_status', limit: 500 });
    for (const a of list.data || []) ads[a.id] = { id: a.id, name: a.name, status: a.effective_status, spend: 0, purchases: 0, value: 0, clicks: 0, impressions: 0 };
    const ins = await graph('GET', `${C.META_AD_ACCOUNT}/insights`, { level: 'ad', date_preset: 'last_7d', limit: 500,
      fields: 'ad_id,ad_name,spend,impressions,clicks,ctr,actions,action_values' });
    for (const r of ins.data || []) {
      const a = ads[r.ad_id] ||= { id: r.ad_id, name: r.ad_name, status: 'UNKNOWN' };
      const pick = (arr) => Number((arr || []).find((x) => ['offsite_conversion.fb_pixel_purchase', 'purchase', 'omni_purchase'].includes(x.action_type))?.value || 0);
      Object.assign(a, { spend: Number(r.spend || 0), impressions: Number(r.impressions || 0), clicks: Number(r.clicks || 0),
        purchases: pick(r.actions), value: pick(r.action_values) });
    }
  } catch (e) { log.push('Meta: ' + (e.message || e)); }
}
const adsOf = (slug) => Object.values(ads).filter((a) => (a.name || '').toLowerCase().startsWith(`[${slug}]`));

// 3) Decisiones por producto
const lines = [], retired = [], paused = [];
let activeCount = perf.products.length;
const retire = async (p) => {
  if (!C.AUTO_RETIRAR_PRODUCTOS || retired.length >= C.MAX_RETIROS_POR_DIA || activeCount <= C.MIN_PRODUCTOS_ACTIVOS) return false;
  await store('POST', `/api/n8n/products/${p.id}/retire`, {}); retired.push(p); activeCount--; return true;
};
for (const p of perf.products) {
  const price = p.price_cents / 100, revenue = p.revenue_cents / 100;
  const mine = adsOf(p.slug), active = mine.filter((a) => a.status === 'ACTIVE');
  const spend = mine.reduce((s, a) => s + (a.spend || 0), 0);
  const roas = spend ? revenue / spend : null;
  const clicks = mine.reduce((s, a) => s + (a.clicks || 0), 0), impr = mine.reduce((s, a) => s + (a.impressions || 0), 0);
  const ctr = impr ? (clicks / impr) * 100 : null;
  let verdict = '', why = '';

  if (p.days_live < C.DIAS_PRUEBA) { verdict = '🧪 En prueba'; why = `día ${p.days_live} de ${C.DIAS_PRUEBA}`; }
  else if (spend >= C.GASTO_MAX_SIN_VENTA && p.sales === 0) {
    verdict = '🛑 Pierde'; why = `gastó ${usd(spend)} sin ventas`;
    if (C.AUTO_PAUSAR_ANUNCIOS) for (const a of active) { try { await graph('POST', a.id, { status: 'PAUSED' }); paused.push(a.name); } catch (e) { log.push(`No pude pausar ${a.name}: ${e.message}`); } }
    if (!(await retire(p))) why += ' (no lo retiré: límite diario o mínimo de productos)';
  } else if (!mine.length && p.days_live >= C.DIAS_PRUEBA * 2 && p.sales === 0) {
    verdict = '💤 Sin ventas ni anuncios'; why = `${p.days_live} días publicado, ${p.views} visitas`;
    if (!(await retire(p))) why += ' → ponle anuncios o retíralo';
  } else if (roas !== null && roas >= C.ROAS_ESCALAR) { verdict = '🚀 Ganador'; why = `ROAS ${roas.toFixed(1)} → sube el presupuesto un 20%`; }
  else if (roas !== null && roas < C.ROAS_MINIMO) {
    verdict = '🔧 Ajustar';
    why = ctr !== null && ctr < 0.8 ? `CTR ${ctr.toFixed(2)}%: el anuncio no llama la atención → prueba otro gancho/creativo`
      : p.views && p.checkouts / p.views < 0.05 ? `muchas visitas (${p.views}) y pocos intentos de compra → mejora portada, precio o descripción`
      : p.checkouts > p.sales * 3 ? `${p.checkouts} intentos y ${p.sales} ventas → revisa el pago` : `ROAS ${roas.toFixed(1)}`;
  } else { verdict = '✅ Bien'; why = roas !== null ? `ROAS ${roas.toFixed(1)}` : `${p.sales} ventas sin anuncios`; }

  lines.push(`${verdict} <b>${esc(p.title)}</b>\n   👁 ${p.views} · 🛒 ${p.checkouts} · 💰 ${p.sales} (${usd(revenue)})${spend ? ` · 📣 ${usd(spend)}` : ''}\n   ${esc(why)}`);
}

// 4) Reemplazos: los mejores candidatos del radar que aún no usaste
let best = [];
if (retired.length) best = (await store('GET', `/api/n8n/candidates/best?limit=${Math.min(3, retired.length + 1)}`)).items || [];

const t = perf.totals;
let text = `📊 <b>Rendimiento (7 días)</b>\nTotal histórico: ${t.orders} ventas · ${usd(t.usd_cents / 100)} · ${t.stars} ⭐\n\n${lines.join('\n\n') || 'No hay productos activos.'}`;
if (paused.length) text += `\n\n⏸️ Anuncios pausados: ${paused.map(esc).join(', ')}`;
if (retired.length) text += `\n\n🗑️ Retirados de la tienda: ${retired.map((p) => esc(p.title)).join(', ')}`;
if (!metaOn) text += '\n\nℹ️ Meta Ads no está conectado (falta META_TOKEN): solo uso las ventas de la tienda.';
if (log.length) text += `\n\n<code>${esc(log.join('\n'))}</code>`;
for (let i = 0; i < text.length; i += 3900) await tg('sendMessage', { chat_id: C.TELEGRAM_CHAT_ID, text: text.slice(i, i + 3900), parse_mode: 'HTML' });

for (const c of best) {
  await tg('sendMessage', { chat_id: C.TELEGRAM_CHAT_ID, parse_mode: 'HTML',
    text: `♻️ <b>Reemplazo sugerido · ${c.ai_score}/10</b>\n${esc(c.ai?.titulo || c.title)}\n📈 ${esc(c.ai?.por_que || '')}\n💲 $${c.ai?.precio_sugerido || ''}`,
    reply_markup: { inline_keyboard: [[{ text: '🛒 Comprar y revender', callback_data: `buy:${c.id}` }, { text: '🛠️ Recrear', callback_data: `rec:${c.id}` }],
      [{ text: '❌ Descartar', callback_data: `no:${c.id}` }, ...(c.url ? [{ text: '🔗 Ver', url: c.url }] : [])]] } });
}
return [{ json: { productos: perf.products.length, pausados: paused.length, retirados: retired.length } }];
