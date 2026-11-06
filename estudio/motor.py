"""Motor visual del estudio de anuncios de Pixelia.
Dado un brief (textos, colores) y las páginas de un producto, genera:
  - reel 9:16 (sin audio) con gancho, páginas que pasan en 3D, móvil con lluvia de stickers y precio que golpea
  - 3 enfoques × 3 tamaños de imagen (1:1, 4:5, 9:16)
Devuelve la línea de tiempo para sincronizar el audio.
"""
import math, random, subprocess, pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = pathlib.Path(__file__).parent
FONTS = HERE / "fonts"
def F(w, s): return ImageFont.truetype(str(FONTS / f"Poppins-{w}.ttf"), int(s))
W, H, FPS = 1080, 1920, 30
INK = "#2E2823"

# ---------- utilidades ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_in_out(t): return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
def back_out(t, s=1.9): t -= 1; return t * t * ((s + 1) * t + s) + 1
def prog(t, a, b): return clamp((t - a) / (b - a))
def hexrgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

# ---------- estilos ----------
STYLE_NAMES = {"color": "Explosión de color", "neon": "Neón oscuro", "minimal": "Minimal elegante", "tiktok": "TikTok nativo", "impacto": "Impacto 3D"}
S = {}

def bright(hexes):  # el color más vivo/claro de la paleta
    return max(hexes, key=lambda c: sum(hexrgb(c)) + 2 * (max(hexrgb(c)) - min(hexrgb(c))))

def set_style(name, colors, pages=None):
    """Prepara el estilo visual. Todas las funciones de dibujo leen de S."""
    b = bright(colors)
    base = dict(name=name, colors=colors, bg="gradient", text="#FFFFFF", shadow=True, glow=False, boxed=False,
                hl_fill=INK, hl_text="#FFFFFF", box_fill="#FFFFFF", box_text="#111111", pill_fill=INK, pill_text="#FFFFFF",
                burst="#FFF6E0", price="#C8442B", old=INK, badge=INK, cta_fill="#FFFFFF", cta_text=INK, domain="#FFFFFF",
                device=(36, 30, 26, 255), stickers=6, falling=14, pages=pages)
    if name == "neon":
        base.update(bg="neon", shadow=False, glow=True, hl_fill=b, hl_text="#0B0820", pill_fill="#1B1238", pill_text=b,
                    burst="#1B1238", price=b, old="#FFFFFF", badge=b, cta_fill=b, cta_text="#0B0820", domain=b, device=(12, 10, 24, 255))
    elif name == "minimal":
        base.update(bg="minimal", text=INK, shadow=False, hl_fill=colors[0], hl_text="#FFFFFF", pill_fill="#FFFFFF", pill_text=INK,
                    burst="#FFFFFF", price=colors[0], cta_fill=INK, cta_text="#FFFFFF", domain=INK, stickers=3, falling=6)
    elif name == "tiktok":
        base.update(bg="page", boxed=True, shadow=False, hl_fill="#FE2C55", pill_fill="#FFFFFF", pill_text="#111111",
                    burst="#FFFFFF", price="#FE2C55", badge="#FE2C55", cta_fill="#FE2C55", cta_text="#FFFFFF", stickers=2, falling=6)
    S.clear(); S.update(base); _bgcache.clear()

_bgcache = {}
def background(w, h, colors, t):
    kind = S.get("bg", "gradient")
    if kind == "neon": return neon_bg(w, h, colors, t)
    if kind == "minimal": return minimal_bg(w, h, colors, t)
    if kind == "page" and S.get("pages"): return page_bg(w, h, t)
    return gradient_bg(w, h, colors, t)

