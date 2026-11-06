"""Bonos del planner: pack de stickers PNG (fondo transparente) y 4 portadas de color."""
import math, pathlib, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont
import planner as P

HERE = pathlib.Path(__file__).parent
ST = HERE / "out" / "Stickers"; PO = HERE / "out" / "Portadas"
for d in (ST, PO): shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
F = lambda w, s: ImageFont.truetype(str(P.FONTS / f"Poppins-{w}.ttf"), s)
LORA = lambda s: ImageFont.truetype(str(HERE / "Lora-MediumItalic.ttf"), s)
C = {"terracota": "#C8775B", "salvia": "#8FA58C", "mostaza": "#D9A85B", "rosa": "#D9A3A0", "arena": "#E8DCCB", "tinta": "#4A3F35", "papel": "#FFFDF9"}
S = 2  # escala para nitidez
n = 0
def save(img, name):
    global n; n += 1
    img.save(ST / f"{n:02d}-{name}.png")

def label(text, bg, fg="#FFFDF9"):
    f = F("Medium", 34 * S); w = int(f.getlength(text)) + 64 * S; h = 74 * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=bg)
    d.text((w / 2, h / 2), text, font=f, fill=fg, anchor="mm"); return im

labels = [("Importante", "terracota"), ("Pagar", "mostaza"), ("Cumpleaños", "rosa"), ("Cita médica", "salvia"), ("Examen", "terracota"),
          ("Entrega", "mostaza"), ("Gym", "salvia"), ("Reunión", "tinta"), ("Viaje", "salvia"), ("Día libre", "rosa"), ("¡Lo logré!", "terracota"),
          ("Recordar", "mostaza"), ("Llamar", "salvia"), ("Compras", "rosa"), ("Ahorro", "mostaza"), ("Lectura", "salvia"),
          ("Autocuidado", "rosa"), ("Clase", "tinta"), ("Pendiente", "arena"), ("Hecho", "salvia"), ("Feriado", "terracota"), ("Aniversario", "rosa")]
for t, col in labels:
    save(label(t, C[col], C["tinta"] if col == "arena" else C["papel"]), "etiqueta-" + t.lower().replace(" ", "-").replace("¡", "").replace("!", "").replace("ñ", "n").replace("é", "e").replace("ó", "o").replace("í", "i"))

# Números de día 1–31
for k in range(1, 32):
    s = 96 * S; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([2, 2, s - 3, s - 3], fill=[C["terracota"], C["salvia"], C["mostaza"], C["rosa"]][k % 4])
    d.text((s / 2, s / 2), str(k), font=F("Bold", 40 * S), fill=C["papel"], anchor="mm"); save(im, f"dia-{k:02d}")

# Washi tape
for i, col in enumerate(["terracota", "salvia", "mostaza", "rosa", "arena", "tinta"]):
    w, h = 420 * S, 64 * S; im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    base = Image.new("RGBA", (w, h), C[col]); base.putalpha(215); im.alpha_composite(base)
    for x in range(0, w, 34 * S): d.line([(x, 0), (x + 30 * S, h)], fill=(255, 253, 249, 70), width=8 * S)
    # bordes "rasgados"
    mask = Image.new("L", (w, h), 255); md = ImageDraw.Draw(mask)
    for y in range(0, h, 8 * S):
        md.polygon([(0, y), (6 * S, y + 4 * S), (0, y + 8 * S)], fill=0); md.polygon([(w, y), (w - 6 * S, y + 4 * S), (w, y + 8 * S)], fill=0)
    im.putalpha(Image.composite(im.getchannel("A"), Image.new("L", (w, h), 0), mask)); save(im, f"washi-{col}")

# Notas adhesivas
for col in ["mostaza", "rosa", "salvia", "arena"]:
    s = 300 * S; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(0, 0), (s, 0), (s, s - 60 * S), (s - 60 * S, s), (0, s)], fill=C[col])
    d.polygon([(s, s - 60 * S), (s - 60 * S, s - 60 * S), (s - 60 * S, s)], fill=(0, 0, 0, 40))
    for y in range(70 * S, s - 40 * S, 44 * S): d.line([(30 * S, y), (s - 80 * S if y > s - 110 * S else s - 30 * S, y)], fill=(255, 253, 249, 150), width=2 * S)
    save(im, f"nota-{col}")

