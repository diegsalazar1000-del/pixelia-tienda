"""Reels FINALES del Reto 30 Días con voz REAL de ElevenLabs (enérgica) + música compuesta con Eleven Music para este reel
+ efectos en los cortes. Hace DOS: voz masculina y voz femenina (para probar cuál engancha más).
Corre en el contenedor del estudio:
  docker exec pixelia-estudio python3 /pixelia/herramientas/reto30/voz.py            (las dos)
  docker exec pixelia-estudio python3 /pixelia/herramientas/reto30/voz.py femenina   (solo una)
  … --musica-nueva  (vuelve a componer la música; por defecto se reutiliza para ahorrar créditos)
Sin ElevenLabs NO sigue (nada de voz robótica de respaldo). Resultado en storage/anuncios/regalo-reto-30-dias/ y un trabajo
"terminado" por reel en la base de datos (el bot los ve como los últimos anuncios del regalo → campaña A/B)."""
import sys, os, json, pathlib, sqlite3, shutil, subprocess, tempfile, wave, time, urllib.parse
import numpy as np
ROOT = pathlib.Path(os.environ.get("PIXELIA_DIR", "/pixelia"))
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "estudio")); sys.path.insert(0, str(HERE))
# las claves están en /pixelia/.env (el estudio las lee al arrancar; un script suelto tiene que leerlas él mismo)
try:
    for _l in (ROOT / ".env").read_text().splitlines():
        if "=" in _l and not _l.strip().startswith("#"):
            _k, _v = _l.split("=", 1); _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
            if _k.startswith(("ELEVENLABS", "ANTHROPIC")) and _v: os.environ.setdefault(_k, _v)
except FileNotFoundError: pass
import audio, voces  # noqa: E402
try: import gasto  # noqa: E402
except Exception: gasto = None

SLUG = "regalo-reto-30-dias"
OUT = ROOT / "storage" / "anuncios" / SLUG; OUT.mkdir(parents=True, exist_ok=True)
GENEROS = [a for a in sys.argv[1:] if a in ("masculina", "femenina")] or ["masculina", "femenina"]
SR = audio.SR
FRASES = [  # una por escena: molestia, "ya no…", la hoja, gratis  (con signos para que la voz suene con energía)
    "¿Anotas tus metas… y a la semana ya ni te acuerdas?",
    "¡Ya no tienes que hacer esto!",
    "Con el Reto 30 Días escribes tus retos a tu manera: un check… o cuántas horas, vasos o páginas hiciste. ¡Y la hoja te calcula sola tu racha y cuánto llevas!",
    "¡Y es gratis! Comenta RETO, o descárgalo en el link del perfil. ¡Y síguenos, que cada semana hay un truco nuevo!",
]
BASE = [3.2, 1.5, 7.0, 3.6]
VOZ = {"stability": 0.30, "similarity_boost": 0.80, "style": 0.65, "use_speaker_boost": True, "speed": 1.08}   # enérgica
COPY = ("¿Anotas tus metas y a la semana ya ni te acuerdas? 🫠 Ya no tienes que hacer esto.\n\n"
        "🔥 Reto 30 Días: escribe tus retos a tu manera (✓ o cuántas horas, vasos, páginas…) y la hoja te calcula sola tu racha y tu avance.\n"
        "📱 Google Sheets (gratis, también en el celular) y Excel.\n\n"
        "💬 Comenta RETO y te lo pasamos, o descárgalo GRATIS en el link del perfil: pixeliadigital.app/reto\n"
        "👉 Síguenos: cada semana un truco nuevo.\n\n#reto #reto30dias #habitos #metas #productividad #googlesheets")
CACHE = ROOT / "storage" / "voces-reto30.json"

# ---------- voz enérgica: la buscamos en la biblioteca de ElevenLabs (español, latina, "energetic/upbeat") ----------
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
    mp3 = tmp / f"v{i}.mp3"
    data = voces.call("POST", f"/text-to-speech/{vid}?output_format=mp3_44100_128", {"text": texto, "model_id": voces.MODEL, "voice_settings": VOZ}, raw=True, timeout=120)
    mp3.write_bytes(data); v = audio.decode(mp3); nz = np.flatnonzero(np.abs(v) > 0.02)
    return v[max(0, nz[0] - 600): nz[-1] + 1500] if len(nz) else v

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
    x = x / max(1.0, np.abs(x).max() / 0.95)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype(np.int16).tobytes())

