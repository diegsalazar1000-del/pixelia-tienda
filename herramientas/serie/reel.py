"""Serie de reels "Cumple tus metas" (5 partes, para ganar seguidores: valor + "Parte X de 5, síguenos para la siguiente").
Los textos están en serie.json. Cada reel: gancho → 3 trucos (número grande, título, visual) → cierre con pregunta.
  Vista previa sin voz (no gasta):  python3 reel.py 1 silencio
  Con voz REAL de ElevenLabs (en el estudio):
    docker exec pixelia-estudio python3 /pixelia/herramientas/serie/reel.py 1 femenina   [--musica-nueva]
Sale en storage/anuncios/serie-metas/parte1-femenina.mp4 (+ -sin-musica.mp4, portada y el texto para Instagram)."""
import sys, json, re, math, shutil, subprocess, tempfile, pathlib, importlib.util
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
W, H, FPS = 1080, 1920, 24
FONTS = HERE.parent / "reto30" / "fonts"
F = lambda s, w="Bold": ImageFont.truetype(str(FONTS / f"Inter-{w}.otf"), int(s))
EMOJI_TTF = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
ORANGE, PINK, INK, TEAL, YEL, WHITE = (255, 107, 61), (255, 79, 163), (35, 26, 61), (20, 184, 166), (255, 217, 102), (255, 255, 255)
GREEN, RED, GRAY = (34, 197, 94), (239, 68, 68), (120, 110, 150)
SERIE = json.loads((HERE / "serie.json").read_text())

# ---------- utilidades de dibujo ----------
def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def back(x):  # entra con un pequeño rebote
    x = max(0.0, min(1.0, x)); c = 1.9; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
_ecache = {}
def emoji(ch, size):
    k = (ch, size)
    if k not in _ecache:
        f = ImageFont.truetype(EMOJI_TTF, 109)
        im = Image.new("RGBA", (180, 160), (0, 0, 0, 0)); ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
        im = im.crop(im.getbbox() or (0, 0, 1, 1))
        _ecache[k] = im.resize((size, round(im.height * size / im.width)), Image.LANCZOS)
    return _ecache[k]
es_emoji = lambda c: ord(c) >= 0x2190 and c not in "✓✗→←"
def trozos(txt):
    txt = txt.replace("️", "").replace("‍", "")
    out = []
    for c in txt:
        e = es_emoji(c)
        if out and out[-1][1] == e and not e: out[-1][0] += c
        else: out.append([c, e])
    return out
def ancho(txt, f): return sum(f.getlength(t) if not e else f.size * 1.05 for t, e in trozos(txt))
def linea(img, y, txt, f, fill, alpha=1.0, stroke=0, sc=(0, 0, 0), x=None):
    """Texto centrado (o desde x) que mezcla letras Inter y emojis de colores."""
    if alpha <= 0: return
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0)); g = ImageDraw.Draw(capa)
    cx = (W - ancho(txt, f)) / 2 if x is None else x
    for t, e in trozos(txt):
        if e:
            em = emoji(t, int(f.size * 0.95)); capa.alpha_composite(em, (int(cx), int(y - em.height / 2))); cx += f.size * 1.05
        else:
            g.text((cx, y), t, font=f, fill=fill, anchor="lm", stroke_width=stroke, stroke_fill=sc); cx += f.getlength(t)
    if alpha < 1: capa.putalpha(capa.getchannel("A").point(lambda a: int(a * alpha)))
    img.alpha_composite(capa)
def partir(txt, f, maxw=900):
    pal, ls, cur = txt.split(), [], ""
    for p in pal:
        n = (cur + " " + p).strip()
        if ancho(n, f) <= maxw or not cur: cur = n
        else: ls.append(cur); cur = p
    return ls + [cur] if cur else ls
def fondo(t):
    img = Image.new("RGBA", (W, H)); g = ImageDraw.Draw(img)
    for y in range(0, H, 6):
        k = y / H; g.rectangle([0, y, W, y + 6], fill=(int(24 + 34 * k), int(14 + 8 * k), int(44 + 36 * k)))
    for i, (cx, cy, r, col) in enumerate(((180, 380, 260, PINK), (930, 1500, 300, ORANGE))):   # luces suaves que flotan
        ox = 40 * math.sin(t * 0.7 + i * 2); glow = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([0, 0, r * 2, r * 2], fill=col + (38,))
        img.alpha_composite(glow, (int(cx - r + ox), int(cy - r)))
    return img
