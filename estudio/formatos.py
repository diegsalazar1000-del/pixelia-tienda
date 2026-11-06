"""Formatos de anuncio distintos (no solo colores): chat, notificaciones, scroll en el móvil, escribir sobre la página,
antes/después, top 3 y video real de fondo (Pexels). Se registran como escenas del motor de guiones (story.py).
"""
import hashlib, json, math, os, pathlib, subprocess, urllib.parse, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import motor as M
from motor import W, H, F, INK, S, back_out, ease_in_out, prog, clamp, paste_center, text_box, fit_font, lines_block

HERE = pathlib.Path(__file__).parent
def SERIF(s): return ImageFont.truetype(str(HERE / "fonts" / "Lora-Medium.ttf"), int(s))

def wrap(text, font, maxw):
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1))); lines, cur = [], ""
    for w in str(text).split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def phone_shell(x0, y0, x1, y1, r=70):
    """Marco de móvil (bisel oscuro) y máscara de la pantalla."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x0 - 22, y0 - 22, x1 + 22, y1 + 22], radius=r + 18, fill=(20, 18, 24, 255))
    mask = Image.new("L", (W, H), 0); ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x1, y1], radius=r, fill=255)
    return lay, mask

def compose_phone(cv, screen, box, rot=0.0, scale=1.0):
    x0, y0, x1, y1 = box
    shell, mask = phone_shell(x0, y0, x1, y1)
    full = Image.new("RGBA", (W, H), (0, 0, 0, 0)); full.alpha_composite(shell)
    scr = Image.new("RGBA", (W, H), (0, 0, 0, 0)); scr.paste(screen, (x0, y0)); full.paste(scr, (0, 0), mask)
    d = ImageDraw.Draw(full); d.rounded_rectangle([W / 2 - 90, y0 + 14, W / 2 + 90, y0 + 46], radius=16, fill=(20, 18, 24, 255))  # isla
    if rot or scale != 1:
        full = full.rotate(rot, Image.BICUBIC, center=(W / 2, H / 2)) if rot else full
        if scale != 1:
            big = full.resize((int(W * scale), int(H * scale)), Image.BILINEAR)
            full = Image.new("RGBA", (W, H), (0, 0, 0, 0)); full.alpha_composite(big, (int((W - big.width) / 2), int((H - big.height) / 2)))
    cv.alpha_composite(M.shadow(full, 40, (0, 40))); cv.alpha_composite(full)

# ---------- 💬 chat ----------
CHAT_BOX = (130, 250, 950, 1690)
def chat_times(msgs):
    t, out = 0.35, []
    for m in msgs:
        typing = 0.45 if m.get("de") != "yo" else 0.15
        out.append((t, t + typing)); t += typing + max(0.55, 0.03 * len(m.get("texto", ""))) + (0.6 if m.get("img") else 0)
    return out, t

def sc_chat(cv, sc, u, d, X):
    x0, y0, x1, y1 = CHAT_BOX; sw, sh = x1 - x0, y1 - y0
    scr = Image.new("RGBA", (sw, sh), (236, 229, 221, 255)); g = ImageDraw.Draw(scr)
    for k in range(0, sh, 46): g.text((k * 7 % sw, k), "·", font=F("Bold", 30), fill=(220, 212, 202, 255))  # textura suave
    hdr = 150; g.rectangle([0, 0, sw, hdr], fill=(32, 120, 104, 255))
    g.ellipse([30, 62, 100, 132], fill=(255, 255, 255, 230))
    g.text((65, 97), (sc.get("nombre") or "A")[0].upper(), font=F("Bold", 36), fill=(32, 120, 104, 255), anchor="mm")
    g.text((120, 72), sc.get("nombre") or "Amiga", font=F("Bold", 40), fill="#FFFFFF")
    times, _ = chat_times(sc["mensajes"]); typing_now = False
    f = F("Medium", 38); maxw = sw * 0.68; y = hdr + 30; bubbles = []
    for m, (ta, tb) in zip(sc["mensajes"], times):
        if u < ta: break
        if u < tb: typing_now = m.get("de") != "yo"; break
        lines = wrap(m["texto"], f, maxw); lh = 50
        bw = max((f.getlength(l) for l in lines), default=0) + 44; bh = len(lines) * lh + 30
        if m.get("img"): bh += int(maxw * 0.62) + 16; bw = max(bw, maxw + 24)
        bubbles.append((m, lines, bw, bh, tb))
    total = sum(b[3] + 18 for b in bubbles) + (90 if typing_now else 0)
    y = hdr + 30 - max(0, total - (sh - hdr - 60))  # se desplaza hacia arriba como un chat real
    for m, lines, bw, bh, tb in bubbles:
        me = m.get("de") == "yo"; e = back_out(prog(u, tb, tb + 0.25))
        b = Image.new("RGBA", (int(bw), int(bh)), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
        bd.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=26, fill=(217, 253, 211, 255) if me else (255, 255, 255, 255))
        yy = 15
        if m.get("img"):
            th = X["pages"][min(len(X["pages"]) - 1, int(m.get("pagina", 0)))].copy(); th.thumbnail((int(maxw), int(maxw * 0.62)))
            b.paste(th, (12, 12)); yy = th.height + 24
        for l in lines: bd.text((22, yy), l, font=f, fill=(30, 30, 30, 255)); yy += 50
        bd.text((bw - 70, bh - 30), "✓✓" if me else "", font=F("Medium", 20), fill=(83, 189, 235, 255))
        if e > 0.01:
            sb = b.resize((max(1, int(b.width * e)), max(1, int(b.height * e)))) if e < 0.999 else b
            scr.alpha_composite(sb, (int(sw - bw - 26) if me else 26, int(y)))
        y += bh + 18
    if typing_now:
        tb_ = Image.new("RGBA", (130, 70), (0, 0, 0, 0)); td = ImageDraw.Draw(tb_); td.rounded_rectangle([0, 0, 129, 69], radius=26, fill="#FFFFFF")
        for k in range(3):
            a = 0.5 + 0.5 * math.sin(u * 10 - k); td.ellipse([24 + k * 30, 28 - 6 * a, 42 + k * 30, 46 - 6 * a], fill=(150, 150, 150, 255))
        scr.alpha_composite(tb_, (26, int(min(y, sh - 90))))
    g.rectangle([0, sh - 90, sw, sh], fill=(240, 240, 240, 255)); g.rounded_rectangle([20, sh - 75, sw - 110, sh - 15], radius=30, fill="#FFFFFF")
    g.text((50, sh - 45), "Mensaje", font=F("Medium", 32), fill=(160, 160, 160, 255), anchor="lm")
    g.ellipse([sw - 90, sh - 80, sw - 20, sh - 10], fill=(32, 120, 104, 255))
    compose_phone(cv, scr, CHAT_BOX, rot=-2 + 1.5 * math.sin(u * 0.8), scale=0.92 + 0.08 * back_out(prog(u, 0, 0.4)))

# ---------- 🔔 notificaciones ----------
def sc_notificaciones(cv, sc, u, d, X):
    x0, y0, x1, y1 = CHAT_BOX; sw, sh = x1 - x0, y1 - y0
    bg = X["pages"][0].resize((sw, int(X["pages"][0].height * sw / X["pages"][0].width))).crop((0, 0, sw, sh)).filter(ImageFilter.GaussianBlur(22))
    scr = Image.blend(bg.convert("RGB"), Image.new("RGB", (sw, sh), hexrgb_s(S["colors"][0])), 0.45).convert("RGBA"); g = ImageDraw.Draw(scr)
    g.text((sw / 2, 230), "9:41", font=F("Bold", 170), fill="#FFFFFF", anchor="mm")
    g.text((sw / 2, 350), sc.get("fecha") or "lunes, 4 de enero", font=F("Medium", 40), fill=(255, 255, 255, 230), anchor="mm")
    items = sc["items"][:4]; f1, f2 = F("Bold", 34), F("Medium", 32)
    for i, it in enumerate(items):
        t0 = 0.4 + i * 0.65; e = back_out(prog(u, t0, t0 + 0.35))
        if e <= 0.01: continue
        card = Image.new("RGBA", (sw - 60, 170), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
        cd.rounded_rectangle([0, 0, card.width - 1, 169], radius=36, fill=(255, 255, 255, 215))
        col = S["colors"][i % len(S["colors"])]; cd.rounded_rectangle([24, 40, 104, 120], radius=22, fill=col)
        cd.text((64, 80), (it.get("app") or "A")[0].upper(), font=F("Bold", 40), fill="#FFFFFF", anchor="mm")
        cd.text((128, 34), (it.get("app") or "")[:24], font=F("Medium", 26), fill=(90, 90, 90, 255))
        cd.text((card.width - 30, 34), "ahora", font=F("Medium", 24), fill=(120, 120, 120, 255), anchor="ra")
        cd.text((128, 70), it.get("titulo", "")[:30], font=f1, fill=(20, 20, 20, 255))
        cd.text((128, 112), it.get("texto", "")[:38], font=f2, fill=(50, 50, 50, 255))
        y = 440 + i * 190 - (1 - e) * 120
        scr.alpha_composite(card if e >= 0.999 else card.resize((card.width, max(1, int(170 * e)))), (30, int(y)))
    compose_phone(cv, scr, CHAT_BOX, rot=2 * math.sin(u * 0.7), scale=0.92 + 0.08 * back_out(prog(u, 0, 0.4)))

def hexrgb_s(h): return M.hexrgb(h) if isinstance(h, str) else (120, 90, 255)

# ---------- 👆 scroll en el móvil ----------
def sc_scroll(cv, sc, u, d, X):
    x0, y0, x1, y1 = CHAT_BOX; sw, sh = x1 - x0, y1 - y0
    idx = sc.get("paginas") or list(range(min(5, len(X["pages"]))))
    strip_pages = [X["pages"][i].resize((sw - 40, int(X["pages"][i].height * (sw - 40) / X["pages"][i].width))) for i in idx]
    total = sum(p.height + 24 for p in strip_pages)
    off = (total - sh + 60) * ease_in_out(clamp((u - 0.4) / max(0.5, d - 0.8)))
    scr = Image.new("RGBA", (sw, sh), (245, 243, 240, 255)); y = 30 - off
    for p in strip_pages:
        if y + p.height > 0 and y < sh: scr.paste(p, (20, int(y)))
        y += p.height + 24
    compose_phone(cv, scr, CHAT_BOX, rot=-3 + 1.5 * math.sin(u), scale=0.9 + 0.1 * back_out(prog(u, 0, 0.4)))
    fy = 1350 - 500 * ((u * 1.1) % 1.0); a = math.sin(math.pi * ((u * 1.1) % 1.0))  # dedo deslizando
    dot = Image.new("RGBA", (130, 130), (0, 0, 0, 0)); ImageDraw.Draw(dot).ellipse([0, 0, 129, 129], fill=(255, 255, 255, int(150 * a)), outline=(255, 255, 255, int(230 * a)), width=5)
    cv.alpha_composite(dot, (int(W / 2 + 120), int(fy)))
    from story import caption
    caption(cv, sc.get("texto", ""), 170, u, 0.1)

# ---------- ✍️ escribir sobre la página ----------
def sc_escribir(cv, sc, u, d, X):
    page = X["pages"][min(len(X["pages"]) - 1, int(sc.get("pagina", 1)))].copy().convert("RGBA")
    pw, ph = page.size; g = ImageDraw.Draw(page)
    card = (int(pw * 0.08), int(ph * 0.45), int(pw * 0.92), int(ph * 0.86))
    g.rounded_rectangle(card, radius=24, fill=(255, 252, 240, 245), outline=(230, 220, 190, 255), width=3)
    lines = [str(x) for x in (sc.get("lineas") or ["Mi meta del mes"])][:4]; f = SERIF(max(26, int(pw * 0.055)))
    n_chars = sum(len(l) for l in lines); shown = int(n_chars * clamp((u - 0.5) / max(0.6, d - 1.1)))
    y = card[1] + 30; pen = None; c = 0
    for l in lines:
        k = max(0, min(len(l), shown - c)); txt = l[:k]
        g.text((card[0] + 50, y), txt, font=f, fill=(40, 50, 90, 255))
        if 0 < k < len(l) or (k == len(l) and shown - c < len(l) + 1 and k): pen = (card[0] + 50 + f.getlength(txt), y + f.size * 0.8)
        g.ellipse([card[0] + 18, y + f.size * 0.35, card[0] + 32, y + f.size * 0.35 + 14], fill=S["colors"][0])
        c += len(l); y += int(f.size * 1.55)
    from story import device_layer, caption
    lay = device_layer(page, W / 2, 1060, back_out(prog(u, 0, 0.4)), rot=-2)
    cv.alpha_composite(M.shadow(lay, 35, (0, 40))); cv.alpha_composite(lay)
    if pen:  # lápiz que sigue la escritura
        dev_w = M.device_frame(page, page.width).width; sx = W / 2 - dev_w / 2 + 26 + pen[0]; sy = 1060 - (ph + 52) / 2 + 26 + pen[1]
        p = Image.new("RGBA", (60, 260), (0, 0, 0, 0)); pd = ImageDraw.Draw(p)
        pd.rounded_rectangle([12, 0, 48, 210], radius=16, fill=S["hl_fill"]); pd.polygon([(12, 210), (48, 210), (30, 258)], fill=(240, 220, 190, 255))
        paste_center(cv, p.rotate(-28, expand=True), sx + 50, sy - 100, 1.0)
    caption(cv, sc.get("texto", ""), 300, u, 0.1)

# ---------- 🔀 antes / después ----------
def sc_antes_despues(cv, sc, u, d, X):
    split = W * (1 - 0.5 * ease_in_out(clamp(u / 0.6)))
    left = Image.new("RGBA", (W, H), (70, 66, 72, 255)); ld = ImageDraw.Draw(left)
    rnd = np.random.default_rng(5)
    for k, it in enumerate((sc.get("antes") or ["pendientes", "olvidos", "estrés"])[:4] * 2):  # notas desordenadas
        x, y = 40 + rnd.uniform(0, 380), 520 + k * 150 + rnd.uniform(-30, 30)
        note = Image.new("RGBA", (360, 120), (0, 0, 0, 0)); nd = ImageDraw.Draw(note)
        nd.rectangle([0, 0, 359, 119], fill=(230, 226, 215, 255)); nd.text((20, 36), it[:16], font=F("Bold", 40), fill=(90, 85, 80, 255))
        nd.line([(12, 60), (340, 70)], fill=(200, 60, 60, 255), width=5)
        left.alpha_composite(note.rotate(rnd.uniform(-25, 25) + 4 * math.sin(u * 6 + k), expand=True), (int(x), int(y)))
    paste_center(left, M.text_box("ANTES", F("Bold", 92), "#FFFFFF"), W / 4, 330)
    right = M.background(W, H, S["colors"], X["t"])
    from story import device_layer
    lay = device_layer(X["pages"][min(len(X["pages"]) - 1, int(sc.get("pagina", 1)))], W * 0.75, 1080, 0.55)
    right.alpha_composite(M.shadow(lay, 30, (0, 30))); right.alpha_composite(lay)
    paste_center(right, M.text_box("AHORA", F("Bold", 92), S["text"] if S["name"] != "minimal" else INK), W * 0.75, 330)
    out = right.copy(); out.paste(left.crop((0, 0, int(split), H)), (0, 0))
    ImageDraw.Draw(out).rectangle([split - 6, 0, split + 6, H], fill="#FFFFFF")
    cv.alpha_composite(out)
    if sc.get("texto"):
        from story import caption
        caption(cv, sc["texto"], 1600, u, 0.7)

# ---------- 🏆 top 3 ----------
def sc_top3(cv, sc, u, d, X):
    items = (sc.get("items") or ["Fácil de usar", "Todo en uno", "Bonito"])[:3]; n = len(items); seg = d / n
    i = min(n - 1, int(u // seg)); v = u - i * seg
    from story import caption
    if sc.get("titulo"): caption(cv, sc["titulo"], 230, u, 0.0)
    e = back_out(prog(v, 0, 0.35))
    num = M.text_box(str(i + 1), F("Bold", 520), S["hl_fill"] if S["name"] != "minimal" else S["colors"][0])
    paste_center(cv, num, W / 2, 720, e, rot=(1 - e) * 20)
    paste_center(cv, M.text_box(items[i], fit_font([items[i]], W - 140, 92), S["text"] if not S.get("boxed") else "#FFFFFF"), W / 2, 1110, back_out(prog(v, 0.15, 0.5)))
    pg = X["pages"][(i + 1) % len(X["pages"])]
    th = M.device_frame(pg, 520, max_h=420, r=30, pad=14)
    paste_center(cv, th, W / 2, 1460, back_out(prog(v, 0.25, 0.6)), rot=-4 + 8 * (i % 2))

# ---------- 🎬 video real de fondo (Pexels, gratis con licencia comercial) ----------
BROLL_DIR = pathlib.Path(os.environ.get("PIXELIA_DIR", "/pixelia")) / "storage" / "broll"
def pexels_video(query):
    """Video real de fondo: Pixabay (gratis) o Pexels (gratis), lo que tenga clave. Se guarda para reutilizarlo."""
    if not query: return None
    BROLL_DIR.mkdir(parents=True, exist_ok=True)
    out = BROLL_DIR / (hashlib.sha1(query.lower().encode()).hexdigest()[:16] + ".mp4")
    if out.exists() and out.stat().st_size > 50000: return out
    if os.environ.get("PIXABAY_API_KEY", "").strip():
        v = pixabay_video(query, out)
        if v: return v
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key: return None
    try:
        q = urllib.parse.urlencode({"query": query, "orientation": "portrait", "size": "medium", "per_page": 8})
        req = urllib.request.Request(f"https://api.pexels.com/v1/videos/search?{q}", headers={"Authorization": key, "User-Agent": "PixeliaEstudio/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r: data = json.load(r)
        best = None
        for v in data.get("videos", []):
            if v.get("duration", 0) < 4: continue
            for fl in v.get("video_files", []):
                w, h = fl.get("width") or 0, fl.get("height") or 0
                if h > w and 900 <= h <= 2000 and (best is None or abs(h - 1280) < abs(best["height"] - 1280)): best = fl
            if best: break
        if not best: return None
        with urllib.request.urlopen(urllib.request.Request(best["link"], headers={"User-Agent": "PixeliaEstudio/1.0"}), timeout=90) as r: out.write_bytes(r.read())
        return out
    except Exception as e:
        print("Pexels:", e); return None

def pixabay_video(query, out):
    try:
        q = urllib.parse.urlencode({"key": os.environ["PIXABAY_API_KEY"].strip(), "q": query[:100], "video_type": "film", "safesearch": "true", "per_page": 10})
        with urllib.request.urlopen(urllib.request.Request(f"https://pixabay.com/api/videos/?{q}", headers={"User-Agent": "PixeliaEstudio/1.0"}), timeout=30) as r:
            hits = json.load(r).get("hits", [])
        if not hits and " " in query:  # búsqueda más simple si no hubo resultados
            return pixabay_video(" ".join(query.split()[:2]), out)
        for h in hits:
            if (h.get("duration") or 0) < 4: continue
            vids = h.get("videos") or {}
            # preferimos verticales; si no, uno horizontal (se recorta al centro)
            cand = sorted([v for v in vids.values() if v.get("url") and (v.get("width") or 0) >= 640], key=lambda v: (not (v.get("height", 0) > v.get("width", 0)), abs((v.get("width") or 0) - 1280)))
            if not cand: continue
            with urllib.request.urlopen(urllib.request.Request(cand[0]["url"], headers={"User-Agent": "PixeliaEstudio/1.0"}), timeout=90) as r: out.write_bytes(r.read())
            if out.stat().st_size > 50000: return out
    except Exception as e:
        print("Pixabay:", e)
    return None

def stock_photo(query):
    """Foto real de Pixabay (gratis, uso comercial) para fondos de imágenes. Se guarda para reutilizarla."""
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key or not query: return None
    BROLL_DIR.mkdir(parents=True, exist_ok=True)
    out = BROLL_DIR / ("img-" + hashlib.sha1(query.lower().encode()).hexdigest()[:16] + ".jpg")
    if out.exists() and out.stat().st_size > 20000: return Image.open(out).convert("RGB")
    try:
        for q_ in (query, " ".join(query.split()[:2])):
            q = urllib.parse.urlencode({"key": key, "q": q_[:100], "image_type": "photo", "orientation": "vertical", "safesearch": "true", "per_page": 10})
            with urllib.request.urlopen(urllib.request.Request(f"https://pixabay.com/api/?{q}", headers={"User-Agent": "PixeliaEstudio/1.0"}), timeout=30) as r:
                hits = json.load(r).get("hits", [])
            if hits: break
        if not hits: return None
        h = max(hits[:5], key=lambda x: x.get("likes", 0))
        with urllib.request.urlopen(urllib.request.Request(h.get("largeImageURL") or h["webformatURL"], headers={"User-Agent": "PixeliaEstudio/1.0"}), timeout=60) as r:
            out.write_bytes(r.read())
        return Image.open(out).convert("RGB")
    except Exception as e:
        print("Pixabay foto:", e); return None

class BrollReader:
    """Lee el video cuadro a cuadro a media resolución (poca memoria en el VPS)."""
    def __init__(self, path, fps, dur):
        self.w, self.h = W // 2, H // 2; self.n = 0; self.last = None
        vf = f"scale={self.w}:{self.h}:force_original_aspect_ratio=increase,crop={self.w}:{self.h},fps={fps}"
        self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-stream_loop", "-1", "-i", str(path), "-t", str(dur + 1), "-vf", vf,
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.fps = fps
    def frame(self, u):
        want = int(u * self.fps)
        while self.n <= want:
            raw = self.p.stdout.read(self.w * self.h * 3)
            if len(raw) < self.w * self.h * 3: break
            self.last = Image.frombytes("RGB", (self.w, self.h), raw); self.n += 1
        return self.last

def sc_broll(cv, sc, u, d, X):
    rd = X.get("broll", {}).get(id(sc))
    if rd is None and sc.get("busqueda") and "bgr_sc" not in X: X["bgr_sc"] = {}
    if rd is None and sc.get("busqueda"):  # modo Pixabay: se abre al llegar a la escena
        if id(sc) not in X["bgr_sc"]:
            v = pexels_video(sc["busqueda"]); X["bgr_sc"][id(sc)] = BrollReader(v, X.get("fps", 30), d + 0.5) if v else None
        rd = X["bgr_sc"][id(sc)]
    fr = rd.frame(u) if rd else None
    if fr is not None:
        bg = fr.resize((W, H), Image.BILINEAR).convert("RGBA")
        zoom = 1 + 0.05 * u / d; bg = bg.resize((int(W * zoom), int(H * zoom)), Image.BILINEAR).crop((0, 0, W, H))
        cv.paste(bg, (0, 0))
        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(shade)
        for k in range(40): sd.rectangle([0, H * k / 40, W, H * (k + 1) / 40], fill=(0, 0, 0, int(60 + 90 * abs(k / 40 - 0.45))))
        cv.alpha_composite(shade)
    lines = sc.get("lineas") or [{"palabras": str(sc.get("texto", "")).split()[:3]}]
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); lines_block(lay, lines, W / 2, 780, W - 120, 108, 0.15, u, 1.27); cv.alpha_composite(lay)
    if sc.get("producto", True):
        dev = M.device_frame(X["pages"][0], 380, max_h=520, r=30, pad=14)
        paste_center(cv, dev, W - 260, 1420, back_out(prog(u, 0.9, 1.3)), rot=8)

RENDERERS = {"chat": sc_chat, "notificaciones": sc_notificaciones, "scroll": sc_scroll, "escribir": sc_escribir,
             "antes_despues": sc_antes_despues, "top3": sc_top3, "broll": sc_broll}
MIN_DUR = {"chat": 3.0, "notificaciones": 3.2, "scroll": 3.2, "escribir": 3.4, "antes_despues": 3.0, "top3": 4.2, "broll": 2.8}

def extra_duration(sc):
    if sc["tipo"] == "chat": return chat_times(sc.get("mensajes", []))[1] + 0.6
    if sc["tipo"] == "notificaciones": return 0.9 + 0.65 * len(sc.get("items", []))
    if sc["tipo"] == "top3": return 1.5 * len(sc.get("items", []))
    if sc["tipo"] == "escribir": return 1.4 + 0.06 * sum(len(x) for x in sc.get("lineas", []))
    return 0
