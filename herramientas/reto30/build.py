"""Reto 30 Días · Pixelia — REGALO (diseño 100% propio, no viene del PLR del tracker).
Hoja vertical: los días van hacia abajo y los retos en columnas. Cada reto se mide con ✓ (sí/no) o con un
NÚMERO y su meta diaria (ej. trabajar 5 horas): verde si llegaste, amarillo si hiciste una parte.
Se calculan solos: racha 🔥 (cuenta si hiciste al menos la mitad), mejor racha 🏆, % cumplido, total acumulado,
barra del reto y un mensaje que cambia.
Uso: python3 build.py salida.xlsx [--ejemplo]
Solo funciones compatibles con Excel y Google Sheets."""
import sys, random
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import FormulaRule
from openpyxl.worksheet.datavalidation import DataValidation
import datetime as dt

OUT = sys.argv[1]; EJ = "--ejemplo" in sys.argv
INK, ORANGE, ORANGE2, CREAM, PEACH, TEAL, TEAL2, GREY, WHITE, LINE, GOLD, YEL = (
    "231A3D", "FF6B3D", "E8501F", "FFF8F1", "FFE6D8", "14B8A6", "0F8F82", "8A8299", "FFFFFF", "F1E4D8", "FFC23D", "FFD966")
FN = "Arial"
def font(s=10, b=False, c=INK, i=False): return Font(name=FN, size=s, bold=b, color=c, italic=i)
def fill(c): return PatternFill("solid", fgColor=c)
thin = Side(style="thin", color=LINE)
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
C = Alignment(horizontal="center", vertical="center", wrap_text=True)

TIPOS = ["✓ Sí / No", "horas", "minutos", "vasos", "páginas", "$", "km", "veces"]
#        reto                         cómo se mide   meta   cuándo
RETOS = [("💧 Tomar agua",            "vasos",       8,    "Un vaso con cada comida"),
         ("💻 Trabajar en mi proyecto", "horas",     5,    "De 8 am a 1 pm"),
         ("📖 Leer",                   "páginas",    10,   "Antes de dormir"),
         ("🚶 Caminar 20 min",          "✓ Sí / No", None, "Después del almuerzo"),
         ("😴 Dormir antes de las 11",  "✓ Sí / No", None, "Celular fuera a las 10:30")]
N = 30; NH = 5
R_NAME, R_TIPO, R_META, R_CUANDO, R_PCT, R_RACHA, R_BEST, R_TOTAL = range(10, 18)
R0 = 20; RN = R0 + N - 1            # filas de los días
HC = [4, 5, 6, 7, 8]                # D..H = retos
SC = [11, 12, 13, 14, 15]           # K..O = racha acumulada (ocultas)
CC = [17, 18, 19, 20, 21]           # Q..U = crédito del día 0..1 (ocultas)
AC = 16                             # P = ¿marcó algo ese día? (oculta)
col = lambda c: chr(64 + c)
START = "$D$6"

wb = Workbook(); ws = wb.active; ws.title = "Mi Reto 30 Días"
ws.sheet_view.showGridLines = False; ws.sheet_properties.tabColor = ORANGE
for k, v in {"A": 2, "B": 7, "C": 11, "D": 15, "E": 15, "F": 15, "G": 15, "H": 15, "I": 9, "J": 2}.items(): ws.column_dimensions[k].width = v
for c in SC + CC + [AC]: ws.column_dimensions[col(c)].hidden = True

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
merge(2, 2, 2, 9, "Tus retos, a tu manera: márcalos con ✓ o escribe cuánto hiciste. La hoja hace el resto.", font(10, False, WHITE, True), ORANGE2)
ws.row_dimensions[2].height = 22

