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

def add(buf, snd, t, gain=1.0):
    i = int(t * SR); j = min(len(buf), i + len(snd))
    if 0 <= i < len(buf): buf[i:j] += snd[: j - i] * gain

# ---------- géneros (patrones originales) ----------
def genre_track(genre, T, bpm=None):
    out = np.zeros(int(T * SR)); g = (genre or "base").lower()
    spec = {"reggaeton": (95, ["Am", "F", "C", "G"]), "pop": (118, ["C", "G", "Am", "F"]), "electronica": (124, ["Am", "F", "C", "G"]),
            "lofi": (80, ["Dm", "G", "C", "Am"]), "acustica": (100, ["G", "D", "Em", "C"]), "base": (118, ["Am", "Am", "C", "G"])}
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

# ---------- voz (Piper) ----------
def read_wav(path):
    with wave.open(str(path)) as w:
        v = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2: v = v[::2]
        sr = w.getframerate()
    if sr != SR: v = np.interp(np.arange(0, len(v), sr / SR), np.arange(len(v)), v)
    return v

def tts(text, genero, tmpdir, speed=1.0):
    voice = VOICES.get(genero, VOICES["femenina"]); model = VOICES_DIR / f"{voice}.onnx"
    if not model.exists(): raise RuntimeError(f"Falta la voz {voice} en {VOICES_DIR}")
    out = pathlib.Path(tmpdir) / f"voz_{abs(hash(text)) % 10**8}.wav"
    cmd = ["python3", "-m", "piper", "-m", str(model), "-f", str(out)]
    r = subprocess.run(cmd + ["--length-scale", str(round(1 / speed, 2))], input=text.encode(), capture_output=True)
    if r.returncode != 0 or not out.exists():  # versiones de piper sin esa opción
        subprocess.run(cmd, input=text.encode(), check=True, capture_output=True)
    return read_wav(out)

def voice_track(B, TL, tmpdir):
    v = B.get("voz", {}); g = v.get("genero", "femenina"); guion = B.get("guion_voz", {})
    buf = np.zeros(int(TL["T"] * SR)); spans = []
    slots = [("gancho", 0.25, 2.3), ("paginas", TL["flip_start"], TL["t2_end"]), ("movil", TL["s3a"] + 0.3, TL["s4"] - 0.1), ("precio", TL["s4"] + 0.5, TL["T"] - 0.3)]
    for key, start, end in slots:
        text = guion.get(key)
        if not text: continue
        clip = tts(text, g, tmpdir, speed=1.12)
        room = end - start
        if len(clip) / SR > room:  # si no cabe, se acelera un poco más
            clip = tts(text, g, tmpdir, speed=min(1.45, 1.12 * (len(clip) / SR) / room))
        add(buf, clip / (np.abs(clip).max() + 1e-9) * 0.95, start); spans.append((start, start + len(clip) / SR))
    return buf, spans

# ---------- mezcla ----------
def mix(B, TL, out_wav, music_genre=None, with_voice=False, tmpdir="/tmp"):
    T = TL["T"]; n = int(T * SR)
    sfx = sfx_track(B, TL)
    music = genre_track(music_genre or "base", T, (B.get("musica") or {}).get("bpm") if music_genre else None)
    duck = np.ones(n)
    i0, i1 = int(TL["s4"] * SR), int((TL["s4"] + 0.8) * SR); duck[i0:i1] = np.linspace(0.35, 1, i1 - i0)
    voice = np.zeros(n)
    if with_voice:
        voice, spans = voice_track(B, TL, tmpdir)
        for a, b in spans:  # la música baja mientras habla la voz
            ia, ib = int(max(0, a - 0.1) * SR), int(min(T, b + 0.15) * SR); duck[ia:ib] = np.minimum(duck[ia:ib], 0.32)
        duck = lowpass(duck, int(0.05 * SR)) + duck * 0  # suaviza
        duck[duck == 0] = 1
    level = 0.55 if music_genre else 0.45
    out = sfx * (0.7 if with_voice else 1.0) + music * duck * level + voice * 1.0
    out = out / (np.abs(out).max() + 1e-9) * 0.89
    with wave.open(str(out_wav), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype(np.int16).tobytes())

def mux(video, wav, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(out)], check=True)
