"""🎨 Reel diseñado (FASE DE PRUEBA, solo con el botón "🎨 Reel diseñado (prueba)", opción d=1).
Igual que las imágenes de creativos.py: la IA diseña cada escena del guion en HTML/CSS pensando en el producto y su público
(no plantilla fija). Chromium hace capturas por escena y por "paso" (los elementos .r1/.r2/.r3 van apareciendo) y aquí se
animan (entrada con golpe, zoom lento, transición) sin más llamadas a la IA. 1 sola llamada a Claude por reel, sin revisión.
Voz, música y efectos: los de siempre (misma línea de tiempo que story.timeline). Si algo falla, el estudio usa el reel normal."""
import json, os, pathlib, re, shutil, subprocess
from PIL import Image, ImageStat

import director, creativos
import story as story_mod
from motor import W, H, FPS, back_out, ease_in_out, clamp

XF = 0.22
PROMPT = """Eres director de arte de REELS para Instagram/TikTok (anuncios que frenan el scroll). Diseña cada escena de este reel de 9:16
como una "diapositiva" que muestra EN PANTALLA lo que la voz está diciendo en ese momento, pensada para ESTE producto y SU público
(nada de plantilla genérica: la estética sale del producto, su categoría y lo que funciona en ella).

PRODUCTO: {producto}
PÚBLICO: {publico}
QUÉ FUNCIONA EN SU CATEGORÍA: {categoria}
{aprendizaje}
GUION (una diapositiva por escena, en este orden; "dice" = lo que dice la voz; "datos" = textos/listas del guion para esa escena; "seg" = duración):
{escenas}

RECURSOS (misma carpeta, usa <img src="archivo">): {assets}
LETRAS (font-family): {fuentes}. Emojis a color: sí, con moderación.

REGLAS (un solo HTML, sin JavaScript, sin enlaces externos):
- html,body{{margin:0;width:1080px;height:1920px;overflow:hidden}}. Cada escena es <section class="s" id="s1">…</section>, <section class="s" id="s2">… (position:absolute;inset:0).
  CSS compartido UNA vez en <style> (sé compacto: clases reutilizables, una identidad visual coherente en todo el reel, con variaciones de composición por escena).
- Elementos que deben APARECER uno tras otro dentro de la escena: ponles class "r1", "r2", "r3" (en ese orden; el fondo y lo fijo sin clase). Máx. 3 pasos.
- Texto: corto (lo esencial de lo que dice la voz, máx. 8 palabras por bloque), MUY grande (titulares ≥ 90px, nada menor de 40px), alto contraste, márgenes ≥ 70px,
  y deja libre la franja de abajo (los últimos 280px) salvo en la última escena.
- Muestra el producto REAL (las imágenes de páginas) en al menos 2 escenas: en celular, laptop, hoja, tarjetas con sombra… grande y nítido.
- Primera escena = gancho que frena el scroll (contraste, tamaño, sorpresa). Última escena = {precio_regla} + «{dominio}» + llamada a la acción «{cta}».
- MENSAJE (método de campañas): 1 idea central en 1 frase; habla de BENEFICIOS no de funciones (cada línea responde "¿y a mí qué?" desde quien mira); compáralo con NO hacer nada (seguir como está); usa "tú"; una sola llamada a la acción.
- {neutro}
- Prohibido: reseñas o cifras inventadas, urgencia falsa, logos de marcas, personas famosas.
Devuelve SOLO JSON: {{"concepto":"nombre corto del estilo","html":"<!doctype html>…"}}"""

def _datos(sc):
    d = {k: sc[k] for k in ("titulo", "texto", "items", "pasos", "mensajes", "lineas", "antes", "despues", "cta", "subtitulo") if sc.get(k)}
    if d.get("lineas"): d["lineas"] = [" ".join(l.get("palabras", [])) if isinstance(l, dict) else str(l) for l in d["lineas"]]
    return json.dumps(d, ensure_ascii=False)[:400]

def _shots(html_path, out_dir, k, pasos):
    """Capturas de la escena k: estado 0 (sin .r1.r2.r3) … estado pasos (todo)."""
    base = html_path.read_text(encoding="utf-8"); files = []
    for st in range(pasos + 1):
        hide = ",".join(f"#s{k} .r{i}" for i in range(st + 1, 4))
        css = f"<style>.s:not(#s{k}){{display:none!important}}{hide + '{visibility:hidden!important}' if hide else ''}</style>"
        p = out_dir / f"e{k}_{st}.html"; p.write_text(base.replace("</head>", css + "</head>", 1) if "</head>" in base else css + base, encoding="utf-8")
        creativos.render(p, out_dir / f"e{k}_{st}.png", W, H)
        files.append(Image.open(out_dir / f"e{k}_{st}.jpg").convert("RGB"))
    return files

def _zoom(im, z, cx=0.5, cy=0.5):
    if abs(z - 1) < 1e-3: return im
    w, h = int(W * z), int(H * z); big = im.resize((w, h), Image.BILINEAR)
    x, y = int((w - W) * cx), int((h - H) * cy); return big.crop((x, y, x + W, y + H))

