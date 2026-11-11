"""📚 MI GRAN AVENTURA — libro de actividades personalizado (2-8 años), uno por pedido, sin IA y sin créditos.
Las páginas de actividades salen del PLR "Kids Book Creator Bundle" ya traducidas (paginas/*.png + paginas.json, ver preparar.py
en la sesión); aquí se arma la historia con el nombre, la edad, el compañero y la persona especial, y cada misión lleva un QR
que abre /v/<pedido>/<n> con una voz que dice su nombre (las voces las graba el estudio con Piper, gratis).
  python3 build.py prueba.json /tmp/salida      (datos de ejemplo abajo si no se pasa JSON)"""
import sys, json, math, random, pathlib, unicodedata, re
from PIL import Image, ImageDraw, ImageFont
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import qrencoder as qe

FD = next((p for p in [HERE.parent.parent / "estudio" / "fonts", pathlib.Path("/pixelia/estudio/fonts")] if (p / "Poppins-Bold.ttf").exists()), None)
EMO = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
DPI = 150; S = DPI / 72; W, H = int(612 * S), int(792 * S)
INK, ROSA, VIOLETA, AMBAR, CIELO, VERDE, CREMA = (35, 26, 61), (255, 79, 163), (124, 92, 255), (255, 183, 3), (56, 189, 248), (34, 197, 94), (255, 247, 230)
def F(s, w="Bold"): return ImageFont.truetype(str(FD / f"Poppins-{w}.ttf"), int(s))
META = json.loads((HERE / "paginas" / "paginas.json").read_text())

COMP = {"perrito": ("🐶", "Coco", "su perrito"), "gatito": ("🐱", "Michi", "su gatito"), "dinosaurio": ("🦖", "Rex", "su dinosaurio"),
        "unicornio": ("🦄", "Luna", "su unicornio"), "dragon": ("🐉", "Chispa", "su dragón"), "robot": ("🤖", "Robi", "su robot"),
        "loro": ("🦜", "Paco", "su loro"), "amigo": ("🧒", "Leo", "su amigo")}
# "Otro": lo que escriba el papá (un conejito, su hermana, la abuela…) → dibujo que corresponda, o ⭐
EMO_OTRO = {"loro": "🦜", "perico": "🦜", "guacamaya": "🦜", "conej": "🐰", "tortuga": "🐢", "hamster": "🐹", "hámster": "🐹", "pez": "🐠", "pececito": "🐠",
    "caballo": "🐴", "poni": "🐴", "oso": "🐻", "pollito": "🐥", "pato": "🦆", "leon": "🦁", "león": "🦁", "tigre": "🐯", "mono": "🐵", "panda": "🐼", "zorro": "🦊",
    "vaca": "🐮", "cerdito": "🐷", "cochinito": "🐷", "rana": "🐸", "pinguino": "🐧", "pingüino": "🐧", "buho": "🦉", "búho": "🦉", "mariposa": "🦋", "abeja": "🐝",
    "ballena": "🐳", "delfin": "🐬", "delfín": "🐬", "tiburon": "🦈", "tiburón": "🦈", "gat": "🐱", "perr": "🐶", "amig": "🧒", "herman": "🧒", "prim": "🧒",
    "abuela": "👵", "abuelo": "👴", "hada": "🧚", "sirena": "🧜", "superh": "🦸", "extraterrestre": "👽", "marciano": "👽", "dinosaurio": "🦖"}
def comp_otro(txt):
    t = re.sub(r"^(un|una|el|la|su|mi)\s+", "", (txt or "").strip().lower())[:20]
    emo = next((e for k, e in EMO_OTRO.items() if any(w.startswith(k) for w in t.split())), "⭐")
    return emo, ("su " + t) if t else "su compañero"

