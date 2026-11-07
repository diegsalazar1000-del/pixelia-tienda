"""Cuento personalizado Pixelia: cuento.json → PDF tamaño Carta (portada, dedicatoria, páginas ilustradas, colorear, certificado).
Uso: python3 build.py cuento.json salida.pdf   (las ilustraciones son escenas con Noto Color Emoji, licencia OFL)."""
import json, sys, subprocess, pathlib, tempfile, html, random
from PIL import Image, ImageFilter, ImageOps, ImageChops

D = json.load(open(sys.argv[1], encoding="utf-8")); OUT = pathlib.Path(sys.argv[2]).resolve()
HERE = pathlib.Path(__file__).parent; TMP = pathlib.Path(tempfile.mkdtemp())
CHROME = next((c for c in ("google-chrome", "chromium", "chromium-browser") if subprocess.run(["which", c], capture_output=True).returncode == 0), "chromium")
e = html.escape
PAL = [("#ffe8f3", "#ff7ab8"), ("#e6f6ff", "#3aa6ff"), ("#fff4d6", "#ffb020"), ("#eafbf0", "#2fbf71"), ("#f1ecff", "#8a6cff")]
CIELO = {"dia": "linear-gradient(#bfe8ff,#eaf7ff 60%,#c9f2c9 60%)", "noche": "linear-gradient(#1c1f5a,#3b3a8f 60%,#22415a 60%)"}

def escena_html(p, w, h, k):
    """Escena: cielo + suelo, personajes grandes al frente, adornos repartidos."""
    rnd = random.Random(k * 7 + 3)
    extras = "".join(f'<span style="position:absolute;left:{rnd.randint(4, 84)}%;top:{rnd.randint(4, 40)}%;font-size:{rnd.randint(int(h*.08), int(h*.13))}px;transform:rotate({rnd.randint(-15, 15)}deg)">{x}</span>' for x in p.get("extra", []) for _ in range(2 if x in "⭐✨" else 1))
    pj = p.get("escena", [])
    b = min(h, w * .62); tam = [b * .34, b * .30, b * .26][:len(pj)]
    chars = "".join(f'<span style="font-size:{int(t)}px;line-height:1;filter:drop-shadow(0 {int(h*.02)}px {int(h*.02)}px rgba(0,0,0,.25))">{x}</span>' for x, t in zip(pj, tam))
    return (f'<div style="position:relative;width:{w}px;height:{h}px;border-radius:{int(h*.06)}px;overflow:hidden;background:{CIELO.get(p.get("cielo", "dia"), CIELO["dia"])}">'
            f'{extras}<div style="position:absolute;left:0;right:0;bottom:{int(h*.06)}px;display:flex;justify-content:center;align-items:flex-end;gap:{int(b*.03)}px">{chars}</div></div>')

def png(html_body, w, h, name):
    f = TMP / f"{name}.html"
    f.write_text(f"<!doctype html><meta charset=utf-8><style>body{{margin:0;font-family:'Noto Color Emoji'}}</style>{html_body}", encoding="utf-8")
    p = TMP / f"{name}.png"
    subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--window-size={w},{h}", f"--screenshot={p}", f.as_uri()], capture_output=True, timeout=60)
    return p

def para_colorear(src, dst):
    """Dibujo para colorear: se reduce la escena a pocas zonas de color y se trazan sus bordes en negro (líneas continuas)."""
    im = Image.open(src).convert("RGB").filter(ImageFilter.MedianFilter(7))
    q = im.quantize(colors=10, method=Image.Quantize.MEDIANCUT).convert("L")
    a = q; b = ImageChops.offset(q, 1, 0); c = ImageChops.offset(q, 0, 1)
    ed = ImageChops.lighter(ImageChops.difference(a, b), ImageChops.difference(a, c)).point(lambda v: 255 if v > 0 else 0)
    ed = ed.filter(ImageFilter.MaxFilter(5))
    ImageOps.invert(ed).convert("RGB").save(dst)

n, edad, nombre = D["nino"], D.get("edad"), e(D["nino"])
pags = D["paginas"]
imgs, lineas = [], []
for k, p in enumerate(pags):
    sp = png(escena_html(p, 1500, 1150, k), 1500, 1150, f"e{k}"); imgs.append(sp)
    if k in (0, 3, 5, len(pags) - 1):
        clean = dict(p, cielo="dia")
        hc = escena_html(clean, 1500, 1850, k).replace("linear-gradient(#bfe8ff,#eaf7ff 60%,#c9f2c9 60%)", "#fff").replace("filter:drop-shadow", "x-f:").replace(f"border-radius:{int(1850*.06)}px", "border-radius:0")
        lp = png(hc, 1500, 1850, f"c{k}")
        para_colorear(lp, TMP / f"l{k}.png"); lineas.append((k, TMP / f"l{k}.png"))

