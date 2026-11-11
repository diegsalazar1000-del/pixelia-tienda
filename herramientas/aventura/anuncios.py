"""Imágenes de anuncio de MI GRAN AVENTURA en el estilo que le gustó a Diego (su arte de Canva): fondo oscuro con neón y estrellas,
titular grande de 3-4 líneas con palabras en color, caja de subtítulo con borde neón, columna de beneficios con íconos, foto real
(fotograma del video de Gemini), páginas reales del libro en abanico, sello redondo y barra de llamada a la acción. Sin estrellas de
reseñas ni "favorito de…" (no hay reseñas todavía: nada inventado).
  python3 anuncios.py   → storage/anuncios/mi-gran-aventura/{A,B,C}-{4x5,9x16}.jpg"""
import sys, math, random, subprocess, tempfile, pathlib
from PIL import Image, ImageDraw, ImageFilter, ImageFont
HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE)); import build as B
OUT = ROOT / "storage" / "anuncios" / "mi-gran-aventura"; OUT.mkdir(parents=True, exist_ok=True)
GAL = ROOT / "public" / "img" / "galeria"; SRC = HERE / "clips" / "fuente.mp4"
F = B.F; AMA, CIAN, ROSA, VERDE, BLANCO, NOCHE = (255, 200, 40), (60, 220, 255), (255, 79, 163), (90, 230, 120), (255, 255, 255), (10, 12, 34)

def fotograma(seg):
    f = tempfile.mktemp(suffix=".jpg"); subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(seg), "-i", str(SRC), "-frames:v", "1", "-q:v", "2", f], check=True)
    return Image.open(f).convert("RGB")
def fondo(W, H, seed):
    im = Image.new("RGB", (W, H), NOCHE); d = ImageDraw.Draw(im)
    for y in range(H): k = y / H; d.line([0, y, W, y], fill=(int(10 + 18 * k), int(12 + 6 * k), int(34 + 30 * k)))
    r = random.Random(seed)
    for _ in range(140):
        x, y, s = r.randrange(W), r.randrange(H), r.choice([1, 1, 2, 2, 3]); d.ellipse([x, y, x + s, y + s], fill=(255, 255, 255, ))
    return im.convert("RGBA")
def glow(im, dibujar, color, radio=18, fuerza=2):
    capa = Image.new("RGBA", im.size, (0, 0, 0, 0)); dibujar(ImageDraw.Draw(capa), color)
    g = capa.filter(ImageFilter.GaussianBlur(radio))
    for _ in range(fuerza): im.alpha_composite(g)
    im.alpha_composite(capa)
def texto_neon(im, xy, t, f, col, anchor="mm", sombra=True):
    if sombra: glow(im, lambda d, c: d.text(xy, t, font=f, fill=c, anchor=anchor), col + (200,), 14, 1)
    ImageDraw.Draw(im).text(xy, t, font=f, fill=col, anchor=anchor, stroke_width=3, stroke_fill=(20, 15, 40))
def caja_neon(im, box, col, r=34, ancho=4, relleno=(14, 16, 44, 230)):
    ImageDraw.Draw(im).rounded_rectangle(box, r, fill=relleno)
    glow(im, lambda d, c: d.rounded_rectangle(box, r, outline=c, width=ancho), col + (255,), 10, 1)
def emoji(im, ch, x, y, s): e = B.emoji(ch, s); im.alpha_composite(e, (int(x - e.width / 2), int(y - e.height / 2)))
def foto_redonda(foto, w, h, x, y, im, col):
    f = foto.copy(); r = max(w / f.width, h / f.height); f = f.resize((int(f.width * r) + 1, int(f.height * r) + 1), Image.LANCZOS)
    f = f.crop(((f.width - w) // 2, (f.height - h) // 2, (f.width - w) // 2 + w, (f.height - h) // 2 + h)).convert("RGBA")
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], 44, fill=255); f.putalpha(m)
    glow(im, lambda d, c: d.rounded_rectangle([x, y, x + w, y + h], 44, outline=c, width=6), col + (255,), 16, 2); im.alpha_composite(f, (x, y))
def hoja(nombre, ancho, ang):
    p = Image.open(GAL / nombre).convert("RGBA"); p = p.resize((ancho, round(p.height * ancho / p.width)), Image.LANCZOS)
    m = Image.new("L", p.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, p.width - 1, p.height - 1], 16, fill=255); p.putalpha(m)
    s = Image.new("RGBA", (p.width + 60, p.height + 60), (0, 0, 0, 0)); ImageDraw.Draw(s).rounded_rectangle([30, 42, p.width + 30, p.height + 42], 18, fill=(0, 0, 0, 150))
    s = s.filter(ImageFilter.GaussianBlur(14)); s.alpha_composite(p, (30, 30)); return s.rotate(ang, expand=True, resample=Image.BICUBIC)
def sello(im, cx, cy, r):
    d = ImageDraw.Draw(im); pts = [(cx + (r if k % 2 == 0 else r * .9) * math.cos(k * math.pi / 16), cy + (r if k % 2 == 0 else r * .9) * math.sin(k * math.pi / 16)) for k in range(32)]
    d.polygon(pts, fill=(212, 160, 23)); d.ellipse([cx - r * .78, cy - r * .78, cx + r * .78, cy + r * .78], fill=(25, 20, 50), outline=(255, 214, 90), width=5)
    for j, (t, s, c) in enumerate([("CON SU", .2, BLANCO), ("NOMBRE", .27, AMA), ("en cada página", .13, BLANCO)]):
        d.text((cx, cy - r * .32 + j * r * .3), t, font=F(int(r * s), "Bold"), fill=c, anchor="mm")

