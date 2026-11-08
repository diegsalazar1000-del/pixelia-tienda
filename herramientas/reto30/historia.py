"""Historia 1080x1920 del Reto 30 Días (deja un hueco abajo para el sticker de enlace). Uso: python3 historia.py portada.jpg salida.jpg"""
import sys
from PIL import Image, ImageDraw, ImageFont
W, H = 1080, 1920; FD = "/usr/share/fonts/opentype/inter/"
F = lambda s, w="Bold": ImageFont.truetype(f"{FD}Inter-{w}.otf", s)
ORANGE, PINK, INK = (255, 107, 61), (255, 79, 163), (35, 26, 61)
img = Image.new("RGB", (W, H)); g = ImageDraw.Draw(img)
for y in range(0, H, 4):
    k = y / H; g.rectangle([0, y, W, y + 4], fill=(int(20 + 30 * k), int(14 + 6 * k), int(36 + 40 * k)))
c = lambda y, t, f, fill: g.text((W / 2, y), t, font=f, fill=fill, anchor="mm")
g.rounded_rectangle([340, 150, 740, 220], 35, fill=ORANGE); c(185, "REGALO GRATIS", F(38, "Black"), "white")
c(320, "¿Tus propósitos se", F(76, "Black"), "white"); c(410, "mueren en febrero?", F(76, "Black"), (255, 177, 153))
c(510, "Marca ✓ y tu racha se calcula sola", F(44, "Medium"), (220, 215, 240))
shot = Image.open(sys.argv[1]).convert("RGB"); sw = 860; shot = shot.resize((sw, int(shot.height * sw / shot.width)))
shot = shot.crop((0, 0, sw, min(shot.height, 700)))
fr = Image.new("RGB", (sw + 24, shot.height + 24), "white"); fr.paste(shot, (12, 12)); img.paste(fr, ((W - fr.width) // 2, 590))
y = 590 + fr.height + 70
c(y, "Google Sheets y Excel · también en el celular", F(36, "Medium"), (220, 215, 240))
c(y + 110, "Toca el enlace y descárgalo", F(50, "Bold"), "white"); c(y + 175, "↓", F(70, "Black"), ORANGE)
# abajo queda libre (~300 px) para poner el sticker de enlace
img.save(sys.argv[2], quality=90); print("ok")
