"""Audio del estudio: efectos sincronizados, música ORIGINAL por género y voz en off (Piper, local y gratis).
Todo se sintetiza aquí: no se usa música ni sonidos con derechos de terceros.
"""
import math, pathlib, subprocess, wave, os
import numpy as np

SR = 44100
rng = np.random.default_rng(3)
VOICES_DIR = pathlib.Path(os.environ.get("PIPER_VOICES", "/voces"))
VOICES = {"femenina": "es_MX-claude-high", "masculina": "es_MX-ald-medium"}

# ---------- síntesis básica ----------
def env(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(d, 1e-4))

def lowpass(x, k):
    if k <= 1: return x
    c = np.cumsum(np.concatenate([[0], x])); y = (c[k:] - c[:-k]) / k
    return np.concatenate([y, np.zeros(len(x) - len(y))])

def osc(freq, n, kind="sine"):
    t = np.arange(n) / SR; ph = 2 * np.pi * freq * t
    if kind == "saw": return 2 * ((freq * t) % 1) - 1
    if kind == "square": return np.sign(np.sin(ph))
    if kind == "tri": return 2 * np.abs(2 * ((freq * t) % 1) - 1) - 1
    return np.sin(ph)

def note(n_):  # nombre de nota → Hz (A4=440)
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    name, octv = n_[:-1], int(n_[-1])
    return 440 * 2 ** ((names[name] + (octv - 4) * 12) / 12)

CHORDS = {"Am": ["A3", "C4", "E4"], "F": ["F3", "A3", "C4"], "C": ["C4", "E4", "G4"], "G": ["G3", "B3", "D4"],
          "Em": ["E3", "G3", "B3"], "Dm": ["D3", "F3", "A3"], "Bm": ["B3", "D4", "F#4"], "D": ["D3", "F#3", "A3"]}

def kick(d=0.25, f0=140, f1=45):
    n = int(d * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(f0 * np.exp(-t * 18) + f1) / SR) * env(n, 0.001, d * 0.5)
def snare(d=0.18):
    n = int(d * SR); return (rng.normal(0, 1, n) * 0.7 + osc(190, n, "tri") * 0.5) * env(n, 0.001, 0.05)
def clap(d=0.2):
    n = int(d * SR); s = rng.normal(0, 1, n) - lowpass(rng.normal(0, 1, n), 3)
    e = np.zeros(n)
    for o in (0, 0.01, 0.022): i = int(o * SR); e[i:] += env(n - i, 0.001, 0.03)
    return s * e * 0.6
def hat(d=0.05, open_=False):
    n = int((0.22 if open_ else d) * SR); s = rng.normal(0, 1, n); s = s - lowpass(s, 2)
    return s * env(n, 0.001, 0.08 if open_ else 0.015) * 0.3
def shaker():
    n = int(0.07 * SR); s = rng.normal(0, 1, n); s = s - lowpass(s, 3)
    return s * np.sin(np.linspace(0, np.pi, n)) * 0.18
def bass(freq, d, kind="sine"):
    n = int(d * SR); s = osc(freq, n, kind) * 0.8 + osc(freq * 2, n) * 0.2
    if kind != "sine": s = lowpass(s, 30)
    return s * env(n, 0.005, d * 0.6) * 0.5
def pluck(freq, d=0.6, bright=0.5):  # Karplus-Strong (guitarra/arpa)
    n = int(d * SR); p = max(2, int(SR / freq)); buf = rng.uniform(-1, 1, p); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]; nxt = (i + 1) % p
        buf[i % p] = 0.996 * (bright * buf[i % p] + (1 - bright) * buf[nxt]) if True else 0
    return out * 0.35
def pad(freqs, d, kind="saw"):
    n = int(d * SR); s = sum(osc(f, n, kind) + osc(f * 1.005, n, kind) for f in freqs) / (2 * len(freqs))
    s = lowpass(s, 18); a = np.minimum(1, np.arange(n) / (0.08 * SR)); r = np.minimum(1, (n - np.arange(n)) / (0.15 * SR))
    return s * a * r * 0.35
