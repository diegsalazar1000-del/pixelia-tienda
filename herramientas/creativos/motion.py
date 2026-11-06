"""Motor de anuncios en movimiento de Pixelia (v2): fondos vivos, páginas que pasan en 3D, stickers que rebotan,
textos que golpean y precio con explosión. Genera reel 9:16 + imágenes 1:1, 4:5 y 9:16.
Uso: python3 motion.py anuncio.json
"""
import json, math, random, subprocess, sys, pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONTS = pathlib.Path("/usr/share/fonts/truetype/google-fonts")
def F(w, s): return ImageFont.truetype(str(FONTS / f"Poppins-{w}.ttf"), int(s))

W, H, FPS = 1080, 1920, 30
rng = random.Random(7)

# ---------- utilidades de animación ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(t): return 1 - (1 - t) ** 3
def ease_in_out(t): return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
def back_out(t, s=1.9): t -= 1; return t * t * ((s + 1) * t + s) + 1
def prog(t, a, b): return clamp((t - a) / (b - a))
def hexrgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def gradient_bg(w, h, colors, t):
    """Degradado diagonal que se mueve lentamente + manchas de luz."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ang = 0.6 + 0.25 * math.sin(t * 0.7)
    u = (xx * math.cos(ang) + yy * math.sin(ang)) / (w * abs(math.cos(ang)) + h * abs(math.sin(ang)))
    u = (u + 0.08 * math.sin(t * 1.3)) % 1.0
    cols = np.array([hexrgb(c) for c in colors + [colors[0]]], np.float32)
    n = len(colors); pos = u * n; i = np.floor(pos).astype(int) % n; f = (pos - np.floor(pos))[..., None]
    img = cols[i] * (1 - f) + cols[(i + 1)] * f
    out = Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGB")
    # manchas de luz
    glow = Image.new("L", (w, h), 0); g = ImageDraw.Draw(glow)
    for k in range(3):
        cx = w * (0.2 + 0.6 * ((k * 0.37 + 0.05 * t) % 1)); cy = h * (0.15 + 0.7 * ((k * 0.61 + 0.03 * t) % 1)); r = w * 0.35
        g.ellipse([cx - r, cy - r, cx + r, cy + r], fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(w * 0.12))
    out = Image.composite(Image.new("RGB", (w, h), (255, 255, 255)), out, glow)
    return out.convert("RGBA")

def perspective_coeffs(src, dst):
    m = []
    for (x, y), (u, v) in zip(dst, src):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); m.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    A = np.array(m, np.float64); B = np.array([p for s in src for p in s], np.float64)
    return np.linalg.solve(A, B)

def warp(img, quad, canvas_size):
    """Deforma img (rectángulo) al cuadrilátero quad=[tl,tr,br,bl] sobre un lienzo transparente."""
    w, h = img.size
    c = perspective_coeffs([(0, 0), (w, 0), (w, h), (0, h)], quad)
    return img.transform(canvas_size, Image.PERSPECTIVE, c, Image.BICUBIC)

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
    if alpha < 1: a = im.getchannel("A").point(lambda v: int(v * alpha)); im = im.copy(); im.putalpha(a)
    cv.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def highlight_word(cv, words, cx, y, font, colors, t0, t, hl_index=None, hl_color="#2E2823"):
    """Palabras que entran de una en una con rebote; una palabra resaltada con caja de color."""
    boxes = [text_box(w, font, "#FFFFFF", "#2E2823", 0) for w in words]
    gap = font.size * 0.28
    total = sum(b.width for b in boxes) + gap * (len(boxes) - 1)
    x = cx - total / 2
    for i, (w_, b) in enumerate(zip(words, boxes)):
        p = prog(t, t0 + i * 0.12, t0 + i * 0.12 + 0.35)
        if p > 0:
            s = back_out(p)
            if i == hl_index:
                pad = 14; bx = Image.new("RGBA", (b.width + 2 * pad, b.height + pad), (0, 0, 0, 0))
                ImageDraw.Draw(bx).rounded_rectangle([0, 0, bx.width - 1, bx.height - 1], radius=18, fill=hl_color)
                bx.alpha_composite(b, (pad, pad // 2)); b = bx
            if i != hl_index:  # sombra suave para que el blanco se lea sobre cualquier color
                sh = Image.new("RGBA", b.size, (0, 0, 0, 0)); sh.putalpha(b.getchannel("A").point(lambda v: int(v * 0.45)).filter(ImageFilter.GaussianBlur(6)))
                dark = Image.new("RGBA", b.size, (60, 25, 10, 0)); dark.putalpha(sh.getchannel("A"))
                paste_center(cv, dark, x + boxes[i].width / 2 + 3, y + 6, s, rot=(1 - p) * -8)
            paste_center(cv, b, x + boxes[i].width / 2, y, s, rot=(1 - p) * -8)
        x += boxes[i].width + gap

def starburst(r, color, points=18, inner=0.82):
    im = Image.new("RGBA", (2 * r + 4, 2 * r + 4), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(r + 2 + (r if k % 2 == 0 else r * inner) * math.cos(k * math.pi / points), r + 2 + (r if k % 2 == 0 else r * inner) * math.sin(k * math.pi / points)) for k in range(2 * points)]
    d.polygon(pts, fill=color); return im

def device_frame(page, w, r=46, pad=26, color=(36, 30, 26, 255)):
    p = page.resize((w, int(page.height * w / page.width)), Image.LANCZOS)
    fr = Image.new("RGBA", (p.width + 2 * pad, p.height + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(fr).rounded_rectangle([0, 0, fr.width - 1, fr.height - 1], radius=r, fill=color)
    fr.alpha_composite(rounded(p, int(r * .55)), (pad, pad)); return fr


# ---------- página que pasa (efecto libro) ----------
def flip_frame(page_a, page_b, p, shade=True):
    """Transición: la página A se levanta desde la derecha y pasa hacia la izquierda descubriendo B."""
    w, h = page_a.size
    out = page_b.copy().convert("RGBA")
    if p <= 0: return page_a.convert("RGBA")
    if p >= 1: return out
    # sombra que cae sobre B
    ang = p * math.pi                    # 0 → 180°
    x_edge = w / 2 + (w / 2) * math.cos(ang)   # borde libre de la hoja que gira (eje en la mitad)
    lift = math.sin(ang) * h * 0.06      # perspectiva: el borde libre "sube"
    # mitad izquierda de A sigue visible hasta que la hoja la tapa
    left_a = page_a.crop((0, 0, w // 2, h)).convert("RGBA")
    out.alpha_composite(left_a, (0, 0))
    if shade:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
        sd.rectangle([min(x_edge, w / 2), 0, max(x_edge, w / 2) + 40, h], fill=(0, 0, 0, int(70 * math.sin(ang))))
        out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(25)))
    if ang < math.pi / 2:   # cara frontal: mitad derecha de A
        face = page_a.crop((w // 2, 0, w, h)).convert("RGBA")
        quad = [(w / 2, 0), (x_edge, -lift), (x_edge, h + lift), (w / 2, h)]
    else:                   # cara trasera: mitad izquierda de B (aparece reflejada al terminar)
        face = page_b.crop((0, 0, w // 2, h)).convert("RGBA")
        quad = [(x_edge, -lift), (w / 2, 0), (w / 2, h), (x_edge, h + lift)]
    lay = warp(face, quad, (w, h))
    if shade:  # brillo según el ángulo
        k = abs(math.cos(ang)); dark = Image.new("RGBA", (w, h), (0, 0, 0, int(90 * (1 - k))))
        dark.putalpha(Image.fromarray((np.array(lay.getchannel("A")) * (0.35 * (1 - k))).astype(np.uint8)))
        lay.alpha_composite(dark)
    out.alpha_composite(lay)
    return out


# ---------- reel ----------
def build_reel(A, base, out_path):
    pages = [Image.open(base / p).convert("RGB") for p in A["paginas"]]
    pw = 860; ph = int(pages[0].height * pw / pages[0].width)
    pages = [p.resize((pw, ph), Image.LANCZOS) for p in pages]
    stickers = [Image.open(base / s).convert("RGBA") for s in A["stickers"]]
    stickers = [s.resize((int(s.width * 150 / max(s.size)), int(s.height * 150 / max(s.size))), Image.LANCZOS) for s in stickers]
    phone = Image.open(base / A["movil"]).convert("RGB")
    colors = A["colores"]
    f_big = F("Bold", 118); f_mid = F("Bold", 70); f_small = F("Medium", 44)
    T = A["segundos"]; total = int(T * FPS)
    ff = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)]
    proc = subprocess.Popen(ff, stdin=subprocess.PIPE)
    flips = A["flip_textos"]  # textos que aparecen con cada página
    n = len(pages); flip_start, flip_each = 2.7, 0.75
    falling = [(rng.uniform(80, W - 80), rng.uniform(-900, -100), rng.uniform(-40, 40), rng.uniform(300, 520), rng.choice(stickers)) for _ in range(16)]
    for fi in range(total):
        t = fi / FPS
        cv = gradient_bg(W, H, colors, t)
        # ===== Escena 1: gancho (0–2.2s) =====
        if t < 2.3:
            a = 1 - prog(t, 2.0, 2.3)
            hook = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            for li, line in enumerate(A["gancho"]):
                highlight_word(hook, line["palabras"], W / 2, 760 + li * 150, f_big, colors, 0.1 + li * 0.35, t, line.get("resaltar"), line.get("color", "#2E2823"))
            if a < 1: hook.putalpha(hook.getchannel("A").point(lambda v: int(v * a)))
            paste_center(cv, hook, W / 2, H / 2, 1 + (1 - a) * 0.15)
        # ===== Escena 2: páginas que pasan (2–~6.5s) =====
        t2_end = flip_start + flip_each * (n - 1) + 0.6
        if 2.2 <= t < t2_end + 0.3:
            k = min(n - 2, int(max(0, t - flip_start) // flip_each))
            p = ease_in_out(clamp(((t - flip_start) - k * flip_each) / (flip_each * 0.8)))
            page = flip_frame(pages[k], pages[k + 1], p if t >= flip_start else 0)
            dev = device_frame(page, pw)
            ent = back_out(prog(t, 2.2, 2.7))
            tilt = 4 * math.sin(t * 1.4)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); paste_center(lay, dev, W / 2, 1060, 0.6 + 0.4 * ent, rot=tilt)
            cv.alpha_composite(shadow(lay, 35, (0, 40))); cv.alpha_composite(lay)
            # texto superior que cambia con cada página
            idx = min(len(flips) - 1, k + (1 if p > 0.5 else 0))
            tb = text_box(flips[idx], f_mid, "#FFFFFF", "#2E2823", 0)
            pill = Image.new("RGBA", (tb.width + 60, tb.height + 24), (0, 0, 0, 0))
            ImageDraw.Draw(pill).rounded_rectangle([0, 0, pill.width - 1, pill.height - 1], radius=pill.height // 2, fill="#2E2823")
            pill.alpha_composite(tb, (30, 12))
            pop = back_out(clamp(((t - flip_start) - (idx - 1) * flip_each) / 0.3)) if idx > 0 else ent
            paste_center(cv, pill, W / 2, 470, max(0.01, pop))
            # stickers que saltan alrededor
            for j, st in enumerate(stickers[:6]):
                sp = back_out(prog(t, 2.3 + j * 0.25, 2.7 + j * 0.25))
                ang = j * 60 + t * 25
                sx = W / 2 + math.cos(math.radians(ang)) * 470; sy = max(640, 1060 + math.sin(math.radians(ang)) * 560)
                paste_center(cv, st, sx, sy, sp * 0.9, rot=10 * math.sin(t * 3 + j))
        # ===== Escena 3: móvil + lluvia de stickers =====
        s3a, s3b = t2_end + 0.2, t2_end + 3.0
        if s3a <= t < s3b + 0.3:
            for (x0, y0, rot0, spd, st) in falling:
                y = y0 + (t - s3a) * spd * 2.2
                if -200 < y < H + 200: paste_center(cv, st, x0, y, 1.1, rot=rot0 + (t - s3a) * 60)
            e = back_out(prog(t, s3a, s3a + 0.5))
            ph_ = device_frame(phone, 500, r=66, pad=20)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); paste_center(lay, ph_, W / 2 + (1 - e) * 700, 1080, 1.0, rot=-6 + 3 * math.sin(t * 2))
            cv.alpha_composite(shadow(lay, 35, (10, 40))); cv.alpha_composite(lay)
            highlight_word(cv, A["movil_texto"], W / 2, 300, F("Bold", 80), colors, s3a + 0.2, t, A.get("movil_resaltar"), "#2E2823")
        # ===== Escena 4: precio que golpea + CTA =====
        s4 = s3b
        if t >= s4:
            e = back_out(prog(t, s4, s4 + 0.45), 2.4)
            burst = starburst(300, "#FFF6E0")
            paste_center(cv, burst, W / 2, 860, e, rot=t * 20)
            pr = text_box(f"${A['precio']:g}", F("Bold", 230), "#C8442B")
            paste_center(cv, pr, W / 2, 830, e)
            old = text_box(f"antes ${A['tachado']:g}", F("Medium", 52), "#2E2823")
            od = ImageDraw.Draw(old); od.line([(10, old.height / 2 + 4), (old.width - 10, old.height / 2 + 4)], fill="#C8442B", width=6)
            paste_center(cv, old, W / 2, 1010, back_out(prog(t, s4 + 0.3, s4 + 0.6)))
            badge = starburst(95, "#2E2823", 12, 0.78); bd = ImageDraw.Draw(badge)
            bd.text((badge.width / 2, badge.height / 2), A.get("descuento", "-50%"), font=F("Bold", 50), fill="#FFFFFF", anchor="mm")
            paste_center(cv, badge, W / 2 + 270, 640, back_out(prog(t, s4 + 0.45, s4 + 0.75)), rot=-12)
            pulse = 1 + 0.05 * math.sin((t - s4) * 9)
            cta = text_box(A["cta"], F("Bold", 58), "#2E2823")
            btn = Image.new("RGBA", (cta.width + 110, cta.height + 50), (0, 0, 0, 0))
            ImageDraw.Draw(btn).rounded_rectangle([0, 0, btn.width - 1, btn.height - 1], radius=btn.height // 2, fill="#FFFFFF")
            btn.alpha_composite(cta, (55, 25))
            paste_center(cv, btn, W / 2, 1270, back_out(prog(t, s4 + 0.6, s4 + 0.95)) * pulse)
            dom = text_box(A["dominio"], F("Bold", 46), "#FFFFFF", "#2E2823", 0)
            paste_center(cv, dom, W / 2, 1420, prog(t, s4 + 0.9, s4 + 1.2))
            for j, st in enumerate(stickers[:4]):
                sp = back_out(prog(t, s4 + 0.2 + j * 0.1, s4 + 0.5 + j * 0.1))
                pos = [(200, 520), (880, 1150), (180, 1180), (900, 470)][j]
                paste_center(cv, st, *pos, sp, rot=15 * math.sin(t * 2 + j))
        proc.stdin.write(cv.convert("RGB").tobytes())
    proc.stdin.close(); proc.wait()


# ---------- imágenes estáticas llamativas ----------
def build_static(A, base, outdir):
    pages = [Image.open(base / p).convert("RGB") for p in A["paginas"]]
    stickers = [Image.open(base / s).convert("RGBA") for s in A["stickers"]]
    phone = Image.open(base / A["movil"]).convert("RGB")
    for v in A["estaticos"]:
        for name, (w, h) in {"1x1": (1080, 1080), "4x5": (1080, 1350), "9x16": (1080, 1920)}.items():
            cv = gradient_bg(w, h, v.get("colores", A["colores"]), v.get("fase", 0.0))
            story = name == "9x16"
            top = 260 if story else 70
            # titular con palabra resaltada
            fsize = 96 if w == h else 104
            f = F("Bold", fsize)
            for li, line in enumerate(v["titular"]):
                highlight_word(cv, line["palabras"], w / 2, top + 70 + li * fsize * 1.18, f, None, -10, 10, line.get("resaltar"), line.get("color", "#2E2823"))
            # composición: dos páginas abiertas en abanico + móvil
            cy = h * (0.60 if not story else 0.55)
            dw = int(w * (0.62 if not story else 0.78))
            lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            back = device_frame(pages[v.get("pagina_fondo", 1)], dw); front = device_frame(pages[v.get("pagina", 0)], dw)
            paste_center(lay, back, w * 0.46, cy - 40, 0.92, rot=9)
            paste_center(lay, front, w * 0.50, cy + 10, 1.0, rot=-5)
            ph_ = device_frame(phone, int(dw * 0.30), r=40, pad=12)
            paste_center(lay, ph_, w * 0.80, cy + dw * 0.18, 1.0, rot=8)
            cv.alpha_composite(shadow(lay, 30, (0, 30))); cv.alpha_composite(lay)
            for j, st in enumerate(stickers[:5]):
                sz = 130 / max(st.size)
                pos = [(0.12, 0.42), (0.90, 0.47), (0.10, 0.74), (0.14, 0.60), (0.90, 0.70)][j]
                paste_center(cv, st, w * pos[0], h * pos[1], sz * 1.1, rot=rng.uniform(-18, 18))
            # explosión de precio
            r = int(w * 0.13); b = starburst(r, "#FFF6E0")
            bd = ImageDraw.Draw(b); bd.text((b.width / 2, b.height / 2 - r * 0.12), f"${A['precio']:g}", font=F("Bold", r * 0.62), fill="#C8442B", anchor="mm")
            bd.text((b.width / 2, b.height / 2 + r * 0.38), f"antes ${A['tachado']:g}", font=F("Medium", r * 0.17), fill="#2E2823", anchor="mm")
            paste_center(cv, b, w * 0.84, h * (0.40 if w == h else 0.33), 0.9 if w == h else 1.0, rot=-10)
            # CTA
            cta = text_box(v.get("cta", A["cta"]), F("Bold", 44), "#2E2823")
            btn = Image.new("RGBA", (cta.width + 80, cta.height + 34), (0, 0, 0, 0))
            ImageDraw.Draw(btn).rounded_rectangle([0, 0, btn.width - 1, btn.height - 1], radius=btn.height // 2, fill="#FFFFFF")
            btn.alpha_composite(cta, (40, 17))
            by = h - (110 if not story else 360)
            paste_center(cv, btn, w / 2, by, 1.0)
            dom = text_box(A["dominio"], F("Bold", 34), "#FFFFFF", "#2E2823", 0)
            paste_center(cv, dom, w / 2, by + (80 if not story else 100), 1.0)
            cv.convert("RGB").save(outdir / f"{v['id']}-{name}.jpg", quality=93)


if __name__ == "__main__":
    A = json.load(open(sys.argv[1])); base = pathlib.Path(sys.argv[1]).parent
    out = base / "out-v2"; out.mkdir(exist_ok=True)
    build_static(A, base, out); print("imágenes ok")
    if "--sin-video" not in sys.argv:
        build_reel(A, base, out / "reel-v2-9x16.mp4"); print("reel ok")
