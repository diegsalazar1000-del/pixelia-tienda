"""Genera el PLAN FINANCIERO 2027 personalizado (Excel que también abre en Google Sheets) con los datos que la persona puso en /plan.
Uso: python3 build.py datos.json salida.xlsx      (sin datos.json → ejemplo de María)
datos = {nombre, prof, ing, malo, var, cs, gas:[[concepto, monto]], meta, mm}
Solo fórmulas que funcionan igual en Excel y en Google Sheets."""
import sys, json, math, pathlib, subprocess
try:
    import openpyxl
except ImportError:   # el estudio no lo trae de fábrica: se instala solo la primera vez
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--break-system-packages", "openpyxl"], check=False)
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "openpyxl"], check=False)
    import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import FormulaRule
from openpyxl.chart import BarChart, Reference
from openpyxl.worksheet.datavalidation import DataValidation

MES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
VERDE, VERDE2, AMAR, GRIS, ROJO, AZUL = "1F7A5A", "E3F4EC", "FFD23F", "F4FBF8", "FDE2E1", "E0F2FE"
F = lambda **k: Font(name="Arial", **k)
fill = lambda c: PatternFill("solid", fgColor=c)
linea = Border(bottom=Side(style="thin", color="D9EFE5"))

EJEMPLO = {"nombre": "María", "prof": "empleada", "ing": 500, "malo": 0, "var": 0, "cs": "$",
           "gas": [["🏠 Renta", 125], ["🛒 Comida", 125], ["💡 Luz, agua, internet", 40], ["🚌 Transporte", 35], ["💳 Tarjeta", 40]],
           "meta": "🛟 Fondo de emergencia", "mm": 600}

