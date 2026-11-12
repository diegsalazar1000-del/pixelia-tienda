// Diseño de la invitación gratis (lo usan el creador /invitacion y la página que reciben /i/<id>)
window.INVITA = {
  TIPOS: {
    asado: { e: '🔥', n: 'Asado / parrilla', bg: 'linear-gradient(160deg,#ffe2c4,#ffb38a)', t: 'Nos vamos de parrilla' },
    cumple: { e: '🎂', n: 'Cumpleaños', bg: 'linear-gradient(160deg,#ffe0f0,#ffb3d6)', t: 'Celebremos un año más' },
    reunion: { e: '🥂', n: 'Reunión', bg: 'linear-gradient(160deg,#e6e0ff,#b9adff)', t: 'Nos reunimos' },
    baby: { e: '🍼', n: 'Baby shower', bg: 'linear-gradient(160deg,#e0f4ff,#ffe0ef)', t: 'Viene en camino' },
    quince: { e: '👑', n: '15 años', bg: 'linear-gradient(160deg,#fff1d6,#f7c6e8)', t: 'Mis quince años' },
    boda: { e: '💍', n: 'Boda', bg: 'linear-gradient(160deg,#fffaf0,#f0e2c8)', t: 'Nos casamos' },
    grado: { e: '🎓', n: 'Graduación', bg: 'linear-gradient(160deg,#e3ecff,#c4d4ff)', t: '¡Me gradúo!' },
    fiesta: { e: '🎉', n: 'Fiesta', bg: 'linear-gradient(160deg,#fff4c4,#ffc8a8)', t: 'Hay fiesta' },
  },
  esc: (s) => String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]),
  fecha(f) {
    if (!f) return 'Fecha por definir';
    const d = new Date(f + 'T12:00'); if (isNaN(d)) return INVITA.esc(f);
    const s = d.toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'long' }); return s.charAt(0).toUpperCase() + s.slice(1);
  },
  html(d, demo) {
    const T = INVITA.TIPOS[d.tipo] || INVITA.TIPOS.fiesta, e = INVITA.esc;
    return `<div class="prev" style="background:${T.bg}">
      <div class="e">${T.e}</div><h3>${T.t}</h3>
      <h2>${e(d.titulo) || (demo ? 'Nombre de tu evento' : '')}</h2>
      <p>📅 <b>${INVITA.fecha(d.fecha)}</b>${d.hora ? ' · 🕓 ' + e(d.hora) : ''}</p>
      <p>📍 ${e(d.lugar) || (demo ? 'El lugar' : '')}</p>
      ${d.msj ? `<p class="q">“${e(d.msj)}”</p>` : ''}
      ${d.host ? `<p style="margin-top:12px;font-size:14px">Te espera: <b>${e(d.host)}</b></p>` : ''}
    </div>`;
  },
};
