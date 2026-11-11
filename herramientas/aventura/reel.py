"""Reel de MI GRAN AVENTURA (~18 s) con el video de Gemini de Diego (clips/fuente.mp4, 4 tomas seguidas de 10 s):
problema (tablet) → el libro con SU nombre → páginas reales → jugando → QR que lo felicita → celebración → cierre.
Cortes rápidos con golpe de zoom (acercar/alejar), destello + whoosh, subtítulos abajo y carteles arriba pequeños (no tapan caras).
  python3 reel.py [salida.mp4] [--organico]      (sin créditos: música de la biblioteca del estudio o sintetizada)
  En el estudio con música de Eleven Music: docker exec pixelia-estudio python3 /pixelia/herramientas/aventura/reel.py --eleven [--musica-nueva] [--organico]"""
import sys, math, shutil, subprocess, tempfile, pathlib, importlib.util, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parent.parent
sp = importlib.util.spec_from_file_location("jefa", ROOT / "herramientas" / "lajefa" / "reel.py"); J = importlib.util.module_from_spec(sp)
_a = sys.argv; sys.argv = ["x"]; sp.loader.exec_module(J); sys.argv = _a
A, S = J.A, J.S
W, H, FPS = J.W, J.H, J.FPS
F, linea, pastilla, ease, back = J.F, J.linea, J.pastilla, J.ease, J.back
VIOLETA, ROSA, ORO, BLANCO, INK = (124, 92, 255), (255, 79, 163), (255, 183, 3), (255, 255, 255), (35, 26, 61)
SRC = HERE / "clips" / "fuente.mp4"
GAL = ROOT / "public" / "img" / "galeria"
MUSICA = ("Playful, warm children's adventure instrumental for a family ad: ukulele, glockenspiel, soft claps and pizzicato strings. "
          "Starts curious and a little sleepy for 3 seconds, then turns magical and joyful around second 5 (a child discovers her name on a book), "
          "bouncy and playful in the middle, and ends celebratory and bright. 112 BPM, no vocals, no long intro. Length about {seg} seconds.")
FIN_CTA = "💬 Comenta AVENTURA · link en el perfil" if "--organico" in sys.argv else "👇 Créalo en 1 minuto"

# (tipo, inicio en el video, duración, subtítulo, cartel, zoom: +1 acerca / -1 aleja)
ESC = [("clip", 2.9, 2.5, "¿Otra vez la tablet, mi amor?", "¿Pantallas todo el día? 😩", 1),
       ("clip", 10.7, 1.5, None, "Dale algo mejor… 🎁", -1),
       ("clip", 13.7, 4.0, "¡Mamá, dice mi nombre!", "Un libro con SU nombre ✨", 1),
       ("libro", None, 2.6, None, None, 0),
       ("clip", 23.9, 2.3, "¡Voy a rescatar al perrito!", "Aprende jugando ✏️", -1),
       ("qr", None, 1.7, None, None, 0),
       ("clip", 34.9, 2.7, "¡Me felicitó por mi nombre!", "¡Misión cumplida! 🏆", 1),
       ("fin", None, 2.4, None, None, 0)]
PAGINAS = [("aventura-portada.jpg", "📖 Su nombre en la portada"), ("aventura-mision.jpg", "🗺️ 12 misiones de su edad"), ("aventura-mapa.jpg", "⭐ Letras, números y lógica")]

def frames(ini, d, tmp, k):
    out = tmp / f"c{k}"; out.mkdir()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(ini), "-i", str(SRC), "-t", str(d), "-vf", f"fps={FPS},scale={W}:{H}:flags=lanczos", str(out / "%04d.jpg")], check=True)
    return sorted(out.glob("*.jpg"))
def zoom(img, z):
    if abs(z - 1) < 1e-3: return img
    big = img.resize((int(W * z), int(H * z)), Image.LANCZOS); x, y = (big.width - W) // 2, (big.height - H) // 2
    return big.crop((x, y, x + W, y + H))
def fondo(t):
    img = Image.new("RGBA", (W, H)); g = ImageDraw.Draw(img)
    for y in range(0, H, 6): k = y / H; g.rectangle([0, y, W, y + 6], fill=(int(124 + 131 * k), int(92 - 13 * k), int(255 - 92 * k)))
    for i, (x, y, r) in enumerate(((160, 320, 250), (950, 1500, 320))):
        c = Image.new("RGBA", (2 * r, 2 * r), (0, 0, 0, 0)); ImageDraw.Draw(c).ellipse([0, 0, 2 * r, 2 * r], fill=(255, 255, 255, 24))
        img.alpha_composite(c, (int(x - r + 30 * math.sin(t * 2 + i)), int(y - r)))
    return img
