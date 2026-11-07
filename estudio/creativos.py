"""🎨 Creativos de imagen diseñados por la IA (pedido de Diego: que no salgan siempre iguales).
Para cada anuncio Claude actúa de director de arte: con lo que funciona en la CATEGORÍA del producto (investigación con
búsqueda web, 1 vez al mes por categoría), el gancho del reel, lo aprendido en Meta y los diseños ya usados (para no
repetir), escribe 3 diseños DISTINTOS en HTML/CSS con las páginas reales del producto. Chromium los convierte en
imágenes 4:5, 1:1 y 9:16 (A/B/C-…jpg, mismos nombres de siempre). Una revisión con visión corrige lo que se vea mal.
Si algo falla (o el contenedor aún no tiene Chromium) se usa el diseño anterior (motor.build_static)."""
import base64, datetime, hashlib, json, os, pathlib, re, shutil, subprocess, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

import director  # _claude, NEUTRO

PIXELIA = pathlib.Path(os.environ.get("PIXELIA_DIR", "/pixelia"))
FONTDIR = pathlib.Path(__file__).parent / "fonts" / "web"
CACHE = PIXELIA / "data" / "creativos"
SIZES = {"4x5": (1080, 1350), "1x1": (1080, 1080), "9x16": (1080, 1920)}
# Letras de Google Fonts (licencia OFL, uso comercial libre). Se bajan una vez al servidor.
FUENTES = {"Anton": "anton/Anton-Regular.ttf", "Bebas Neue": "bebasneue/BebasNeue-Regular.ttf", "Archivo Black": "archivoblack/ArchivoBlack-Regular.ttf",
           "Montserrat": "montserrat/Montserrat[wght].ttf", "Poppins": None, "Inter": "inter/Inter[opsz,wght].ttf", "Space Grotesk": "spacegrotesk/SpaceGrotesk[wght].ttf",
           "Playfair Display": "playfairdisplay/PlayfairDisplay[wght].ttf", "DM Serif Display": "dmserifdisplay/DMSerifDisplay-Regular.ttf", "Lora": None,
           "Caveat": "caveat/Caveat[wght].ttf", "Pacifico": "pacifico/Pacifico-Regular.ttf", "Permanent Marker": "apache/permanentmarker/PermanentMarker-Regular.ttf",
           "Fredoka": "fredoka/Fredoka[wdth,wght].ttf", "Righteous": "righteous/Righteous-Regular.ttf"}

def chrome():
    for b in (os.environ.get("CHROME_BIN"), "chromium", "chromium-browser", "google-chrome"):
        if b and shutil.which(b): return shutil.which(b)
    return None

def fuentes_css():
    """@font-face de las letras disponibles (se bajan la 1ª vez). Devuelve (css, nombres)."""
    FONTDIR.mkdir(parents=True, exist_ok=True); css, ok = [], []
    base = pathlib.Path(__file__).parent / "fonts"
    for fam, src in FUENTES.items():
        if src is None:
            files = {"Poppins": [("Poppins-Regular.ttf", 400), ("Poppins-Medium.ttf", 500), ("Poppins-Bold.ttf", 700)], "Lora": [("Lora-Medium.ttf", 500)]}[fam]
            for f, w in files:
                if (base / f).exists(): css.append(f"@font-face{{font-family:'{fam}';src:url('file://{base / f}');font-weight:{w}}}")
            ok.append(fam); continue
        p = FONTDIR / src.split("/")[-1].replace("[", "_").replace("]", "_").replace(",", "_")
        if not p.exists():
            try:
                url = "https://raw.githubusercontent.com/google/fonts/main/" + ("" if src.startswith("apache/") else "ofl/") + urllib.request.quote(src)
                with urllib.request.urlopen(url, timeout=30) as r: data = r.read()
                if len(data) > 10000: p.write_bytes(data)
            except Exception as e: print("letra", fam, e)
        if p.exists():
            var = "[" in src
            css.append(f"@font-face{{font-family:'{fam}';src:url('file://{p}');{'font-weight:100 900;' if var else ''}}}"); ok.append(fam)
    return "\n".join(css), ok

