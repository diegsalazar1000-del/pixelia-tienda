"""Estilo 'Impacto 3D': letras en bloque 3D, esferas brillantes, rayos de luz, páginas que salen volando de la tablet,
collage de polaroids y precio que golpea. Cada reel usa una RECETA (paleta, rayos, giros, lados) distinta según la semilla;
la receta se guarda en el guion para poder repetir un estilo que guste.
Escenas: gancho → salen → collage → precio. Cada escena dura lo que su frase de voz.
"""
import math, random, subprocess
from PIL import Image, ImageDraw, ImageFilter
from motor import F, W, H, FPS, paste_center, text_box, device_frame, back_out, ease_in_out, prog, money
import looks as L

INK = "#1A1030"
PALETAS = {  # fondos de cada escena (centro, borde) + acentos
    "fiesta":  {"bg": [("#FF2E88", "#5B1FD6"), ("#FF7A00", "#FF2E88"), ("#00C2FF", "#5B1FD6"), ("#FFD60A", "#FF7A00")],
                "acc": ["#FFD60A", "#00C2FF", "#FF7A00", "#FF2E88", "#5B1FD6"], "precio": "#FF2E88", "boton": "#5B1FD6"},
    "tropical": {"bg": [("#00D2A0", "#006D77"), ("#FFB703", "#FB5607"), ("#3A86FF", "#023E8A"), ("#FFE066", "#FF8800")],
                 "acc": ["#FF006E", "#FFE066", "#3A86FF", "#FB5607", "#00D2A0"], "precio": "#FF006E", "boton": "#023E8A"},
    "galaxia": {"bg": [("#7B2FF7", "#160B3A"), ("#F72585", "#3A0CA3"), ("#4CC9F0", "#3A0CA3"), ("#B5179E", "#240046")],
                "acc": ["#4CC9F0", "#F72585", "#FFD60A", "#7B2FF7", "#B5179E"], "precio": "#FFD60A", "boton": "#F72585"},
    "dulce":   {"bg": [("#FF8FAB", "#C9184A"), ("#FFC8DD", "#FF6392"), ("#A0E7E5", "#4361EE"), ("#FFF3B0", "#FF9F1C")],
                "acc": ["#FFD166", "#4361EE", "#06D6A0", "#EF476F", "#FFFFFF"], "precio": "#C9184A", "boton": "#4361EE"},
}
NOTAS = ["#FFE066", "#FF8FC8", "#9BE7C4", "#A0C4FF"]

def receta(seed, base=None):
    """Elige paleta y detalles al azar (o respeta una receta guardada)."""
    r = random.Random(seed); R = dict(base or {})
    R.setdefault("paleta", r.choice(list(PALETAS))); R.setdefault("rayos", r.choice([12, 16, 20, 24]))
    R.setdefault("giro", r.choice([-1, 1])); R.setdefault("inclina", r.choice([-5, -3, 3, 5])); R.setdefault("seed", seed)
    return R

# ---------- utilidades ----------
def baked(im, blur=26, off=(10, 30), alpha=110):
    pad = blur * 2 + max(abs(off[0]), abs(off[1]))
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (30, 0, 40, 0)); sh.putalpha(im.getchannel("A").point(lambda v: alpha if v > 0 else 0))
    out.alpha_composite(sh, (pad + off[0], pad + off[1])); out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(im, (pad, pad)); return out

def ball(r, c, blur=0):
    s = L.sphere(r, c)
    if blur:
        p = Image.new("RGBA", (s.width + 6 * blur, s.height + 6 * blur), (0, 0, 0, 0)); p.alpha_composite(s, (3 * blur, 3 * blur)); s = p.filter(ImageFilter.GaussianBlur(blur))
    return s

def fit3d(text, maxw, start, face, side, depth):
    s = start
    while s > 60:
        im = L.text3d(text, F("Bold", s), face, side, int(depth * s / start))
        if im.width <= maxw: return im
        s -= 10
    return L.text3d(text, F("Bold", 60), face, side, 8)

def fit_font(text, maxw, start, fn):
    s = start; d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    while s > 24 and d.textlength(text, font=fn(s)) > maxw: s -= 2
    return fn(s)

