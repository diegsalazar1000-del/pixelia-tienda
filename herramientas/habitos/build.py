"""Mi 2027 en Hábitos · Pixelia — tracker de hábitos para Excel y Google Sheets (todo automático).
Uso: python3 build.py salida.xlsx [--ejemplo]
Solo funciones compatibles con Excel y Google Sheets (nada de SPARKLINE/FILTER/3D)."""
import sys, random
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import FormulaRule, ColorScaleRule
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.utils import get_column_letter as L

EJ = "--ejemplo" in sys.argv
OUT = sys.argv[1]
YEAR = 2027
HOY_EJEMPLO = (2027, 3, 18)

# ---------- estilo (colores Pixelia) ----------
NAVY, VIO, VIO2, LILA, SOFT, PINK, CYAN, MINT, AMBER, GREY, WHITE, LINE, OFF = (
    "1B1640", "7C5CFF", "5B3FE0", "ECE7FF", "F8F6FF", "FF4FD8", "22D3EE", "34D399", "FBBF24", "77738F", "FFFFFF", "E3DEF5", "ECEAF3")
F = "Arial"
def font(s=10, b=False, c=NAVY, i=False): return Font(name=F, size=s, bold=b, color=c, italic=i)
def fill(c): return PatternFill("solid", fgColor=c)
thin = Side(style="thin", color=LINE)
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True, indent=1)
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
CATS = ["💪 Salud", "🧠 Mente", "🧘 Bienestar", "💸 Dinero", "📚 Aprendizaje", "💼 Trabajo/Estudio", "❤️ Relaciones", "🏠 Hogar"]
MOODS = ["😫", "😞", "😐", "😊", "😍"]
N_H = 15                      # hábitos por mes
EJEMPLOS = [("💧 Tomar 2 litros de agua", "💪 Salud", 25, "Tener más energía y mejor piel"),
            ("📖 Leer 10 minutos", "📚 Aprendizaje", 20, "Terminar 12 libros este año"),
            ("🚶 Caminar 30 minutos", "💪 Salud", 16, "Sentirme ligera y dormir mejor"),
            ("📵 Sin celular 1 h antes de dormir", "🧘 Bienestar", 20, "Descansar de verdad"),
            ("💸 Cero gastos hormiga", "💸 Dinero", 20, "Juntar para mi viaje"),
            ("🧘 5 minutos de respirar", "🧘 Bienestar", 15, "Menos estrés"),
            ("🛏️ Dormir antes de las 11", "💪 Salud", 20, "Levantarme sin sueño")]

wb = Workbook()

def widths(ws, d):
    for k, v in d.items(): ws.column_dimensions[k].width = v

def paint(ws, r1, r2, c1, c2, color):
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1): ws.cell(row=r, column=c).fill = fill(color)

def merge(ws, r1, c1, r2, c2, value=None, f=None, bg=None, al=CENTER, fmt=None, border=False):
    if (r1, c1) != (r2, c2): ws.merge_cells(start_row=r1, start_column=c1, end_row=r2, end_column=c2)
    c = ws.cell(row=r1, column=c1)
    if value is not None: c.value = value
    if f: c.font = f
    if al: c.alignment = al
    if fmt: c.number_format = fmt
    for r in range(r1, r2 + 1):
        for cc in range(c1, c2 + 1):
            x = ws.cell(row=r, column=cc)
            if bg: x.fill = fill(bg)
            if border: x.border = BOX
    return c

def dv_list(ws, formula, rng, prompt=None, strict=False):
    dv = DataValidation(type="list", formula1=formula, allow_blank=True, showDropDown=False, showErrorMessage=strict)
    if prompt: dv.promptTitle = "Elige"; dv.prompt = prompt; dv.showInputMessage = True
    ws.add_data_validation(dv); dv.add(rng)

def card(ws, r, c1, c2, label, color, value, sub, fmt=None, vsize=18):
    merge(ws, r, c1, r, c2, label, font(8, True, WHITE), color)
    merge(ws, r + 1, c1, r + 1, c2, value, font(vsize, True, NAVY), WHITE, fmt=fmt)
    merge(ws, r + 2, c1, r + 2, c2, sub, font(8, False, GREY), WHITE)
    for rr in (r, r + 1, r + 2):
        for cc in range(c1, c2 + 1):
            b = ws.cell(row=rr, column=cc)
            b.border = Border(left=Side("thin", color=color) if cc == c1 else None, right=Side("thin", color=color) if cc == c2 else None,
                              top=Side("thin", color=color) if rr == r else None, bottom=Side("medium", color=color) if rr == r + 2 else None)

# ======================= INICIO =======================
I = wb.active; I.title = "Inicio"; I.sheet_view.showGridLines = False; I.sheet_properties.tabColor = VIO
widths(I, {"A": 2, "B": 5, "C": 34, "D": 20, "E": 12, "F": 38, "G": 2})
paint(I, 1, 60, 1, 7, SOFT)
merge(I, 2, 2, 2, 6, "Mi 2027 en Hábitos ✨", font(24, True, WHITE), VIO, LEFT)
merge(I, 3, 2, 3, 6, "Pequeños hábitos, un año distinto. Marca ✓ cada día y deja que la hoja haga el resto.", font(10, False, WHITE, True), VIO, LEFT)
I.row_dimensions[2].height = 46; I.row_dimensions[3].height = 22
I["C5"] = "📅 Año que vas a seguir:"; I["C5"].font = font(11, True); I["C5"].alignment = Alignment(horizontal="right", vertical="center")
I["D5"] = YEAR; I["D5"].font = font(14, True, VIO); I["D5"].fill = fill(WHITE); I["D5"].border = BOX; I["D5"].alignment = CENTER
dv_list(I, '"2026,2027,2028,2029,2030"', "D5", "¿Qué año vas a seguir?")
I.row_dimensions[5].height = 26
# "hoy" (oculto): en el ejemplo se fija una fecha para que las capturas muestren un mes en curso
I["Z1"] = f"=DATE({HOY_EJEMPLO[0]},{HOY_EJEMPLO[1]},{HOY_EJEMPLO[2]})" if EJ else "=TODAY()"
I["Z1"].number_format = "dd/mm/yyyy"; I.column_dimensions["Z"].hidden = True
HOY = "Inicio!$Z$1"

