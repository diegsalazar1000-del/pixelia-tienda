"""Motor de escenas: convierte el guion de la IA en un reel 9:16.
Cada escena dura lo que necesita su frase de voz (así la voz nunca se corta) y entre escenas hay una transición corta.
"""
import math, random, subprocess
from PIL import Image, ImageDraw, ImageFilter
import motor as M
from motor import W, H, FPS, F, INK, S, back_out, ease_in_out, prog, clamp, paste_center, text_box, fit_font, highlight_words, lines_block

MIN_DUR = {"gancho": 2.4, "pov": 2.6, "problema": 3.2, "paginas": 3.4, "zoom": 2.6, "grid": 2.8, "incluye": 3.0, "movil": 2.8, "precio": 3.6}
XF = 0.22  # duración de la transición entre escenas

def scene_duration(sc, vdur=None):
    import formatos
    if sc["tipo"] == "clip": return round(float(sc.get("dur", 8)), 2)  # el clip dura lo que dura
    words = len(str(sc.get("voz") or "").split())
    need = (vdur + 0.6) if vdur else (words * 0.42 + 0.9)  # con la duración REAL de la voz si ya se generó
    d = max(MIN_DUR.get(sc["tipo"], formatos.MIN_DUR.get(sc["tipo"], 2.6)), need, formatos.extra_duration(sc))
    if sc["tipo"] in ("problema", "incluye"): d = max(d, 1.0 + 0.55 * len(sc.get("items", [])))
    if sc["tipo"] == "paginas": d = max(d, 0.8 + 0.75 * (len(sc.get("paginas", [])) - 1) + 0.4)
    return round(min(d, 8.0), 2)

def timeline(story, vdurs=None):
    t, scenes = 0.0, []
    for k, sc in enumerate(story["escenas"]):
        vd = (vdurs or [None] * 99)[k] if vdurs else None
        d = scene_duration(sc, vd); scenes.append({"tipo": sc["tipo"], "start": round(t, 2), "dur": d, "vdur": vd}); t += d
    return {"scenes": scenes, "T": round(t, 2)}