def _blobs(w, h, colors, t, base, strength, radius):
    sw, sh = w // 4, h // 4
    if (sw, sh) not in _grid: _grid[(sw, sh)] = np.mgrid[0:sh, 0:sw].astype(np.float32)
    yy, xx = _grid[(sw, sh)]; img = np.empty((sh, sw, 3), np.float32); img[:] = hexrgb(base)
    for k, c in enumerate(colors[:3]):
        cx = sw * (0.5 + 0.38 * math.sin(t * 0.5 + k * 2.1)); cy = sh * (0.5 + 0.4 * math.cos(t * 0.37 + k * 1.7))
        g = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * (sw * radius) ** 2)))[..., None] * strength
        img = img * (1 - g) + np.array(hexrgb(c), np.float32) * g
    return Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGB").resize((w, h), Image.BILINEAR).convert("RGBA")

def neon_bg(w, h, colors, t): return _blobs(w, h, colors, t, "#0B0820", 0.75, 0.32)
def minimal_bg(w, h, colors, t): return _blobs(w, h, colors, t, "#F7F1EA", 0.22, 0.36)

def page_bg(w, h, t):
    """Fondo estilo TikTok: la portada del producto ampliada, desenfocada y oscurecida, con zoom lento."""
    key = (w, h)
    if key not in _bgcache:
        p = S["pages"][0]; sc = max(w * 1.2 / p.width, h * 1.2 / p.height)
        big = p.resize((int(p.width * sc), int(p.height * sc)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(28))
        big = Image.blend(big.convert("RGB"), Image.new("RGB", big.size, (10, 10, 14)), 0.55)
        _bgcache[key] = big
    big = _bgcache[key]; dx = (big.width - w) * (0.5 + 0.4 * math.sin(t * 0.25)); dy = (big.height - h) * (0.5 + 0.4 * math.cos(t * 0.2))
    return big.crop((int(dx), int(dy), int(dx) + w, int(dy) + h)).convert("RGBA")

_grid = {}
def gradient_bg(w, h, colors, t):
    """Degradado diagonal en movimiento + manchas de luz (calculado a 1/4 de resolución y escalado)."""
    sw, sh = w // 4, h // 4
    if (sw, sh) not in _grid: _grid[(sw, sh)] = np.mgrid[0:sh, 0:sw].astype(np.float32)
    yy, xx = _grid[(sw, sh)]
    ang = 0.6 + 0.25 * math.sin(t * 0.7)
    u = (xx * math.cos(ang) + yy * math.sin(ang)) / (sw * abs(math.cos(ang)) + sh * abs(math.sin(ang)))
    u = (u + 0.08 * math.sin(t * 1.3)) % 1.0
    cols = np.array([hexrgb(c) for c in list(colors) + [colors[0]]], np.float32)
    n = len(colors); pos = u * n; i = np.floor(pos).astype(int) % n; f = (pos - np.floor(pos))[..., None]
    img = cols[i] * (1 - f) + cols[i + 1] * f
    small = Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGB")
    glow = Image.new("L", (sw, sh), 0); g = ImageDraw.Draw(glow)
    for k in range(3):
        cx = sw * (0.2 + 0.6 * ((k * 0.37 + 0.05 * t) % 1)); cy = sh * (0.15 + 0.7 * ((k * 0.61 + 0.03 * t) % 1)); r = sw * 0.35
        g.ellipse([cx - r, cy - r, cx + r, cy + r], fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(sw * 0.12))
    small = Image.composite(Image.new("RGB", (sw, sh), (255, 255, 255)), small, glow)
    return small.resize((w, h), Image.BILINEAR).convert("RGBA")

def perspective_coeffs(src, dst):
    m = []
    for (x, y), (u, v) in zip(dst, src):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); m.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    return np.linalg.solve(np.array(m, np.float64), np.array([p for s in src for p in s], np.float64))

def warp(img, quad, size):
    w, h = img.size
    return img.transform(size, Image.PERSPECTIVE, perspective_coeffs([(0, 0), (w, 0), (w, h), (0, h)], quad), Image.BICUBIC)

def shadow(layer, blur=30, offset=(0, 30), alpha=110):
    a = layer.getchannel("A").point(lambda v: alpha if v > 0 else 0).filter(ImageFilter.GaussianBlur(blur))
    sh = Image.new("RGBA", layer.size, (40, 20, 10, 0)); sh.putalpha(a)
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0)); out.alpha_composite(sh, offset); return out

