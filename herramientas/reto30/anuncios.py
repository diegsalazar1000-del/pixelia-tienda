"""Imágenes A/B/C del Reto 30 Días para anuncios (4x5, 9x16, 1x1), con los nombres que usa la campaña del bot.
Uso: python3 anuncios.py carpeta_salida"""
import sys, pathlib
from PIL import Image, ImageDraw, ImageFont
HERE = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
F = lambda s, w="Bold": ImageFont.truetype(str(HERE / "fonts" / f"Inter-{w}.otf"), int(s))
ORANGE, PINK, INK, PEACH_T = (255, 107, 61), (255, 79, 163), (35, 26, 61), (255, 177, 153)
SIZES = {"4x5": (1080, 1350), "9x16": (1080, 1920), "1x1": (1080, 1080)}

lleno = Image.open(HERE / "capturas" / "lleno.png").convert("RGB")
W0, H0 = lleno.size
def es(p, c, t=30): return all(abs(a - b) <= t for a, b in zip(p, c))
XB = next(x for x in range(W0 // 20, W0 // 2) if es(lleno.getpixel((x, int(H0 * 0.6))), ORANGE))
ink = [y for y in range(int(H0 * 0.2), int(H0 * 0.5)) if es(lleno.getpixel((XB + 6, y)), INK, 12)]
X1 = max(x for x in range(W0 // 2, W0) if min(lleno.getpixel((x, int(H0 * 0.6)))) < 250) + 4
HOJA = lleno.crop((XB - 4, ink[0], X1, int(H0 * 0.62)))   # retos, totales y los primeros días llenos

CONCEPTOS = {
    "A": (["¿Anotas tus metas", "y a la semana", "ya ni te acuerdas?"], [False, False, True], "Ya no tienes que hacer esto · GRATIS"),
    "B": (["Trabajar 5 horas.", "Leer 10 páginas.", "Tomar 8 vasos."], [False, False, False], "Márcalo con ✓ o escribe cuánto hiciste"),
    "C": (["GRATIS:", "tu Reto 30 Días", "en Google Sheets"], [True, False, False], "Tu racha y tu avance se calculan solos"),
}
def bg(g, W, H):
    for y in range(0, H, 4):
        k = y / H; g.rectangle([0, y, W, y + 4], fill=(int(20 + 30 * k), int(14 + 6 * k), int(36 + 40 * k)))
for letra, (lineas, acento, pie) in CONCEPTOS.items():
    for nom, (W, H) in SIZES.items():
        img = Image.new("RGB", (W, H)); g = ImageDraw.Draw(img); bg(g, W, H)
        fs = 74 if nom != "1x1" else 62; y = 70 if nom == "1x1" else (120 if nom == "4x5" else 260)
        for ln, ac in zip(lineas, acento):
            g.text((W / 2, y), ln, font=F(fs, "Black"), fill=ORANGE if ac else "white", anchor="mt"); y += fs + 16
        g.text((W / 2, y + 10), pie, font=F(38 if nom != "1x1" else 32, "Bold"), fill=PEACH_T, anchor="mt"); y += 80
        foot = 150 if nom != "9x16" else 330
        avail_h = H - y - foot - 20; sw = W - 120
        h = HOJA.resize((sw, int(HOJA.height * sw / HOJA.width)), Image.LANCZOS)
        if h.height > avail_h: h = h.crop((0, 0, sw, avail_h))
        fr = Image.new("RGB", (h.width + 16, h.height + 16), "white"); fr.paste(h, (8, 8)); img.paste(fr, ((W - fr.width) // 2, y))
        by = H - foot + 20 if nom != "9x16" else H - foot + 40
        g.rounded_rectangle([140, by, W - 140, by + 100], 50, fill=PINK)
        g.text((W / 2, by + 50), "Comenta RETO · link en el perfil", font=F(40, "Black"), fill="white", anchor="mm")
        img.save(OUT / f"{letra}-{nom}.jpg", quality=90)
print("ok", sorted(p.name for p in OUT.glob("*.jpg")))
