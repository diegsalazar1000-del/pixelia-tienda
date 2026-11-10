"""Prepara las páginas del PLR para "Mi Gran Aventura": rasteriza, borra el texto en inglés y guarda dónde va el español.
Salida: /home/claude/tienda/herramientas/aventura/paginas/<id>.png + paginas.json  (el generador escribe el texto al vuelo,
así puede personalizar títulos con el nombre del niño o su compañero)."""
import re, json, subprocess, tempfile, pathlib
from PIL import Image, ImageDraw
SRC = pathlib.Path("/home/claude/plrkids/zip/x/pdfs/PDFS")
OUT = pathlib.Path("/home/claude/tienda/herramientas/aventura/paginas"); OUT.mkdir(parents=True, exist_ok=True)
DPI = 150; S = DPI / 72

T = {"TRACE IT": "REPASA", "COLOR IT": "COLOREA", "DRAW IT": "DIBÚJALO"}
P = {   # id: (pdf, página, {texto en inglés: plantilla en español}, títulos en contorno)
 "trazo1": ("Pencil Control level 1.pdf", 6, {"TRACE THE DOTTED LINES": "REPASA LAS LÍNEAS PUNTEADAS"}),
 "trazo2": ("Pencil Control level 1.pdf", 12, {"TRACE THE DOTTED LINES": "REPASA LAS LÍNEAS PUNTEADAS"}),
 "perro_trazo": ("Pencil Control level 2 (1).pdf", 3, {"TRACE AND COLOR THE DOTTED SHAPE": "REPASA Y COLOREA LA FIGURA"}),
 "lab_casa": ("Mazes (Level 1 - Ages 2-5).pdf", 3, {"HELP THE PUPPY GET HOME": "LLEVA AL PERRITO A CASA"}),
 "lab_sol": ("Mazes (Level 1 - Ages 2-5).pdf", 8, {"FIND THE SUN IN THE CLOUDS": "AYUDA AL SOL A SALIR DE LAS NUBES"}),
 "lab_cometa": ("Mazes (Level 1 - Ages 2-5).pdf", 12, {"SAVE THE KITE": "¡RESCATA LA COMETA!"}),
 "lab_explorador": ("Mazes (Level 2 Medium - Ages 6-7).pdf", 3, {"HELP THE EXPLORER": "AYUDA A {NU} A CRUZAR"}),
 "lab_jardin": ("Mazes (Level 2 Medium - Ages 6-7).pdf", 9, {"NAVIGATE THE GARDEN OF FLOWERS": "CRUZA EL JARDÍN DE FLORES"}),
 "tijera": ("scissor practice level 1.pdf", 9, {}),
 "circulo": ("_shapes Dot marker coloring.pdf", 3, {"Circle": "Círculo"}, ("Circle",)),
 "perro_puntos": ("Animals dot markers coloring.pdf", 3, {"Dog": "Perro"}, ("Dog",)),
 "sombras1": ("shadow matching workbook.pdf", 3, {"MATCH EACH PICTURE TO ITS SHADOW!": "UNE CADA DIBUJO CON SU SOMBRA"}),
 "sombras2": ("shadow matching workbook.pdf", 6, {"MATCH EACH PICTURE TO ITS SHADOW!": "UNE CADA DIBUJO CON SU SOMBRA"}),
 "entre": ("Math Activities Level 1.pdf", 3, {"FILL IN THE NUMBER THAT COMES BETWEEN": "¿QUÉ NÚMERO VA EN EL MEDIO?"}),
 "secuencia": ("Math Activities Level 1.pdf", 8, {"FILL IN THE MISSING NUMBER IN THE SEQUENCE": "COMPLETA LOS NÚMEROS QUE FALTAN"}),
 "cantidad": ("Math Activities Level 1.pdf", 14, {"MATCH THE SAME NUMBER/AMOUNT": "UNE CADA GRUPO CON SU NÚMERO"}),
 "cuenta100": ("Math Activities Level 2.pdf", 3, {"COUNTING 1 TO 100": "CUENTA DEL 1 AL 100", "Fill in the missing numbers": "Escribe los números que faltan"}),
 "suma_colorea": ("Math Activities Level 2.pdf", 10, {"ADD AND COLOR": "SUMA Y COLOREA", "COLOR 2 + 2 STARS": "COLOREA 2 + 2 ESTRELLAS", "COLOR 4 + 6 CIRCLES": "COLOREA 4 + 6 CÍRCULOS"}, ("ADD AND COLOR", "COLOR 2 + 2 STARS", "COLOR 4 + 6 CIRCLES")),
 "decenas": ("Math Activities Level 3.pdf", 3, {"TEN BARS": "BARRAS DE DIEZ", "Count the ten bars and color the correct answer.": "Cuenta las barras y colorea la respuesta correcta."}, ("TEN BARS",)),
 "hora": ("Time Telling Workbook.pdf", 8, {"WRITTEN TIME": "LA HORA EN PALABRAS", "Write the time in words.": "Escribe la hora con palabras.", "ONE O’CLOCK": "LA UNA"}, ("WRITTEN TIME", "ONE O’CLOCK")),
 "sudoku": ("_Sudoku Workbook level 1 .pdf", 3, {"FILL IN THE PUZZLE": "COMPLETA EL SUDOKU: DEL 1 AL 4, SIN REPETIR"}),
 "puntos1": ("Dot to Dot level 1.pdf", 3, {"CONNECT THE DOTS AND COLOR THE PICTURE": "UNE LOS PUNTOS Y COLOREA"}),
 "puntos2": ("Dot to Dot level 1.pdf", 9, {"CONNECT THE DOTS AND COLOR THE PICTURE": "UNE LOS PUNTOS Y COLOREA"}),
 "puntos3": ("Dot to Dot Level 2.pdf", 3, {"CONNECT THE DOTS": "UNE LOS PUNTOS", "COLOR IT": "COLORÉALO", "DRAW IT": "DIBÚJALO"}),
 "diferencias1": ("Find the differences coloring ( 4 Differences ).pdf", 3, {}),
 "diferencias2": ("Find the differences coloring ( 4 Differences ).pdf", 8, {}),
 "diferencias3": ("Find the differences coloring ( 4 Differences ).pdf", 14, {}),
 "figuras": ("_Shapes Activities.pdf", 3, {"Square": "Cuadrado", "Trace it:": "Repasa:", "Color it:": "Colorea:", "Draw it:": "Dibújalo:"}, ("Square",)),
 "granja": ("Farm Animals Activity & Coloring.pdf", 3, {"CHICKEN": "GALLINA", "Chickens lay eggs and are": "Las gallinas ponen huevos", "kept in coops on farms.": "y duermen en el gallinero.",
     "PONY": "PONI", "Ponies are small horses": "Los ponis son caballitos", "that are gentle with children.": "muy cariñosos con los niños.", **T}, ("CHICKEN", "PONY")),
 "mar1": ("Under the Sea Workbook.pdf", 3, {"DOLPHIN": "DELFÍN", "Dolphins are playful and communicate": "Los delfines son juguetones y", "with clicks and whistles.": "hablan con silbidos.",
     "SWORDFISH": "PEZ ESPADA", "Swordfish have long, pointed": "El pez espada tiene una", "\"swords\" on their faces.": "nariz larga como una espada.", **T}, ("DOLPHIN", "SWORDFISH")),
 "mar2": ("Under the Sea Workbook.pdf", 5, {"WHALE": "BALLENA", "Whales are the largest": "Las ballenas son los animales", "animals in the ocean.": "más grandes del mar.",
     "JELLYFISH": "MEDUSA", "Jellyfish have soft bodies and can": "Las medusas son blanditas y", "sting to protect themselves.": "pican para protegerse.", **T}, ("WHALE", "JELLYFISH")),
 "selva": ("Wild Animals Activity & Coloring.pdf", 3, {"ELEPHANT": "ELEFANTE", "Elephants have long trunks that": "Los elefantes usan su trompa", "they use to eat, drink, and play.": "para comer, beber y jugar.",
     "LEOPARD": "LEOPARDO", "Leopards are great climbers": "Los leopardos trepan árboles", "and have spotted coats.": "y tienen manchas.", **T}, ("ELEPHANT", "LEOPARD")),
 "espacio": ("Space Coloring & Learning book (1).pdf", 3, {"SPACE": "EL ESPACIO", "Space is the huge, empty area beyond": "El espacio es enorme y está más allá", "Earth filled with stars and planets.": "de la Tierra, lleno de estrellas y planetas."}, ("SPACE",)),
 "planeta": ("Space Coloring & Learning book (1).pdf", 5, {"PLANET": "PLANETA", "A planet is a big, round object that": "Un planeta es una bola gigante", "orbits a star.": "que gira alrededor de una estrella."}, ("PLANET",)),
}
LETRAS = "A B C D E F G H I J K L LL M N Ñ O P Q R S T U V W X Y Z".split()   # páginas 2..29 del abecedario en español
for i, l in enumerate(LETRAS): P["letra_" + l] = ("Spanish Alphabet Tracing.pdf", i + 2, {})