def construir(prod, B, story, pages, phone, out_path, tmp, vdurs=None, say=None):
    """Arma el reel mudo en out_path y devuelve la línea de tiempo (TL) para el audio de siempre."""
    if not creativos.chrome(): raise RuntimeError("sin Chromium")
    work = pathlib.Path(tmp) / "reel_diseno"; shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
    TL = story_mod.timeline(story, vdurs); escenas = story["escenas"]
    assets = []
    for i, pg in enumerate(pages[:4]):
        im = pg.convert("RGB"); im.thumbnail((1400, 1400)); im.save(work / f"producto-{i + 1}.jpg", quality=88)
        assets.append(f"producto-{i + 1}.jpg (página {i + 1}, {im.width}x{im.height})")
    if phone is not None:
        im = phone.convert("RGB"); im.thumbnail((900, 1600)); im.save(work / "celular.jpg", quality=88); assets.append(f"celular.jpg (vista en celular, {im.width}x{im.height})")
    css, fams = creativos.fuentes_css()
    inv = creativos.investigacion_categoria(prod)  # cacheada 30 días por categoría (no gasta otra vez)
    ap = ""
    try: ap = json.loads((creativos.PIXELIA / "data" / "aprendizaje-resumen.json").read_text()).get("texto", "")
    except Exception: pass
    precio = float(prod.get("price") or 0)
    lista = [{"n": k + 1, "tipo": sc["tipo"], "dice": str(sc.get("voz") or "")[:220], "datos": _datos(sc), "seg": s["dur"]} for k, (sc, s) in enumerate(zip(escenas, TL["scenes"]))]
    if say: say("🎨 Reel diseñado (prueba): la IA está diseñando cada escena…")
    R = director._claude(PROMPT.format(
        producto=json.dumps({k: prod.get(k) for k in ("title", "short", "category")}, ensure_ascii=False)[:600], publico=B.get("publico", ""),
        categoria=json.dumps({k: inv.get(k) for k in ("conceptos", "colores_que_funcionan", "evitar")}, ensure_ascii=False)[:2200],
        aprendizaje=("LO QUE YA APRENDIMOS EN META: " + ap[:800]) if ap else "", escenas=json.dumps(lista, ensure_ascii=False),
        assets=", ".join(assets), fuentes=", ".join(fams),
        precio_regla=f"el precio «${precio:.2f}» bien visible" if precio else "la palabra «GRATIS» enorme (regalo a cambio del correo)",
        dominio=B.get("dominio", "pixeliadigital.app"), cta=B.get("cta", "Descárgalo"), neutro=director.NEUTRO),
        max_tokens=int(os.environ.get("REEL_DISENO_TOKENS", "12000")), timeout=300)
    html = re.sub(r"<link[^>]+>", "", R.get("html") or "")
    if "<section" not in html: raise RuntimeError("la IA no devolvió escenas")
    html = html.replace("<head>", f"<head><meta charset='utf-8'><style>{css}</style>", 1) if "<head>" in html else f"<meta charset='utf-8'><style>{css}</style>" + html
    doc = work / "reel.html"; doc.write_text(html, encoding="utf-8")
    shots = []
    for k in range(1, len(escenas) + 1):
        sec = re.search(rf'<section[^>]*id=["\']s{k}["\'][\s\S]*?(?=<section[^>]*id=["\']s{k + 1}["\']|</body>|$)', html)
        pasos = max([int(x) for x in re.findall(r'class=["\'][^"\']*\br([123])\b', sec.group(0))] or [0]) if sec else 0
        fr = _shots(doc, work, k, pasos)
        if ImageStat.Stat(fr[-1].convert("L")).stddev[0] < 6: raise RuntimeError(f"la escena {k} salió vacía")
        shots.append(fr)
    # animación: entrada con golpe, pasos que aparecen, zoom lento y transición entre escenas
    def frame(t):
        i = max(k for k, s in enumerate(TL["scenes"]) if s["start"] <= t + 1e-6); s = TL["scenes"][i]; u = t - s["start"]; d = s["dur"]; fr = shots[i]
        n = len(fr) - 1; ventana = min(0.35 * d, 0.35 + 0.4 * n)
        st = 0 if n == 0 else min(n, int(clamp((u - 0.06) / max(0.1, ventana) * (n + 1), 0, n + 0.999)))
        if i == 0: st = max(st, 1 if n else 0)  # el gancho nunca arranca vacío (miniatura y primer segundo)
        img = fr[st]
        if n and st > 0 and not (i == 0 and st == 1):  # el paso nuevo entra suave (el 1º del gancho ya está desde el inicio)
            t0 = 0.06 + ventana * st / (n + 1); a = clamp((u - t0) / 0.18)
            if a < 1: img = Image.blend(fr[st - 1], fr[st], ease_in_out(a))
        z = 1.0 + 0.035 * u / d
        if i == 0: z += 0.12 * (1 - back_out(clamp(u / 0.45)))  # golpe de entrada del gancho
        img = _zoom(img, z, 0.5, 0.45)
        if i > 0 and u < XF:
            ps = TL["scenes"][i - 1]; prev = _zoom(shots[i - 1][-1], 1.035 + 0.12 * (u / XF), 0.5, 0.45)
            img = Image.blend(prev, img, ease_in_out(u / XF))
        return img
    ff = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)]
    proc = subprocess.Popen(ff, stdin=subprocess.PIPE)
    for fi in range(int(TL["T"] * FPS)): proc.stdin.write(frame(fi / FPS).tobytes())
    proc.stdin.close(); proc.wait()
    if proc.returncode: raise RuntimeError("ffmpeg falló")
    story["concepto"] = (story.get("concepto") or "") + f" · diseño: {R.get('concepto', '')}"
    try:
        hist_f = out_path.parent / "reels-disenados.json"; hist = json.loads(hist_f.read_text()) if hist_f.exists() else []
        hist_f.write_text(json.dumps((hist + [{"concepto": R.get("concepto")}])[-10:], ensure_ascii=False))
    except Exception: pass
    return TL
