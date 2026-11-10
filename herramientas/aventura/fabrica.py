"""Fabrica en el ESTUDIO los libros personalizados pagados (la tienda los pide con /api/studio/libro-next):
PDF con build.generar + una voz por misión con ElevenLabs (voz real, ~900 caracteres por libro; AVENTURA_VOZ=piper la apaga) y Piper gratis de respaldo → storage/libros/<pedido>/ → avisa a la tienda."""
import json, os, pathlib, subprocess, sys, tempfile, traceback
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
VOCES = pathlib.Path(os.environ.get("PIPER_VOICES", "/voces")); MODELO = VOCES / "es_MX-claude-high.onnx"

def voz(texto, mp3):
    if os.environ.get("AVENTURA_VOZ", "eleven") != "piper":   # voz real (pedido de Diego 10-nov); si falla o no hay créditos → Piper
        try:
            est = pathlib.Path(os.environ.get("PIXELIA_DIR", "/pixelia")) / "estudio"
            if str(est) not in sys.path: sys.path.insert(0, str(est))
            import voces
            if voces.key():
                voces.tts_mp3(texto, "femenina", mp3, 0.95); return "ElevenLabs"
        except Exception as e: print("ElevenLabs falló, uso Piper:", e, flush=True)
    piper(texto, mp3); return "Piper"

def piper(texto, mp3):
    wav = pathlib.Path(tempfile.mktemp(suffix=".wav"))
    subprocess.run(["python3", "-m", "piper", "-m", str(MODELO), "-f", str(wav), "--length-scale", "1.08"], input=texto.encode(), capture_output=True)
    if not wav.exists(): subprocess.run(["python3", "-m", "piper", "-m", str(MODELO), "-f", str(wav)], input=texto.encode(), check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af", "apad=pad_dur=0.4,volume=1.6", "-ac", "1", "-b:a", "64k", str(mp3)], check=True)
    wav.unlink(missing_ok=True)

def fabricar(job, raiz, api):
    pid = job["id"]
    try:
        import build
        out = pathlib.Path(raiz) / "storage" / "libros" / pid
        r = build.generar(job["datos"], out)
        for i, t in enumerate(r["voces"]):
            try: voz(t, out / f"m{i + 1}.mp3")
            except Exception as e: print("voz", i + 1, e, flush=True)   # sin voz igual se entrega (la página muestra el texto)
        api("POST", "/api/studio/libro-done", {"id": pid, "archivo": f"libros/{pid}/libro.pdf"})
        print("📚 libro listo", pid, r["paginas"], "páginas nivel", r["nivel"], flush=True)
    except Exception as e:
        traceback.print_exc(); api("POST", "/api/studio/libro-done", {"id": pid, "error": str(e)[:300]})
