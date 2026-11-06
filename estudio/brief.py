"""Brief creativo con IA: a partir del producto, Claude decide público, colores, textos, voz y música."""
import json, os, urllib.request

GENEROS = ["reggaeton", "pop", "electronica", "lofi", "acustica", "cumbia", "trap"]
ESTILOS = ["color", "neon", "minimal", "tiktok"]
TIPOS = ["problema", "curiosidad", "oferta", "pov"]

PROMPT = """Eres director creativo de anuncios para Meta (Reels/Stories) de una tienda de productos digitales en español para Latinoamérica.
Producto:
{producto}

Devuelve SOLO un JSON válido (sin texto extra) con esta forma exacta:
{{
 "publico": "a quién va dirigido, en una frase",
 "paises": ["3 a 5 países de Latam donde más conviene anunciarlo"],
 "edad": "rango, ej 18-34",
 "colores": ["#hex", "#hex", "#hex"],
 "gancho": [{{"palabras": ["2-3 palabras"]}}, {{"palabras": ["2-3 palabras"]}}, {{"palabras": ["2 palabras"], "resaltar": 1}}],
 "textos_paginas": ["{n} frases MUY cortas (máx 26 caracteres), una por cada página de la lista, que describan ESA página"],
 "movil_texto": ["3-4 palabras"], "movil_resaltar": 0,
 "stickers": ["3 textos de 1-2 palabras para stickers, ej: NUEVO, PDF, Fácil de usar"],
 "cta": "LLAMADA A LA ACCIÓN EN MAYÚSCULAS, máx 18 caracteres",
 "estaticos": [
   {{"titular": [{{"palabras": ["..."]}}, {{"palabras": ["..."], "resaltar": 0}}], "cta": "MAYÚSCULAS", "pagina": 1, "pagina_fondo": 2}},
   {{"titular": [...], "cta": "...", "pagina": 2, "pagina_fondo": 3}},
   {{"titular": [...], "cta": "...", "pagina": 0, "pagina_fondo": 1}}
 ],
 "voz": {{"genero": "femenina|masculina", "por_que": "breve"}},
 "guion_voz": {{"gancho": "MÁX 5 palabras", "paginas": "MÁX 9 palabras sobre lo que incluye", "movil": "MÁX 5 palabras", "precio": "MÁX 6 palabras, con el precio dicho natural (ej: 'solo cuatro noventa y nueve')"}},
 "ganchos": [
   {{"tipo": "problema", "lineas": [{{"palabras": ["..."]}}, {{"palabras": ["..."]}}, {{"palabras": ["..."], "resaltar": 0}}], "voz": "MÁX 5 palabras", "texto": "texto principal corto para Meta (2-3 líneas + 3 viñetas con emoji)", "titular": "máx 40 caracteres"}},
   {{"tipo": "curiosidad", ...}}, {{"tipo": "oferta", ...}}, {{"tipo": "pov", ...}}
 ],
 "musica": {{"genero": "uno de: {generos}", "bpm": número, "por_que": "breve"}},
 "estilo": {{"sugerido": "uno de: color, neon, minimal, tiktok", "por_que": "breve"}},
 "copy": {{
   "A": {{"texto": "texto principal con 3-4 viñetas con emoji", "titular": "máx 40 caracteres", "descripcion": "máx 30 caracteres"}},
   "B": {{...}}, "C": {{...}}
 }}
}}
Reglas:
- Gancho: pregunta o frase que frene el scroll. Palabra clave en "resaltar" (índice dentro de su línea). Máximo 12 caracteres por palabra.
- Titulares de imágenes: 2 líneas de 2-3 palabras; el enfoque C es la oferta con el precio.
- Colores: 3 colores vivos y saturados que contrasten con texto blanco y encajen con el público (no pasteles apagados).
- Voz y música adecuadas al público, pensando en lo que hoy está de moda en Reels/TikTok en esos países: jóvenes 16-24 → reggaetón o trap; 25-34 urbano → pop o reggaetón; organización/estudio/calma → lofi; profesionales/negocios → electrónica suave; hogar/familia/manualidades → acústica; público popular de México, Colombia, Perú, Argentina → cumbia. Voz femenina o masculina según quién compra (no siempre femenina).
- El GUION DE VOZ se lee a ritmo normal: respeta el máximo de palabras; frases naturales, como habla una persona, sin listas ni símbolos.
- Los 4 ganchos deben ser realmente distintos: problema (dolor del cliente), curiosidad (pregunta o dato que intriga), oferta (precio/descuento), pov ("POV: ..." escena con la que el público se identifica). Máx 3 líneas de 1-3 palabras.
- Nada de promesas de dinero, salud o resultados garantizados; no menciones marcas de terceros (Canva, GoodNotes, Apple…) en titulares.
- Precio: {precio}. Precio anterior: {tachado}.
"""