def pastilla(img, y, txt, f, bgc, fg=WHITE, s=1.0, pad=34):
    if s <= 0.01: return
    w = ancho(txt, f) + pad * 2; h = f.size * 1.6
    capa = Image.new("RGBA", (int(w) + 4, int(h) + 4), (0, 0, 0, 0)); ImageDraw.Draw(capa).rounded_rectangle([0, 0, w, h], int(h / 2), fill=bgc)
    tmp = Image.new("RGBA", capa.size, (0, 0, 0, 0)); tmp.alpha_composite(capa)
    # texto dentro de la pastilla
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g.alpha_composite(tmp, (int((W - w) / 2), int(y - h / 2)))
    linea(g, y, txt, f, fg)
    if s != 1.0:
        g = g.resize((int(W * s), int(H * s)), Image.LANCZOS); off = (int((W - W * s) / 2), int(y - y * s))
        z = Image.new("RGBA", (W, H), (0, 0, 0, 0)); z.alpha_composite(g.crop((max(0, -off[0]), max(0, -off[1]), g.width, g.height)), (max(0, off[0]), max(0, off[1]))); g = z
    img.alpha_composite(g)
def pegar_escalado(img, el, cx, cy, s):
    if s <= 0.02: return
    e = el.resize((max(1, int(el.width * s)), max(1, int(el.height * s))), Image.LANCZOS)
    img.alpha_composite(e, (int(cx - e.width / 2), int(cy - e.height / 2)))

# ---------- la hoja del Reto 30 Días (reutiliza las capturas del regalo) ----------
_hoja = None
def hoja():
    global _hoja
    if _hoja is None:
        sp = importlib.util.spec_from_file_location("r30", HERE.parent / "reto30" / "reel.py"); m = importlib.util.module_from_spec(sp)
        argv = sys.argv; sys.argv = ["reel.py"]; sp.loader.exec_module(m); sys.argv = argv
        alto = min(m.full.height, m.HH + int(10 * m.ROW * m.SC))      # encabezado + 10 días
        _hoja = (m.full.crop((0, 0, m.full.width, alto)), m.empty.crop((0, 0, m.full.width, alto)), m.HH)
    return _hoja