def rhodes(freqs, d):
    n = int(d * SR); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t + 0.8 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 3)) for f in freqs) / len(freqs)
    return s * env(n, 0.005, d * 0.5) * (1 + 0.15 * np.sin(2 * np.pi * 5 * t)) * 0.35

def guacharaca(accent=False):
    n = int(0.11 * SR); s = rng.normal(0, 1, n); s = s - lowpass(s, 2)
    e = np.zeros(n)
    for k in range(5): i = int(k * 0.018 * SR); e[i:] += env(n - i, 0.001, 0.008)
    return s * e * (0.22 if accent else 0.14)
def accordion(freqs, d):
    n = int(d * SR); t = np.arange(n) / SR; vib = 1 + 0.004 * np.sin(2 * np.pi * 6 * t)
    s = sum(osc(f, n, "saw") * 0.5 + osc(f * 1.003, n, "square") * 0.3 for f in freqs) / len(freqs)
    s = lowpass(s * vib, 6)
    return s * np.minimum(1, t / 0.02) * np.minimum(1, (d - t) / 0.05) * 0.3
def b808(freq, d):
    n = int(d * SR); t = np.arange(n) / SR; f = freq * (1 + 0.5 * np.exp(-t * 30))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR); x = np.tanh(x * 1.8)
    return x * np.minimum(1, t / 0.003) * np.exp(-t / (d * 0.7)) * 0.75

def add(buf, snd, t, gain=1.0):
    i = int(t * SR); j = min(len(buf), i + len(snd))
    if 0 <= i < len(buf): buf[i:j] += snd[: j - i] * gain

