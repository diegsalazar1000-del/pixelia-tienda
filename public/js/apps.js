// 🧰 Herramientas gratis de Pixelia: piezas compartidas (medición, píxel, ventanita del correo, moneda)
(function () {
  const K = document.currentScript.dataset.k;          // racha | dinero | cobro | cuenta
  const ST = 'px_app_' + K;
  const PX = window.PX = {
    k: K,
    $: (id) => document.getElementById(id),
    load(def) { try { return Object.assign(def || {}, JSON.parse(localStorage.getItem(ST)) || {}); } catch { return def || {}; } },
    save(s) { try { localStorage.setItem(ST, JSON.stringify(s)); } catch {} },
    ev(e) { try { fetch('/api/vista', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ k: K, e }), keepalive: true }); } catch {} },
    px(n, extra) { try { fbq('trackCustom', n, Object.assign({ app: K }, extra || {})); } catch {} },
    // "También te puede servir": las otras apps (Diego 12-nov)
    APPS: { racha: ['🔥', 'Mi Racha de 30 días', '/racha'], dinero: ['💸', 'Mi mes en dinero', '/dinero'], invitacion: ['💌', 'Tu invitación bonita', '/invitacion'] },
    otras(el) {
      if (!el) return;
      el.innerHTML = '<p style="font-size:14px;color:#c9c2ee;margin:18px 0 8px;text-align:center">También te puede servir (gratis):</p>' +
        Object.entries(PX.APPS).filter(([k]) => k !== K).map(([k, [e, n, u]]) => `<a data-a="${k}" href="${u}?ref=${K}" style="display:flex;align-items:center;gap:12px;text-decoration:none;color:#fff;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:12px 14px;margin-top:8px"><span style="font-size:28px">${e}</span><b style="flex:1">${n}</b><span style="color:#ffb38a;font-size:20px">›</span></a>`).join('');
      el.querySelectorAll('a[data-a]').forEach((a) => a.addEventListener('click', () => { PX.ev('otra_' + a.dataset.a); PX.px('EligioApp', { desde: K, a: a.dataset.a, interes: PX.INTERES[a.dataset.a] }); }));
    },
    // interés de cada app → públicos separados en Meta (Diego 12-nov)
    INTERES: { racha: 'habitos-planners', dinero: 'finanzas', invitacion: 'interactivo-whatsapp' },
    // moneda: se adivina por la zona horaria; se puede cambiar
    MON: { USD: ['$', 'en-US'], VES: ['Bs', 'es-VE'], MXN: ['$', 'es-MX'], COP: ['$', 'es-CO'], PEN: ['S/', 'es-PE'], CLP: ['$', 'es-CL'], ARS: ['$', 'es-AR'], EUR: ['€', 'es-ES'], GTQ: ['Q', 'es-GT'], DOP: ['RD$', 'es-DO'], BOB: ['Bs', 'es-BO'], CRC: ['₡', 'es-CR'], UYU: ['$', 'es-UY'], PYG: ['₲', 'es-PY'], HNL: ['L', 'es-HN'] },
    monAdivina() {
      const z = (Intl.DateTimeFormat().resolvedOptions().timeZone || '');
      const m = { Mexico: 'MXN', Bogota: 'COP', Lima: 'PEN', Santiago: 'CLP', Buenos_Aires: 'ARS', Argentina: 'ARS', Madrid: 'EUR', Guatemala: 'GTQ', Santo_Domingo: 'DOP', La_Paz: 'BOB', Costa_Rica: 'CRC', Montevideo: 'UYU', Asuncion: 'PYG', Tegucigalpa: 'HNL' };
      for (const k in m) if (z.includes(k)) return m[k];
      return 'USD';   // Venezuela, Ecuador, Panamá, El Salvador, EE. UU.: dólares
    },
    fmt(n, mon) { const [s, loc] = PX.MON[mon] || PX.MON.USD; const dec = ['CLP', 'COP', 'PYG', 'ARS'].includes(mon) ? 0 : 2; return s + ' ' + Number(n || 0).toLocaleString(loc, { minimumFractionDigits: 0, maximumFractionDigits: dec }); },
    // ventanita del correo (una sola vez por app)
    pedirCorreo(titulo) {
      const s = PX.load(); if (s._correo || s._pidio) return; s._pidio = 1; PX.save(s); PX.ev('pidio');
      const d = document.createElement('div'); d.className = 'sheet on';
      d.innerHTML = `<div class="box"><h2>${titulo}</h2><p class="sub">Para más novedades, apps gratis e información, ingresa tu correo 💌 (y te llega un cupón de regalo 🎁).</p>
        <input id="pxEmail" type="email" placeholder="tu@correo.com" autocomplete="email" style="margin-top:14px">
        <label class="chk"><input type="checkbox" id="pxOk" checked> Acepto recibir novedades de Pixelia (puedes darte de baja cuando quieras).</label>
        <button class="btn" id="pxEnviar">Mantenerme informado 💌</button><div class="msg" id="pxMsg"></div><button class="x" id="pxNo">Ahora no</button></div>`;
      document.body.appendChild(d);
      d.querySelector('#pxNo').onclick = () => { d.remove(); PX.ev('nocorreo'); };
      d.querySelector('#pxEnviar').onclick = async () => {
        const msg = d.querySelector('#pxMsg'), b = d.querySelector('#pxEnviar');
        if (!d.querySelector('#pxOk').checked) { msg.textContent = 'Marca la casilla para poder escribirte 😊'; return; }
        b.disabled = true; msg.textContent = 'Enviando…';
        try {
          const r = await fetch('/api/regalo', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ email: d.querySelector('#pxEmail').value, regalos: [K], consent: true, tipo: PX.extra || '' }) });
          const j = await r.json(); if (!r.ok) throw new Error(j.error || 'Revisa tu correo');
          const s2 = PX.load(); s2._correo = 1; PX.save(s2); PX.ev('correo'); try { fbq('track', 'Lead', { content_name: K, content_category: PX.INTERES[K] }); } catch {} PX.px('CorreoApp', { interes: PX.INTERES[K] });
          msg.textContent = '💌 ¡Listo! Revisa tu correo.'; setTimeout(() => d.remove(), 2000);
        } catch (e) { msg.textContent = e.message; b.disabled = false; }
      };
    },
  };
  PX.ev(localStorage.getItem(ST) ? 'volvio' : 'abrio');
  setTimeout(() => PX.px('AbrioApp', { interes: PX.INTERES[K] }), 50);
  // ⏱️ cuánto se quedan (solo con la página a la vista) → píxel: TiempoApp {seg: 15|45|120}
  let seg = 0; const tt = setInterval(() => { if (document.visibilityState !== 'visible') return; seg++;
    if (seg === 15 || seg === 45 || seg === 120) { PX.px('TiempoApp', { seg, interes: PX.INTERES[K] }); if (seg === 120) { PX.ev('s120'); clearInterval(tt); } } }, 1000);
})();