def ctx(d):
    nina = d.get("genero") != "nino"
    tipo = d.get("comp_tipo") if d.get("comp_tipo") in COMP or d.get("comp_tipo") == "otro" else "perrito"
    cn = (d.get("comp_nombre") or "").strip()[:16]
    if tipo == "otro":
        emo, Csu = comp_otro(d.get("comp_otro"))
        C = cn or Csu[3:].capitalize()   # sin nombre: "Sofía y Conejito…"
    else:
        emo, C, Csu = COMP[tipo][0], cn or COMP[tipo][1], COMP[tipo][2]
    esp = (d.get("especial") or "").strip() or "el búho sabio del bosque"
    nom = (d.get("nombre") or "").strip()[:20] or "Sofía"
    return {"N": nom, "NU": nom.upper(), "E": str(d.get("edad") or 5), "C": C, "Cemo": emo, "Csu": Csu,
            "P": esp[:30], "Pm": esp[:1].upper() + esp[1:30], "L": inicial(nom),
            "heroe": "heroína" if nina else "héroe", "una": "una" if nina else "un", "listo": "lista" if nina else "listo",
            "solito": "solita" if nina else "solito", "nino": "niña" if nina else "niño", "Hemo": "👧" if nina else "👦",
            "campeon": "campeona" if nina else "campeón", "explorador": "exploradora" if nina else "explorador"}
def inicial(n):
    n = n.strip().upper()
    if n[:2] == "LL": return "LL"
    c = n[:1]; return c if c == "Ñ" else (unicodedata.normalize("NFKD", c).encode("ascii", "ignore").decode() or "A")
def fmt(t, c): return t.format(**c)

