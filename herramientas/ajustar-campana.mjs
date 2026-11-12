// ⚙️ Ajustar campañas desde el servidor (Diego no tiene que entrar al Administrador de anuncios).
// Uso:
//   node herramientas/ajustar-campana.mjs pausar <id_campaña>
//   node herramientas/ajustar-campana.mjs activar <id_campaña>
//   node herramientas/ajustar-campana.mjs presupuesto <id_campaña> <usd_por_dia>
// El presupuesto se cambia donde esté puesto: en la campaña (CBO) o repartido en sus conjuntos activos (ABO).
import '../src/config.js';   // carga .env (token de Meta) cuando se corre con docker exec
import { api } from '../src/telegram/anuncios-meta.js';

const [acc, id, usd] = process.argv.slice(2);
if (!acc || !id) { console.log('Uso: pausar|activar <id> · presupuesto <id> <usd>'); process.exit(1); }
const c = await api('GET', id, { fields: 'name,effective_status,daily_budget' });
console.log(`📣 ${c.name} (${c.effective_status})`);

if (acc === 'pausar' || acc === 'activar') {
  await api('POST', id, { status: acc === 'pausar' ? 'PAUSED' : 'ACTIVE' });
  console.log(acc === 'pausar' ? '⏸️ Pausada.' : '▶️ Activada.');
} else if (acc === 'presupuesto') {
  const cents = Math.round(Number(usd) * 100);
  if (!(cents >= 100)) { console.log('Presupuesto inválido (mínimo $1).'); process.exit(1); }
  if (Number(c.daily_budget)) {
    await api('POST', id, { daily_budget: cents });
    console.log(`💵 Presupuesto de la campaña: $${(Number(c.daily_budget) / 100).toFixed(2)} → $${(cents / 100).toFixed(2)} al día.`);
  } else {
    const sets = ((await api('GET', `${id}/adsets`, { fields: 'name,daily_budget,effective_status', limit: 50 })).data || []).filter((s) => s.effective_status === 'ACTIVE' && Number(s.daily_budget));
    const total = sets.reduce((s, a) => s + Number(a.daily_budget), 0);
    if (!total) { console.log('No encontré presupuesto diario en la campaña ni en sus conjuntos activos.'); process.exit(1); }
    for (const s of sets) {
      const nuevo = Math.max(100, Math.round(cents * Number(s.daily_budget) / total));
      await api('POST', s.id, { daily_budget: nuevo });
      console.log(`💵 ${s.name}: $${(Number(s.daily_budget) / 100).toFixed(2)} → $${(nuevo / 100).toFixed(2)} al día`);
    }
  }
} else { console.log('Acción desconocida: usa pausar, activar o presupuesto.'); process.exit(1); }
