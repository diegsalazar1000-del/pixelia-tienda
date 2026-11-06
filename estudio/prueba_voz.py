"""Prueba de voces: genera una frase con voz femenina y masculina y la manda al bot del radar."""
import pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import estudio, audio, os, numpy as np, subprocess
tmp = tempfile.mkdtemp(); motor_ = "ElevenLabs" if os.environ.get("ELEVENLABS_API_KEY") else "Piper (gratis)"
for g in ("femenina", "masculina"):
    v = audio.tts("¿Tu agenda es un caos? Mira este planner: todo tu año, organizado y bonito.", g, tmp)
    wav = pathlib.Path(tmp) / f"{g}.wav"; mp3 = pathlib.Path(tmp) / f"voz-{g}.mp3"
    import wave
    with wave.open(str(wav), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(audio.SR); w.writeframes((np.clip(v, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), str(mp3)], check=True)
    estudio.tg("sendAudio", {"chat_id": estudio.CHAT, "caption": f"🎙️ Prueba de voz {g} · {motor_}", "title": f"Voz {g}"}, {"audio": mp3})
    print("✅ Enviada voz", g, "·", motor_)
