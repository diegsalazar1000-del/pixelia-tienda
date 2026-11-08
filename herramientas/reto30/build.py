"""Reto 30 Días · Pixelia — REGALO (diseño 100% propio, no viene del PLR del tracker).
Hoja vertical: los días van hacia abajo y los hábitos en columnas. Marca ✓ y se calculan solos
la racha 🔥, la mejor racha 🏆, el % de cada hábito, la barra del reto y un mensaje que cambia.
Uso: python3 build.py salida.xlsx [--ejemplo]
Solo funciones compatibles con Excel y Google Sheets."""
import sys, random
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import FormulaRule
from openpyxl.worksheet.datavalidation import DataValidation
import datetime as dt

OUT = sys.argv[1]; EJ = "--ejemplo" in sys.argv
INK, ORANGE, ORANGE2, CREAM, PEACH, TEAL, TEAL2, GREY, WHITE, LINE, GOLD = (
    "231A3D", "FF6B3D", "E8501F", "FFF8F1", "FFE6D8", "14B8A6", "0F8F82", "8A8299", "FFFFFF", "F1E4D8", "FFC23D")
FN = "Arial"
def font(s=10, b=False, c=INK, i=False): return Font(name=FN, size=s, bold=b, color=c, italic=i)
def fill(c): return PatternFill("solid", fgColor=c)
thin = Side(style="thin", color=LINE)
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
C = Alignment(horizontal="center", vertical="center", wrap_text=True)
Lf = Alignment(horizontal="left", vertical="center", wrap_text=True, indent=1)

HAB = ["💧 Tomar 2 L de agua", "🚶 Caminar 20 min", "📖 Leer 10 páginas", "😴 Dormir antes de las 11", "💸 Cero gastos hormiga"]
N = 30; NH = 5
R_NAME, R_PCT, R_RACHA, R_BEST = 10, 11, 12, 13
R0 = 15; RN = R0 + N - 1            # filas de los días
HC = [4, 5, 6, 7, 8]                # columnas D..H = hábitos
SC = [11, 12, 13, 14, 15]           # columnas K..O = ayudante de racha (ocultas)
AC = 16                             # P = ¿marcó algo ese día? (oculta)
col = lambda c: chr(64 + c)
START = "$D$6"

wb = Workbook(); ws = wb.active; ws.title = "Mi Reto 30 Días"
ws.sheet_view.showGridLines = False; ws.sheet_properties.tabColor = ORANGE
for k, v in {"A": 2, "B": 7, "C": 9, "D": 15, "E": 15, "F": 15, "G": 15, "H": 15, "I": 9, "J": 2}.items(): ws.column_dimensions[k].width = v
for c in SC + [AC]: ws.column_dimensions[col(c)].hidden = True

def merge(r1, c1, r2, c2, v=None, f=None, bg=None, al=C, fmt=None):
    if (r1, c1) != (r2, c2): ws.merge_cells(start_row=r1, start_column=c1, end_row=r2, end_column=c2)
    x = ws.cell(row=r1, column=c1)
    if v is not None: x.value = v
    if f: x.font = f
    x.alignment = al
    if fmt: x.number_format = fmt
    if bg:
        for r in range(r1, r2 + 1):
            for cc in range(c1, c2 + 1): ws.cell(row=r, column=cc).fill = fill(bg)
    return x

for r in range(1, RN + 8):
    for c in range(1, 11): ws.cell(row=r, column=c).fill = fill(CREAM)

# --- encabezado ---
merge(1, 2, 1, 9, "🔥 RETO 30 DÍAS", font(22, True, WHITE), ORANGE); ws.row_dimensions[1].height = 40
merge(2, 2, 2, 9, "Marca ✓ cada día. La hoja hace el resto: tu racha, tu % y tu barra se calculan solos.", font(10, False, WHITE, True), ORANGE2)
ws.row_dimensions[2].height = 22

# día del reto (k): con fecha de inicio = días transcurridos; sin fecha = último día marcado
LAST = f"SUMPRODUCT(MAX(${col(AC)}${R0}:${col(AC)}${RN}*$B${R0}:$B${RN}))"
K = f"IF({START}=\"\",{LAST},MAX(0,MIN({N},TODAY()-{START}+1)))"
ws["P2"] = f"={K}"; KC = "$P$2"                     # celda oculta con el día del reto
NAMED = f"COUNTIF($D${R_NAME}:$H${R_NAME},\"?*\")"
TOTAL = f"SUMPRODUCT(($D${R0}:$H${RN}<>\"\")*($D${R_NAME}:$H${R_NAME}<>\"\"))"
ws["P3"] = f"=IF({NAMED}=0,0,{TOTAL}/({NAMED}*{N}))"; PC = "$P$3"   # avance total (0-1)