I["B7"] = "CÓMO SE USA (2 minutos)"; I["B7"].font = font(12, True, VIO)
pasos = [("1", "Escribe tus hábitos aquí abajo. Ya te dejamos ejemplos: cámbialos, bórralos o agrega hasta 15. Elige categoría y cuántos días al mes quieres cumplirlo."),
         ("2", "Cada día abre la pestaña del mes y marca ✓ en los hábitos que cumpliste (toca la casilla y elige ✓, o escribe una x). Registra también tu ánimo."),
         ("3", "Listo. Tu %, tu nivel, tus 🔥 rachas y el mensaje de cómo vas se calculan solos. En «Mi Año» ves todo tu 2027 de un vistazo.")]
r = 8
for n, t in pasos:
    c = I.cell(row=r, column=2, value=n); c.font = font(14, True, WHITE); c.fill = fill(PINK if n == "2" else (CYAN if n == "3" else VIO)); c.alignment = CENTER
    merge(I, r, 3, r, 6, t, font(10), WHITE, LEFT)
    I.row_dimensions[r].height = 34; r += 1

H0 = 13   # encabezado de hábitos; hábitos en filas 14..28
merge(I, H0 - 1, 2, H0 - 1, 6, "🎯 MIS HÁBITOS", font(12, True, VIO), None, Alignment(horizontal="left", vertical="center"))
for k, lab in enumerate(["#", "Hábito", "Categoría", "Días al mes", "¿Para qué lo hago? (opcional)"]):
    c = I.cell(row=H0, column=2 + k, value=lab); c.font = font(10, True, WHITE); c.fill = fill(NAVY); c.alignment = CENTER; c.border = BOX
I.row_dimensions[H0].height = 24
for i in range(N_H):
    rr = H0 + 1 + i
    I.cell(row=rr, column=2, value=i + 1).font = font(9, True, GREY)
    I.cell(row=rr, column=2).alignment = CENTER
    for cc in range(2, 7):
        I.cell(row=rr, column=cc).border = BOX
        if cc > 2: I.cell(row=rr, column=cc).fill = fill(WHITE)
    if i < len(EJEMPLOS):
        h, cat, meta, por = EJEMPLOS[i]
        I.cell(row=rr, column=3, value=h); I.cell(row=rr, column=4, value=cat); I.cell(row=rr, column=5, value=meta); I.cell(row=rr, column=6, value=por)
    I.cell(row=rr, column=3).font = font(10, True); I.cell(row=rr, column=3).alignment = LEFT
    I.cell(row=rr, column=4).font = font(10); I.cell(row=rr, column=4).alignment = CENTER
    I.cell(row=rr, column=5).font = font(11, True, VIO); I.cell(row=rr, column=5).alignment = CENTER
    I.cell(row=rr, column=6).font = font(9, False, GREY, True); I.cell(row=rr, column=6).alignment = LEFT
    I.row_dimensions[rr].height = 22
dv_list(I, '"' + ",".join(CATS) + '"', f"D{H0+1}:D{H0+N_H}", "Elige una categoría")
dvn = DataValidation(type="whole", operator="between", formula1="1", formula2="31", allow_blank=True, showErrorMessage=True,
                     errorTitle="Días al mes", error="Escribe un número del 1 al 31")
I.add_data_validation(dvn); dvn.add(f"E{H0+1}:E{H0+N_H}")
IR = lambda i: H0 + 1 + i     # fila en Inicio del hábito i

G0 = H0 + N_H + 2   # metas grandes
merge(I, G0, 2, G0, 6, "🚀 MIS 3 METAS GRANDES DE " + str(YEAR), font(12, True, PINK), None, Alignment(horizontal="left", vertical="center"))
I.cell(row=G0, column=2).value = '="🚀 MIS 3 METAS GRANDES DE "&$D$5'
for k, lab in enumerate(["#", "Mi meta", "¿Por qué me importa?", "", "¿Qué hábito me acerca?"]):
    c = I.cell(row=G0 + 1, column=2 + k, value=lab or None); c.font = font(10, True, WHITE); c.fill = fill(PINK); c.alignment = CENTER; c.border = BOX
I.merge_cells(start_row=G0 + 1, start_column=4, end_row=G0 + 1, end_column=5)
metas_ej = [("Correr mis primeros 5 km", "Demostrarme que puedo", "🚶 Caminar 30 minutos"),
            ("Ahorrar para viajar en diciembre", "Me lo merezco", "💸 Cero gastos hormiga"),
            ("Leer 12 libros", "Quiero aprender cosas nuevas", "📖 Leer 10 minutos")]
for i in range(3):
    rr = G0 + 2 + i
    I.cell(row=rr, column=2, value=i + 1).font = font(11, True, PINK); I.cell(row=rr, column=2).alignment = CENTER
    I.merge_cells(start_row=rr, start_column=4, end_row=rr, end_column=5)
    for cc in range(2, 7):
        I.cell(row=rr, column=cc).border = BOX
        if cc > 2: I.cell(row=rr, column=cc).fill = fill(WHITE)
    for cc in (3, 4, 6): I.cell(row=rr, column=cc).alignment = LEFT; I.cell(row=rr, column=cc).font = font(10, cc == 3)
    if EJ:
        I.cell(row=rr, column=3, value=metas_ej[i][0]); I.cell(row=rr, column=4, value=metas_ej[i][1]); I.cell(row=rr, column=6, value=metas_ej[i][2])
    I.row_dimensions[rr].height = 26