LAST = f"SUMPRODUCT(MAX(${col(AC)}${R0}:${col(AC)}${RN}*$B${R0}:$B${RN}))"
K = f"IF({START}=\"\",{LAST},MAX(0,MIN({N},TODAY()-{START}+1)))"
ws["P2"] = f"={K}"; KC = "$P$2"                     # día del reto (oculto)
NAMED = f"COUNTIF($D${R_NAME}:$H${R_NAME},\"?*\")"
CRED = f"SUMPRODUCT(($Q${R0}:$U${RN})*($D${R_NAME}:$H${R_NAME}<>\"\"))"
ws["P3"] = f"=IF({NAMED}=0,0,{CRED}/({NAMED}*{N}))"; PC = "$P$3"   # avance total (0-1)

merge(5, 2, 5, 3, "📅 EMPIEZO EL", font(8, True, WHITE), TEAL)
merge(6, 2, 6, 3, "Escribe la fecha →", font(8, False, GREY, True), WHITE)
merge(5, 4, 5, 4, "FECHA", font(8, True, WHITE), TEAL)
d = ws["D6"]; d.number_format = "DD/MM/YYYY"; d.font = font(11, True, INK); d.alignment = C; d.fill = fill(WHITE); d.border = BOX
if EJ: d.value = dt.date(2027, 1, 1)
merge(5, 5, 5, 6, "📍 VAS EN EL", font(8, True, WHITE), TEAL)
merge(6, 5, 6, 6, f'=IF({KC}=0,"Día 0 de 30","Día "&{KC}&" de 30")', font(12, True, INK), WHITE)
merge(5, 7, 5, 9, "⭐ AVANCE DEL RETO", font(8, True, WHITE), ORANGE)
merge(6, 7, 6, 9, f'=ROUND({PC}*100,0)&"%"', font(14, True, ORANGE2), WHITE)
merge(7, 2, 7, 9, f'=REPT("█",ROUND({PC}*30,0))&REPT("░",30-ROUND({PC}*30,0))', font(13, False, ORANGE), WHITE)
ws.row_dimensions[7].height = 24
MSG = (f'=IF({KC}=0,"👉 Escribe tus retos, pon tu fecha de inicio y marca tu primer día. Hoy arranca.",'
       f'IF({KC}>={N},IF({PC}>=0.8,"🏆 ¡LO LOGRASTE! 30 días. Esto ya no es un reto, es tu vida.","🏁 ¡Terminaste los 30 días! Lo que hiciste cuenta. ¿Repetimos?"),'
       f'IF({KC}<=3,"💪 Arrancaste. Lo más difícil (empezar) ya pasó.",'
       f'IF({KC}<=7,"🔥 Primera semana. Esta vez no se te olvidó.",'
       f'IF({KC}<=14,"😎 Dos semanas. Ya no eres el de la lista olvidada.",'
       f'IF({KC}<=21,"🚀 Mitad del reto. El lunes ya no te gana.",'
       f'"🌟 Recta final. Esto ya es tu estilo de vida."))))))')
merge(8, 2, 8, 9, MSG, font(11, True, INK), PEACH); ws.row_dimensions[8].height = 30

# --- configuración de cada reto + resumen ---
labels = {R_NAME: ("MIS RETOS ✏️", font(8, True, WHITE), INK), R_TIPO: ("¿Cómo lo mido?", font(8, True, INK), PEACH),
          R_META: ("Meta por día", font(8, True, INK), PEACH), R_CUANDO: ("¿Cuándo lo hago?", font(8, True, INK), PEACH),
          R_PCT: ("✅ Cumplido", font(9, True, INK), WHITE), R_RACHA: ("🔥 Racha actual", font(9, True, INK), WHITE),
          R_BEST: ("🏆 Mejor racha", font(9, True, INK), WHITE), R_TOTAL: ("📦 Llevo", font(9, True, INK), WHITE)}
