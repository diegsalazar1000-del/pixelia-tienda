#!/bin/bash
# Rehace las capturas de la hoja (lleno/vacío) y los datos del ejemplo que usa reel.py. Necesita LibreOffice (se corre en la sesión de Claude, no en el servidor).
set -e; cd "$(dirname "$0")"; T=$(mktemp -d)
python3 build.py $T/lleno.xlsx --ejemplo
python3 - "$T" <<'P'
import openpyxl, json, sys
T = sys.argv[1]; wb = openpyxl.load_workbook(f"{T}/lleno.xlsx"); ws = wb.active
meta = [ws.cell(row=12, column=c).value for c in range(4, 9)]
dias = []
for r in range(20, 50):
    vals = [ws.cell(row=r, column=c).value for c in range(4, 9)]
    if all(v in (None, "") for v in vals): break
    cred = [0 if v in (None, "") else (1 if m is None else min(1, float(v) / m)) for v, m in zip(vals, meta)]
    dias.append(cred)
racha, out, acum = 0, [], 0
for i, cr in enumerate(dias):
    racha = racha + 1 if sum(cr) / 5 >= 0.5 else 0; acum += sum(cr)
    out.append({"dia": i + 1, "racha": racha, "pct": round(100 * acum / 150)})
json.dump(out, open("capturas/datos.json", "w")); print("días del ejemplo:", len(out), out[-1])
for r in range(20, 50):
    for c in range(4, 9): ws.cell(row=r, column=c).value = None
ws["P2"] = 0; wb.save(f"{T}/vacio.xlsx")
P
soffice --headless --convert-to pdf --outdir $T $T/lleno.xlsx $T/vacio.xlsx >/dev/null 2>&1
for f in lleno vacio; do pdftoppm -r 200 -png -singlefile $T/$f.pdf capturas/$f 2>/dev/null; done
rm -rf $T; ls -la capturas