# ---------- géneros (patrones originales) ----------
def genre_track(genre, T, bpm=None):
    out = np.zeros(int(T * SR)); g = (genre or "base").lower()
    spec = {"reggaeton": (95, ["Am", "F", "C", "G"]), "pop": (118, ["C", "G", "Am", "F"]), "electronica": (124, ["Am", "F", "C", "G"]),
            "lofi": (80, ["Dm", "G", "C", "Am"]), "acustica": (100, ["G", "D", "Em", "C"]), "base": (118, ["Am", "Am", "C", "G"]),
            "cumbia": (98, ["Am", "Dm", "G", "C"]), "trap": (140, ["Am", "F", "Dm", "Em"])}
    bpm_, prog_ = spec.get(g, spec["base"]); bpm = bpm or bpm_
    step = 60 / bpm / 4  # semicorchea
    bar = step * 16; nbars = int(T / bar) + 1
    for b in range(nbars):
        t0 = b * bar; ch = CHORDS[prog_[b % 4]]; root = note(ch[0]) / 2
        if g == "reggaeton":  # dembow: bombo 1-2-3-4, caja en 4 y 7 de cada media barra
            for s in (0, 4, 8, 12): add(out, kick(0.22, 120, 48), t0 + s * step, 0.8)
            for s in (3, 6, 11, 14): add(out, snare(0.14), t0 + s * step, 0.45)
            for s in range(0, 16, 2): add(out, hat(), t0 + s * step, 0.6)
            for s in (0, 3, 8, 11): add(out, bass(root, step * 3, "sine"), t0 + s * step, 0.9)
            for k, f in enumerate(ch): add(out, pluck(note(f) * 2, 0.5, 0.4), t0 + (k * 2 + 4) * step, 0.5)
            add(out, pad([note(f) for f in ch], bar, "saw"), t0, 0.25)
        elif g == "pop":
            for s in (0, 4, 8, 12): add(out, kick(), t0 + s * step, 0.8)
            for s in (4, 12): add(out, clap(), t0 + s * step, 0.7)
            for s in range(2, 16, 4): add(out, hat(), t0 + s * step, 0.7)
            for s in range(0, 16, 2): add(out, bass(root, step * 1.8, "saw"), t0 + s * step, 0.6)
            for k in range(8): add(out, pluck(note(ch[k % 3]) * 2, 0.35, 0.6), t0 + k * 2 * step, 0.45)
            add(out, pad([note(f) for f in ch], bar), t0, 0.3)
        elif g == "electronica":
            for s in (0, 4, 8, 12): add(out, kick(0.3, 160, 42), t0 + s * step, 0.9)
            for s in (2, 6, 10, 14): add(out, hat(open_=True), t0 + s * step, 0.5); add(out, bass(root, step * 1.6, "saw"), t0 + s * step, 0.7)
            for s in (4, 12): add(out, clap(), t0 + s * step, 0.5)
            arp = [note(f) * 2 for f in ch] + [note(ch[0]) * 4]
            for k in range(16): add(out, osc(arp[k % 4], int(step * 0.9 * SR), "square") * env(int(step * 0.9 * SR), 0.002, 0.05) * 0.08, t0 + k * step)
        elif g == "lofi":
            sw = step * 0.18
            for s in (0, 7, 10): add(out, kick(0.2, 100, 45), t0 + s * step, 0.6)
            for s in (4, 12): add(out, snare(0.12), t0 + s * step + sw, 0.3)
            for s in range(0, 16, 2): add(out, hat(), t0 + s * step + (sw if s % 4 else 0), 0.35)
            add(out, rhodes([note(f) for f in ch], bar * 0.95), t0, 0.7); add(out, bass(root, bar * 0.5), t0, 0.6); add(out, bass(root, bar * 0.4), t0 + bar * 0.5, 0.5)
        elif g == "acustica":
            for s in (0, 8): add(out, kick(0.2, 100, 50), t0 + s * step, 0.5)
            for s in range(0, 16, 2): add(out, shaker(), t0 + s * step, 0.6)
            for s in (0, 3, 6, 8, 11, 14):  # rasgueo
                for k, f in enumerate(ch): add(out, pluck(note(f), 0.8, 0.55), t0 + s * step + k * 0.012, 0.35)
        elif g == "cumbia":  # guacharaca + bajo raíz/quinta + "acordeón"
            for s in (0, 8): add(out, kick(0.2, 110, 50), t0 + s * step, 0.7)
            for s in (4, 12): add(out, snare(0.1), t0 + s * step, 0.3)
            for s in range(0, 16, 2): add(out, guacharaca(s % 4 == 0), t0 + s * step, 0.9)
            fifth = root * 1.5
            for s, f in ((0, root), (6, root), (8, fifth), (14, fifth)): add(out, bass(f, step * 2, "sine"), t0 + s * step, 0.9)
            for k, s in enumerate((2, 6, 10, 14)): add(out, accordion([note(f) * 2 for f in ch], step * 1.6), t0 + s * step, 0.45)
        elif g == "trap":  # medio tiempo, 808 largo, hi-hats con redobles
            for s in (0, 10): add(out, b808(root, bar * 0.45), t0 + s * step, 1.0)
            add(out, clap(), t0 + 8 * step, 0.8); add(out, snare(0.15), t0 + 8 * step, 0.4)
            for s in range(16):
                add(out, hat(), t0 + s * step, 0.55)
                if s in (6, 14):  # redoble de hi-hat
                    for r in range(3): add(out, hat(0.03), t0 + s * step + (r + 1) * step / 3, 0.4)
            add(out, pad([note(f) for f in ch], bar, "tri"), t0, 0.35)
            for k, f in enumerate(ch): add(out, pluck(note(f) * 2, 0.4, 0.7), t0 + (k * 4 + 2) * step, 0.35)
        else:  # base suave (la del primer anuncio)
            for s in (0, 4, 8, 12): add(out, kick(), t0 + s * step, 0.55)
            for s in (2, 6, 10, 14): add(out, hat(), t0 + s * step, 1.0)
            add(out, bass(root, step * 3.6), t0, 0.5)
    if g == "lofi":  # crepitar de vinilo
        crack = (rng.random(len(out)) > 0.9993) * rng.normal(0, 0.3, len(out)); out += lowpass(crack, 2) + rng.normal(0, 0.004, len(out))
    fade = int(0.4 * SR); out[:fade] *= np.linspace(0, 1, fade); out[-fade:] *= np.linspace(1, 0, fade)
    return out / (np.abs(out).max() + 1e-9) * 0.8

