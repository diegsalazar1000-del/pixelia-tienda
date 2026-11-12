// Diseño de la invitación gratis (lo usan el creador /invitacion y la página que reciben /i/<id>)
window.INVITA = {
  TIPOS: {
    asado:   { e: '🔥', n: 'Parrilla', t: 'Nos vamos de parrilla', bg: 'linear-gradient(160deg,#ffe6c9,#ffb07a)', ink: '#3a1d0a', acc: '#d9480f', sobre: '#c2410c', lluvia: ['🔥', '🥩', '🌭', '🍺', '🌽'], font: "'Poppins',sans-serif" },
    cumple:  { e: '🎂', n: 'Cumpleaños', t: 'Celebremos un año más', bg: 'linear-gradient(160deg,#ffe3f1,#ffb3d6)', ink: '#3d0f2b', acc: '#d6336c', sobre: '#e64980', lluvia: ['🎈', '🎂', '🎉', '🎁', '✨'], font: "'Poppins',sans-serif" },
    reunion: { e: '🥂', n: 'Reunión', t: 'Nos reunimos', bg: 'linear-gradient(160deg,#ece8ff,#b9adff)', ink: '#1f1546', acc: '#5f3dc4', sobre: '#6741d9', lluvia: ['🥂', '✨', '🍕', '🎶'], font: "'Poppins',sans-serif" },
    baby:    { e: '🍼', n: 'Baby shower', t: 'Viene en camino', bg: 'linear-gradient(160deg,#e3f4ff,#ffe3ef)', ink: '#203047', acc: '#1c7ed6', sobre: '#74c0fc', lluvia: ['🍼', '🧸', '👶', '☁️', '💙', '💗'], font: "Georgia,serif" },
    quince:  { e: '👑', n: '15 años', t: 'Mis quince años', bg: 'linear-gradient(160deg,#fff3dc,#f7c6e8)', ink: '#3b1238', acc: '#ae3ec9', sobre: '#cc5de8', lluvia: ['👑', '✨', '💖', '🌸'], font: "Georgia,serif" },
    boda:    { e: '💍', n: 'Boda', t: 'Nos casamos', bg: 'linear-gradient(160deg,#fffbf3,#efe0c4)', ink: '#3a2e1f', acc: '#a67c37', sobre: '#c9a96e', lluvia: ['🤍', '💍', '🌿', '✨', '🕊️'], font: "Georgia,serif" },
    grado:   { e: '🎓', n: 'Graduación', t: '¡Me gradúo!', bg: 'linear-gradient(160deg,#e5edff,#c3d3ff)', ink: '#14244a', acc: '#364fc7', sobre: '#4263eb', lluvia: ['🎓', '⭐', '🎉', '📜'], font: "'Poppins',sans-serif" },
    fiesta:  { e: '🎉', n: 'Fiesta', t: 'Hay fiesta', bg: 'linear-gradient(160deg,#fff6c9,#ffc9a8)', ink: '#3a240a', acc: '#e8590c', sobre: '#f76707', lluvia: ['🎉', '🎊', '✨', '🎶', '🪩'], font: "'Poppins',sans-serif" },
  },
  // cómo se le dice a la parrilla en cada país (Diego 12-nov)
  ASADO: { VE: ['Parrilla', 'Nos vamos de parrilla'], AR: ['Asado', 'Nos vamos de asado'], UY: ['Asado', 'Nos vamos de asado'], PY: ['Asado', 'Nos vamos de asado'], CL: ['Asado', 'Nos vamos de asado'],
    CO: ['Asado', 'Hay asado'], BO: ['Churrasco', 'Hay churrasco'], MX: ['Carne asada', 'Hay carne asada'], PE: ['Parrillada', 'Hay parrillada'], EC: ['Parrillada', 'Hay parrillada'],
    ES: ['Barbacoa', 'Nos vamos de barbacoa'], DO: ['Barbacoa', 'Hay barbacoa'], PR: ['BBQ', 'Hay BBQ'], CR: ['Carne asada', 'Hay carne asada'], GT: ['Churrasco', 'Hay churrasco'],
    SV: ['Carne asada', 'Hay carne asada'], HN: ['Carne asada', 'Hay carne asada'], NI: ['Carne asada', 'Hay carne asada'], PA: ['Parrillada', 'Hay parrillada'], US: ['BBQ / parrilla', 'Hay parrillada'] },
  pais() {
    const z = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
    const m = { Caracas: 'VE', Buenos_Aires: 'AR', Argentina: 'AR', Montevideo: 'UY', Asuncion: 'PY', Santiago: 'CL', Bogota: 'CO', La_Paz: 'BO', Mexico: 'MX', Monterrey: 'MX', Tijuana: 'MX', Cancun: 'MX', Merida: 'MX', Chihuahua: 'MX', Hermosillo: 'MX', Lima: 'PE', Guayaquil: 'EC', Madrid: 'ES', Canary: 'ES', Santo_Domingo: 'DO', Puerto_Rico: 'PR', Costa_Rica: 'CR', Guatemala: 'GT', El_Salvador: 'SV', Tegucigalpa: 'HN', Managua: 'NI', Panama: 'PA', New_York: 'US', Chicago: 'US', Los_Angeles: 'US', Denver: 'US', Phoenix: 'US' };
    for (const k in m) if (z.includes(k)) return m[k];
    return 'VE';
  },
  tema(d) {   // tema del tipo + palabra del país para el asado
    const T = { ...(INVITA.TIPOS[d.tipo] || INVITA.TIPOS.fiesta) };
    if (d.tipo === 'asado') { const w = INVITA.ASADO[d.pais] || INVITA.ASADO.VE; T.n = w[0]; T.t = w[1]; }
    return T;
  },
  esc: (s) => String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]),
  fecha(f) {
    if (!f) return 'Fecha por definir';
    const d = new Date(f + 'T12:00'); if (isNaN(d)) return INVITA.esc(f);
    const s = d.toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'long' }); return s.charAt(0).toUpperCase() + s.slice(1);
  },
  faltan(f) { if (!f) return ''; const n = Math.round((new Date(f + 'T12:00') - new Date(new Date().toDateString() + ' 12:00')) / 864e5); return n > 1 ? `⏳ Faltan ${n} días` : n === 1 ? '⏳ ¡Es mañana!' : n === 0 ? '🎉 ¡Es hoy!' : ''; },
  html(d, demo) {
    const T = INVITA.tema(d), e = INVITA.esc;
    return `<div class="prev inv" style="background:${T.bg};color:${T.ink};--acc:${T.acc}">
      <div class="deco d1">${T.lluvia[0]}</div><div class="deco d2">${T.lluvia[1]}</div><div class="deco d3">${T.lluvia[2] || T.e}</div>
      <div class="e">${T.e}</div><h3 style="color:${T.acc}">${T.t}</h3>
      <h2 style="font-family:${T.font}">${e(d.titulo) || (demo ? 'Nombre de tu evento' : '')}</h2>
      <div class="lin" style="background:${T.acc}"></div>
      <p>📅 <b>${INVITA.fecha(d.fecha)}</b>${d.hora ? '<br>🕓 ' + e(d.hora) : ''}</p>
      <p>📍 ${e(d.lugar) || (demo ? 'El lugar' : '')}</p>
      ${d.msj ? `<p class="q">“${e(d.msj)}”</p>` : ''}
      ${d.host ? `<p class="host">Te espera <b>${e(d.host)}</b></p>` : ''}
      ${!demo && INVITA.faltan(d.fecha) ? `<div class="falta" style="background:${T.acc}">${INVITA.faltan(d.fecha)}</div>` : ''}
    </div>`;
  },
  // lluvia de emojis del tema
  lluvia(tipo, n = 26) {
    const T = INVITA.TIPOS[tipo] || INVITA.TIPOS.fiesta;
    for (let i = 0; i < n; i++) {
      const c = document.createElement('div'); c.className = 'cae'; c.textContent = T.lluvia[i % T.lluvia.length];
      c.style.left = Math.random() * 100 + 'vw'; c.style.fontSize = 18 + Math.random() * 22 + 'px';
      c.style.animationDuration = 2.4 + Math.random() * 2 + 's'; c.style.animationDelay = Math.random() * 1.2 + 's';
      document.body.appendChild(c); setTimeout(() => c.remove(), 5000);
    }
  },
  CSS: `.inv{position:relative;overflow:hidden;border-radius:26px;padding:34px 22px 28px;text-align:center;box-shadow:0 30px 60px rgba(0,0,0,.45)}
.inv .e{font-size:70px;animation:lat 2.4s ease-in-out infinite}
.inv h3{font:800 13px Poppins,sans-serif;letter-spacing:4px;text-transform:uppercase;margin-top:6px}
.inv h2{font-size:34px;line-height:1.08;margin:10px 0 12px;font-weight:800}
.inv .lin{width:60px;height:4px;border-radius:4px;margin:0 auto 14px;opacity:.7}
.inv p{margin:8px 0;font-size:17px;line-height:1.35}
.inv .q{font-style:italic;opacity:.85;margin-top:14px}
.inv .host{margin-top:14px;font-size:15px}
.inv .falta{display:inline-block;color:#fff;font:800 15px Poppins,sans-serif;padding:8px 16px;border-radius:999px;margin-top:14px;animation:lat 1.8s ease-in-out infinite}
.inv .deco{position:absolute;font-size:34px;opacity:.35;animation:flo 6s ease-in-out infinite}
.inv .d1{top:14px;left:16px}.inv .d2{top:18px;right:18px;animation-delay:-2s}.inv .d3{bottom:16px;right:22px;animation-delay:-4s}
@keyframes lat{0%,100%{transform:scale(1)}50%{transform:scale(1.08)}}
@keyframes flo{0%,100%{transform:translateY(0) rotate(-8deg)}50%{transform:translateY(-10px) rotate(8deg)}}
.cae{position:fixed;top:-50px;z-index:50;pointer-events:none;animation:caer linear forwards}
@keyframes caer{to{transform:translateY(110vh) rotate(540deg)}}`,
};
(function () { const st = document.createElement('style'); st.textContent = INVITA.CSS; document.head.appendChild(st); })();
