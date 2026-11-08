"""Reel del regalo "Reto 30 Días" (fórmula de Diego: molestia → "ya no tienes que hacer esto" → magia → gratis).
Usa las capturas de capturas/ (las hace capturar.sh con LibreOffice) y las letras de fonts/ (Inter, OFL), así corre
igual en la sesión de Claude que en el contenedor del estudio.
  python3 reel.py salida.mp4 [--dur 3.4,1.6,7.2,3.8] [--audio audio.wav] [--poster poster.jpg]
--dur = segundos de cada escena (molestia, "ya no tienes que…", la hoja, gratis); voz.py los ajusta a la voz."""
import sys, json, subprocess, shutil, tempfile, pathlib
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
W, H, FPS = 1080, 1920, 24
F = lambda s, w="Bold": ImageFont.truetype(str(HERE / "fonts" / f"Inter-{w}.otf"), int(s))
ORANGE, PINK, INK, TEAL, YEL = (255, 107, 61), (255, 79, 163), (35, 26, 61), (20, 184, 166), (255, 217, 102)
PEACH_T = (255, 177, 153)

HOOK = ("¿Anotas tus metas", "y a la semana", "ya ni te acuerdas?")
LIBRETA_T = "Metas de esta semana"
LIBRETA = ["Ir al gym", "Trabajar 5 horas en lo mío", "Leer 10 páginas", "Ahorrar", "Dormir temprano"]
SELLO = ("OLVIDADO", "a los 5 días")

