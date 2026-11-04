"""Genera los 3 flujos de n8n (JSON importable) a partir del código en n8n/src/."""
import json, uuid, pathlib

SRC = pathlib.Path(__file__).parent / "src"
OUT = pathlib.Path(__file__).parent

def code(name, file, x, y):
    return {"parameters": {"jsCode": (SRC / file).read_text()}, "name": name, "type": "n8n-nodes-base.code",
            "typeVersion": 2, "position": [x, y], "id": str(uuid.uuid4())}

def schedule(name, hour, x, y):
    return {"parameters": {"rule": {"interval": [{"field": "days", "triggerAtHour": hour}]}}, "name": name,
            "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2, "position": [x, y], "id": str(uuid.uuid4())}

def chain(nodes):
    conns = {}
    for a, b in zip(nodes, nodes[1:]):
        conns[a["name"]] = {"main": [[{"node": b["name"], "type": "main", "index": 0}]]}
    return conns

def workflow(name, nodes, tz="America/Caracas"):
    return {"name": name, "nodes": nodes, "connections": chain(nodes), "active": False,
            "settings": {"executionOrder": "v1", "timezone": tz}, "pinData": {}}

def note(text, x, y, w=420, h=300):
    return {"parameters": {"content": text, "width": w, "height": h}, "name": "Nota " + str(uuid.uuid4())[:4],
            "type": "n8n-nodes-base.stickyNote", "typeVersion": 1, "position": [x, y], "id": str(uuid.uuid4())}

# 1) Radar diario
radar_nodes = [
    schedule("Cada día 8:00", 8, 0, 300),
    code("Config", "config.js", 220, 300),
    code("Etsy", "etsy.js", 440, 300),
    code("YouTube", "youtube.js", 660, 300),
    code("Explorador web", "web.js", 880, 300),
    code("TikTok", "tiktok.js", 1100, 300),
    code("Instagram", "instagram.js", 1320, 300),
    code("Hotmart", "hotmart.js", 1540, 300),
    code("Filtrar y guardar", "guardar.js", 1760, 300),
    code("Evaluar con IA", "evaluar.js", 1980, 300),
    code("Avisar por Telegram", "avisar.js", 2200, 300),
]
radar = workflow("1 · Radar diario de tendencias", radar_nodes)
radar["nodes"].append(note("## 📡 Radar diario\n1. Rellena el nodo **Config**.\n2. Pulsa **Test workflow** para probar.\n3. Actívalo (arriba a la derecha).\n\nCada fuente sin clave se salta sola, así puedes empezar solo con Etsy.", 0, 0))

# 2) Decisiones desde Telegram
trigger = {"parameters": {"updates": ["callback_query"], "additionalFields": {}}, "name": "Telegram Trigger",
           "type": "n8n-nodes-base.telegramTrigger", "typeVersion": 1.1, "position": [0, 300], "id": str(uuid.uuid4()),
           "webhookId": str(uuid.uuid4()), "credentials": {"telegramApi": {"id": "", "name": "Bot del radar"}}}
dec_nodes = [trigger, code("Config", "config.js", 220, 300), code("Procesar decisión", "decidir.js", 440, 300)]
dec = workflow("2 · Decisiones del radar (Telegram)", dec_nodes)
dec["nodes"].append(note("## 🧠 Decisiones\nEscucha los botones del radar.\nEn **Telegram Trigger** crea la credencial con el token del **bot del radar** (no el de la tienda).\nCopia el mismo **Config** del flujo 1.\nDebe estar **activo** siempre.", 0, 0))

# 3) Rendimiento diario
perf_nodes = [schedule("Cada día 21:00", 21, 0, 300), code("Config", "config.js", 220, 300), code("Revisar ventas y anuncios", "rendimiento.js", 440, 300)]
perf = workflow("3 · Rendimiento diario y Meta Ads", perf_nodes)
perf["nodes"].append(note("## 📊 Rendimiento\nCruza las ventas de la tienda con Meta Ads.\n**Importante:** el nombre de cada anuncio en Meta debe empezar con **[slug-del-producto]**, ej. `[planner-de-bodas] v1`.\nAjusta las reglas en **Config** (DIAS_PRUEBA, GASTO_MAX_SIN_VENTA…).", 0, 0))

for fname, wf in [("1-radar-diario.json", radar), ("2-decisiones-telegram.json", dec), ("3-rendimiento-meta-ads.json", perf)]:
    (OUT / fname).write_text(json.dumps(wf, ensure_ascii=False, indent=2))
    print("ok", fname, len(wf["nodes"]), "nodos")