T0 = G0 + 6
I.cell(row=T0, column=2, value="💡 TRUCOS").font = font(12, True, VIO)
tips = ["📱 En el celular: abre el archivo con la app de Google Sheets o de Excel. Para marcar, toca la casilla y elige ✓.",
        "☁️ Google Sheets: en drive.google.com toca «Nuevo → Subir archivo», ábrelo y luego «Archivo → Guardar como Hojas de cálculo de Google».",
        "🔁 ¿Quieres casillas de verificación en Google Sheets? Selecciona los días y ve a «Insertar → Casilla de verificación». También cuentan.",
        "🎨 El día de hoy se ilumina en celeste. Las casillas que marcas se pintan solas y tu racha 🔥 sigue aunque cambie el mes.",
        "📆 ¿Termina el año? Cambia el año arriba, borra tus ✓ y empieza de nuevo. La hoja es tuya para siempre.",
        "🖨️ ¿Prefieres papel? En la carpeta viene la versión imprimible en PDF."]
for k, t in enumerate(tips):
    merge(I, T0 + 1 + k, 2, T0 + 1 + k, 6, t, font(9, False, NAVY), WHITE, LEFT)
    I.row_dimensions[T0 + 1 + k].height = 26
merge(I, T0 + 8, 2, T0 + 8, 6, "Hecho con 💜 por Pixelia · pixeliadigital.app", font(9, True, VIO), None, CENTER)

I.page_setup.orientation = 'portrait'; I.sheet_properties.pageSetUpPr.fitToPage = True; I.page_setup.fitToWidth = 1; I.page_setup.fitToHeight = 0

# ======================= MESES =======================
C_HAB, C_META, C_D1 = 2, 3, 4           # B, C, D..AH
C_DN = C_D1 + 30                        # AH
C_HECHOS, C_PCT, C_RACHA, C_MEJOR, C_MSG = 35, 36, 37, 38, 39   # AI..AM
H1 = 41                                 # AO: rachas (31 columnas) AO..BS
C_CAP, C_MET, C_MAXP, C_MINP = 72, 73, 74, 75                   # BT..BW
R_TOP, R_HAB = 9, 10                    # fila de días, primera fila de hábito
R_LAST = R_HAB + N_H - 1                # 24
R_DIA, R_ANIMO = R_LAST + 1, R_LAST + 2 # 25, 26
P = {k: f"${L(41 + j)}$2" for j, k in enumerate(["mes", "anio", "ini", "dim", "pas", "est", "avg", "av", "ritmo", "cap", "met"])}
P["hoy"] = "$AO$3"
D1, DN = L(C_D1), L(C_DN)
def mark(ref): return f"AND({ref}<>\"\",{ref}<>FALSE)"