for r, (t, f, bg) in labels.items(): merge(r, 2, r, 3, t, f, bg)
ws.row_dimensions[R_NAME].height = 40; ws.row_dimensions[R_CUANDO].height = 30; ws.row_dimensions[R_TOTAL].height = 30
dv_t = DataValidation(type="list", formula1='"' + ",".join(TIPOS) + '"', allow_blank=True, showErrorMessage=False)
dv_t.promptTitle = "¿Cómo lo mides?"; dv_t.prompt = "✓ si es sí/no; o elige la unidad (horas, vasos, páginas…)"; dv_t.showInputMessage = True
ws.add_data_validation(dv_t); dv_t.add(f"D{R_TIPO}:H{R_TIPO}")
for i, c in enumerate(HC):
    L, S, CR = col(c), col(SC[i]), col(CC[i])
    nombre, tipo, meta, cuando = RETOS[i]
    T, M = f"{L}${R_TIPO}", f"{L}${R_META}"
    ISNUM = f'AND({T}<>"",LEFT({T},1)<>"✓")'
    x = ws.cell(row=R_NAME, column=c, value=nombre); x.font = font(9, True, WHITE); x.fill = fill(INK); x.alignment = C
    for r, v, f in ((R_TIPO, tipo, font(9, True, TEAL2)), (R_META, meta, font(11, True, INK)), (R_CUANDO, cuando, font(8, False, GREY, True))):
        y = ws.cell(row=r, column=c, value=v); y.font = f; y.alignment = C; y.fill = fill(WHITE); y.border = BOX
    rng, srng, crng = f"{L}${R0}:{L}${RN}", f"{S}${R0}:{S}${RN}", f"{CR}${R0}:{CR}${RN}"
    p = ws.cell(row=R_PCT, column=c, value=f'=IF(OR({L}${R_NAME}="",{KC}=0),"",SUM({crng})/MAX(1,{KC}))'); p.number_format = "0%"
    RX = f'IF(INDEX({rng},{KC})<>"",INDEX({srng},{KC}),IF({KC}>1,INDEX({srng},{KC}-1),0))'
    ra = ws.cell(row=R_RACHA, column=c, value=f'=IF(OR({L}${R_NAME}="",{KC}=0),"",{RX}&IF({RX}=1," día"," días"))')
    be = ws.cell(row=R_BEST, column=c, value=f'=IF({L}${R_NAME}="","",MAX({srng})&IF(MAX({srng})=1," día"," días"))')
    to = ws.cell(row=R_TOTAL, column=c, value=f'=IF({L}${R_NAME}="","",IF({ISNUM},SUM({rng})&IF({M}="",""," de "&{M}*{N})&" "&{T},COUNTA({rng})&" de {N} días"))')
    for y in (p, ra, be, to): y.font = font(11, True, INK); y.alignment = C; y.fill = fill(WHITE); y.border = BOX
    to.font = font(9, True, ORANGE2)
    for r in range(R0, RN + 1):
        cell = f"{L}{r}"
        ws.cell(row=r, column=CC[i], value=f'=IF({cell}="",0,IF({ISNUM},IF({M}="",1,MIN(1,N({cell})/{M})),1))')
        prev = f"{S}{r-1}" if r > R0 else "0"
        ws.cell(row=r, column=SC[i], value=f'=IF({CR}{r}>=0.5,{prev}+1,0)')   # la racha sigue si hiciste al menos la mitad
merge(R_NAME, 9, R_NAME, 9, "HOY", font(8, True, WHITE), INK)
for r in range(R_TIPO, R_TOTAL + 1): ws.cell(row=r, column=9).fill = fill(WHITE)

