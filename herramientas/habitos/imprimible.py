"""PDF imprimible + guía rápida (HTML → Chrome headless). Uso: python3 imprimible.py"""
import calendar, datetime as dt, subprocess, pathlib

Y = 2027
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
LET = "LMMJVSD"
COLS = ["#7c5cff", "#ff4fd8", "#22d3ee"]
OUT = pathlib.Path(__file__).parent
CSS = """
@page{size:A4 landscape;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter','Arial',sans-serif;color:#1b1640;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.pg{width:297mm;height:210mm;padding:11mm 12mm;page-break-after:always;position:relative;background:#f8f6ff;overflow:hidden}
.pg:last-child{page-break-after:auto}
.top{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:5mm}
h1{font-size:30px;font-weight:800;letter-spacing:-.5px}
h1 span{color:var(--c)}
.sub{font-size:11px;color:#77738f}
table{border-collapse:collapse;width:100%;table-layout:fixed;background:#fff}
td,th{border:1px solid #e3def5;text-align:center;font-size:9px;height:7.2mm}
th{background:#1b1640;color:#fff;font-weight:700;height:5.2mm}
th.we{color:#ff9ceb}
td.h{text-align:left;padding-left:2mm;width:58mm}
th.h{width:58mm;text-align:left;padding-left:2mm}
td.m,th.m{width:11mm}
.row-mood td{height:7mm}
.foot{position:absolute;bottom:6mm;left:12mm;right:12mm;display:flex;justify-content:space-between;font-size:9px;color:#9a96b5}
.boxes{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:3mm;margin-top:4mm}
.box{background:#fff;border:1px solid #e3def5;border-radius:3mm;padding:2mm 3mm;height:24mm;font-size:9px;font-weight:700;color:var(--c)}
.pill{display:inline-block;background:var(--c);color:#fff;font-weight:800;border-radius:99px;padding:1.5mm 4mm;font-size:11px}
"""

def mes(m):
    c = COLS[(m - 1) % 3]; dim = calendar.monthrange(Y, m)[1]
    head = "".join(f'<th class="{"we" if dt.date(Y,m,d).weekday()>=5 else ""}">{LET[dt.date(Y,m,d).weekday()]}<br>{d}</th>' for d in range(1, dim + 1))
    rows = "".join('<tr><td class="h"></td><td class="m"></td>' + "<td></td>" * dim + '<td class="m"></td></tr>' for _ in range(13))
    mood = '<tr class="row-mood"><td class="h" style="font-weight:700;color:#0e7490">Mi ánimo (😍 😊 😐 😞 😫)</td><td class="m"></td>' + "<td></td>" * dim + '<td class="m"></td></tr>'
    return f"""<section class="pg" style="--c:{c}">
<div class="top"><div><span class="pill">{m:02d}</span><h1>{MESES[m-1]} <span>{Y}</span></h1></div>
<div class="sub">Colorea la casilla cada día que cumplas · Meta = días al mes · Al final cuenta tus ✓</div></div>
<table><tr><th class="h">Mis hábitos</th><th class="m">Meta</th>{head}<th class="m">Total</th></tr>{rows}{mood}</table>
<div class="boxes"><div class="box">¿Qué me salió bien?</div><div class="box">¿Qué me costó más?</div><div class="box">¿Qué me hizo fallar y cómo lo arreglo?</div><div class="box">El próximo mes quiero sentir…</div></div>
<div class="foot"><span>Mi {Y} en Hábitos</span><span>Pixelia · pixeliadigital.app</span></div></section>"""

def portada():
    return f"""<section class="pg" style="--c:#7c5cff;background:linear-gradient(135deg,#1b1640,#3b2a8f 55%,#7c5cff);color:#fff;display:flex;flex-direction:column;justify-content:center;padding:0 24mm">
<div style="font-size:15px;letter-spacing:4px;opacity:.8">VERSIÓN IMPRIMIBLE</div>
<div style="font-size:74px;font-weight:900;line-height:1;margin:6mm 0">Mi {Y}<br>en Hábitos ✨</div>
<div style="font-size:18px;opacity:.9;max-width:170mm">Pequeños hábitos, un año distinto. Imprime el mes que vas a empezar, pégalo donde lo veas y colorea cada día que cumplas.</div>
<div style="margin-top:12mm;display:flex;gap:4mm;font-size:13px">{''.join(f'<span style="background:rgba(255,255,255,.14);border-radius:99px;padding:2mm 5mm">{t}</span>' for t in ['12 meses','Mis metas','Mi año en píxeles','Ánimo diario','Reflexión mensual'])}</div>
<div class="foot" style="color:rgba(255,255,255,.6)"><span>Uso personal</span><span>Pixelia · pixeliadigital.app</span></div></section>"""