meses = []
for m in range(1, 13):
    ws = wb.create_sheet(MESES[m - 1]); meses.append(ws)
    ws.sheet_view.showGridLines = False; ws.sheet_properties.tabColor = [VIO, PINK, CYAN][(m - 1) % 3]
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions[L(C_HAB)].width = 30
    ws.column_dimensions[L(C_META)].width = 6
    for c in range(C_D1, C_DN + 1): ws.column_dimensions[L(c)].width = 3.6
    widths(ws, {L(C_HECHOS): 8, L(C_PCT): 7, L(C_RACHA): 8, L(C_MEJOR): 8, L(C_MSG): 22, "AN": 2})
    for c in range(41, 80): ws.column_dimensions[L(c)].hidden = True
    paint(ws, 1, 40, 1, C_MSG + 1, SOFT)

    # parámetros ocultos
    ws["AO1"] = "parámetros (no tocar)"
    ws[P["mes"].replace("$", "")] = m
    ws[P["anio"].replace("$", "")] = "=Inicio!$D$5"
    ws[P["ini"].replace("$", "")] = f"=DATE({P['anio']},{P['mes']},1)"
    ws[P["dim"].replace("$", "")] = f"=DAY(DATE({P['anio']},{P['mes']}+1,0))"
    ws["AO3"] = f"={HOY}"
    ws[P["pas"].replace("$", "")] = f"=IF({P['hoy']}<{P['ini']},0,IF({P['hoy']}>={P['ini']}+{P['dim']},{P['dim']},DAY({P['hoy']})))"
    ws[P["est"].replace("$", "")] = f"=IF({P['hoy']}<{P['ini']},-1,IF({P['hoy']}>={P['ini']}+{P['dim']},1,0))"
    ws[P["avg"].replace("$", "")] = f"=IF(COUNT($AO${R_ANIMO}:$BS${R_ANIMO})=0,\"\",AVERAGE($AO${R_ANIMO}:$BS${R_ANIMO}))"
    capR, metR = f"${L(C_CAP)}${R_HAB}:${L(C_CAP)}${R_LAST}", f"${L(C_MET)}${R_HAB}:${L(C_MET)}${R_LAST}"
    ws[P["av"].replace("$", "")] = f"=IF(SUM({metR})=0,\"\",SUM({capR})/SUM({metR}))"
    ws[P["ritmo"].replace("$", "")] = f"=IF(OR({P['pas']}=0,SUM({metR})=0),\"\",MIN(1.2,SUM({capR})/(SUM({metR})*{P['pas']}/{P['dim']})))"
    ws[P["cap"].replace("$", "")] = f"=IF({P['est']}=-1,0,SUM({capR}))"
    ws[P["met"].replace("$", "")] = f"=IF({P['est']}=-1,0,SUM({metR}))"

    # título
    merge(ws, 2, 2, 3, 2, f'="{MESES[m-1].upper()} "&{P["anio"]}', font(24, True, WHITE), VIO, LEFT)
    merge(ws, 4, 2, 4, 2, "Marca ✓ cada día que cumplas", font(9, False, WHITE, True), VIO, LEFT)
    merge(ws, 2, 3, 4, 3, None, None, VIO)
    ws.row_dimensions[2].height = 16; ws.row_dimensions[3].height = 30; ws.row_dimensions[4].height = 16
    # tarjetas
    HR, BR = f"$B${R_HAB}:$B${R_LAST}", f"${L(C_MEJOR)}${R_HAB}:${L(C_MEJOR)}${R_LAST}"
    MAXP, MINP = f"${L(C_MAXP)}${R_HAB}:${L(C_MAXP)}${R_LAST}", f"${L(C_MINP)}${R_HAB}:${L(C_MINP)}${R_LAST}"
    av, est, ritmo = P["av"], P["est"], P["ritmo"]
    card(ws, 2, 5, 10, "AVANCE DEL MES", VIO, f'=IF(OR({est}=-1,{av}=""),"—",{av})',
         f'=IF(OR({est}=-1,{av}=""),"",REPT("▰",ROUND({av}*10,0))&REPT("▱",10-ROUND({av}*10,0)))', "0%", 20)
    card(ws, 2, 11, 16, "MI NIVEL", PINK,
         f'=IF({est}=-1,"⏳ Pronto",IF({ritmo}="","—",IF({ritmo}<0.3,"🌱 Semilla",IF({ritmo}<0.55,"🚶 En camino",IF({ritmo}<0.8,"🔥 Constante","🚀 Imparable")))))',
         "según tu ritmo", None, 13)
    card(ws, 2, 17, 22, "🔥 MEJOR RACHA", "FF8A3D", f'=MAX({BR})&IF(MAX({BR})=1," día"," días")',
         f'=IF(MAX({BR})=0,"¡Empieza hoy!",INDEX({HR},MATCH(MAX({BR}),{BR},0)))', None, 16)
    card(ws, 2, 23, 27, "MI ÁNIMO", CYAN, f'=IF({P["avg"]}="","—",CHOOSE(ROUND({P["avg"]},0),"😫","😞","😐","😊","😍"))',
         f'=IF({P["avg"]}="","regístralo abajo",COUNT($AO${R_ANIMO}:$BS${R_ANIMO})&" días")', None, 18)
    card(ws, 2, 28, 34, "⭐ HÁBITO ESTRELLA", MINT, f'=IF(OR({est}=-1,MAX({MAXP})<=0),"—",INDEX({HR},MATCH(MAX({MAXP}),{MAXP},0)))',
         f'=IF(OR({est}=-1,MAX({MAXP})<=0),"",TEXT(MAX({MAXP}),"0%")&" cumplido")', None, 9)
    card(ws, 2, 35, 39, "🛟 A RESCATAR", AMBER, f'=IF(OR({est}=-1,MIN({MINP})>=1,SUM({metR})=0),"—",INDEX({HR},MATCH(MIN({MINP}),{MINP},0)))',
         f'=IF(OR({est}=-1,MIN({MINP})>=1,SUM({metR})=0),"",TEXT(MIN({MINP}),"0%")&" · ¡dale cariño!")', None, 9)
    # mensaje del mes
    msg = (f'=IF({est}=-1,"⏳ Este mes todavía no empieza. Cuando llegue, ¡vamos con todo!",'
           f'IF(SUM({capR})=0,IF({est}=1,"📌 Este mes quedó en blanco. No pasa nada: lo importante es volver.","👋 Empieza hoy con UN solo hábito. El resto viene después."),'
           f'IF({ritmo}<0.3,"🌱 Vas sembrando. Elige 1 hábito y no lo sueltes esta semana.",'
           f'IF({ritmo}<0.55,"🚶 Vas en camino. Ya hiciste lo más difícil: empezar.",'
           f'IF({ritmo}<0.8,"🔥 ¡Estás constante! Tu yo del próximo mes te lo va a agradecer.",'
           f'"🚀 ¡Imparable! Esto ya no es fuerza de voluntad, es tu estilo de vida.")))))')
    merge(ws, 6, 2, 6, C_MSG, msg, font(11, True, VIO2), LILA, LEFT)
    ws.row_dimensions[5].height = 6; ws.row_dimensions[6].height = 26; ws.row_dimensions[7].height = 6

    # encabezados de la tabla
    for c, lab in [(C_HAB, "MIS HÁBITOS"), (C_META, "META"), (C_HECHOS, "HECHOS"), (C_PCT, "%"), (C_RACHA, "🔥 RACHA"), (C_MEJOR, "🏆 MEJOR"), (C_MSG, "¿CÓMO VOY?")]:
        merge(ws, 8, c, 9, c, lab, font(9, True, WHITE), NAVY, CENTER, border=True)
    for k in range(31):
        c = C_D1 + k; col = L(c)
        d = ws.cell(row=R_TOP, column=c, value=f'=IF({k+1}<={P["dim"]},{P["ini"]}+{k},"")')
        d.number_format = "d"; d.font = font(9, True, WHITE); d.fill = fill(NAVY); d.alignment = CENTER; d.border = BOX
        w = ws.cell(row=8, column=c, value=f'=IF({col}{R_TOP}="","",CHOOSE(WEEKDAY({col}{R_TOP}),"D","L","M","M","J","V","S"))')
        w.font = font(8, True, "C9C2FF"); w.fill = fill(NAVY); w.alignment = CENTER; w.border = BOX
    ws.row_dimensions[8].height = 15; ws.row_dimensions[9].height = 18

    # hábitos
    prev = meses[m - 2] if m > 1 else None
    for i in range(N_H):
        r = R_HAB + i; ir = IR(i)
        b = ws.cell(row=r, column=C_HAB, value=f'=IF(Inicio!$C${ir}="","",Inicio!$C${ir})')
        b.font = font(10, True); b.alignment = LEFT; b.fill = fill(WHITE); b.border = BOX
        ws.cell(row=r, column=C_META, value=f'=IF(B{r}="","",MIN(IF(Inicio!$E${ir}="",20,Inicio!$E${ir}),{P["dim"]}))')
        ws.cell(row=r, column=C_META).font = font(10, True, VIO); ws.cell(row=r, column=C_META).alignment = CENTER
        ws.cell(row=r, column=C_META).fill = fill(WHITE); ws.cell(row=r, column=C_META).border = BOX
        for k in range(31):
            x = ws.cell(row=r, column=C_D1 + k); x.border = BOX; x.alignment = CENTER; x.font = font(10, True, WHITE); x.fill = fill(WHITE)
        rng = f"{D1}{r}:{DN}{r}"
        ws.cell(row=r, column=C_HECHOS, value=f'=IF(B{r}="","",SUMPRODUCT(({rng}<>"")*({rng}<>FALSE)*(${D1}${R_TOP}:${DN}${R_TOP}<>"")))')
        ws.cell(row=r, column=C_PCT, value=f'=IF(OR(B{r}="",N(C{r})=0),"",MIN(1,{L(C_HECHOS)}{r}/C{r}))').number_format = "0%"
        hr = f"$AO{r}:$BS{r}"
        ws.cell(row=r, column=C_RACHA, value=(f'=IF(B{r}="","",IF({est}=1,INDEX({hr},{P["dim"]}),IF({est}=0,'
                                              f'MAX(INDEX({hr},{P["pas"]}),IF({P["pas"]}>1,INDEX({hr},{P["pas"]}-1),0)),0)))'))
        ws.cell(row=r, column=C_MEJOR, value=f'=IF(B{r}="","",MAX({hr}))')
        h, c_ = f"{L(C_HECHOS)}{r}", f"C{r}"
        ws.cell(row=r, column=C_MSG, value=(f'=IF(B{r}="","",IF({h}>={c_},"✅ ¡Meta cumplida!",IF({est}=-1,"⏳ Pronto",'
                                            f'IF({est}=1,"📌 Cerró en "&TEXT({L(C_PCT)}{r},"0%"),'
                                            f'IF({h}>={c_}*{P["pas"]}/{P["dim"]},"👍 A buen ritmo",'
                                            f'IF({c_}-{h}>{P["dim"]}-{P["pas"]}+1,"💪 Suma lo que puedas","⚡ Te faltan "&({c_}-{h})))))))'))
        for c in (C_HECHOS, C_PCT, C_RACHA, C_MEJOR):
            x = ws.cell(row=r, column=c); x.font = font(10, True, NAVY); x.alignment = CENTER; x.fill = fill(WHITE); x.border = BOX
        ws.cell(row=r, column=C_RACHA).font = font(10, True, "E8590C")
        ws.cell(row=r, column=C_MSG).font = font(8, False, NAVY); ws.cell(row=r, column=C_MSG).alignment = LEFT
        ws.cell(row=r, column=C_MSG).fill = fill(WHITE); ws.cell(row=r, column=C_MSG).border = BOX
        # rachas (ocultas): la del día 1 continúa la racha del último día del mes anterior
        for k in range(31):
            col = L(C_D1 + k); hc = H1 + k
            if k == 0:
                carry = f'IFERROR(INDEX(\'{prev.title}\'!$AO{r}:$BS{r},\'{prev.title}\'!$AR$2),0)' if prev else "0"
                f_ = f'=IF(AND({mark(col + str(r))},{col}${R_TOP}<>""),1+{carry},0)'
            else:
                f_ = f'=IF(AND({mark(col + str(r))},{col}${R_TOP}<>""),{L(hc-1)}{r}+1,0)'
            ws.cell(row=r, column=hc, value=f_)
        ws.cell(row=r, column=C_CAP, value=f'=IF(B{r}="",0,MIN(N({h}),N({c_})))')
        ws.cell(row=r, column=C_MET, value=f'=IF(B{r}="",0,N({c_}))')
        ws.cell(row=r, column=C_MAXP, value=f'=IF({L(C_PCT)}{r}="",-1,{L(C_PCT)}{r})')
        ws.cell(row=r, column=C_MINP, value=f'=IF({L(C_PCT)}{r}="",2,{L(C_PCT)}{r})')
        ws.row_dimensions[r].height = 21
    dv_list(ws, '"✓"', f"{D1}{R_HAB}:{DN}{R_LAST}", "Elige ✓ (o escribe x)")

    # % del día y ánimo
    merge(ws, R_DIA, 2, R_DIA, 3, "% DEL DÍA", font(9, True, WHITE), VIO, LEFT)
    merge(ws, R_ANIMO, 2, R_ANIMO, 3, "MI ÁNIMO HOY 😊", font(9, True, WHITE), CYAN, LEFT)
    for k in range(31):
        c = C_D1 + k; col = L(c)
        f_ = (f'=IF(OR({col}${R_TOP}="",{col}${R_TOP}>{P["hoy"]},COUNTIF($B${R_HAB}:$B${R_LAST},"?*")=0),"",'
              f'SUMPRODUCT(({col}{R_HAB}:{col}{R_LAST}<>"")*({col}{R_HAB}:{col}{R_LAST}<>FALSE)*($B${R_HAB}:$B${R_LAST}<>""))/COUNTIF($B${R_HAB}:$B${R_LAST},"?*"))')
        x = ws.cell(row=R_DIA, column=c, value=f_); x.number_format = "0%"; x.font = font(6, True, NAVY); x.alignment = CENTER; x.border = BOX
        y = ws.cell(row=R_ANIMO, column=c); y.border = BOX; y.alignment = CENTER; y.font = font(10); y.fill = fill(WHITE)
        ws.cell(row=R_ANIMO, column=H1 + k, value=f'=IFERROR(MATCH({col}{R_ANIMO},{{"😫","😞","😐","😊","😍"}},0),"")')
    dv_list(ws, '"' + ",".join(reversed(MOODS)) + '"', f"{D1}{R_ANIMO}:{DN}{R_ANIMO}", "¿Cómo te sentiste hoy?")
    leyenda = "😍 genial · 😊 bien · 😐 normal · 😞 bajón · 😫 agotada"
    merge(ws, R_DIA, C_HECHOS, R_ANIMO, C_MSG, leyenda, font(8, False, GREY, True), WHITE, CENTER, border=True)
    ws.row_dimensions[R_DIA].height = 18; ws.row_dimensions[R_ANIMO].height = 22

    # reflexión + qué me hizo fallar
    R0 = R_ANIMO + 2
    merge(ws, R0, 2, R0, 18, "📝 MI REFLEXIÓN DEL MES", font(10, True, WHITE), PINK, LEFT)
    preguntas = ["¿Qué me salió bien?", "¿Qué me costó más?", "¿Qué hábito cambió más mi día?", "¿Qué quiero sentir más el próximo mes?"]
    for k, q in enumerate(preguntas):
        rr = R0 + 1 + k
        merge(ws, rr, 2, rr, 2, q, font(9, True, NAVY), LILA, LEFT, border=True)
        merge(ws, rr, 3, rr, 18, None, font(9), WHITE, LEFT, border=True)
        ws.row_dimensions[rr].height = 30
    merge(ws, R0, 20, R0, C_MSG, "🧩 ¿QUÉ ME HIZO FALLAR? (y cómo lo arreglo)", font(10, True, WHITE), AMBER, LEFT)
    for (c1, c2, lab) in [(20, 26, "Hábito"), (27, 33, "¿Por qué fallé?"), (34, C_MSG, "Mi plan")]:
        merge(ws, R0 + 1, c1, R0 + 1, c2, lab, font(9, True, NAVY), "FFF3D1", CENTER, border=True)
        for k in range(3): merge(ws, R0 + 2 + k, c1, R0 + 2 + k, c2, None, font(9), WHITE, LEFT, border=True)

    # formato condicional
    grid = f"{D1}{R_HAB}:{DN}{R_LAST}"
    ws.conditional_formatting.add(grid, FormulaRule(formula=[f'{D1}${R_TOP}=""'], fill=fill(OFF), stopIfTrue=True))
    ws.conditional_formatting.add(grid, FormulaRule(formula=[f'AND({D1}{R_HAB}<>"",{D1}{R_HAB}<>FALSE)'], fill=fill(VIO), font=Font(color=WHITE, bold=True)))
    ws.conditional_formatting.add(grid, FormulaRule(formula=[f'{D1}${R_TOP}={P["hoy"]}'], fill=fill("DDF8FD")))
    ws.conditional_formatting.add(grid, FormulaRule(formula=[f'AND($B{R_HAB}="",{D1}${R_TOP}<>"")'], fill=fill("FBFAFE")))
    ws.conditional_formatting.add(f"{D1}{R_TOP}:{DN}{R_TOP}", FormulaRule(formula=[f'AND({D1}{R_TOP}<>"",{D1}{R_TOP}={P["hoy"]})'], fill=fill(CYAN), font=Font(color=NAVY, bold=True)))
    ws.conditional_formatting.add(f"{D1}8:{DN}8", FormulaRule(formula=[f'OR({D1}8="S",{D1}8="D")'], font=Font(color="FF9CEB", bold=True)))
    ws.conditional_formatting.add(f"{D1}{R_ANIMO}:{DN}{R_ANIMO}", FormulaRule(formula=[f'{D1}${R_TOP}=""'], fill=fill(OFF)))
    ws.conditional_formatting.add(f"{D1}{R_DIA}:{DN}{R_DIA}", ColorScaleRule(start_type="num", start_value=0, start_color="FFFFFF", mid_type="num", mid_value=0.5, mid_color="C9BCFF", end_type="num", end_value=1, end_color="7C5CFF"))
    pc = f"{L(C_PCT)}{R_HAB}:{L(C_PCT)}{R_LAST}"
    ws.conditional_formatting.add(pc, FormulaRule(formula=[f'AND({L(C_PCT)}{R_HAB}<>"",{L(C_PCT)}{R_HAB}>=1)'], fill=fill("C9F5E2"), font=Font(color="0B6B47", bold=True), stopIfTrue=True))
    ws.conditional_formatting.add(pc, FormulaRule(formula=[f'AND({L(C_PCT)}{R_HAB}<>"",{L(C_PCT)}{R_HAB}>=0.6)'], fill=fill("E6FBF2"), stopIfTrue=True))
    ws.conditional_formatting.add(pc, FormulaRule(formula=[f'AND({L(C_PCT)}{R_HAB}<>"",{est}<>-1,{L(C_PCT)}{R_HAB}<0.3)'], fill=fill("FFE3EC")))
    msgc = f"{L(C_MSG)}{R_HAB}:{L(C_MSG)}{R_LAST}"
    ws.conditional_formatting.add(msgc, FormulaRule(formula=[f'LEFT({L(C_MSG)}{R_HAB},1)="✅"'], font=Font(color="0B6B47", bold=True)))
    ws.conditional_formatting.add(msgc, FormulaRule(formula=[f'LEFT({L(C_MSG)}{R_HAB},1)="⚡"'], font=Font(color="C2410C", bold=True)))

    ws.freeze_panes = "D1"
    ws.page_setup.orientation = "landscape"; ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_area = f"A1:{L(C_MSG)}{R0 + 5}"

