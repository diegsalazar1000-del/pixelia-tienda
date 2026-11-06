"""Generador de creativos para Meta Ads (Pixelia).
Crea, para un producto, imágenes en 1:1, 4:5 y 9:16 con varios enfoques de texto, y un reel animado 9:16.
Uso: python3 creativos.py producto.json
"""
import json, math, subprocess, sys, pathlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONTS = pathlib.Path("/usr/share/fonts/truetype/google-fonts")
LORA = pathlib.Path("/home/claude/productos/planner2027")
def F(w, s): return ImageFont.truetype(str(FONTS / f"Poppins-{w}.ttf"), int(s))
def LI(s): return ImageFont.truetype(str(LORA / "Lora-MediumItalic.ttf"), int(s))
def LM(s): return ImageFont.truetype(str(LORA / "Lora-Medium.ttf"), int(s))

PAL = {"bg": "#F3EADF", "bg2": "#FBF6EF", "ink": "#4A3F35", "muted": "#8C7D6D", "terra": "#C8775B", "sage": "#8FA58C",
       "sand": "#E8DCCB", "mustard": "#D9A85B", "paper": "#FFFDF9", "dark": "#2E2823"}
SIZES = {"feed-1x1": (1080, 1080), "feed-4x5": (1080, 1350), "story-9x16": (1080, 1920)}


def wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def fit_text(draw, text, kind, maxw, maxh, start, minsize=30):
    s = start
    while s > minsize:
        f = (LM if kind == "serif" else lambda z: F("Bold", z))(s)
        lines = wrap(draw, text, f, maxw)
        if len(lines) * s * 1.12 <= maxh: return f, lines, s
        s -= 4
    f = (LM if kind == "serif" else lambda z: F("Bold", z))(minsize)
    return f, wrap(draw, text, f, maxw), minsize

