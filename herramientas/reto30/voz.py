"""Reel FINAL del Reto 30 Días con voz (ElevenLabs) y música, y lo deja listo en el bot para publicar y hacer campañas.
Corre en el contenedor del estudio (usa su voz, su música y su caché de voces):
  docker exec pixelia-estudio python3 /pixelia/herramientas/reto30/voz.py
Resultado en storage/anuncios/regalo-reto-30-dias/: reel con voz y música, versión sin música para Meta, portada,
imágenes A/B/C (4x5, 9x16, 1x1) y un trabajo "terminado" en la base de datos → el bot lo ve como el último anuncio del regalo."""
import sys, os, json, pathlib, sqlite3, shutil, subprocess, tempfile, wave, datetime
import numpy as np
ROOT = pathlib.Path(os.environ.get("PIXELIA_DIR", "/pixelia"))
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "estudio")); sys.path.insert(0, str(HERE))
import audio  # noqa: E402  (voz ElevenLabs con caché, música de la biblioteca)

SLUG = "regalo-reto-30-dias"
OUT = ROOT / "storage" / "anuncios" / SLUG; OUT.mkdir(parents=True, exist_ok=True)
GENERO, MUSICA = os.environ.get("RETO_VOZ", "femenina"), os.environ.get("RETO_MUSICA", "pop")
FRASES = [  # una por escena: molestia, "ya no…", la hoja, gratis
    "¿Anotas tus metas… y a la semana ya ni te acuerdas?",
    "Ya no tienes que hacer esto.",
    "Con el Reto 30 Días escribes tus retos a tu manera: un check, o cuántas horas, vasos o páginas hiciste. Y la hoja te calcula sola tu racha y cuánto llevas.",
    "Es gratis. Comenta RETO, o descárgalo en el link del perfil. Y síguenos: cada semana hay un truco nuevo.",
]
BASE = [3.4, 1.6, 7.2, 3.8]
COPY = ("¿Anotas tus metas y a la semana ya ni te acuerdas? 🫠 Ya no tienes que hacer esto.\n\n"
        "🔥 Reto 30 Días: escribe tus retos a tu manera (✓ o cuántas horas, vasos, páginas…) y la hoja te calcula sola tu racha y tu avance.\n"
        "📱 Google Sheets (gratis, también en el celular) y Excel.\n\n"
        "💬 Comenta RETO y te lo pasamos, o descárgalo GRATIS en el link del perfil: pixeliadigital.app/reto\n"
        "👉 Síguenos: cada semana un truco nuevo.\n\n#reto #reto30dias #habitos #metas #productividad #googlesheets")

tmp = pathlib.Path(tempfile.mkdtemp())
try:
    voces = [audio.tts(f, GENERO, tmp) for f in FRASES]
    print("voz:", audio.LAST_ENGINE.get("v"))
    D = [round(max(b, len(v) / audio.SR + 0.45), 2) for b, v in zip(BASE, voces)]
    T = sum(D); n = int(T * audio.SR)
    voz = np.zeros(n); t = 0.0
    for d, v in zip(D, voces):
        k = int((t + 0.12) * audio.SR); voz[k:k + len(v)] += v[: max(0, n - k)]; t += d
    try: audio.ai_music(MUSICA, {"publico": "personas que quieren cumplir sus metas"})
    except Exception as e: print("música IA:", e)
    mus, nombre = audio.library_track(MUSICA, T)
    if mus is None: mus = audio.genre_track(MUSICA, T); nombre = "sintetizada"
    mus = np.asarray(mus[:n], dtype=np.float64)
    env_ = np.convolve((np.abs(voz) > 0.02).astype(float), np.ones(int(0.25 * audio.SR)) / int(0.25 * audio.SR), "same")
    duck = 0.32 - 0.22 * np.clip(env_ * 3, 0, 1)            # la música baja cuando habla la voz
    def wav(x, path):
        x = x / max(1.0, np.abs(x).max() / 0.95)
        with wave.open(str(path), "w") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(audio.SR); w.writeframes((x * 32767).astype(np.int16).tobytes())
    wav(voz + mus * duck, tmp / "mix.wav"); wav(voz, tmp / "voz.wav")
    import reel
    reel.D = D
    reel.render(str(OUT / "reel-reto30.mp4"), str(tmp / "mix.wav"), str(OUT / "portada-reel.jpg"))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(OUT / "reel-reto30.mp4"), "-i", str(tmp / "voz.wav"), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-shortest", str(OUT / "reel-sin-musica-para-meta.mp4")], check=True)
    for f in (HERE / "anuncios").glob("*.jpg"): shutil.copy(f, OUT / f.name)
    (OUT / "guion.json").write_text(json.dumps({"story": {"copy": {"texto": COPY, "titular": "GRATIS: Reto 30 Días"}, "formato": "reto30-manual",
                                                          "voz": GENERO, "musica": MUSICA}, "manual": True}, ensure_ascii=False, indent=1))
    db = sqlite3.connect(str(ROOT / "data" / "tienda.db"))
    row = db.execute("SELECT id FROM products WHERE slug = ?", (SLUG,)).fetchone()
    if not row: raise SystemExit("Falta el producto del regalo: corre antes herramientas/regalos.mjs")
    res = {"dir": str(OUT), "reel": "reel-reto30.mp4", "product_id": row[0], "manual": True, "sel": {"v": "f" if GENERO == "femenina" else "m", "g": MUSICA, "s": "ia"}}
    db.execute("INSERT INTO ad_jobs (product_id, options, status, result) VALUES (?, ?, 'done', ?)", (row[0], json.dumps({"manual": "reto30"}), json.dumps(res)))
    db.commit(); db.close()
    print(f"✔ Reel listo ({T:.1f} s, música: {nombre}) en {OUT}")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
