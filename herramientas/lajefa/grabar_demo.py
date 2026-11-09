"""Graba la app La Jefa EN USO (como un video de pantalla del teléfono) para el reel: calcula un precio,
guarda, manda un recordatorio por WhatsApp y hace un estado. Sale pantallas/demo/*.jpg + demo.json (tiempos y fases).
Corre en la sesión de Claude (Chrome + Playwright):  python3 grabar_demo.py"""
import json, base64, pathlib, shutil, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
APP = HERE.parent.parent / "src" / "apps" / "jefa" / "index.html"
OUT = HERE / "pantallas" / "demo"
PRE = """try{localStorage.clear();localStorage.setItem('jefa-moneda','"USD"');localStorage.setItem('jefa-neg','"Dulces de Mari"');
localStorage.setItem('jefa-tel','"+58 412 555 0101"');localStorage.setItem('jefa-deudas',JSON.stringify([{n:'Carla',q:12}]));}catch(e){}"""
TOQUE = """try{Object.defineProperty(navigator,"clipboard",{value:{writeText:()=>Promise.resolve()}})}catch(e){}document.addEventListener('pointerdown',e=>{const d=document.createElement('div');d.style.cssText=`position:fixed;left:${e.clientX-22}px;top:${e.clientY-22}px;width:44px;height:44px;border-radius:50%;background:rgba(255,255,255,.55);border:3px solid rgba(122,24,70,.6);z-index:9999;pointer-events:none;transition:transform .35s,opacity .35s`;document.body.appendChild(d);requestAnimationFrame(()=>{d.style.transform='scale(1.6)';d.style.opacity='0'});setTimeout(()=>d.remove(),400)},true);"""

def main():
    shutil.rmtree(OUT, ignore_errors=True); OUT.mkdir(parents=True)
    html = APP.read_text().replace("<head>", f"<head><script>{PRE}</script>", 1).replace("</body>", f"<script>{TOQUE}</script></body>")
    tmp = pathlib.Path("/tmp/jefa-demo.html"); tmp.write_text(html)
    frames, fases = [], []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=False)
        pg = ctx.new_page(); pg.goto(f"file://{tmp}"); pg.wait_for_timeout(800)
        cdp = ctx.new_cdp_session(pg)
        def on_frame(ev):
            frames.append((ev["metadata"]["timestamp"], ev["data"])); cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})
        cdp.on("Page.screencastFrame", on_frame)
        cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 85, "maxWidth": 780, "maxHeight": 1688, "everyNthFrame": 1})
        marca = lambda n: fases.append((n, time.time()))
        # 1) calcular el precio
        marca("precio"); pg.wait_for_timeout(300)
        pg.click("#prod", click_count=3); pg.keyboard.type("Torta de chocolate", delay=35)
        pg.click("#cobro", click_count=3); pg.keyboard.type("15", delay=60); pg.wait_for_timeout(200)
        pg.click("#calc"); pg.wait_for_timeout(900)
        pg.evaluate("document.querySelector('#pv').scrollIntoView({behavior:'smooth',block:'center'})"); pg.wait_for_timeout(700)
        pg.click("[data-pv]"); pg.wait_for_timeout(400); pg.click("#usar"); pg.wait_for_timeout(900)
        # 2) cobrar por WhatsApp
        marca("cobro"); pg.click("[data-v=deben]"); pg.wait_for_timeout(400)
        pg.click("#tonos [data-t=drama]"); pg.wait_for_timeout(700)
        pg.evaluate("document.querySelector('#rec').scrollIntoView({behavior:'smooth',block:'center'})"); pg.wait_for_timeout(500)
        pg.click("#coprec"); pg.wait_for_timeout(1000)
        # 3) hacer el estado
        marca("estado"); pg.click("[data-v=estados]"); pg.wait_for_timeout(300)
        pg.evaluate("document.querySelector('#v-estados>.card').style.display='none';window.scrollTo(0,0)"); pg.wait_for_timeout(900)
        for js in ["ecol='menta';prepEstados()", "ecol='lavanda';prepEstados()", "eplant='lista';prepEstados()", "eplant='pedidos';ecol='rosa';prepEstados()"]:
            pg.evaluate(js); pg.wait_for_timeout(650)
        marca("fin"); cdp.send("Page.stopScreencast"); pg.wait_for_timeout(200); b.close()
    t0 = frames[0][0]
    for i, (t, d) in enumerate(frames): (OUT / f"{i:04d}.jpg").write_bytes(base64.b64decode(d))
    (HERE / "pantallas" / "demo.json").write_text(json.dumps({"t": [round(t - t0, 3) for t, _ in frames],
        "fases": {n: round(t - t0, 3) for n, t in fases}}, indent=0))
    print(f"ok {len(frames)} fotogramas, {frames[-1][0] - t0:.1f} s, fases:", {n: round(t - t0, 1) for n, t in fases})

if __name__ == "__main__":
    main()