def device(canvas, img, x, y, w, radius=None, pad=None, shadow=True):
    radius = radius or int(w * 0.045); pad = pad or int(w * 0.03)
    r = w / img.width; img = img.resize((int(w), int(img.height * r)), Image.LANCZOS)
    W, H = img.width + 2 * pad, img.height + 2 * pad
    if shadow:
        m = Image.new("L", canvas.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([x + 10, y + 34, x + W + 10, y + H + 34], radius=radius, fill=120)
        m = m.filter(ImageFilter.GaussianBlur(max(10, w // 28)))
        canvas.paste(Image.new("RGBA", canvas.size, (70, 50, 30, 255)), (0, 0), m)
    ImageDraw.Draw(canvas).rounded_rectangle([x, y, x + W, y + H], radius=radius, fill=PAL["dark"])
    mm = Image.new("L", img.size, 0); ImageDraw.Draw(mm).rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=int(radius * .55), fill=255)
    canvas.paste(img.convert("RGBA"), (x + pad, y + pad), mm)
    return W, H

def pill(d, x, y, text, font, bg, fg, padx=34, h=None, center=False):
    tw = d.textlength(text, font=font); h = h or int(font.size * 2.1); w = int(tw + 2 * padx)
    if center: x = int(x - w / 2)
    d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=bg)
    d.text((x + w / 2, y + h / 2), text, font=font, fill=fg, anchor="mm")
    return w, h

def price_tag(d, x, y, price, compare, scale=1.0, center=False):
    f1, f2 = F("Bold", 64 * scale), F("Medium", 34 * scale)
    t1 = f"${price:g}"; t2 = f"${compare:g}"
    w1 = d.textlength(t1, font=f1); w2 = d.textlength(t2, font=f2); gap = 18 * scale
    total = w1 + gap + w2
    if center: x = x - total / 2
    d.text((x, y), t1, font=f1, fill=PAL["ink"])
    d.text((x + w1 + gap, y + 22 * scale), t2, font=f2, fill=PAL["muted"])
    ly = y + 22 * scale + f2.size * 0.62
    d.line([(x + w1 + gap - 4, ly), (x + w1 + gap + w2 + 4, ly)], fill=PAL["terra"], width=max(3, int(4 * scale)))
    return total


def make_image(P, angle, size_name, imgs, out):
    W, H = SIZES[size_name]
    cv = Image.new("RGBA", (W, H), PAL["bg"]); d = ImageDraw.Draw(cv)
    # fondo decorativo
    d.ellipse([W * .62, -W * .22, W * 1.28, W * .44], fill=PAL["sand"])
    d.ellipse([W * .80, H - W * .30, W * 1.25, H + W * .15], fill=PAL["sage"])
    M = 72
    story = size_name.startswith("story")
    # zona de texto
    ty = 250 if story else 70
    tag = angle.get("etiqueta")
    if tag:
        _, th = pill(d, M, ty, tag, F("Medium", 28), PAL["terra"], PAL["paper"]); ty += th + 26
    head_h = H * (0.20 if not story else 0.17)
    f, lines, s = fit_text(d, angle["titular"], "serif", W - 2 * M, head_h, 92 if not story else 104)
    for i, ln in enumerate(lines):
        d.text((M, ty + i * s * 1.12), ln, font=f, fill=PAL["ink"])
    ty += len(lines) * s * 1.12 + 18
    sub = angle.get("subtitulo")
    if sub:
        fs = F("Regular", 34 if not story else 40)
        for i, ln in enumerate(wrap(d, sub, fs, W - 2 * M)[:2]):
            d.text((M, ty + i * fs.size * 1.35), ln, font=fs, fill=PAL["muted"])
        ty += 2 * fs.size * 1.35
    # zona de imagen
    bottom_band = 230 if not story else 640
    area_top, area_bot = ty + 20, H - bottom_band
    ah = area_bot - area_top
    tablet_w = min(W * (0.84 if story else 0.70), ah / 0.80 * 1.05)
    tx = int(W * 0.06); tyy = int(area_top + 10)
    tw, th_ = device(cv, imgs[angle.get("imagen", "portada")], tx, tyy, int(tablet_w))
    pw = int(tablet_w * 0.34)
    ph_img = imgs[angle.get("movil", "movil")]
    ph_h = ph_img.height * pw / ph_img.width
    py = int(min(area_bot - ph_h - 20, tyy + th_ * 0.25))
    device(cv, ph_img, int(W - M - pw - 10), py, pw, radius=int(pw * 0.12), pad=int(pw * 0.05))
    # banda inferior: precio + CTA
    d = ImageDraw.Draw(cv)
    by = H - bottom_band + (40 if not story else 50)
    if story:
        price_tag(d, W / 2, by, P["precio"], P["tachado"], 1.3, center=True)
        pill(d, W / 2, by + 125, angle.get("cta", "Descárgalo hoy"), F("Medium", 42), PAL["ink"], PAL["paper"], padx=64, center=True)
        d.text((W / 2, by + 265), P["dominio"], font=F("Medium", 32), fill=PAL["ink"], anchor="mm")
    else:
        price_tag(d, M, by, P["precio"], P["tachado"])
        fcta = F("Medium", 34); cw = d.textlength(angle.get("cta", "Descárgalo hoy"), font=fcta) + 88
        pill(d, W - M - cw, by + 4, angle.get("cta", "Descárgalo hoy"), fcta, PAL["ink"], PAL["paper"], padx=44)
        d.text((M, H - 62), P["extras"], font=F("Regular", 26), fill=PAL["ink"])
        d.text((W - M, H - 62), P["dominio"], font=F("Medium", 26), fill=PAL["ink"], anchor="ra")
    cv.convert("RGB").save(out, quality=92)


def right_pill_fix(path):  # no-op placeholder (layout ya calculado)
    return path


# ---------------- REEL ----------------
def ease(t): return 1 - (1 - t) ** 3

def reel(P, imgs, out, fps=30):
    W, H = 1080, 1920
    scenes = P["reel"]
    dur = [s.get("seg", 2.6) for s in scenes]
    total = int(sum(dur) * fps)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    starts = [sum(dur[:i]) for i in range(len(dur))]
    cache = {}
    def base():
        if "bg" not in cache:
            b = Image.new("RGB", (W, H), PAL["bg"]); d = ImageDraw.Draw(b)
            d.ellipse([W * .55, -W * .3, W * 1.35, W * .5], fill=PAL["sand"]); d.ellipse([-W * .35, H - W * .4, W * .3, H + W * .2], fill=PAL["sage"])
            cache["bg"] = b
        return cache["bg"].copy()
    for fi in range(total):
        t = fi / fps
        si = max(i for i in range(len(scenes)) if starts[i] <= t)
        s = scenes[si]; lt = (t - starts[si]) / dur[si]; e = ease(min(1, lt / 0.35))
        cv = base().convert("RGBA"); d = ImageDraw.Draw(cv)
        kind = s["tipo"]
        if kind == "gancho":
            f, lines, sz = fit_text(d, s["texto"], "serif", W - 160, 700, 120)
            y0 = H / 2 - len(lines) * sz * 1.12 / 2 + (1 - e) * 80
            for i, ln in enumerate(lines):
                d.text((W / 2, y0 + i * sz * 1.12), ln, font=f, fill=PAL["ink"], anchor="ma")
            if s.get("sub"):
                fs = F("Medium", 44); d.text((W / 2, y0 + len(lines) * sz * 1.12 + 40), s["sub"], font=fs, fill=PAL["terra"], anchor="ma")
        elif kind == "pantalla":
            img = imgs[s["imagen"]]
            z = 1.0 + 0.06 * lt
            w = int((W - 220) * z) if not s.get("movil") else int(560 * z)
            x = int((W - w) / 2); y = int(560 - (1 - e) * 200) if not s.get("movil") else int(420 - (1 - e) * 160)
            device(cv, img, x, y, w, shadow=True)
            d = ImageDraw.Draw(cv)
            fs = F("Bold", 64)
            for i, ln in enumerate(wrap(d, s["texto"], fs, W - 160)):
                d.text((W / 2, 210 + i * 80), ln, font=fs, fill=PAL["ink"], anchor="ma")
        elif kind == "lista":
            d.text((W / 2, 380), s["titulo"], font=LM(84), fill=PAL["ink"], anchor="ma")
            for i, it in enumerate(s["items"]):
                ie = ease(max(0, min(1, (lt - i * 0.12) / 0.3)))
                if ie <= 0: continue
                y = 600 + i * 150 + (1 - ie) * 40
                d.ellipse([140, y, 210, y + 70], fill=[PAL["terra"], PAL["sage"], PAL["mustard"], PAL["terra"], PAL["sage"]][i % 5])
                d.text((175, y + 35), "✓" if False else str(i + 1), font=F("Bold", 34), fill=PAL["paper"], anchor="mm")
                d.text((250, y + 35), it, font=F("Medium", 46), fill=PAL["ink"], anchor="lm")
        elif kind == "cierre":
            img = imgs["mockup"]; w = int(W - 120)
            im = img.resize((w, int(img.height * w / img.width)), Image.LANCZOS)
            cv.paste(im, (60, int(260 + (1 - e) * 60)))
            d = ImageDraw.Draw(cv)
            price_tag(d, W / 2, 1360, P["precio"], P["tachado"], 1.4, center=True)
            pill(d, W / 2, 1500, s.get("cta", "Descárgalo hoy"), F("Medium", 46), PAL["ink"], PAL["paper"], padx=70, center=True)
            d.text((W / 2, 1690), P["dominio"], font=F("Medium", 40), fill=PAL["ink"], anchor="mm")
        # fundido entre escenas
        if lt > 0.9 and si < len(scenes) - 1:
            a = (lt - 0.9) / 0.1
            cv = Image.blend(cv.convert("RGB"), base(), a * 0.6).convert("RGBA")
        proc.stdin.write(cv.convert("RGB").tobytes())
    proc.stdin.close(); proc.wait()


if __name__ == "__main__":
    P = json.load(open(sys.argv[1]))
    base = pathlib.Path(sys.argv[1]).parent
    out = base / "out"; out.mkdir(exist_ok=True)
    imgs = {k: Image.open(base / v).convert("RGB") for k, v in P["imagenes"].items()}
    for a in P["enfoques"]:
        for sz in SIZES:
            make_image(P, a, sz, imgs, out / f"{a['id']}-{sz}.jpg")
    print("imágenes ok")
    if "--sin-video" not in sys.argv:
        reel(P, imgs, out / "reel-9x16.mp4"); print("reel ok")
