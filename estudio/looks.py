"""Estilos visuales nuevos ("looks") para los anuncios de Pixelia.
Cada look dibuja fotogramas a partir de una receta (dict). Las piezas (papel, cinta, polaroid,
flechas a mano, burbujas de chat, grano...) se combinan para que cada anuncio se vea distinto.
"""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from motor import F, W, H, hexrgb, paste_center, text_box, fit_font, device_frame, rounded, shadow, starburst, money

INK = "#2E2823"

def LORA(s): from motor import FONTS; from PIL import ImageFont; return ImageFont.truetype(str(FONTS / "Lora-Medium.ttf"), int(s))

# ---------- texturas y fondos ----------
def grain(cv, amount=14, seed=0):
    rng = np.random.default_rng(seed)
    a = np.asarray(cv.convert("RGB"), np.int16) + rng.normal(0, amount, (cv.height, cv.width, 1)).astype(np.int16)
    out = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGB").convert("RGBA"); return out

def vignette(cv, strength=0.45):
    m = Image.new("L", (cv.width // 4, cv.height // 4), 0)
    ImageDraw.Draw(m).ellipse([-m.width * .25, -m.height * .15, m.width * 1.25, m.height * 1.15], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(m.width * .18)).resize(cv.size)
    dark = Image.new("RGBA", cv.size, (0, 0, 0, int(255 * strength)))
    dark.putalpha(Image.eval(m, lambda v: int((255 - v) * strength)))
    cv.alpha_composite(dark); return cv

def paper_grid(w, h, base="#F6F0E6", line="#D9CFC2", step=54):
    im = Image.new("RGBA", (w, h), base); d = ImageDraw.Draw(im)
    for x in range(0, w, step): d.line([(x, 0), (x, h)], fill=line, width=2)
    for y in range(0, h, step): d.line([(0, y), (w, y)], fill=line, width=2)
    return grain(im, 7, 1)

def flat_split(w, h, c1, c2, ang=12):
    im = Image.new("RGBA", (w, h), c1); d = ImageDraw.Draw(im)
    off = math.tan(math.radians(ang)) * w
    d.polygon([(0, h * .55 + off / 2), (w, h * .55 - off / 2), (w, h), (0, h)], fill=c2); return im

def cork(w, h, base="#C9A27A", seed=2):
    rng = np.random.default_rng(seed)
    a = np.zeros((h // 3, w // 3, 3), np.float32) + hexrgb(base)
    a += rng.normal(0, 18, (h // 3, w // 3, 1)); im = Image.fromarray(a.clip(0, 255).astype(np.uint8)).resize((w, h), Image.NEAREST)
    return im.filter(ImageFilter.GaussianBlur(1.2)).convert("RGBA")

def blurred_page(page, w, h, darken=0.5, tint=(10, 10, 14)):
    sc = max(w * 1.2 / page.width, h * 1.2 / page.height)
    big = page.resize((int(page.width * sc), int(page.height * sc)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(30))
    big = Image.blend(big.convert("RGB"), Image.new("RGB", big.size, tint), darken)
    x, y = (big.width - w) // 2, (big.height - h) // 2
    return big.crop((x, y, x + w, y + h)).convert("RGBA")

# ---------- trazos "a mano" ----------
def _wobble(pts, rng, j=4):
    return [(x + rng.uniform(-j, j), y + rng.uniform(-j, j)) for x, y in pts]

def hand_circle(cv, box, color, width=9, seed=0):
    rng = random.Random(seed); x0, y0, x1, y1 = box; cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    pts = [(cx + rx * (1 + .04 * math.sin(a * 3)) * math.cos(a), cy + ry * math.sin(a)) for a in np.linspace(-.4, 2 * math.pi + .25, 70)]
    ImageDraw.Draw(cv).line(_wobble(pts, rng, 2), fill=color, width=width, joint="curve")

def hand_arrow(cv, p0, p1, color, width=9, bend=0.25, seed=0):
    rng = random.Random(seed); (x0, y0), (x1, y1) = p0, p1
    mx, my = (x0 + x1) / 2 - (y1 - y0) * bend, (y0 + y1) / 2 + (x1 - x0) * bend
    pts = [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t * t * y1) for t in np.linspace(0, 1, 40)]
    d = ImageDraw.Draw(cv); d.line(_wobble(pts, rng, 1.5), fill=color, width=width, joint="curve")
    ang = math.atan2(y1 - pts[-4][1], x1 - pts[-4][0])
    for s in (2.6, -2.6): d.line([(x1, y1), (x1 - 46 * math.cos(ang + s / 6), y1 - 46 * math.sin(ang + s / 6))], fill=color, width=width)

def underline(cv, x0, x1, y, color, width=14, seed=0):
    rng = random.Random(seed)
    pts = [(x, y + 6 * math.sin(i * .9) + rng.uniform(-2, 2)) for i, x in enumerate(np.linspace(x0, x1, 14))]
    ImageDraw.Draw(cv).line(pts, fill=color, width=width, joint="curve")

def marker(cv, box, color, alpha=150):
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0)); x0, y0, x1, y1 = box
    ImageDraw.Draw(lay).polygon([(x0 - 8, y0 + 6), (x1 + 6, y0 - 4), (x1 + 10, y1 - 2), (x0 - 4, y1 + 6)], fill=hexrgb(color) + (alpha,))
    cv.alpha_composite(lay)

# ---------- objetos ----------
def tape(w=190, h=58, color=(250, 236, 180, 190)):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    zig = [(0, 0)] + [(0 if i % 2 else 7, h * i / 8) for i in range(9)] + [(w - (0 if i % 2 else 7), h - h * i / 8) for i in range(9)]
    d.polygon(zig, fill=color); return im

def polaroid(img, w, caption=None, color=INK):
    pw = w - 60; ph = int(pw * img.height / img.width); ph = min(ph, int(pw * 1.25))
    sc = max(pw / img.width, ph / img.height); im = img.resize((int(img.width * sc) + 1, int(img.height * sc) + 1), Image.LANCZOS).crop((0, 0, pw, ph))
    card = Image.new("RGBA", (w, ph + 30 + (140 if caption else 90)), "#FFFFFF"); card.paste(im, (30, 30))
    if caption: ImageDraw.Draw(card).text((w / 2, ph + 30 + 70), caption, font=LORA(52), fill=color, anchor="mm")
    return card

def postit(text_lines, color="#FFE066", size=420, font=None):
    im = Image.new("RGBA", (size, size), color); d = ImageDraw.Draw(im)
    d.polygon([(size, size - 60), (size, size), (size - 60, size)], fill=(0, 0, 0, 40))
    f = font or F("Bold", 58); y = size / 2 - (len(text_lines) - 1) * 38
    for ln in text_lines: d.text((size / 2, y), ln, font=f, fill=INK, anchor="mm"); y += 76
    return im

def bubble(text, me=False, w=760, font=None):
    f = font or F("Medium", 50); d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    words, lines, cur = text.split(), [], ""
    for wd in words:
        if d.textlength((cur + " " + wd).strip(), font=f) > w - 90: lines.append(cur); cur = wd
        else: cur = (cur + " " + wd).strip()
    lines.append(cur); bw = int(max(d.textlength(l, font=f) for l in lines) + 70); bh = 40 + 66 * len(lines)
    im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
    dd.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=38, fill="#2F7BF6" if me else "#FFFFFF")
    for i, l in enumerate(lines): dd.text((35, 22 + i * 66), l, font=f, fill="#FFFFFF" if me else "#111111")
    return im

def notification(title, body, app="Recordatorios", w=960):
    im = Image.new("RGBA", (w, 230), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, 229], radius=44, fill=(245, 245, 247, 235))
    d.rounded_rectangle([34, 34, 104, 104], radius=18, fill="#FF9F0A")
    d.ellipse([52, 52, 86, 86], outline="#FFFFFF", width=6)
    d.text((126, 44), app.upper(), font=F("Medium", 30), fill="#6B6B70"); d.text((w - 40, 44), "ahora", font=F("Regular", 30), fill="#6B6B70", anchor="ra")
    d.text((126, 92), title, font=F("Bold", 42), fill="#111111"); d.text((126, 150), body, font=F("Regular", 38), fill="#333333")
    return im

def price_tag(price, old=None, fill="#FFFFFF", ink=INK, accent="#C8442B"):
    im = Image.new("RGBA", (520, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(80, 0), (520, 0), (520, 300), (80, 300), (0, 150)], fill=fill); d.ellipse([46, 132, 82, 168], fill=(0, 0, 0, 60))
    d.text((300, 135 if old else 150), money(price), font=F("Bold", 140), fill=accent, anchor="mm")
    if old:
        d.text((300, 245), f"antes {money(old)}", font=F("Medium", 44), fill=ink, anchor="mm")
        tw = d.textlength(f"antes {money(old)}", font=F("Medium", 44)); d.line([(300 - tw / 2, 248), (300 + tw / 2, 248)], fill=accent, width=5)
    return im

def big_words(cv, words, y, color, maxw=W - 100, start=260, font_fn=None, hl=None, hl_color=None, align="center", x=None, gap=0.86):
    """Palabras gigantes, una por línea, llenando el ancho."""
    out_y = y
    for i, wd in enumerate(words):
        s = start; fn = font_fn or (lambda s: F("Bold", s))
        while s > 60 and ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(wd, font=fn(s)) > maxw: s -= 6
        tb = text_box(wd, fn(s), hl_color if (hl is not None and i == hl) else color)
        cx = (x if x is not None else W / 2) if align == "center" else (x or 60) + tb.width / 2
        paste_center(cv, tb, cx, out_y + tb.height / 2); out_y += tb.height * gap
    return out_y

# ---------- efectos 3D / impacto ----------
def shade(c, k):
    r, g, b = hexrgb(c) if isinstance(c, str) else c[:3]
    return (int(clamp255(r * k)), int(clamp255(g * k)), int(clamp255(b * k)), 255)

def clamp255(v): return max(0, min(255, v))

def text3d(text, font, face="#FFFFFF", side="#7A1E5A", depth=26, dx=0.55, dy=1.0, outline=None, ow=0):
    """Letras en bloque 3D: se apilan copias desplazadas (lado) y encima la cara con brillo."""
    tb = text_box(text, font, face, outline, ow)
    pad = depth + 10; im = Image.new("RGBA", (tb.width + pad * 2, tb.height + pad * 2), (0, 0, 0, 0))
    mask = tb.getchannel("A")
    for k in range(depth, 0, -1):
        col = shade(side, 0.75 + 0.25 * (1 - k / depth)); lay = Image.new("RGBA", tb.size, col); lay.putalpha(mask)
        im.alpha_composite(lay, (int(pad + k * dx), int(pad + k * dy)))
    im.alpha_composite(tb, (pad, pad))
    # brillo en la mitad superior de la cara
    hl = Image.new("RGBA", tb.size, (255, 255, 255, 0)); g = Image.linear_gradient("L").resize(tb.size).point(lambda v: max(0, 90 - v))
    hl.putalpha(Image.fromarray((np.asarray(g, np.float32) * np.asarray(mask, np.float32) / 255).astype(np.uint8)))
    im.alpha_composite(hl, (pad, pad))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); a = im.getchannel("A").filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * .45))
    sh.putalpha(a); out = Image.new("RGBA", (im.width + 30, im.height + 40), (0, 0, 0, 0)); out.alpha_composite(sh, (24, 34)); out.alpha_composite(im, (0, 0))
    return out