# ======================= MI AÑO =======================
Y = wb.create_sheet("Mi Año", 1); Y.sheet_view.showGridLines = False; Y.sheet_properties.tabColor = PINK
widths(Y, {"A": 2, "B": 30, "C": 10, "D": 16, "E": 11, "F": 9, "G": 30, "H": 2})
for c in range(9, 22): Y.column_dimensions[L(c)].width = 7
for c in range(22, 30): Y.column_dimensions[L(c)].hidden = True
paint(Y, 1, 70, 1, 21, SOFT)
merge(Y, 2, 2, 3, 7, '="MI "&Inicio!$D$5&" EN HÁBITOS 🚀"', font(22, True, WHITE), PINK, LEFT)
Y.row_dimensions[2].height = 22; Y.row_dimensions[3].height = 26
# tabla mensual (filas 10..21)
T = 10
for k, lab in enumerate(["Mes", "Avance", "Nivel", "🔥 Mejor racha", "Ánimo", "⭐ Hábito estrella"]):
    merge(Y, T - 1, 2 + k, T - 1, 2 + k, lab, font(9, True, WHITE), NAVY, CENTER, border=True)
merge(Y, T - 2, 2, T - 2, 7, "📅 MES A MES", font(12, True, VIO), None, Alignment(horizontal="left", vertical="center"))
for m in range(12):
    r = T + m; q = f"'{MESES[m]}'!"
    est = f"{q}$AT$2"
    vals = [MESES[m], f'=IF({est}=-1,"",{q}$AV$2)', f'=IF({est}=-1,"",{q}$K$3)', f'=IF({est}=-1,"",MAX({q}$AL${R_HAB}:$AL${R_LAST}))',
            f'=IF({est}=-1,"",{q}$W$3)', f'=IF({est}=-1,"",{q}$AB$3)']
    for k, v in enumerate(vals):
        c = Y.cell(row=r, column=2 + k, value=v); c.border = BOX; c.fill = fill(WHITE); c.alignment = CENTER; c.font = font(10, k in (0, 1))
    Y.cell(row=r, column=2).alignment = LEFT; Y.cell(row=r, column=7).alignment = LEFT; Y.cell(row=r, column=7).font = font(9)
    Y.cell(row=r, column=3).number_format = "0%"
    Y.cell(row=r, column=22, value=f"={q}$AX$2"); Y.cell(row=r, column=23, value=f"={q}$AY$2"); Y.cell(row=r, column=24, value=f"=IF({q}$AU$2=\"\",\"\",{q}$AU$2)")
    Y.row_dimensions[r].height = 20
