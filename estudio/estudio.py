"""Trabajador del estudio de anuncios. Corre en su propio contenedor (pixelia-estudio) en el VPS.
Pide trabajos a la tienda, genera imágenes + reel con audio y los envía al bot del radar en Telegram.
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile, time, traceback, urllib.request, uuid, zipfile
from PIL import Image

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import motor, story as story_mod, audio, musica, brief as brief_mod, director, formatos  # noqa: E402

PIXELIA = pathlib.Path(os.environ.get("PIXELIA_DIR", "/pixelia"))

def load_env():
    env = {}
    for line in (PIXELIA / ".env").read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1); env[k.strip()] = v.strip()
    return env

ENV = load_env()
STORE = os.environ.get("STORE_URL", "http://127.0.0.1:3000")
KEY = ENV.get("N8N_API_KEY", "")
TG = ENV.get("RADAR_BOT_TOKEN", ""); CHAT = ENV.get("TELEGRAM_ADMIN_CHAT_ID", "")
os.environ.setdefault("ANTHROPIC_API_KEY", ENV.get("ANTHROPIC_API_KEY", ""))
os.environ.setdefault("ANTHROPIC_MODEL", ENV.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"))
if ENV.get("ELEVENLABS_API_KEY"): os.environ.setdefault("ELEVENLABS_API_KEY", ENV["ELEVENLABS_API_KEY"])
if ENV.get("PEXELS_API_KEY"): os.environ.setdefault("PEXELS_API_KEY", ENV["PEXELS_API_KEY"])
if ENV.get("PIXABAY_API_KEY"): os.environ.setdefault("PIXABAY_API_KEY", ENV["PIXABAY_API_KEY"])
GEN_NAMES = {"reggaeton": "Reggaetón", "pop": "Pop", "trap": "Trap", "cumbia": "Cumbia", "electronica": "Electrónica", "lofi": "Lo-fi", "acustica": "Acústica", "base": "Suave", "0": "sin música"}
VOZ_NAMES = {"f": "voz femenina", "m": "voz masculina", "0": "sin voz"}
FORMAT_NAMES = {"clasico": "Clásico", "conversacion": "💬 Chat", "vida_real": "🎬 Video real", "pantalla": "📱 Pantalla de móvil",
                "tutorial": "✍️ Cómo se usa", "comparacion": "🔀 Antes/después", "lista": "🏆 Top 3", "comedia": "😂 Comedia", "clip": "📹 Tu video"}
# 4 variantes para A/B en Meta: (estilo, tipo de gancho)
VARIANTES = [("color", "gancho"), ("tiktok", "pov"), ("neon", "problema"), ("minimal", "gancho")]  # (estilo, escena de apertura)

# ---------- HTTP ----------
def api(method, path, data=None):
    req = urllib.request.Request(STORE + path, method=method, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"x-api-key": KEY, "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        if r.status == 204: return None
        return json.load(r)

def tg(method, fields=None, files=None):
    """Llamada a Telegram con multipart (para enviar fotos y video)."""
    boundary = uuid.uuid4().hex; body = bytearray()
    for k, v in (fields or {}).items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n".encode()
        body += (json.dumps(v) if isinstance(v, (dict, list)) else str(v)).encode() + b"\r\n"
    for k, path in (files or {}).items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{pathlib.Path(path).name}\"\r\nContent-Type: application/octet-stream\r\n\r\n".encode()
        body += pathlib.Path(path).read_bytes() + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{TG}/{method}", data=bytes(body), headers={"content-type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=180) as r: return json.load(r)

def say(text, kb=None):
    f = {"chat_id": CHAT, "text": text[:4000], "parse_mode": "HTML", "disable_web_page_preview": "true"}
    if kb: f["reply_markup"] = {"inline_keyboard": kb}
    return tg("sendMessage", f)

def esc(s): return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ---------- páginas del producto ----------
MESES = {"enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"}
NAV = {"índice", "indice", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic", "hábitos", "finanzas", "notas", "2027", "2026", "2028"}

def page_text(pdf, i):
    t = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
    words = [w for w in t.split() if w.lower() not in NAV]
    def is_title(l):
        toks = [w.lower().strip(".,:") for w in l.split()]
        return len(l.strip()) > 3 and sum(w in NAV for w in toks) < 2 and any(w not in NAV and not w.isdigit() for w in toks)
    title = next((l.strip() for l in t.splitlines() if is_title(l)), "")
    return len(words), " ".join(title.split())[:60]

def pdf_pages(pdf, tmp, want=6, dpi=100):
    """Elige páginas variadas y con contenido (evita las del final, que suelen ser notas o en blanco)."""
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    n = int(next((l.split()[-1] for l in out.splitlines() if l.startswith("Pages:")), "1"))
    last = max(2, int(n * 0.85)) if n > 6 else n
    cand = sorted(set([1] + [max(1, round(1 + k * (last - 1) / max(1, want * 2 - 1))) for k in range(want * 2)]))
    info = {i: page_text(pdf, i) for i in cand}
    keep = [1] + [i for i in cand[1:] if info[i][0] >= 8]           # con algo de contenido
    titles_seen, chosen = set(), []
    for i in keep:                                                  # sin repetir el mismo tipo de página
        first = (info[i][1].split() or [""])[0].lower().strip(".,:·")
        key = "mes" if first in MESES else first   # una sola página de cada tipo (un mes, una semana, hábitos…)
        if i == 1 or key not in titles_seen: chosen.append(i); titles_seen.add(key)
    if len(chosen) > want: chosen = [chosen[0]] + [chosen[1:][round(k * (len(chosen) - 2) / (want - 2))] for k in range(want - 1)]
    imgs, titles = [], []
    for i in chosen[:want]:
        base = pathlib.Path(tmp) / f"p{pathlib.Path(pdf).stem}_{i}"
        subprocess.run(["pdftoppm", "-f", str(i), "-l", str(i), "-r", str(dpi), "-png", "-singlefile", str(pdf), str(base)], check=True)
        imgs.append(Image.open(f"{base}.png").convert("RGB")); titles.append(info.get(i, (0, ""))[1] or f"página {i}")
    return imgs, titles

def product_pages(prod, tmp):
    f = PIXELIA / "storage" / "products" / (prod.get("file_name") or "_")
    if not f.exists(): raise RuntimeError("El producto no tiene archivo subido (sube un PDF o un ZIP con PDF o imágenes).")
    pdfs, images = [], []
    if f.suffix.lower() == ".pdf": pdfs = [f]
    elif f.suffix.lower() == ".zip":
        with zipfile.ZipFile(f) as z:
            for name in z.namelist():
                low = name.lower()
                if low.endswith(".pdf") or low.endswith((".png", ".jpg", ".jpeg")):
                    dst = pathlib.Path(tmp) / f"z_{len(pdfs) + len(images)}_{pathlib.Path(name).name}"
                    dst.write_bytes(z.read(name)); (pdfs if low.endswith(".pdf") else images).append(dst)
    elif f.suffix.lower() in (".png", ".jpg", ".jpeg"): images = [f]
    if pdfs:
        main = max(pdfs, key=lambda p: ("movil" not in p.name.lower(), p.stat().st_size))  # el principal (no la versión móvil)
        pages, titles = pdf_pages(main, tmp)
        mob = next((p for p in pdfs if "movil" in p.name.lower() or "mobile" in p.name.lower()), None)
        phone = (lambda ims: ims[min(2, len(ims) - 1)])(pdf_pages(mob, tmp, want=4)[0]) if mob else pages[min(1, len(pages) - 1)]
    elif images:
        imgs = [Image.open(p).convert("RGB") for p in sorted(images)[:8] if "sticker" not in p.name.lower()] or [Image.open(images[0]).convert("RGB")]
        pages = imgs[:6]; phone = pages[min(1, len(pages) - 1)]; titles = [p.stem for p in sorted(images)[:6]]
    else:
        raise RuntimeError("No encontré PDF ni imágenes dentro del archivo del producto.")
    if len(pages) == 1: pages, titles = pages * 2, titles * 2
    return pages, phone, titles

# ---------- trabajo ----------
def hook_lines(story):
    """Titular de imagen a partir de la apertura del guion (para que imagen y reel cuenten lo mismo)."""
    sc = story["escenas"][0]
    if sc["tipo"] in ("gancho", "broll"): return sc["lineas"]
    if sc["tipo"] == "clip" and (sc.get("gancho") or {}).get("lineas"): return sc["gancho"]["lineas"]
    if sc["tipo"] == "chat": words = next((m["texto"] for m in sc["mensajes"] if m.get("texto")), "").split()[:8]
    elif sc["tipo"] == "notificaciones": words = sc["items"][0]["titulo"].split()
    elif sc["tipo"] == "antes_despues": words = ["Antes", "vs", "AHORA"]
    else: words = None
    if words is not None:
        lines = [words[k:k + 3] for k in range(0, len(words), 3)][:3]
        return [{"palabras": l} for l in lines] or [{"palabras": ["Nuevo"]}]
    words = (["POV:"] + sc.get("texto", "").split()) if sc["tipo"] == "pov" else sc.get("titulo", "").split()
    lines = [words[k:k + 3] for k in range(0, len(words), 3)][:3]
    return [{"palabras": l, **({"resaltar": 0} if sc["tipo"] == "pov" and n == 0 else {})} for n, l in enumerate(lines)] or [{"palabras": ["Nuevo"]}]

def real_photo(story):
    """Foto real de Pixabay acorde al producto (usa la búsqueda de la escena de video real del guion)."""
    import formatos
    q = next((p.get("busqueda") for s in story["escenas"] for p in s.get("planos", []) if p.get("busqueda") and not p.get("producto")), None) \
        or next((s.get("busqueda") for s in story["escenas"] if s.get("busqueda")), None) or "cozy desk coffee notebook"
    return formatos.stock_photo(q)

def clip_frame(story, tmp):
    """Fotograma del clip del usuario para las imágenes estáticas."""
    sc = story["escenas"][0]; p = os.path.join(tmp, "clipframe.jpg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{sc['dur'] * 0.45:.2f}", "-i", sc["archivo"], "-frames:v", "1", p], check=False)
    try: return Image.open(p).convert("RGB")
    except Exception: return None

def history(out):
    f = out / "historial.json"
    try: return json.loads(f.read_text())
    except Exception: return []

def remember(out, st):
    h = history(out) + [{"concepto": st.get("concepto"), "formato": st.get("formato"), "orden": [e["tipo"] for e in st["escenas"]],
                         "frases": [e.get("voz") for e in st["escenas"]][:3]}]
    (out / "historial.json").write_text(json.dumps(h[-12:], ensure_ascii=False))

def three_formats(prod, B, out):
    """3 formatos distintos para los candidatos: los 2 que más pegan y no se usaron hace poco + 1 al azar (para variar)."""
    import random
    used = [h.get("formato") for h in history(out)[-3:]]
    rank = ranked_formats(prod, B, out / "brief.json") + [f for f in brief_mod.FORMATOS if f not in B.get("formatos_rank", [])]
    fresh = [f for f in rank if f not in used] or rank
    rest = [f for f in fresh[2:] if f != "comedia"] or fresh[2:] or rank
    return list(dict.fromkeys(fresh[:2] + [random.choice(rest)]))

def new_story(prod, B, titles, n_pages, out, force_style=None, force_open=None, extra_avoid=None, seed=0, force_format=None, stock=False, single=False):
    avoid = history(out)[-5:] + (extra_avoid or [])
    mk = lambda f: brief_mod.make_storyboard(prod, B, titles, force_open=force_open, force_style=force_style, avoid=avoid, force_format=f, stock=stock)
    try:
        if single or os.environ.get("AD_DIRECTOR", "1") == "0": return mk(force_format)
        fmts = [force_format] * 3 if (force_format or stock) else three_formats(prod, B, out)
        norm = lambda g, f: brief_mod.normalize_story(g, B, n_pages, force_open, force_style, f, stock)
        story, info = director.elegir(prod, B, mk, fmts, norm)
        if info:
            n = info.get("nota") or {}
            say(f"🎬 El director comparó {len(info['formatos'])} guiones ({', '.join(FORMAT_NAMES.get(f, f) for f in info['formatos'])}) y eligió "
                f"<b>{esc(FORMAT_NAMES.get(story.get('formato'), story.get('formato')))}</b>"
                + (f" · gancho {n.get('gancho')}/10 · coherencia {n.get('coherencia')}/10" if n else "") + (f"\n💡 {esc(info['por_que'])}" if info.get("por_que") else ""))
        return story
    except Exception as e:
        print("guion IA falló:", e)
        return brief_mod.fallback_story(B, n_pages, force_open=force_open, force_style=force_style, seed=seed or int(time.time()), force_format=force_format, stock=stock)

def ranked_formats(prod, B, brief_file):
    """Formatos ordenados por lo que más pega con el público (se calcula una vez y se guarda en el brief)."""
    if not B.get("formatos_rank"):
        B["formatos_rank"] = brief_mod.rank_formats(prod, B)
        brief_file.write_text(json.dumps(B, ensure_ascii=False, indent=2))
    return B["formatos_rank"]

def next_format(prod, B, brief_file, out):
    """'Otra variante': el siguiente formato mejor valorado que no se usó en los últimos reels."""
    used = [h.get("formato") for h in history(out)[-4:]]
    rank = ranked_formats(prod, B, brief_file) + [f for f in brief_mod.FORMATOS if f not in B.get("formatos_rank", [])]
    return next((f for f in rank if f not in used), rank[0])

def clip_story(prod, B, titles, n_pages, out, clip, tmp, force_style=None):
    """📹 Anuncio con un video del usuario (ej. Gemini): su clip abre (con su sonido) y el resto lo arma la IA alrededor."""
    dur = formatos.clip_duration(clip)
    cola = director.cola_muda(clip, dur)  # final mudo y quieto de Veo
    info = director.describir_clip(clip, dur, tmp, cola) or {}
    pant = info.get("pantalla") if isinstance(info.get("pantalla"), dict) and os.environ.get("CLIP_PANTALLA") == "1" else None  # pantalla mágica APAGADA (a Diego le pareció artificial)
    try:
        q = [[float(a) * 3, float(b) * 3] for a, b in pant["esquinas"]][:4] if pant else None  # 360x640 → 1080x1920
        if q and len(q) == 4 and (max(x for x, _ in q) - min(x for x, _ in q)) > 150 and (max(y for _, y in q) - min(y for _, y in q)) > 100: pant = {"q": q, "tipo": pant.get("tipo", "")}
        else: pant = None
    except Exception: pant = None
    if cola:
        if pant: pant["t"] = round(cola + 0.15, 2); dur = round(min(dur, cola + 2.3), 2)  # el producto real aparece en la pantalla durante el final quieto
        else: dur = round(max(4.0, cola + 0.6), 2)  # sin pantalla: se corta el final muerto
    else: pant = None
    extra = (f"Este reel EMPIEZA con un clip real ya grabado de {dur:.1f} segundos (con su propio sonido y diálogo): {info.get('que_pasa', 'una persona en una situación cotidiana')}. "
             f"Emoción: {info.get('emocion', '')}. Lo más fuerte pasa hacia el segundo {info.get('momento_clave', 1)}. NO escribas una escena para el clip. "
             "Agrega al JSON 'gancho_clip': {\"lineas\": [1-2 líneas de 1-3 palabras], \"t\": segundo en que aparece el texto (0 si debe frenar el scroll desde el inicio, o el momento clave si el clip ya engancha solo)}. "
             "Las escenas del JSON son las que van DESPUÉS del clip: 2-3 que muestren el producto como la solución a lo que pasó en el clip (la primera retoma la situación del clip), y al final 'precio'. "
             "No uses escenas de apertura (gancho, pov, chat, notificaciones, broll, meme).")
    try:
        story = brief_mod.make_storyboard(prod, B, titles, force_style=force_style, avoid=history(out)[-5:], extra=extra)
    except Exception as e:
        print("guion IA falló:", e); story = brief_mod.fallback_story(B, n_pages, force_style=force_style, seed=int(time.time()))
    rest = [e for e in story["escenas"] if e["tipo"] not in ("gancho", "pov", "chat", "notificaciones", "broll", "meme", "montaje")][:4]
    if not any(e["tipo"] in ("paginas", "zoom", "grid", "scroll", "pasos") for e in rest):
        rest.insert(0, {"tipo": "paginas", "paginas": list(range(min(4, n_pages))), "textos": (B.get("textos_paginas") or [""])[:4], "voz": ""})
    g = story.pop("gancho_clip", None) or {}
    ls = [l for l in (g.get("lineas") or []) if isinstance(l, dict) and l.get("palabras")] or B["gancho"][:2]
    for l in ls: l["palabras"] = [brief_mod.noemoji(w)[:14] for w in l["palabras"] if brief_mod.noemoji(w)][:3]
    try: t = max(0.0, min(dur - 1.5, float(g.get("t", 0))))
    except Exception: t = 0.0
    story["escenas"] = [{"tipo": "clip", "archivo": str(clip), "dur": dur, "voz": "", "gancho": {"lineas": ls[:2], "t": t, "dura": (pant["t"] - t) if pant else 99}, **({"pantalla": pant} if pant else {})}] + rest
    story["formato"] = "clip"; story["subtitulos"] = story.get("subtitulos", True)
    return story

def pick(v, g, story):
    """'ia' o vacío = lo que sugiere la IA para este reel."""
    v = v if v in ("f", "m", "0") else ("f" if story["voz"] == "femenina" else "m")
    g = g if g and g != "ia" else story["musica"]
    return v, g

def run_job(J):
    job, prod, opts = J["job"], J["product"], J["job"]["options"] or {}
    slug = prod["slug"]; out = PIXELIA / "storage" / "anuncios" / slug; out.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="estudio_")
    try:
        brief_file, guion_file, silent = out / "brief.json", out / "guion.json", out / "reel-mudo.mp4"
        cache = {}
        def load_pages():
            if "p" not in cache: cache["p"] = product_pages(prod, tmp)
            return cache["p"]
        if opts.get("n") == "1" or not brief_file.exists():
            pages, phone, titles = load_pages()
            say(f"🎨 Analizando <b>{esc(prod['title'])}</b>: público, colores y textos…")
            try: B = brief_mod.make_brief(prod, len(pages), titles)
            except Exception as e:
                print("brief IA falló:", e); B = brief_mod.normalize({}, prod, len(pages), titles)
            brief_file.write_text(json.dumps(B, ensure_ascii=False, indent=2))
        else:
            B = json.loads(brief_file.read_text())
            if "ganchos" not in B: B = brief_mod.normalize(B, prod, len(B.get("textos_paginas", [])) or 6)
        pro = opts.get("q") == "1"  # botón 🧠 Anuncio PRO (gasta más Claude); lo normal sigue como antes
        if pro and not B.get("investigacion") and os.environ.get("AD_RESEARCH", "1") != "0":
            say("🔎 Investigando en internet a quién le vende este producto y qué anuncios funcionan en su nicho (1 sola vez por producto)…")
            inv = director.investigar(prod, B)
            if inv:
                B["investigacion"] = inv; brief_file.write_text(json.dumps(B, ensure_ascii=False, indent=2)); say(director.resumen_investigacion(inv))
        if opts.get("x"): return run_variants(job, prod, B, out, tmp, load_pages, opts)
        audio_only = opts.get("a") == "1" and guion_file.exists() and silent.exists()
        if audio_only:
            G = json.loads(guion_file.read_text()); story, TL = G["story"], G["TL"]
        else:
            pages, phone, titles = load_pages()
            fs = opts.get("s") if opts.get("s") in motor.STYLE_NAMES else None
            ff = next_format(prod, B, brief_file, out) if opts.get("f") == "otro" else (opts.get("f") if opts.get("f") in brief_mod.FORMATOS else None)
            stock = opts.get("p") == "1"  # botón "📸 Crear con fotos y videos de Pixabay"
            say("📹 Armando el anuncio alrededor de tu video…" if opts.get("c") else "🧠 Anuncio PRO: 3 guiones, el director elige el mejor y al final reviso el video…" if pro else "📸 Creando con fotos y videos reales de Pixabay…" if stock else "✍️ La IA está eligiendo el formato y escribiendo el guion…")
            clip = PIXELIA / "storage" / "clips" / f"{opts.get('c')}.mp4" if opts.get("c") else None
            if clip is not None and not clip.exists(): raise RuntimeError("no encontré tu video; mándamelo otra vez al bot")
            story = clip_story(prod, B, titles, len(pages), out, clip, tmp, force_style=fs) if clip else new_story(prod, B, titles, len(pages), out, force_style=fs, force_format=ff, stock=stock, single=not pro)
            st = story["estilo"]; v, g = pick(opts.get("v"), opts.get("g"), story)
            say(f"🎬 <b>{esc(story.get('concepto') or 'Reel nuevo')}</b>\nFormato: {esc(FORMAT_NAMES.get(story.get('formato'), story.get('formato')))} · estilo {motor.STYLE_NAMES.get(st, st)}\nEscenas: {' → '.join(e['tipo'] for e in story['escenas'])}\nMontando (2–6 min)…")
            B2 = json.loads(json.dumps(B)); B2["estaticos"][0]["titular"] = hook_lines(story)
            for old in out.glob("[ABC]-*.jpg"): old.unlink()
            motor.build_static(B2, pages, phone, out, style=st, photo=clip_frame(story, tmp) if story["escenas"][0]["tipo"] == "clip" else real_photo(story) if stock else None)
            vd = None
            if v in ("f", "m"):
                try: vd = audio.voice_durations(story, "femenina" if v == "f" else "masculina", tmp)
                except Exception as e: print("voz previa falló:", e)
            TL = story_mod.build(B, story, pages, phone, silent, style=st, vdurs=vd)
            if pro and os.environ.get("AD_REVIEW", "1") != "0":
                say("🔍 Revisando el video antes de mandártelo…")
                fixed, probs = director.revisar(story, silent, TL, tmp, audio.ahorro())
                if fixed:
                    try:
                        s2 = brief_mod.normalize_story(fixed, B, len(pages), None, fs, story["formato"], stock)
                        if audio.ahorro() and [e["tipo"] for e in s2["escenas"]] == [e["tipo"] for e in story["escenas"]]:
                            for a, b in zip(s2["escenas"], story["escenas"]): a["voz"] = b.get("voz", "")  # en ahorro no se generan voces nuevas
                        for k in ("estilo", "musica", "voz", "letra", "animacion", "subtitulos", "copy", "concepto"): s2[k] = story.get(k, s2.get(k))
                        story = s2; vd = None
                        if v in ("f", "m"):
                            try: vd = audio.voice_durations(story, "femenina" if v == "f" else "masculina", tmp)
                            except Exception as e: print("voz previa falló:", e)
                        TL = story_mod.build(B, story, pages, phone, silent, style=st, vdurs=vd)
                        say("🔧 Corregí antes de enviarlo:\n" + "\n".join("• " + esc(p) for p in probs))
                    except Exception as e: print("no pude aplicar la corrección:", e)
                else: say("✅ Revisado: se entiende bien.")
            guion_file.write_text(json.dumps({"story": story, "TL": TL}, ensure_ascii=False, indent=1)); remember(out, story)
        st = story["estilo"]; v, g = pick(opts.get("v"), opts.get("g"), story)
        with_voice = v in ("f", "m")
        if with_voice: B["voz"]["genero"] = "femenina" if v == "f" else "masculina"
        wav = pathlib.Path(tmp) / "audio.wav"
        info = audio.mix(B, TL, wav, music_genre=g, with_voice=with_voice, tmpdir=tmp, story=story)
        final = out / f"reel-{st}_{VOZ_NAMES.get(v, 'sin voz').replace(' ', '-')}_{g}.mp4"; audio.mux(silent, wav, final)
        wav0 = pathlib.Path(tmp) / "audio0.wav"; audio.mix(B, TL, wav0, music_genre="0", with_voice=with_voice, tmpdir=tmp, story=story)
        audio.mux(silent, wav0, out / "reel-sin-musica-para-meta.mp4")
        deliver(prod, B, out, final, v, g, st, info, story, send_images=not audio_only)
        sug = {"v": "f" if story["voz"] == "femenina" else "m", "g": story["musica"], "s": "ia"}
        api("POST", f"/api/studio/jobs/{job['id']}", {"status": "done", "result": {"dir": str(out), "reel": final.name, "product_id": prod["id"],
            "sel": {"v": opts.get("v") or "ia", "g": opts.get("g") or "ia", "s": opts.get("s") or "ia"}, "sug": sug}})
        auto_scout(g)
    except Exception as e:
        traceback.print_exc()
        api("POST", f"/api/studio/jobs/{job['id']}", {"status": "error", "error": str(e)})
        say(f"⚠️ No pude crear los anuncios de <b>{esc(prod.get('title'))}</b>:\n{esc(e)}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def run_variants(job, prod, B, out, tmp, load_pages, opts):
    """4 reels con guiones, estilos y aperturas distintos para probar en Meta cuál vende más."""
    pages, phone, titles = load_pages(); vdir = out / "variantes"; shutil.rmtree(vdir, ignore_errors=True); vdir.mkdir()
    reels, imgs, meta, made = [], [], [], []
    formats = ranked_formats(prod, B, out / "brief.json")[:4]
    say("🧪 Formatos elegidos por la IA para este público: " + ", ".join(FORMAT_NAMES.get(f, f) for f in formats))
    for k, fmt in enumerate(formats):
        name = f"V{k + 1}"
        say(f"🧪 {name}/4 · formato {FORMAT_NAMES.get(fmt, fmt)}: escribiendo guion…")
        story = new_story(prod, B, titles, len(pages), out, force_format=fmt, single=True,
                          extra_avoid=[{"concepto": m.get("concepto"), "orden": [e["tipo"] for e in m["escenas"]]} for m in made], seed=k + 1)
        used = [m["estilo"] for m in made]
        if story["estilo"] in used:  # que cada variante también se vea distinta
            story["estilo"] = next((x for x in motor.STYLE_NAMES if x not in used), story["estilo"])
        made.append(story); remember(out, story); st = story["estilo"]
        v, g = pick(opts.get("v"), opts.get("g"), story)
        B2 = json.loads(json.dumps(B)); B2["voz"]["genero"] = "femenina" if v == "f" else "masculina"
        est = B2["estaticos"][k % 3]; est["titular"] = hook_lines(story)
        motor.build_static(B2, pages, phone, vdir, style=st, prefix=name, only=[k % 3])
        vd = None
        if v in ("f", "m"):
            try: vd = audio.voice_durations(story, B2["voz"]["genero"], tmp)
            except Exception as e: print("voz previa falló:", e)
        silent = pathlib.Path(tmp) / f"{name}.mp4"; TL = story_mod.build(B2, story, pages, phone, silent, style=st, seed=7 + k, vdurs=vd)
        wav = pathlib.Path(tmp) / f"{name}.wav"
        info = audio.mix(B2, TL, wav, music_genre=g, with_voice=v in ("f", "m"), tmpdir=tmp, seed=k, story=story)
        reel = vdir / f"{name}-reel.mp4"; audio.mux(silent, wav, reel)
        reels.append(reel); imgs.append(vdir / f"{name}-4x5.jpg")
        meta.append({"nombre": name, "estilo": FORMAT_NAMES.get(fmt, fmt) + " · " + motor.STYLE_NAMES[st], "tipo": fmt, "gancho": story.get("concepto", ""),
                     "texto": (story.get("copy") or {}).get("texto", ""), "titular": (story.get("copy") or {}).get("titular", ""),
                     "musica": info["musica"], "escenas": " → ".join(e["tipo"] for e in story["escenas"])})
    media = [{"type": "photo", "media": f"attach://i{k}", "caption": f"{m['nombre']} · {m['estilo']}"} for k, m in enumerate(meta)]
    tg("sendMediaGroup", {"chat_id": CHAT, "media": media}, {f"i{k}": p for k, p in enumerate(imgs)})
    vids = [{"type": "video", "media": f"attach://v{k}", "caption": f"{m['nombre']} · {m['estilo']} · {m['escenas']}", "supports_streaming": True} for k, m in enumerate(meta)]
    tg("sendMediaGroup", {"chat_id": CHAT, "media": vids}, {f"v{k}": p for k, p in enumerate(reels)})
    zpath = out / f"variantes-{prod['slug'][:30]}.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for p in sorted(vdir.glob("*")): z.write(p, p.name)
        z.writestr("TEXTOS-Y-PLAN-DE-PRUEBA.txt", variants_text(prod, B, meta))
    tg("sendDocument", {"chat_id": CHAT, "caption": "📦 Las 4 variantes (imágenes 1:1, 4:5, 9:16 + reels) con textos y plan de prueba"}, {"document": zpath})
    say(f"🧪 <b>4 variantes de {esc(prod['title'])} listas</b>\n" + "\n".join(f"• <b>{m['nombre']}</b>: {esc(m['estilo'])} — {esc(m['gancho'])}" for m in meta) +
        f"\n\n📋 <b>Cómo probarlas en Meta</b>\n1. Una campaña de Ventas con 1 conjunto de anuncios y los 4 anuncios dentro.\n2. Nómbralos <code>[{esc(prod['slug'])}] V1</code> … <code>V4</code>.\n3. 3-4 días sin tocar nada. Luego apaga los 2 con el costo por clic (CPC) más alto y deja los otros.\n4. El que consiga ventas más baratas es el ganador: de ese hacemos más versiones.")
    api("POST", f"/api/studio/jobs/{job['id']}", {"status": "done", "result": {"dir": str(vdir), "variantes": [m["nombre"] for m in meta], "product_id": prod["id"],
        "sel": {"v": opts.get("v") or "ia", "g": opts.get("g") or "ia", "s": "ia"}, "sug": {"v": "ia", "g": "ia", "s": "ia"}}})

def variants_text(prod, B, meta):
    L = [f"VARIANTES PARA PROBAR · {prod['title']}", f"Enlace: https://{prod.get('dominio', 'pixeliadigital.app')}/p/{prod['slug']}",
         f"Público: {B.get('publico', '')}", f"Países: {', '.join(B.get('paises', []))} · Edad: {B.get('edad', '')}", ""]
    for m in meta:
        L += [f"=== {m['nombre']} · nombre en Meta: [{prod['slug']}] {m['nombre']} ===", f"Estilo: {m['estilo']} · Gancho ({m['tipo']}): {m['gancho']}",
              f"Música: {m['musica']}", "Texto principal:", m["texto"], f"Titular: {m['titular']}", ""]
    L += ["PLAN DE PRUEBA", "- 1 campaña de Ventas, 1 conjunto (Advantage+ o los países de arriba), los 4 anuncios dentro.",
          "- Presupuesto del conjunto: el que tengas para el producto (ej. 3-5 $/día).",
          "- No cambies nada durante 3-4 días (Meta necesita aprender).",
          "- Día 4: apaga los 2 con CPC más alto o CTR más bajo. Día 7: quédate con el de menor costo por compra.",
          "- Pide al bot nuevas variantes del ganador (mismo gancho, otro estilo o música)."]
    return "\n".join(L)

def deliver(prod, B, out, reel, v, g, st, info, story=None, send_images=True):
    if send_images:
        imgs = [out / f"{c}-4x5.jpg" for c in "ABC"]
        media = [{"type": "photo", "media": f"attach://i{k}"} for k in range(3)]
        media[0]["caption"] = f"🖼️ {esc(prod['title'])} · estilo {motor.STYLE_NAMES.get(st, st)} · 3 enfoques (también 1:1 y 9:16 en el ZIP)"
        tg("sendMediaGroup", {"chat_id": CHAT, "media": media}, {f"i{k}": p for k, p in enumerate(imgs)})
    tg("sendVideo", {"chat_id": CHAT, "caption": f"🎬 Reel · {motor.STYLE_NAMES.get(st, st)} · {VOZ_NAMES.get(v, v)} · {GEN_NAMES.get(g, g)}\n🎵 {info.get('musica', '')}" + (f"\n⚠️ La voz falló: {info['voz'][7:120]}" if str(info.get('voz', '')).startswith('error') else ""),
                     "supports_streaming": "true"}, {"video": reel})
    zpath = out / f"anuncios-{prod['slug'][:30]}.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for p in sorted(out.glob("[ABC]-*.jpg")): z.write(p, p.name)
        z.write(reel, reel.name)
        if (out / "reel-sin-musica-para-meta.mp4").exists(): z.write(out / "reel-sin-musica-para-meta.mp4", "reel-sin-musica-para-meta.mp4")
        credit = musica.credits_for(info.get("archivo", ""))
        z.writestr("TEXTOS-ANUNCIO.txt", reel_text(prod, story) + copy_text(prod, B) + META_MUSIC + (f"\n\nCRÉDITO DE LA MÚSICA (ponlo al final del texto principal):\nMúsica: {credit}" if credit else ""))
    tg("sendDocument", {"chat_id": CHAT, "caption": "📦 Todo junto: imágenes, reel y textos para Meta"}, {"document": zpath})
    sug_g = B["musica"]["genero"]
    say(f"✅ <b>Anuncios de {esc(prod['title'])}</b>\n👥 Público: {esc(B.get('publico'))}\n🌎 Países: {esc(', '.join(B.get('paises', [])))} · Edad {esc(B.get('edad', ''))}\n"
        f"🎙️ Voz sugerida: {esc(B['voz']['genero'])} — {esc(B['voz'].get('por_que', ''))}\n🎵 Ritmo sugerido: {esc(GEN_NAMES.get(sug_g, sug_g))} — {esc(B['musica'].get('por_que', ''))}\n"
        f"🎨 Estilo de este reel: {esc(motor.STYLE_NAMES.get(st, st))}\n"
        + (f"\n🎬 Idea del reel: {esc(story.get('concepto', ''))}" if story else "") +
        f"\nNombra los anuncios en Meta: <code>[{esc(prod['slug'])}] A</code> / B / C / reel")

META_MUSIC = """

