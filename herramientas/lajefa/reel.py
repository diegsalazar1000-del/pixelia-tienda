"""Reel corto de LA JEFA (~13 s, para retención): clips de Gemini (clips/c1..c4, ya recortados a lo que se dice) +
pantallas reales de la app (pantallas/*.png) + textos, subtítulos, música y efectos.
  python3 reel.py [salida.mp4]            (corre igual en la sesión o en el estudio; sin créditos: música sintetizada o de la biblioteca)
Historia: susto ("¿Estoy perdiendo plata?") → frustración ("¡Con razón no me alcanza!") → la app → "aquí manda la jefa" → "¡Me pagaron!" → cierre."""
import sys, json, math, shutil, subprocess, tempfile, pathlib, importlib.util, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sp = importlib.util.spec_from_file_location("serie", HERE.parent / "serie" / "reel.py"); S = importlib.util.module_from_spec(sp)
_argv = sys.argv; sys.argv = ["x"]; sp.loader.exec_module(S); sys.argv = _argv
sys.path.insert(0, str(ROOT / "estudio")); import audio as A   # noqa: E402
W, H, FPS = 1080, 1920, 24
F, linea, pastilla, partir, ease, back = S.F, S.linea, S.pastilla, S.partir, S.ease, S.back
ROSA, VINO, ORO, ROJO, BLANCO = (232, 51, 122), (122, 24, 70), (245, 184, 61), (220, 38, 38), (255, 255, 255)

# cierre: orgánico = "Comenta DEMO" (comentarios.js responde con el link); --anuncio = el botón del anuncio lleva a /jefa
FIN_CTA = "👇 Pruébala gratis aquí" if "--anuncio" in sys.argv else "💬 Comenta DEMO · link en el perfil"
# (tipo, fuente, duración, subtítulo de lo que dice, texto grande)
ESC = [("clip", "c1", 2.6, "¿Qué? ¿Estoy perdiendo plata?", "Pierdes $1,50 en cada torta 😱"),
       ("clip", "c2", 2.1, "¡Con razón no me alcanza!", "Y pones el precio “a ojo” 🙈"),
       ("app", None, 4.2, None, "👑 Así de fácil"),
       ("clip", "c3", 2.6, "Ahora sí, aquí manda la jefa", "Precios · Clientas · Cobros"),
       ("clip", "c4", 2.0, "¡Me pagaron!", "Y te pagan sin pena 💸"),
       ("fin", None, 1.8, None, None)]
PANTALLAS = [("precio", "💰 Tu precio justo"), ("lista", "📋 Tu lista para WhatsApp"), ("estado", "🎨 Estados bonitos"), ("cobro", "💸 Cobra sin pena 😂")]
# la app EN USO (grabar_demo.py): fase → (duración en el reel, rótulo)
DEMO = json.loads((HERE / "pantallas" / "demo.json").read_text()) if (HERE / "pantallas" / "demo.json").exists() else None
FASES = [("precio", 1.7, "💰 Calcula tu precio justo"), ("cobro", 1.1, "💬 Cobra por WhatsApp"), ("estado", 1.4, "🎨 Tu estado en segundos")]

def frames_clip(src, d, tmp):
    out = tmp / src; out.mkdir()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(HERE / "clips" / f"{src}.mp4"), "-t", str(d), "-vf", f"fps={FPS},scale={W}:{H}:flags=lanczos",
                    str(out / "%04d.jpg")], check=True)
    fs = sorted(out.glob("*.jpg")); return fs

def subtitulo(img, txt, a):   # abajo, compacto y legible: no tapa la cara
    if a <= 0: return
    f = F(46, "Black"); ls = partir(txt, f, 860); y0 = 1660 - (len(ls) - 1) * 30
    w = max(S.ancho(l, f) for l in ls) + 56; h = len(ls) * 60 + 28
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(capa).rounded_rectangle([W / 2 - w / 2, y0 - 44, W / 2 + w / 2, y0 - 44 + h], 22, fill=(0, 0, 0, int(140 * a)))
    img.alpha_composite(capa)
    for j, l in enumerate(ls): linea(img, y0 + j * 60, l, f, BLANCO, alpha=a)

def cartel(img, txt, t, rojo=False, y=250):   # arriba y compacto: no tapa la cara
    s = back(t * 3.2)
    if s <= 0.02: return
    ls = partir(txt, F(56, "Black"), 900); h = len(ls) * 70 + 40
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(capa)
    g.rounded_rectangle([70, y - h / 2, W - 70, y + h / 2], 36, fill=(ROJO if rojo else ROSA) + (240,))
    ww = max(S.ancho(l, F(56, "Black")) for l in ls) + 70
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(capa)
    g.rounded_rectangle([W / 2 - ww / 2, y - h / 2, W / 2 + ww / 2, y + h / 2], 30, fill=(ROJO if rojo else ROSA) + (235,))
    for j, l in enumerate(ls): linea(capa, y - h / 2 + 55 + j * 70, l, F(56, "Black"), BLANCO)
    if s != 1:
        capa = capa.resize((int(W * s), int(H * s)), Image.LANCZOS); z = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ox, oy = int(W / 2 - W * s / 2), int(y - y * s); z.alpha_composite(capa.crop((max(0, -ox), max(0, -oy), capa.width, capa.height)), (max(0, ox), max(0, oy))); capa = z
    img.alpha_composite(capa)

