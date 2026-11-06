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
    "precio": "SIEMPRE la última: precio que golpea + botón (cta en MAYÚSCULAS ≤ 18 caracteres)",
}
APERTURAS = ["gancho", "pov", "problema"]

STORY_PROMPT = """Eres guionista de Reels/TikTok que venden productos digitales en Latinoamérica. Escribe el guion de UN reel vertical de 12-20 segundos.
Producto: {producto}
Público: {publico}
Páginas disponibles del producto (índice: título): {paginas}
Tipos de escena disponibles: {escenas}
{forzar}
Guiones anteriores (NO repitas su orden de escenas ni sus frases): {evitar}

Devuelve SOLO JSON:
{{"concepto": "idea del reel en 1 frase",
 "estilo": "color|neon|minimal|tiktok (el que mejor encaje con este concepto y público)",
 "musica": "uno de: {generos}", "voz": "femenina|masculina (según quién compra)",
 "escenas": [
   {{"tipo": "...", ...campos del tipo..., "voz": "frase que dice la voz en esta escena"}}
 ],
 "copy": {{"texto": "texto principal para Meta con 3 viñetas con emoji", "titular": "≤ 40 caracteres", "descripcion": "≤ 30 caracteres"}}
}}
Reglas:
- 4 a 6 escenas. La primera es de apertura (gancho, pov o problema). La última es "precio". No repitas un tipo.
- Incluye al menos una escena que MUESTRE el producto (paginas, zoom o grid); "paginas" suele funcionar muy bien.
- Campos por tipo: gancho→lineas [{{"palabras": [...], "resaltar": índice opcional}}]; pov→texto, pagina; problema→titulo, items; paginas→paginas, textos;
  zoom→pagina, texto; grid→texto; incluye→titulo, items; movil→palabras, resaltar; precio→cta.
- Los textos en pantalla deben corresponder a la página que se ve (usa los títulos de la lista).
- "voz": español latino natural y conversacional, MÁXIMO 9 palabras por escena (se lee a ritmo normal). En "precio" di el precio de forma natural ({precio_dicho}).
- Nada de promesas de dinero/salud, ni reseñas o testimonios inventados, ni urgencia falsa. Sin emojis en los textos de pantalla.
- Precio {precio}, antes {tachado}.
"""

def _words(t, n): return " ".join(str(t or "").split()[:n])

def precio_dicho(p):
    try:
        e, c = divmod(round(float(p) * 100), 100)
        return f"{e} dólares con {c}" if c else f"{e} dólares"
    except Exception: return str(p)

def make_storyboard(prod, B, titles, force_open=None, force_style=None, avoid=None, api_key=None, model=None):
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    forzar = []
    if force_open: forzar.append(f"La PRIMERA escena debe ser de tipo \"{force_open}\".")
    if force_style: forzar.append(f"Usa el estilo \"{force_style}\".")
    prompt = STORY_PROMPT.format(
        producto=json.dumps({k: prod.get(k) for k in ("title", "short", "description")}, ensure_ascii=False)[:1500],
        publico=B.get("publico", ""), paginas=json.dumps({i: t for i, t in enumerate(titles)}, ensure_ascii=False),
        escenas=json.dumps(ESCENAS, ensure_ascii=False), forzar="\n".join(forzar), evitar=json.dumps(avoid or [], ensure_ascii=False)[:1500],
        generos=", ".join(GENEROS), precio=prod.get("price"), tachado=prod.get("compare") or "ninguno", precio_dicho=precio_dicho(prod.get("price")))
    body = {"model": model, "max_tokens": 4000, "temperature": 1.0, "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r: data = json.load(r)
    text = "".join(b.get("text", "") for b in data.get("content", [])).replace("```json", "").replace("```", "")
    return normalize_story(json.loads(text[text.index("{"): text.rindex("}") + 1]), B, len(titles), force_open, force_style)

def fallback_story(B, n_pages, force_open=None, force_style=None, seed=0):
    """Guion sin IA (si falla la API): combina escenas al azar a partir del brief."""
    import random
    rng = random.Random(seed)
    tp = B.get("textos_paginas") or ["Mira por dentro"] * n_pages
    opens = {"gancho": {"tipo": "gancho", "lineas": B["gancho"], "voz": B.get("guion_voz", {}).get("gancho", "")},
             "pov": {"tipo": "pov", "texto": "por fin todo en orden", "pagina": 0, "voz": "Por fin, todo en orden."},
             "problema": {"tipo": "problema", "titulo": "¿Te pasa esto?", "items": ["Olvidas pendientes", "Todo desordenado", "Sin tiempo"], "voz": "¿Te pasa esto? Tranquila, hay solución."}}
    first = opens[force_open or rng.choice(APERTURAS)]
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
    return normalize_story(story, B, n_pages, force_open, force_style)

def normalize_story(S, B, n_pages, force_open=None, force_style=None):
    clamp = lambda i: max(0, min(n_pages - 1, int(i))) if str(i).lstrip("-").isdigit() else 0
    out, seen = [], set()
    for sc in S.get("escenas") or []:
        t = sc.get("tipo")
        if t not in ESCENAS or t in seen or t == "precio": continue
        seen.add(t); sc = dict(sc); sc["voz"] = _words(sc.get("voz"), 11)
        if t == "gancho":
            ls = [l for l in sc.get("lineas") or [] if isinstance(l, dict) and l.get("palabras")] or B["gancho"]
            for l in ls: l["palabras"] = [str(w)[:14] for w in l["palabras"]][:4]
            sc["lineas"] = ls[:3]
        elif t == "pov": sc["texto"] = _words(sc.get("texto"), 7) or "por fin todo en orden"; sc["pagina"] = clamp(sc.get("pagina", 0))
        elif t in ("problema", "incluye"):
            sc["titulo"] = _words(sc.get("titulo") or ("¿Te pasa esto?" if t == "problema" else "Incluye"), 5)
            sc["items"] = [_words(i, 5)[:30] for i in (sc.get("items") or []) if str(i).strip()][:5] or ["..."]
        elif t == "paginas":
            idx = [clamp(i) for i in (sc.get("paginas") or list(range(min(4, n_pages))))][:5]
            idx = list(dict.fromkeys(idx)) or [0]
            if len(idx) < 2 and n_pages > 1: idx = list(range(min(4, n_pages)))
            tx = [str(x)[:30] for x in (sc.get("textos") or [])]
            sc["paginas"] = idx; sc["textos"] = (tx + [(B.get("textos_paginas") or [""])[min(i, len(B.get("textos_paginas") or [""]) - 1)] for i in idx])[:len(idx)]
        elif t in ("zoom",): sc["pagina"] = clamp(sc.get("pagina", 1)); sc["texto"] = str(sc.get("texto") or "")[:30]
        elif t == "grid": sc["texto"] = str(sc.get("texto") or "Todo incluido")[:30]
        elif t == "movil":
            sc["palabras"] = [str(w)[:14] for w in (sc.get("palabras") or B.get("movil_texto") or ["En", "tu", "móvil"])][:4]
            r = sc.get("resaltar"); sc["resaltar"] = r if isinstance(r, int) and 0 <= r < len(sc["palabras"]) else len(sc["palabras"]) - 1
        out.append(sc)
    if not out or out[0]["tipo"] not in APERTURAS:
        out.insert(0, {"tipo": "gancho", "lineas": B["gancho"], "voz": B.get("guion_voz", {}).get("gancho", "")})
    out = out[:5]
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
    return {"concepto": str(S.get("concepto", ""))[:200], "estilo": est, "musica": mus, "voz": voz, "escenas": out, "copy": cp}