def generar(d, out):
    d = {**EJEMPLO, **{k: v for k, v in (d or {}).items() if v not in (None, "")}}
    cs = str(d.get("cs") or "$")[:3]; num = f'"{cs} "#,##0;[Red]-"{cs} "#,##0'
    nom = str(d.get("nombre") or "").strip()[:30]
    gas = [[str(g[0])[:40], max(0, float(g[1] or 0))] for g in (d.get("gas") or [])][:10] or EJEMPLO["gas"]
    var = bool(d.get("var")) and float(d.get("malo") or 0) > 0
    base = (float(d["ing"]) + float(d["malo"])) / 2 if var else float(d["ing"])
    wb = openpyxl.Workbook()

    # ---------- INICIO ----------
    S = wb.active; S.title = "Inicio"; S.sheet_view.showGridLines = False
    S.column_dimensions["A"].width = 3; S.column_dimensions["B"].width = 34; S.column_dimensions["C"].width = 18; S.column_dimensions["D"].width = 44
    S["B2"] = f"📊 Plan financiero 2027{' de ' + nom if nom else ''}"; S["B2"].font = F(size=20, bold=True, color=VERDE)
    S["B3"] = "Que el nuevo año no te agarre desprevenido · las celdas amarillas las puedes cambiar"; S["B3"].font = F(size=10, italic=True, color="5D7A6E")
    def campo(r, et, val, fmt=None, nota="", editable=True):
        S.cell(r, 2, et).font = F(bold=True); c = S.cell(r, 3, val)
        if fmt: c.number_format = fmt
        if editable: c.fill = fill("FFF6D6")
        c.border = linea; S.cell(r, 4, nota).font = F(size=9, color="5D7A6E")
        return c
    campo(5, "A qué te dedicas", str(d.get("prof") or "")[:40])
    campo(6, "Ganas al mes (promedio)", round(base, 2), num, "Si un mes ganas más, guarda la diferencia 😉")
    S["B8"] = "🏠 Lo necesario cada mes"; S["B8"].font = F(size=13, bold=True, color=VERDE)
    r0 = 9
    for i in range(10):
        r = r0 + i
        if i < len(gas): S.cell(r, 2, gas[i][0]); S.cell(r, 3, gas[i][1])
        S.cell(r, 2).fill = fill("FFF6D6"); S.cell(r, 3).fill = fill("FFF6D6"); S.cell(r, 3).number_format = num
        S.cell(r, 2).border = linea; S.cell(r, 3).border = linea
    S.cell(r0 + 10, 2, "Total lo necesario").font = F(bold=True)
    S.cell(r0 + 10, 3, f"=SUM(C{r0}:C{r0 + 9})").number_format = num; S.cell(r0 + 10, 3).font = F(bold=True)
    S["B21"] = "🧮 Así se reparte lo que te queda"; S["B21"].font = F(size=13, bold=True, color=VERDE)
    pct = 0.5 if var else 0.45
    rows = [("Te queda después de lo necesario", "=MAX(0,C6-C19)", "", False),
            ("🎯 Ahorro para tu meta", f"=ROUND(C22*{pct},0)", f"{int(pct * 100)}% de lo que te queda", False),
            ("🎄 Apartar para diciembre 2027", "=ROUND(C22*0.1,0)", "10%: regalos y cena sin deudas", False),
            ("🎉 Gustos y salidas", "=C22-C23-C24", "Lo que sobra, sin culpa", False)]
    for j, (et, f, nota, ed) in enumerate(rows):
        c = campo(22 + j, et, f, num, nota, ed); c.font = F(bold=True, color="16A34A" if j == 1 else "14261F")
    S["B27"] = "🎯 Tu meta 2027"; S["B27"].font = F(size=13, bold=True, color=VERDE)
    campo(28, "Meta", str(d.get("meta") or "")[:40])
    campo(29, "¿Cuánto necesitas?", float(d.get("mm") or 0) or None, num)
    c = campo(30, "La cumples en", '=IF(OR(C29="",C23<=0),"Pon el monto de tu meta",IF(ROUNDUP(C29/C23,0)>12,ROUNDUP(C29/C23,0)&" meses",INDEX({"enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"},ROUNDUP(C29/C23,0))&" de 2027 🎉"))', None, "", False)
    c.font = F(size=13, bold=True, color="16A34A")
    S["B32"] = "📌 Cómo usarlo"; S["B32"].font = F(size=13, bold=True, color=VERDE)
    for k, t in enumerate(["1️⃣ Cada mes abre su pestaña (Ene, Feb…): el plan ya está puesto.",
                           "2️⃣ Escribe lo que de verdad gastaste en la columna REAL.",
                           "3️⃣ El semáforo te avisa: 🟢 vas bien · 🟡 cerca del tope · 🔴 te pasaste.",
                           "4️⃣ En 'Mi año' y 'Meta' ves tu ahorro subiendo mes a mes.",
                           "📱 En Google Sheets: drive.google.com → Nuevo → Subir archivo → ábrelo con Hojas de cálculo."]):
        S.cell(33 + k, 2, t).font = F(size=10)
    S["B39"] = "Hecho con 💚 por Pixelia · pixeliadigital.app"; S["B39"].font = F(size=9, color="9CA3AF")
    for r in (5, 6, 28, 29): S.cell(r, 3).alignment = Alignment(horizontal="right")

    # ---------- 12 MESES ----------
    extra = {0: [("🎒 Útiles y regreso a clases", "=ROUND(Inicio!C6*0.06,0)")], 7: [("🎒 Regreso a clases", "=ROUND(Inicio!C6*0.05,0)")],
             11: [("🎁 Regalos y cena (con lo apartado)", "=Inicio!C24*11")]}
    for m, nm in enumerate(MES):
        W = wb.create_sheet(nm[:3]); W.sheet_view.showGridLines = False
        for col, w in zip("ABCDEF", (3, 36, 15, 15, 15, 8)): W.column_dimensions[col].width = w
        W["B2"] = f"📅 {nm} 2027"; W["B2"].font = F(size=18, bold=True, color=VERDE)
        W["B3"] = "Escribe en REAL lo que gastaste · el semáforo se pinta solo"; W["B3"].font = F(size=10, italic=True, color="5D7A6E")
        W["B5"] = "💵 Entró este mes"; W["C5"] = "=Inicio!C6"
        for j, h in enumerate(["Concepto", "Plan", "Real", "Diferencia", ""]):
            c = W.cell(7, 2 + j, h); c.font = F(bold=True, color="FFFFFF"); c.fill = fill(VERDE)
        filas = [(f'=IF(Inicio!B{r0 + i}="","",Inicio!B{r0 + i})', f'=IF(Inicio!B{r0 + i}="","",Inicio!C{r0 + i})') for i in range(10)]
        ex = extra.get(m, []); filas += ex
        rex = 8 + 10   # fila del gasto extra del mes (si hay): sale de "Gustos" para no descuadrar
        gustos = f"=MAX(0,Inicio!C25-C{rex})" if ex and m != 11 else "=Inicio!C25"
        filas += [("🎯 Ahorro para tu meta", "=Inicio!C23"), ("🎄 Apartar para diciembre", "=0" if m == 11 else "=Inicio!C24"), ("🎉 Gustos y salidas", gustos)]
        if m == 11: W["B5"] = "💵 Entró este mes + lo apartado"; W["C5"] = "=Inicio!C6+Inicio!C24*11"
        W["B5"].font = F(bold=True); W["C5"].number_format = num; W["C5"].fill = fill("FFF6D6")
        r = 8
        for et, plan in filas:
            W.cell(r, 2, et); W.cell(r, 3, plan).number_format = num
            W.cell(r, 4).number_format = num; W.cell(r, 4).fill = fill("FFF6D6")
            W.cell(r, 5, f'=IF(D{r}="","",C{r}-D{r})').number_format = num
            W.cell(r, 6, f'=IF(D{r}="","",IF(D{r}<=C{r},"🟢",IF(D{r}<=C{r}*1.05,"🟡","🔴")))').alignment = Alignment(horizontal="center")
            for c in range(2, 7): W.cell(r, c).border = linea
            r += 1
        fin = r - 1
        W.cell(r, 2, "Total").font = F(bold=True)
        W.cell(r, 3, f"=SUM(C8:C{fin})").number_format = num
        W.cell(r, 4, f"=SUM(D8:D{fin})").number_format = num
        for c in (3, 4): W.cell(r, c).font = F(bold=True)
        W.cell(r + 1, 2, "Te sobra este mes").font = F(bold=True, color="16A34A")
        W.cell(r + 1, 3, f"=C5-C{r}").number_format = num
        W.cell(r + 1, 4, f'=IF(D{r}=0,"",C5-D{r})').number_format = num
        rng = f"D8:D{fin}"
        W.conditional_formatting.add(rng, FormulaRule(formula=[f'AND(D8<>"",D8>C8*1.05)'], fill=fill(ROJO)))
        W.conditional_formatting.add(rng, FormulaRule(formula=[f'AND(D8<>"",D8>C8,D8<=C8*1.05)'], fill=fill("FEF3C7")))
        W.conditional_formatting.add(rng, FormulaRule(formula=[f'AND(D8<>"",D8<=C8)'], fill=fill(VERDE2)))
        # dónde quedó el ahorro real de este mes (para Mi año)
        W["H8"] = "Ahorro real"; W["H8"].font = F(size=8, color="9CA3AF")
        W["H9"] = f'=IF(D{fin - 2}="",0,D{fin - 2})'; W["H9"].font = F(size=8, color="9CA3AF")
        W.freeze_panes = "B8"

    # ---------- MI AÑO ----------
    A = wb.create_sheet("Mi año"); A.sheet_view.showGridLines = False
    for col, w in zip("ABCDE", (3, 14, 16, 16, 18)): A.column_dimensions[col].width = w
    A["B2"] = "📈 Mi año 2027"; A["B2"].font = F(size=18, bold=True, color=VERDE)
    for j, h in enumerate(["Mes", "Ahorro plan", "Ahorro real", "Acumulado"]):
        c = A.cell(4, 2 + j, h); c.font = F(bold=True, color="FFFFFF"); c.fill = fill(VERDE)
    for m, nm in enumerate(MES):
        r = 5 + m
        A.cell(r, 2, nm); A.cell(r, 3, "=Inicio!C23").number_format = num
        A.cell(r, 4, f"='{nm[:3]}'!H9").number_format = num
        A.cell(r, 5, f"=SUM(D$5:D{r})").number_format = num
        for c in range(2, 6): A.cell(r, c).border = linea
    A["B18"] = "Total ahorrado"; A["B18"].font = F(bold=True); A["E18"] = "=E16"; A["E18"].number_format = num; A["E18"].font = F(bold=True, color="16A34A")
    A["B19"] = "Para diciembre"; A["B19"].font = F(bold=True); A["E19"] = "=Inicio!C24*11"; A["E19"].number_format = num; A["E19"].font = F(bold=True, color="0284C7")
    ch = BarChart(); ch.type = "col"; ch.title = "Ahorro acumulado"; ch.height, ch.width = 7, 16; ch.legend = None
    ch.add_data(Reference(A, min_col=5, min_row=4, max_row=16), titles_from_data=True); ch.set_categories(Reference(A, min_col=2, min_row=5, max_row=16))
    A.add_chart(ch, "G4")

    # ---------- META ----------
    M = wb.create_sheet("Meta"); M.sheet_view.showGridLines = False
    M.column_dimensions["A"].width = 3; M.column_dimensions["B"].width = 26; M.column_dimensions["C"].width = 40
    M["B2"] = f"🎯 {str(d.get('meta') or 'Mi meta')[:40]}"; M["B2"].font = F(size=18, bold=True, color=VERDE)
    M["B4"] = "Necesitas"; M["C4"] = "=Inicio!C29"; M["B5"] = "Llevas"; M["C5"] = "='Mi año'!E18"
    M["B6"] = "Avance"; M["C6"] = '=IF(N(C4)=0,"",MIN(1,C5/C4))'; M["C6"].number_format = "0%"
    M["B7"] = ""; M["C7"] = '=IF(C6="","",REPT("█",ROUND(C6*20,0))&REPT("░",20-ROUND(C6*20,0)))'; M["C7"].font = F(size=16, color="16A34A")
    M["B8"] = "La cumples en"; M["C8"] = "=Inicio!C30"
    for r in (4, 5): M.cell(r, 3).number_format = num
    for r in range(4, 9): M.cell(r, 2).font = F(bold=True)
    M["B10"] = "💡 Si un mes ahorras más, la fecha se adelanta sola."; M["B10"].font = F(size=10, italic=True, color="5D7A6E")

    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True); wb.save(out)
    return {"meses": 12, "base": base}

if __name__ == "__main__":
    d = json.loads(pathlib.Path(sys.argv[1]).read_text()) if len(sys.argv) > 2 else {}
    print(generar(d, sys.argv[-1] if len(sys.argv) > 1 else "/tmp/plan.xlsx"))