def render(html_path, png, w, h):
    b = chrome()
    if not b: raise RuntimeError("falta Chromium en el estudio (bash instalar-estudio.sh)")
    subprocess.run([b, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--default-background-color=FFFFFFFF", f"--window-size={w},{h}", f"--screenshot={png}", f"file://{html_path}"],
                   check=True, capture_output=True, timeout=90)
    Image.open(png).convert("RGB").crop((0, 0, w, h)).save(str(png).replace(".png", ".jpg"), quality=92)

# ---------- investigación por categoría (cacheada 30 días) ----------
INV = """Eres director de arte de anuncios de Meta (Instagram/Facebook) para productos digitales en Latinoamérica. Hoy es {hoy}.
Categoría: {cat}. Ejemplo de producto: {prod}
Busca en internet (máx. 3 búsquedas: Biblioteca de anuncios de Meta, TikTok Creative Center, Pinterest, artículos de creativos que convierten 2025-2026)
qué IMÁGENES de anuncio funcionan para esta categoría: composiciones, estilos visuales, tipos de titular, cómo muestran el producto, qué se ve "nativo" en el feed.
No copies anuncios: saca patrones. Devuelve SOLO JSON:
{{"conceptos":[{{"nombre":"corto","idea":"cómo se ve (1-2 frases)","por_que":"por qué para esta categoría"}}] (8 conceptos MUY distintos entre sí: ej. pantalla de celular/notificaciones, antes y después, editorial tipográfico, lista/checklist, nota escrita a mano, comparación tabla, POV/meme, foto real con texto, mockup del producto protagonista, calendario/fecha clave, pregunta grande, oferta/precio protagonista),
 "colores_que_funcionan":"1 frase","evitar":["…"]}}"""

def investigacion_categoria(prod):
    cat = (prod.get("category") or "general").strip() or "general"
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / ("cat-" + hashlib.sha1(cat.lower().encode()).hexdigest()[:10] + ".json")
    try:
        d = json.loads(f.read_text())
        if (datetime.date.today() - datetime.date.fromisoformat(d["fecha"])).days < 30: return d
    except Exception: pass
    try:
        d = director._claude(INV.format(hoy=datetime.date.today().isoformat(), cat=cat, prod=json.dumps({k: prod.get(k) for k in ("title", "short")}, ensure_ascii=False)),
                             max_tokens=3000, tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}], timeout=240)
        d = {"fecha": datetime.date.today().isoformat(), "categoria": cat, "conceptos": (d.get("conceptos") or [])[:10],
             "colores_que_funcionan": d.get("colores_que_funcionan", ""), "evitar": (d.get("evitar") or [])[:6]}
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1)); return d
    except Exception as e:
        print("investigación de categoría falló:", e); return {"conceptos": [], "evitar": []}

# ---------- diseño ----------
DISENO = """Eres un director de arte TOP de anuncios para Instagram y Facebook (estilo de las marcas que más venden con creativos estáticos).
Diseña {n} imagen(es) de anuncio para este producto digital. Cada una con un CONCEPTO VISUAL DISTINTO, pensado para su categoría y su público.

PRODUCTO: {producto}
PÚBLICO: {publico}
LO QUE CUENTA EL REEL DE ESTE ANUNCIO (la imagen debe contar la misma idea): gancho «{gancho}» · concepto «{concepto}»
QUÉ FUNCIONA EN ESTA CATEGORÍA (investigación real; elige conceptos de aquí o mejores, sin copiar anuncios): {categoria}
{aprendizaje}
NO REPITAS estos conceptos ya usados con este producto: {usados}

RECURSOS (archivos en la misma carpeta; úsalos con <img src="archivo">):
{assets}
- Las páginas del producto son REALES: muéstralas grandes y nítidas (en laptop, tablet, celular, hoja impresa, o recortadas con sombra), porque la gente compra lo que ve.
{fotos}
LETRAS disponibles (font-family): {fuentes}. Emojis a color: sí (con moderación).
COLORES: los del producto {colores} o los que mejor funcionen para el concepto (contraste alto, que destaque en el feed).

REGLAS DEL DISEÑO (HTML + CSS en un solo archivo, sin JavaScript, sin enlaces externos):
- Lienzo = toda la ventana. Se va a capturar a 1080x1350 (principal), 1080x1080 y 1080x1920: usa html,body{{margin:0;width:100vw;height:100vh;overflow:hidden}}, flexbox y medidas relativas
  (vw, vh, vmin, %, clamp) para que se vea BIEN en los 3 tamaños. Nada importante a menos de 5vmin del borde. Nada cortado ni encimado.
- Texto: titular corto y potente (máx. 9 palabras), letras grandes (titular ≥ 7vmin; ningún texto menor de 2.6vmin). Máx. 3 bloques de texto además del precio/CTA.
- Siempre: {precio_regla}, el dominio «{dominio}» y una llamada a la acción corta ({cta}).
- MENSAJE (método de campañas): 1 idea central en 1 frase; habla de BENEFICIOS no de funciones (cada línea responde "¿y a mí qué?" desde quien mira); compáralo con NO hacer nada (seguir como está); usa "tú"; una sola llamada a la acción.
- {neutro}
- Prohibido: reseñas o testimonios inventados, cifras de ventas inventadas, "últimas unidades"/urgencia falsa, logos de marcas (ni Apple, ni Excel, ni Google), personas famosas.
- Que se vea NATIVO y llamativo, no un folleto: jerarquía clara, mucho aire, un punto focal, un detalle que sorprenda (sticker, flecha dibujada, subrayado a mano, etiqueta de precio, notificación, nota adhesiva…).
- Cada diseño DIFERENTE de verdad: otra composición, otra letra, otra paleta, otro concepto.

Devuelve SOLO JSON: {{"disenos":[{{"concepto":"nombre corto","por_que":"1 frase","foto":"búsqueda en inglés para una foto real de Pixabay o null","html":"<!doctype html>…"}}]}}"""

