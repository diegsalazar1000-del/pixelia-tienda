"""Buscador automático de música REAL y legal para los anuncios.
Busca en Openverse (catálogo Creative Commons: Jamendo, Freesound, Wikimedia) canciones que permiten uso comercial,
recorta el coro y te las manda al bot para que solo digas ✅ o ❌. Las aprobadas pasan a storage/musica/<género>/.
"""
import json, os, pathlib, subprocess, tempfile, time, urllib.parse, urllib.request, uuid
import numpy as np
import audio

API = "https://api.openverse.org/v1/audio/"
UA = {"User-Agent": "PixeliaEstudio/1.0 (anuncios de una tienda pequeña)"}
# palabras de búsqueda por género (en inglés y español: el catálogo es internacional)
TERMS = {
    "reggaeton": ["reggaeton", "dembow", "latin urban", "moombahton"],
    "cumbia": ["cumbia", "latin cumbia", "tropical latin"],
    "trap": ["trap beat", "trap", "hip hop beat"],
    "pop": ["upbeat pop", "dance pop", "pop"],
    "electronica": ["upbeat electronic", "house", "edm"],
    "lofi": ["lofi", "chillhop", "lo-fi hip hop"],
    "acustica": ["acoustic guitar upbeat", "acoustic happy", "ukulele"],
    "base": ["upbeat background", "happy upbeat", "positive"],
}
# solo licencias que permiten uso comercial Y mezclar con voz (sin NC ni ND); primero las que no piden crédito
LIC_ORDER = {"cc0": 0, "pdm": 0, "by": 1, "by-sa": 2}

def root(): return audio.MUSIC_DIR
def state_file(): return root() / "vistos.json"
def credits_file(): return root() / "creditos.json"

def load(p, default):
    try: return json.loads(p.read_text())
    except Exception: return default

def search(genre, want=3):
    seen = set(load(state_file(), []))
    found = []
    for q in TERMS.get(genre, [genre]):
        params = {"q": q, "license_type": "commercial", "license": "cc0,pdm,by,by-sa", "category": "music", "page_size": 20}
        req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=30) as r: data = json.load(r)
        except Exception as e:
            print("openverse:", e); continue
        for it in data.get("results", []):
            dur = (it.get("duration") or 0) / 1000
            if it["id"] in seen or not it.get("url") or not (45 <= dur <= 420): continue
            if (it.get("license") or "").lower() not in LIC_ORDER: continue
            found.append(it); seen.add(it["id"])
        if len(found) >= want * 3: break
    found.sort(key=lambda it: (LIC_ORDER.get(it["license"].lower(), 9), -(it.get("rating") or 0)))
    return found

def preview(path, out_mp3, seconds=25):
    """Recorta la parte más movida (coro) para escucharla en Telegram."""
    x = audio.decode(path); n = int(seconds * audio.SR)
    if len(x) > n:
        hop = audio.SR // 2; e = x[: len(x) // hop * hop].reshape(-1, hop).std(axis=1)
        e = np.convolve(e, np.ones(n // hop), "valid"); lo = int(len(e) * 0.12)
        k = lo + int(np.argmax(e[lo:])) if len(e) > lo else 0; x = x[k * hop: k * hop + n]
    raw = (np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(audio.SR), "-ac", "1", "-i", "-", "-b:a", "128k", str(out_mp3)],
                   input=raw, check=True)

def credit_line(it):
    lic = (it.get("license") or "").upper().replace("PDM", "Dominio público").replace("CC0", "CC0 (dominio público)")
    return f"{it.get('title', '')} — {it.get('creator', '')} ({lic} {it.get('license_version') or ''}) {it.get('foreign_landing_url') or ''}".strip()

def scout(genre, tg, chat, want=3):
    """Busca, descarga y manda al bot hasta `want` canciones nuevas del género con botones ✅/❌."""
    pend = root() / "pendientes"; pend.mkdir(parents=True, exist_ok=True)
    items = search(genre, want); sent = 0
    seen = load(state_file(), [])
    for it in items:
        if sent >= want: break
        seen.append(it["id"])
        try:
            tok = uuid.uuid4().hex[:10]; ext = pathlib.Path(urllib.parse.urlparse(it["url"]).path).suffix.lower() or ".mp3"
            if ext not in audio.AUDIO_EXT: ext = ".mp3"
            full = pend / f"{tok}{ext}"
            with urllib.request.urlopen(urllib.request.Request(it["url"], headers=UA), timeout=60) as r: full.write_bytes(r.read())
            if full.stat().st_size < 50_000: full.unlink(); continue
            prev = pathlib.Path(tempfile.mkdtemp()) / f"{genre}-{tok}.mp3"; preview(full, prev)
            (pend / f"{tok}.json").write_text(json.dumps({"genre": genre, "file": full.name, "title": it.get("title"), "credit": credit_line(it),
                                                          "needs_credit": it["license"].lower() not in ("cc0", "pdm")}, ensure_ascii=False))
            needs = "⚠️ Pide crédito (lo pongo solo en los textos del anuncio)" if it["license"].lower() not in ("cc0", "pdm") else "✅ Sin crédito obligatorio"
            tg("sendAudio", {"chat_id": chat, "title": (it.get("title") or "Canción")[:60], "performer": (it.get("creator") or "")[:60],
                             "caption": f"🎵 Sugerencia para <b>{genre}</b>\n{credit_line(it)[:300]}\n{needs}", "parse_mode": "HTML",
                             "reply_markup": {"inline_keyboard": [[{"text": "✅ Usar", "callback_data": f"mus:ok:{tok}"}, {"text": "❌ Descartar", "callback_data": f"mus:no:{tok}"}]]}},
               {"audio": prev})
            sent += 1
        except Exception as e:
            print("canción falló:", it.get("id"), e)
    state_file().write_text(json.dumps(seen[-3000:]))
    return sent

def credits_for(name):
    return load(credits_file(), {}).get(name)

def pending_requests():
    """Pedidos del bot (/musica buscar <género>): archivos en storage/musica/pedidos/."""
    d = root() / "pedidos"
    if not d.is_dir(): return []
    out = []
    for f in sorted(d.glob("*")):
        out.append(f.name); f.unlink()
    return out