Y.conditional_formatting.add(f"C{T}:C{T+11}", ColorScaleRule(start_type="num", start_value=0, start_color="FFE3EC", mid_type="num", mid_value=0.5, mid_color="FFF6D6", end_type="num", end_value=1, end_color="B8F0D8"))
# tarjetas del año
AV, MES_R, RACHA_R = f"$C${T}:$C${T+11}", f"$B${T}:$B${T+11}", f"$E${T}:$E${T+11}"
card(Y, 5, 2, 2, "AVANCE DEL AÑO", VIO, f'=IF(SUM($W${T}:$W${T+11})=0,"—",SUM($V${T}:$V${T+11})/SUM($W${T}:$W${T+11}))',
     f'=IF(SUM($W${T}:$W${T+11})=0,"tu año empieza pronto","de todas tus metas hasta hoy")', "0%", 18)
card(Y, 5, 4, 4, "🏆 MEJOR MES", MINT, f'=IF(MAX({AV})<=0,"—",INDEX({MES_R},MATCH(MAX({AV}),{AV},0)))',
     f'=IF(MAX({AV})<=0,"",TEXT(MAX({AV}),"0%"))', None, 13)
card(Y, 5, 5, 6, "🔥 RACHA RÉCORD", "FF8A3D", f'=MAX({RACHA_R})&" días"', "seguidos", None, 14)
card(Y, 5, 7, 7, "ÁNIMO DEL AÑO", CYAN, f'=IF(COUNT($X${T}:$X${T+11})=0,"—",CHOOSE(ROUND(AVERAGE($X${T}:$X${T+11}),0),"😫","😞","😐","😊","😍"))',
     "promedio de tus días", None, 16)
