// 💚 Pago Móvil (Venezuela, en bolívares a la tasa oficial BCV). Solo se ofrece a visitantes con zona horaria de Venezuela.
// Datos en .env (bash configurar.sh pagomovil): PAGOMOVIL_BANCO, PAGOMOVIL_TEL, PAGOMOVIL_CI, PAGOMOVIL_NOMBRE (opcional),
// PAGOMOVIL_TASA (respaldo si no se puede leer la tasa del día). Confirmación manual con botón en el bot (como Binance).
const env = (k) => (process.env[k] || '').trim();
export const pagoMovilEnabled = () => !!(env('PAGOMOVIL_BANCO') && env('PAGOMOVIL_TEL') && env('PAGOMOVIL_CI'));
export const datosPagoMovil = () => ({ banco: env('PAGOMOVIL_BANCO'), tel: env('PAGOMOVIL_TEL'), ci: env('PAGOMOVIL_CI'), nombre: env('PAGOMOVIL_NOMBRE') });
let tasa = { v: Number(env('PAGOMOVIL_TASA')) || 0, t: 0, fuente: 'respaldo' };
async function actualizar() {
  try {
    const r = await fetch('https://ve.dolarapi.com/v1/dolares/oficial', { signal: AbortSignal.timeout(4000) });
    const j = await r.json(); const v = Number(j.promedio || j.precio);
    if (v > 1) tasa = { v, t: Date.now(), fuente: 'BCV' };
  } catch (e) { console.error('[pagomovil] tasa:', e.message); tasa.t = Date.now() - 2.5 * 3600e3; }   // reintenta en 30 min, sin frenar la página
}
export async function tasaBs() { if (Date.now() - tasa.t > 3 * 3600e3) await actualizar(); return tasa.v; }
export const enBs = (cents, t) => Math.round(cents / 100 * t * 100) / 100;
