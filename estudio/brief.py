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
    clean = lambda t: " ".join(w for w in str(t).replace("·", " ").split() if not w.isdigit() and w not in ("‹", "›"))[:26]
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
