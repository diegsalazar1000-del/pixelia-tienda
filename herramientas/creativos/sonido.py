"""Efectos de sonido y base rítmica ORIGINALES (sintetizados) sincronizados con el reel de motion.py.
Uso: python3 sonido.py anuncio.json  → out-v2/audio.wav y out-v2/reel-v2-sonido-9x16.mp4
"""
import json, sys, pathlib, subprocess, wave
import numpy as np

SR = 44100
rng = np.random.default_rng(3)

def env(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(d, 1e-4))
    return e

def lowpass(x, k):
    if k <= 1: return x
    c = np.cumsum(np.concatenate([[0], x])); y = (c[k:] - c[:-k]) / k
    return np.concatenate([y, np.zeros(len(x) - len(y))])

def pop(pitch=1.0):
    n = int(0.12 * SR); t = np.arange(n) / SR
    f = (500 + 900 * (t / t[-1])) * pitch
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.04)
    s += rng.normal(0, 0.15, n) * env(n, 0.001, 0.006)
    return s * 0.55

def whoosh(dur=0.42, bright=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    shape = np.sin(np.pi * t / dur) ** 2
    lo = lowpass(noise, 22); hi = noise - lowpass(noise, 4)
    s = (lo * (1 - t / dur) + hi * 0.35 * bright * (t / dur)) * shape
    return s * 0.45 / (np.abs(s).max() + 1e-9)

def impact():
    n = int(0.9 * SR); t = np.arange(n) / SR
    f = 120 * np.exp(-t * 6) + 42
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.35)
    crack = lowpass(rng.normal(0, 1, n), 3) * env(n, 0.001, 0.05)
    return (boom * 0.9 + crack * 0.35)

def sparkle():
    out = np.zeros(int(0.6 * SR))
    for i, fr in enumerate([1568, 1976, 2349, 3136]):
        n = int(0.25 * SR); t = np.arange(n) / SR
        s = np.sin(2 * np.pi * fr * t) * env(n, 0.002, 0.09) * 0.18
        o = int(i * 0.06 * SR); out[o:o + n] += s
    return out

def click():
    n = int(0.05 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * 1800 * t) * env(n, 0.001, 0.012) * 0.4

def beat(total, bpm=118, start=0.0, end=None):
    """Base original: bombo, hi-hat y bajo sencillo."""
    out = np.zeros(int(total * SR)); spb = 60 / bpm; end = end or total
    kick_n = int(0.25 * SR); tk = np.arange(kick_n) / SR
    kick = np.sin(2 * np.pi * np.cumsum(140 * np.exp(-tk * 18) + 45) / SR) * env(kick_n, 0.001, 0.12)
    hat_n = int(0.05 * SR); hat = (rng.normal(0, 1, hat_n) - lowpass(rng.normal(0, 1, hat_n), 2)) * env(hat_n, 0.001, 0.015) * 0.25
    bass_notes = [55.0, 55.0, 65.41, 49.0]
    b = start; k = 0
    while b < end:
        i = int(b * SR)
        if i + kick_n < len(out): out[i:i + kick_n] += kick * 0.55
        h = int((b + spb / 2) * SR)
        if h + hat_n < len(out): out[h:h + hat_n] += hat
        bn = int(spb * SR * 0.9); tb = np.arange(bn) / SR
        f = bass_notes[(k // 4) % 4]
        bass = (np.sin(2 * np.pi * f * tb) + 0.3 * np.sin(2 * np.pi * 2 * f * tb)) * env(bn, 0.01, 0.25) * 0.22
        if i + bn < len(out): out[i:i + bn] += bass
        b += spb; k += 1
    # entrada y salida suaves
    fade = int(0.4 * SR); out[:fade] *= np.linspace(0, 1, fade); out[-fade:] *= np.linspace(1, 0, fade)
    return out

def add(buf, snd, t, gain=1.0):
    i = int(t * SR); j = min(len(buf), i + len(snd))
    if i < len(buf): buf[i:j] += snd[: j - i] * gain

def build(A, out_wav):
    T = A["segundos"]; buf = np.zeros(int(T * SR))
    music = beat(T, start=0.0)
    # Gancho: un "pop" por palabra
    for li, line in enumerate(A["gancho"]):
        for i, _ in enumerate(line["palabras"]):
            add(buf, pop(1 + 0.08 * i + 0.1 * li), 0.1 + li * 0.35 + i * 0.12 + 0.05, 0.8)
    # Entrada del iPad y hojas que pasan
    n = len(A["paginas"]); flip_start, flip_each = 2.7, 0.75
    add(buf, whoosh(0.5, 0.6), 2.15, 0.9)
    for k in range(n - 1): add(buf, whoosh(0.42, 1.0 + 0.1 * k), flip_start + k * flip_each, 0.85)
    for j in range(6): add(buf, pop(1.3 + 0.05 * j), 2.3 + j * 0.25 + 0.12, 0.45)
    t2_end = flip_start + flip_each * (n - 1) + 0.6
    s3a = t2_end + 0.2; s4 = t2_end + 3.0
    # Móvil + lluvia de stickers
    add(buf, whoosh(0.5, 1.3), s3a - 0.05, 1.0)
    for i, _ in enumerate(A["movil_texto"]): add(buf, pop(1.1 + 0.06 * i), s3a + 0.2 + i * 0.12 + 0.05, 0.7)
    for k in range(10): add(buf, pop(1.6 + 0.04 * (k % 5)), s3a + 0.3 + k * 0.22, 0.25)
    # Precio que golpea
    add(buf, impact(), s4 + 0.05, 1.0)
    add(buf, pop(0.9), s4 + 0.35, 0.6); add(buf, pop(1.4), s4 + 0.5, 0.6)
    add(buf, click(), s4 + 0.62, 1.0); add(buf, sparkle(), s4 + 0.65, 1.0)
    # La música baja (ducking) justo en el golpe de precio
    duck = np.ones_like(music); i0 = int((s4) * SR); i1 = int((s4 + 0.8) * SR)
    duck[i0:i1] = np.linspace(0.35, 1, i1 - i0)
    mix = buf + music * duck * 0.8
    # "voz" (si existe una pista de voz, se mezcla)
    voz = pathlib.Path(out_wav).with_name("voz.wav")
    if voz.exists():
        with wave.open(str(voz)) as w:
            v = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
            if w.getnchannels() == 2: v = v[::2]
            if w.getframerate() != SR: v = np.interp(np.arange(0, len(v), w.getframerate() / SR), np.arange(len(v)), v)
        mix[: len(v)] = mix[: len(v)] * 0.55 + v[: len(mix)] * 1.0
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.89
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(str(out_wav), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

if __name__ == "__main__":
    A = json.load(open(sys.argv[1])); base = pathlib.Path(sys.argv[1]).parent / "out-v2"
    wav = base / "audio.wav"; build(A, wav)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(base / "reel-v2-9x16.mp4"), "-i", str(wav),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                    str(base / "reel-v2-sonido-9x16.mp4")], check=True)
    print("ok")
