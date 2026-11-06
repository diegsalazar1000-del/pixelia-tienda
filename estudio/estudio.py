"""Trabajador del estudio de anuncios. Corre en su propio contenedor (pixelia-estudio) en el VPS.
Pide trabajos a la tienda, genera imágenes + reel con audio y los envía al bot del radar en Telegram.
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile, time, traceback, urllib.request, uuid, zipfile
from PIL import Image

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import motor, audio, brief as brief_mod  # noqa: E402

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
GEN_NAMES = {"reggaeton": "Reggaetón", "pop": "Pop", "electronica": "Electrónica", "lofi": "Lo-fi", "acustica": "Acústica", "base": "Suave"}

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
def run_job(J):
    job, prod, opts = J["job"], J["product"], J["job"]["options"] or {}
    slug = prod["slug"]; out = PIXELIA / "storage" / "anuncios" / slug; out.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="estudio_")
    try:
        brief_file, reel_silent, tl_file = out / "brief.json", out / "reel-mudo.mp4", out / "timeline.json"
        reuse = brief_file.exists() and reel_silent.exists() and tl_file.exists() and opts.get("n") != "1" and ("v" in opts or "g" in opts)
        if reuse:
            B = json.loads(brief_file.read_text()); TL = json.loads(tl_file.read_text())
        else:
            pages, phone, titles = product_pages(prod, tmp)
            say(f"🎨 Analizando <b>{esc(prod['title'])}</b> y escribiendo los textos…")
            try: B = brief_mod.make_brief(prod, len(pages), titles)
            except Exception as e:
                print("brief IA falló:", e); B = brief_mod.normalize({}, prod, len(pages), titles)
            brief_file.write_text(json.dumps(B, ensure_ascii=False, indent=2))
            for old in out.glob("*.jpg"): old.unlink()
            motor.build_static(B, pages, phone, out)
            say("🎬 Imágenes listas. Montando el reel (2–6 min)…")
            TL = motor.build_reel(B, pages, phone, reel_silent)
            tl_file.write_text(json.dumps(TL))
        # audio según opciones: v = f/m/0 (voz), g = género musical
        v = opts.get("v", "0"); g = opts.get("g") or "base"
        with_voice = v in ("f", "m")
        if with_voice: B["voz"]["genero"] = "femenina" if v == "f" else "masculina"
        wav = pathlib.Path(tmp) / "audio.wav"
        audio.mix(B, TL, wav, music_genre=None if g == "base" else g, with_voice=with_voice, tmpdir=tmp)
        tag = f"{'voz-' + v if with_voice else 'sin-voz'}_{g}"
        final = out / f"reel-{tag}.mp4"; audio.mux(reel_silent, wav, final)
        deliver(prod, B, out, final, v, g, reuse)
        api("POST", f"/api/studio/jobs/{job['id']}", {"status": "done", "result": {"dir": str(out), "reel": final.name, "brief": B.get("publico")}})
    except Exception as e:
        traceback.print_exc()
        api("POST", f"/api/studio/jobs/{job['id']}", {"status": "error", "error": str(e)})
        say(f"⚠️ No pude crear los anuncios de <b>{esc(prod.get('title'))}</b>:\n{esc(e)}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def deliver(prod, B, out, reel, v, g, only_audio):
    pid = prod["id"]; sug_v = "f" if B["voz"]["genero"] == "femenina" else "m"; sug_g = B["musica"]["genero"]
    if not only_audio:
        imgs = [out / f"{c}-4x5.jpg" for c in "ABC"]
        media = [{"type": "photo", "media": f"attach://i{k}"} for k in range(3)]
        media[0]["caption"] = f"🖼️ {esc(prod['title'])} · 3 enfoques (también en 1:1 y 9:16 en el ZIP)"
        tg("sendMediaGroup", {"chat_id": CHAT, "media": media}, {f"i{k}": p for k, p in enumerate(imgs)})
    voz_txt = "sin voz" if v not in ("f", "m") else ("voz femenina" if v == "f" else "voz masculina")
    tg("sendVideo", {"chat_id": CHAT, "caption": f"🎬 Reel · {voz_txt} · ritmo {GEN_NAMES.get(g, g)}", "supports_streaming": "true"}, {"video": reel})
    # paquete completo
    zpath = out / f"anuncios-{prod['slug'][:30]}.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for p in sorted(out.glob("*.jpg")): z.write(p, p.name)
        z.write(reel, reel.name)
        z.writestr("TEXTOS-ANUNCIO.txt", copy_text(prod, B))
    tg("sendDocument", {"chat_id": CHAT, "caption": "📦 Todo junto: imágenes, reel y textos para Meta"}, {"document": zpath})
    def keep(**kw):  # conserva las opciones actuales y cambia solo la indicada
        o = {"v": v or "0", "g": g or "base", **kw}
        return ",".join(f"{k}={x}" for k, x in o.items() if x not in (None, ""))
    kb = [
        [{"text": f"🎙️ Voz sugerida ({'femenina' if sug_v == 'f' else 'masculina'})", "callback_data": f"ad:{pid}:{keep(v=sug_v)}"},
         {"text": "🔇 Sin voz", "callback_data": f"ad:{pid}:{keep(v='0')}"}],
        [{"text": "👩 Voz femenina", "callback_data": f"ad:{pid}:{keep(v='f')}"}, {"text": "👨 Voz masculina", "callback_data": f"ad:{pid}:{keep(v='m')}"}],
        [{"text": f"🎵 Ritmo sugerido: {GEN_NAMES.get(sug_g, sug_g)}", "callback_data": f"ad:{pid}:{keep(g=sug_g)}"}],
        [{"text": GEN_NAMES[x], "callback_data": f"ad:{pid}:{keep(g=x)}"} for x in ("reggaeton", "pop", "electronica")],
        [{"text": GEN_NAMES[x], "callback_data": f"ad:{pid}:{keep(g=x)}"} for x in ("lofi", "acustica", "base")],
        [{"text": "🔁 Textos y diseño nuevos", "callback_data": f"ad:{pid}:{keep(n='1')}"}],
    ]
    say(f"✅ <b>Anuncios de {esc(prod['title'])}</b>\n👥 Público: {esc(B.get('publico'))}\n🌎 Países: {esc(', '.join(B.get('paises', [])))} · Edad {esc(B.get('edad', ''))}\n"
        f"🎙️ Voz sugerida: {esc(B['voz']['genero'])} — {esc(B['voz'].get('por_que', ''))}\n🎵 Ritmo sugerido: {esc(GEN_NAMES.get(sug_g, sug_g))} — {esc(B['musica'].get('por_que', ''))}\n\n"
        f"Nombra los anuncios en Meta: <code>[{esc(prod['slug'])}] A</code> / B / C / reel\nCambia lo que quieras 👇", kb)

def copy_text(prod, B):
    lines = [f"ANUNCIOS · {prod['title']}", f"Enlace: https://{prod.get('dominio', 'pixeliadigital.app')}/p/{prod['slug']}", "",
             f"Público: {B.get('publico', '')}", f"Países: {', '.join(B.get('paises', []))} · Edad: {B.get('edad', '')}", ""]
    for k in "ABC":
        c = (B.get("copy") or {}).get(k) or {}
        lines += [f"=== Enfoque {k} (imágenes {k}-*) · nombre en Meta: [{prod['slug']}] {k} ===", "Texto principal:", c.get("texto", ""),
                  f"Titular: {c.get('titular', '')}", f"Descripción: {c.get('descripcion', '')}", ""]
    lines += ["Reel: usa el texto del enfoque A · nombre en Meta: [" + prod["slug"] + "] reel"]
    return "\n".join(lines)

def main():
    print("🎬 Estudio de anuncios esperando trabajos…", flush=True)
    while True:
        try:
            J = api("POST", "/api/studio/next", {})
            if J: print("Trabajo", J["job"], J["product"]["slug"], flush=True); run_job(J); continue
        except Exception as e:
            print("Error de conexión con la tienda:", e, flush=True)
        time.sleep(10)

if __name__ == "__main__":
    main()