_tel = {}
def telefono(nombre, ancho=640):
    if nombre not in _tel:
        sc = Image.open(HERE / "pantallas" / f"{nombre}.png").convert("RGB")
        sc = sc.resize((ancho, round(sc.height * ancho / sc.width)), Image.LANCZOS)
        alto = min(sc.height, int(ancho * 2.05)); sc = sc.crop((0, 0, ancho, alto))
        b = 22; ph = Image.new("RGBA", (ancho + 2 * b, alto + 2 * b), (0, 0, 0, 0))
        ImageDraw.Draw(ph).rounded_rectangle([0, 0, ph.width - 1, ph.height - 1], 70, fill=(20, 16, 26))
        m = Image.new("L", sc.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, ancho - 1, alto - 1], 52, fill=255)
        ph.paste(sc, (b, b), m)
        sh = Image.new("RGBA", (ph.width + 120, ph.height + 120), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([60, 80, ph.width + 60, ph.height + 80], 70, fill=(0, 0, 0, 110))
        sh = sh.filter(ImageFilter.GaussianBlur(28)); sh.alpha_composite(ph, (60, 60)); _tel[nombre] = sh
    return _tel[nombre]

def fondo_marca(t):
    img = Image.new("RGBA", (W, H)); g = ImageDraw.Draw(img)
    for y in range(0, H, 6):
        k = y / H; g.rectangle([0, y, W, y + 6], fill=(int(122 + 110 * k), int(24 + 27 * k), int(70 + 52 * k)))
    for i, (x, y, r) in enumerate(((150, 300, 260), (960, 1500, 320))):
        c = Image.new("RGBA", (2 * r, 2 * r), (0, 0, 0, 0)); ImageDraw.Draw(c).ellipse([0, 0, 2 * r, 2 * r], fill=(255, 255, 255, 22))
        img.alpha_composite(c, (int(x - r + 30 * math.sin(t + i)), int(y - r)))
    return img

_demo = {}
def demo_frame(real):
    ts = DEMO["t"]; i = max(0, max((k for k, x in enumerate(ts) if x <= real), default=0))
    if i not in _demo:
        sc = Image.open(HERE / "pantallas" / "demo" / f"{i:04d}.jpg").convert("RGB"); _demo.clear(); _demo[i] = sc
    return _demo[i]
def esc_demo(t, d, titulo):
    img = fondo_marca(t); fs = DEMO["fases"]; orden = ["precio", "cobro", "estado", "fin"]
    acc = 0.0
    for nombre, dur, rot in FASES:
        if t < acc + dur or nombre == FASES[-1][0]: break
        acc += dur
    lt = t - acc; a, b = fs[nombre], fs[orden[orden.index(nombre) + 1]]
    sc = demo_frame(a + min(1, lt / dur) * (b - a))
    ancho = 600; sc = sc.resize((ancho, round(sc.height * ancho / sc.width)), Image.LANCZOS)
    b_ = 20; ph = Image.new("RGBA", (ancho + 2 * b_, sc.height + 2 * b_), (0, 0, 0, 0))
    ImageDraw.Draw(ph).rounded_rectangle([0, 0, ph.width - 1, ph.height - 1], 64, fill=(20, 16, 26))
    m = Image.new("L", sc.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, sc.width - 1, sc.height - 1], 48, fill=255); ph.paste(sc, (b_, b_), m)
    linea(img, 150, titulo, F(60, "Black"), BLANCO, alpha=ease(t * 4), stroke=4, sc=VINO)
    img.alpha_composite(ph, (int(W / 2 - ph.width / 2), 230))
    S.pastilla(img, 1740, rot, F(52, "Black"), ORO + (255,), fg=VINO, s=back(lt * 5))
    return img

def esc_app(t, d, titulo):
    if DEMO: return esc_demo(t, d, titulo)
    img = fondo_marca(t); n = len(PANTALLAS); k = min(n - 1, int(t / (d / n))); lt = t - k * d / n
    linea(img, 210, titulo, F(64, "Black"), BLANCO, alpha=ease(t * 4), stroke=4, sc=VINO)
    ph = telefono(PANTALLAS[k][0]); s = 0.86 + 0.14 * back(lt * 5) if lt < 0.3 else 1.0
    p2 = ph.resize((int(ph.width * s), int(ph.height * s)), Image.LANCZOS)
    img.alpha_composite(p2, (int(W / 2 - p2.width / 2), int(1010 - p2.height / 2)))
    S.pastilla(img, 1690, PANTALLAS[k][1], F(54, "Black"), ORO + (255,), fg=VINO, s=back(lt * 5))
    return img