# Iconos sencillos
def star(col):
    s = 140 * S; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); cx = cy = s / 2
    pts = [(cx + (s * .46 if k % 2 == 0 else s * .2) * math.sin(k * math.pi / 5), cy - (s * .46 if k % 2 == 0 else s * .2) * math.cos(k * math.pi / 5)) for k in range(10)]
    d.polygon(pts, fill=C[col]); return im
def heart(col):
    s = 140 * S; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(s / 2 + s * .028 * 16 * math.sin(t) ** 3, s * .45 - s * .028 * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)))
           for t in [i * 2 * math.pi / 200 for i in range(200)]]
    d.polygon(pts, fill=C[col]); return im
def sun(col):
    s = 160 * S; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = s / 2
    for k in range(12):
        a = k * math.pi / 6; d.line([(c + s * .3 * math.cos(a), c + s * .3 * math.sin(a)), (c + s * .46 * math.cos(a), c + s * .46 * math.sin(a))], fill=C[col], width=9 * S)
    d.ellipse([c - s * .22, c - s * .22, c + s * .22, c + s * .22], fill=C[col]); return im
def flower(col):
    s = 150 * S; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = s / 2
    for k in range(6):
        a = k * math.pi / 3; x, y = c + s * .22 * math.cos(a), c + s * .22 * math.sin(a); r = s * .2
        d.ellipse([x - r, y - r, x + r, y + r], fill=C[col])
    d.ellipse([c - s * .14, c - s * .14, c + s * .14, c + s * .14], fill=C["mostaza"] if col != "mostaza" else C["terracota"]); return im
for fn, cols in [(star, ["mostaza", "terracota"]), (heart, ["rosa", "terracota"]), (sun, ["mostaza", "terracota"]), (flower, ["rosa", "salvia"])]:
    for col in cols: save(fn(col), f"{fn.__name__}-{col}")

# Frases cortas
for t, col in [("Tú puedes", "terracota"), ("Paso a paso", "salvia"), ("Respira", "rosa"), ("Hoy sí", "mostaza")]:
    f = LORA(54 * S); w = int(f.getlength(t)) + 70 * S; h = 110 * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=24 * S, fill=C["papel"], outline=C[col], width=4 * S)
    d.text((w / 2, h / 2), t, font=f, fill=C[col], anchor="mm"); save(im, "frase-" + t.lower().replace(" ", "-").replace("ú", "u").replace("í", "i"))
print("stickers:", n)

# ---------- 4 portadas ----------
schemes = {"Terracota": ("#C8775B", "#E8DCCB", "#8FA58C", "#D9A85B"), "Salvia": ("#8FA58C", "#E1E8DC", "#C8775B", "#D9A85B"),
           "Mostaza": ("#D9A85B", "#F1E3C6", "#8FA58C", "#C8775B"), "Rosa": ("#D9A3A0", "#F2E0DC", "#8FA58C", "#D9A85B")}
from reportlab.lib.colors import HexColor
orig = (P.TERRA, P.SAND, P.SAGE, P.MUSTARD)
for name, (a, b, c2, d2) in schemes.items():
    P.TERRA, P.SAND, P.SAGE, P.MUSTARD = map(HexColor, (a, b, c2, d2))
    for mode, (W, H), dpi in [("Tablet", (1024, 768), 144), ("Movil", (600, 1300), 144)]:
        pdf = HERE / "out" / f"_c_{name}_{mode}.pdf"
        pl = P.Planner(pdf, W, H, mode.lower() if mode == "Tablet" else "movil"); pl.cover(); pl.page("indice", nav=False); pl.c.save()
        (PO / mode).mkdir(exist_ok=True)
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", "-singlefile", str(pdf), str(PO / mode / f"Portada-{name}")], check=True)
        pdf.unlink()
P.TERRA, P.SAND, P.SAGE, P.MUSTARD = orig
print("portadas ok")