CSS = """@page{size:Letter;margin:0}*{box-sizing:border-box}body{margin:0;font-family:'Lora',serif;color:#2b2140;-webkit-print-color-adjust:exact;print-color-adjust:exact}
@font-face{font-family:'Lora';src:url('LORA')}@font-face{font-family:'Pop';src:url('POP')}
.pg{width:8.5in;height:11in;page-break-after:always;position:relative;overflow:hidden;padding:.7in}
.pg:last-child{page-break-after:auto}
h1,h2,.pop{font-family:'Pop',sans-serif}
.txt{font-size:27px;line-height:1.6;margin:0}
.num{position:absolute;bottom:.35in;left:0;right:0;text-align:center;font:600 13px 'Pop';color:#9a8fb5}
.img{width:100%;border-radius:28px;display:block}
.nombre{color:var(--c)}"""
CSS = CSS.replace("LORA", (HERE / "Lora-Medium.ttf").as_uri()).replace("POP", (HERE / "Poppins-Bold.ttf").as_uri())
H = []
# portada
H.append(f"""<section class="pg" style="background:radial-gradient(circle at 70% 20%,#ffd84d55,transparent 40%),linear-gradient(160deg,#1c1f5a,#5b3fe0 60%,#ff7ab8);color:#fff;padding:.8in">
<div class="pop" style="font-size:18px;letter-spacing:4px;opacity:.85">UN CUENTO ÚNICO PARA</div>
<div class="pop" style="font-size:96px;line-height:1;margin:10px 0 22px;color:#ffd84d">{nombre}</div>
<h1 style="font-size:46px;line-height:1.1;margin:0 0 .4in">{e(D['titulo'])}</h1>
<img class="img" src="{imgs[1].as_uri()}" style="border:8px solid #fff3;box-shadow:0 30px 60px #0006">
<div class="pop" style="position:absolute;bottom:.6in;left:.8in;right:.8in;display:flex;justify-content:space-between;font-size:15px;opacity:.9"><span>Escrito solo para {nombre}</span><span>pixelia</span></div></section>""")
# dedicatoria
H.append(f"""<section class="pg" style="display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;background:#fffaf2">
<div style="font-size:70px">💌</div><div class="pop" style="font-size:16px;letter-spacing:3px;color:#8a6cff;margin:20px 0">DEDICATORIA</div>
<div style="font-size:30px;line-height:1.5;max-width:6in;font-style:italic">{e(D['dedicatoria'])}</div>
<div style="margin-top:.6in;font-size:15px;color:#9a8fb5">Este cuento no existe en ninguna otra casa del mundo.<br>Fue creado una sola vez, solo para ti.</div></section>""")
# páginas del cuento
for k, p in enumerate(pags):
    bg, c = PAL[k % len(PAL)]
    t = e(p["texto"]).replace(e(n), f'<b class="nombre">{nombre}</b>').replace(e(D.get("mascota", "")), f'<b>{e(D.get("mascota", ""))}</b>') if D.get("mascota") else e(p["texto"]).replace(e(n), f'<b class="nombre">{nombre}</b>')
    H.append(f"""<section class="pg" style="background:{bg};--c:{c}"><img class="img" src="{imgs[k].as_uri()}" style="margin-bottom:.4in;box-shadow:0 18px 40px rgba(43,33,64,.18)">
<p class="txt">{t}</p><div class="num">{k + 1}</div></section>""")
# final
H.append(f"""<section class="pg" style="background:linear-gradient(#1c1f5a,#3b3a8f);color:#fff;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center">
<div style="font-size:120px">🌙</div><h2 style="font-size:40px;max-width:6.5in;line-height:1.25">{e(D['frase_final'])}</h2><div class="pop" style="font-size:18px;opacity:.7;margin-top:20px">FIN</div></section>""")
# para colorear
for k, lp in lineas:
    H.append(f"""<section class="pg" style="background:#fff"><div class="pop" style="font-size:28px;color:#8a6cff;margin-bottom:6px">🖍️ ¡Colorea tu aventura, {nombre}!</div>
<div style="font-size:15px;color:#7a7096;margin-bottom:.3in">Escena de la página {k + 1}</div><img src="{lp.as_uri()}" style="width:100%;max-height:8.4in;object-fit:contain;border:3px dashed #d9d0f5;border-radius:24px"></section>""")
# certificado
H.append(f"""<section class="pg" style="background:#fffaf2;padding:.6in"><div style="border:10px double #ffb020;border-radius:30px;height:100%;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:.5in">
<div style="font-size:90px">🏅</div><div class="pop" style="font-size:20px;letter-spacing:4px;color:#ff7ab8">CERTIFICADO OFICIAL</div>
<div style="font-size:24px;margin:20px 0 6px">Se reconoce a</div><div class="pop" style="font-size:72px;color:#5b3fe0">{nombre}</div>
<div style="font-size:24px;max-width:5.8in;margin-top:14px">como protagonista y héroe de <b>«{e(D['titulo'])}»</b>, por su valentía, su corazón bueno y su imaginación sin límites.</div>
<div style="margin-top:.6in;display:flex;gap:1.4in;font-size:15px;color:#7a7096"><div>__________________<br>Firma de mamá o papá</div><div>__________________<br>Fecha</div></div></div></section>""")
doc = TMP / "cuento.html"; doc.write_text(f"<!doctype html><meta charset=utf-8><style>{CSS}</style>" + "".join(H), encoding="utf-8")
subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={OUT}", doc.as_uri()], check=True, capture_output=True, timeout=120)
print("ok", OUT)
