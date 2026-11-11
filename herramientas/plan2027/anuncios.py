"""Imágenes de anuncio del Plan Financiero 2027 (3 conceptos × 4:5 y 9:16), dibujadas en HTML y capturadas con Chrome.
Uso: python3 herramientas/plan2027/anuncios.py [carpeta_salida]   (por defecto storage/anuncios/plan-financiero-2027/)
Sirve para todo el año: nada de "enero" ni fechas en el gancho principal."""
import sys, pathlib, asyncio
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[1] / "storage" / "anuncios" / "plan-financiero-2027"

CSS = """
*{margin:0;padding:0;box-sizing:border-box;font-family:Poppins,'Noto Color Emoji',sans-serif}
body{width:1080px;overflow:hidden;color:#14261f}
.bg{position:relative;width:1080px;background:linear-gradient(160deg,#0b3326 0%,#145c45 55%,#1f7a5a 100%);overflow:hidden}
.glow{position:absolute;border-radius:50%;filter:blur(60px);opacity:.45}
h1{color:#fff;font-weight:800;line-height:1.06;letter-spacing:-1px}
h1 b{color:#ffd23f}
.sub{color:#d7f5e8;font-weight:500}
.phone{background:#0d1512;border-radius:64px;padding:18px;box-shadow:0 40px 80px rgba(0,0,0,.45)}
.scr{background:#eef5f1;border-radius:48px;overflow:hidden}
.top{background:#145c45;color:#fff;padding:26px 28px 18px;font-weight:800;font-size:30px}
.pad{padding:22px}
.card{background:#fff;border-radius:22px;padding:20px;margin-bottom:16px;box-shadow:0 3px 10px rgba(0,0,0,.06)}
.kp{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.kp div{background:#f4fbf8;border-radius:16px;padding:14px}
.kp small{display:block;font-size:19px;color:#5d7a6e}.kp b{font-size:32px}
.split{display:flex;height:30px;border-radius:15px;overflow:hidden;margin-top:6px}
.leg{display:grid;grid-template-columns:1fr auto;gap:6px 12px;font-size:21px;margin-top:12px}
.dot{display:inline-block;width:16px;height:16px;border-radius:5px;margin-right:8px}
.chart{display:flex;align-items:flex-end;gap:8px;height:170px}
.chart div{flex:1;background:#7fd1ad;border-radius:8px 8px 0 0}.chart .m{background:#ffd23f}
.goal{background:#fff8dc;border-radius:16px;padding:16px;font-size:24px}
.cta{display:inline-block;background:#ffd23f;color:#14261f;font-weight:800;border-radius:24px;box-shadow:0 8px 0 #d9a800}
.url{color:#bfe9d6;font-weight:600}
.flow{display:flex;flex-direction:column;gap:18px}
.step{background:rgba(255,255,255,.1);border:2px solid rgba(255,255,255,.18);border-radius:26px;padding:20px 26px;color:#fff;font-size:40px;font-weight:700}
.step b{color:#ffd23f;font-size:52px}
.arrow{color:#ffd23f;font-size:40px;text-align:center;line-height:1}
.wa{background:#e9dccb;border-radius:40px;overflow:hidden}
.wah{background:#075e54;color:#fff;padding:24px 28px;font-size:30px;font-weight:700;display:flex;align-items:center;gap:16px}
.av{width:58px;height:58px;border-radius:50%;background:#ffd23f;display:flex;align-items:center;justify-content:center;font-size:32px}
.msgs{padding:26px;display:flex;flex-direction:column;gap:16px}
.b{max-width:80%;padding:16px 20px;border-radius:22px;font-size:32px;line-height:1.3;box-shadow:0 2px 3px rgba(0,0,0,.12)}
.in{background:#fff;align-self:flex-start;border-top-left-radius:6px}
.out{background:#dcf8c6;align-self:flex-end;border-top-right-radius:6px}
.b small{display:block;text-align:right;font-size:18px;color:#7a8a83;margin-top:4px}
.shot{background:#fff;border-radius:16px;padding:14px;margin-top:10px}
"""

def pantalla(esc=1.0):
    """Mini pantalla del plan (María, empleada, $500, meta fondo de emergencia $600 → octubre)."""
    return f"""<div class="scr" style="zoom:{esc}"><div class="top">📊 Plan 2027 de María</div><div class="pad">
<div class="card"><div class="kp"><div><small>Ganas al mes</small><b>$500</b></div><div><small>Ahorras al mes</small><b style="color:#16a34a">$61</b></div>
<div><small>Lo necesario</small><b>$365</b></div><div><small>Para diciembre</small><b style="color:#0284c7">$14</b></div></div></div>
<div class="card"><div class="split"><i style="width:73%;background:#1f7a5a"></i><i style="width:12%;background:#ffd23f"></i><i style="width:3%;background:#38bdf8"></i><i style="width:12%;background:#f472b6"></i></div>
<div class="leg"><span><span class="dot" style="background:#1f7a5a"></span>Lo necesario</span><b>$365</b><span><span class="dot" style="background:#ffd23f"></span>Ahorro y meta</span><b>$61</b>
<span><span class="dot" style="background:#f472b6"></span>Gustos y salidas</span><b>$60</b></div></div>
<div class="card"><div class="chart">{''.join(f'<div class="{"m" if i>=9 else ""}" style="height:{(i+1)/12*100}%"></div>' for i in range(12))}</div></div>
<div class="goal">🎯 Fondo de emergencia: lo cumples en <b>octubre</b> 🎉</div></div></div>"""