def rounded(img, r):
    m = Image.new("L", img.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=r, fill=255)
    out = img.convert("RGBA"); out.putalpha(m); return out

def text_box(text, font, fill, stroke=None, sw=0):
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    l, t, r, b = d.textbbox((0, 0), text, font=font, stroke_width=sw)
    im = Image.new("RGBA", (r - l + 20, b - t + 20), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10 - l, 10 - t), text, font=font, fill=fill, stroke_width=sw, stroke_fill=stroke)
    return im

def paste_center(cv, im, cx, cy, scale=1.0, rot=0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0: return
    if scale != 1: im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 1: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    cv.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def fit_font(words, maxw, start, minsize=48):
    s = start
    while s > minsize:
        f = F("Bold", s); d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        if sum(d.textlength(w, font=f) for w in words) + s * 0.4 * len(words) <= maxw: return f
        s -= 4
    return F("Bold", minsize)

def highlight_words(cv, words, cx, y, font, t0, t, hl_index=None, hl_color=INK):
    hl_color = S.get("hl_fill", hl_color)
    boxes = [text_box(w, font, S.get("hl_text", "#FFFFFF") if i == hl_index else (S.get("box_text") if S.get("boxed") else S.get("text", "#FFFFFF")))
             for i, w in enumerate(words)]
    gap = font.size * (0.36 if S.get("boxed") else 0.28)
    total = sum(b.width for b in boxes) + gap * (len(boxes) - 1)
    x = cx - total / 2
    for i, b in enumerate(boxes):
        p = prog(t, t0 + i * 0.12, t0 + i * 0.12 + 0.35)
        if p > 0:
            s = back_out(p); im = b
            if i == hl_index or S.get("boxed"):
                pad = 14; bx = Image.new("RGBA", (b.width + 2 * pad, b.height + pad), (0, 0, 0, 0))
                ImageDraw.Draw(bx).rounded_rectangle([0, 0, bx.width - 1, bx.height - 1], radius=18 if not S.get("boxed") else 12,
                                                     fill=hl_color if i == hl_index else S["box_fill"])
                bx.alpha_composite(b, (pad, pad // 2)); im = bx
            elif S.get("glow"):
                gl = text_box(words[i], font, S["hl_fill"]).filter(ImageFilter.GaussianBlur(16))
                paste_center(cv, gl, x + b.width / 2, y, s * 1.03, rot=(1 - p) * -8, alpha=0.9)
            elif S.get("shadow", True):
                dark = Image.new("RGBA", b.size, (60, 25, 10, 0))
                dark.putalpha(b.getchannel("A").point(lambda v: int(v * 0.45)).filter(ImageFilter.GaussianBlur(6)))
                paste_center(cv, dark, x + b.width / 2 + 3, y + 6, s, rot=(1 - p) * -8)
            paste_center(cv, im, x + b.width / 2, y, s, rot=(1 - p) * -8)
        x += b.width + gap

def lines_block(cv, lines, cx, y0, maxw, size, t0, t, line_gap=1.2):
    for li, line in enumerate(lines):
        f = fit_font(line["palabras"], maxw, size)
        highlight_words(cv, line["palabras"], cx, y0 + li * size * line_gap, f, t0 + li * 0.35, t, line.get("resaltar"))

def starburst(r, color, points=18, inner=0.82):
    im = Image.new("RGBA", (2 * r + 4, 2 * r + 4), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(r + 2 + (r if k % 2 == 0 else r * inner) * math.cos(k * math.pi / points),
            r + 2 + (r if k % 2 == 0 else r * inner) * math.sin(k * math.pi / points)) for k in range(2 * points)]
    d.polygon(pts, fill=color); return im

def device_frame(page, w, max_h=None, r=46, pad=26, color=None):
    color = color or S.get("device", (36, 30, 26, 255))
    ph = int(page.height * w / page.width)
    if max_h and ph > max_h: w = int(w * max_h / ph); ph = max_h
    p = page.resize((w, ph), Image.LANCZOS)
    fr = Image.new("RGBA", (p.width + 2 * pad, p.height + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(fr).rounded_rectangle([0, 0, fr.width - 1, fr.height - 1], radius=r, fill=color)
    fr.alpha_composite(rounded(p, int(r * .55)), (pad, pad)); return fr

PAGOS = [p.strip() for p in __import__("os").environ.get("PAGOS_ANUNCIO", "PayPal,Visa,Mastercard,Binance").split(",") if p.strip()]

def pay_strip(scale=1.0, dark=None):
    """Franja 'Paga con: PayPal · Visa · Mastercard · Binance' con icono de tarjeta (sin logos de marcas)."""
    darkbg = S.get("name") in ("neon", "tiktok")
    fg = "#FFFFFF" if darkbg else INK
    bg = {"neon": (27, 18, 56, 240), "tiktok": (0, 0, 0, 190)}.get(S.get("name"), (255, 255, 255, 245))
    f1, f2 = F("Medium", 30 * scale), F("Bold", 30 * scale)
    pills = [text_box(p, f2, fg) for p in PAGOS]
    lead = text_box("Paga con", f1, fg)
    ic_w, ic_h = int(54 * scale), int(36 * scale)
    gap = int(16 * scale); dot = int(10 * scale)
    w = ic_w + gap + lead.width + gap + sum(p.width for p in pills) + (len(pills) - 1) * (gap + dot) + int(40 * scale)
    h = max(lead.height, ic_h) + int(20 * scale)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=bg)
    x = int(20 * scale); cy = h / 2
    card = S.get("hl_fill", "#7B5CFF")  # icono de tarjeta genérica
    d.rounded_rectangle([x, cy - ic_h / 2, x + ic_w, cy + ic_h / 2], radius=int(6 * scale), fill=card)
    d.rectangle([x, cy - ic_h / 2 + ic_h * 0.22, x + ic_w, cy - ic_h / 2 + ic_h * 0.40], fill=(0, 0, 0, 90))
    d.rounded_rectangle([x + ic_w * 0.12, cy + ic_h * 0.08, x + ic_w * 0.42, cy + ic_h * 0.30], radius=2, fill=(255, 255, 255, 200))
    x += ic_w + gap
    im.alpha_composite(lead, (x, int(cy - lead.height / 2))); x += lead.width + gap
    for k, p in enumerate(pills):
        im.alpha_composite(p, (x, int(cy - p.height / 2))); x += p.width
        if k < len(pills) - 1:
            d.ellipse([x + gap / 2, cy - dot / 2, x + gap / 2 + dot, cy + dot / 2], fill=card); x += gap + dot
    return im

def money(x): return f"${x:.2f}".replace(".00", "") if abs(x - round(x)) < 1e-9 else f"${x:.2f}"

# ---------- stickers generados (sin archivos externos) ----------
def diecut(im, pad=16):
    big = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0)); big.paste(im, (pad, pad), im)
    a = big.getchannel("A").filter(ImageFilter.MaxFilter(21)).point(lambda v: 255 if v > 10 else 0)
    white = Image.new("RGBA", big.size, (255, 255, 255, 255)); white.putalpha(a); white.alpha_composite(big); return white

def make_stickers(texts, colors):
    out = []
    pal = [c for c in colors] + [INK]
    for i, t in enumerate(texts[:4]):
        f = F("Bold", 34); tw = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(t, font=f)
        im = Image.new("RGBA", (int(tw + 60), 70), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, im.width - 1, 69], radius=35, fill=pal[(i + 1) % len(pal)] if i % 2 else INK)
        d.text((im.width / 2, 35), t, font=f, fill="#FFFFFF", anchor="mm"); out.append(diecut(im))
    def star(c):
        s = 130; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); cx = s / 2
        pts = [(cx + (s * .46 if k % 2 == 0 else s * .2) * math.sin(k * math.pi / 5), cx - (s * .46 if k % 2 == 0 else s * .2) * math.cos(k * math.pi / 5)) for k in range(10)]
        ImageDraw.Draw(im).polygon(pts, fill=c); return diecut(im)
    def heart(c):
        s = 130; im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        pts = [(s / 2 + s * .028 * 16 * math.sin(t) ** 3, s * .45 - s * .028 * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))) for t in np.linspace(0, 2 * math.pi, 120)]
        ImageDraw.Draw(im).polygon(pts, fill=c); return diecut(im)
    def spark(c):
        s = 120; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); m = s / 2
        d.polygon([(m, 4), (m + 14, m - 14), (s - 4, m), (m + 14, m + 14), (m, s - 4), (m - 14, m + 14), (4, m), (m - 14, m - 14)], fill=c); return diecut(im)
    out += [star("#FFC83D"), heart("#FF5C8A"), spark("#7B5CFF"), star("#FF7A45")]
    return out


