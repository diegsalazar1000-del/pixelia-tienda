// ¿Qué hace la gente al llegar? (Diego 10-nov: muchas visitas y nadie descarga → medir antes de cambiar).
// Manda eventos sin datos personales: vio (la página cargó de verdad), s5/s15/s45 (segundos mirándola),
// mitad (bajó a la mitad), boton (tocó un botón o enlace). El servidor cuenta 1 por persona por día.
(function () {
  try {
    var s = document.currentScript, k = (s && s.getAttribute('data-k')) || '';
    if (!k) { var m = location.pathname.match(/^\/p\/([a-z0-9-]+)/); k = m ? m[1] : (location.pathname.replace(/\//g, '') || 'inicio'); }
    k = k.toLowerCase().replace(/[^a-z0-9-]/g, '').slice(0, 40); if (!k) return;
    var hechos = {};
    var ev = function (e) {
      if (hechos[e]) return; hechos[e] = 1;
      var o = { k: k, e: e };
      if (e === 'vio') { try { o.tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (x) {} o.wd = navigator.webdriver ? 1 : 0; o.tc = ('ontouchstart' in window || navigator.maxTouchPoints > 0) ? 1 : 0; o.sw = screen.width || 0; }
      var b = JSON.stringify(o);
      try { if (navigator.sendBeacon) navigator.sendBeacon('/api/vista', new Blob([b], { type: 'application/json' })); else fetch('/api/vista', { method: 'POST', headers: { 'content-type': 'application/json' }, body: b, keepalive: true }); } catch (x) {}
    };
    var arrancar = function () {
      ev('vio');
      var seg = 0;   // solo cuenta el tiempo con la página a la vista
      var t = setInterval(function () {
        if (document.visibilityState !== 'visible') return; seg++;
        if (seg === 5) ev('s5'); if (seg === 15) ev('s15'); if (seg === 45) { ev('s45'); clearInterval(t); }
      }, 1000);
      addEventListener('scroll', function () {
        var h = document.documentElement.scrollHeight - innerHeight;
        if (h > 200 && scrollY / h >= 0.5) ev('mitad');
      }, { passive: true });
      document.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('a,button,[onclick],.btn')) ev('boton'); }, true);
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', arrancar); else arrancar();
  } catch (x) {}
})();