# ---------- misiones (actividad, título, historia, frase de la voz) ----------
VOZ_OK = "¡Muy bien, {N}! "
A = [  # 2 a 4 años (cortas: se las lee mamá o papá)
 ("trazo1", "¡Empieza la aventura!", "{N} y {C} salen de casa. ¡El camino está lleno de curvas! Repasa las líneas con tu dedo o tu lápiz para abrir el camino.", "¡Muy bien, {N}! Abriste el camino de la aventura."),
 ("lab_sol", "¿Dónde está el sol?", "Unas nubes traviesas escondieron al sol y todo está oscuro. Ayúdalo a salir para que vuelva a brillar.", "¡Bravo, {N}! Gracias a ti el sol brilla otra vez."),
 ("perro_trazo", "Un amigo nuevo", "En el parque, {C} conoce a un perrito muy tímido. Repasa su figura y coloréalo de tu color favorito.", "¡Qué bonito te quedó, {N}! El perrito ya es tu amigo."),
 ("sombras1", "Sombras misteriosas", "En el bosque aparecen sombras raras. ¿Serán monstruos? ¡No! Son amigos escondidos. Une cada dibujo con su sombra.", "¡Qué valiente eres, {N}! Encontraste a todos los amigos."),
 ("circulo", "Las burbujas mágicas", "{C} sopla burbujas mágicas. Píntalas una por una con tu dedo o con un marcador.", "¡Wow, {N}! Pintaste todas las burbujas mágicas."),
 ("tijera", "El puente de papel", "Para cruzar el río hay que hacer un puente. Con ayuda de un adulto, recorta por las líneas.", "¡Lo lograste, {N}! Ya pueden cruzar el río."),
 ("lab_casa", "¡Un perrito perdido!", "Al otro lado del río, un perrito llora porque no encuentra su casa. {N}, ¡tú conoces el camino! Llévalo de regreso.", "¡Eres {una} {heroe}, {N}! El perrito ya está en casa."),
 ("granja", "La granja", "{N} y {C} llegan a una granja. La gallina y el poni quieren que los colorees.", "¡Muy bien, {N}! La gallina y el poni te dan las gracias."),
 ("perro_puntos", "Las manchas del perrito", "El perrito de la granja perdió sus manchas. Pínta cada círculo con tu dedo para devolvérselas.", "¡Qué lindo, {N}! El perrito tiene sus manchas otra vez."),
 ("diferencias1", "El reto de {C}", "{C} dice: ¡te reto! Encuentra 4 cosas diferentes entre los dos dibujos.", "¡Las encontraste, {N}! {C} está muy feliz."),
 ("mar1", "¡A la playa!", "Llegan al mar y saltan los delfines. Repasa y colorea a los animales del mar.", "¡Muy bien, {N}! Los delfines te saludan."),
 ("trazo2", "Camino a casa de {P}", "Ya es hora de visitar a {P}. Repasa las líneas para llegar.", "¡Llegaste, {N}! {Pm} te espera con un abrazo gigante."),
]
B = [  # 4 a 6 años
 ("letra_{L}", "La llave mágica", "Para empezar la aventura, {N} necesita una llave mágica: ¡la letra {L}, la primera de su nombre! Repásala con mucho cuidado.", "¡Muy bien, {N}! La letra {L} abrió la puerta de la aventura."),
 ("entre", "El puente de números", "Al puente le faltan tablas. Escribe el número que va en el medio para que {N} y {C} puedan cruzar.", "¡Bravo, {N}! El puente quedó listo."),
 ("sombras2", "Sombras misteriosas", "En el bosque aparecen sombras raras. ¿Serán monstruos? ¡No! Son amigos escondidos. Une cada dibujo con su sombra.", "¡Qué valiente eres, {N}! Encontraste a todos los amigos."),
 ("lab_casa", "¡Un perrito perdido!", "Un perrito llora porque no encuentra su casa. {N}, ¡tú conoces el camino! Sigue el laberinto con tu lápiz y llévalo de regreso.", "¡Eres {una} {heroe}, {N}! El perrito ya está en casa."),
 ("figuras", "La casa del duende", "Un duende construye su casa con figuras. Repasa, colorea y dibuja el cuadrado para ayudarlo.", "¡Gracias, {N}! El duende ya tiene casa."),
 ("puntos1", "El animal escondido", "Algo se esconde entre los puntos… Únelos del 1 en adelante y descubre quién es.", "¡Lo descubriste, {N}! Qué ojos de {explorador} tienes."),
 ("granja", "La granja", "{N} y {C} llegan a una granja. Repasa los nombres de la gallina y el poni, y coloréalos.", "¡Muy bien, {N}! La granja está feliz."),
 ("secuencia", "Los números perdidos", "Un viento travieso se llevó algunos números. Escríbelos en su lugar.", "¡Excelente, {N}! Todos los números volvieron a casa."),
 ("diferencias2", "El reto de {C}", "{C} dice: ¡te reto! Encuentra 4 cosas diferentes entre los dos dibujos.", "¡Las encontraste, {N}! {C} está muy feliz."),
 ("lab_cometa", "¡La cometa enredada!", "La cometa de {C} se enredó en el cielo. Sigue el camino para rescatarla.", "¡Rescataste la cometa, {N}! {C} salta de alegría."),
 ("mar2", "En el fondo del mar", "{N} y {C} bajan al fondo del mar. Repasa y colorea a la ballena y a la medusa.", "¡Muy bien, {N}! Eres {una} {explorador} del mar."),
 ("cantidad", "La fiesta de {P}", "{Pm} preparó una fiesta sorpresa. Cuenta cada grupo y únelo con su número.", "¡Contaste muy bien, {N}! Que empiece la fiesta."),
]
C = [  # 6 a 8 años
 ("sopa", "Los nombres escondidos", "Un mago escondió las palabras de la aventura en esta sopa de letras. ¡Encuéntralas todas y enciérralas!", "¡Bien hecho, {N}! Rompiste el hechizo del mago."),
 ("lab_explorador", "El gran laberinto", "Para llegar al castillo, {N} tiene que cruzar un laberinto enorme. ¡No te pierdas!", "¡Lo cruzaste, {N}! El castillo está cerca."),
 ("suma_colorea", "Las estrellas del camino", "Las estrellas solo se encienden si sumas bien. Suma y colorea las que dice cada caja.", "¡Muy bien, {N}! Encendiste las estrellas."),
 ("sudoku", "El candado mágico", "La puerta del castillo tiene un candado. En cada fila y cada columna van los números 1, 2, 3 y 4 sin repetir.", "¡Abriste el candado, {N}! Qué mente tan brillante."),
 ("puntos3", "El dibujo secreto", "Une los puntos para descubrir el dibujo secreto. Después coloréalo y dibújalo tú.", "¡Lo descubriste, {N}! Eres {una} gran artista."),
 ("decenas", "El tesoro del pirata", "Un pirata guardó sus monedas en barras de 10. Cuéntalas y colorea la respuesta correcta.", "¡Encontraste el tesoro, {N}! Eres {una} {campeon}."),
 ("lab_jardin", "El jardín encantado", "El jardín del castillo está encantado. Encuentra el camino entre las flores.", "¡Saliste del jardín, {N}! Qué {explorador}."),
 ("diferencias3", "El reto de {C}", "{C} dice: ¡te reto! Encuentra 4 cosas diferentes entre los dos dibujos.", "¡Las encontraste, {N}! {C} está muy feliz."),
 ("hora", "El reloj del castillo", "El reloj del castillo se volvió loco. Escribe cada hora con palabras para arreglarlo.", "¡Arreglaste el reloj, {N}! Ya es hora de seguir."),
 ("selva", "La selva", "{N} y {C} llegan a la selva. Repasa los nombres del elefante y el leopardo, y coloréalos.", "¡Muy bien, {N}! Los animales de la selva te saludan."),
 ("cuenta100", "La escalera de 100", "Para subir a la torre hay una escalera de 100 escalones, pero faltan algunos números. ¡Complétalos!", "¡Llegaste a la cima, {N}! Qué {listo} eres."),
 ("espacio", "¡Viaje al espacio!", "Desde la torre, {N} y {C} despegan en un cohete. Colorea el espacio antes de volver a casa de {P}.", "¡Volviste del espacio, {N}! {Pm} está muy {orgullo} de ti."),
]
MOMENTOS = {"A": ["espacio", "planeta"], "B": ["espacio", "planeta"], "C": ["planeta", "granja"]}
nivel = lambda e: "A" if e <= 3 else ("B" if e <= 5 else "C")