# ---------- geometría de la hoja (se detecta sola en la captura vacía) ----------
lleno = Image.open(HERE / "capturas" / "lleno.png").convert("RGB")
vacio = Image.open(HERE / "capturas" / "vacio.png").convert("RGB")
DATOS = json.load(open(HERE / "capturas" / "datos.json"))
def es(p, c, tol=30): return all(abs(a - b) <= tol for a, b in zip(p, c))
Wd, Hd = vacio.size
XB = next(x for x in range(Wd // 20, Wd // 2) if es(vacio.getpixel((x, int(Hd * 0.6))), ORANGE))  # columna de los días
X0 = XB - 4
X1 = max(x for x in range(Wd // 2, Wd) if vacio.getpixel((x, int(Hd * 0.6)))[0] < 252 or vacio.getpixel((x, int(Hd * 0.6)))[2] < 252) + 4
col_or = [y for y in range(int(Hd * 0.35), Hd) if es(vacio.getpixel((XB + 6, y)), ORANGE) or es(vacio.getpixel((XB + 6, y)), (232, 80, 31))]
DAY0, DAYN = col_or[0], col_or[-1] + 1      # primer y último píxel de los 30 días
ROW = (DAYN - DAY0) / 30
ink = [y for y in range(int(Hd * 0.2), DAY0) if es(vacio.getpixel((XB + 6, y)), INK, 12)]
HDR = (ink[0], DAY0 - int(ROW * 1.1))       # desde "MIS RETOS" hasta antes de la línea de ayuda (incluye ¿cómo lo mido?, meta, totales)

def tira(img):
    a = img.crop((X0, HDR[0], X1, HDR[1])); b = img.crop((X0, DAY0, X1, DAYN))
    s = Image.new("RGB", (X1 - X0, a.height + b.height), "white"); s.paste(a, (0, 0)); s.paste(b, (0, a.height)); return s, a.height
full, hh = tira(lleno); empty, _ = tira(vacio)
# arriba de la tira: el resumen del vacío (sin totales) hasta que termine de llenarse
SC = 1000 / full.width
full = full.resize((1000, round(full.height * SC)), Image.LANCZOS); empty = empty.resize(full.size, Image.LANCZOS)
HH = round(hh * SC)
fila_y = lambda n: HH + round((n - 1) * ROW * SC)   # y de arriba de la fila del día n
DIAS = len(DATOS)

def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def bg(g):
    for y in range(0, H, 4):
        k = y / H; g.rectangle([0, y, W, y + 4], fill=(int(20 + 30 * k), int(14 + 6 * k), int(36 + 40 * k)))
def center(g, y, txt, f, fill, stroke=0, sc=None):
    g.text((W / 2, y), txt, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=sc)

def libreta(img, t, dim=0.0):
    g = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 140, 600, 940, 1520
    g.rounded_rectangle([x0 + 14, y0 + 18, x1 + 14, y1 + 18], 26, fill=(10, 8, 20))
    g.rounded_rectangle([x0, y0, x1, y1], 26, fill=(252, 249, 236))
    for y in range(y0 + 160, y1 - 30, 100): g.line([(x0 + 30, y), (x1 - 30, y)], fill=(170, 200, 230), width=3)
    g.line([(x0 + 120, y0 + 20), (x0 + 120, y1 - 20)], fill=(240, 150, 150), width=3)
    for k in range(7): g.ellipse([x0 + 40, y0 + 80 + k * 130, x0 + 70, y0 + 110 + k * 130], fill=(40, 30, 60))
    g.text((x0 + 150, y0 + 70), LIBRETA_T, font=F(50, "BoldItalic"), fill=(30, 60, 140))
    fi = F(46, "MediumItalic")
    for i, it in enumerate(LIBRETA):
        y = y0 + 220 + i * 100
        g.text((x0 + 150, y), it, font=fi, fill=(30, 60, 140), anchor="lm")
        p = ease((t - 0.45 * D[0] - i * 0.2) / 0.35)   # tachado progresivo
        if p > 0:
            w = g.textlength(it, font=fi)
            g.line([(x0 + 140, y + 4), (x0 + 140 + (w + 30) * p, y - 6)], fill=(220, 40, 40), width=9)
    ts = 0.75 * D[0]
    if t > ts:  # sello
        a = ease((t - ts) / 0.25); s = 1.6 - 0.6 * a
        st = Image.new("RGBA", (620, 170), (0, 0, 0, 0)); sg = ImageDraw.Draw(st)
        sg.rounded_rectangle([6, 6, 614, 164], 18, outline=(220, 40, 40, int(255 * a)), width=10)
        sg.text((310, 62), SELLO[0], font=F(76, "Black"), fill=(220, 40, 40, int(255 * a)), anchor="mm")
        sg.text((310, 128), SELLO[1], font=F(40, "Bold"), fill=(220, 40, 40, int(255 * a)), anchor="mm")
        st = st.resize((int(620 * s), int(170 * s))).rotate(-12, expand=True)
        img.paste(st, (W // 2 - st.width // 2, 1210 - st.height // 2), st)
    if dim: img.paste(Image.new("RGB", img.size, (0, 0, 0)), (0, 0), Image.new("L", img.size, int(255 * dim)))

def frame(t):
    img = Image.new("RGB", (W, H)); g = ImageDraw.Draw(img); bg(g)
    t1, t2, t3 = D[0], D[0] + D[1], D[0] + D[1] + D[2]
    if t < t2:  # 1) la molestia + 2) "ya no tienes que hacer esto"
        libreta(img, t, dim=0.6 * ease((t - t1) / 0.3) if t > t1 else 0)
        g = ImageDraw.Draw(img)
        center(g, 200, HOOK[0], F(80, "Black"), "white")
        center(g, 300, HOOK[1], F(80, "Black"), "white")
        center(g, 400, HOOK[2], F(80, "Black"), PEACH_T)
        if t > t1:
            a = ease((t - t1) / 0.35); y = 1010 + int(60 * (1 - a))
            center(g, y - 70, "Ya no tienes que", F(96, "Black"), "white", 6, INK)
            center(g, y + 50, "hacer esto.", F(124, "Black"), ORANGE, 6, INK)
    elif t < t3:  # 3) la magia: la hoja se llena sola (con ✓ y con números)
        k = t - t2; dur = D[2]
        llenado = max(0.5, dur - 2.2)
        d = min(DIAS, int(max(0, k - 0.4) / llenado * DIAS) + (1 if k > 0.4 else 0))
        sheet = empty.copy()
        if d:
            sheet.paste(full.crop((0, HH, full.width, fila_y(d + 1))), (0, HH))
            if d >= DIAS: sheet.paste(full.crop((0, 0, full.width, HH)), (0, 0))   # al final aparecen los totales
        x = DATOS[d - 1] if d else {"dia": 0, "racha": 0, "pct": 0}
        center(g, 110, "Márcalo con ✓ o escribe cuánto hiciste", F(46, "Bold"), PEACH_T)
        cards = [("DÍA", f"{x['dia']} de 30", TEAL), ("RACHA", f"{x['racha']} días" if x["racha"] != 1 else "1 día", ORANGE), ("AVANCE", f"{x['pct']}%", PINK)]
        bw = 300
        for i, (lab, val, colr) in enumerate(cards):
            x0 = 60 + i * (bw + 30)
            g.rounded_rectangle([x0, 180, x0 + bw, 350], 28, fill="white")
            g.rounded_rectangle([x0, 180, x0 + bw, 234], 28, fill=colr); g.rectangle([x0, 208, x0 + bw, 234], fill=colr)
            g.text((x0 + bw / 2, 207), lab, font=F(30, "Bold"), fill="white", anchor="mm")
            g.text((x0 + bw / 2, 296), val, font=F(56, "Black"), fill=INK, anchor="mm")
        g.rounded_rectangle([60, 380, W - 60, 416], 18, outline=(255, 255, 255), width=3)
        if x["pct"]: g.rounded_rectangle([64, 384, 64 + int((W - 128) * x["pct"] / 100), 412], 16, fill=ORANGE)
        top = 450; vis = min(sheet.height, H - top - 30)
        card = Image.new("RGB", (sheet.width + 20, vis + 20), "white"); card.paste(sheet.crop((0, 0, sheet.width, vis)), (10, 10))
        img.paste(card, (W // 2 - card.width // 2, top))
        if k > llenado + 0.5:   # mensaje de la hoja
            a = ease((k - llenado - 0.5) / 0.35); s = 0.7 + 0.3 * a
            bwid, bh = int(940 * s), int(150 * s); bx = (W - bwid) // 2; by = 1600
            g.rounded_rectangle([bx, by, bx + bwid, by + bh], 40, fill=INK, outline=ORANGE, width=6)
            center(g, by + bh / 2 - 22 * s, "Mitad del reto.", F(52 * s, "Black"), "white")
            center(g, by + bh / 2 + 34 * s, "El lunes ya no te gana.", F(46 * s, "Bold"), PEACH_T)
    else:  # 4) gratis + llamada a la acción
        k = t - t3; a = ease(k / 0.4); p = D[3] / 3.8
        center(g, 380, "GRATIS", F(230 * (0.6 + 0.4 * a), "Black"), ORANGE, 8, INK)
        center(g, 560, "Reto 30 Días · Google Sheets y Excel", F(48, "Bold"), "white")
        if k > 0.5 * p:
            g.rounded_rectangle([90, 700, W - 90, 920], 46, fill="white")
            center(g, 770, "Comenta", F(64, "Bold"), INK); center(g, 860, "RETO", F(110, "Black"), PINK)
        if k > 1.1 * p:
            center(g, 1060, "o descárgalo en", F(50, "Medium"), (220, 215, 240))
            center(g, 1140, "pixeliadigital.app/reto", F(70, "Black"), "white")
            center(g, 1220, "(link en el perfil)", F(44, "Medium"), (220, 215, 240))
        if k > 1.8 * p:
            g.rounded_rectangle([140, 1400, W - 140, 1560], 40, fill=ORANGE)
            center(g, 1450, "Síguenos: cada semana", F(52, "Bold"), "white"); center(g, 1515, "un truco nuevo", F(52, "Bold"), "white")
    return img

D = [float(x) for x in arg("--dur", "3.4,1.6,7.2,3.8").split(",")]
def render(out, audio=None, poster=None):
    tmp = tempfile.mkdtemp(); T = sum(D)
    for i in range(int(T * FPS)): frame(i / FPS).save(f"{tmp}/{i:04d}.jpg", quality=88)
    if poster: frame(D[0] + D[1] + D[2] - 0.5).save(poster, quality=85)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/%04d.jpg"]
    if audio: cmd += ["-i", audio, "-c:a", "aac", "-b:a", "160k", "-shortest"]
    subprocess.run(cmd + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], check=True)
    shutil.rmtree(tmp); print("ok", out, "escenas:", D)

if __name__ == "__main__":
    render(sys.argv[1], arg("--audio"), arg("--poster"))