# ---------- piezas ----------
def pill(text, font, fill, color, pad=(30, 12)):
    tb = text_box(text, font, color)
    im = Image.new("RGBA", (tb.width + 2 * pad[0], tb.height + 2 * pad[1]), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=im.height // 2, fill=fill)
    im.alpha_composite(tb, pad); return im

def mark(kind, size, color):
    """Círculo con ✓ o ✗ dibujado (sin emojis)."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, size - 1, size - 1], fill=color); w = max(4, size // 9); c = size / 2
    if kind == "ok": d.line([(size * .27, c), (size * .44, size * .68), (size * .75, size * .32)], fill="#FFFFFF", width=w, joint="curve")
    else:
        o = size * .3; d.line([(o, o), (size - o, size - o)], fill="#FFFFFF", width=w); d.line([(size - o, o), (o, size - o)], fill="#FFFFFF", width=w)
    return im

def caption(cv, text, y, u, t0=0.0):
    if not text: return
    p = pill(text, fit_font([text], W - 200, 62), S["pill_fill"], S["pill_text"])
    paste_center(cv, p, W / 2, y, max(0.01, back_out(prog(u, t0, t0 + 0.35))))

def device_layer(img, cx, cy, scale, rot=0.0, w=None):
    dev = M.device_frame(img, w or img.width)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); paste_center(lay, dev, cx, cy, scale, rot=rot)
    return lay

# ---------- escenas (u = tiempo dentro de la escena) ----------
def sc_gancho(cv, sc, u, d, X):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lines_block(lay, sc["lineas"], W / 2, 760 - (len(sc["lineas"]) - 3) * 70, W - 120, 118, 0.1, u, 1.27)
    paste_center(cv, lay, W / 2, H / 2, 1 + 0.04 * u / d)

def sc_pov(cv, sc, u, d, X):
    page = X["pages"][sc["pagina"]]
    lay = device_layer(page, W / 2, 1180, 0.95 + 0.08 * u / d, rot=-3 + 2 * math.sin(u))
    cv.alpha_composite(M.shadow(lay, 35, (0, 40))); cv.alpha_composite(lay)
    tag = pill("POV:", F("Bold", 70), S["hl_fill"], S["hl_text"], (34, 14))
    paste_center(cv, tag, W / 2, 300, back_out(prog(u, 0.05, 0.4)))
    words = sc["texto"].split(); half = (len(words) + 1) // 2
    lines = [{"palabras": words[:half]}, {"palabras": words[half:]}] if len(words) > 3 else [{"palabras": words}]
    lines_block(cv, lines, W / 2, 450, W - 140, 92, 0.35, u, 1.25)

def sc_problema(cv, sc, u, d, X):
    highlight_words(cv, sc["titulo"].split(), W / 2, 380, fit_font(sc["titulo"].split(), W - 140, 100), 0.05, u, len(sc["titulo"].split()) - 1)
    n = len(sc["items"]); y0 = 820 - (n - 3) * 90
    for i, it in enumerate(sc["items"]):
        t0 = 0.5 + i * 0.5; e = back_out(prog(u, t0, t0 + 0.35))
        if e <= 0.01: continue
        row = pill(it, fit_font([it], W - 330, 66), S["box_fill"] if S.get("boxed") else (255, 255, 255, 235) if S["name"] != "neon" else (27, 18, 56, 235),
                   INK if S["name"] != "neon" else "#FFFFFF", (40, 16))
        x = W / 2 + 50
        paste_center(cv, row, x, y0 + i * 200, e, rot=(1 - e) * -6)
        paste_center(cv, mark("no", 104, "#E5484D"), x - row.width / 2 - 44, y0 + i * 200, back_out(prog(u, t0 + 0.15, t0 + 0.45)))

def sc_incluye(cv, sc, u, d, X):
    highlight_words(cv, (sc["titulo"] + ":").split(), W / 2, 330, fit_font(sc["titulo"].split(), W - 140, 104), 0.05, u, 0)
    n = len(sc["items"]); y0 = 660 - (n - 3) * 70
    phone = M.device_frame(X["phone"], 300, max_h=600, r=40, pad=14)
    paste_center(cv, phone, W - 190, 1500, back_out(prog(u, 0.2, 0.6)), rot=8)
    for i, it in enumerate(sc["items"]):
        t0 = 0.45 + i * 0.45; e = back_out(prog(u, t0, t0 + 0.35))
        if e <= 0.01: continue
        tb = text_box(it, fit_font([it], W - 330, 74), S["text"] if not S.get("boxed") else "#FFFFFF")
        if S.get("boxed"): tb = pill(it, fit_font([it], W - 330, 68), S["box_fill"], S["box_text"], (24, 10))
        y = y0 + i * 175; x = 160
        paste_center(cv, mark("ok", 110, S["hl_fill"] if S["name"] != "minimal" else S["colors"][0]), x, y, e)
        cv.alpha_composite(tb, (int(x + 80), int(y - tb.height / 2))) if e > 0.9 else paste_center(cv, tb, x + 80 + tb.width / 2, y, e)

def sc_paginas(cv, sc, u, d, X):
    pg = [X["pages"][i] for i in sc["paginas"]]; n = len(pg)
    fs = 0.6; fe = max(0.55, (d - 1.0) / max(1, n - 1)) if n > 1 else 1
    k = min(n - 2, int(max(0, u - fs) // fe)) if n > 1 else 0
    p = ease_in_out(clamp(((u - fs) - k * fe) / (fe * 0.8))) if n > 1 and u >= fs else 0
    page = M.flip_frame(pg[k], pg[min(k + 1, n - 1)], p)
    ent = back_out(prog(u, 0.0, 0.45))
    lay = device_layer(page, W / 2, 1060, 0.6 + 0.4 * ent, rot=4 * math.sin(u * 1.4))
    cv.alpha_composite(M.shadow(lay, 35, (0, 40))); cv.alpha_composite(lay)
    idx = min(n - 1, k + (1 if p > 0.5 else 0)); tx = sc["textos"][idx] if idx < len(sc["textos"]) else ""
    pop = back_out(clamp(((u - fs) - (idx - 1) * fe) / 0.3)) if idx > 0 else ent
    caption(cv, tx, 440, 1.0 if pop >= 1 else pop)
    for j, st in enumerate(X["stickers"][:S["stickers"]]):
        sp = back_out(prog(u, 0.1 + j * 0.22, 0.45 + j * 0.22)); ang = j * 60 + (X["t"]) * 25
        paste_center(cv, st, W / 2 + math.cos(math.radians(ang)) * 470, max(640, 1060 + math.sin(math.radians(ang)) * 560), sp * 0.9, rot=10 * math.sin(X["t"] * 3 + j))

def sc_zoom(cv, sc, u, d, X):
    page = X["pages"][sc["pagina"]]; e = ease_in_out(clamp(u / d))
    z = 1.0 + 0.9 * e  # se acerca a la mitad superior de la página
    big = page.resize((int(page.width * z), int(page.height * z)), Image.BILINEAR)
    cx, cy = big.width * (0.5 - 0.12 * e), big.height * (0.5 - 0.22 * e)
    crop = big.crop((int(cx - page.width / 2), int(cy - page.height / 2), int(cx + page.width / 2), int(cy + page.height / 2)))
    lay = device_layer(crop, W / 2, 1080, back_out(prog(u, 0, 0.4)) * 1.05)
    cv.alpha_composite(M.shadow(lay, 35, (0, 40))); cv.alpha_composite(lay)
    caption(cv, sc["texto"], 400, u, 0.15)

def sc_grid(cv, sc, u, d, X):
    pages = X["pages"][:6] if len(X["pages"]) >= 4 else (X["pages"] * 3)[:4]
    cols = 2; rows = (len(pages) + 1) // 2; tw = 400
    for i, p in enumerate(pages):
        th = M.device_frame(p, tw, max_h=360, r=26, pad=12)
        r_, c_ = divmod(i, cols); x = W / 2 + (c_ - 0.5) * 470; y = 960 + (r_ - (rows - 1) / 2) * 400
        e = back_out(prog(u, 0.15 + i * 0.16, 0.5 + i * 0.16))
        paste_center(cv, th, x, y + 10 * math.sin(X["t"] * 2 + i), e, rot=(-6 + 12 * ((i * 37) % 10) / 10) * e)
    caption(cv, sc["texto"], 270, u, 0.05)

def sc_movil(cv, sc, u, d, X):
    for (x0, y0, rot0, spd, st) in X["falling"]:
        y = y0 + u * spd * 2.2
        if -200 < y < H + 200: paste_center(cv, st, x0, y, 1.0, rot=rot0 + u * 60)
    e = back_out(prog(u, 0, 0.5))
    ph = M.device_frame(X["phone"], 500, max_h=1000, r=66, pad=20)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); paste_center(lay, ph, W / 2 + (1 - e) * 700, 1100, 1.0, rot=-6 + 3 * math.sin(u * 2))
    cv.alpha_composite(M.shadow(lay, 35, (10, 40))); cv.alpha_composite(lay)
    highlight_words(cv, sc["palabras"], W / 2, 300, fit_font(sc["palabras"], W - 140, 84), 0.2, u, sc.get("resaltar"))

def sc_precio(cv, sc, u, d, X):
    B = X["B"]; t = X["t"]; e = back_out(prog(u, 0, 0.45), 2.4)
    paste_center(cv, M.starburst(300, S["burst"]), W / 2, 860, e, rot=t * 20)
    ptxt = M.money(B["precio"]); paste_center(cv, text_box(ptxt, F("Bold", 230 if len(ptxt) <= 3 else 190), S["price"]), W / 2, 830, e)
    if B.get("tachado"):
        old = text_box(f"antes {M.money(B['tachado'])}", F("Medium", 52), S["old"])
        ImageDraw.Draw(old).line([(10, old.height / 2 + 4), (old.width - 10, old.height / 2 + 4)], fill=S["price"], width=6)
        paste_center(cv, old, W / 2, 1010, back_out(prog(u, 0.3, 0.6)))
        off = round((1 - B["precio"] / B["tachado"]) * 100)
        if off >= 10:
            badge = M.starburst(95, S["badge"], 12, 0.78)
            ImageDraw.Draw(badge).text((badge.width / 2, badge.height / 2), f"-{off}%", font=F("Bold", 50), fill="#FFFFFF" if S["name"] != "neon" else "#0B0820", anchor="mm")
            paste_center(cv, badge, W / 2 + 270, 640, back_out(prog(u, 0.45, 0.75)), rot=-12)
    btn = pill(sc.get("cta") or B["cta"], F("Bold", 58), S["cta_fill"], S["cta_text"], (55, 25))
    paste_center(cv, btn, W / 2, 1270, back_out(prog(u, 0.6, 0.95)) * (1 + 0.05 * math.sin(u * 9)))
    paste_center(cv, text_box(B["dominio"], F("Bold", 46), S["domain"]), W / 2, 1420, prog(u, 0.9, 1.2))
    if M.PAGOS and B.get("precio"):
        ps = M.pay_strip(1.35); ps = ps if ps.width <= W - 80 else ps.resize((W - 80, int(ps.height * (W - 80) / ps.width)), Image.LANCZOS)
        paste_center(cv, ps, W / 2, 1545, back_out(prog(u, 1.0, 1.35)))
    for j, st in enumerate(X["stickers"][:min(4, S["stickers"])]):
        pos = [(200, 520), (880, 1150), (180, 1180), (900, 470)][j]
        paste_center(cv, st, *pos, back_out(prog(u, 0.2 + j * 0.1, 0.5 + j * 0.1)), rot=15 * math.sin(t * 2 + j))

def subtitles(cv, sc, s, t):
    """Subtítulos estilo TikTok: grupos de 4 palabras, la palabra que suena se ilumina."""
    words = str(sc.get("voz") or "").split()
    if not words: return
    start = s["start"] + 0.15; dur = s.get("vdur") or len(words) * 0.36; per = dur / len(words)
    if t < start or t > start + dur + 0.25: return
    wi = min(len(words) - 1, int((t - start) / per)); a = wi // 4 * 4; chunk = words[a:a + 4]
    f = F("Bold", 66); boxes = []
    for j, w in enumerate(chunk):
        on = a + j == wi
        boxes.append(text_box(w, f, S["hl_fill"] if on and S["name"] != "minimal" else (S["colors"][0] if on else "#FFFFFF"), stroke="#000000", sw=7))
    gap = 18; total = sum(b.width for b in boxes) + gap * (len(boxes) - 1)
    if total > W - 80:
        k = (W - 80) / total; boxes = [b.resize((int(b.width * k), int(b.height * k))) for b in boxes]; total = W - 80; gap *= k
    x = W / 2 - total / 2
    for j, b in enumerate(boxes):
        sc_ = 1.12 if a + j == wi else 1.0
        paste_center(cv, b, x + b.width / 2, 1650, sc_); x += b.width + gap

RENDER = {"gancho": sc_gancho, "pov": sc_pov, "problema": sc_problema, "incluye": sc_incluye, "paginas": sc_paginas,
          "zoom": sc_zoom, "grid": sc_grid, "movil": sc_movil, "precio": sc_precio}

# ---------- reel ----------
def build(B, story, pages, phone, out_path, style=None, seed=7, only_times=None, vdurs=None):
    import formatos
    RENDER.update(formatos.RENDERERS)
    style = style or story.get("estilo", "color"); colors = B["colores"]
    M.set_style(style, colors, pages)
    S["letra"] = story.get("letra") or "poppins"; S["anim"] = story.get("animacion") or "pop"
    S["letra_k"] = {"bebas": 1.22, "anton": 1.08, "pacifico": 0.86, "archivo": 0.9, "lora": 1.0}.get(S["letra"], 1.0)
    TL = timeline(story, vdurs); T = TL["T"]
    pw = 860; pr = []
    for p in pages:
        ph = int(p.height * pw / p.width)
        pr.append(p.resize((int(pw * 1100 / ph), 1100), Image.LANCZOS) if ph > 1100 else p.resize((pw, ph), Image.LANCZOS))
    base = pr[0].size; pr = [p.resize(base, Image.LANCZOS) for p in pr]
    stickers = M.make_stickers(B.get("stickers", ["NUEVO", "PDF", "Descarga inmediata"]), colors)
    rng = random.Random(seed)
    X = {"B": B, "pages": pr, "phone": phone, "stickers": stickers, "t": 0.0,
         "falling": [(rng.uniform(80, W - 80), rng.uniform(-900, -100), rng.uniform(-40, 40), rng.uniform(300, 520), rng.choice(stickers)) for _ in range(S["falling"])],
         "broll": {}, "fps": FPS}
    # Modo Pixabay: un video real distinto de fondo en CADA escena (se abre al llegar a la escena: poca memoria)
    fondos = story.get("fondos") or []
    X["bgq"] = [None for sc in story["escenas"]]  # (sin video pegado de fondo: en modo Pixabay se usa el montaje de fotos)
    X["bgr"] = {}
    for sc, s in zip(story["escenas"], TL["scenes"]):  # escenas de video real
        if sc["tipo"] == "broll" and not story.get("stock"):
            v = formatos.pexels_video(sc.get("busqueda"))
            if v: X["broll"][id(sc)] = formatos.BrollReader(v, FPS, s["dur"])
    def real_bg(i, u):
        q = X["bgq"][i] if i < len(X["bgq"]) else None
        if not q: return None
        if i not in X["bgr"]:
            for k in [k for k in X["bgr"] if k < i - 1]: X["bgr"].pop(k).p.kill()  # cierra videos ya usados
            v = formatos.pexels_video(q); X["bgr"][i] = formatos.BrollReader(v, FPS, TL["scenes"][i]["dur"] + 0.5) if v else None
        rd = X["bgr"][i]; fr = rd.frame(u) if rd else None
        if fr is None: return None
        z = 1.04 + 0.05 * u / max(0.1, TL["scenes"][i]["dur"])
        big = fr.resize((int(W * z), int(H * z)), Image.BILINEAR)
        big = big.crop(((big.width - W) // 2, (big.height - H) // 2, (big.width - W) // 2 + W, (big.height - H) // 2 + H))
        return Image.blend(big, Image.new("RGB", (W, H), (10, 8, 16)), 0.42).convert("RGBA")
    def frame(t):
        X["t"] = t
        i = max(k for k, s in enumerate(TL["scenes"]) if s["start"] <= t + 1e-6)
        sc, s = story["escenas"][i], TL["scenes"][i]; u = t - s["start"]
        cv = (real_bg(i, u) if story.get("stock") and sc["tipo"] != "broll" else None) or M.background(W, H, colors, t)
        RENDER[sc["tipo"]](cv, sc, u, s["dur"], X)
        if story.get("subtitulos") and sc["tipo"] not in ("precio", "chat", "notificaciones", "montaje", "pasos", "meme", "clip"): subtitles(cv, sc, s, t)
        if i > 0 and u < XF:  # transición: la escena anterior se aleja y se desvanece
            ps = TL["scenes"][i - 1]
            pr_ = X["bgr"].get(i - 1) if story.get("stock") else None
            prev = (Image.blend(pr_.last.resize((W, H)), Image.new("RGB", (W, H), (10, 8, 16)), 0.42).convert("RGBA") if pr_ is not None and pr_.last is not None else M.background(W, H, colors, t))
            RENDER[story["escenas"][i - 1]["tipo"]](prev, story["escenas"][i - 1], ps["dur"] - 0.01, ps["dur"], X)
            a = u / XF; prev = prev.resize((int(W * (1 + 0.15 * a)), int(H * (1 + 0.15 * a))), Image.BILINEAR).crop(
                (int(W * 0.075 * a), int(H * 0.075 * a), int(W * 0.075 * a) + W, int(H * 0.075 * a) + H))
            cv = Image.blend(prev, cv, ease_in_out(a))
        return cv.convert("RGB")
    if only_times: return [frame(t) for t in only_times]
    ff = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)]
    proc = subprocess.Popen(ff, stdin=subprocess.PIPE)
    for fi in range(int(T * FPS)): proc.stdin.write(frame(fi / FPS).tobytes())
    proc.stdin.close(); proc.wait()
    for rd in list(X["bgr"].values()) + list(X["broll"].values()):
        try: rd.p.kill()
        except Exception: pass
    TL["story"] = True
    return TL