DISEÑOS = {
 "A": {"lin": [("Un libro donde", BLANCO, 74), ("SU NOMBRE", AMA, 118), ("es el héroe", CIAN, 92)], "sub": "12 misiones con su nombre, su mascota y su familia, de su edad (2 a 8 años).", "foto": 15.6, "col": CIAN},
 "B": {"lin": [("Menos pantallas,", BLANCO, 82), ("más", AMA, 96), ("aventuras", ROSA, 120)], "sub": "Cambia la tablet por un libro de actividades hecho para tu hijo, con su nombre.", "foto": 36.2, "col": ROSA},
 "C": {"lin": [("Aprende letras", BLANCO, 80), ("y números…", AMA, 90), ("¡rescatando a su perrito!", CIAN, 62)], "sub": "Cada actividad es una misión de su propia historia. Aprende jugando, sin darse cuenta.", "foto": 24.8, "col": VERDE},
}
BENEF = [("✏️", "Trazos y motricidad"), ("🔤", "Letras en español con Ñ"), ("🔢", "Números y lógica"), ("🔊", "QR que lo felicita por su nombre")]

def pieza(k, W, H):
    D = DISEÑOS[k]; im = fondo(W, H, ord(k)); alto = H / 1350; col = D["col"]
    emoji(im, "⭐", 100, 110 * alto, 90); emoji(im, "✨", W - 110, 150 * alto, 80)
    y = 120 * alto
    for t, c, s in D["lin"]:
        f = B.encajar(ImageDraw.Draw(im), t, W - 160, s); texto_neon(im, (W / 2, y + f.size / 2), t, f, c); y += f.size * 1.02
    y += 16 * alto
    caja_neon(im, [60, y, W - 60, y + 120], col); ls = B.wrap(ImageDraw.Draw(im), D["sub"], F(32, "Medium"), W - 200)
    for j, l in enumerate(ls[:2]): ImageDraw.Draw(im).text((W / 2, y + 60 + (j - (len(ls[:2]) - 1) / 2) * 42), l, font=F(32, "Medium"), fill=BLANCO, anchor="mm")
    y += 150 * (1 if H == 1350 else 1.15)
    # columna de beneficios + foto (en 4:5 todo más compacto y el libro encima de la foto, como un mockup)
    alto9 = H > 1350; paso = 116 if alto9 else 104; caja = 100 if alto9 else 92
    fy = int(y); fh = int(H - 330 * alto - fy - 160) if alto9 else paso * 4 - 12
    foto_redonda(fotograma(D["foto"]), 500, fh, W - 560, fy, im, col)
    by = fy
    for e, t in BENEF:
        caja_neon(im, [40, by, 500, by + caja], col, r=28, ancho=3); emoji(im, e, 95, by + caja / 2, 52)
        ls = B.wrap(ImageDraw.Draw(im), t, F(29, "Bold"), 320)
        for j, l in enumerate(ls[:2]): ImageDraw.Draw(im).text((140, by + caja / 2 + (j - (len(ls[:2]) - 1) / 2) * 34), l, font=F(29, "Bold"), fill=BLANCO, anchor="lm")
        by += paso
    if alto9:
        py = max(by, fy + fh) - 40
        for nombre, x, ang, w in [("aventura-mapa.jpg", W / 2 + 120, -9, 250), ("aventura-mision.jpg", W / 2 - 150, 8, 250), ("aventura-portada.jpg", W / 2 - 10, -2, 290)]:
            h_ = hoja(nombre, w, ang); im.alpha_composite(h_, (int(x - h_.width / 2), int(py)))
        sello(im, 150, py + 190, 115)
    else:   # páginas reales del libro saliendo de la esquina de la foto + sello sobre los beneficios
        for nombre, x, yy, ang, w in [("aventura-mision.jpg", W - 330, fy + fh - 170, 10, 170), ("aventura-portada.jpg", W - 175, fy + fh - 210, -6, 200)]:
            h_ = hoja(nombre, w, ang); im.alpha_composite(h_, (int(x - h_.width / 2), int(yy)))
        sello(im, 470, fy + fh + 20, 78)
    # barra final
    cy = H - 160 * alto
    caja_neon(im, [60, cy - 55, W - 60, cy + 55], AMA, r=55, ancho=4, relleno=(255, 200, 40, 255))
    ImageDraw.Draw(im).text((W / 2, cy), "Créalo en 1 minuto · llega a tu correo", font=F(42, "Bold"), fill=(25, 20, 50), anchor="mm")
    ImageDraw.Draw(im).text((W / 2, H - 60 * alto), "Mi Gran Aventura · libro de actividades personalizado · pixelia", font=F(26, "Medium"), fill=(200, 200, 230), anchor="mm")
    return im.convert("RGB")

if __name__ == "__main__":
    for k in DISEÑOS:
        pieza(k, 1080, 1350).save(OUT / f"{k}-4x5.jpg", quality=92); pieza(k, 1080, 1920).save(OUT / f"{k}-9x16.jpg", quality=92)
        print("ok", k)