def calculo(alto):  # A: el número que engancha
    v = alto > 1400
    return f"""<div class="bg" style="height:{alto}px">
<div class="glow" style="width:600px;height:600px;background:#ffd23f;top:-200px;right:-200px;opacity:.25"></div>
<div style="position:absolute;left:70px;right:70px;top:{110 if v else 70}px"><h1 style="font-size:{82 if v else 74}px">¿Cuánto puedes <b>ahorrar</b> con lo que ganas?</h1>
<p class="sub" style="font-size:36px;margin-top:16px">Escribe tu sueldo y mira tu plan del año en 1 minuto</p></div>
<div class="flow" style="position:absolute;left:70px;width:500px;top:{560 if v else 500}px;{'' if v else 'zoom:.82'}">
<div class="step">Ganas<br><b>$500</b></div><div class="arrow">▼</div>
<div class="step">Ahorras<br><b>$61 al mes</b></div><div class="arrow">▼</div>
<div class="step">Tu meta<br><b>en octubre ✅</b></div></div>
<div class="phone" style="position:absolute;right:60px;top:{520 if v else 400}px;width:440px;transform:rotate(4deg)">{pantalla(.62)}</div>
<div style="position:absolute;left:70px;right:70px;bottom:{110 if v else 60}px;text-align:center"><span class="cta" style="font-size:42px;padding:26px 46px">📊 Haz tu plan en 1 minuto</span>
<p class="url" style="font-size:28px;margin-top:22px">pixeliadigital.app</p></div></div>"""

def problema(alto):  # B: el dolor de fin de mes
    v = alto > 1400
    return f"""<div class="bg" style="height:{alto}px">
<div class="glow" style="width:500px;height:500px;background:#dc2626;top:-160px;left:-160px;opacity:.3"></div>
<div style="position:absolute;left:70px;right:70px;top:{120 if v else 70}px"><h1 style="font-size:{88 if v else 80}px">¿Cobras y a los 15 días <b>ya no te queda nada?</b> 😩</h1>
<p class="sub" style="font-size:38px;margin-top:20px">No es que ganes poco. Es que nadie te enseñó a repartirlo.</p></div>
<div class="phone" style="position:absolute;left:50%;transform:translateX(-50%);top:{720 if v else 470}px;width:{560 if v else 400}px">{pantalla(.78 if v else .56)}</div>
<div style="position:absolute;left:70px;right:70px;bottom:{110 if v else 50}px;text-align:center"><span class="cta" style="font-size:42px;padding:26px 46px">👇 Arma tu plan mes a mes</span>
<p class="url" style="font-size:28px;margin-top:20px">Excel y Google Sheets · hecho con tus números</p></div></div>"""

def chat(alto):  # C: chat de WhatsApp (sirve todo el año)
    v = alto > 1400
    return f"""<div class="bg" style="height:{alto}px">
<div style="position:absolute;left:60px;right:60px;top:{110 if v else 50}px"><h1 style="font-size:{60 if v else 54}px;text-align:center">El mensaje que <b>todas</b> quieren mandar 👀</h1></div>
<div class="wa" style="position:absolute;left:60px;right:60px;top:{300 if v else 225}px;{'' if v else 'zoom:.86'}">
<div class="wah"><div class="av">👩</div>Caro 💛</div><div class="msgs">
<div class="b in">Amiga, ¿cómo hiciste para llegar a fin de mes <b>sin deudas</b>? 😳<small>7:42 p. m.</small></div>
<div class="b out">Me hice un plan mes a mes 🙌 Pongo lo que gano y me dice cuánto gastar y cuánto guardar<small>7:43 p. m. ✓✓</small></div>
<div class="b out" style="padding:12px;width:{560 if v else 470}px"><div class="shot">{pantalla(.5 if v else .42)}</div><small>7:43 p. m. ✓✓</small></div>
<div class="b in">¡Pásamelo YA! 😭🙏<small>7:43 p. m.</small></div></div></div>
<div style="position:absolute;left:60px;right:60px;bottom:{110 if v else 45}px;text-align:center"><span class="cta" style="font-size:40px;padding:24px 42px">📊 Haz el tuyo en 1 minuto</span></div></div>"""

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        for letra, fn in [("A", calculo), ("B", problema), ("C", chat)]:
            for nom, alto in [("4x5", 1350), ("9x16", 1920)]:
                await pg.set_viewport_size({"width": 1080, "height": alto})
                await pg.set_content(f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{fn(alto)}</body></html>")
                await pg.wait_for_timeout(300)
                await pg.screenshot(path=str(OUT / f"{letra}-{nom}.jpg"), type="jpeg", quality=90)
        await b.close()
    print("listo:", OUT)

asyncio.run(main())
