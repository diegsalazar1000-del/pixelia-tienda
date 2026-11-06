"""Trabajador del estudio de anuncios. Corre en su propio contenedor (pixelia-estudio) en el VPS.
Pide trabajos a la tienda, genera imágenes + reel con audio y los envía al bot del radar en Telegram.
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile, time, traceback, urllib.request, uuid, zipfile
from PIL import Image

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import motor, audio, musica, brief as brief_mod  # noqa: E402

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
GEN_NAMES = {"reggaeton": "Reggaetón", "pop": "Pop", "trap": "Trap", "cumbia": "Cumbia", "electronica": "Electrónica", "lofi": "Lo-fi", "acustica": "Acústica", "base": "Suave", "0": "sin música"}
VOZ_NAMES = {"f": "voz femenina", "m": "voz masculina", "0": "sin voz"}
# 4 variantes para A/B en Meta: (estilo, tipo de gancho)
VARIANTES = [("color", "problema"), ("tiktok", "curiosidad"), ("neon", "oferta"), ("minimal", "pov")]

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
def with_hook(B, tipo):
    """Copia del brief con el gancho (texto en pantalla + voz) del tipo indicado."""
    B2 = json.loads(json.dumps(B)); h = next((g for g in B.get("ganchos", []) if g.get("tipo") == tipo), None)
    if h:
        B2["gancho"] = h["lineas"]
        if h.get("voz"): B2.setdefault("guion_voz", {})["gancho"] = h["voz"]
    return B2, h or {}

def run_job(J):
    job, prod, opts = J["job"], J["product"], J["job"]["options"] or {}
    slug = prod["slug"]; out = PIXELIA / "storage" / "anuncios" / slug; out.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="estudio_")
    try:
        brief_file, tl_file = out / "brief.json", out / "timeline.json"
        new_brief = opts.get("n") == "1" or not brief_file.exists()
        pages = phone = None
        def load_pages():
            nonlocal pages, phone
            if pages is None: pages, phone, _ = product_pages(prod, tmp)
            return pages, phone
        if new_brief:
            pages, phone, titles = product_pages(prod, tmp)
            say(f"🎨 Analizando <b>{esc(prod['title'])}</b> y escribiendo los textos…")
            try: B = brief_mod.make_brief(prod, len(pages), titles)
            except Exception as e:
                print("brief IA falló:", e); B = brief_mod.normalize({}, prod, len(pages), titles)
            brief_file.write_text(json.dumps(B, ensure_ascii=False, indent=2))
            for old in list(out.glob("reel-mudo*.mp4")) + list(out.glob("*.jpg")): old.unlink()
        else:
            B = json.loads(brief_file.read_text())
            if "ganchos" not in B: B = brief_mod.normalize(B, prod, len(B.get("textos_paginas", [])) or 6)
        sug = {"v": "f" if B["voz"]["genero"] == "femenina" else "m", "g": B["musica"]["genero"], "s": B.get("estilo", {}).get("sugerido", "color")}
        # primera vez: voz y música sugeridas por la IA, estilo "color" (la base que ya te gustó)
        v = opts.get("v") or sug["v"]; g = opts.get("g") or sug["g"]; st = opts.get("s") or "color"
        sel = {"v": v, "g": g, "s": st}
        if opts.get("x"): return run_variants(job, prod, B, out, tmp, load_pages, v, g, sug)
        silent = out / f"reel-mudo-{st}.mp4"
        if not silent.exists() or not tl_file.exists():
            pg, ph = load_pages()
            say(f"🎬 Montando el reel · estilo {motor.STYLE_NAMES.get(st, st)} (2–6 min)…")
            for old in out.glob("[ABC]-*.jpg"): old.unlink()
            motor.build_static(B, pg, ph, out, style=st)
            TL = motor.build_reel(B, pg, ph, silent, style=st); tl_file.write_text(json.dumps(TL)); new_visual = True
        else:
            TL = json.loads(tl_file.read_text())
            prev = (out / "estilo.txt").read_text() if (out / "estilo.txt").exists() else ""
            new_visual = prev != st or not (out / "A-4x5.jpg").exists()
            if new_visual:
                pg, ph = load_pages(); motor.build_static(B, pg, ph, out, style=st)
        (out / "estilo.txt").write_text(st)
        with_voice = v in ("f", "m")
        if with_voice: B["voz"]["genero"] = "femenina" if v == "f" else "masculina"
        wav = pathlib.Path(tmp) / "audio.wav"
        info = audio.mix(B, TL, wav, music_genre=g, with_voice=with_voice, tmpdir=tmp)
        final = out / f"reel-{st}_{VOZ_NAMES.get(v, 'sin voz').replace(' ', '-')}_{g}.mp4"; audio.mux(silent, wav, final)
        # versión sin música (voz + efectos) para que Meta le ponga música de su biblioteca libre de derechos
        wav0 = pathlib.Path(tmp) / "audio0.wav"; audio.mix(B, TL, wav0, music_genre="0", with_voice=with_voice, tmpdir=tmp)
        audio.mux(silent, wav0, out / "reel-sin-musica-para-meta.mp4")
        deliver(prod, B, out, final, v, g, st, info, send_images=new_visual or new_brief)
        api("POST", f"/api/studio/jobs/{job['id']}", {"status": "done", "result": {"dir": str(out), "reel": final.name, "product_id": prod["id"], "sel": sel, "sug": sug}})
        auto_scout(g)
    except Exception as e:
        traceback.print_exc()
        api("POST", f"/api/studio/jobs/{job['id']}", {"status": "error", "error": str(e)})
        say(f"⚠️ No pude crear los anuncios de <b>{esc(prod.get('title'))}</b>:\n{esc(e)}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def run_variants(job, prod, B, out, tmp, load_pages, v, g, sug):
    """4 anuncios distintos (estilo + gancho) para probar en Meta cuál vende más."""
    pages, phone = load_pages(); vdir = out / "variantes"; shutil.rmtree(vdir, ignore_errors=True); vdir.mkdir()
    with_voice = v in ("f", "m")
    if with_voice: B["voz"]["genero"] = "femenina" if v == "f" else "masculina"
    reels, imgs, meta = [], [], []
    for k, (st, tipo) in enumerate(VARIANTES):
        name = f"V{k + 1}"; B2, h = with_hook(B, tipo)
        est = B2["estaticos"][k % 3]; est["titular"] = B2["gancho"]
        say(f"🧪 {name}/4 · {motor.STYLE_NAMES[st]} · gancho {tipo}…")
        motor.build_static(B2, pages, phone, vdir, style=st, prefix=name, only=[k % 3])
        silent = pathlib.Path(tmp) / f"{name}.mp4"; TL = motor.build_reel(B2, pages, phone, silent, style=st, seed=7 + k)
        wav = pathlib.Path(tmp) / f"{name}.wav"
        info = audio.mix(B2, TL, wav, music_genre=g, with_voice=with_voice, tmpdir=tmp, seed=k)
        reel = vdir / f"{name}-reel.mp4"; audio.mux(silent, wav, reel)
        reels.append(reel); imgs.append(vdir / f"{name}-4x5.jpg")
        meta.append({"nombre": name, "estilo": motor.STYLE_NAMES[st], "tipo": tipo, "gancho": " ".join(" ".join(l["palabras"]) for l in B2["gancho"]),
                     "texto": h.get("texto", ""), "titular": h.get("titular", ""), "musica": info["musica"]})
    media = [{"type": "photo", "media": f"attach://i{k}", "caption": f"{m['nombre']} · {m['estilo']} · {m['tipo']}"} for k, m in enumerate(meta)]
    tg("sendMediaGroup", {"chat_id": CHAT, "media": media}, {f"i{k}": p for k, p in enumerate(imgs)})
    vids = [{"type": "video", "media": f"attach://v{k}", "caption": f"{m['nombre']} · {m['estilo']} · gancho {m['tipo']}", "supports_streaming": True} for k, m in enumerate(meta)]
    tg("sendMediaGroup", {"chat_id": CHAT, "media": vids}, {f"v{k}": p for k, p in enumerate(reels)})
    zpath = out / f"variantes-{prod['slug'][:30]}.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for p in sorted(vdir.glob("*")): z.write(p, p.name)
        z.writestr("TEXTOS-Y-PLAN-DE-PRUEBA.txt", variants_text(prod, B, meta))
    tg("sendDocument", {"chat_id": CHAT, "caption": "📦 Las 4 variantes (imágenes 1:1, 4:5, 9:16 + reels) con textos y plan de prueba"}, {"document": zpath})
    say(f"🧪 <b>4 variantes de {esc(prod['title'])} listas</b>\n" + "\n".join(f"• <b>{m['nombre']}</b>: {esc(m['estilo'])} · gancho {m['tipo']} — «{esc(m['gancho'])}»" for m in meta) +
        f"\n\n📋 <b>Cómo probarlas en Meta</b>\n1. Una campaña de Ventas con 1 conjunto de anuncios y los 4 anuncios dentro.\n2. Nómbralos <code>[{esc(prod['slug'])}] V1</code> … <code>V4</code>.\n3. 3-4 días sin tocar nada. Luego apaga los 2 con el costo por clic (CPC) más alto y deja los otros.\n4. El que consiga ventas más baratas es el ganador: de ese hacemos más versiones.")
    api("POST", f"/api/studio/jobs/{job['id']}", {"status": "done", "result": {"dir": str(vdir), "variantes": [m["nombre"] for m in meta], "product_id": prod["id"], "sel": {"v": v, "g": g, "s": "color"}, "sug": sug}})

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

def deliver(prod, B, out, reel, v, g, st, info, send_images=True):
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
        z.writestr("TEXTOS-ANUNCIO.txt", copy_text(prod, B) + META_MUSIC + (f"\n\nCRÉDITO DE LA MÚSICA (ponlo al final del texto principal):\nMúsica: {credit}" if credit else ""))
    tg("sendDocument", {"chat_id": CHAT, "caption": "📦 Todo junto: imágenes, reel y textos para Meta"}, {"document": zpath})
    sug_g = B["musica"]["genero"]
    say(f"✅ <b>Anuncios de {esc(prod['title'])}</b>\n👥 Público: {esc(B.get('publico'))}\n🌎 Países: {esc(', '.join(B.get('paises', [])))} · Edad {esc(B.get('edad', ''))}\n"
        f"🎙️ Voz sugerida: {esc(B['voz']['genero'])} — {esc(B['voz'].get('por_que', ''))}\n🎵 Ritmo sugerido: {esc(GEN_NAMES.get(sug_g, sug_g))} — {esc(B['musica'].get('por_que', ''))}\n"
        f"🎨 Estilo sugerido: {esc(motor.STYLE_NAMES.get(B.get('estilo', {}).get('sugerido', 'color')))} — {esc(B.get('estilo', {}).get('por_que', ''))}\n\n"
        f"Nombra los anuncios en Meta: <code>[{esc(prod['slug'])}] A</code> / B / C / reel")

META_MUSIC = """

MÚSICA DE META (opcional, automática)
El archivo reel-sin-musica-para-meta.mp4 trae voz y efectos pero NO música. Al subirlo en el Administrador de anuncios,
marca "Agregar música" → "Aplicar música automáticamente": Meta elige una canción real de su biblioteca libre de derechos.
OJO: con tus otros reels (que ya traen música) DESACTIVA "Agregar música" en las mejoras de Advantage+, o Meta pondrá otra canción encima."""

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
