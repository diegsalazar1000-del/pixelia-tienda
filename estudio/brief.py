"""Brief creativo con IA: a partir del producto, Claude decide público, colores, textos, voz y música."""
import json, os, urllib.request

GENEROS = ["reggaeton", "pop", "electronica", "lofi", "acustica"]

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
 "guion_voz": {{"gancho": "frase de 2 s", "paginas": "frase de 3-4 s sobre lo que incluye", "movil": "frase de 2 s", "precio": "frase de 2 s con el precio"}},
 "musica": {{"genero": "uno de: {generos}", "bpm": número, "por_que": "breve"}},
 "copy": {{
   "A": {{"texto": "texto principal con 3-4 viñetas con emoji", "titular": "máx 40 caracteres", "descripcion": "máx 30 caracteres"}},
   "B": {{...}}, "C": {{...}}
 }}
}}
Reglas:
- Gancho: pregunta o frase que frene el scroll. Palabra clave en "resaltar" (índice dentro de su línea). Máximo 12 caracteres por palabra.
- Titulares de imágenes: 2 líneas de 2-3 palabras; el enfoque C es la oferta con el precio.
- Colores: 3 colores vivos y saturados que contrasten con texto blanco y encajen con el público (no pasteles apagados).
- Voz y música adecuadas al público (ej. jóvenes/fiesta → reggaetón o pop; profesionales → electrónica suave; estudiantes/calma → lofi; hogar/familia → acústica).
- Nada de promesas de dinero, salud o resultados garantizados; no menciones marcas de terceros (Canva, GoodNotes, Apple…) en titulares.
- Precio: {precio}. Precio anterior: {tachado}.
"""

def make_brief(prod, n_pages, titles=None, api_key=None, model=None):
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    txt = json.dumps({k: prod.get(k) for k in ("title", "short", "description", "category", "price", "compare")}, ensure_ascii=False)
    body = {"model": model, "max_tokens": 4000, "messages": [{"role": "user", "content": PROMPT.format(
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
    return B