# ---------- efectos ----------
def pop(pitch=1.0):
    n = int(0.12 * SR); t = np.arange(n) / SR; f = (500 + 900 * (t / t[-1])) * pitch
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.04) + rng.normal(0, 0.15, n) * env(n, 0.001, 0.006)) * 0.55
def whoosh(dur=0.42, bright=1.0):
    n = int(dur * SR); t = np.arange(n) / SR; noise = rng.normal(0, 1, n); shape = np.sin(np.pi * t / dur) ** 2
    s = (lowpass(noise, 22) * (1 - t / dur) + (noise - lowpass(noise, 4)) * 0.35 * bright * (t / dur)) * shape
    return s * 0.45 / (np.abs(s).max() + 1e-9)
def impact():
    n = int(0.9 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(120 * np.exp(-t * 6) + 42) / SR) * env(n, 0.002, 0.35) * 0.9 + lowpass(rng.normal(0, 1, n), 3) * env(n, 0.001, 0.05) * 0.35
def sparkle():
    out = np.zeros(int(0.6 * SR))
    for i, fr in enumerate([1568, 1976, 2349, 3136]):
        n = int(0.25 * SR); t = np.arange(n) / SR; o = int(i * 0.06 * SR)
        out[o:o + n] += np.sin(2 * np.pi * fr * t) * env(n, 0.002, 0.09) * 0.18
    return out
def click():
    n = int(0.05 * SR); return osc(1800, n) * env(n, 0.001, 0.012) * 0.4

def sfx_track(B, TL):
    buf = np.zeros(int(TL["T"] * SR))
    for li, line in enumerate(B["gancho"]):
        for i, _ in enumerate(line["palabras"]): add(buf, pop(1 + 0.08 * i + 0.1 * li), 0.1 + li * 0.35 + i * 0.12 + 0.05, 0.8)
    add(buf, whoosh(0.5, 0.6), 2.15, 0.9)
    for k in range(TL["n"] - 1): add(buf, whoosh(0.42, 1.0 + 0.1 * k), TL["flip_start"] + k * TL["flip_each"], 0.85)
    for j in range(6): add(buf, pop(1.3 + 0.05 * j), 2.42 + j * 0.25, 0.45)
    s3a, s4 = TL["s3a"], TL["s4"]
    add(buf, whoosh(0.5, 1.3), s3a - 0.05, 1.0)
    for i, _ in enumerate(B["movil_texto"]): add(buf, pop(1.1 + 0.06 * i), s3a + 0.25 + i * 0.12, 0.7)
    for k in range(10): add(buf, pop(1.6 + 0.04 * (k % 5)), s3a + 0.3 + k * 0.22, 0.25)
    add(buf, impact(), s4 + 0.05, 1.0); add(buf, pop(0.9), s4 + 0.35, 0.6); add(buf, pop(1.4), s4 + 0.5, 0.6)
    add(buf, click(), s4 + 0.62, 1.0); add(buf, sparkle(), s4 + 0.65, 1.0)
    return buf

# ---------- música REAL de la biblioteca ----------
# Canciones libres de derechos que tú envías al bot del radar con el género en el texto (se guardan en storage/musica/<género>/).
MUSIC_DIR = pathlib.Path(os.environ.get("PIXELIA_DIR", "/pixelia")) / "storage" / "musica"
AUDIO_EXT = (".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac")

def library(genre):
    d = MUSIC_DIR / (genre or "")
    return sorted(p for p in d.glob("*") if p.suffix.lower() in AUDIO_EXT) if d.is_dir() else []

