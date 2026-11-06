"""Cerebro de los anuncios:
1) investigar(): investigación REAL en internet (con fuentes) del público y de los anuncios que funcionan en el nicho. Se guarda en el brief.
2) elegir(): 3 guiones de formatos distintos + un "director" exigente que elige el mejor y lo pule.
3) revisar(): mira fotogramas del video terminado y corrige lo que no se entienda (una sola vez).
"""
import base64, json, os, subprocess, urllib.request
from concurrent.futures import ThreadPoolExecutor

MODEL = lambda: os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")

def _claude(content, max_tokens=4000, tools=None, timeout=240):
    body = {"model": MODEL(), "max_tokens": max_tokens, "messages": [{"role": "user", "content": content}]}
    if tools: body["tools"] = tools
    out = ""
    for _ in range(5):  # la búsqueda web puede "pausarse": se continúa
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                     headers={"x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""), "anthropic-version": "2023-06-01", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r: data = json.load(r)
        out += "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        if data.get("stop_reason") != "pause_turn": break
        body["messages"] = body["messages"] + [{"role": "assistant", "content": data["content"]}]
    import re
    out = re.sub(r"</?cite[^>]*>", "", out).replace("```json", "").replace("```", "")
    return json.loads(out[out.index("{"): out.rindex("}") + 1])

NEUTRO = ("Español NEUTRO latinoamericano (se vende en varios países): nada de modismos de un solo país (ni 'chévere', 'pana', 'güey', 'chido', 'parce', 'bacán', 'vale'), "
          "sin voseo, tuteo cálido. Palabras que se entiendan igual en México, Colombia, Venezuela, Argentina, Chile, Perú y EE. UU. latino.")

# ===================== 1) investigación real =====================
INV_PROMPT = """Investiga EN INTERNET (5-6 búsquedas, en español e inglés) para hacer anuncios de este producto digital. Hoy es {hoy}.
Producto: {producto}
Público que creemos: {publico}

Busca:
A) Quién compra de verdad este tipo de producto: reseñas de Etsy/Amazon/Hotmart de productos parecidos, comentarios de TikTok/Reddit/foros, artículos.
   Saca sus dolores, deseos, las FRASES TEXTUALES que usa la gente (cortas), dudas antes de comprar y en qué momento lo necesitan.
B) Qué anuncios y videos de este nicho están funcionando ahora (Biblioteca de anuncios de Meta, TikTok Creative Center, videos virales del nicho, artículos de marketing):
   qué ganchos de los primeros 3 segundos se repiten, qué estructuras de video, qué tipo de imágenes. Solo la idea, nunca copiar.
REGLA DE ORO: no inventes. Cada dato debe venir de algo que leíste; si no encontraste algo, deja la lista vacía. Pon la url de donde salió.
Devuelve SOLO JSON:
{{"publico_real": {{"quien": "1-2 frases", "edad": "rango", "paises": [..], "dolores": [..], "deseos": [..], "frases_reales": [..], "objeciones": [..], "momentos": [..]}},
 "anuncios": {{"ganchos": [..], "estructuras": [..], "visuales": [..], "evitar": [..]}},
 "fuentes": [{{"url": "...", "dato": "qué saqué de ahí"}}]}}"""

def investigar(prod, B):
    import datetime
    try:
        R = _claude(INV_PROMPT.format(hoy=datetime.date.today().isoformat(),
                                      producto=json.dumps({k: prod.get(k) for k in ("title", "short", "description", "category")}, ensure_ascii=False)[:1500],
                                      publico=B.get("publico", "")),
                    max_tokens=6000, tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": int(os.environ.get("AD_RESEARCH_SEARCHES", "6"))}], timeout=300)
    except Exception as e:
        print("investigación falló:", e); return None
    pr, an = R.get("publico_real") or {}, R.get("anuncios") or {}
    lim = lambda xs, n=6: [str(x)[:160] for x in (xs or []) if str(x).strip()][:n]
    return {"publico_real": {"quien": str(pr.get("quien", ""))[:300], "edad": str(pr.get("edad", ""))[:30], "paises": lim(pr.get("paises"), 8),
                             "dolores": lim(pr.get("dolores")), "deseos": lim(pr.get("deseos")), "frases_reales": lim(pr.get("frases_reales"), 8),
                             "objeciones": lim(pr.get("objeciones"), 5), "momentos": lim(pr.get("momentos"), 4)},
            "anuncios": {k: lim(an.get(k)) for k in ("ganchos", "estructuras", "visuales", "evitar")},
            "fuentes": [{"url": str(f.get("url", ""))[:300], "dato": str(f.get("dato", ""))[:200]} for f in (R.get("fuentes") or []) if isinstance(f, dict) and f.get("url")][:12]}

def resumen_investigacion(I):
    """Texto corto para Telegram."""
    if not I: return ""
    p = I["publico_real"]; a = I["anuncios"]
    L = [f"🔎 <b>Investigación del público</b> ({len(I['fuentes'])} fuentes)", f"👥 {p['quien']} · {p['edad']}"]
    if p["dolores"]: L.append("😣 " + " · ".join(p["dolores"][:3]))
    if p["frases_reales"]: L.append("💬 «" + "» · «".join(p["frases_reales"][:3]) + "»")
    if a["ganchos"]: L.append("🎣 Ganchos que funcionan: " + " · ".join(a["ganchos"][:3]))
    return "\n".join(L)

# ===================== 2) 3 guiones + director =====================
DIRECTOR = """Eres director creativo exigente de anuncios en Reels/TikTok para productos digitales en Latinoamérica.
Producto: {producto}
Público (investigación real): {inv}
Aquí van {n} guiones candidatos (JSON). Califica cada uno de 1 a 10 en:
- gancho: los primeros 3 segundos frenan el scroll de ESTE público (usa sus dolores/frases reales)
- claridad: en 1 visto se entiende qué es, para qué sirve y cuánto cuesta
- coherencia: en CADA escena la voz, el texto en pantalla y la imagen/foto/meme dicen LO MISMO al mismo tiempo; una sola idea por escena; las búsquedas de fotos muestran literalmente lo que se dice; nadie se pierde
- publico: le habla a esta gente con sus palabras, en español neutro
- originalidad: no parece una plantilla
Luego toma el MEJOR y mejóralo sin cambiar su formato ni sus tipos de escena: arregla lo que bajó la nota (textos más concretos, fotos que coincidan, voz natural ≤ 9 palabras por escena).
{neutro}
Devuelve SOLO JSON: {{"notas": [{{"guion": índice, "gancho": n, "claridad": n, "coherencia": n, "publico": n, "originalidad": n}}], "ganador": índice, "por_que": "1 frase", "guion": {{...el guion ganador mejorado, MISMO esquema JSON...}}}}

Candidatos:
{cands}"""

def elegir(prod, B, make_one, formatos, normalize):
    """make_one(fmt) -> guion normalizado. Hace 3 en paralelo (formatos distintos o el mismo forzado) y el director elige y pule."""
    with ThreadPoolExecutor(3) as ex:
        res = list(ex.map(lambda f: _safe(make_one, f), formatos[:3]))
    cands = [r for r in res if r]
    if not cands: raise RuntimeError("no salió ningún guion")
    if len(cands) == 1: return cands[0], None
    inv = B.get("investigacion") or {"publico": B.get("publico", "")}
    slim = [{k: c.get(k) for k in ("concepto", "formato", "escenas", "copy", "letra", "animacion", "estilo", "musica", "voz", "subtitulos")} for c in cands]
    try:
        D = _claude(DIRECTOR.format(producto=json.dumps({k: prod.get(k) for k in ("title", "short", "price")}, ensure_ascii=False),
                                    inv=json.dumps(inv.get("publico_real", inv), ensure_ascii=False)[:2500], n=len(cands), neutro=NEUTRO,
                                    cands=json.dumps(slim, ensure_ascii=False)[:24000]), max_tokens=6000)
        i = int(D.get("ganador", 0)); i = i if 0 <= i < len(cands) else 0
        best = cands[i]
        if isinstance(D.get("guion"), dict) and D["guion"].get("escenas"):
            g = dict(D["guion"]); g["formato"] = best["formato"]
            try:
                pulido = normalize(g, best["formato"])
                if [e["tipo"] for e in pulido["escenas"]] and len(pulido["escenas"]) >= 3: best = {**pulido, "stock": best.get("stock"), "fondos": best.get("fondos")}
            except Exception as e: print("guion pulido no válido, uso el ganador tal cual:", e)
        nota = next((n for n in D.get("notas", []) if n.get("guion") == i), {})
        return best, {"ganador": i, "por_que": str(D.get("por_que", ""))[:200], "nota": nota, "formatos": [c["formato"] for c in cands]}
    except Exception as e:
        print("director falló, uso el primero:", e); return cands[0], None

def _safe(f, x):
    try: return f(x)
    except Exception as e: print("guion candidato falló:", e); return None

# ===================== 3) revisión final del video =====================
REVISION = """Eres el control de calidad de un anuncio vertical. Te paso {n} fotogramas (uno por escena, en orden) y el guion.
Revisa que: ningún texto esté cortado, tapado o salido de la pantalla; cada escena se entienda sola en 2 segundos; la imagen/foto/meme coincida con lo que dice la voz y el texto;
no haya escenas repetidas; no falte el producto ni el precio; ortografía correcta; español neutro.
Guion: {guion}
Si TODO está bien: {{"ok": true}}.
Si hay fallas: {{"ok": false, "problemas": ["escena N: qué pasa"], "guion": {{...el MISMO guion corregido (mismo esquema, mismos tipos de escena; cambia solo textos, búsquedas de fotos o el orden; {voz})...}}}}
Devuelve SOLO JSON."""

def fotogramas(video, TL, tmpdir, maxn=7):
    out = []
    for k, s in enumerate(TL["scenes"][:maxn]):
        t = s["start"] + s["dur"] * 0.72; p = os.path.join(tmpdir, f"rev{k}.jpg")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "5", p], check=False)
        if os.path.exists(p): out.append(p)
    return out