def esc_fin(t):
    img = fondo_marca(t)
    linea(img, 640, "👑", F(220, "Black"), BLANCO, alpha=ease(t * 5))
    linea(img, 860, "La Jefa", F(150, "Black"), BLANCO, alpha=ease((t - .1) * 5), stroke=6, sc=VINO)
    linea(img, 990, "La app de tu negocio desde casa", F(52, "Bold"), (255, 230, 240), alpha=ease((t - .3) * 4))
    pastilla(img, 1160, "Pruébala gratis · $4.99 de por vida", F(52, "Black"), ORO + (255,), fg=VINO, s=back((t - .45) * 4))
    linea(img, 1340, FIN_CTA, F(56, "Black"), BLANCO, alpha=ease((t - .7) * 4))
    return img

def main(out):
    tmp = pathlib.Path(tempfile.mkdtemp()); fr = tmp / "f"; fr.mkdir(); n = 0; cortes = []; t0 = 0.0
    try:
        for tipo, src, d, sub, txt in ESC:
            cortes.append(t0); fs = frames_clip(src, d, tmp) if tipo == "clip" else []
            for i in range(int(round(d * FPS))):
                t = i / FPS
                if tipo == "clip":
                    img = Image.open(fs[min(i, len(fs) - 1)]).convert("RGBA")
                    z = 1 + 0.04 * t / d; img = img.resize((int(W * z), int(H * z)), Image.LANCZOS).crop((int(W * (z - 1) / 2), int(H * (z - 1) / 2), int(W * (z - 1) / 2) + W, int(H * (z - 1) / 2) + H))
                    if src == "c1": pastilla(img, 180, "¿Vendes desde casa? 🧁💅🏪", F(46, "Black"), (255, 255, 255, 235), fg=VINO, s=1.0)
                    cartel(img, txt, t - (0.55 if src == "c1" else 0.25), rojo=src == "c1", y=420 if src != "c3" else 380)
                    subtitulo(img, sub, ease((t - 0.1) * 6))
                elif tipo == "app": img = esc_app(t, d, txt)
                else: img = esc_fin(t)
                if t < 0.1 and t0 > 0: img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(160 * (1 - t / 0.1)))))
                g = ImageDraw.Draw(img); T = sum(e[2] for e in ESC); g.rectangle([0, 0, int(W * (t0 + t) / T), 10], fill=ORO)
                img.convert("RGB").save(fr / f"{n:04d}.jpg", quality=90); n += 1
            t0 += d
        # ---- audio: voces de los clips + música + efectos ----
        T = n / FPS; m = int(T * A.SR); voz = np.zeros(m)
        for (tipo, src, d, _, _), c in zip(ESC, cortes):
            if tipo != "clip": continue
            raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(HERE / "clips" / f"{src}.mp4"), "-t", str(d), "-ac", "1", "-ar", str(A.SR), "-f", "s16le", "-"], capture_output=True, check=True).stdout
            x = np.frombuffer(raw, np.int16).astype(np.float64) / 32768; x = x / (np.abs(x).max() + 1e-9) * 0.9
            k = int(c * A.SR); voz[k:k + len(x)] += x[: m - k]
        mus, _ = A.library_track("pop", T) if A.library("pop") else (None, None)
        if mus is None: mus = A.genre_track("pop", T)
        mus = np.asarray(mus, dtype=np.float64)[:m]; mus = np.pad(mus, (0, m - len(mus))); mus /= (np.abs(mus).max() + 1e-9)
        w = int(0.15 * A.SR); env = np.convolve((np.abs(voz) > 0.03).astype(float), np.ones(w) / w, "same")
        mix = voz + mus * (0.38 - 0.28 * np.clip(env * 3, 0, 1))
        fx = np.zeros(m)
        A.add(fx, A.impact(), 0.55, 0.6)
        for c in cortes[1:]: A.add(fx, A.whoosh(0.35), max(0, c - 0.2), 0.6)
        ca = cortes[2]
        if DEMO:
            acc = 0.0
            for j, (_, dur, _) in enumerate(FASES): A.add(fx, A.pop(1.0 + 0.1 * j), ca + acc, 0.7); acc += dur
        else:
            for j in range(len(PANTALLAS)): A.add(fx, A.pop(1.0 + 0.1 * j), ca + j * ESC[2][2] / len(PANTALLAS), 0.7)
        A.add(fx, A.sparkle(), cortes[-1] + 0.1, 0.8)
        x = mix + fx; x = x / max(1.0, np.abs(x).max() / 0.95)
        with wave.open(str(tmp / "a.wav"), "w") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(A.SR); wf.writeframes((x * 32767).astype(np.int16).tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(fr / "%04d.jpg"), "-i", str(tmp / "a.wav"), "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
        print(f"ok {out} ({T:.1f} s)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    out = a[0] if a else str(ROOT / "storage" / "anuncios" / "la-jefa" / ("reel-lajefa-anuncio.mp4" if "--anuncio" in sys.argv else "reel-lajefa.mp4"))
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True); main(out)