# ---------- página que pasa (efecto libro) ----------
def flip_frame(page_a, page_b, p):
    w, h = page_a.size
    if p <= 0: return page_a.convert("RGBA")
    if p >= 1: return page_b.convert("RGBA")
    out = page_b.copy().convert("RGBA")
    ang = p * math.pi; x_edge = w / 2 + (w / 2) * math.cos(ang); lift = math.sin(ang) * h * 0.06
    out.alpha_composite(page_a.crop((0, 0, w // 2, h)).convert("RGBA"), (0, 0))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([min(x_edge, w / 2), 0, max(x_edge, w / 2) + 40, h], fill=(0, 0, 0, int(70 * math.sin(ang))))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(25)))
    if ang < math.pi / 2:
        face = page_a.crop((w // 2, 0, w, h)).convert("RGBA"); quad = [(w / 2, 0), (x_edge, -lift), (x_edge, h + lift), (w / 2, h)]
    else:
        face = page_b.crop((0, 0, w // 2, h)).convert("RGBA"); quad = [(x_edge, -lift), (w / 2, 0), (w / 2, h), (x_edge, h + lift)]
    lay = warp(face, quad, (w, h))
    k = abs(math.cos(ang)); dark = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dark.putalpha(Image.fromarray((np.array(lay.getchannel("A")) * (0.35 * (1 - k))).astype(np.uint8)))
    lay.alpha_composite(dark); out.alpha_composite(lay)
    return out


def timeline(n_pages):
    flip_start, flip_each = 2.7, 0.75
    t2_end = flip_start + flip_each * (n_pages - 1) + 0.6
    s3a = t2_end + 0.2; s4 = t2_end + 3.0
    return {"flip_start": flip_start, "flip_each": flip_each, "n": n_pages, "t2_end": t2_end, "s3a": s3a, "s4": s4, "T": round(s4 + 3.4, 2)}


# ---------- reel ----------
def build_reel(B, pages, phone, out_path, progress=None, style="color", only_times=None, seed=7):
    """only_times=[t...] devuelve solo esos fotogramas (para pruebas rápidas)."""
    colors = B["colores"]; TL = timeline(len(pages)); T = TL["T"]; set_style(style, colors, pages)
    pw = 860; pages_r = []
    for p in pages:
        ph = int(p.height * pw / p.width)
        if ph > 1100: w2 = int(pw * 1100 / ph); pages_r.append(p.resize((w2, 1100), Image.LANCZOS))
        else: pages_r.append(p.resize((pw, ph), Image.LANCZOS))
    base_size = pages_r[0].size; pages_r = [p.resize(base_size, Image.LANCZOS) for p in pages_r]
    stickers = make_stickers(B.get("stickers", ["NUEVO", "PDF", "Descarga inmediata"]), colors)
    rng = random.Random(seed)
    falling = [(rng.uniform(80, W - 80), rng.uniform(-900, -100), rng.uniform(-40, 40), rng.uniform(300, 520), rng.choice(stickers)) for _ in range(S["falling"])]
    flips = B["textos_paginas"]
    while len(flips) < len(pages): flips.append(flips[-1] if flips else "")
    ff = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)]
    proc = None if only_times else subprocess.Popen(ff, stdin=subprocess.PIPE); shots = []
    n = len(pages_r); fs_, fe = TL["flip_start"], TL["flip_each"]; t2_end, s3a, s4 = TL["t2_end"], TL["s3a"], TL["s4"]
    total = int(T * FPS); f_mid = F("Bold", 64)
    for fi in ([round(x * FPS) for x in only_times] if only_times else range(total)):
        t = fi / FPS
        cv = background(W, H, colors, t)
        if t < 2.3:  # gancho
            a = 1 - prog(t, 2.0, 2.3); hook = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            lines_block(hook, B["gancho"], W / 2, 760 - (len(B["gancho"]) - 3) * 70, W - 120, 118, 0.1, t, 1.27)
            if a < 1: hook.putalpha(hook.getchannel("A").point(lambda v: int(v * a)))
            paste_center(cv, hook, W / 2, H / 2, 1 + (1 - a) * 0.15)
        if 2.2 <= t < t2_end + 0.3:  # páginas
            k = min(n - 2, int(max(0, t - fs_) // fe)) if n > 1 else 0
            p = ease_in_out(clamp(((t - fs_) - k * fe) / (fe * 0.8))) if n > 1 else 0
            page = flip_frame(pages_r[k], pages_r[min(k + 1, n - 1)], p if t >= fs_ else 0)
            dev = device_frame(page, page.width)
            ent = back_out(prog(t, 2.2, 2.7))
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); paste_center(lay, dev, W / 2, 1060, 0.6 + 0.4 * ent, rot=4 * math.sin(t * 1.4))
            cv.alpha_composite(shadow(lay, 35, (0, 40))); cv.alpha_composite(lay)
            idx = min(len(flips) - 1, k + (1 if p > 0.5 else 0))
            tb = text_box(flips[idx], fit_font([flips[idx]], W - 200, 64), S["pill_text"])
            pill = Image.new("RGBA", (tb.width + 60, tb.height + 24), (0, 0, 0, 0))
            ImageDraw.Draw(pill).rounded_rectangle([0, 0, pill.width - 1, pill.height - 1], radius=pill.height // 2, fill=S["pill_fill"])
            pill.alpha_composite(tb, (30, 12))
            pop = back_out(clamp(((t - fs_) - (idx - 1) * fe) / 0.3)) if idx > 0 else ent
            paste_center(cv, pill, W / 2, 440, max(0.01, pop))
            for j, st in enumerate(stickers[:S["stickers"]]):
                sp = back_out(prog(t, 2.3 + j * 0.25, 2.7 + j * 0.25)); ang = j * 60 + t * 25
                paste_center(cv, st, W / 2 + math.cos(math.radians(ang)) * 470, max(640, 1060 + math.sin(math.radians(ang)) * 560), sp * 0.9, rot=10 * math.sin(t * 3 + j))
        if s3a <= t < s4 + 0.3:  # móvil
            for (x0, y0, rot0, spd, st) in falling:
                y = y0 + (t - s3a) * spd * 2.2
                if -200 < y < H + 200: paste_center(cv, st, x0, y, 1.0, rot=rot0 + (t - s3a) * 60)
            e = back_out(prog(t, s3a, s3a + 0.5))
            ph_ = device_frame(phone, 500, max_h=1000, r=66, pad=20)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); paste_center(lay, ph_, W / 2 + (1 - e) * 700, 1100, 1.0, rot=-6 + 3 * math.sin(t * 2))
            cv.alpha_composite(shadow(lay, 35, (10, 40))); cv.alpha_composite(lay)
            mt = B["movil_texto"]; highlight_words(cv, mt, W / 2, 300, fit_font(mt, W - 140, 84), s3a + 0.2, t, B.get("movil_resaltar"))
        if t >= s4:  # precio
            e = back_out(prog(t, s4, s4 + 0.45), 2.4)
            paste_center(cv, starburst(300, S["burst"]), W / 2, 860, e, rot=t * 20)
            ptxt = money(B["precio"]); pr = text_box(ptxt, F("Bold", 230 if len(ptxt) <= 3 else 190), S["price"])
            paste_center(cv, pr, W / 2, 830, e)
            if B.get("tachado"):
                old = text_box(f"antes {money(B['tachado'])}", F("Medium", 52), S["old"])
                ImageDraw.Draw(old).line([(10, old.height / 2 + 4), (old.width - 10, old.height / 2 + 4)], fill=S["price"], width=6)
                paste_center(cv, old, W / 2, 1010, back_out(prog(t, s4 + 0.3, s4 + 0.6)))
                off = round((1 - B["precio"] / B["tachado"]) * 100)
                if off >= 10:
                    badge = starburst(95, S["badge"], 12, 0.78)
                    ImageDraw.Draw(badge).text((badge.width / 2, badge.height / 2), f"-{off}%", font=F("Bold", 50), fill="#FFFFFF" if S["name"] != "neon" else "#0B0820", anchor="mm")
                    paste_center(cv, badge, W / 2 + 270, 640, back_out(prog(t, s4 + 0.45, s4 + 0.75)), rot=-12)
            pulse = 1 + 0.05 * math.sin((t - s4) * 9)
            cta = text_box(B["cta"], F("Bold", 58), S["cta_text"])
            btn = Image.new("RGBA", (cta.width + 110, cta.height + 50), (0, 0, 0, 0))
            ImageDraw.Draw(btn).rounded_rectangle([0, 0, btn.width - 1, btn.height - 1], radius=btn.height // 2, fill=S["cta_fill"])
            btn.alpha_composite(cta, (55, 25))
            paste_center(cv, btn, W / 2, 1270, back_out(prog(t, s4 + 0.6, s4 + 0.95)) * pulse)
            paste_center(cv, text_box(B["dominio"], F("Bold", 46), S["domain"]), W / 2, 1420, prog(t, s4 + 0.9, s4 + 1.2))
            if PAGOS:
                ps = pay_strip(1.35); ps = ps if ps.width <= W - 80 else ps.resize((W - 80, int(ps.height * (W - 80) / ps.width)), Image.LANCZOS)
                paste_center(cv, ps, W / 2, 1545, back_out(prog(t, s4 + 1.0, s4 + 1.35)))
            for j, st in enumerate(stickers[:min(4, S["stickers"])]):
                pos = [(200, 520), (880, 1150), (180, 1180), (900, 470)][j]
                paste_center(cv, st, *pos, back_out(prog(t, s4 + 0.2 + j * 0.1, s4 + 0.5 + j * 0.1)), rot=15 * math.sin(t * 2 + j))
        if only_times: shots.append(cv.convert("RGB")); continue
        proc.stdin.write(cv.convert("RGB").tobytes())
        if progress and fi % 60 == 0: progress(fi / total)
    if only_times: return shots
    proc.stdin.close(); proc.wait()
    return TL


# ---------- imágenes ----------
def build_static(B, pages, phone, outdir, style="color", prefix=None, only=None, sizes=None):
    """prefix='V2' → V2-4x5.jpg… (variantes); only=[índices de B['estaticos']] a dibujar."""
    rng = random.Random(3); files = []; set_style(style, B["colores"], pages)
    stickers = make_stickers(B.get("stickers", ["NUEVO", "PDF"]), B["colores"])
    for vi, v in enumerate(B["estaticos"]):
        if only is not None and vi not in only: continue
        for name, (w, h) in {"1x1": (1080, 1080), "4x5": (1080, 1350), "9x16": (1080, 1920)}.items():
            if sizes and name not in sizes: continue
            cols = v.get("colores") or B["colores"]
            cv = background(w, h, cols, vi * 2.0); story = name == "9x16"
            top = 260 if story else 70; size = (96 if w == h else 104) * (0.8 if len(v["titular"]) >= 3 else 1)
            head_bottom = top + 70 + (len(v["titular"]) - 0.5) * size * 1.18
            for li, line in enumerate(v["titular"]):
                f = fit_font(line["palabras"], w - 120, size)
                highlight_words(cv, line["palabras"], w / 2, top + 70 + li * size * 1.18, f, -10, 10, line.get("resaltar"))
            sq = w == h and bool(PAGOS)  # en cuadrado con franja de pagos, el dispositivo va algo más pequeño
            cy = h * (0.52 if sq else 0.60 if not story else 0.55); dw = int(w * (0.56 if sq else 0.62 if not story else 0.78)); max_h = int(h * (0.34 if sq else 0.42 if w == h else 0.40))
            lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            back = device_frame(pages[min(len(pages) - 1, v.get("pagina_fondo", 1))], dw, max_h)
            front = device_frame(pages[min(len(pages) - 1, v.get("pagina", 0))], dw, max_h)
            paste_center(lay, back, w * 0.46, cy - 40, 0.92, rot=9); paste_center(lay, front, w * 0.50, cy + 10, 1.0, rot=-5)
            ph_ = device_frame(phone, int(dw * 0.30), int(max_h * 0.9), r=40, pad=12)
            paste_center(lay, ph_, w * 0.80, cy + front.height * 0.25, 1.0, rot=8)
            cv.alpha_composite(shadow(lay, 30, (0, 30))); cv.alpha_composite(lay)
            for j, st in enumerate(stickers[:min(5, S["stickers"])]):
                pos = [(0.12, 0.42), (0.90, 0.47), (0.10, 0.74), (0.14, 0.60), (0.90, 0.70)][j]
                half = st.width * 0.45 + 12; sx = max(half, min(w - half, w * pos[0]))
                paste_center(cv, st, sx, h * pos[1], 0.9, rot=rng.uniform(-18, 18))
            r = int(w * 0.13); b = starburst(r, S["burst"]); bd = ImageDraw.Draw(b)
            ptxt = money(B["precio"])
            bd.text((b.width / 2, b.height / 2 - r * 0.12), ptxt, font=F("Bold", r * (0.62 if len(ptxt) <= 3 else 0.46)), fill=S["price"], anchor="mm")
            if B.get("tachado"): bd.text((b.width / 2, b.height / 2 + r * 0.38), f"antes {money(B['tachado'])}", font=F("Medium", r * 0.17), fill=S["old"], anchor="mm")
            by_ = max(h * (0.40 if w == h else 0.33), head_bottom + b.height * 0.42)
            paste_center(cv, b, w * 0.84, by_, 0.9 if w == h else 1.0, rot=-10)
            cta = text_box(v.get("cta", B["cta"]), F("Bold", 44), S["cta_text"])
            btn = Image.new("RGBA", (cta.width + 80, cta.height + 34), (0, 0, 0, 0))
            ImageDraw.Draw(btn).rounded_rectangle([0, 0, btn.width - 1, btn.height - 1], radius=btn.height // 2, fill=S["cta_fill"])
            btn.alpha_composite(cta, (40, 17)); by = h - (110 if not story else 360)
            if PAGOS:  # franja abajo del todo; el botón y el dominio suben un poco
                ps = pay_strip(1.0); maxw = w - 60
                if ps.width > maxw: ps = ps.resize((maxw, int(ps.height * maxw / ps.width)), Image.LANCZOS)
                by -= ps.height + (14 if not story else 0)
                paste_center(cv, ps, w / 2, (h - ps.height / 2 - 18) if not story else by + 200)
            paste_center(cv, btn, w / 2, by); paste_center(cv, text_box(B["dominio"], F("Bold", 34), S["domain"]), w / 2, by + (80 if not story else 100))
            path = outdir / f"{prefix or chr(65 + vi)}-{name}.jpg"; cv.convert("RGB").save(path, quality=92); files.append(path)
    return files