MÚSICA DE META (opcional, automática)
El archivo reel-sin-musica-para-meta.mp4 trae voz y efectos pero NO música. Al subirlo en el Administrador de anuncios,
marca "Agregar música" → "Aplicar música automáticamente": Meta elige una canción real de su biblioteca libre de derechos.
OJO: con tus otros reels (que ya traen música) DESACTIVA "Agregar música" en las mejoras de Advantage+, o Meta pondrá otra canción encima."""

def reel_text(prod, story):
    if not story: return ""
    c = story.get("copy") or {}
    return "\n".join([f"=== REEL · nombre en Meta: [{prod['slug']}] reel ===", f"Idea: {story.get('concepto', '')}",
                      "Escenas: " + " → ".join(e["tipo"] for e in story["escenas"]), "Guion de voz: " + " / ".join(e.get("voz", "") for e in story["escenas"] if e.get("voz")),
                      "Texto principal:", c.get("texto", ""), f"Titular: {c.get('titular', '')}", f"Descripción: {c.get('descripcion', '')}", "", ""])

def copy_text(prod, B):
    lines = [f"ANUNCIOS · {prod['title']}", f"Enlace: https://{prod.get('dominio', 'pixeliadigital.app')}/p/{prod['slug']}", "",
             f"Público: {B.get('publico', '')}", f"Países: {', '.join(B.get('paises', []))} · Edad: {B.get('edad', '')}", ""]
    for k in "ABC":
        c = (B.get("copy") or {}).get(k) or {}
        lines += [f"=== Enfoque {k} (imágenes {k}-*) · nombre en Meta: [{prod['slug']}] {k} ===", "Texto principal:", c.get("texto", ""),
                  f"Titular: {c.get('titular', '')}", f"Descripción: {c.get('descripcion', '')}", ""]
    lines += ["Reel: usa el texto del enfoque A · nombre en Meta: [" + prod["slug"] + "] reel", "",
              "Añade al final del texto principal: 💳 Paga con " + ", ".join(motor.PAGOS) + " · ⚡ Descarga inmediata"]
    return "\n".join(lines)

def auto_scout(g, force=False):
    """Si el género tiene menos de 3 canciones reales, busca y sugiere (máx. una vez al día por género)."""
    if g in (None, "", "0") or (os.environ.get("ELEVENLABS_API_KEY") and not force): return  # con ElevenLabs la música se crea sola
    if not force and len(audio.library(g)) >= 3: return
    f = audio.MUSIC_DIR / "ultima_busqueda.json"; last = musica.load(f, {})
    if not force and time.time() - last.get(g, 0) < 86400: return
    last[g] = time.time(); f.parent.mkdir(parents=True, exist_ok=True); f.write_text(json.dumps(last))
    try:
        say(f"🔎 Buscando canciones reales y libres de derechos de <b>{esc(GEN_NAMES.get(g, g))}</b> para tus anuncios…")
        n = musica.scout(g, tg, CHAT)
        say(f"🎧 Escucha las {n} sugerencias y toca ✅ las que te gusten." if n else
            f"No encontré canciones nuevas de {esc(GEN_NAMES.get(g, g))} con licencia comercial. Mientras tanto uso el ritmo sintetizado; también puedes enviarme un MP3 con el género en el pie.")
    except Exception as e:
        traceback.print_exc(); say(f"⚠️ La búsqueda de música falló: {esc(e)}")

def main():
    print("🎬 Estudio de anuncios esperando trabajos…", flush=True)
    while True:
        try:
            J = api("POST", "/api/studio/next", {})
            if J: print("Trabajo", J["job"], J["product"]["slug"], flush=True); run_job(J); continue
            for g in musica.pending_requests(): auto_scout(g, force=True)
        except Exception as e:
            print("Error de conexión con la tienda:", e, flush=True)
        time.sleep(10)

if __name__ == "__main__":
    main()