def metas():
    filas = "".join(f'<tr><td style="font-size:20px;font-weight:900;color:#ff4fd8;width:14mm">{i}</td><td style="height:22mm"></td><td></td><td></td></tr>' for i in (1, 2, 3))
    hab = "".join(f'<tr><td style="color:#7c5cff;font-weight:800;width:14mm">{i}</td><td style="height:8.4mm"></td><td></td><td></td></tr>' for i in range(1, 11))
    return f"""<section class="pg" style="--c:#ff4fd8"><div class="top"><h1>Mis metas grandes de <span>{Y}</span> 🚀</h1><div class="sub">Pocas, claras y con un hábito que te acerque cada día</div></div>
<table><tr><th>#</th><th>Mi meta</th><th>¿Por qué me importa?</th><th>¿Qué hábito me acerca?</th></tr>{filas}</table>
<div style="height:5mm"></div><table><tr><th>#</th><th>Hábito que voy a seguir</th><th>Categoría (salud, dinero, mente…)</th><th>Días al mes</th></tr>{hab}</table>
<div class="foot"><span>Mi {Y} en Hábitos</span><span>Pixelia · pixeliadigital.app</span></div></section>"""

def pixeles():
    head = "".join(f"<th>{d}</th>" for d in range(1, 32))
    rows = ""
    for m in range(1, 13):
        dim = calendar.monthrange(Y, m)[1]
        rows += f'<tr><td class="h" style="width:24mm;font-weight:700">{MESES[m-1]}</td>' + "".join("<td></td>" if d <= dim else '<td style="background:#ecebf3"></td>' for d in range(1, 32)) + "</tr>"
    ley = "".join(f'<span style="display:inline-flex;align-items:center;gap:2mm;margin-right:6mm"><i style="width:5mm;height:5mm;border-radius:1mm;background:{c};display:inline-block;border:1px solid #ccc"></i>{t}</span>'
                  for c, t in [("#7c5cff", "😍 Genial"), ("#22d3ee", "😊 Bien"), ("#fbbf24", "😐 Normal"), ("#ff8a3d", "😞 Bajón"), ("#ff4fd8", "😫 Agotada")])
    return f"""<section class="pg" style="--c:#22d3ee"><div class="top"><h1>Mi año en <span>píxeles</span> 🎨</h1><div class="sub">Pinta cada día del color de cómo te sentiste. En diciembre vas a ver tu año entero.</div></div>
<table><tr><th class="h" style="width:24mm">Mes</th>{head}</tr>{rows}</table>
<div style="margin-top:5mm;font-size:11px">{ley}</div>
<div class="foot"><span>Mi {Y} en Hábitos</span><span>Pixelia · pixeliadigital.app</span></div></section>"""

def pdf(html, name):
    p = OUT / f"_{name}.html"; p.write_text(f"<!doctype html><meta charset=utf-8><style>{CSS}</style>{html}", encoding="utf-8")
    subprocess.run(["google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={OUT/name}", p.as_uri()], check=True, capture_output=True)
    print("ok", name)

pdf(portada() + metas() + "".join(mes(m) for m in range(1, 13)) + pixeles(), f"Mi-{Y}-en-Habitos-IMPRIMIBLE.pdf")

