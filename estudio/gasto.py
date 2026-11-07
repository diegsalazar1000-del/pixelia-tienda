"""💸 Anota lo que consume cada llamada a la API de Claude (mismo archivo que la tienda: data/gasto-claude.jsonl)."""
import json, os, pathlib, datetime

def registrar(src, data):
    try:
        u = (data or {}).get("usage") or {}
        if not u: return
        i = (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0) * 1.25 + (u.get("cache_read_input_tokens") or 0) * 0.1
        o = u.get("output_tokens") or 0
        w = ((u.get("server_tool_use") or {}).get("web_search_requests")) or 0
        usd = i / 1e6 * float(os.environ.get("PRECIO_IN", 2)) + o / 1e6 * float(os.environ.get("PRECIO_OUT", 10)) + w * float(os.environ.get("PRECIO_BUSQUEDA", 0.01))
        f = pathlib.Path(os.environ.get("PIXELIA_DIR", "/pixelia")) / "data" / "gasto-claude.jsonl"
        with open(f, "a") as fh:
            fh.write(json.dumps({"t": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"), "s": src, "i": round(i), "o": o, "w": w, "usd": round(usd, 5)}) + "\n")
    except Exception:
        pass
