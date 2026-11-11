"""Fábrica del Plan financiero 2027 (la llama el estudio cuando entra un pedido pagado con form='plan')."""
import pathlib, traceback, importlib.util

def fabricar(job, raiz, api):
    pid = job["id"]
    try:
        spec = importlib.util.spec_from_file_location("plan_build", pathlib.Path(__file__).with_name("build.py"))
        b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
        out = pathlib.Path(raiz) / "storage" / "libros" / pid / "plan-2027.xlsx"
        b.generar(job["datos"], out)
        api("POST", "/api/studio/libro-done", {"id": pid, "archivo": f"libros/{pid}/plan-2027.xlsx"})
        print("📊 plan listo", pid, flush=True)
    except Exception as e:
        traceback.print_exc(); api("POST", "/api/studio/libro-done", {"id": pid, "error": str(e)[:300]})
