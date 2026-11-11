"""Reel corto del Plan Financiero 2027: clip de Gemini (problema) → la página en uso (2 pantallas) → cierre.
Uso: python3 herramientas/plan2027/reel.py <clip.mp4> <segundo_corte> "<gancho arriba>" "<subtítulo de la frase>" <salida.mp4>
Diego 11-nov: corto (~13 s), dinámico, letreros que NO tapen caras (gancho arriba pequeño, subtítulo abajo compacto)."""
import sys, pathlib, asyncio, subprocess, tempfile, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from anuncios import CSS, pantalla  # misma pantalla del plan que en las imágenes

CLIP, CORTE, GANCHO, FRASE, OUT = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
W, H = 720, 1280
FB = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
CAJA = HERE.parents[1] / "public" / "sonidos" / "caja-registradora.mp3"
T = pathlib.Path(tempfile.mkdtemp())
sh = lambda *a: subprocess.run(a, check=True, capture_output=True)

def letrero(txt, size, y, fondo=(0, 0, 0, 170), color=(255, 255, 255), amarillo=False):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); f = ImageFont.truetype(FB, size)
    lines, cur = [], ""
    for w in txt.split():
        if d.textlength((cur + " " + w).strip(), font=f) > W - 110: lines.append(cur); cur = w
        else: cur = (cur + " " + w).strip()
    lines.append(cur); lh = size * 1.25; bh = lh * len(lines) + 28
    bw = max(d.textlength(l, font=f) for l in lines) + 48
    x0 = (W - bw) / 2
    d.rounded_rectangle([x0, y, x0 + bw, y + bh], 22, fill=(255, 210, 63, 245) if amarillo else fondo)
    for i, l in enumerate(lines):
        d.text((W / 2, y + 14 + lh * i + lh / 2), l, font=f, fill=(20, 38, 31) if amarillo else color, anchor="mm")
    return im

FORM = """<div class="scr"><div class="top">📊 Tu plan 2027</div><div class="pad">
<div class="card"><b style="font-size:30px">💼 ¿A qué te dedicas?</b><div style="margin-top:14px;display:flex;flex-wrap:wrap;gap:10px;font-size:24px">
<span style="background:#1f7a5a;color:#fff;border-radius:30px;padding:10px 18px">💼 Empleado</span><span style="border:2px solid #d9efe5;border-radius:30px;padding:10px 18px">🛍️ Negocio</span><span style="border:2px solid #d9efe5;border-radius:30px;padding:10px 18px">🛵 Delivery</span></div></div>
<div class="card"><b style="font-size:30px">💵 ¿Cuánto ganas al mes?</b><div style="margin-top:14px;border:3px solid #1f7a5a;border-radius:18px;padding:16px 20px;font-size:44px;font-weight:800;text-align:right">$ 500<span style="color:#1f7a5a">|</span></div></div>
<div class="card"><b style="font-size:30px">🎯 Tu meta</b><div style="margin-top:12px;font-size:26px">🛟 Fondo de emergencia · $600</div></div>
<div style="background:#ffd23f;border-radius:20px;padding:22px;text-align:center;font-size:32px;font-weight:800;box-shadow:0 6px 0 #d9a800">✨ Ver mi plan</div></div></div>"""

