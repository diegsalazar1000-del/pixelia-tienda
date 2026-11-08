"""Reel del regalo "Reto 30 Días" (fórmula de Diego: molestia → "ya no tienes que hacer esto" → magia → gratis).
Necesita las capturas de la hoja hechas con LibreOffice (lleno y vacío, 200 dpi):
  python3 reel.py lleno.png vacio.png salida.mp4 [poster.jpg]
Sin audio a propósito: en Instagram se le pone un audio en tendencia al publicar (más alcance)."""
import sys, math, os, subprocess, shutil, tempfile
from PIL import Image, ImageDraw, ImageFont

LLENO, VACIO, OUT = sys.argv[1:4]; POSTER = sys.argv[4] if len(sys.argv) > 4 else None
W, H, FPS, T = 1080, 1920, 24, 15.0
FD = "/usr/share/fonts/opentype/inter/"
def F(s, w="Bold"): return ImageFont.truetype(f"{FD}Inter-{w}.otf", s)
ORANGE, PINK, INK, TEAL, CREAM = (255, 107, 61), (255, 79, 163), (35, 26, 61), (20, 184, 166), (255, 248, 241)

# --- hoja: encabezado de hábitos + 30 días (sin el resumen, lo animamos nosotros) ---
X0, X1 = 165, 1160
HDR = (542, 613); DAY_TOP = lambda n: 693 if n == 1 else round(743 + 37.17 * (n - 2)); DAY_END = 1838
def strip(img):
    a = img.crop((X0, HDR[0], X1, HDR[1])); b = img.crop((X0, DAY_TOP(1), X1, DAY_END))
    s = Image.new("RGB", (X1 - X0, a.height + b.height), "white"); s.paste(a, (0, 0)); s.paste(b, (0, a.height)); return s, a.height
full, hh = strip(Image.open(LLENO).convert("RGB")); empty, _ = strip(Image.open(VACIO).convert("RGB"))
SC = 1000 / full.width; full = full.resize((1000, round(full.height * SC)), Image.LANCZOS); empty = empty.resize(full.size, Image.LANCZOS)
row_y = lambda n: round((hh + DAY_TOP(n) - DAY_TOP(1)) * SC)   # y de arriba de la fila n en la tira escalada

# marcas reales del ejemplo (para que los contadores digan la verdad)
src = Image.open(LLENO).convert("RGB"); COLS = [400, 548, 696, 844, 992]
def marcado(n, c):
    y = (DAY_TOP(n) + (DAY_TOP(n + 1) if n < 30 else DAY_END)) // 2 + (12 if n == 1 else 0)
    p = src.getpixel((COLS[c], y)); return p[1] > 150 and p[0] < 90
M = [[marcado(n, c) for c in range(5)] for n in range(1, 31)]
DIAS = max(n for n in range(1, 31) if any(M[n - 1])) if any(any(r) for r in M) else 18
def stats(d):
    if d == 0: return 0, 0, 0
    tot = sum(sum(M[i]) for i in range(d)); pct = round(100 * tot / (5 * 30))
    r = 0
    for i in range(d - 1, -1, -1):
        if M[i][0]: r += 1
        else: break
    return d, pct, r

def ease(x): x = max(0, min(1, x)); return 1 - (1 - x) ** 3
def bg(g):
    for y in range(0, H, 4):
        k = y / H; g.rectangle([0, y, W, y + 4], fill=(int(20 + 30 * k), int(14 + 6 * k), int(36 + 40 * k)))
def center(g, y, txt, f, fill, stroke=0, sc=None):
    g.text((W / 2, y), txt, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=sc)