def shake(cv, amt, rng):
    if amt <= 0.5: return cv
    m = int(amt) + 4; dx, dy = rng.uniform(-amt, amt), rng.uniform(-amt, amt)
    big = cv.resize((W + 2 * m, H + 2 * m), Image.BILINEAR)
    return big.crop((int(m + dx), int(m + dy), int(m + dx) + W, int(m + dy) + H))

def polaroid(img, w, cap):
    pw = w - 60; ph = min(int(pw * img.height / img.width), int(pw * 1.25))
    sc = max(pw / img.width, ph / img.height); im = img.resize((int(img.width * sc) + 1, int(img.height * sc) + 1), Image.LANCZOS).crop((0, 0, pw, ph))
    card = Image.new("RGBA", (w, ph + 170), "#FFFFFF"); card.paste(im, (30, 30))
    ImageDraw.Draw(card).text((w / 2, ph + 100), cap, font=fit_font(cap, w - 50, 52, L.LORA), fill="#2E2823", anchor="mm")
    return card

def postit(lines, color, size):
    f = F("Bold", 84)
    for ln in lines: f = min(f, fit_font(ln, size - 60, 84, lambda s: F("Bold", s)), key=lambda x: x.size)
    return L.postit(lines, color, size, f)

# ---------- reel ----------
class Reel:
    def __init__(self, B, pages, phone, R):
        self.B, self.R = B, R; P = PALETAS[R["paleta"]]; self.P = P; acc = P["acc"]; inc = R["inclina"]
        pg = list(pages) + list(pages) * 3; cover, p1, p2 = pg[0], pg[1], pg[2]
        ln = [" ".join(l.get("palabras", [])).upper() for l in B.get("gancho", [])][:3] or ["NUEVO"]
        sides = ["#3A0D8C", "#8A0046", "#14306E"]; faces = [acc[0], "#FFFFFF", acc[1]]
        self.H1 = [fit3d(t, W - 120, 260 if i == len(ln) - 1 else 200, faces[i % 3], sides[i % 3], 30).rotate(inc, Image.BICUBIC, expand=True) for i, t in enumerate(ln)]
        self.B1 = [(140, 260, ball(120, acc[0], 8), 0), (930, 380, ball(70, acc[1], 4), 1), (900, 1500, ball(150, acc[2]), 2),
                   (170, 1380, ball(90, acc[1]), 3), (560, 1750, ball(60, acc[0], 10), 4)]
        quad = [(170, 1380), (910, 1330), (1010, 1760), (60, 1830)]
        if R["giro"] < 0: quad = [(W - x, y) for x, y in (quad[1], quad[0], quad[3], quad[2])]
        tab = L.tablet3d(cover, quad); tab = tab.crop(tab.getbbox()); self.TAB = baked(tab, 36, (0, 40), 120)
        s = R["giro"]
        self.FLY = [(baked(L.card_flying(cover, 640, -8 * s)), W / 2 - 70 * s, 640), (baked(L.card_flying(p1, 380, 14 * s)), W / 2 - 240 * s, 1050),
                    (baked(L.card_flying(phone, 230, -12 * s)), W / 2 + 240 * s, 1000)]
        t2 = " ".join(B.get("movil_texto") or ["Tablet + móvil"]).upper()
        self.T2 = fit3d(t2, W - 120, 108, "#FFFFFF", "#9E1050", 20).rotate(-3 * s, Image.BICUBIC, expand=True)
        self.B2 = [(W / 2 + 320 * s, 560, ball(70, acc[0]), 0), (W / 2 - 390 * s, 520, ball(50, acc[1], 5), 1)]
        self.GLOW = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(self.GLOW).polygon([(230, 1420), (880, 1380), (1080, 300), (0, 300)], fill=(255, 245, 210, 95))
        self.GLOW = self.GLOW.filter(ImageFilter.GaussianBlur(50))
        tp = (list(B.get("textos_paginas") or []) + ["", "", ""])
        self.P3 = [(baked(polaroid(phone, 340, tp[2] or "en tu móvil").rotate(-10 * s, Image.BICUBIC, expand=True)), W / 2 - 320 * s, 700),
                   (baked(polaroid(p1, 520, tp[1] or "por dentro").rotate(9 * s, Image.BICUBIC, expand=True)), W / 2 + 180 * s, 520),
                   (baked(polaroid(cover, 660, tp[0] or B.get("titulo", "")).rotate(-3 * s, Image.BICUBIC, expand=True), 30, (16, 50)), W / 2 + 60 * s, 1110)]
        price = money(B["precio"]); st = [x for x in (B.get("stickers") or []) if x][:2] or ["PDF"]
        self.N3 = [(baked(postit(["SOLO", price], NOTAS[0], 360).rotate(-8, Image.BICUBIC, expand=True)), 250, 1530),
                   (baked(postit(st[0].split()[:2] if len(st[0]) > 9 else [st[0]], NOTAS[(R["seed"] % 3) + 1], 330).rotate(7, Image.BICUBIC, expand=True)), 800, 1560)]
        self.B3 = [(120, 200, ball(140, acc[3], 14), 0), (980, 1700, ball(160, acc[0], 16), 1), (900, 1300, ball(60, acc[2]), 2)]
        self.TAPE = L.tape()
        self.DEV4 = baked(device_frame(cover, 560, r=30, pad=16).rotate(-6, Image.BICUBIC, expand=True))
        self.SOLO = L.text3d("SOLO", F("Bold", 120), "#FFFFFF", "#B33A00", 16).rotate(inc, Image.BICUBIC, expand=True)
        self.PRICE = fit3d(price, W - 80, 330, P["precio"], "#4A0030", 40).rotate(inc, Image.BICUBIC, expand=True)
        self.OLD = None
        if B.get("tachado"):
            o = text_box(f"antes {money(B['tachado'])}", F("Bold", 60), INK); ImageDraw.Draw(o).line([(10, o.height / 2 + 6), (o.width - 10, o.height / 2 + 6)], fill=P["precio"], width=8)
            self.OLD = o.rotate(inc, Image.BICUBIC, expand=True)
        cta = str(B.get("cta") or "LO QUIERO")[:18]; bf = fit_font(cta, 620, 66, lambda s: F("Bold", s))
        btn = Image.new("RGBA", (700, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(btn)
        d.rounded_rectangle([0, 18, 699, 149], radius=70, fill=L.shade(P["boton"], .55)); d.rounded_rectangle([0, 0, 699, 130], radius=65, fill=P["boton"])
        d.text((350, 65), cta, font=bf, fill="#FFFFFF", anchor="mm"); self.BTN = btn
        self.B4 = [(150, 330, ball(110, acc[3]), 0), (960, 260, ball(80, acc[4], 6), 1), (930, 1250, ball(120, acc[1]), 2), (120, 1300, ball(60, acc[4], 8), 3)]
        self.dom = B.get("dominio", "pixeliadigital.app"); self.rng = random.Random(R["seed"])

    def bg(self, k, u, cy=None):
        c1, c2 = self.P["bg"][k]; return L.rays_bg(W, H, c1, c2, self.R["rayos"], cy=cy, rot=u * 0.15 * self.R["giro"])

    def floaters(self, cv, spec, u, t0=0.0):
        for i, (x, y, im, ph) in enumerate(spec):
            e = back_out(prog(u, t0 + i * 0.08, t0 + i * 0.08 + 0.45))
            paste_center(cv, im, x + 14 * math.sin(u * 1.3 + ph), y + 26 * math.sin(u * 1.7 + ph * 2), e)

    def gancho(self, u):
        cv = self.bg(0, u); self.floaters(cv, self.B1, u); hit = 0; n = len(self.H1)
        tot = sum(im.height * .78 for im in self.H1); y = H * 0.42 - tot / 2 + self.H1[0].height * .39
        for i, im in enumerate(self.H1):
            t0 = 0.15 + i * 0.35; p = prog(u, t0, t0 + 0.4)
            if p > 0:
                if i < n - 1: paste_center(cv, im, W / 2 + 10, y - (1 - back_out(p)) * 900)
                else: paste_center(cv, im, W / 2 + 10, y, 1 + 1.4 * (1 - ease_in_out(p)), alpha=min(1, p * 3))
                if 0 < u - (t0 + 0.4) < 0.25: hit = (18 if i == n - 1 else 8) * (1 - (u - t0 - 0.4) / 0.25)
            y += im.height * .78
        return shake(cv, hit, self.rng)

    def salen(self, u):
        cv = self.bg(1, u, H * .78)
        e = back_out(prog(u, 0, 0.45)); paste_center(cv, self.TAB, W / 2, 1580 + (1 - e) * 700)
        g = prog(u, 0.4, 0.8)
        if g > 0: lay = self.GLOW.copy(); lay.putalpha(lay.getchannel("A").point(lambda v: int(v * g))); cv.alpha_composite(lay)
        for i, (im, x, y) in reversed(list(enumerate(self.FLY))):
            p = prog(u, 0.55 + i * 0.25, 1.15 + i * 0.25)
            if p <= 0: continue
            q = back_out(p, 1.4); sx, sy = W / 2, 1520
            paste_center(cv, im, sx + (x - sx) * q, sy + (y - sy) * q + 10 * math.sin(u * 2 + i), 0.2 + 0.8 * q, rot=(1 - q) * 40 * (1 if i % 2 else -1))
        paste_center(cv, self.T2, W / 2, 230 - (1 - back_out(prog(u, 1.4, 1.8))) * 500); self.floaters(cv, self.B2, u, 1.2)
        return cv

    def collage(self, u):
        cv = self.bg(2, u, H * .5); self.floaters(cv, self.B3, u); hit = 0
        for i, (im, x, y) in enumerate(self.P3 + self.N3):
            t0 = 0.1 + i * 0.4; p = prog(u, t0, t0 + 0.28)
            if p <= 0: continue
            paste_center(cv, im, x, y, 1 + 0.6 * (1 - ease_in_out(p)), alpha=min(1, p * 2.5))
            if i == 2 and p >= 1: paste_center(cv, self.TAPE, x, y - 410, back_out(prog(u, t0 + 0.3, t0 + 0.5)), rot=4)
            if 0 < u - (t0 + 0.28) < 0.15: hit = 10
        return shake(cv, hit, self.rng)

    def precio(self, u):
        cv = self.bg(3, u, H * .45); self.floaters(cv, self.B4, u)
        paste_center(cv, self.DEV4, 560, 470 - (1 - back_out(prog(u, 0, 0.45))) * 900)
        paste_center(cv, self.SOLO, W / 2, 830, back_out(prog(u, 0.35, 0.65)))
        p = prog(u, 0.6, 0.85); hit = 0
        if p > 0: paste_center(cv, self.PRICE, W / 2, 1060, 1 + 1.8 * (1 - ease_in_out(p)), alpha=min(1, p * 3))
        if 0 < u - 0.85 < 0.3: hit = 22 * (1 - (u - 0.85) / 0.3)
        if self.OLD: paste_center(cv, self.OLD, W / 2, 1300, back_out(prog(u, 1.1, 1.4)))
        paste_center(cv, self.BTN, W / 2, 1530, back_out(prog(u, 1.4, 1.75)) * (1 + 0.05 * math.sin(max(0, u - 1.75) * 8)))
        a = prog(u, 1.7, 2.1)
        paste_center(cv, text_box(self.dom, F("Bold", 44), INK), W / 2, 1760, alpha=a)
        paste_center(cv, text_box("Paga con PayPal · Visa · Mastercard · Binance", F("Medium", 30), INK), W / 2, 1820, alpha=a)
        return shake(cv, hit, self.rng)

# ---------- guion, tiempos y efectos de sonido ----------
MIN_DUR = {"gancho": 3.0, "salen": 3.6, "collage": 3.4, "precio": 4.2}
XF = 0.18

def make_story(B):
    gv = B.get("guion_voz") or {}
    return {"estilo": "impacto", "concepto": "Impacto 3D", "voz": (B.get("voz") or {}).get("genero", "femenina"), "musica": "lofi", "copy": (B.get("copy") or {}).get("A", {}),
            "escenas": [{"tipo": "gancho", "lineas": B.get("gancho", []), "voz": gv.get("gancho", "")},
                        {"tipo": "salen", "voz": gv.get("paginas", "")},
                        {"tipo": "collage", "voz": gv.get("movil", "")},
                        {"tipo": "precio", "voz": gv.get("precio", "")}]}

def timeline(story, n_hook=3):
    t, scenes, ev = 0.0, [], []
    for k, sc in enumerate(story["escenas"]):
        words = len(str(sc.get("voz") or "").split())
        d = round(min(6.5, max(MIN_DUR[sc["tipo"]], words * 0.42 + 1.0)), 2)
        scenes.append({"tipo": sc["tipo"], "start": round(t, 2), "dur": d}); tp = sc["tipo"]
        if k: ev.append(["whoosh", t - 0.22, 0.8, 1.0 + 0.1 * k])
        if tp == "gancho":
            for i in range(5): ev.append(["pop", t + i * 0.08 + 0.1, 0.35, 1.4 + 0.1 * i])
            for i in range(n_hook):
                t0 = t + 0.15 + i * 0.35; ev.append(["whoosh", t0 - 0.05, 0.5, 1.4])
                ev.append(["impact", t0 + 0.38, 1.0, 1.0] if i == n_hook - 1 else ["thud", t0 + 0.38, 0.8, 1.0])
        elif tp == "salen":
            ev += [["whoosh", t, 0.8, 0.7], ["sparkle", t + 0.4, 0.6, 1.0]]
            for i in range(3): ev.append(["whoosh", t + 0.55 + i * 0.25, 0.7, 1.2 + 0.15 * i])
            ev.append(["thud", t + 1.75, 0.7, 1.0]); ev.append(["pop", t + 1.25, 0.4, 1.6])
        elif tp == "collage":
            for i in range(5): ev.append(["thud", t + 0.1 + i * 0.4 + 0.27, 0.75, 1.0 + 0.05 * i])
            ev.append(["click", t + 1.3, 0.6, 1.0])
        elif tp == "precio":
            ev += [["whoosh", t, 0.7, 0.8], ["pop", t + 0.5, 0.6, 1.0], ["impact", t + 0.83, 1.0, 1.0], ["sparkle", t + 0.9, 0.8, 1.0],
                   ["pop", t + 1.2, 0.5, 1.3], ["click", t + 1.6, 0.9, 1.0]]
        t += d
    return {"scenes": scenes, "T": round(t, 2), "sfx": [[a, round(b, 3), c, e] for a, b, c, e in ev], "music_level": 0.55}

def build(B, pages, phone, out_path, seed=1, R=None, story=None, only_times=None):
    R = receta(seed, R); story = story or make_story(B); story["receta"] = R
    TL = timeline(story, len([l for l in B.get("gancho", [])][:3]) or 1); TL["receta"] = R
    rl = Reel(B, pages, phone, R); fns = {"gancho": rl.gancho, "salen": rl.salen, "collage": rl.collage, "precio": rl.precio}
    sc = TL["scenes"]
    def frame(t):
        i = max(k for k, s in enumerate(sc) if s["start"] <= t + 1e-6); s = sc[i]; u = t - s["start"]
        cv = fns[s["tipo"]](u)
        if i < len(sc) - 1 and u > s["dur"] - XF:
            a = (u - (s["dur"] - XF)) / XF; z = 1 + 0.35 * a * a
            big = cv.resize((int(W * z), int(H * z)), Image.BILINEAR); x0, y0 = (big.width - W) // 2, (big.height - H) // 2; cv = big.crop((x0, y0, x0 + W, y0 + H))
        if i > 0 and u < 0.15: cv.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(200 * (1 - u / 0.15)))))
        return cv.convert("RGB")
    if only_times: return [frame(t) for t in only_times]
    ff = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)]
    proc = subprocess.Popen(ff, stdin=subprocess.PIPE)
    for fi in range(int(TL["T"] * FPS)): proc.stdin.write(frame(fi / FPS).tobytes())
    proc.stdin.close(); proc.wait()
    TL["story"] = True
    return TL, story

def stills(B, pages, phone, outdir, seed=1, R=None):
    """3 imágenes 9:16 (gancho, collage, precio) con la misma receta del reel."""
    R = receta(seed, R); rl = Reel(B, pages, phone, R); files = []
    for name, im in (("A", rl.gancho(3.0)), ("B", rl.collage(3.2)), ("C", rl.precio(3.0))):
        p = outdir / f"{name}-9x16.jpg"; im.convert("RGB").save(p, quality=92); files.append(p)
    return files