ARREGLO = """Eres el director de arte. Este diseño de anuncio (HTML abajo) se ve así en la captura 1080x1350 adjunta. Problema detectado: {problema}
Corrígelo manteniendo el concepto. Recuerda: medidas relativas, nada cortado/encimado, textos legibles. Devuelve SOLO JSON {{"html":"<!doctype html>…"}}
HTML:
{html}"""

REVISION = """Eres un director de arte exigente. Te paso {n} anuncios (capturas 1080x1350) en orden. Para cada uno dime si está listo para publicar en Instagram.
Mal = texto cortado o encimado, letras ilegibles o muy pequeñas, elementos fuera del lienzo, imagen rota/vacía, se ve amateur o confuso, falta precio/CTA.
Devuelve SOLO JSON {{"revision":[{{"ok":true|false,"problema":"qué arreglar exactamente (si no está ok)"}}]}}"""

def _b64(p): return base64.b64encode(pathlib.Path(p).read_bytes()).decode()

def disenar(prod, B, story, pages, phone, out, tmp, prefixes=("A", "B", "C"), say=None):
    """Crea {prefix}-4x5/1x1/9x16.jpg en out. Devuelve la lista de archivos. Lanza excepción si no se puede."""
    if not chrome(): raise RuntimeError("sin Chromium")
    import formatos
    work = pathlib.Path(tmp) / "creativos"; shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
    assets = []
    for i, pg in enumerate(pages[:4]):
        im = pg.convert("RGB"); im.thumbnail((1400, 1400)); im.save(work / f"producto-{i + 1}.jpg", quality=90)
        assets.append(f"- producto-{i + 1}.jpg: página {i + 1} del producto ({im.width}x{im.height}, {'horizontal' if im.width > im.height else 'vertical'})")
    if phone is not None:
        im = phone.convert("RGB"); im.thumbnail((900, 1600)); im.save(work / "celular.jpg", quality=90)
        assets.append(f"- celular.jpg: cómo se ve en el celular ({im.width}x{im.height})")
    css, fams = fuentes_css()
    inv = investigacion_categoria(prod)
    hist_f = out / "creativos.json"
    try: hist = json.loads(hist_f.read_text())
    except Exception: hist = []
    sc = (story or {}).get("escenas", [{}])
    gancho = " ".join(sum((l.get("palabras", []) for l in (sc[0].get("lineas") or [])), [])) or next((e.get("voz") for e in sc if e.get("voz")), "") if story else ""
    precio = float(prod.get("price") or 0)
    ap = ""
    try: ap = json.loads((PIXELIA / "data" / "aprendizaje-resumen.json").read_text()).get("texto", "")
    except Exception: pass
    hay_fotos = bool(os.environ.get("PIXABAY_API_KEY", "").strip())
    prompt = DISENO.format(
        n=len(prefixes), producto=json.dumps({k: prod.get(k) for k in ("title", "short", "description", "category")}, ensure_ascii=False)[:1400],
        publico=B.get("publico", ""), gancho=gancho[:200], concepto=(story or {}).get("concepto", ""),
        categoria=json.dumps({k: inv.get(k) for k in ("conceptos", "colores_que_funcionan", "evitar")}, ensure_ascii=False)[:3500],
        aprendizaje=("LO QUE YA APRENDIMOS EN META (úsalo): " + ap) if ap else "", usados=json.dumps([h.get("concepto") for h in hist[-8:]], ensure_ascii=False),
        assets="\n".join(assets), fotos=("- FOTO REAL opcional: si el concepto la necesita, pon en \"foto\" una búsqueda en inglés y úsala como <img src=\"foto.jpg\"> SIEMPRE con un color de fondo detrás (por si no llega). Máx. 1 diseño con foto." if hay_fotos else "- No hay fotos de stock: no uses foto.jpg."),
        fuentes=", ".join(fams), colores=", ".join(B.get("colores", [])[:5]),
        precio_regla=(f"el precio «${precio:.2f}» bien visible" + (f" (antes ${float(prod.get('compare')):.2f}, solo si quieres)" if float(prod.get("compare") or 0) > precio else "")) if precio else "la palabra «GRATIS» bien grande (es un regalo a cambio del correo)",
        dominio=B.get("dominio", "pixeliadigital.app"), cta=B.get("cta", "Descárgalo"), neutro=director.NEUTRO)
    if say: say("🎨 Diseñando las imágenes del anuncio (director de arte con IA)…")
    R = director._claude(prompt, max_tokens=16000, timeout=300)
    ds = [d for d in (R.get("disenos") or []) if d.get("html")][:len(prefixes)]
    if not ds: raise RuntimeError("la IA no devolvió diseños")
    files = []

    def armar(k, d):
        sub = work / prefixes[k]; sub.mkdir(exist_ok=True)
        for f in work.glob("*.jpg"): shutil.copy(f, sub / f.name)
        if d.get("foto") and hay_fotos:
            ph = formatos.stock_photo(str(d["foto"])[:80])
            if ph is not None: ph.convert("RGB").save(sub / "foto.jpg", quality=90)
        html = d["html"]
        html = re.sub(r"<link[^>]+>", "", html)
        html = html.replace("<head>", f"<head><meta charset='utf-8'><style>{css}</style>", 1) if "<head>" in html else f"<meta charset='utf-8'><style>{css}</style>" + html
        (sub / "index.html").write_text(html, encoding="utf-8")
        render(sub / "index.html", sub / "4x5.png", *SIZES["4x5"])
        return sub

    subs = [armar(k, d) for k, d in enumerate(ds)]
    # revisión con visión (1 vez): corrige los que se vean mal
    if os.environ.get("CREATIVOS_REVISION", "1") != "0":
        try:
            content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": _b64(s / "4x5.jpg")}} for s in subs]
            content.append({"type": "text", "text": REVISION.format(n=len(subs))})
            rev = director._claude(content, max_tokens=1200, timeout=180).get("revision") or []
            for k, r in enumerate(rev[:len(subs)]):
                if r.get("ok") is False and r.get("problema"):
                    if say: say(f"🔧 Ajustando el diseño {prefixes[k]}: {r['problema'][:120]}")
                    fx = director._claude([{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": _b64(subs[k] / "4x5.jpg")}},
                                           {"type": "text", "text": ARREGLO.format(problema=r["problema"], html=ds[k]["html"][:30000])}], max_tokens=9000, timeout=240)
                    if fx.get("html"): ds[k]["html"] = fx["html"]; subs[k] = armar(k, ds[k])
        except Exception as e: print("revisión de creativos:", e)
    for k, s in enumerate(subs):
        for name, (w, h) in SIZES.items():
            if name != "4x5": render(s / "index.html", s / f"{name}.png", w, h)
            dst = out / f"{prefixes[k]}-{name}.jpg"; shutil.copy(s / f"{name}.jpg", dst); files.append(dst)
        hist.append({"concepto": ds[k].get("concepto"), "por_que": ds[k].get("por_que"), "fecha": datetime.date.today().isoformat()})
    hist_f.write_text(json.dumps(hist[-20:], ensure_ascii=False, indent=1))
    if say: say("🎨 " + " · ".join(f"<b>{p}</b>: {director_esc(ds[k].get('concepto'))}" for k, p in enumerate(prefixes[:len(ds)])))
    return files

def director_esc(s): return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