Y.row_dimensions[6].height = 30
# gráfico
ch = BarChart(); ch.type = "col"; ch.title = "Avance por mes"; ch.style = 10; ch.legend = None
ch.add_data(Reference(Y, min_col=3, min_row=T, max_row=T + 11), titles_from_data=False)
ch.set_categories(Reference(Y, min_col=2, min_row=T, max_row=T + 11))
ch.y_axis.scaling.min = 0; ch.y_axis.scaling.max = 1; ch.y_axis.number_format = "0%"; ch.y_axis.majorGridlines = None
ch.series[0].graphicalProperties.solidFill = VIO; ch.series[0].graphicalProperties.line.solidFill = VIO
ch.height = 7.2; ch.width = 15.5
Y.add_chart(ch, "I8")
# mapa de calor hábito × mes
M0 = T + 14
merge(Y, M0 - 1, 2, M0 - 1, 7, "🗓️ TU AÑO HÁBITO POR HÁBITO", font(12, True, VIO), None, Alignment(horizontal="left", vertical="center"))
hdr = ["Hábito"] + [x[:3] for x in MESES] + ["Año"]
cols = [2] + list(range(9, 21)) + [21]
for c, lab in zip(cols, hdr):
    merge(Y, M0, c, M0, c, lab, font(9, True, WHITE), NAVY, CENTER, border=True)