def revisar(story, video, TL, tmpdir, ahorro=False):
    """Devuelve (guion_corregido o None, problemas)."""
    frames = fotogramas(video, TL, tmpdir)
    if not frames: return None, []
    content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(open(p, "rb").read()).decode()}} for p in frames]
    slim = {k: story.get(k) for k in ("concepto", "formato", "escenas")}
    content.append({"type": "text", "text": REVISION.format(n=len(frames), guion=json.dumps(slim, ensure_ascii=False)[:12000],
                                                           voz="NO cambies los textos de 'voz'" if ahorro else "cambia la 'voz' solo si es imprescindible")})
    try: R = _claude(content, max_tokens=5000)
    except Exception as e: print("revisión falló:", e); return None, []
    if R.get("ok") or not isinstance(R.get("guion"), dict): return None, []
    return R["guion"], [str(x)[:160] for x in (R.get("problemas") or [])][:6]

# ===================== 📹 clip del usuario =====================
def describir_clip(path, dur, tmpdir):
    """Mira 4 fotogramas del clip y dice qué pasa (para escribir el resto del anuncio alrededor)."""
    frames = []
    for k, t in enumerate([dur * x for x in (0.1, 0.4, 0.65, 0.9)]):
        p = os.path.join(tmpdir, f"clip{k}.jpg")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "5", p], check=False)
        if os.path.exists(p): frames.append(p)
    if not frames: return ""
    content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(open(p, "rb").read()).decode()}} for p in frames]
    content.append({"type": "text", "text": f"Son 4 fotogramas en orden de un clip de {dur:.0f} s que abrirá un anuncio. Devuelve SOLO JSON: "
                    '{"que_pasa": "qué pasa en el clip, en 1-2 frases", "momento_clave": segundos en que pasa lo más fuerte (número), "emocion": "1 palabra", '
                    '"zona_libre": "arriba|abajo (dónde se puede poner texto sin tapar la cara)"}'})
    try: return _claude(content, max_tokens=400)
    except Exception as e: print("no pude describir el clip:", e); return {}