def visual_hoja(img, k, cy):
    full, empty, hh = hoja(); s = 860 / full.width
    full = full.resize((860, int(full.height * s))); empty = empty.resize(full.size); hh = int(hh * s)
    cut = int(hh + (full.height - hh) * ease(k))
    card = empty.copy(); card.paste(full.crop((0, 0, full.width, cut)), (0, 0))
    if cut < full.height: ImageDraw.Draw(card).line([(0, cut), (full.width, cut)], fill=ORANGE, width=6)
    card = card.convert("RGBA"); mask = Image.new("L", card.size, 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, card.width, card.height], 28, fill=255); card.putalpha(mask)
    sh = Image.new("RGBA", (card.width + 40, card.height + 40), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([20, 26, card.width + 20, card.height + 26], 30, fill=(0, 0, 0, 120))
    x, y = (W - card.width) // 2, int(cy - card.height / 2)
    img.alpha_composite(sh, (x - 20, y - 20)); img.alpha_composite(card, (x, y))

def visual_timer(img, k, cy, d):
    g = ImageDraw.Draw(img); r = 250
    g.ellipse([W / 2 - r, cy - r, W / 2 + r, cy + r], outline=(255, 255, 255, 50), width=30)
    a = 360 * ease(min(1, k * 1.15))
    g.arc([W / 2 - r, cy - r, W / 2 + r, cy + r], -90, -90 + a, fill=ORANGE, width=30)
    seg = max(0, 120 - int(k * d * 9))                      # cuenta atrás rápida desde 2:00
    g.text((W / 2, cy - 20), f"{seg // 60}:{seg % 60:02d}", font=F(150, "Black"), fill=WHITE, anchor="mm")
    g.text((W / 2, cy + 95), "solo empieza", font=F(44, "Medium"), fill=YEL, anchor="mm")

def visual_calendario(img, k, cy):
    g = ImageDraw.Draw(img); dias = "LMMJVSD"
    filas = [("✓✓✗✓✓✓✓", "1 día: humano 👍", GREEN), ("✓✓✗✗···", "2 seguidos: adiós meta 💀", RED)]
    for fi, (marcas, txt, col) in enumerate(filas):
        y = cy - 170 + fi * 330
        for i, (dl, mk) in enumerate(zip(dias, marcas)):
            kk = (k * 1.25 - fi * 0.45 - i * 0.05) * 5
            if kk <= 0: continue
            x = 165 + i * 125; s = back(min(1, kk))
            mal = mk == "✗"; bgc = (RED if (mal and fi == 1) else GRAY) if mal else (GREEN if mk == "✓" else (60, 50, 90))
            r = 52 * s
            g.ellipse([x - r, y - r, x + r, y + r], fill=bgc)
            g.text((x, y - 88), dl, font=F(36), fill=(220, 210, 240), anchor="mm")
            g.text((x, y + 2), mk if mk != "·" else "", font=F(int(58 * s), "Black"), fill=WHITE, anchor="mm")
        a = ease((k * 1.25 - fi * 0.45 - 0.4) * 4)
        linea(img, y + 110, txt, F(48, "Black"), col, alpha=a)

# ---------- escenas ----------
def esc_gancho(img, t, d, P):
    pastilla(img, 330, f"PARTE {P['n']}/5", F(46, "Black"), PINK, s=back(t * 3))
    y0 = 760
    for i, l in enumerate(P["gancho"]):
        k = (t - 0.12 - i * 0.28) * 4
        s = back(min(1, max(0, k)))
        if s > 0:
            el = Image.new("RGBA", (W, 200), (0, 0, 0, 0)); linea(el, 100, l, F(118, "Black"), WHITE if i != 1 else YEL, stroke=6, sc=INK)
            pegar_escalado(img, el, W / 2, y0 + i * 150, s)
    linea(img, y0 + 3 * 150 + 20, P["sub"], F(56, "MediumItalic"), (255, 190, 170), alpha=ease((t - 1.1) * 3))
    a = ease((t - 1.3) * 3)
    for i in range(3):
        g = ImageDraw.Draw(img); x = W / 2 + (i - 1) * 170; y = 1550; r = 62 * a
        if r > 1:
            g.ellipse([x - r, y - r, x + r, y + r], fill=ORANGE if i < 2 else PINK)
            g.text((x, y), "?" if i == 2 else str(i + 1), font=F(int(70 * a), "Black"), fill=WHITE, anchor="mm")
def esc_truco(img, t, d, P, i):
    tr = P["trucos"][i]; g = ImageDraw.Draw(img)
    for j in range(3):                                         # 1 · 2 · 3 arriba: dónde vamos
        x = W / 2 + (j - 1) * 110; c = ORANGE if j == i else ((255, 255, 255, 70) if j > i else (255, 255, 255, 160))
        g.ellipse([x - 16, 200 - 16, x + 16, 200 + 16], fill=c)
    s = back(t * 3.2); r = 95 * s
    if r > 1:
        g.ellipse([W / 2 - r, 380 - r, W / 2 + r, 380 + r], fill=PINK if i == 2 else ORANGE)
        g.text((W / 2, 384), f"#{i + 1}", font=F(int(96 * s), "Black"), fill=WHITE, anchor="mm")
    tit = partir(tr["titulo"], F(84, "Black"), 940)
    for j, l in enumerate(tit):
        linea(img, 560 + j * 100, l, F(84, "Black"), WHITE, alpha=ease((t - 0.15 - j * 0.12) * 4), stroke=4, sc=INK)
    cy = 1010 + (len(tit) - 1) * 40; k = max(0, (t - 0.45) / max(0.5, d - 1.1))
    v = tr.get("visual", "icono")
    if v == "hoja": visual_hoja(img, k, cy)
    elif v == "timer": visual_timer(img, k, cy, d)
    elif v == "calendario": visual_calendario(img, k, cy)
    else:
        s2 = back((t - 0.3) * 2.5); fl = 18 * math.sin(t * 3)
        pegar_escalado(img, emoji(tr["emoji"], 380), W / 2, cy + fl, s2)
    ls = partir(tr["texto"], F(54, "Bold"), 920); y = 1440 + (len(tit) - 1) * 30
    caja = ease((t - 0.8) * 3)
    if caja > 0:
        hgt = len(ls) * 72 + 50
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(ov).rounded_rectangle([60, y - 35, W - 60, y - 35 + hgt], 30, fill=(255, 255, 255, int(235 * caja)))
        img.alpha_composite(ov)
        for j, l in enumerate(ls): linea(img, y + 2 + j * 72, l, F(54, "Bold"), INK, alpha=caja)
def esc_cierre(img, t, d, P):
    n = P["n"]
    pastilla(img, 400, f"PARTE {n} DE 5", F(60, "Black"), PINK, s=back(t * 3))
    nxt = "Síguenos para la " + (str(n + 1) if n < 5 else "serie nueva")
    linea(img, 600, nxt, F(76, "Black"), WHITE, alpha=ease((t - 0.25) * 4), stroke=4, sc=INK)
    pul = 1 + 0.06 * math.sin(t * 8) if t > 0.7 else back((t - 0.4) * 3)
    pastilla(img, 790, "➕ Seguir", F(64, "Black"), ORANGE, s=pul, pad=60)
    for j, l in enumerate(partir(P["pregunta"], F(68, "Black"), 900)):
        linea(img, 1080 + j * 92, l, F(68, "Black"), YEL, alpha=ease((t - 0.9 - j * 0.15) * 4), stroke=4, sc=INK)
    linea(img, 1480, "🎁 Reto 30 Días GRATIS en el perfil", F(48, "Bold"), WHITE, alpha=ease((t - 1.4) * 3))
    linea(img, 1580, SERIE["cuenta"], F(46, "Medium"), (220, 200, 240), alpha=ease((t - 1.5) * 3))

BASE = [2.8, 4.2, 4.2, 4.2, 3.8]
def frame(P, D, t):
    img = fondo(t); ini = 0.0
    for e, d in enumerate(D):
        if t < ini + d or e == len(D) - 1:
            lt = t - ini
            if e == 0: esc_gancho(img, lt, d, P)
            elif e == len(D) - 1: esc_cierre(img, lt, d, P)
            else: esc_truco(img, lt, d, P, e - 1)
            if e > 0 and lt < 0.12:                                   # destello de corte
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(150 * (1 - lt / 0.12)))))
            break
        ini += d
    g = ImageDraw.Draw(img); T = sum(D)                                # barra de avance arriba (para que lo vean entero)
    g.rectangle([0, 0, W, 12], fill=(255, 255, 255, 40)); g.rectangle([0, 0, int(W * min(1, t / T)), 12], fill=ORANGE)
    return img.convert("RGB")