def lineas(pdf, p):
    t = tempfile.mktemp(suffix=".html"); subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), "-bbox-layout", str(pdf), t], check=True, stderr=subprocess.DEVNULL)
    s = open(t).read()
    for m in re.finditer(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', s, re.S):
        yield [round(float(x) * S) for x in m.groups()[:4]], " ".join(re.findall(r">([^<]+)</word>", m.group(5))).replace("&quot;", '"')

meta = {}
for k, spec in P.items():
    pdf, p, reps = spec[:3]; cont = spec[3] if len(spec) > 3 else ()
    pre = tempfile.mktemp(); subprocess.run(["pdftoppm", "-f", str(p), "-l", str(p), "-r", str(DPI), "-png", str(SRC / pdf), pre], check=True, stderr=subprocess.DEVNULL)
    im = Image.open(next(pathlib.Path(pre).parent.glob(pathlib.Path(pre).name + "*.png"))).convert("L").resize((int(612 * S), int(792 * S)))
    d = ImageDraw.Draw(im); textos = []; faltan = set(reps)
    for box, t in lineas(SRC / pdf, p):
        if re.fullmatch(r"\d+", t) and box[1] > 700 * S: d.rectangle([box[0] - 30, box[1] - 30, box[2] + 30, box[3] + 30], fill=255); continue   # número de página
        if t in reps:
            d.rectangle([box[0] - 6, box[1] - 4, box[2] + 6, box[3] + 4], fill=255); textos.append({"box": box, "t": reps[t], "contorno": t in cont}); faltan.discard(t)
    # el pie original (línea + círculo) se borra: el generador pone el nuestro
    d.rectangle([0, int(712 * S), im.width, im.height], fill=255)
    if faltan: print("⚠️", k, "no encontré:", faltan)
    im.save(OUT / f"{k}.png", optimize=True); meta[k] = textos
json.dump(meta, open(OUT / "paginas.json", "w"), ensure_ascii=False, indent=0)
print(len(meta), "páginas listas")