async def pantallas():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        for nom, cuerpo, txt in [("s1", FORM, "Escribe lo que ganas…"), ("s2", pantalla(1.0), "…y mira tu plan de todo el año")]:
            await pg.set_content(f"""<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class="bg" style="height:1920px"><div class="glow" style="width:700px;height:700px;background:#ffd23f;top:-250px;right:-250px;opacity:.25"></div>
<h1 style="position:absolute;top:150px;left:60px;right:60px;text-align:center;font-size:78px">{txt}</h1>
<div class="phone" style="position:absolute;left:50%;transform:translateX(-50%);top:420px;width:760px">{cuerpo}</div></div></body></html>""")
            await pg.wait_for_timeout(300); await pg.screenshot(path=str(T / f"{nom}.png"))
        await pg.set_content(f"""<html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div class="bg" style="height:1920px">
<div class="glow" style="width:800px;height:800px;background:#ffd23f;top:500px;left:140px;opacity:.3"></div>
<div style="position:absolute;top:560px;left:60px;right:60px;text-align:center"><h1 style="font-size:110px">Tu plan 2027<br><b>en 1 minuto</b></h1>
<p class="sub" style="font-size:44px;margin-top:30px">Excel y Google Sheets · hecho con tus números</p>
<span class="cta" style="font-size:58px;padding:34px 60px;margin-top:70px">📊 Hazlo aquí 👇</span>
<p class="url" style="font-size:40px;margin-top:40px">Pago único $3.99 · sin suscripción</p></div></div></body></html>""")
        await pg.wait_for_timeout(300); await pg.screenshot(path=str(T / "fin.png"))
        await b.close()

def whoosh(path, dur=0.45):
    sr = 44100; n = int(sr * dur); t = np.arange(n) / sr; rng = np.random.default_rng(1)
    x = rng.normal(0, 1, n); env = np.sin(np.pi * t / dur) ** 2
    y = np.convolve(x, np.ones(6) / 6, "same") * env * 0.5
    w = wave.open(str(path), "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((y * 32767).astype("<i2").tobytes()); w.close()

asyncio.run(pantallas())
whoosh(T / "w.wav")
letrero(GANCHO, 40, 70).save(T / "gancho.png")
letrero(FRASE, 36, H - 250).save(T / "frase.png")

D1, D2, D3 = 1.6, 2.0, 2.4   # pantalla 1, pantalla 2, cierre
# 1) clip recortado con letreros (gancho 0-2.8 s, frase al final)
sh("ffmpeg", "-y", "-i", CLIP, "-i", T / "gancho.png", "-i", T / "frase.png", "-t", str(CORTE), "-filter_complex",
   f"[0:v]scale={W}:{H},fps=30[v];[v][1:v]overlay=0:0:enable='lt(t,2.8)'[a];[a][2:v]overlay=0:0:enable='gte(t,{CORTE-2.6})'[o]",
   "-map", "[o]", "-map", "0:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-ar", "44100", "-ac", "2", T / "c1.mp4")
# 2) pantallas con zoom suave + cierre
def img(src, dur, out, z0, z1):
    fr = int(dur * 30)
    sh("ffmpeg", "-y", "-loop", "1", "-i", src, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", str(dur), "-filter_complex",
       f"[0:v]scale=1440:2560,zoompan=z='{z0}+({z1}-{z0})*on/{fr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={fr}:s={W}x{H}:fps=30[v]",
       "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out)
img(T / "s1.png", D1, T / "c2.mp4", 1.0, 1.08)
img(T / "s2.png", D2, T / "c3.mp4", 1.12, 1.0)
img(T / "fin.png", D3, T / "c4.mp4", 1.0, 1.05)
(T / "l.txt").write_text("".join(f"file '{T}/c{i}.mp4'\n" for i in range(1, 5)))
sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", T / "l.txt", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", T / "base.mp4")
# 3) efectos: whoosh en cada corte + cha-ching al aparecer el plan
c2, c3, c4 = CORTE, CORTE + D1, CORTE + D1 + D2
sh("ffmpeg", "-y", "-i", T / "base.mp4", "-i", T / "w.wav", "-i", T / "w.wav", "-i", T / "w.wav", "-i", str(CAJA), "-filter_complex",
   f"[1:a]adelay={int((c2-0.2)*1000)}|{int((c2-0.2)*1000)}[a1];[2:a]adelay={int((c3-0.2)*1000)}|{int((c3-0.2)*1000)}[a2];"
   f"[3:a]adelay={int((c4-0.2)*1000)}|{int((c4-0.2)*1000)}[a3];[4:a]volume=0.8,adelay={int((c3+0.15)*1000)}|{int((c3+0.15)*1000)}[a4];"
   "[0:a][a1][a2][a3][a4]amix=inputs=5:normalize=0[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", OUT)
print("listo:", OUT)