def render(P, D, out, audio=None, poster=None):
    tmp = tempfile.mkdtemp(); T = sum(D)
    for i in range(int(T * FPS)): frame(P, D, i / FPS).save(f"{tmp}/{i:04d}.jpg", quality=88)
    if poster: frame(P, D, D[0] * 0.95).save(poster, quality=88)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/%04d.jpg"]
    if audio: cmd += ["-i", audio, "-c:a", "aac", "-b:a", "160k", "-shortest"]
    subprocess.run(cmd + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], check=True)
    shutil.rmtree(tmp); print("ok", out, f"{T:.1f} s, escenas:", D)

def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    n = int(a[0]) if a else 1; genero = a[1] if len(a) > 1 else "femenina"
    P = next(p for p in SERIE["partes"] if p["n"] == n)
    OUT = ROOT / "storage" / "anuncios" / "serie-metas"; OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"parte{n}-texto.txt").write_text(P["copy"])
    if genero == "silencio":
        out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else str(OUT / f"parte{n}-sin-voz.mp4")
        return render(P, BASE, out, poster=out.replace(".mp4", ".jpg"))
    sys.path.insert(0, str(HERE.parent)); import numpy as np, reels_audio as RA
    RA.preparar(); A = RA.audio; SR = RA.SR
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        vid, nombre = RA.voz_energica(genero)
        frases = [P["voz_gancho"]] + [t["voz"] for t in P["trucos"]] + [P["voz_cierre"]]
        vs = [RA.tts(f, vid, tmp, i) for i, f in enumerate(frases)]
        D = [round(max(b, len(v) / SR + 0.45), 2) for b, v in zip(BASE, vs)]
        T = sum(D); m = int(T * SR); voz = np.zeros(m); t = 0.0; cortes = []
        for d, v in zip(D, vs):
            k = int((t + 0.1) * SR); voz[k:k + len(v)] += v[: max(0, m - k)]; cortes.append(t); t += d
        mus = RA.musica(T, "--musica-nueva" in sys.argv)
        w = int(0.2 * SR); env_ = np.convolve((np.abs(voz) > 0.02).astype(float), np.ones(w) / w, "same")
        mix = voz + mus * (0.40 - 0.26 * np.clip(env_ * 3, 0, 1))
        fx = np.zeros(m)
        A.add(fx, A.impact(), 0.05, 0.7)
        for c in cortes[1:]: A.add(fx, A.whoosh(0.4), max(0, c - 0.25), 0.7)
        for c in cortes[1:4]: A.add(fx, A.pop(1.1), c + 0.12, 0.8)          # aparece el número del truco
        A.add(fx, A.sparkle(), cortes[4] + 0.1, 0.9)
        RA.wav(mix + fx, tmp / "mix.wav"); RA.wav(voz + fx, tmp / "voz.wav")
        nom = OUT / f"parte{n}-{genero}.mp4"
        render(P, D, str(nom), str(tmp / "mix.wav"), str(OUT / f"parte{n}-portada.jpg"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(nom), "-i", str(tmp / "voz.wav"), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-shortest", str(OUT / f"parte{n}-{genero}-sin-musica.mp4")], check=True)
        print(f"✔ Parte {n} con voz {genero} ({T:.1f} s, {nombre})")
        print(f"Míralo en el teléfono: https://pixeliadigital.app/media/anuncios/serie-metas/parte{n}-{genero}.mp4")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
