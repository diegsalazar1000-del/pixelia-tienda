"""Voz natural con ElevenLabs (si hay ELEVENLABS_API_KEY). Si no hay clave o falla, el estudio usa Piper.
Elige sola una voz latinoamericana femenina y otra masculina de la biblioteca de ElevenLabs y las recuerda.
"""
import json, os, pathlib, subprocess, urllib.parse, urllib.request

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

def pick_voice(genero):
    """ID de voz para 'femenina'/'masculina' (busca una vez en la biblioteca y la agrega a tu cuenta)."""
    gender = "female" if genero == "femenina" else "male"
    cache = {}
    try: cache = json.loads(cache_file().read_text())
    except Exception: pass
    if cache.get(gender): return cache[gender]["id"]
    best = None
    try:  # 1) biblioteca compartida: voces en español
        q = urllib.parse.urlencode({"language": "es", "gender": gender, "page_size": 50, "sort": "cloned_by_count"})
        voices = call("GET", f"/shared-voices?{q}").get("voices", [])
        voices = sorted(voices, key=lambda v: _score(v, gender), reverse=True)
        if voices and _score(voices[0], gender) > 0:
            v = voices[0]
            added = call("POST", f"/voices/add/{v['public_owner_id']}/{v['voice_id']}", {"new_name": f"Pixelia {genero}"})
            best = {"id": added.get("voice_id", v["voice_id"]), "name": v.get("name"), "accent": v.get("accent")}
    except Exception as e:
        print("biblioteca ElevenLabs:", e)
    if not best:  # 2) voces que ya están en tu cuenta
        mine = call("GET", "/voices").get("voices", [])
        mine = sorted(mine, key=lambda v: _score(v, gender), reverse=True)
        if not mine: raise RuntimeError("ElevenLabs no devolvió voces")
        best = {"id": mine[0]["voice_id"], "name": mine[0].get("name"), "accent": (mine[0].get("labels") or {}).get("accent")}
    cache[gender] = best; cache_file().parent.mkdir(parents=True, exist_ok=True); cache_file().write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    return best["id"]

def tts_mp3(text, genero, out_path, speed=1.0):
    vid = pick_voice(genero)
    body = {"text": text, "model_id": MODEL,
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True, "speed": max(0.8, min(1.15, speed))}}
    data = call("POST", f"/text-to-speech/{vid}?output_format=mp3_44100_128", body, raw=True, timeout=90)
    pathlib.Path(out_path).write_bytes(data)
    return out_path