def hoja(nombre, ancho):
    im = Image.open(GAL / nombre).convert("RGBA"); im = im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], 26, fill=255); im.putalpha(m)
    sh = Image.new("RGBA", (im.width + 100, im.height + 100), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([50, 70, im.width + 50, im.height + 70], 30, fill=(0, 0, 0, 110))
    sh = sh.filter(ImageFilter.GaussianBlur(24)); sh.alpha_composite(im, (50, 50)); return sh
def esc_libro(t, d):
    img = fondo(t); n = len(PAGINAS); k = min(n - 1, int(t / (d / n))); lt = t - k * d / n
    linea(img, 200, "Así es su libro", F(66, "Black"), BLANCO, alpha=ease(t * 4), stroke=4, sc=INK)
    p = hoja(PAGINAS[k][0], 760); s = 0.8 + 0.2 * back(lt * 5)
    p = p.resize((int(p.width * s), int(p.height * s)), Image.LANCZOS).rotate((-4, 3, -2)[k] * ease(lt * 4), expand=True, resample=Image.BICUBIC)
    img.alpha_composite(p, (int(W / 2 - p.width / 2), int(1000 - p.height / 2)))
    pastilla(img, 1730, PAGINAS[k][1], F(54, "Black"), ORO + (255,), fg=INK, s=back(lt * 5)); return img
def pantalla_qr(t):
    sc = Image.new("RGBA", (560, 1100)); g = ImageDraw.Draw(sc)
    for y in range(0, 1100, 5): k = y / 1100; g.rectangle([0, y, 560, y + 5], fill=(int(124 + 131 * k), int(92 - 13 * k), int(255 - 92 * k)))
    cx, cy, r = 280, 330 - 18 * abs(math.sin(t * 6)), 120
    pts = [(cx + (r if q % 2 == 0 else r * .45) * math.sin(q * math.pi / 5), cy - (r if q % 2 == 0 else r * .45) * math.cos(q * math.pi / 5)) for q in range(10)]; g.polygon(pts, fill=ORO)
    for j, l in enumerate(["¡Muy bien, Sofía!", "Rescataste", "al perrito"]): g.text((280, 560 + j * 62), l, font=F(48 if j == 0 else 40, "Black" if j == 0 else "Bold"), fill=BLANCO, anchor="mm")
    g.rounded_rectangle([110, 820, 450, 900], 40, fill=ORO); g.text((280, 860), "Escuchar", font=F(36, "Black"), fill=INK, anchor="mm")
    b = 22; ph = Image.new("RGBA", (560 + 2 * b, 1100 + 2 * b), (0, 0, 0, 0)); ImageDraw.Draw(ph).rounded_rectangle([0, 0, ph.width - 1, ph.height - 1], 70, fill=(20, 16, 26))
    m = Image.new("L", sc.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, 559, 1099], 52, fill=255); ph.paste(sc, (b, b), m); return ph
def esc_qr(t, d):
    img = fondo(t); linea(img, 200, "Escanea al terminar…", F(62, "Black"), BLANCO, alpha=ease(t * 4), stroke=4, sc=INK)
    ph = pantalla_qr(t); s = 0.85 + 0.15 * back(t * 4); ph = ph.resize((int(ph.width * s), int(ph.height * s)), Image.LANCZOS)
    img.alpha_composite(ph, (int(W / 2 - ph.width / 2), int(1000 - ph.height / 2)))
    for i in range(3):   # ondas de sonido
        a = (t * 2 + i / 3) % 1; c = Image.new("RGBA", (W, H), (0, 0, 0, 0)); rr = 330 + 200 * a
        ImageDraw.Draw(c).ellipse([W / 2 - rr, 1000 - rr, W / 2 + rr, 1000 + rr], outline=(255, 255, 255, int(120 * (1 - a))), width=8); img.alpha_composite(c)
    pastilla(img, 1730, "🔊 Una voz lo felicita por su nombre", F(50, "Black"), ORO + (255,), fg=INK, s=back((t - .2) * 4)); return img
