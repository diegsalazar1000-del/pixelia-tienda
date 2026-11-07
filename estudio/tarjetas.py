"""Tarjeta del CONSEJO DE LA SEMANA para Instagram/Facebook (1080x1350, colores Pixelia, sin emojis: el contenedor no tiene esa letra).
La tienda deja el pedido en data/ig-pendientes/<id>.json y aquí se dibuja storage/anuncios/ig-posts/<id>.jpg."""
import json, pathlib, re
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent
FONTS = HERE / "fonts"
W, H = 1080, 1350
VIO, PINK, CYAN, NAVY = (124, 92, 255), (255, 79, 216), (34, 211, 238), (23, 18, 58)

def f(w, s): return ImageFont.truetype(str(FONTS / f"Poppins-{w}.ttf"), s)
def limpio(t): return re.sub(r"[^\u0000-￿]|[☀-➿️]", "", str(t or "")).strip()

def wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def fondo():
    im = Image.new("RGB", (W, H), NAVY)
    px = im.load()
    for y in range(H):
        for x in range(0, W, 4):
            t = (x / W) * 0.35 + (y / H) * 0.65
            c = tuple(int(NAVY[i] * (1 - t) + (58, 42, 143)[i] * t) for i in range(3))
            for k in range(4):
                if x + k < W: px[x + k, y] = c
    glow = Image.new("L", (W, H), 0); g = ImageDraw.Draw(glow)
    g.ellipse((W - 520, H - 520, W + 260, H + 260), fill=120)
    from PIL import ImageFilter
    glow = glow.filter(ImageFilter.GaussianBlur(140))
    im.paste(Image.new("RGB", (W, H), VIO), (0, 0), glow)
    return im

def dibujar(p, out):
    im = fondo(); d = ImageDraw.Draw(im)
    x0 = 84
    d.rounded_rectangle((x0, 86, x0 + 360, 136), 25, fill=PINK)
    d.text((x0 + 180, 111), "CONSEJO DE LA SEMANA", font=f("Bold", 22), fill="white", anchor="mm")
    # titular grande
    tit = limpio(p.get("titular")); size = 78
    while True:
        ft = f("Bold", size); lines = wrap(d, tit, ft, W - 2 * x0)
        if len(lines) <= 3 or size <= 52: break
        size -= 4
    y = 180
    for ln in lines: d.text((x0, y), ln, font=ft, fill="white"); y += int(size * 1.12)
    y += 34
    # 3 puntos, centrados en el espacio libre
    fp = f("Medium", 38); cajas = []
    for t in [limpio(x) for x in (p.get("puntos") or [])][:3]:
        ls = wrap(d, t, fp, W - 2 * x0 - 160)[:3]; cajas.append((ls, max(150, 50 * len(ls) + 70)))
    total = sum(h for _, h in cajas) + 28 * (len(cajas) - 1)
    y = max(y, y + ((H - 240) - y - total) / 2)
    for i, (ls, hbox) in enumerate(cajas):
        d.rounded_rectangle((x0, y, W - x0, y + hbox), 34, fill=(255, 255, 255))
        col = [VIO, PINK, CYAN][i]
        d.ellipse((x0 + 30, y + hbox / 2 - 40, x0 + 110, y + hbox / 2 + 40), fill=col)
        d.text((x0 + 70, y + hbox / 2), str(i + 1), font=f("Bold", 42), fill="white", anchor="mm")
        ty = y + hbox / 2 - 50 * len(ls) / 2 + 2
        for ln in ls: d.text((x0 + 140, ty), ln, font=fp, fill=NAVY); ty += 50
        y += hbox + 28
    # cierre + marca
    c = limpio(p.get("cierre"))
    if c:
        fc = f("Bold", 34); w = d.textlength(c, font=fc)
        d.rounded_rectangle((x0, H - 200, x0 + w + 60, H - 136), 32, fill=PINK)
        d.text((x0 + 30, H - 168), c, font=fc, fill="white", anchor="lm")
    d.text((x0, H - 78), "pixelia", font=f("Bold", 44), fill="white", anchor="lm")
    lw = d.textlength("pixelia", font=f("Bold", 44)); d.rounded_rectangle((x0 + lw + 4, H - 100, x0 + lw + 16, H - 88), 3, fill=PINK)
    d.text((W - x0, H - 78), "pixeliadigital.app", font=f("Medium", 28), fill=(220, 214, 255), anchor="rm")
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=92)

def pendientes(pixelia):
    """Dibuja las tarjetas pedidas por la tienda. Devuelve cuántas hizo."""
    d = pixelia / "data" / "ig-pendientes"; n = 0
    for j in sorted(d.glob("*.json")) if d.exists() else []:
        try:
            p = json.loads(j.read_text()); dibujar(p, pixelia / "storage" / "anuncios" / "ig-posts" / f"{re.sub(r'[^0-9a-z-]', '', p['id'])}.jpg"); n += 1
        except Exception as e: print("tarjeta falló:", e, flush=True)
        j.unlink(missing_ok=True)
    return n

if __name__ == "__main__":
    import sys
    dibujar({"titular": "Empieza tu 2027 desde noviembre", "puntos": ["Elige solo 3 hábitos y escríbelos donde los veas", "Márcalos cada noche: 10 segundos y listo", "Si fallas un día, no rompas la racha dos días seguidos"],
             "cierre": "Guárdalo para enero"}, pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "tarjeta.jpg"))