def make_brief(prod, n_pages, titles=None, api_key=None, model=None):
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    txt = json.dumps({k: prod.get(k) for k in ("title", "short", "description", "category", "price", "compare")}, ensure_ascii=False)
    body = {"model": model, "max_tokens": 7000, "messages": [{"role": "user", "content": PROMPT.format(
        producto=txt + "\nPáginas que se verán en el reel, en orden: " + json.dumps(titles or [], ensure_ascii=False), n=n_pages, generos=", ".join(GENEROS), precio=prod.get("price"), tachado=prod.get("compare") or "ninguno")}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.load(r)
    text = "".join(b.get("text", "") for b in data.get("content", [])).replace("```json", "").replace("```", "")
    B = json.loads(text[text.index("{"): text.rindex("}") + 1])
    return normalize(B, prod, n_pages, titles)

def normalize(B, prod, n_pages, titles=None):
    """Completa y corrige el brief para que el motor nunca falle."""
    B.setdefault("colores", ["#FF6B4A", "#FFB23F", "#FF6FA8"])
    B["colores"] = [c for c in B["colores"] if isinstance(c, str) and c.startswith("#") and len(c) == 7][:4] or ["#FF6B4A", "#FFB23F", "#FF6FA8"]
    tw = [w for w in str(prod.get("title", "")).replace("·", " ").split() if len(w) > 1][:5]
    B.setdefault("gancho", [{"palabras": tw[:2] or ["Nuevo"]}, {"palabras": (tw[2:4] or ["producto"]) + ["✨"][:0]}, {"palabras": ["Descárgalo", "HOY"], "resaltar": 1}])
    for l in B["gancho"]: l["palabras"] = [w[:14] for w in l.get("palabras", [])][:4] or ["..."]
    def clean(t):  # título de página → texto corto: sin números, sin palabras repetidas, máx 4 palabras
        ws = []
        for w in str(t).replace("·", " ").split():
            if w.isdigit() or w in ("‹", "›") or w.lower() in [x.lower() for x in ws]: continue
            ws.append(w)
        return " ".join(ws[:4])[:26]
    tp = [str(x)[:30] for x in B.get("textos_paginas", [])] or [clean(t) for t in (titles or [])]
    B["textos_paginas"] = (tp + [tp[-1] if tp else prod.get("title", "")[:26]] * n_pages)[:n_pages]
    B.setdefault("movil_texto", ["También", "en", "tu", "MÓVIL"]); B.setdefault("movil_resaltar", len(B["movil_texto"]) - 1)
    B.setdefault("stickers", ["NUEVO", "PDF", "Descarga inmediata"])
    B["cta"] = (B.get("cta") or "DESCÁRGALO HOY")[:20]
    est = B.get("estaticos") or []
    while len(est) < 3: est.append({"titular": [{"palabras": prod.get("title", "Nuevo").split()[:3]}], "cta": B["cta"], "pagina": len(est), "pagina_fondo": len(est) + 1})
    B["estaticos"] = est[:3]
    v = B.get("voz") or {}; v["genero"] = v.get("genero") if v.get("genero") in ("femenina", "masculina") else "femenina"; B["voz"] = v
    m = B.get("musica") or {}; m["genero"] = m.get("genero") if m.get("genero") in GENEROS else "pop"; B["musica"] = m
    B["precio"] = float(prod.get("price") or 0); B["tachado"] = float(prod.get("compare") or 0) or None
    B["dominio"] = prod.get("dominio", "pixeliadigital.app")
    gv = B.get("guion_voz") or {"gancho": " ".join(w for l in B["gancho"][:2] for w in l["palabras"]), "paginas": "Todo lo que necesitas, en un solo lugar.",
                                "movil": "También en tu móvil.", "precio": "Hoy con descuento. Descárgalo ya."}
    lim = {"gancho": 6, "paginas": 10, "movil": 6, "precio": 8}
    B["guion_voz"] = {k: " ".join(str(gv.get(k, "")).split()[:n]) for k, n in lim.items() if gv.get(k)}
    # 4 ganchos distintos para las variantes (si la IA no los dio, se derivan)
    gs = [g for g in (B.get("ganchos") or []) if isinstance(g, dict) and g.get("lineas")]
    copyA = (B.get("copy") or {}).get("A") or {}
    precio = f"${B['precio']:.2f}"
    fallback = {"problema": B["gancho"], "curiosidad": [{"palabras": ["¿Ya", "viste", "esto?"]}, {"palabras": tw[:2] or ["Nuevo"]}, {"palabras": ["en", "PDF"], "resaltar": 1}],
                "oferta": [{"palabras": ["Solo", precio], "resaltar": 1}, {"palabras": tw[:2] or ["Descarga"]}, {"palabras": ["al", "instante"]}],
                "pov": [{"palabras": ["POV:", "por", "fin"]}, {"palabras": ["todo", "en", "orden"], "resaltar": 2}]}
    have = {g.get("tipo") for g in gs}
    for t in TIPOS:
        if t not in have: gs.append({"tipo": t, "lineas": fallback[t]})
    for g in gs:
        for l in g["lineas"]: l["palabras"] = [w[:14] for w in l.get("palabras", [])][:4] or ["..."]
        g["lineas"] = g["lineas"][:3]
        g["voz"] = " ".join(str(g.get("voz") or B["guion_voz"].get("gancho", "")).split()[:6])
        g.setdefault("texto", copyA.get("texto", "")); g.setdefault("titular", copyA.get("titular", ""))
    B["ganchos"] = gs[:4]
    e = B.get("estilo") or {}; e["sugerido"] = e.get("sugerido") if e.get("sugerido") in ESTILOS else "color"; B["estilo"] = e
    return B


# ===================== GUION DE CADA REEL (distinto cada vez) =====================
ESCENAS = {
    "gancho": "texto grande animado palabra por palabra para frenar el scroll (lineas: 2-3 líneas de 1-3 palabras)",
    "pov": "'POV: ...' escena con la que el público se identifica, sobre una página del producto (texto ≤ 6 palabras, pagina)",
    "problema": "título + 3 dolores cortos del cliente que aparecen tachados con ✗ (titulo ≤ 4 palabras, items ≤ 4 palabras c/u)",
    "paginas": "el producto en tablet pasando 3-5 páginas con un texto por página (paginas: índices, textos ≤ 26 caracteres)",
    "zoom": "acercamiento a una página para mostrar un detalle (pagina, texto ≤ 26 caracteres)",
    "grid": "mosaico de varias páginas apareciendo, muestra cantidad/variedad (texto ≤ 26 caracteres)",
    "incluye": "lista 'Incluye:' con 3-5 cosas que aparecen con ✓ (titulo ≤ 3 palabras, items ≤ 4 palabras)",
    "movil": "el producto en un móvil con lluvia de stickers (palabras: 3-4 palabras, resaltar índice)",
    "chat": "conversación de WhatsApp ficticia y natural que cuenta una mini historia (mensajes: 3-6 [{de: 'otro'|'yo', texto ≤ 60 caracteres, img: true opcional para mandar una foto del producto, pagina}], nombre del contacto)",
    "notificaciones": "pantalla bloqueada del móvil con notificaciones que llegan (items: 3-4 [{app: nombre genérico como 'Recordatorios' o 'Calendario', titulo, texto}]) — sin marcas reales",
    "scroll": "el producto en el móvil recorrido con el dedo hacia abajo (paginas: índices, texto ≤ 26 caracteres)",
    "escribir": "un lápiz escribe a mano sobre una página del producto, se ve cómo se usa (pagina, lineas: 2-4 frases cortas escritas a mano, texto ≤ 26 caracteres arriba)",
    "antes_despues": "pantalla dividida: ANTES (notas desordenadas) vs AHORA (el producto) (antes: 3 palabras del caos, pagina, texto ≤ 30 caracteres opcional)",
    "top3": "3 razones numeradas con números gigantes (titulo ≤ 4 palabras, items: 3 razones ≤ 4 palabras)",
    "broll": "video REAL de fondo (stock) con texto grande encima (busqueda: 2-4 palabras EN INGLÉS para buscar el video, de objetos/lugares, sin caras, ej. 'cozy desk coffee notebook'; lineas como en gancho)",
    "montaje": "SOLO en modo fotos reales: montaje rápido de 4-8 fotos reales, cada foto ilustra lo que se dice (planos: [{busqueda: 2-5 palabras EN INGLÉS de una foto concreta que muestre esa idea, puede ser graciosa o curiosa pero relacionada con el producto, texto: ≤ 4 palabras en pantalla, producto: true si en ese plano se ve el producto, pagina}])",
    "pasos": "TUTORIAL: explica cómo se usa el producto paso a paso con un ejemplo real (titulo ≤ 5 palabras, items: 3-5 pasos [{texto: ≤ 8 palabras, pagina: índice de la página que muestra ese paso}]); úsalo cuando la gente podría no entender qué es o cómo se usa",
    "meme": "COMEDIA: meme como los virales (tarjeta blanca con texto negro arriba y foto de reacción abajo), 2-3 paneles que cuentan el chiste y el último remata con el producto (plantilla: nadie_yo | texto_arriba | expectativa | antes; paneles: [{texto: ≤ 70 caracteres, busqueda: 2-5 palabras EN INGLÉS de una foto de reacción graciosa SIN famosos ni marcas (ej. 'shocked cat', 'man crying laptop', 'dog sunglasses relaxed', 'woman buried in papers'), producto: true en el panel que muestra el producto, pagina, zoom_dramatico: true opcional}], remate: ≤ 28 caracteres en un botón al final)",
    "precio": "SIEMPRE la última: precio que golpea + botón (cta en MAYÚSCULAS ≤ 18 caracteres)",
}
APERTURAS = ["meme", "gancho", "pov", "problema", "chat", "notificaciones", "broll", "antes_despues", "montaje"]
FORMATOS = {
    "clasico": ("texto animado + producto en tablet pasando páginas", ["gancho", "paginas"]),
    "conversacion": ("empieza con un chat de WhatsApp que cuenta una historia y revela el producto", ["chat"]),
    "vida_real": ("video real de fondo con un texto potente, luego el producto", ["broll"]),
    "pantalla": ("notificaciones en el móvil y el producto recorrido con el dedo", ["notificaciones", "scroll"]),
    "tutorial": ("video tutorial: explica cómo se usa paso a paso con un ejemplo (ideal si el producto no es conocido); puede incluir el lápiz escribiendo", ["pasos", "escribir"]),
    "comparacion": ("antes / después", ["antes_despues"]),
    "lista": ("top 3 razones con números gigantes", ["top3"]),
    "comedia": ("humor viral: toma un formato de chiste que esté pegando en TikTok/Reels (Nadie: / Yo:, expectativa vs realidad, POV exagerado, 'yo antes / yo ahora') y hazlo con el producto; abre con un meme y remata mostrando el producto", ["meme"]),
}

STORY_PROMPT = """Eres guionista de Reels/TikTok que venden productos digitales en Latinoamérica. Escribe el guion de UN reel vertical de 12-20 segundos.
Producto: {producto}
Público: {publico}
Investigación REAL de este público y de los anuncios que funcionan en el nicho (úsala: sus dolores, sus frases y los ganchos que funcionan; no inventes datos): {investigacion}
Páginas disponibles del producto (índice: título): {paginas}
Tipos de escena disponibles: {escenas}
Formatos de anuncio disponibles (elige UNO, el que más pegue con este público y producto): {formatos}
{forzar}
Guiones anteriores (NO repitas su orden de escenas ni sus frases): {evitar}

Devuelve SOLO JSON:
{{"concepto": "idea del reel en 1 frase", "formato": "uno de los formatos",
 "letra": "tipografía de los titulares: poppins (moderna redonda) | anton (impacto, condensada) | bebas (mayúsculas altas, tendencia) | archivo (gruesa, fuerte) | pacifico (manuscrita, femenina/cálida) | lora (elegante, serif)",
 "animacion": "cómo entran las palabras: pop | subir | rebote | zoom | maquina (se escriben letra a letra)", "subtitulos": true/false (true si hay voz y el público es de TikTok/Reels),
 "estilo": "color|neon|minimal|tiktok (el que mejor encaje con este concepto y público)",
 "musica": "uno de: {generos}", "voz": "femenina|masculina (según quién compra)",
 "escenas": [
   {{"tipo": "...", ...campos del tipo..., "voz": "frase que dice la voz en esta escena"}}
 ],
 "copy": {{"texto": "texto principal para Meta con 3 viñetas con emoji", "titular": "≤ 40 caracteres", "descripcion": "≤ 30 caracteres"}}
}}
Reglas:
- 4 a 6 escenas. La primera debe enganchar (gancho, pov, problema, chat, notificaciones, broll o antes_despues). La última es "precio". No repitas un tipo.
- Incluye al menos una escena que MUESTRE el producto (paginas, zoom o grid); "paginas" suele funcionar muy bien.
- Campos por tipo: gancho→lineas [{{"palabras": [...], "resaltar": índice opcional}}]; pov→texto, pagina; problema→titulo, items; paginas→paginas, textos;
  zoom→pagina, texto; grid→texto; incluye→titulo, items; movil→palabras, resaltar; chat→nombre, mensajes; notificaciones→items, fecha;
  scroll→paginas, texto; escribir→pagina, lineas, texto; antes_despues→antes, pagina, texto; top3→titulo, items; broll→busqueda, lineas; meme→plantilla, paneles, remate; precio→cta.
- Si el producto es poco conocido o hay que explicar cómo se usa (un juego, un kit, algo nuevo), prefiere el formato "tutorial" con una escena "pasos".
- En "comedia": el chiste es sobre una situación cotidiana del público que el producto resuelve (exagerada, autoironía, nunca burlándote del cliente ni de nadie). Inspírate en la ESTRUCTURA de memes y sketches virales, pero no copies clips, audios, frases registradas ni personajes famosos. La voz puede sonar divertida y con timing (pausas, "...").
- El formato elegido manda: usa sus escenas clave y complétalo con 2-4 escenas que encajen (no siempre las mismas).
- En "chat" la conversación es una escena dramatizada y cotidiana (amigas, compañeros), nunca una reseña ni un testimonio de resultados.
- Los textos en pantalla deben corresponder a la página que se ve (usa los títulos de la lista).
- COHERENCIA (para que nadie se pierda): en cada escena la voz, el texto en pantalla y lo que se ve cuentan LA MISMA idea al mismo tiempo; una sola idea por escena; el texto en pantalla resume lo que dice la voz; las búsquedas de fotos/memes muestran literalmente lo que se dice; la historia avanza en orden (problema → producto → cómo ayuda → precio).
- Sé concreto y detallista con ESTE producto: nombra lo que trae de verdad (usa los títulos de las páginas) y el momento real en que esta persona lo usa. Nada de frases genéricas que sirvan para cualquier producto.
- Idioma: español NEUTRO latinoamericano (se vende en varios países): sin modismos de un solo país (ni chévere, pana, güey, chido, parce, bacán, vale), sin voseo, tuteo cálido.
- "voz": español latino natural y conversacional, MÁXIMO 9 palabras por escena (se lee a ritmo normal). En "precio" di el precio de forma natural ({precio_dicho}).
- Nada de promesas de dinero/salud, ni reseñas o testimonios inventados, ni urgencia falsa. Sin emojis en los textos de pantalla.
- Precio {precio}, antes {tachado}.
"""

import re as _re
_EMOJI = _re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]")
def noemoji(t): return " ".join(_EMOJI.sub("", str(t or "")).split())  # la tipografía no tiene emojis (saldrían cuadritos)
def _words(t, n): return " ".join(noemoji(t).split()[:n])

def precio_dicho(p):
    try:
        e, c = divmod(round(float(p) * 100), 100)
        return f"{e} dólares con {c}" if c else f"{e} dólares"
    except Exception: return str(p)

def make_storyboard(prod, B, titles, force_open=None, force_style=None, avoid=None, api_key=None, model=None, force_format=None, stock=False):
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    forzar = []
    if force_open: forzar.append(f"La PRIMERA escena debe ser de tipo \"{force_open}\".")
    if force_style: forzar.append(f"Usa el estilo \"{force_style}\".")
    if force_format in FORMATOS: forzar.append(f"Usa el formato \"{force_format}\" ({FORMATOS[force_format][0]}).")
    if stock:  # botón "Crear con fotos y videos de Pixabay"
        forzar.append("MODO FOTOS REALES: arma el reel sobre todo con 2 o 3 escenas \"montaje\" (en total 10-18 fotos) intercaladas con 1 escena que muestre el producto (paginas o zoom) y termina con \"precio\". "
                      "Cada foto debe ilustrar EXACTAMENTE la frase que se dice en ese momento (si hablas de olvidar citas: 'woman forgot appointment phone calendar'; de desorden: 'messy desk sticky notes'; de organizarse: 'hands writing planner coffee'). "
                      "Puedes usar ideas graciosas o curiosas (un gato sobre la agenda, alguien enterrado en papeles) siempre que se entienda la relación con el producto. Mete 2-3 planos con producto: true. "
                      "Las búsquedas en inglés, concretas y visuales; nada de marcas ni personas famosas.")
    prompt = STORY_PROMPT.format(
        producto=json.dumps({k: prod.get(k) for k in ("title", "short", "description")}, ensure_ascii=False)[:1500],
        publico=B.get("publico", ""), investigacion=json.dumps({k: (B.get("investigacion") or {}).get(k) for k in ("publico_real", "anuncios")}, ensure_ascii=False)[:3000] if B.get("investigacion") else "no disponible", paginas=json.dumps({i: t for i, t in enumerate(titles)}, ensure_ascii=False),
        escenas=json.dumps(ESCENAS, ensure_ascii=False), formatos=json.dumps({k: v[0] for k, v in FORMATOS.items()}, ensure_ascii=False), forzar="\n".join(forzar), evitar=json.dumps(avoid or [], ensure_ascii=False)[:1500],
        generos=", ".join(GENEROS), precio=prod.get("price"), tachado=prod.get("compare") or "ninguno", precio_dicho=precio_dicho(prod.get("price")))
    body = {"model": model, "max_tokens": 4000, "temperature": 1.0, "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r: data = json.load(r)
    text = "".join(b.get("text", "") for b in data.get("content", [])).replace("```json", "").replace("```", "")
    return normalize_story(json.loads(text[text.index("{"): text.rindex("}") + 1]), B, len(titles), force_open, force_style, force_format, stock)

def rank_formats(prod, B, api_key=None):
    """Los 4 formatos que más pegan con este público (para las 4 variantes)."""
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    prompt = (f"Producto digital: {prod.get('title')}. Público: {B.get('publico', '')}.\nFormatos de anuncio: "
              + json.dumps({k: v[0] for k, v in FORMATOS.items()}, ensure_ascii=False)
              + "\nDevuelve SOLO un JSON con los 4 formatos (claves) que más venderían a este público, del mejor al peor, todos distintos: {\"formatos\": [..]}")
    body = {"model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"), "max_tokens": 300, "messages": [{"role": "user", "content": prompt}]}
    try:
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                     headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r: data = json.load(r)
        t = "".join(b.get("text", "") for b in data.get("content", []))
        got = [f for f in json.loads(t[t.index("{"): t.rindex("}") + 1]).get("formatos", []) if f in FORMATOS]
    except Exception as e:
        print("rank_formats:", e); got = []
    for f in ["conversacion", "vida_real", "comparacion", "clasico", "lista", "pantalla", "tutorial"]:
        if f not in got: got.append(f)
    return list(dict.fromkeys(got))[:4]

def fallback_story(B, n_pages, force_open=None, force_style=None, seed=0, force_format=None, stock=False):
    """Guion sin IA (si falla la API): combina escenas al azar a partir del brief."""
    import random
    rng = random.Random(seed)
    tp = B.get("textos_paginas") or ["Mira por dentro"] * n_pages
    opens = {"gancho": {"tipo": "gancho", "lineas": B["gancho"], "voz": B.get("guion_voz", {}).get("gancho", "")},
             "pov": {"tipo": "pov", "texto": "por fin todo en orden", "pagina": 0, "voz": "Por fin, todo en orden."},
             "problema": {"tipo": "problema", "titulo": "¿Te pasa esto?", "items": ["Olvidas pendientes", "Todo desordenado", "Sin tiempo"], "voz": "¿Te pasa esto? Tranquila, hay solución."}}
    k = force_open or rng.choice(APERTURAS)
    first = opens[k] if k in opens else key_scene(k, B, n_pages)
    middle = [{"tipo": "paginas", "paginas": list(range(min(4, n_pages))), "textos": tp[:4], "voz": B.get("guion_voz", {}).get("paginas", "")},
              {"tipo": "grid", "texto": "Todo lo que necesitas", "voz": "Todo lo que necesitas, en un solo lugar."},
              {"tipo": "zoom", "pagina": min(1, n_pages - 1), "texto": tp[min(1, len(tp) - 1)], "voz": "Cada detalle, pensado para ti."},
              {"tipo": "incluye", "titulo": "Incluye", "items": [t for t in tp[:4]], "voz": "Mira todo lo que incluye."},
              {"tipo": "movil", "palabras": B.get("movil_texto", ["También", "en", "tu", "móvil"]), "resaltar": B.get("movil_resaltar"), "voz": "Y también en tu móvil."}]
    rng.shuffle(middle)
    middle.sort(key=lambda m: m["tipo"] != "paginas")  # las páginas pasando (lo que mejor funciona) casi siempre van
    story = {"concepto": "guion automático", "estilo": force_style or rng.choice(ESTILOS), "musica": B["musica"]["genero"], "voz": B["voz"]["genero"],
             "escenas": [first] + middle[: rng.choice([2, 3])] + [{"tipo": "precio", "cta": B.get("cta", "DESCÁRGALO HOY"), "voz": B.get("guion_voz", {}).get("precio", "")}],
             "copy": (B.get("copy") or {}).get("A") or {}}
    if force_format: story["formato"] = force_format
    return normalize_story(story, B, n_pages, force_open, force_style, force_format, stock)

def key_scene(t, B, n_pages):
    """Escena clave de cada formato con textos genéricos (si la IA no la dio)."""
    tp = B.get("textos_paginas") or ["Mira por dentro"]
    return {"chat": {"tipo": "chat", "nombre": "Ana", "mensajes": [{"de": "otro", "texto": "Amiga, ¿cómo haces para tener todo tan organizado?"},
                     {"de": "yo", "texto": "Uso este planner digital"}, {"de": "yo", "texto": "", "img": True, "pagina": 0}, {"de": "otro", "texto": "¡Pásame el link!"}],
                     "voz": "Mi amiga me preguntó cómo me organizo."},
            "broll": {"tipo": "broll", "busqueda": "cozy desk coffee notebook", "lineas": B["gancho"], "voz": B.get("guion_voz", {}).get("gancho", "")},
            "notificaciones": {"tipo": "notificaciones", "items": [{"app": "Recordatorios", "titulo": "Pagar la luz", "texto": "Vence hoy"},
                               {"app": "Calendario", "titulo": "Cita médica", "texto": "Mañana 9:00"}, {"app": "Notas", "titulo": "Lista del súper", "texto": "Sin terminar"}],
                               "voz": "¿Tu móvil también te recuerda todo lo que olvidas?"},
            "scroll": {"tipo": "scroll", "paginas": list(range(min(5, n_pages))), "texto": "Mira por dentro", "voz": "Así se ve por dentro."},
            "escribir": {"tipo": "escribir", "pagina": min(1, n_pages - 1), "lineas": ["Ahorrar para el viaje", "Leer 2 libros", "Ir al gym"], "texto": "Así de fácil", "voz": "Escribes tus metas y listo."},
            "antes_despues": {"tipo": "antes_despues", "antes": ["papelitos", "olvidos", "estrés"], "pagina": min(1, n_pages - 1), "texto": "", "voz": "Antes, caos. Ahora, todo en orden."},
            "top3": {"tipo": "top3", "titulo": "3 razones", "items": [x for x in tp[:3]] or ["Fácil", "Bonito", "Completo"], "voz": "Tres razones para tenerlo."},
            "gancho": {"tipo": "gancho", "lineas": B["gancho"], "voz": B.get("guion_voz", {}).get("gancho", "")},
            "pasos": {"tipo": "pasos", "titulo": "Así se usa", "voz": "Así de fácil se usa, paso a paso.", "items": [
                {"texto": "Descárgalo al instante", "pagina": 0}, {"texto": "Ábrelo en tu tablet o imprímelo", "pagina": min(1, n_pages - 1)},
                {"texto": "Rellénalo a tu gusto", "pagina": min(2, n_pages - 1)}, {"texto": "Disfrútalo todos los días", "pagina": min(3, n_pages - 1)}]},
            "montaje": {"tipo": "montaje", "voz": "¿Tu agenda es un caos? Así se organiza tu año.", "planos": [
                {"busqueda": "messy desk sticky notes", "texto": "¿Todo un caos?"}, {"busqueda": "stressed woman calendar", "texto": "¿Olvidas todo?"},
                {"busqueda": "", "texto": "Tu planner 2027", "producto": True, "pagina": 0}, {"busqueda": "hands writing planner coffee", "texto": "Todo en orden"},
                {"busqueda": "happy woman tablet sofa", "texto": "Por fin"}]},
            "paginas": {"tipo": "paginas", "paginas": list(range(min(4, n_pages))), "textos": tp[:4], "voz": B.get("guion_voz", {}).get("paginas", "")},
            "meme": {"tipo": "meme", "plantilla": "expectativa", "remate": "Por fin lo logré", "voz": "Yo intentando organizarme... versus yo con esto.", "paneles": [
                {"texto": "Yo jurando que este mes sí me organizo", "busqueda": "woman buried in papers stressed"},
                {"texto": "Yo desde que tengo esto", "producto": True, "pagina": 0}]}}[t]

def normalize_story(S, B, n_pages, force_open=None, force_style=None, force_format=None, stock=False):
    clamp = lambda i: max(0, min(n_pages - 1, int(i))) if str(i).lstrip("-").isdigit() else 0
    out, seen = [], set()
    comedia = (force_format or S.get("formato")) == "comedia"
    for sc in S.get("escenas") or []:
        t = sc.get("tipo")
        if t == "meme" and not comedia: continue  # los memes solo en el formato comedia
        if t not in ESCENAS or (t in seen and t != "montaje") or t == "precio" or (t == "montaje" and not stock): continue
        seen.add(t); sc = dict(sc); sc["voz"] = _words(sc.get("voz"), 11)
        if t == "gancho":
            ls = [l for l in sc.get("lineas") or [] if isinstance(l, dict) and l.get("palabras")] or B["gancho"]
            for l in ls: l["palabras"] = [noemoji(w)[:14] for w in l["palabras"] if noemoji(w)][:4]
            sc["lineas"] = ls[:3]
        elif t == "pov": sc["texto"] = _words(sc.get("texto"), 7) or "por fin todo en orden"; sc["pagina"] = clamp(sc.get("pagina", 0))
        elif t in ("problema", "incluye"):
            sc["titulo"] = _words(sc.get("titulo") or ("¿Te pasa esto?" if t == "problema" else "Incluye"), 5)
            sc["items"] = [_words(i, 5)[:30] for i in (sc.get("items") or []) if str(i).strip()][:5] or ["..."]
        elif t == "paginas":
            idx = [clamp(i) for i in (sc.get("paginas") or list(range(min(4, n_pages))))][:5]
            idx = list(dict.fromkeys(idx)) or [0]
            if len(idx) < 2 and n_pages > 1: idx = list(range(min(4, n_pages)))
            tx = [noemoji(x)[:30] for x in (sc.get("textos") or [])]
            sc["paginas"] = idx; sc["textos"] = (tx + [(B.get("textos_paginas") or [""])[min(i, len(B.get("textos_paginas") or [""]) - 1)] for i in idx])[:len(idx)]
        elif t in ("zoom",): sc["pagina"] = clamp(sc.get("pagina", 1)); sc["texto"] = noemoji(sc.get("texto"))[:30]
        elif t == "grid": sc["texto"] = noemoji(sc.get("texto") or "Todo incluido")[:30]
        elif t == "movil":
            sc["palabras"] = [str(w)[:14] for w in (sc.get("palabras") or B.get("movil_texto") or ["En", "tu", "móvil"])][:4]
            r = sc.get("resaltar"); sc["resaltar"] = r if isinstance(r, int) and 0 <= r < len(sc["palabras"]) else len(sc["palabras"]) - 1
        elif t == "chat":
            ms = [m for m in sc.get("mensajes") or [] if isinstance(m, dict) and (m.get("texto") or m.get("img"))][:6]
            for m in ms: m["de"] = "yo" if m.get("de") == "yo" else "otro"; m["texto"] = noemoji(m.get("texto"))[:80]; m["pagina"] = clamp(m.get("pagina", 0))
            if len(ms) < 2: continue
            sc["mensajes"] = ms; sc["nombre"] = str(sc.get("nombre") or "Ana")[:16]
        elif t == "notificaciones":
            its = [i for i in sc.get("items") or [] if isinstance(i, dict) and i.get("titulo")][:4]
            if not its: continue
            sc["items"] = [{"app": noemoji(i.get("app") or "Recordatorios")[:20], "titulo": noemoji(i["titulo"])[:30], "texto": noemoji(i.get("texto"))[:38]} for i in its]
        elif t == "scroll":
            sc["paginas"] = list(dict.fromkeys(clamp(i) for i in (sc.get("paginas") or range(min(5, n_pages)))))[:6] or [0]; sc["texto"] = noemoji(sc.get("texto"))[:30]
        elif t == "escribir":
            sc["pagina"] = clamp(sc.get("pagina", 1)); sc["lineas"] = [str(x)[:28] for x in (sc.get("lineas") or ["Mi meta"])][:4]; sc["texto"] = noemoji(sc.get("texto"))[:30]
        elif t == "antes_despues":
            sc["antes"] = [str(x)[:16] for x in (sc.get("antes") or ["caos", "olvidos", "estrés"])][:4]; sc["pagina"] = clamp(sc.get("pagina", 1)); sc["texto"] = noemoji(sc.get("texto"))[:30]
        elif t == "top3":
            sc["titulo"] = _words(sc.get("titulo") or "3 razones", 5); sc["items"] = [_words(i, 5)[:28] for i in (sc.get("items") or [])][:3]
            if len(sc["items"]) < 3: continue
        elif t == "montaje":
            ps = [p for p in sc.get("planos") or [] if isinstance(p, dict) and (p.get("busqueda") or p.get("producto"))][:8]
            for p in ps:
                p["busqueda"] = " ".join(str(p.get("busqueda") or "").split()[:6]); p["texto"] = noemoji(p.get("texto"))[:28]
                p["producto"] = bool(p.get("producto")); p["pagina"] = clamp(p.get("pagina", 0))
            if len(ps) < 3: continue
            sc["planos"] = ps
        elif t == "meme":
            ps = [p for p in sc.get("paneles") or [] if isinstance(p, dict) and p.get("texto")][:3]
            for p in ps:
                p["texto"] = noemoji(p["texto"])[:80]; p["busqueda"] = " ".join(str(p.get("busqueda") or "").split()[:6])
                p["producto"] = bool(p.get("producto")); p["pagina"] = clamp(p.get("pagina", 0)); p["zoom_dramatico"] = bool(p.get("zoom_dramatico"))
            if len(ps) < 2: continue
            if not any(p["producto"] for p in ps): ps[-1]["producto"] = True
            sc["paneles"] = ps; sc["plantilla"] = sc.get("plantilla") if sc.get("plantilla") in ("nadie_yo", "texto_arriba", "expectativa", "antes") else "texto_arriba"
            sc["remate"] = noemoji(sc.get("remate"))[:28]
        elif t == "pasos":
            its = [i for i in sc.get("items") or [] if isinstance(i, dict) and i.get("texto")][:5]
            for i in its: i["texto"] = _words(i["texto"], 9); i["pagina"] = clamp(i.get("pagina", 0))
            if len(its) < 2: continue
            sc["items"] = its; sc["titulo"] = _words(sc.get("titulo") or "Así se usa", 5)
        elif t == "broll":
            sc["busqueda"] = " ".join(str(sc.get("busqueda") or "cozy desk notebook").split()[:5])
            ls = [l for l in sc.get("lineas") or [] if isinstance(l, dict) and l.get("palabras")] or [{"palabras": str(sc.get("texto") or "").split()[:3] or ["Nuevo"]}]
            for l in ls: l["palabras"] = [noemoji(w)[:14] for w in l["palabras"] if noemoji(w)][:4]
            sc["lineas"] = ls[:3]
        out.append(sc)
    fmt = force_format or (S.get("formato") if S.get("formato") in FORMATOS else None)
    if fmt and not any(s["tipo"] in FORMATOS[fmt][1] for s in out):  # el formato manda: su escena clave va primero
        k = FORMATOS[fmt][1][0]; out = [s for s in out if s["tipo"] != k]
        out.insert(0 if k in APERTURAS else min(1, len(out)), key_scene(k, B, n_pages))
    if force_open and (not out or out[0]["tipo"] != force_open):
        out = [s for s in out if s["tipo"] != force_open]; out.insert(0, key_scene(force_open, B, n_pages) if force_open in ("chat", "broll", "notificaciones", "antes_despues", "gancho") else {"tipo": "gancho", "lineas": B["gancho"], "voz": ""})
    if not out or out[0]["tipo"] not in APERTURAS:
        out.insert(0, {"tipo": "gancho", "lineas": B["gancho"], "voz": B.get("guion_voz", {}).get("gancho", "")})
    out = out[:5]
    if stock and not any(s["tipo"] == "montaje" for s in out):
        out.insert(0, key_scene("montaje", B, n_pages)); out = out[:5]
    if len(out) < 3:  # asegura algo de producto en pantalla
        if "paginas" not in [s["tipo"] for s in out]:
            out.append({"tipo": "paginas", "paginas": list(range(min(4, n_pages))), "textos": (B.get("textos_paginas") or [""])[:4], "voz": ""})
    pr = next((s for s in S.get("escenas") or [] if s.get("tipo") == "precio"), {}) or {}
    out.append({"tipo": "precio", "cta": str(pr.get("cta") or B.get("cta") or "DESCÁRGALO HOY").upper()[:20],
                "voz": _words(pr.get("voz") or B.get("guion_voz", {}).get("precio", ""), 11)})
    est = force_style or (S.get("estilo") if S.get("estilo") in ESTILOS else "color")
    mus = S.get("musica") if S.get("musica") in GENEROS else B["musica"]["genero"]
    voz = S.get("voz") if S.get("voz") in ("femenina", "masculina") else B["voz"]["genero"]
    cp = S.get("copy") or (B.get("copy") or {}).get("A") or {}
    letras = ("poppins", "anton", "bebas", "archivo", "pacifico", "lora"); anims = ("pop", "subir", "rebote", "zoom", "maquina")
    import random as _r
    fondos = [" ".join(str(q).split()[:6]) for q in (S.get("fondos") or []) if str(q).strip()][:5]
    if stock and not fondos: fondos = [s.get("busqueda") for s in out if s.get("busqueda")] or ["cozy desk coffee notebook", "hands writing planner", "minimal workspace morning"]
    return {"concepto": str(S.get("concepto", ""))[:200], "formato": fmt or "clasico", "subtitulos": bool(S.get("subtitulos", True)),
            "letra": S.get("letra") if S.get("letra") in letras else _r.choice(letras[:4]), "animacion": S.get("animacion") if S.get("animacion") in anims else _r.choice(anims),
            "stock": bool(stock), "fondos": fondos,
            "estilo": est, "musica": mus, "voz": voz, "escenas": out, "copy": cp}