def decode(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

def library_track(genre, T, seed=0):
    """Toma la parte con más energía (el coro / el 'drop') de una canción real del género y la recorta al largo del reel."""
    files = library(genre)
    if not files: return None, None
    path = files[seed % len(files)]
    x = decode(path); n = int(T * SR)
    if len(x) < n: x = np.tile(x, n // max(1, len(x)) + 1)
    hop = SR // 2; win = n
    e = np.convolve(x[: len(x) // hop * hop].reshape(-1, hop).std(axis=1), np.ones(max(1, win // hop)), "valid")
    lo = int(len(e) * 0.12)  # evita la intro
    k = lo + int(np.argmax(e[lo:])) if len(e) > lo else 0
    seg = x[k * hop: k * hop + n].copy()
    if len(seg) < n: seg = np.concatenate([seg, np.zeros(n - len(seg))])
    fi, fo = int(0.25 * SR), int(0.8 * SR)
    seg[:fi] *= np.linspace(0, 1, fi); seg[-fo:] *= np.linspace(1, 0, fo)
    return seg / (np.abs(seg).max() + 1e-9) * 0.6, path.name

def ai_music(g, B, seed=0, per_genre=3):
    """Con ElevenLabs: crea canciones del género hasta tener `per_genre` en la biblioteca (luego se reutilizan: ahorra créditos)."""
    if not os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVENLABS_MUSIC", "1") == "0": return
    have = library(g)
    if len(have) >= per_genre and seed < len(have): return
    if len(have) >= per_genre + 1: return
    try:
        import voces, time as _t
        d = MUSIC_DIR / g; d.mkdir(parents=True, exist_ok=True)
        voces.compose_music(g, d / f"ia-{g}-{int(_t.time())}.mp3", 30, str(B.get("publico", ""))[:150])
    except Exception as e:
        print("Eleven Music falló (sigo con lo que hay):", e)

# ---------- reels por escenas (guion de la IA) ----------
def ding(pitch=1.0):
    n = int(0.5 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1320 * pitch * t) + 0.5 * np.sin(2 * np.pi * 1980 * pitch * t)) * env(n, 0.002, 0.18) * 0.3
def scratch():
    n = int(0.06 * SR); s = rng.normal(0, 1, n); s = s - lowpass(s, 2)
    return s * env(n, 0.002, 0.02) * 0.12

def word_sfx(buf, words_lines, t0, anim, k0=0):
    """Un sonido por cada palabra que aparece (pop, subida, rebote, zoom o tecleo)."""
    for li, line in enumerate(words_lines):
        for i, w in enumerate(line):
            t = t0 + li * 0.35 + i * (0.18 if anim == "maquina" else 0.12)
            if anim == "maquina":
                for c in range(len(w)): add(buf, click(), t + c * 0.06, 0.35)
            elif anim == "subir": add(buf, whoosh(0.18, 1.6), t, 0.35)
            elif anim == "rebote": add(buf, pop(0.8 + 0.06 * i), t + 0.25, 0.8)
            elif anim == "zoom": add(buf, whoosh(0.22, 1.8), t, 0.4); add(buf, pop(1.3), t + 0.2, 0.5)
            else: add(buf, pop(1 + 0.08 * i + 0.1 * li), t, 0.8)

def sfx_story(story, TL):
    buf = np.zeros(int(TL["T"] * SR)); anim = story.get("animacion", "pop")
    for k, (sc, s) in enumerate(zip(story["escenas"], TL["scenes"])):
        t0, d, tp = s["start"], s["dur"], sc["tipo"]
        if k: add(buf, whoosh(0.4, 1.0 + 0.08 * k), max(0, t0 - 0.15), 0.85)
        if sc.get("texto") and tp not in ("pov", "broll"): add(buf, pop(1.25), t0 + 0.15, 0.6)  # aparece el rótulo
        if tp in ("gancho", "broll"):
            word_sfx(buf, [l.get("palabras", []) for l in sc.get("lineas", [])], t0 + 0.15, anim)
        elif tp == "pov":
            add(buf, pop(0.9), t0 + 0.1, 0.8); word_sfx(buf, [str(sc.get("texto", "")).split()], t0 + 0.35, anim)
        elif tp == "chat":
            import formatos
            for m, (ta, tb) in zip(sc.get("mensajes", []), formatos.chat_times(sc.get("mensajes", []))[0]):
                add(buf, pop(1.5 if m.get("de") == "yo" else 1.15), t0 + tb, 0.75)
        elif tp == "notificaciones":
            for i in range(len(sc.get("items", []))): add(buf, ding(1 + 0.06 * i), t0 + 0.4 + i * 0.65, 0.8)
        elif tp == "scroll": add(buf, whoosh(1.2, 0.8), t0 + 0.4, 0.5)
        elif tp == "escribir":
            n = sum(len(x) for x in sc.get("lineas", [])); dur = max(0.6, d - 1.1)
            for c in range(0, n, 2): add(buf, scratch(), t0 + 0.5 + dur * c / max(1, n), 1.0)
        elif tp == "antes_despues": add(buf, whoosh(0.6, 1.2), t0, 0.9); add(buf, impact(), t0 + 0.55, 0.5)
        elif tp == "top3":
            for i in range(3): add(buf, impact(), t0 + i * d / 3, 0.55); add(buf, pop(1.2), t0 + i * d / 3 + 0.2, 0.6)
        elif tp == "problema":
            for i, _ in enumerate(sc.get("items", [])): add(buf, pop(0.8), t0 + 0.55 + i * 0.5, 0.7); add(buf, click(), t0 + 0.68 + i * 0.5, 0.8)
        elif tp == "incluye":
            for i, _ in enumerate(sc.get("items", [])): add(buf, pop(1.2 + 0.08 * i), t0 + 0.5 + i * 0.45, 0.7)
            add(buf, sparkle(), t0 + 0.5 + len(sc.get("items", [])) * 0.45, 0.6)
        elif tp == "paginas":
            n = len(sc.get("paginas", [])); fe = max(0.55, (d - 1.0) / max(1, n - 1))
            for j in range(n - 1): add(buf, whoosh(0.42, 1.0 + 0.1 * j), t0 + 0.6 + j * fe, 0.8)
        elif tp == "grid":
            for i in range(6): add(buf, pop(1.3 + 0.05 * i), t0 + 0.2 + i * 0.16, 0.5)
        elif tp == "zoom": add(buf, whoosh(0.8, 0.6), t0 + 0.1, 0.6)
        elif tp == "movil":
            add(buf, whoosh(0.5, 1.3), t0, 0.9)
            for k2 in range(8): add(buf, pop(1.6 + 0.04 * (k2 % 5)), t0 + 0.3 + k2 * 0.22, 0.25)
        elif tp == "precio":
            add(buf, impact(), t0 + 0.05, 1.0); add(buf, pop(0.9), t0 + 0.35, 0.6); add(buf, pop(1.4), t0 + 0.5, 0.6)
            add(buf, click(), t0 + 0.62, 1.0); add(buf, sparkle(), t0 + 0.65, 1.0)
    return buf

def voice_durations(story, genero, tmpdir):
    """Genera (o toma de la caché) la voz de cada escena ANTES del video, para que cada escena dure lo que su frase."""
    out = []
    for sc in story["escenas"]:
        t = str(sc.get("voz") or "").strip()
        out.append(round(len(tts(t, genero, tmpdir, 1.0)) / SR, 2) if t else None)
    return out

def voice_story(story, TL, genero, tmpdir):
    """Una frase por escena, a ritmo natural. Nunca se corta: si una frase se alarga, la siguiente espera."""
    T = TL["T"]; buf = np.zeros(int(T * SR)); spans = []; free = 0.0
    for sc, s in zip(story["escenas"], TL["scenes"]):
        text = str(sc.get("voz") or "").strip()
        if not text: continue
        start = max(s["start"] + 0.15, free + 0.12)
        clip = tts(text, genero, tmpdir, 1.0)
        room = T - 0.12 - start
        if len(clip) / SR > room:  # solo puede pasar al final: un poco más rápido y, si aún no cabe, se acorta la frase
            clip = tts(text, genero, tmpdir, 1.08)
            if len(clip) / SR > room: clip = tts(shorten(text, room / (len(clip) / SR) * 0.95), genero, tmpdir, 1.05)
            if len(clip) / SR > room:
                n = int(room * SR); clip = clip[:n].copy(); f = min(n, int(0.15 * SR)); clip[-f:] *= np.linspace(1, 0, f)
        clip = soft_compress(clip / (np.abs(clip).max() + 1e-9))
        add(buf, clip, start); spans.append((start, start + len(clip) / SR)); free = start + len(clip) / SR
    return buf, spans

# ---------- voz (Piper) ----------
def read_wav(path):
    with wave.open(str(path)) as w:
        v = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2: v = v[::2]
        sr = w.getframerate()
    if sr != SR: v = np.interp(np.arange(0, len(v), sr / SR), np.arange(len(v)), v)
    return v

LAST_ENGINE = {"v": ""}
def tts(text, genero, tmpdir, speed=1.0):
    if os.environ.get("ELEVENLABS_API_KEY"):  # voz natural (de pago); si falla, sigue con Piper
        try:
            import voces
            import hashlib
            vid = voces.pick_voice(genero)  # incluye la voz en la clave: si cambia la voz, no se reutiliza
            cdir = MUSIC_DIR.parent / "voz-cache"; cdir.mkdir(parents=True, exist_ok=True)
            mp3 = cdir / f"{hashlib.sha1(f'{vid}|{speed}|{text}'.encode()).hexdigest()[:20]}.mp3"
            if not mp3.exists(): voces.tts_mp3(text, genero, mp3, speed)
            LAST_ENGINE["v"] = "ElevenLabs"; v = decode(mp3); nz = np.flatnonzero(np.abs(v) > 0.02)
            return v[max(0, nz[0] - 800): nz[-1] + 2000] if len(nz) else v
        except Exception as e:
            print("ElevenLabs falló, uso Piper:", e)
    LAST_ENGINE["v"] = "Piper (gratis)"
    voice = VOICES.get(genero, VOICES["femenina"]); model = VOICES_DIR / f"{voice}.onnx"
    if not model.exists(): raise RuntimeError(f"Falta la voz {voice} en {VOICES_DIR}")
    out = pathlib.Path(tmpdir) / f"voz_{abs(hash((text, speed))) % 10**8}.wav"
    cmd = ["python3", "-m", "piper", "-m", str(model), "-f", str(out)]
    r = subprocess.run(cmd + ["--length-scale", str(round(1 / speed, 2))],
                       input=text.encode(), capture_output=True)
    if r.returncode != 0 or not out.exists():  # versiones de piper sin esas opciones
        subprocess.run(cmd, input=text.encode(), check=True, capture_output=True)
    v = read_wav(out)
    nz = np.flatnonzero(np.abs(v) > 0.02)  # quita silencios de los bordes
    return v[max(0, nz[0] - 800): nz[-1] + 2000] if len(nz) else v

def soft_compress(x, thr=0.45, ratio=2.5):
    """Compresor limpio: solo baja los picos por encima del umbral (sin saturar como una radio)."""
    a = np.abs(x); y = np.where(a > thr, thr + (a - thr) / ratio, a) * np.sign(x)
    return y / (np.abs(y).max() + 1e-9) * 0.9

def shorten(text, ratio):
    """Recorta la frase (por comas o palabras) para que quepa sin acelerar la voz."""
    words = text.split(); keep = max(2, int(len(words) * ratio))
    cut = " ".join(words[:keep])
    for sep in (".", "!", "?", ",", ":"):
        j = cut.rfind(sep)
        if j > len(cut) * 0.5: return cut[: j + 1]
    return cut.rstrip(",;:") + "."

def voice_track(B, TL, tmpdir):
    """Voz a ritmo NATURAL: si una frase no cabe, se acorta (no se acelera más de un 6%)."""
    v = B.get("voz", {}); g = v.get("genero", "femenina"); guion = B.get("guion_voz", {})
    buf = np.zeros(int(TL["T"] * SR)); spans = []
    slots = [("gancho", 0.2, TL["flip_start"] - 0.05), ("paginas", TL["flip_start"] + 0.15, TL["s3a"] + 0.2),
             ("movil", TL["s3a"] + 0.35, TL["s4"] + 0.25), ("precio", TL["s4"] + 0.45, TL["T"] - 0.15)]
    free = 0
    for key, start, end in slots:
        text = str(guion.get(key) or "").strip()
        if not text: continue
        start = max(start, free + 0.15); room = end - start
        if room < 0.8: continue
        clip = tts(text, g, tmpdir, 1.0)
        for _ in range(3):
            dur = len(clip) / SR
            if dur <= room: break
            if dur <= room * 1.06: clip = tts(text, g, tmpdir, 1.06); break
            text = shorten(text, room / dur * 0.95); clip = tts(text, g, tmpdir, 1.0)
        clip = clip[: int(room * SR)]
        clip = soft_compress(clip / (np.abs(clip).max() + 1e-9))  # volumen parejo SIN distorsión
        add(buf, clip, start); spans.append((start, start + len(clip) / SR)); free = start + len(clip) / SR
    return buf, spans

# ---------- mezcla ----------
def mix(B, TL, out_wav, music_genre=None, with_voice=False, tmpdir="/tmp", seed=0, story=None):
    """music_genre: género (usa canción real de la biblioteca si hay; si no, ritmo sintetizado) · '0' = sin música."""
    T = TL["T"]; n = int(T * SR); info = {"musica": "ninguna"}
    sfx = sfx_story(story, TL) if story else sfx_track(B, TL)
    g = music_genre or "base"
    if g == "0": music = np.zeros(n)
    else:
        ai_music(g, B, seed)
        music, name = library_track(g, T, seed)
        if music is None:
            music = genre_track(g, T, (B.get("musica") or {}).get("bpm") if g != "base" else None)
            music = music / (np.abs(music).max() + 1e-9) * 0.6; info["musica"] = f"ritmo sintetizado ({g})"
        else: info["musica"] = f"canción real: {name}"; info["archivo"] = f"{g}/{name}"
        music = music[:n] if len(music) >= n else np.concatenate([music, np.zeros(n - len(music))])
    duck = np.ones(n)
    s4 = TL["scenes"][-1]["start"] if story else TL["s4"]
    i0, i1 = int(s4 * SR), min(n, int((s4 + 0.8) * SR)); duck[i0:i1] = np.linspace(0.55, 1, i1 - i0)
    voice = np.zeros(n); sfx_gain = np.ones(n)
    if with_voice:
        try:
            voice, spans = voice_story(story, TL, B["voz"]["genero"], tmpdir) if story else voice_track(B, TL, tmpdir); info["voz"] = "ok"
        except Exception as e:  # si la voz falla, el anuncio sale igual (sin voz) y se avisa
            print("voz falló:", e); voice, spans = np.zeros(n), []; info["voz"] = f"error: {e}"
        for a, b in spans:  # la música baja (sin desaparecer) mientras habla la voz
            ia, ib = int(max(0, a - 0.12) * SR), int(min(T, b + 0.2) * SR)
            duck[ia:ib] = np.minimum(duck[ia:ib], 0.5); sfx_gain[ia:ib] = 0.45
        k = int(0.08 * SR); duck = np.convolve(duck, np.ones(k) / k, "same"); sfx_gain = np.convolve(sfx_gain, np.ones(k) / k, "same")
    music_level = 1.25 if not with_voice else 1.0
    out = sfx * 0.45 * sfx_gain + music * duck * music_level + voice * 1.0
    out = out / (np.abs(out).max() + 1e-9) * 0.9  # solo normaliza: nada de saturación
    with wave.open(str(out_wav), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype(np.int16).tobytes())
    return info

def mux(video, wav, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(out)], check=True)
