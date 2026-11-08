"""Clip corto en bucle para la página /reto: la hoja llenándose sola (escena 3 del reel, sin textos de anuncio).
Uso: python3 demo_web.py salida.mp4 poster.jpg"""
import sys, subprocess, tempfile, shutil
sys.argv = [sys.argv[0], "x", *sys.argv[1:]]
import reel
OUT, POSTER = sys.argv[2], sys.argv[3]
reel.D = [0.0, 0.0, 6.5, 0.0]
tmp = tempfile.mkdtemp(); fps = 24; n = int(6.5 * fps)
for i in range(n + 24):   # +1 s quieto al final antes de repetir
    im = reel.frame(min(i, n - 1) / fps).crop((0, 160, 1080, 1580)).resize((720, 946))
    im.save(f"{tmp}/{i:04d}.jpg", quality=86)
    if i == n - 1: im.save(POSTER, quality=84)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", f"{tmp}/%04d.jpg", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "27", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", OUT], check=True)
shutil.rmtree(tmp); print("ok", OUT)