# --- los 30 días ---
merge(R0 - 1, 2, R0 - 1, 9, "Toca la casilla y elige ✓ — o escribe el número (ej. 3,5 horas)", font(8, False, GREY, True), CREAM)
for n in range(1, N + 1):
    r = R0 + n - 1
    b = ws.cell(row=r, column=2, value=n); b.font = font(10, True, WHITE); b.fill = fill(ORANGE if n % 7 else ORANGE2); b.alignment = C
    f = ws.cell(row=r, column=3, value=f'=IF({START}="","",{START}+{n}-1)'); f.number_format = "DD/MM"; f.font = font(9, False, GREY); f.alignment = C; f.fill = fill(WHITE)
    for c in HC:
        x = ws.cell(row=r, column=c); x.fill = fill(WHITE); x.border = BOX; x.alignment = C; x.font = font(12, True, INK)
    h = ws.cell(row=r, column=9, value=f'=IF(COUNTA(D{r}:H{r})=0,"",ROUND(SUM(Q{r}:U{r})/MAX(1,{NAMED})*100,0)&"%")')
    h.font = font(9, True, TEAL2); h.alignment = C; h.fill = fill(WHITE); h.border = BOX
    ws.cell(row=r, column=AC, value=f'=IF(COUNTA(D{r}:H{r})>0,1,0)')
    ws.row_dimensions[r].height = 21
dv = DataValidation(type="list", formula1='"✓"', allow_blank=True, showErrorMessage=False)
dv.promptTitle = "Marca"; dv.prompt = "Elige ✓ — o escribe cuánto hiciste (un número)"; dv.showInputMessage = True
ws.add_data_validation(dv); dv.add(f"D{R0}:H{RN}")
ws.conditional_formatting.add(f"D{R0}:H{RN}", FormulaRule(formula=[f'AND(D{R0}<>"",Q{R0}>=1)'], fill=fill(TEAL), font=Font(color=WHITE, bold=True), stopIfTrue=True))
ws.conditional_formatting.add(f"D{R0}:H{RN}", FormulaRule(formula=[f'AND(D{R0}<>"",Q{R0}<1)'], fill=fill(YEL), font=Font(color=INK, bold=True)))
ws.conditional_formatting.add(f"B{R0}:C{RN}", FormulaRule(formula=[f'AND({START}<>"",$B{R0}={KC})'], fill=fill(GOLD), font=Font(color=INK, bold=True)))

# --- pie ---
r = RN + 2
merge(r, 2, r, 9, "🟩 llegaste a tu meta · 🟨 hiciste una parte (si es al menos la mitad, tu racha sigue)", font(8, False, GREY), CREAM)
merge(r + 1, 2, r + 1, 9, "¿Te gustó? Imagina TODO tu 2027 así: 12 meses, niveles 🚀, ánimo diario y tu resumen del año.", font(10, True, INK), PEACH)
merge(r + 2, 2, r + 2, 9, "👉 Mi 2027 en Hábitos · pixeliadigital.app/p/mi-2027-en-habitos  (usa el cupón de 15% que te llegó al correo)", font(9, False, ORANGE2), PEACH)
merge(r + 4, 2, r + 4, 9, "Hecho con 💜 por Pixelia · pixeliadigital.app · Uso personal", font(8, False, GREY), CREAM)
ws.freeze_panes = f"D{R0}"
ws.print_area = f"A1:J{RN + 6}"
ws.page_setup.orientation = "portrait"; ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 1
ws.sheet_properties.pageSetUpPr.fitToPage = True

if EJ:   # ejemplo lleno para fotos y reel: va por el día 18
    random.seed(7)
    for n in range(1, 19):
        r = R0 + n - 1
        ws.cell(row=r, column=4, value=random.choice([8, 8, 8, 7, 6, 8, 5]))               # vasos (meta 8)
        ws.cell(row=r, column=5, value=random.choice([5, 5, 4, 5, 3.5, 5, 6, 2]))          # horas (meta 5)
        if random.random() < 0.85: ws.cell(row=r, column=6, value=random.choice([10, 12, 10, 6, 15, 10]))  # páginas (meta 10)
        if random.random() < 0.8: ws.cell(row=r, column=7, value="✓")
        if random.random() < 0.7: ws.cell(row=r, column=8, value="✓")
    for c, v in zip(range(4, 9), [8, 5, 12, "✓", "✓"]): ws.cell(row=R0 + 17, column=c, value=v)   # el día 18 sale completo
    ws["P2"] = 18   # el "hoy" del ejemplo queda fijo en el día 18
wb.save(OUT); print("ok", OUT)