LIBRETA = ["Ir al gym", "Tomar 2 litros de agua", "Leer un libro al mes", "Ahorrar", "Dormir temprano"]
def libreta(img, t, dim=0.0):
    g = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 140, 560, 940, 1500
    g.rounded_rectangle([x0 + 14, y0 + 18, x1 + 14, y1 + 18], 26, fill=(10, 8, 20))
    g.rounded_rectangle([x0, y0, x1, y1], 26, fill=(252, 249, 236))
    for y in range(y0 + 160, y1 - 30, 100): g.line([(x0 + 30, y), (x1 - 30, y)], fill=(170, 200, 230), width=3)
    g.line([(x0 + 120, y0 + 20), (x0 + 120, y1 - 20)], fill=(240, 150, 150), width=3)
    for k in range(7): g.ellipse([x0 + 40, y0 + 80 + k * 130, x0 + 70, y0 + 110 + k * 130], fill=(40, 30, 60))
    g.text((x0 + 150, y0 + 70), "Propósitos 2026", font=F(54, "BoldItalic"), fill=(30, 60, 140))
    for i, it in enumerate(LIBRETA):
        y = y0 + 220 + i * 100
        g.text((x0 + 150, y), it, font=F(50, "MediumItalic"), fill=(30, 60, 140), anchor="lm")
        # tachado progresivo (empieza a los 1.4 s)
        p = ease((t - 1.4 - i * 0.22) / 0.35)
        if p > 0:
            w = g.textlength(it, font=F(50, "MediumItalic"))
            g.line([(x0 + 140, y + 4), (x0 + 140 + (w + 30) * p, y - 6)], fill=(220, 40, 40), width=9)
    if t > 2.5:  # sello "ABANDONADO"
        a = ease((t - 2.5) / 0.25); s = 1.6 - 0.6 * a
        st = Image.new("RGBA", (620, 170), (0, 0, 0, 0)); sg = ImageDraw.Draw(st)
        sg.rounded_rectangle([6, 6, 614, 164], 18, outline=(220, 40, 40, int(255 * a)), width=10)
        sg.text((310, 62), "ABANDONADO", font=F(70, "Black"), fill=(220, 40, 40, int(255 * a)), anchor="mm")
        sg.text((310, 128), "14 de febrero", font=F(40, "Bold"), fill=(220, 40, 40, int(255 * a)), anchor="mm")
        st = st.resize((int(620 * s), int(170 * s))).rotate(-12, expand=True)
        img.paste(st, (W // 2 - st.width // 2, 1180 - st.height // 2), st)
    if dim: img.paste(Image.new("RGB", img.size, (0, 0, 0)), (0, 0), Image.new("L", img.size, int(255 * dim)))

def frame(t):
    img = Image.new("RGB", (W, H)); g = ImageDraw.Draw(img); bg(g)
    if t < 4.6:  # 1) la molestia
        libreta(img, t, dim=0.55 * ease((t - 3.2) / 0.3) if t > 3.2 else 0)
        g = ImageDraw.Draw(img)
        center(g, 200, "¿Tus propósitos", F(86, "Black"), "white")
        center(g, 300, "se mueren en febrero?", F(86, "Black"), (255, 177, 153))
        if t > 3.2:  # 2) "ya no tienes que hacer esto"
            a = ease((t - 3.2) / 0.35); y = 980 + int(60 * (1 - a))
            center(g, y - 70, "Ya no tienes que", F(96, "Black"), "white", 6, INK)
            center(g, y + 50, "hacer esto.", F(120, "Black"), ORANGE, 6, INK)
    elif t < 12.0:  # 3) la magia: la hoja se llena sola
        k = (t - 4.6)
        d = min(DIAS, int(max(0, k - 0.6) / 5.2 * DIAS) + (1 if k > 0.6 else 0))
        sheet = empty.copy()
        if d:
            y = row_y(d + 1) if d < 30 else full.height
            sheet.paste(full.crop((0, 0, full.width, y)), (0, 0))
        dia, pct, racha = stats(d)
        center(g, 120, "Marca ✓ y la hoja hace el resto", F(54, "Bold"), (255, 177, 153))
        cards = [("DÍA", f"{dia} de 30", TEAL), ("🔥 RACHA".replace("🔥 ", ""), f"{racha} días" if racha != 1 else "1 día", ORANGE), ("AVANCE", f"{pct}%", PINK)]
        bw = 300
        for i, (lab, val, col) in enumerate(cards):
            x = 60 + i * (bw + 30)
            g.rounded_rectangle([x, 200, x + bw, 380], 28, fill="white")
            g.rounded_rectangle([x, 200, x + bw, 256], 28, fill=col); g.rectangle([x, 228, x + bw, 256], fill=col)
            g.text((x + bw / 2, 228), lab, font=F(30, "Bold"), fill="white", anchor="mm")
            g.text((x + bw / 2, 320), val, font=F(58, "Black"), fill=INK, anchor="mm")
        # barra del reto
        g.rounded_rectangle([60, 410, W - 60, 450], 20, fill=(255, 255, 255, 40), outline=(255, 255, 255), width=3)
        if pct: g.rounded_rectangle([64, 414, 64 + int((W - 128) * pct / 100 * 30 / 15) if False else 64 + int((W - 128) * pct / 100), 446], 18, fill=ORANGE)
        # hoja (se acerca un poco al final)
        z = 1 + 0.06 * ease((k - 5.8) / 1.2)
        sh = sheet.resize((int(sheet.width * z), int(sheet.height * z)), Image.LANCZOS)
        top = 490; vis = min(sh.height, H - top - 40)
        card = Image.new("RGB", (sh.width + 20, vis + 20), "white"); card.paste(sh.crop((0, 0, sh.width, vis)), (10, 10))
        img.paste(card, (W // 2 - card.width // 2, top))
        if k > 6.0:  # mensaje de la hoja
            a = ease((k - 6.0) / 0.35); s = 0.7 + 0.3 * a
            bwid, bh = int(940 * s), int(150 * s); bx = (W - bwid) // 2; by = 1500
            g.rounded_rectangle([bx, by, bx + bwid, by + bh], 40, fill=INK, outline=ORANGE, width=6)
            center(g, by + bh / 2 - 22 * s, "Mitad del reto.", F(int(52 * s), "Black"), "white")
            center(g, by + bh / 2 + 34 * s, "Febrero, tiembla. 😎".replace(" 😎", ""), F(int(46 * s), "Bold"), (255, 177, 153))
    else:  # 4) gratis + llamada a la acción
        k = t - 12.0; a = ease(k / 0.4)
        center(g, 380, "GRATIS", F(int(230 * (0.6 + 0.4 * a)), "Black"), ORANGE, 8, INK)
        center(g, 560, "Reto 30 Días · Google Sheets y Excel", F(48, "Bold"), "white")
        if k > 0.5:
            g.rounded_rectangle([90, 700, W - 90, 920], 46, fill="white")
            center(g, 770, "Comenta", F(64, "Bold"), INK)
            center(g, 860, "RETO", F(110, "Black"), PINK)
        if k > 1.1:
            center(g, 1060, "y descárgalo en", F(50, "Medium"), (220, 215, 240))
            center(g, 1140, "pixeliadigital.app/reto", F(70, "Black"), "white")
            center(g, 1220, "(link en el perfil)", F(44, "Medium"), (220, 215, 240))
        if k > 1.8:
            g.rounded_rectangle([140, 1400, W - 140, 1560], 40, fill=ORANGE)
            center(g, 1450, "Síguenos: cada semana", F(52, "Bold"), "white")
            center(g, 1515, "un truco nuevo", F(52, "Bold"), "white")
    return img

tmp = tempfile.mkdtemp()
for i in range(int(T * FPS)): frame(i / FPS).save(f"{tmp}/{i:04d}.jpg", quality=88)
if POSTER: frame(1.0 + 3.3).save(POSTER, quality=85)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/%04d.jpg", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], check=True)
shutil.rmtree(tmp); print("ok", OUT, "días:", DIAS)
