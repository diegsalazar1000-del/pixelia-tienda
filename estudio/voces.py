"""Voz natural con ElevenLabs (si hay ELEVENLABS_API_KEY). Si no hay clave o falla, el estudio usa Piper.
Elige sola una voz latinoamericana femenina y otra masculina de la biblioteca de ElevenLabs y las recuerda.
"""
import json, os, pathlib, subprocess, time, urllib.error, urllib.parse, urllib.request

API = "https://api.elevenlabs.io/v1"
MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")
LATAM = ("latin", "latam", "mexic", "colomb", "argentin", "venezol", "chile", "peru", "neutral", "latino")

def key(): return os.environ.get("ELEVENLABS_API_KEY", "").strip()
def cache_file(): return pathlib.Path(os.environ.get("PIXELIA_DIR", "/pixelia")) / "storage" / "voces-elevenlabs.json"

def call(method, path, body=None, raw=False, timeout=60):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"xi-api-key": key(), "content-type": "application/json", "accept": "audio/mpeg" if raw else "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read() if raw else json.load(r)

def _score(v, gender):
    lab = {k: str(x).lower() for k, x in (v.get("labels") or {}).items()} if isinstance(v.get("labels"), dict) else {}
    txt = " ".join([str(v.get(k, "")).lower() for k in ("accent", "language", "locale", "description", "name", "use_case", "category")] + list(lab.values()))
    g = str(v.get("gender") or lab.get("gender", "")).lower()
    if g and g != gender: return -1
    s = 0
    if "es" == str(v.get("language", lab.get("language", ""))).lower()[:2] or "spanish" in txt or "español" in txt: s += 5
    if any(w in txt for w in LATAM): s += 4
    if any(w in txt for w in ("advert", "commercial", "social", "narrat", "conversational", "young", "warm")): s += 2
    s += min(3, (v.get("cloned_by_count") or v.get("usage_character_count_1y") or 0) / 20000)
    return s

def _load_cache():
    try: return json.loads(cache_file().read_text())
    except Exception: return {}

def _save_cache(c):
    cache_file().parent.mkdir(parents=True, exist_ok=True); cache_file().write_text(json.dumps(c, ensure_ascii=False, indent=1))

def _library_voice(gender):
    """Busca en la biblioteca compartida una voz en español (latina si se puede). Prueba varias formas de consulta."""
    tries = [{"language": "es", "gender": gender, "page_size": 50, "sort": "usage_character_count_1y"},
             {"language": "es", "gender": gender, "page_size": 50},
             {"search": "spanish latin " + gender, "page_size": 50}]
    for params in tries:
        try:
            voices = call("GET", "/shared-voices?" + urllib.parse.urlencode(params)).get("voices", [])
        except Exception as e:
            print("biblioteca ElevenLabs:", params, e); continue
        voices = sorted(voices, key=lambda v: _score(v, gender), reverse=True)
        if voices and _score(voices[0], gender) > 0:
            v = voices[0]
            try:
                added = call("POST", f"/voices/add/{v['public_owner_id']}/{v['voice_id']}", {"new_name": f"Pixelia {gender}"})
                vid = added.get("voice_id", v["voice_id"])
            except Exception as e:
                print("no pude agregar la voz de la biblioteca:", e); vid = v["voice_id"]
            return {"id": vid, "name": v.get("name"), "accent": v.get("accent"), "source": "library"}
    return None

def _account_voice(gender):
    """Voces propias de la cuenta (funcionan también en el plan gratis)."""
    mine = call("GET", "/voices").get("voices", [])
    mine = [v for v in mine if (v.get("category") or "") != "professional"] or mine
    mine = sorted(mine, key=lambda v: _score(v, gender), reverse=True)
    if not mine: raise RuntimeError("ElevenLabs no devolvió voces")
    return {"id": mine[0]["voice_id"], "name": mine[0].get("name"), "accent": (mine[0].get("labels") or {}).get("accent"), "source": "account", "t": time.time()}

def pick_voice(genero, avoid_library=False):
    gender = "female" if genero == "femenina" else "male"
    cache = _load_cache(); cur = cache.get(gender)
    free = cache.get("free_plan_until", 0) > time.time()
    if cur:
        if cur.get("source") == "library" and not avoid_library: return cur["id"]
        if cur.get("source") == "account" and (free or avoid_library or time.time() - cur.get("t", 0) < 86400): return cur["id"]
    best = None if (avoid_library or free) else _library_voice(gender)
    best = best or _account_voice(gender)
    cache[gender] = best; _save_cache(cache)
    return best["id"]

def tts_mp3(text, genero, out_path, speed=1.0):
    body = {"text": text, "model_id": MODEL,
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True, "speed": max(0.8, min(1.15, speed))}}
    vid = pick_voice(genero)
    try:
        data = call("POST", f"/text-to-speech/{vid}?output_format=mp3_44100_128", body, raw=True, timeout=90)
    except urllib.error.HTTPError as e:
        if e.code != 402: raise
        # plan gratis: las voces de la biblioteca no se pueden usar por API → voz propia de la cuenta; reintento en 1 día
        c = _load_cache(); c["free_plan_until"] = time.time() + 86400; c.pop("female" if genero == "femenina" else "male", None); _save_cache(c)
        vid = pick_voice(genero, avoid_library=True)
        data = call("POST", f"/text-to-speech/{vid}?output_format=mp3_44100_128", body, raw=True, timeout=90)
    pathlib.Path(out_path).write_bytes(data)
    return out_path

def reset():
    """Olvida las voces elegidas (por ejemplo, después de pasar al plan de pago)."""
    try: cache_file().unlink()
    except FileNotFoundError: pass

# ---------- música con Eleven Music (planes de pago; licencia comercial) ----------
MUSIC_PROMPTS = {
    "reggaeton": "Modern Latin reggaeton instrumental, classic dembow beat, 95 BPM, punchy kick, catchy plucked synth hook, bright and danceable",
    "cumbia": "Modern Latin cumbia instrumental, accordion melody, guacharaca and congas, 98 BPM, festive and catchy",
    "trap": "Latin trap instrumental, 140 BPM half-time groove, deep 808 bass, crisp hi-hat rolls, dark catchy melody",
    "pop": "Upbeat Latin pop instrumental, 118 BPM, bright synths and guitar, feel-good and catchy, TikTok style",
    "electronica": "Upbeat house / dance instrumental, 124 BPM, four-on-the-floor, energetic modern synth drop",
    "lofi": "Lo-fi hip hop instrumental, 80 BPM, warm Rhodes chords, soft vinyl crackle, calm and cozy study vibe",
    "acustica": "Upbeat acoustic instrumental, strummed guitar and claps, 100 BPM, warm, happy and homey",
    "base": "Light upbeat background instrumental for a product ad, 115 BPM, positive, modern and clean",
}

def compose_music(genre, out_path, seconds=30, audience=""):
    prompt = MUSIC_PROMPTS.get(genre, MUSIC_PROMPTS["base"]) + (f". Made for a short social media ad aimed at {audience}" if audience else "") + \
             ". No vocals. Energetic from the very first second, no long intro."
    body = {"prompt": prompt[:1900], "music_length_ms": int(seconds * 1000), "model_id": os.environ.get("ELEVENLABS_MUSIC_MODEL", "music_v1"),
            "force_instrumental": True}
    data = call("POST", "/music?output_format=mp3_44100_128", body, raw=True, timeout=240)
    pathlib.Path(out_path).write_bytes(data)
    return out_path