if not voces.key(): raise SystemExit("❌ No hay clave de ElevenLabs en el estudio: no hago el reel con voz robótica.")
if audio.ahorro(): raise SystemExit("❌ El modo ahorro está encendido (/ahorro off en el bot) y bloquea ElevenLabs.")
import reel  # noqa: E402
db = sqlite3.connect(str(ROOT / "data" / "tienda.db"))
row = db.execute("SELECT id FROM products WHERE slug = ?", (SLUG,)).fetchone()
if not row: raise SystemExit("Falta el producto del regalo: corre antes herramientas/regalos.mjs")
nueva = "--musica-nueva" in sys.argv
for f in (HERE / "anuncios").glob("*.jpg"): shutil.copy(f, OUT / f.name)
for genero in GENEROS:
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        vid, nombre = voz_energica(genero)
        voces_ = [tts(f, vid, tmp, i) for i, f in enumerate(FRASES)]
        D = [round(max(b, len(v) / SR + 0.35), 2) for b, v in zip(BASE, voces_)]
        T = sum(D); n = int(T * SR); voz = np.zeros(n); t = 0.0; cortes = []
        for d, v in zip(D, voces_):
            k = int((t + 0.08) * SR); voz[k:k + len(v)] += v[: max(0, n - k)]; cortes.append(t); t += d
        mus = musica(T, nueva); nueva = False
        env_ = np.convolve((np.abs(voz) > 0.02).astype(float), np.ones(int(0.2 * SR)) / int(0.2 * SR), "same")
        mix = voz * 1.0 + mus * (0.42 - 0.27 * np.clip(env_ * 3, 0, 1))   # música arriba en los huecos, abajo cuando habla
        fx = np.zeros(n)
        audio.add(fx, audio.impact(), 0.75 * D[0], 0.8)                 # sello "OLVIDADO"
        for c in cortes[1:]: audio.add(fx, audio.whoosh(0.4), max(0, c - 0.25), 0.7)
        audio.add(fx, audio.sparkle(), cortes[3] + 0.05, 1.0)             # "GRATIS"
        audio.add(fx, audio.pop(1.2), cortes[3] + 0.5 * D[3] / 3.6, 0.8)  # aparece "Comenta RETO"
        wav(mix + fx, tmp / "mix.wav"); wav(voz + fx, tmp / "voz.wav")
        reel.D = D
        nom = f"reel-reto30-{genero}.mp4"
        reel.render(str(OUT / nom), str(tmp / "mix.wav"), str(OUT / "portada-reel.jpg"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(OUT / nom), "-i", str(tmp / "voz.wav"), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-shortest", str(OUT / f"reel-reto30-{genero}-sin-musica.mp4")], check=True)
        (OUT / "guion.json").write_text(json.dumps({"story": {"copy": {"texto": COPY, "titular": "GRATIS: Reto 30 Días"}, "formato": "reto30-manual",
                                                              "voz": genero, "musica": "reto30"}, "manual": True}, ensure_ascii=False, indent=1))
        res = {"dir": str(OUT), "reel": nom, "product_id": row[0], "manual": True, "voz": genero, "sel": {"v": "f" if genero == "femenina" else "m", "g": "reto30", "s": "ia"}}
        db.execute("INSERT INTO ad_jobs (product_id, options, status, result) VALUES (?, ?, 'done', ?)", (row[0], json.dumps({"manual": "reto30", "voz": genero}), json.dumps(res)))
        db.commit()
        print(f"✔ Reel {genero} listo ({T:.1f} s, voz: {nombre}): {nom}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
db.close()
print("Míralos en el teléfono: pixeliadigital.app/media/anuncios/regalo-reto-30-dias/reel-reto30-masculina.mp4 y …-femenina.mp4")
