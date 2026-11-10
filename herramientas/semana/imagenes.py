"""Contenido de 2 semanas (10-22 nov): historias diarias (1080x1920) + publicaciones del feed (1080x1350), estilo Pixelia."""
import sys, json, random
sys.path.insert(0, "/home/claude/ig")
from PIL import Image, ImageDraw, ImageFilter
from logo import F, gradient, wordmark, VIOLET, PINK, CORAL, AMBER, CYAN, INK, CREAM, hexrgb
OUT = "/home/claude/ig/semana"; IMG = "/home/claude/tienda/public/img/"; REG = "/home/claude/tienda/public/regalos/"
JEFA = "#E8337A"; VINO = "#7A1846"

def wrap(d, t, f, mw):
    o, c = [], ""
    for w in t.split():
        n = (c + " " + w).strip()
        if d.textlength(n, font=f) <= mw or not c: c = n
        else: o.append(c); c = w
    return o + ([c] if c else [])
def text(im, t, xy, f, fill, mw=900, lh=1.15, center=False):
    d = ImageDraw.Draw(im); x, y = xy
    for l in wrap(d, t, f, mw):
        d.text((x, y), l, font=f, fill=fill, anchor="ma" if center else "la"); y += f.size * lh
    return y
def pill(t, f, bg, fg, pad=(36, 16)):
    tw = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(t, font=f)
    im = Image.new("RGBA", (int(tw + 2 * pad[0]), int(f.size * 1.3 + 2 * pad[1])), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=im.height // 2, fill=bg); d.text((pad[0], pad[1]), t, font=f, fill=fg); return im
def pixels(im, seed, cols=("#FFFFFF", AMBER), a=200):
    r = random.Random(seed); d = ImageDraw.Draw(im); W = im.width
    for k, (x, y, s) in enumerate([(W - 120, 50, 46), (W - 175, 120, 30), (W - 60, 270, 22), (W - 230, 55, 20)]):
        d.rounded_rectangle([x, y, x + s, y + s], radius=max(4, s // 4), fill=hexrgb(cols[(k + seed) % len(cols)]) + (a,))
def foto(path, w, rad=40):
    p = Image.open(path).convert("RGBA"); p = p.resize((w, round(p.height * w / p.width)), Image.LANCZOS)
    m = Image.new("L", p.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, p.width - 1, p.height - 1], radius=rad, fill=255); p.putalpha(m); return p
def pegar(im, lay, xy, sombra=True):
    if sombra:
        s = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh = Image.new("RGBA", lay.size, (0, 0, 0, 110)); sh.putalpha(lay.getchannel("A").point(lambda a: a * 110 // 255))
        s.alpha_composite(sh, (int(xy[0]), int(xy[1] + 28))); im.alpha_composite(s.filter(ImageFilter.GaussianBlur(30)))
    im.alpha_composite(lay, (int(xy[0]), int(xy[1])))
def pie(im, dark=False):
    W, H = im.size; c = INK if dark else "#FFFFFF"; d = ImageDraw.Draw(im)
    im.alpha_composite(wordmark(64, c), (70, H - 120)); d.text((W - 70, H - 82), "@pixelia.digitalstore", font=F("Medium", 30), fill=c, anchor="rm")

# ---------- HISTORIAS ----------
P = {
 "jefa": (IMG + "portada-la-jefa.jpg", (JEFA, VIOLET), "pixeliadigital.app/jefa", "PRUÉBALA GRATIS"),
 "habitos": (IMG + "portada-habitos-2027.jpg", (VIOLET, CYAN), "pixeliadigital.app/p/mi-2027-en-habitos", "TU 2027"),
 "panel": (IMG + "portada-panel-financiero.jpg", (CORAL, AMBER), "pixeliadigital.app/p/plantilla-excel-de-finanzas-personales", "EXCEL + GOOGLE SHEETS"),
 "loteria": (IMG + "portada-loteria-baby-shower.jpg", (PINK, AMBER), "pixeliadigital.app/p/loteria-de-baby-shower-imprimible-60-tablas-unicas", "BABY SHOWER"),
 "ahorro": (REG + "portada-reto-ahorro.jpg", ("#16A34A", CYAN), "pixeliadigital.app/regalo", "GRATIS"),
 "navidad": (REG + "portada-planificador-navideno.jpg", ("#DC2626", "#F59E0B"), "pixeliadigital.app/regalo", "GRATIS"),
 "reto30": (REG + "reto-30-dias.jpg", (VIOLET, PINK), "pixeliadigital.app/reto", "GRATIS"),
}
HIST = [
 ("2026-11-10", "jefa", "¿Vendes y vendes… y nunca te alcanza?", "Descubre en 1 minuto si estás perdiendo plata en cada venta."),
 ("2026-11-11", "habitos", "2027 no se va a cambiar solo.", "Tus hábitos de todo el año en una sola hoja, con tu progreso al día."),
 ("2026-11-12", "ahorro", "¿Y si en diciembre de 2027 tuvieras 1.378 guardados?", "Reto de ahorro de 52 semanas, en tu moneda. Gratis."),
 ("2026-11-13", "panel", "La quincena llega el viernes… y se va el sábado.", "Mira a dónde se va tu plata con tu Panel Financiero mensual."),
 ("2026-11-14", "loteria", "El baby shower del que toda la familia va a hablar.", "Lotería imprimible con 60 tablas únicas. Imprimes y a jugar."),
 ("2026-11-15", "navidad", "Diciembre llega rápido… y la plata se va más rápido.", "Planificador navideño gratis: regalos, cena y gastos en orden."),
 ("2026-11-16", "jefa", "“El viernes te pago, mija.” El viernes:", "Anota quién te debe y cóbrale por WhatsApp con un toque."),
 ("2026-11-17", "habitos", "Enero: “este año sí”. Marzo: “¿qué metas?”", "Mira tu año completo y no sueltes tus metas en 2027."),
 ("2026-11-18", "reto30", "30 días. Un hábito. Cero excusas.", "Reto de 30 días gratis: lo marcas cada día y ves tu avance."),
 ("2026-11-19", "panel", "“¿En qué se me fue la plata?” Te lo dice tu Excel.", "Ingresos, gastos y ahorro del mes, con gráficos solos."),
 ("2026-11-20", "jefa", "¿Cuánto cobrar por lo que haces?", "La Jefa te dice tu precio justo y te arma tu lista para WhatsApp."),
 ("2026-11-21", "loteria", "¿Te tocó organizar el baby shower?", "Ríete con la familia: 60 tablas distintas, lista para imprimir."),
 ("2026-11-22", "ahorro", "Ahorra sin sufrir: una semana a la vez.", "52 semanas, un poquito cada vez. Descárgalo gratis."),
]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
def historia(n, fecha, k, hook, sub):
    fp, (c1, c2), url, label = P[k]; W, H = 1080, 1920
    im = gradient(W, H, c1, c2).convert("RGBA"); pixels(im, n)
    im.alpha_composite(pill(label, F("Bold", 34), "#FFFFFF", hexrgb(c1)), (80, 150))
    y = text(im, hook, (80, 260), F("Bold", 92), "#FFFFFF", mw=800, lh=1.08)
    ph = foto(fp, 760); ph.thumbnail((760, 1560 - max(y, 560) - 60 - 230)); pegar(im, ph, ((W - ph.width) / 2, max(y, 560) + 40))
    yb = max(y, 560) + 40 + ph.height + 50
    text(im, sub, (W / 2, yb), F("Medium", 44), "#FFFFFF", mw=900, lh=1.25, center=True)
    # zona para el sticker de enlace (Diego lo pone en el teléfono) + la dirección por si acaso
    im.alpha_composite(pill("Toca el enlace de aquí abajo", F("Bold", 42), INK, "#FFFFFF"), (int(W / 2 - 310), 1560))
    ImageDraw.Draw(im).text((W / 2, 1860), "pixeliadigital.app", font=F("Medium", 28), fill="#FFFFFF", anchor="mm")
    im.convert("RGB").save(f"{OUT}/historia-{fecha}-{k}.jpg", quality=92)

# ---------- FEED ----------
def burbuja(im, x, y, t, mia, f):
    d = ImageDraw.Draw(im); ls = wrap(d, t, f, 600); w = max(d.textlength(l, font=f) for l in ls) + 60; h = len(ls) * f.size * 1.3 + 40
    x0 = 1080 - 90 - w if mia else x
    d.rounded_rectangle([x0, y, x0 + w, y + h], radius=34, fill=hexrgb("#DCF8C6") if mia else (255, 255, 255))
    for i, l in enumerate(ls): d.text((x0 + 30, y + 20 + i * f.size * 1.3), l, font=f, fill=INK)
    return y + h + 26
def feed():
    W, H = 1080, 1350; out = {}
    # 1 · martes 10: meme de chat
    im = Image.new("RGBA", (W, H), hexrgb(CREAM) + (255,)); pixels(im, 1, (PINK, VIOLET, AMBER), 255)
    text(im, "Toda emprendedora ha vivido esto:", (90, 110), F("Bold", 70), INK, mw=840, lh=1.1)
    d = ImageDraw.Draw(im); d.rounded_rectangle([70, 330, W - 70, 1080], radius=40, fill=hexrgb("#EFE7DE"))
    f = F("Medium", 40); y = burbuja(im, 110, 380, "Amiga, apártame 2 tortas. Ya te transfiero", False, f)
    y = burbuja(im, 0, y, "¡Listo, mi reina!", True, f)
    d.text((W / 2, y + 20), "— 3 días después —", font=F("Bold", 36), fill=hexrgb("#8A7F99"), anchor="ma"); y += 90
    y = burbuja(im, 0, y, "¿Y la transferencia?", True, f)
    d.text((W - 100, y - 10), "Visto", font=F("Medium", 30), fill=hexrgb("#8A7F99"), anchor="ra")
    im.alpha_composite(pill("Etiqueta a la que le ha pasado", F("Bold", 40), PINK, "#FFFFFF"), (90, 1120))
    pie(im, True); out["2026-11-10"] = im
    # 2 · jueves 12: 3 errores (para guardar)
    im = gradient(W, H, CORAL, AMBER).convert("RGBA"); pixels(im, 2, ("#FFFFFF",), 170)
    text(im, "3 errores que se comen tu ganancia", (90, 120), F("Bold", 80), "#FFFFFF", mw=860, lh=1.08)
    y = 500
    for i, (t, s) in enumerate([("No contar tu tiempo", "Tu hora también cuesta, aunque trabajes en casa."), ("Olvidar lo pequeño", "Empaque, gas, delivery, la bolsita… todo suma."), ("Copiar el precio de otra", "Sus gastos no son los tuyos.")]):
        d = ImageDraw.Draw(im); d.ellipse([90, y, 160, y + 70], fill="#FFFFFF"); d.text((125, y + 35), str(i + 1), font=F("Bold", 40), fill=hexrgb(CORAL), anchor="mm")
        d.text((190, y - 4), t, font=F("Bold", 48), fill="#FFFFFF"); yy = text(im, s, (190, y + 62), F("Medium", 36), "#FFFFFF", mw=800, lh=1.2); y = yy + 60
    im.alpha_composite(pill("Guárdalo para tu próximo precio", F("Bold", 40), "#FFFFFF", hexrgb(CORAL)), (90, 1090))
    pie(im); out["2026-11-12"] = im
    # 3 · lunes 16: valor (1% mejor)
    im = gradient(W, H, "#16A34A", CYAN).convert("RGBA"); pixels(im, 3)
    text(im, "No tienes que cambiar tu vida en un día", (90, 120), F("Bold", 76), "#FFFFFF", mw=800, lh=1.08)
    d = ImageDraw.Draw(im)
    for i, (n, t) in enumerate([("1%", "mejor cada día"), ("365", "días seguidos"), ("37 veces", "mejor al final del año")]):
        y = 520 + i * 170; d.rounded_rectangle([90, y, W - 90, y + 140], radius=36, fill=(255, 255, 255, 235))
        d.text((140, y + 70), n, font=F("Bold", 64), fill=hexrgb("#16A34A"), anchor="lm"); d.text((W - 140, y + 70), t, font=F("Medium", 40), fill=INK, anchor="rm")
    text(im, "Un poquito hoy, otro poquito mañana. Eso es todo.", (90, 1060), F("Medium", 44), "#FFFFFF", mw=880, lh=1.25)
    pie(im); out["2026-11-16"] = im
    # 4 · miércoles 18: ¿qué tipo de emprendedora eres?
    im = gradient(W, H, JEFA, VIOLET).convert("RGBA"); pixels(im, 4)
    text(im, "¿Qué tipo de emprendedora eres?", (90, 140), F("Bold", 84), "#FFFFFF", mw=880, lh=1.08)
    y = 520
    for i, op in enumerate(["La del cuaderno lleno de tachones", "La que lo lleva todo “en la memoria”", "La que ya no pierde ni un cobro"]):
        p = pill(f"{'ABC'[i]}   {op}", F("Bold", 40), "#FFFFFF", hexrgb(VINO), (40, 22)); im.alpha_composite(p, (90, y)); y += 150
    text(im, "Dinos tu letra en los comentarios", (90, y + 30), F("Medium", 44), "#FFFFFF")
    pie(im); out["2026-11-18"] = im
    # 5 · viernes 20: valor (señales de progreso, para compartir)
    im = Image.new("RGBA", (W, H), hexrgb(CREAM) + (255,)); pixels(im, 5, (VIOLET, PINK, AMBER), 255)
    text(im, "5 señales de que vas avanzando (aunque no lo notes)", (90, 100), F("Bold", 70), INK, mw=800, lh=1.08)
    y = 440
    for t in ["Ya no te rindes al primer “no”", "Te levantas aunque no tengas ganas", "Cuidas tu plata un poquito más", "Celebras lo pequeño", "Compites solo contigo"]:
        d = ImageDraw.Draw(im); d.ellipse([90, y, 150, y + 60], fill=hexrgb(VIOLET)); d.line([(106, y + 31), (116, y + 42), (135, y + 19)], fill="#FFFFFF", width=7)
        d.text((180, y + 30), t, font=F("Medium", 42), fill=INK, anchor="lm"); y += 110
    im.alpha_composite(pill("Compártelo con quien lo necesita", F("Bold", 40), PINK, "#FFFFFF"), (90, 1080))
    pie(im, True); out["2026-11-20"] = im
    for k, v in out.items(): v.convert("RGB").save(f"{OUT}/feed-{k}.jpg", quality=93)

for n, h in enumerate(HIST): historia(n, *h)
feed()
