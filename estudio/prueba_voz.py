"""Prueba de voces: genera una frase con voz femenina y masculina y la manda al bot del radar."""
import pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import estudio, audio, os, numpy as np, subprocess
tmp = tempfile.mkdtemp()
if "--reset" in sys.argv:
    import voces; voces.reset(); print("🔄 Voces olvidadas: elijo de nuevo")
for g in ("femenina", "masculina"):
    v = audio.tts("¿Tu agenda es un caos? Mira este planner: todo tu año, organizado y bonito.", g, tmp)
    motor_ = audio.LAST_ENGINE["v"]
    wav = pathlib.Path(tmp) / f"{g}.wav"; mp3 = pathlib.Path(tmp) / f"voz-{g}.mp3"
    import wave
    with wave.open(str(wav), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(audio.SR); w.writeframes((np.clip(v, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), str(mp3)], check=True)
    estudio.tg("sendAudio", {"chat_id": estudio.CHAT, "caption": f"🎙️ Prueba de voz {g} · {motor_}", "title": f"Voz {g}"}, {"audio": mp3})
    import voces, json as _j
    info = _j.loads(voces.cache_file().read_text()).get("female" if g == "femenina" else "male", {}) if voces.cache_file().exists() else {}
    print("✅ Enviada voz", g, "·", motor_, ("· " + str(info.get("name")) + (" (biblioteca)" if info.get("source") == "library" else " (de la cuenta)")) if info and motor_ == "ElevenLabs" else "")
if os.environ.get("ELEVENLABS_API_KEY"):
    try:
        import voces
        out = pathlib.Path(tmp) / "musica-prueba-reggaeton.mp3"; voces.compose_music("reggaeton", out, 10)
        estudio.tg("sendAudio", {"chat_id": estudio.CHAT, "caption": "🎵 Prueba de música · Eleven Music · reggaetón (10 s)", "title": "Prueba reggaetón"}, {"audio": out})
        print("✅ Música de prueba enviada")
    except Exception as e:
        print("ℹ️ La música de ElevenLabs no funcionó:", e, "\n   (la API de música solo funciona en planes de pago: Starter o superior)")