merge(4, 2, 4, 9, None, None, CREAM)
merge(5, 2, 5, 3, "📅 EMPIEZO EL", font(8, True, WHITE), TEAL)
merge(6, 2, 6, 3, "Escribe la fecha →", font(8, False, GREY, True), WHITE)
merge(5, 4, 5, 4, "FECHA", font(8, True, WHITE), TEAL)
d = ws["D6"]; d.number_format = "DD/MM/YYYY"; d.font = font(11, True, INK); d.alignment = C; d.fill = fill(WHITE); d.border = BOX
if EJ: d.value = dt.date(2027, 1, 1)
merge(5, 5, 5, 6, "📍 VAS EN EL", font(8, True, WHITE), TEAL)
merge(6, 5, 6, 6, f'=IF({KC}=0,"Día 0 de 30","Día "&{KC}&" de 30")', font(12, True, INK), WHITE)
merge(5, 7, 5, 9, "⭐ AVANCE DEL RETO", font(8, True, WHITE), ORANGE)
merge(6, 7, 6, 9, f'=ROUND({PC}*100,0)&"%"', font(14, True, ORANGE2), WHITE)
# barra de avance (texto: funciona igual en Excel y Sheets)
merge(7, 2, 7, 9, f'=REPT("█",ROUND({PC}*30,0))&REPT("░",30-ROUND({PC}*30,0))', font(13, False, ORANGE), WHITE)
ws.row_dimensions[7].height = 24
MSG = (f'=IF({KC}=0,"👉 Pon tu fecha de inicio y marca tu primer ✓. Hoy arranca.",'
       f'IF({KC}>={N},IF({PC}>=0.8,"🏆 ¡LO LOGRASTE! 30 días. Esto ya no es un reto, es tu vida.","🏁 ¡Terminaste los 30 días! Lo que hiciste cuenta. ¿Repetimos?"),'
       f'IF({KC}<=3,"💪 Arrancaste. Lo más difícil (empezar) ya pasó.",'
       f'IF({KC}<=7,"🔥 Primera semana. Tu yo de febrero te lo va a agradecer.",'
       f'IF({KC}<=14,"😎 Dos semanas. Ya no eres el mismo de la libreta abandonada.",'
       f'IF({KC}<=21,"🚀 Mitad del reto pasada. Febrero, tiembla.",'
       f'"🌟 Recta final. Esto ya es tu estilo de vida."))))))')
merge(8, 2, 8, 9, MSG, font(11, True, INK), PEACH); ws.row_dimensions[8].height = 30

# --- nombres de hábitos + resumen por hábito ---
merge(R_NAME, 2, R_NAME, 3, "MIS HÁBITOS ✏️", font(8, True, WHITE), INK)
merge(R_PCT, 2, R_PCT, 3, "✅ Cumplido", font(9, True, INK), WHITE)
merge(R_RACHA, 2, R_RACHA, 3, "🔥 Racha actual", font(9, True, INK), WHITE)
merge(R_BEST, 2, R_BEST, 3, "🏆 Mejor racha", font(9, True, INK), WHITE)
ws.row_dimensions[R_NAME].height = 40
for i, c in enumerate(HC):
    L, S = col(c), col(SC[i])
    x = ws.cell(row=R_NAME, column=c, value=HAB[i]); x.font = font(9, True, WHITE); x.fill = fill(INK); x.alignment = C
    rng, srng = f"{L}${R0}:{L}${RN}", f"{S}${R0}:{S}${RN}"
    p = ws.cell(row=R_PCT, column=c, value=f'=IF(OR({L}${R_NAME}="",{KC}=0),"",COUNTA({rng})/MAX(1,{KC}))'); p.number_format = "0%"
    RX = f'IF(INDEX({rng},{KC})<>"",INDEX({srng},{KC}),IF({KC}>1,INDEX({srng},{KC}-1),0))'
    ra = ws.cell(row=R_RACHA, column=c, value=f'=IF(OR({L}${R_NAME}="",{KC}=0),"",{RX}&IF({RX}=1," día"," días"))')
    be = ws.cell(row=R_BEST, column=c, value=f'=IF({L}${R_NAME}="","",MAX({srng})&IF(MAX({srng})=1," día"," días"))')
    for y in (p, ra, be): y.font = font(11, True, INK); y.alignment = C; y.fill = fill(WHITE); y.border = BOX
    for r in range(R0, RN + 1):
        prev = f"{S}{r-1}" if r > R0 else "0"
        ws.cell(row=r, column=SC[i], value=f'=IF({L}{r}<>"",{prev}+1,0)')
