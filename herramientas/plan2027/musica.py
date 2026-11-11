"""Pone MÚSICA de Eleven Music a los reels del Plan 2027 (corre en el estudio, usa la clave de ElevenLabs del .env).
Uso: docker exec pixelia-estudio python3 /pixelia/herramientas/plan2027/musica.py [--musica-nueva]
Toma herramientas/plan2027/reels/base-*.mp4, compone UNA canción (se guarda en storage/musica/plan2027/fondo.mp3 y se reutiliza),
la mezcla bajita (baja más cuando hablan) y manda cada reel al bot del radar. Salida: storage/anuncios/plan-financiero-2027/reel-*.mp4"""
import sys, os, json, pathlib, subprocess, tempfile, uuid, urllib.request
import numpy as np
ROOT = pathlib.Path(os.environ.get("PIXELIA_DIR", "/pixelia"))
sys.path.insert(0, str(ROOT / "herramientas"))
import reels_audio as R  # noqa: E402  (carga las claves de ElevenLabs)

ENV = {}
for l in (ROOT / ".env").read_text().splitlines():
    if "=" in l and not l.strip().startswith("#"):
        k, v = l.split("=", 1); ENV[k.strip()] = v.strip().strip('"').strip("'")
TG, CHAT = ENV.get("RADAR_BOT_TOKEN", ""), ENV.get("TELEGRAM_ADMIN_CHAT_ID", "")
SR = R.SR
PROMPT = ("Modern instrumental for a short social media ad about taking control of your money. Starts minimal and a little tense "
          "(soft pulsing synth, ticking hi-hat) for the first 7 seconds, then a bright uplifting lift with warm piano chords, claps and a "
          "confident pop beat, optimistic and clean, ends with a clear resolved chord. No vocals, no long intro. Length about {seg} seconds.")

def tg_video(path, caption):
    if not TG or not CHAT: return
    b = uuid.uuid4().hex; body = bytearray()
    for k, v in {"chat_id": CHAT, "caption": caption}.items():
        body += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    body += f"--{b}\r\nContent-Disposition: form-data; name=\"video\"; filename=\"{path.name}\"\r\nContent-Type: video/mp4\r\n\r\n".encode() + path.read_bytes() + b"\r\n"
    body += f"--{b}--\r\n".encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{TG}/sendVideo", data=bytes(body), headers={"content-type": f"multipart/form-data; boundary={b}"})
    urllib.request.urlopen(req, timeout=180).read()

def audio_de(video):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(video), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float64) / 32768

bases = sorted((ROOT / "herramientas" / "plan2027" / "reels").glob("base-*.mp4"))
out_dir = ROOT / "storage" / "anuncios" / "plan-financiero-2027"; out_dir.mkdir(parents=True, exist_ok=True)
nueva = "--musica-nueva" in sys.argv
for i, base in enumerate(bases):
    x = audio_de(base); T = len(x) / SR
    mus = R.musica(T, nueva and i == 0, archivo="plan2027/fondo.mp3", prompt=PROMPT)[:len(x)]
    mus = np.pad(mus, (0, len(x) - len(mus)))
    w = int(0.2 * SR); env = np.convolve((np.abs(x) > 0.04).astype(float), np.ones(w) / w, "same")
    mix = x + mus * (0.30 - 0.20 * np.clip(env * 3, 0, 1))          # música bajita, baja más cuando hablan
    mix = mix / max(1.0, np.abs(mix).max() / 0.9)                    # sin saturar (que no distorsione en el teléfono)
    tmp = pathlib.Path(tempfile.mkdtemp()) / "a.wav"; R.wav(mix, tmp)
    out = out_dir / base.name.replace("base-", "reel-")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(base), "-i", str(tmp), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)], check=True)
    print("✔", out)
    try: tg_video(out, f"🎬 Plan 2027 · {base.stem.replace('base-', '')} · con música")
    except Exception as e: print("aviso Telegram:", e)