# ---------- dibujo ----------
def emoji(ch, size):
    f = ImageFont.truetype(EMO, 109); im = Image.new("RGBA", (200, 180), (0, 0, 0, 0)); ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox()); return im.resize((size, round(im.height * size / im.width)), Image.LANCZOS)
def pegar(im, ch, x, y, s): e = emoji(ch, s); im.paste(e, (int(x - e.width / 2), int(y - e.height / 2)), e)
def wrap(d, t, f, mw):
    o, c = [], ""
    for w in t.split():
        n = (c + " " + w).strip()
        if d.textlength(n, font=f) <= mw or not c: c = n
        else: o.append(c); c = w
    return o + [c]
def encajar(d, t, mw, s, minimo=14):
    while s > minimo and d.textlength(t, font=F(s)) > mw: s -= 2
    return F(s)
def estrella(d, cx, cy, r, col, borde=None):
    pts = [(cx + (r if k % 2 == 0 else r * .45) * math.sin(k * math.pi / 5), cy - (r if k % 2 == 0 else r * .45) * math.cos(k * math.pi / 5)) for k in range(10)]
    d.polygon(pts, fill=col, outline=borde)
    if borde: d.line(pts + [pts[0]], fill=borde, width=4)
def qr(url, size):
    for v in range(3, 10):
        try: q = qe.QRCode(v, qe.QRErrorCorrectLevel.M); q.addData(url); q.make(); break
        except Exception: continue
    n = q.getModuleCount(); m = size / (n + 4); im = Image.new("RGB", (size, size), "white"); d = ImageDraw.Draw(im)
    for r in range(n):
        for k in range(n):
            if q.isDark(r, k): d.rectangle([(k + 2) * m, (r + 2) * m, (k + 3) * m - .5, (r + 3) * m - .5], fill=INK)
    return im