merge(Y, M0, 3, M0, 8, "Categoría", font(9, True, WHITE), NAVY, CENTER, border=True)
for i in range(N_H):
    r = M0 + 1 + i; ir = IR(i)
    c = Y.cell(row=r, column=2, value=f'=IF(Inicio!$C${ir}="","",Inicio!$C${ir})'); c.font = font(9, True); c.alignment = LEFT; c.fill = fill(WHITE); c.border = BOX
    merge(Y, r, 3, r, 8, f'=IF(Inicio!$C${ir}="","",Inicio!$D${ir})', font(9, False, GREY), WHITE, CENTER, border=True)
    for m in range(12):
        q = f"'{MESES[m]}'!"
        x = Y.cell(row=r, column=9 + m, value=f'=IF({q}$AT$2=-1,"",{q}$AJ${R_HAB+i})')
        x.number_format = "0%"; x.font = font(8, True); x.alignment = CENTER; x.border = BOX; x.fill = fill(WHITE)
    x = Y.cell(row=r, column=21, value=f'=IF(COUNT(I{r}:T{r})=0,"",AVERAGE(I{r}:T{r}))')
    x.number_format = "0%"; x.font = font(9, True, VIO); x.alignment = CENTER; x.border = BOX; x.fill = fill(LILA)
    Y.row_dimensions[r].height = 19
Y.conditional_formatting.add(f"I{M0+1}:U{M0+N_H}", FormulaRule(formula=[f'AND(I{M0+1}<>"",I{M0+1}>=0.7)'], font=Font(color=WHITE, bold=True)))
Y.conditional_formatting.add(f"I{M0+1}:U{M0+N_H}", ColorScaleRule(start_type="num", start_value=0, start_color="FFFFFF", mid_type="num", mid_value=0.5, mid_color="D7CCFF", end_type="num", end_value=1, end_color="7C5CFF"))
# por categoría
K0 = M0 + N_H + 3
merge(Y, K0 - 1, 2, K0 - 1, 7, "🧩 ¿EN QUÉ ÁREA DE MI VIDA VOY MEJOR?", font(12, True, VIO), None, Alignment(horizontal="left", vertical="center"))
for c, lab in [(2, "Categoría"), (3, "Hábitos"), (4, "Avance del año")]:
    merge(Y, K0, c, K0, c, lab, font(9, True, WHITE), NAVY, CENTER, border=True)
merge(Y, K0, 5, K0, 7, "", font(9, True, WHITE), NAVY, CENTER, border=True)
CATR, YR = f"Inicio!$D${IR(0)}:$D${IR(N_H-1)}", f"$U${M0+1}:$U${M0+N_H}"
for k, cat in enumerate(CATS):
    r = K0 + 1 + k
    Y.cell(row=r, column=2, value=cat).font = font(10, True)
    Y.cell(row=r, column=3, value=f'=COUNTIFS({CATR},$B{r},Inicio!$C${IR(0)}:$C${IR(N_H-1)},"?*")')
    Y.cell(row=r, column=4, value=f'=IFERROR(AVERAGEIF({CATR},$B{r},{YR}),"")').number_format = "0%"
    merge(Y, r, 5, r, 7, f'=IF(D{r}="","",REPT("█",ROUND(D{r}*20,0)))', font(9, False, VIO), WHITE, Alignment(horizontal="left", vertical="center"), border=True)
    for c in (2, 3, 4):
        x = Y.cell(row=r, column=c); x.border = BOX; x.fill = fill(WHITE); x.alignment = CENTER if c > 2 else LEFT
    Y.cell(row=r, column=4).font = font(10, True, VIO)
    Y.row_dimensions[r].height = 19
Y.freeze_panes = "C1"
Y.page_setup.orientation = "landscape"; Y.sheet_properties.pageSetUpPr.fitToPage = True; Y.page_setup.fitToWidth = 1; Y.page_setup.fitToHeight = 0

# ======================= EJEMPLO =======================
if EJ:
    random.seed(7)
    import datetime as dt
    hoy = dt.date(*HOY_EJEMPLO)
    prob = [0.8, 0.62, 0.42, 0.3, 0.55, 0.38, 0.5]
    for m in range(1, 4):
        ws = meses[m - 1]
        dim = (dt.date(YEAR, m % 12 + 1, 1) - dt.timedelta(days=1)).day if m < 12 else 31
        for d in range(1, dim + 1):
            if dt.date(YEAR, m, d) > hoy: break
            mejora = 0.06 * (m - 1)
            for i, p in enumerate(prob):
                prevv = ws.cell(row=R_HAB + i, column=C_D1 + d - 2).value if d > 1 else None
                pp = min(0.97, p + mejora + (0.12 if prevv else -0.05))
                if random.random() < pp: ws.cell(row=R_HAB + i, column=C_D1 + d - 1, value="✓")
            ws.cell(row=R_ANIMO, column=C_D1 + d - 1, value=random.choices(MOODS, [1, 2, 4, 6, 4 + m])[0])
    E = meses[0]; R0 = R_ANIMO + 2
    for k, t in enumerate(["Tomar agua ya me sale solo 💧", "Las caminatas cuando llovía", "Leer antes de dormir: duermo mejor", "Más calma y menos celular"]):
        E.cell(row=R0 + 1 + k, column=3, value=t)
    for k, (h, p, plan) in enumerate([("🚶 Caminar", "Lluvia y flojera", "Video de 20 min en casa"), ("📵 Sin celular", "Me quedaba en reels", "Cargarlo fuera del cuarto")]):
        E.cell(row=R0 + 2 + k, column=20, value=h); E.cell(row=R0 + 2 + k, column=27, value=p); E.cell(row=R0 + 2 + k, column=34, value=plan)
    wb.active = wb.sheetnames.index("Marzo")
else:
    wb.active = 0

wb.calculation.fullCalcOnLoad = True
wb.save(OUT)
print("ok", OUT)