merge(R_NAME, 9, R_NAME, 9, "HOY", font(8, True, WHITE), INK)
for r in (R_PCT, R_RACHA, R_BEST): ws.cell(row=r, column=9).fill = fill(WHITE)

# --- los 30 días ---
merge(R0 - 1, 2, R0 - 1, 9, "Toca la casilla y elige ✓ (o escribe una x)", font(8, False, GREY, True), CREAM)
for n in range(1, N + 1):
    r = R0 + n - 1
    b = ws.cell(row=r, column=2, value=n); b.font = font(10, True, WHITE); b.fill = fill(ORANGE if n % 7 else ORANGE2); b.alignment = C
    f = ws.cell(row=r, column=3, value=f'=IF({START}="","",{START}+{n}-1)'); f.number_format = "DD/MM"; f.font = font(9, False, GREY); f.alignment = C; f.fill = fill(WHITE)
    for c in HC:
        x = ws.cell(row=r, column=c); x.fill = fill(WHITE); x.border = BOX; x.alignment = C; x.font = font(12, True, WHITE)
    h = ws.cell(row=r, column=9, value=f'=IF(COUNTA(D{r}:H{r})=0,"",COUNTA(D{r}:H{r})&"/"&MAX(1,{NAMED}))')
    h.font = font(9, True, TEAL2); h.alignment = C; h.fill = fill(WHITE); h.border = BOX
    ws.cell(row=r, column=AC, value=f'=IF(COUNTA(D{r}:H{r})>0,1,0)')
    ws.row_dimensions[r].height = 21
dv = DataValidation(type="list", formula1='"✓"', allow_blank=True, showErrorMessage=False)
dv.promptTitle = "Marca"; dv.prompt = "Elige ✓ (o escribe una x)"; dv.showInputMessage = True
ws.add_data_validation(dv); dv.add(f"D{R0}:H{RN}")
ws.conditional_formatting.add(f"D{R0}:H{RN}", FormulaRule(formula=[f'D{R0}<>""'], fill=fill(TEAL), font=Font(color=WHITE, bold=True)))
ws.conditional_formatting.add(f"B{R0}:C{RN}", FormulaRule(formula=[f'AND({START}<>"",$B{R0}={KC})'], fill=fill(GOLD), font=Font(color=INK, bold=True)))

# --- pie ---
r = RN + 2
merge(r, 2, r, 9, "¿Te gustó? Imagina TODO tu 2027 así: 12 meses, niveles 🚀, ánimo diario y tu resumen del año.", font(10, True, INK), PEACH)
merge(r + 1, 2, r + 1, 9, "👉 Mi 2027 en Hábitos · pixeliadigital.app/p/mi-2027-en-habitos  (usa el cupón de 15% que te llegó al correo)", font(9, False, ORANGE2), PEACH)
merge(r + 3, 2, r + 3, 9, "Hecho con 💜 por Pixelia · pixeliadigital.app · Uso personal", font(8, False, GREY), CREAM)
ws.freeze_panes = "D15"
ws.print_area = f"A1:J{RN + 6}"
ws.page_setup.orientation = "portrait"; ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 1
ws.sheet_properties.pageSetUpPr.fitToPage = True

if EJ:   # ejemplo lleno para fotos y reel: va por el día 18
    random.seed(7); probs = [0.92, 0.75, 0.82, 0.68, 0.8]
    for n in range(1, 19):
        for i, c in enumerate(HC):
            if random.random() < probs[i] or (i == 0): ws.cell(row=R0 + n - 1, column=c, value="✓")
    ws["P2"] = 18   # el "hoy" del ejemplo queda fijo en el día 18
    ws["D6"].value = dt.date(2027, 1, 1)
wb.save(OUT); print("ok", OUT)