def pie(d, n, c):
    d.text((W / 2, H - 70), f"La gran aventura de {c['N']}  ·  {n}", font=F(22, "Medium"), fill=VIOLETA, anchor="mm")
def lienzo(): return Image.new("RGB", (W, H), "white")

def actividad(k, c):
    im = Image.open(HERE / "paginas" / f"{k}.png").convert("RGB"); d = ImageDraw.Draw(im)
    for t in META.get(k, []):
        x0, y0, x1, y1 = t["box"]; txt = fmt(t["t"], c); f = encajar(d, txt, (x1 - x0) + 40, (y1 - y0) * 0.95)
        if t["contorno"]: d.text(((x0 + x1) / 2, (y0 + y1) / 2), txt, font=f, fill="white", anchor="mm", stroke_width=max(2, f.size // 22), stroke_fill=(150, 150, 150))
        else: d.text(((x0 + x1) / 2, (y0 + y1) / 2), txt, font=f, fill=INK, anchor="mm")
    return im
def sopa(c):
    quitar = lambda s: "".join(ch for ch in unicodedata.normalize("NFKD", s.upper()) if ch.isalpha() and not unicodedata.combining(ch)).replace("Ñ", "Ñ")
    pal = []
    for w in [c["N"], c["C"], c["P"].split()[-1], "AVENTURA", "TESORO", "ESTRELLA", "MAPA", "AMIGO"]:
        w = quitar(unicodedata.normalize("NFC", w))[:10]
        if 3 <= len(w) and w not in pal: pal.append(w)
    pal = pal[:8]; n = 11; g = [[""] * n for _ in range(n)]; rnd = random.Random(c["N"])
    for w in sorted(pal, key=len, reverse=True):
        for _ in range(400):
            dx, dy = rnd.choice([(1, 0), (0, 1), (1, 1)]); x, y = rnd.randrange(n - dx * (len(w) - 1)), rnd.randrange(n - dy * (len(w) - 1))
            if all(g[y + dy * i][x + dx * i] in ("", w[i]) for i in range(len(w))):
                for i in range(len(w)): g[y + dy * i][x + dx * i] = w[i]
                break
    for r in g:
        for i in range(n): r[i] = r[i] or rnd.choice("ABCDEFGHIJLMNOPRSTUVZ")
    im = lienzo(); d = ImageDraw.Draw(im); top = 90; cel = 84; x0 = (W - n * cel) / 2
    d.rounded_rectangle([x0 - 20, top - 20, x0 + n * cel + 20, top + n * cel + 20], radius=30, outline=INK, width=4)
    for r in range(n):
        for k in range(n): d.text((x0 + k * cel + cel / 2, top + r * cel + cel / 2), g[r][k], font=F(46), fill=INK, anchor="mm")
    y = top + n * cel + 70; d.text((W / 2, y), "Encuentra estas palabras:", font=F(38), fill=VIOLETA, anchor="mm"); y += 50
    for i, w in enumerate(pal): d.text((W / 2 + (-220 if i % 2 == 0 else 220), y + 20 + (i // 2) * 60), w, font=F(40), fill=INK, anchor="mm")
    return im

def mision(n, m, c, url, col):
    k, titulo, hist, _ = m
    act = sopa(c) if k == "sopa" else actividad(fmt(k, c), c)
    act = act.crop((0, int(12 * S), W, int(712 * S))); act.thumbnail((int(W * .82), H - 300 - 360))
    im = lienzo(); d = ImageDraw.Draw(im)
    d.rounded_rectangle([60, 40, W - 60, 290], radius=36, fill=CREMA, outline=col, width=5)
    d.text((100, 72), fmt(f"Misión {n}: {titulo}", c), font=encajar(d, fmt(f"Misión {n}: {titulo}", c), W - 330, 40), fill=col)
    y = 132
    for l in wrap(d, fmt(hist, c), F(30, "Medium"), W - 220)[:4]: d.text((100, y), l, font=F(30, "Medium"), fill=INK); y += 40
    pegar(im, c["Cemo"], W - 130, 95, 90)
    im.paste(act, ((W - act.width) // 2, 305))
    y = H - 345; d.rounded_rectangle([60, y, W - 60, y + 230], radius=36, fill=(240, 236, 255))
    im.paste(qr(url, 190), (95, y + 20))
    d.text((310, y + 40), "¿Terminaste la misión?", font=F(34), fill=VIOLETA)
    for i, l in enumerate(wrap(d, f"Pídele a un adulto que escanee el código con la cámara: ¡alguien tiene un mensaje para {c['N']}!", F(26, "Medium"), W - 520)):
        d.text((310, y + 92 + i * 36), l, font=F(26, "Medium"), fill=INK)
    estrella(d, W - 130, y + 110, 62, "white", INK); d.text((W - 130, y + 200), "¡Coloréala!", font=F(20), fill=INK, anchor="mm")
    pie(d, n + 4, c); return im

def portada(c):
    im = lienzo(); d = ImageDraw.Draw(im)
    for y in range(H): t = y / H; d.line([0, y, W, y], fill=(int(186 + 60 * t), int(230 + 15 * t), int(255 - 40 * t)))
    d.ellipse([-200, H - 520, W + 200, H + 300], fill=(134, 211, 120)); d.ellipse([-300, H - 380, W / 2 + 200, H + 300], fill=(104, 190, 96))
    pegar(im, "☀️", W - 190, 190, 200)
    for x, y, s in [(170, 230, 150), (W / 2 + 40, 160, 110)]: pegar(im, "☁️", x, y, s)
    for x, y, s in [(130, H - 560, 230), (W - 150, H - 600, 260), (330, H - 470, 160)]: pegar(im, "🌳", x, y, s)
    d.rounded_rectangle([80, 330, W - 80, 760], radius=50, fill="white")
    d.text((W / 2, 420), "La gran aventura de", font=F(54), fill=INK, anchor="mm")
    d.text((W / 2, 555), c["N"], font=encajar(d, c["N"], W - 240, 170), fill=ROSA, anchor="mm", stroke_width=5, stroke_fill=INK)
    sub = f"y {c['Csu']}" + ("" if c["C"].lower() == c["Csu"][3:].lower() else f" {c['C']}"); d.text((W / 2, 690), sub, font=encajar(d, sub, W - 220, 52), fill=VIOLETA, anchor="mm")
    pegar(im, c["Hemo"], W / 2 - 150, H - 330, 280); pegar(im, c["Cemo"], W / 2 + 170, H - 290, 220)
    for x, y in [(240, 870), (W - 260, 900), (W / 2, 840)]: estrella(d, x, y, 34, AMBAR)
    t = f"12 misiones para {c['una']} {c['heroe']} de {c['E']} años"
    d.rounded_rectangle([W / 2 - 330, H - 140, W / 2 + 330, H - 60], radius=40, fill=INK)
    d.text((W / 2, H - 100), t, font=encajar(d, t, 620, 30), fill="white", anchor="mm")
    return im
def presentacion(c):
    im = lienzo(); d = ImageDraw.Draw(im)
    d.text((W / 2, 110), f"¡Hola, {c['N']}!", font=F(64), fill=ROSA, anchor="mm")
    d.text((W / 2, 185), "Esta aventura es tuya. Dibújate aquí o pega tu foto:", font=F(30, "Medium"), fill=INK, anchor="mm")
    d.rounded_rectangle([170, 250, W - 170, 800], radius=40, outline=VIOLETA, width=8)
    for x, y in [(170, 250), (W - 170, 250), (170, 800), (W - 170, 800)]: estrella(d, x, y, 40, AMBAR)
    y = 880
    for et, v in [("Me llamo", c["N"]), ("Tengo", f"{c['E']} años"), ("Mi compañero de aventura", f"{c['C']} {c['Cemo']}" if False else c["C"]), ("Alguien que quiero mucho", c["Pm"])]:
        d.text((150, y), et + ":", font=F(32, "Medium"), fill=INK); d.text((W - 150, y), v, font=encajar(d, v, 520, 38), fill=VIOLETA, anchor="ra"); y += 72
    pegar(im, c["Cemo"], W / 2, H - 230, 150); pie(d, 2, c); return im
def traza_nombre(c):
    im = lienzo(); d = ImageDraw.Draw(im)
    d.text((W / 2, 110), "Primero, firma como explorador", font=F(46), fill=INK, anchor="mm")
    d.text((W / 2, 180), "Repasa tu nombre con tu lápiz", font=F(34, "Medium"), fill=VIOLETA, anchor="mm")
    y = 270
    for k in range(5):
        d.line([90, y + 150, W - 90, y + 150], fill=(60, 60, 60), width=3); d.line([90, y + 30, W - 90, y + 30], fill=(200, 200, 200), width=2); d.line([90, y + 90, W - 90, y + 90], fill=(215, 215, 215), width=2)
        if k < 4: d.text((W / 2, y + 150), c["N"], font=encajar(d, c["N"], W - 200, 150), fill="white", anchor="ms", stroke_width=3, stroke_fill=(140, 140, 140))
        else: d.text((110, y + 10), f"Ahora escríbelo tú {c['solito']}:", font=F(26, "Medium"), fill=VIOLETA)
        y += 210
    pie(d, 3, c); return im
def mapa(c, titulos):
    im = lienzo(); d = ImageDraw.Draw(im)
    d.text((W / 2, 100), "El mapa de la aventura", font=F(56), fill=INK, anchor="mm")
    d.text((W / 2, 170), "Colorea cada estrella cuando termines una misión", font=F(28, "Medium"), fill=VIOLETA, anchor="mm")
    pts = []
    for i in range(12):
        fila, col = divmod(i, 3); col = col if fila % 2 == 0 else 2 - col
        pts.append((200 + col * 330, 330 + fila * 270))
    for a, b in zip(pts, pts[1:]):
        for t in range(0, 101, 6): x = a[0] + (b[0] - a[0]) * t / 100; y = a[1] + (b[1] - a[1]) * t / 100; d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(200, 190, 230))
    for i, (x, y) in enumerate(pts):
        estrella(d, x, y, 70, "white", INK); d.text((x, y + 6), str(i + 1), font=F(36), fill=INK, anchor="mm")
        t = fmt(titulos[i], c); d.text((x, y + 95), t, font=encajar(d, t, 300, 24, 16), fill=INK, anchor="mm")
    pegar(im, c["Hemo"], 120, 230, 90); pegar(im, "🏠", W - 120, H - 190, 110); pie(d, 4, c); return im
def momento(k, txt, n, c):
    act = actividad(k, c).crop((0, int(12 * S), W, int(712 * S))); act.thumbnail((int(W * .9), H - 330))
    im = lienzo(); d = ImageDraw.Draw(im); d.text((W / 2, 90), fmt(txt, c), font=encajar(d, fmt(txt, c), W - 120, 44), fill=ROSA, anchor="mm")
    im.paste(act, ((W - act.width) // 2, 160)); pie(d, n, c); return im
def diploma(c, url):
    im = lienzo(); d = ImageDraw.Draw(im)
    d.rounded_rectangle([50, 50, W - 50, H - 50], radius=40, outline=AMBAR, width=14); d.rounded_rectangle([80, 80, W - 80, H - 80], radius=30, outline=VIOLETA, width=4)
    estrella(d, W / 2, 250, 110, AMBAR)
    d.text((W / 2, 440), "DIPLOMA", font=F(96), fill=VIOLETA, anchor="mm")
    d.text((W / 2, 540), f"de {c['heroe']} de la aventura para", font=F(38, "Medium"), fill=INK, anchor="mm")
    d.text((W / 2, 670), c["N"], font=encajar(d, c["N"], W - 260, 160), fill=ROSA, anchor="mm")
    for i, t in enumerate([f"por completar las 12 misiones junto a {c['C']}", "con mucho esfuerzo, valentía y alegría."]): d.text((W / 2, 800 + i * 56), t, font=encajar(d, t, W - 220, 34), fill=INK, anchor="mm")
    im.paste(qr(url, 200), (int(W / 2 - 100), 930)); d.text((W / 2, 1150), "Escanea: ¡hay un mensaje final!", font=F(26), fill=VIOLETA, anchor="mm")
    d.line([W / 2 - 260, 1290, W / 2 + 260, 1290], fill=INK, width=3); d.text((W / 2, 1325), "Firma de mamá o papá", font=F(26, "Medium"), fill=INK, anchor="mm")
    return im

def generar(datos, out_dir):
    c = ctx(datos); c["orgullo"] = "orgullosa" if c["P"].split()[0].lower() in ("la", "mi") and not c["P"].lower().startswith("mi papá") else "orgulloso"
    e = max(2, min(8, int(datos.get("edad") or 5))); lv = nivel(e); M = {"A": A, "B": B, "C": C}[lv]
    base = datos.get("qr_base") or "https://pixeliadigital.app/v/demo"
    col = [ROSA, VERDE, VIOLETA, CIELO]
    pags = [portada(c), presentacion(c), traza_nombre(c), mapa(c, [m[1] for m in M])]
    for i, m in enumerate(M): pags.append(mision(i + 1, m, c, f"{base}/{i + 1}", col[i % 4]))
    for j, k in enumerate(MOMENTOS[lv]): pags.append(momento(k, ["{N} y {C} viajan al espacio. ¡Colorea este momento!", "¡Descubrieron un planeta nuevo! Ponle un nombre:"][j] if lv != "C" or j == 0 else "Un día en la granja con {C}. ¡Colorea este momento!", len(pags) + 1, c))
    pags.append(diploma(c, f"{base}/13"))
    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    pdf = out / "libro.pdf"; pags[0].save(pdf, save_all=True, append_images=pags[1:], resolution=DPI, quality=85)
    voces = [fmt(m[3], c) for m in M] + [fmt(f"¡Felicidades, {{N}}! Completaste las doce misiones con {{C}}. Eres {{una}} {{heroe}} de verdad. {c['Pm']} y todos en casa están muy {c['orgullo']}s de ti.".replace("{c['Pm']}", c["Pm"]), c)]
    titulos = [fmt(m[1], c) for m in M] + ["¡Aventura completada!"]
    (out / "voces.json").write_text(json.dumps({"nombre": c["N"], "genero": datos.get("genero"), "voces": voces, "titulos": titulos, "emoji": c["Cemo"]}, ensure_ascii=False))
    return {"pdf": str(pdf), "paginas": len(pags), "nivel": lv, "voces": voces}

if __name__ == "__main__":
    d = json.loads(pathlib.Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 and sys.argv[1].endswith(".json") else {"nombre": "Sofía", "edad": 5, "genero": "nina", "comp_tipo": "perrito", "comp_nombre": "Coco", "especial": "la abuela Rosa"}
    print(json.dumps(generar(d, sys.argv[2] if len(sys.argv) > 2 else "/tmp/aventura"), ensure_ascii=False, indent=1))
