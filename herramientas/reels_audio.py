"""Voz ENÉRGICA de ElevenLabs (caché + volumen parejo) y música de Eleven Music para reels hechos a mano (serie de metas, Reto 30 Días…).
Corre en el contenedor del estudio. Uso: import reels_audio as RA; RA.preparar(); v = RA.tts(texto, RA.voz_energica("femenina")[0], tmp, 0)"""
import sys, os, json, pathlib, urllib.parse
import numpy as np
ROOT = pathlib.Path(os.environ.get("PIXELIA_DIR", "/pixelia"))
sys.path.insert(0, str(ROOT / "estudio"))
try:
    for _l in (ROOT / ".env").read_text().splitlines():
        if "=" in _l and not _l.strip().startswith("#"):
            _k, _v = _l.split("=", 1); _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
            if _k.startswith(("ELEVENLABS", "ANTHROPIC")) and _v: os.environ.setdefault(_k, _v)
except FileNotFoundError: pass
import audio, voces  # noqa: E402
SR = audio.SR
VOZ = {"stability": 0.30, "similarity_boost": 0.80, "style": 0.65, "use_speaker_boost": True, "speed": 1.08}
CACHE = ROOT / "storage" / "voces-reto30.json"
ENERGIA = ("energetic", "upbeat", "excited", "enthusiastic", "dynamic", "hype", "vibrant", "cheerful", "lively", "bold", "powerful", "intense")
def puntaje(v, gender):
    txt = " ".join(str(v.get(k, "")).lower() for k in ("name", "description", "descriptive", "use_case", "accent", "language", "locale", "age"))
    if str(v.get("gender", "")).lower() not in ("", gender): return -1
    s = 6 * sum(w in txt for w in ENERGIA[:6]) + 2 * sum(w in txt for w in ENERGIA[6:])
    if str(v.get("language", "")).lower().startswith("es") or "spanish" in txt: s += 5
    if any(w in txt for w in voces.LATAM): s += 4
    if any(w in txt for w in ("advert", "social", "commercial", "promo")): s += 3
    if "young" in txt or "middle" in txt: s += 1
    return s + min(2, (v.get("cloned_by_count") or 0) / 5000)
def voz_energica(genero):
    gender = "female" if genero == "femenina" else "male"
    c = {}
    try: c = json.loads(CACHE.read_text())
    except Exception: pass
    if c.get(gender): return c[gender]["id"], c[gender].get("name", "")
    cands = []
    for p in ({"language": "es", "gender": gender, "search": "energetic", "page_size": 50},
              {"language": "es", "gender": gender, "use_cases": "advertisement", "page_size": 50},
              {"language": "es", "gender": gender, "search": "upbeat", "page_size": 50}):
        try: cands += voces.call("GET", "/shared-voices?" + urllib.parse.urlencode(p)).get("voices", [])
        except Exception as e: print("biblioteca:", e)
    cands = sorted({v["voice_id"]: v for v in cands}.values(), key=lambda v: puntaje(v, gender), reverse=True)
    best = None
    if cands and puntaje(cands[0], gender) > 0:
        v = cands[0]
        try: best = {"id": voces.call("POST", f"/voices/add/{v['public_owner_id']}/{v['voice_id']}", {"new_name": f"Pixelia {gender} enérgica"}).get("voice_id", v["voice_id"]), "name": v.get("name")}
        except Exception as e: print("no pude agregar la voz enérgica (uso la de siempre):", e)
    if not best: best = {"id": voces.pick_voice(genero), "name": "voz Pixelia de siempre"}
    c[gender] = best; CACHE.write_text(json.dumps(c, ensure_ascii=False, indent=1))
    return best["id"], best.get("name", "")
def tts(texto, vid, tmp, i):
    """Voz de ElevenLabs con caché (si se rehace el reel no se paga otra vez la misma frase) y volumen PAREJO:
    cada frase se lleva al mismo nivel, para que ninguna empiece 'bajitica' (pasó con la voz masculina)."""
    import hashlib
    cdir = ROOT / "storage" / "voz-cache"; cdir.mkdir(parents=True, exist_ok=True)
    mp3 = cdir / ("r30-" + hashlib.sha1(f"{vid}|{json.dumps(VOZ, sort_keys=True)}|{texto}".encode()).hexdigest()[:20] + ".mp3")
    if not mp3.exists():
        mp3.write_bytes(voces.call("POST", f"/text-to-speech/{vid}?output_format=mp3_44100_128", {"text": texto, "model_id": voces.MODEL, "voice_settings": VOZ}, raw=True, timeout=120))
    v = audio.decode(mp3); nz = np.flatnonzero(np.abs(v) > 0.02)
    v = v[max(0, nz[0] - 600): nz[-1] + 1500] if len(nz) else v
    return nivelar(v)

def nivelar(v, objetivo=0.12):
    """Volumen parejo dentro de la frase y entre frases: sube las partes bajas (ventanas de 0,3 s) sin pasarse."""
    v = np.asarray(v, dtype=np.float64)
    voz = v[np.abs(v) > 0.01]
    if not len(voz): return v
    v = v * (objetivo / (np.sqrt(np.mean(voz ** 2)) + 1e-9))            # misma fuerza en todas las frases
    w = int(0.3 * SR); n = len(v)
    rms = np.sqrt(np.convolve(v ** 2, np.ones(w) / w, "same")) + 1e-9
    g = np.clip(objetivo / rms, 1.0, 3.5)                                  # solo sube lo que quedó bajito (máx ×3,5)
    g[rms < objetivo * 0.15] = 1.0                                         # los silencios no se suben (nada de ruido)
    g = np.convolve(g, np.ones(w) / w, "same")
    v = v * g
    return v / max(1.0, np.abs(v).max() / 0.98)

# ---------- música compuesta para este reel (se reutiliza) ----------
def musica(T, nueva):
    f = ROOT / "storage" / "musica" / "reto30" / "energetica.mp3"; f.parent.mkdir(parents=True, exist_ok=True)
    if nueva or not f.exists():
        prompt = (f"Energetic motivational Latin pop / electro instrumental for a fast social media reel about finally achieving your goals. "
                  f"Punchy drums and claps from the very first second, 124 BPM, bright synth hook, a short riser around second 4 and a big "
                  f"uplifting drop right after, confident and fun, no long intro, no vocals. Length about {int(T) + 2} seconds.")
        data = voces.call("POST", "/music?output_format=mp3_44100_128", {"prompt": prompt, "music_length_ms": int((T + 2) * 1000),
                          "model_id": os.environ.get("ELEVENLABS_MUSIC_MODEL", "music_v1"), "force_instrumental": True}, raw=True, timeout=300)
        f.write_bytes(data); print("🎵 música nueva compuesta con Eleven Music")
    x = audio.decode(f); n = int(T * SR)
    if len(x) < n: x = np.tile(x, n // max(1, len(x)) + 1)
    x = x[:n].copy(); fo = int(0.9 * SR); x[-fo:] *= np.linspace(1, 0, fo)
    return x / (np.abs(x).max() + 1e-9)

def wav(x, path):
    import wave
    x = x / max(1.0, np.abs(x).max() / 0.95)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype(np.int16).tobytes())

def preparar():
    if not voces.key(): raise SystemExit("❌ No hay clave de ElevenLabs: no hago el reel con voz robótica.")
    if audio.ahorro(): raise SystemExit("❌ El modo ahorro está encendido (/ahorro off en el bot).")
