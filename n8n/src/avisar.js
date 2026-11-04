// 📲 AVISAR POR TELEGRAM — te manda los mejores con botones para decidir.
const C = $('Config').first().json;
const { evaluated = [], log = [], found = 0 } = $input.first().json;
const tg = (method, body) => this.helpers.httpRequest({ method: 'POST', url: `https://api.telegram.org/bot${C.TELEGRAM_RADAR_TOKEN}/${method}`, body, json: true });
const esc = (s) => String(s ?? '').replace(/[&<>]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[ch]));
const icon = { etsy: '🟠 Etsy', tiktok: '⚫ TikTok', instagram: '🟣 Instagram', hotmart: '🔥 Hotmart' };
const num = (n) => Number(n || 0).toLocaleString('es');

const winners = evaluated
  .filter((c) => c.ai_score >= C.NOTA_MINIMA_AVISO && c.ai?.es_producto_digital && c.ai?.decision !== 'descartar')
  .sort((a, b) => b.ai_score - a.ai_score || b.trend_score - a.trend_score)
  .slice(0, 10);

for (const c of winners) {
  const m = c.metrics || {}, ai = c.ai;
  const stats = c.source === 'etsy' ? `❤️ ${num(m.favoritos)} favoritos · publicado hace ${m.dias} días`
    : c.source === 'hotmart' ? `🔥 temperatura ${num(m.hot_score)} · ${num(m.reseñas)} reseñas`
    : `${m.vistas ? `👁 ${num(m.vistas)} vistas · ` : ''}❤️ ${num(m.likes)} · hace ${m.dias} días`;
  const text = `📡 <b>${ai.nota}/10 · ${esc(ai.titulo)}</b>
${icon[c.source] || c.source} · ${stats}

📦 ${esc(ai.producto)}
📈 ${esc(ai.por_que)}
🔑 ${esc(ai.derechos)}
⚠️ Riesgos: ${esc(ai.riesgos)}
💲 Precio sugerido: <b>$${ai.precio_sugerido}</b>
👉 Sugerencia: <b>${ai.decision === 'comprar_reventa' ? 'Comprar y revender' : 'Recrear versión propia'}</b>`;
  try {
    await tg('sendMessage', {
      chat_id: C.TELEGRAM_CHAT_ID, text, parse_mode: 'HTML', link_preview_options: { is_disabled: true },
      reply_markup: { inline_keyboard: [
        [{ text: '🛒 Comprar y revender', callback_data: `buy:${c.id}` }, { text: '🛠️ Recrear', callback_data: `rec:${c.id}` }],
        [{ text: '❌ Descartar', callback_data: `no:${c.id}` }, ...(c.url ? [{ text: '🔗 Ver original', url: c.url }] : [])],
      ] },
    });
    await this.helpers.httpRequest({ method: 'POST', url: `${C.TIENDA_URL}/api/n8n/candidates/${c.id}`, headers: { 'x-api-key': C.TIENDA_API_KEY }, body: { status: 'notified' }, json: true });
  } catch (e) { log.push(`Telegram #${c.id}: ${e.message}`); }
}

await tg('sendMessage', {
  chat_id: C.TELEGRAM_CHAT_ID, parse_mode: 'HTML',
  text: `🗞️ <b>Radar de hoy</b>\nRevisados: ${found} · Evaluados: ${evaluated.length} · Te avisé: ${winners.length}\n\n<code>${esc(log.join('\n')).slice(0, 3000)}</code>`,
});
return [{ json: { avisados: winners.length, log } }];