def sphere(r, color, light=(0.32, 0.28)):
    s = 2 * r; yy, xx = np.mgrid[0:s, 0:s].astype(np.float32) / s
    d = np.sqrt((xx - .5) ** 2 + (yy - .5) ** 2); inside = (d <= .5)
    hl = np.exp(-(((xx - light[0]) ** 2 + (yy - light[1]) ** 2) / 0.018)); body = 1 - 0.55 * (d / .5) ** 2
    base = np.array(hexrgb(color), np.float32)
    rgb = base * body[..., None] + 255 * hl[..., None] * 0.85
    rim = np.clip((d - .43) / .07, 0, 1)[..., None]; rgb = rgb * (1 - rim * .35)
    a = (inside * 255).astype(np.uint8)
    im = Image.fromarray(np.dstack([rgb.clip(0, 255).astype(np.uint8), a]), "RGBA"); return im.filter(ImageFilter.SMOOTH)

def rays_bg(w, h, c1, c2, n=18, cx=None, cy=None, rot=0.0):
    """Fondo de rayos de sol con degradado radial vivo."""
    cx = w / 2 if cx is None else cx; cy = h * .42 if cy is None else cy
    yy, xx = np.mgrid[0:h // 3, 0:w // 3].astype(np.float32) * 3
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / math.hypot(w, h)
    a1, a2 = np.array(hexrgb(c1), np.float32), np.array(hexrgb(c2), np.float32)
    rgb = a1 * (1 - np.clip(d * 1.6, 0, 1))[..., None] + a2 * np.clip(d * 1.6, 0, 1)[..., None]
    ang = (np.arctan2(yy - cy, xx - cx) + rot) % (2 * math.pi / n * 2)
    ray = (ang < 2 * math.pi / n)[..., None] * 0.10
    rgb = rgb * (1 + ray)
    return Image.fromarray(rgb.clip(0, 255).astype(np.uint8)).resize((w, h), Image.BILINEAR).convert("RGBA")

def tablet3d(page, quad, bezel=(20, 18, 30, 255), size=(W, H), thick=26):
    """Tableta en perspectiva con canto (grosor) para que se vea 3D."""
    from motor import warp
    dev = device_frame(page, 900, color=bezel)
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    edge = warp(Image.new("RGBA", dev.size, shade(bezel, 0.55)), [(x + thick * .3, y + thick) for x, y in quad], size)
    m = Image.new("L", dev.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, dev.width - 1, dev.height - 1], radius=46, fill=255)
    e2 = Image.new("RGBA", dev.size, shade(bezel, .55)); e2.putalpha(m); edge = warp(e2, [(x + thick * .3, y + thick) for x, y in quad], size)
    lay.alpha_composite(edge); lay.alpha_composite(warp(dev, quad, size)); return lay

def card_flying(img, w, rot, blur=0, border=14):
    c = device_frame(img, w, r=18, pad=border, color=(255, 255, 255, 255))
    c = c.rotate(rot, Image.BICUBIC, expand=True)
    return c.filter(ImageFilter.GaussianBlur(blur)) if blur else c

def streaks(cv, p0, p1, color=(255, 255, 255), n=5, width=10, alpha=150, spread=60):
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    (x0, y0), (x1, y1) = p0, p1; ang = math.atan2(y1 - y0, x1 - x0); nx, ny = -math.sin(ang), math.cos(ang)
    for i in range(n):
        o = (i - (n - 1) / 2) * spread / max(1, n - 1); L_ = 0.55 + 0.45 * ((i * 37) % 10) / 10
        d.line([(x0 + nx * o, y0 + ny * o), (x0 + (x1 - x0) * L_ + nx * o, y0 + (y1 - y0) * L_ + ny * o)], fill=color + (alpha,), width=width)
    cv.alpha_composite(lay.filter(ImageFilter.GaussianBlur(3)))