def esc_fin(t):
    img = fondo(t); p = hoja("aventura-portada.jpg", 520); s = 0.85 + 0.15 * back(t * 4)
    p = p.resize((int(p.width * s), int(p.height * s)), Image.LANCZOS).rotate(4, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(p, (int(W / 2 - p.width / 2), 170))
    linea(img, 1080, "Mi Gran Aventura", F(110, "Black"), BLANCO, alpha=ease((t - .1) * 5), stroke=6, sc=INK)
    linea(img, 1200, "Su nombre. Su aventura.", F(56, "Bold"), (255, 236, 248), alpha=ease((t - .3) * 4))
    pastilla(img, 1350, "De 2 a 8 años · llega a tu correo", F(52, "Black"), ORO + (255,), fg=INK, s=back((t - .45) * 4))
    linea(img, 1520, FIN_CTA, F(58, "Black"), BLANCO, alpha=ease((t - .7) * 4)); return img

def main(out):
    tmp = pathlib.Path(tempfile.mkdtemp()); fr = tmp / "f"; fr.mkdir(); n = 0; cortes = []; t0 = 0.0; T = sum(e[2] for e in ESC)
    try:
        for k, (tipo, ini, d, sub, txt, zd) in enumerate(ESC):
            cortes.append(t0); fs = frames(ini, d, tmp, k) if tipo == "clip" else []
            for i in range(int(round(d * FPS))):
                t = i / FPS
                if tipo == "clip":
                    img = Image.open(fs[min(i, len(fs) - 1)]).convert("RGBA")
                    golpe = 0.10 * (1 - ease(t * 4))                     # golpe al entrar
                    z = 1.0 + (0.07 * t / d if zd > 0 else 0.07 * (1 - t / d)) + golpe   # acercar o alejar despacio
                    img = zoom(img, z)
                    if txt: J.cartel(img, txt, t - 0.2, rojo=k == 0, y=260)
                    if sub: J.subtitulo(img, sub, ease((t - 0.1) * 6))
                elif tipo == "libro": img = esc_libro(t, d)
                elif tipo == "qr": img = esc_qr(t, d)
                else: img = esc_fin(t)
                if t < 0.1 and t0 > 0: img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(170 * (1 - t / 0.1)))))
                ImageDraw.Draw(img).rectangle([0, 0, int(W * (t0 + t) / T), 10], fill=ORO)
                img.convert("RGB").save(fr / f"{n:04d}.jpg", quality=90); n += 1
            t0 += d
        # ---- audio: voces originales + música + efectos ----
        T = n / FPS; m = int(T * A.SR); voz = np.zeros(m)
        for (tipo, ini, d, *_), c in zip(ESC, cortes):
            if tipo != "clip": continue
            raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(ini), "-i", str(SRC), "-t", str(d), "-ac", "1", "-ar", str(A.SR), "-f", "s16le", "-"], capture_output=True, check=True).stdout
            x = np.frombuffer(raw, np.int16).astype(np.float64) / 32768; x = x / (np.abs(x).max() + 1e-9) * 0.9
            f = int(0.03 * A.SR); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
            k = int(c * A.SR); voz[k:k + len(x)] += x[: m - k]
        mus = None
        if "--eleven" in sys.argv:   # música compuesta para ESTE reel con Eleven Music (en el estudio; se guarda y se reutiliza)
            sys.path.insert(0, str(ROOT / "herramientas")); import reels_audio as R
            mus = R.musica(T, "--musica-nueva" in sys.argv, archivo="aventura/infantil.mp3", prompt=MUSICA)
        if mus is None: mus, _ = A.library_track("pop", T) if A.library("pop") else (None, None)
        if mus is None: mus = A.genre_track("pop", T)
        mus = np.asarray(mus, dtype=np.float64)[:m]; mus = np.pad(mus, (0, m - len(mus))); mus /= (np.abs(mus).max() + 1e-9)
        w = int(0.15 * A.SR); env = np.convolve((np.abs(voz) > 0.03).astype(float), np.ones(w) / w, "same")
        mix = voz + mus * (0.36 - 0.27 * np.clip(env * 3, 0, 1)); fx = np.zeros(m)
        for c in cortes[1:]: A.add(fx, A.whoosh(0.35), max(0, c - 0.2), 0.55)
        A.add(fx, A.sparkle(), cortes[2] + 0.5, 0.7)                                  # "¡dice mi nombre!"
        for j in range(len(PAGINAS)): A.add(fx, A.pop(1.0 + 0.12 * j), cortes[3] + j * ESC[3][2] / len(PAGINAS), 0.7)
        A.add(fx, A.ding(1.2), cortes[5] + 0.2, 0.8); A.add(fx, A.sparkle(), cortes[-1] + 0.1, 0.8)
        x = mix + fx; x = x / max(1.0, np.abs(x).max() / 0.95)
        with wave.open(str(tmp / "a.wav"), "w") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(A.SR); wf.writeframes((x * 32767).astype(np.int16).tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(fr / "%04d.jpg"), "-i", str(tmp / "a.wav"), "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
        print(f"ok {out} ({T:.1f} s)")
    finally: shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    out = a[0] if a else str(ROOT / "storage" / "anuncios" / "mi-gran-aventura" / ("reel-aventura-organico.mp4" if "--organico" in sys.argv else "reel-aventura.mp4"))
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True); main(out)