# ---------- guía rápida ----------
G = """
<style>@page{size:A4;margin:0}.g{width:210mm;height:297mm;padding:16mm 16mm;page-break-after:always;background:#f8f6ff;position:relative}
.g h2{font-size:26px;font-weight:900;margin-bottom:2mm}.g h3{font-size:14px;color:#7c5cff;margin:6mm 0 2mm}.g p,.g li{font-size:11.5px;line-height:1.6}
.g ol,.g ul{padding-left:6mm}.tip{background:#fff;border-left:4px solid #ff4fd8;border-radius:2mm;padding:3mm 4mm;margin-top:3mm;font-size:11px}
.lv{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm;margin-top:2mm}.lv div{background:#fff;border-radius:3mm;padding:3mm;font-size:10.5px;border:1px solid #e3def5}
.lv b{display:block;font-size:13px}</style>
<section class="g"><div style="background:linear-gradient(135deg,#1b1640,#7c5cff);color:#fff;border-radius:5mm;padding:9mm 9mm"><div style="letter-spacing:3px;font-size:11px;opacity:.8">GUÍA RÁPIDA</div>
<div style="font-size:34px;font-weight:900;line-height:1.1;margin-top:2mm">Mi 2027 en Hábitos ✨</div><div style="opacity:.85;margin-top:2mm;font-size:13px">Empiezas en 2 minutos. Aquí tienes todo lo que necesitas saber.</div></div>
<h3>📦 QUÉ TRAE TU DESCARGA</h3><ul>
<li><b>Mi-2027-en-Habitos.xlsx</b> — tu tracker (Excel o Google Sheets). Es el que vas a usar.</li>
<li><b>EJEMPLO-lleno.xlsx</b> — el mismo archivo con 3 meses ya llenos para que veas cómo se ve.</li>
<li><b>IMPRIMIBLE.pdf</b> — por si prefieres papel: 12 meses, metas y tu año en píxeles.</li></ul>
<h3>🚀 EMPIEZA EN 3 PASOS</h3><ol>
<li><b>Pestaña «Inicio»:</b> escribe tus hábitos (ya hay 7 de ejemplo: cámbialos o bórralos), elige la categoría y cuántos días al mes quieres cumplir cada uno.</li>
<li><b>Pestaña del mes:</b> cada día toca la casilla del hábito que cumpliste y elige <b>✓</b> (o escribe una x). Abajo marca tu ánimo con una carita.</li>
<li><b>Pestaña «Mi Año»:</b> mira tu avance mes a mes, tu racha récord, tu mejor mes y en qué área de tu vida vas mejor.</li></ol>
<div class="tip">💡 No llenes 15 hábitos el primer mes. Con 3 a 5 es más fácil no soltarlos. Cuando ya te salgan solos, agrega otro.</div>
<h3>🔥 RACHAS, NIVELES Y MENSAJES</h3>
<p>La <b>racha</b> cuenta los días seguidos que cumples un hábito, y continúa aunque cambie el mes. El <b>nivel</b> se calcula según tu ritmo (lo que llevas comparado con lo que deberías llevar a esta altura del mes):</p>
<div class="lv"><div><b>🌱 Semilla</b>menos del 30%</div><div><b>🚶 En camino</b>30% a 55%</div><div><b>🔥 Constante</b>55% a 80%</div><div><b>🚀 Imparable</b>80% o más</div></div>
<p style="margin-top:3mm">En «¿Cómo voy?» cada hábito te dice si vas a buen ritmo, cuántos días te faltan o si ya cumpliste la meta. El día de hoy se ilumina en celeste.</p>
</section>
<section class="g"><h2>📱 En el celular y en Google Sheets</h2>
<h3>GOOGLE SHEETS (recomendado para el celular)</h3><ol>
<li>Entra a <b>drive.google.com</b> desde la computadora o la app de Drive.</li>
<li>Toca <b>Nuevo → Subir archivo</b> y elige <b>Mi-2027-en-Habitos.xlsx</b>.</li>
<li>Ábrelo y ve a <b>Archivo → Guardar como Hojas de cálculo de Google</b>.</li>
<li>Listo: ábrelo desde la app de <b>Google Sheets</b> en tu teléfono y marca tus días donde estés.</li></ol>
<div class="tip">¿Te gustan las casillas de verificación? En Google Sheets selecciona los días de un mes y ve a <b>Insertar → Casilla de verificación</b>. También cuentan para tus % y rachas.</div>
<h3>EXCEL</h3><p>Ábrelo con doble clic. En el celular usa la app gratuita de <b>Microsoft Excel</b>. Si aparece «Habilitar edición», tócalo.</p>
<h3>❓ PREGUNTAS FRECUENTES</h3><ul>
<li><b>¿Puedo cambiar un hábito a mitad de año?</b> Sí. Cámbialo en «Inicio» y se actualiza en todos los meses. Si solo quieres cambiarlo en un mes, escríbelo encima en la pestaña de ese mes.</li>
<li><b>¿Por qué un mes dice «⏳ Pronto»?</b> Porque todavía no llega. Se activa solo el día 1.</li>
<li><b>¿Sirve para 2028?</b> Sí: en «Inicio» cambia el año, borra tus ✓ y las fechas se acomodan solas.</li>
<li><b>Se me borró una fórmula.</b> Usa deshacer (Ctrl+Z) o vuelve a descargar el archivo desde tu correo de compra.</li>
<li><b>¿Puedo compartirlo?</b> Es para tu uso personal. Si a alguien le gusta, ¡recomiéndale la tienda! 💜</li></ul>
<div class="tip" style="border-color:#7c5cff">¿Dudas? Escríbenos por Telegram desde el enlace «💬 Soporte» de <b>pixeliadigital.app</b>. Respondemos con gusto.</div>
</section>"""
p = OUT / "_guia.html"; p.write_text(f"<!doctype html><meta charset=utf-8><style>{CSS}</style>{G}", encoding="utf-8")
subprocess.run(["google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={OUT/'Guia-rapida.pdf'}", p.as_uri()], check=True, capture_output=True)
print("ok guia")
