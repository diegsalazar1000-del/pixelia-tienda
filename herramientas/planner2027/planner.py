"""Genera "Mi Año en Mini · Planner Digital 2027" (Pixelia) en formato tablet (horizontal) y móvil (vertical).
PDF con hipervínculos: barra de meses, accesos rápidos y navegación entre semanas.
Uso: python3 planner.py  → crea out/Mi-Ano-en-Mini-2027-Tablet.pdf y out/Mi-Ano-en-Mini-2027-Movil.pdf
"""
import calendar, datetime as dt, os, pathlib
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import simpleSplit

HERE = pathlib.Path(__file__).parent
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
FONTS = pathlib.Path("/usr/share/fonts/truetype/google-fonts")

# ---------- Fuentes ----------
def _static_lora():
    from fontTools.ttLib import TTFont as FT
    from fontTools.varLib import instancer
    for src, dst, w in [("Lora-Variable.ttf", "Lora-Medium.ttf", 500), ("Lora-Italic-Variable.ttf", "Lora-MediumItalic.ttf", 500)]:
        p = HERE / dst
        if not p.exists():
            f = instancer.instantiateVariableFont(FT(FONTS / src), {"wght": w})
            f.save(p)
_static_lora()
for name, path in {"P": FONTS / "Poppins-Regular.ttf", "PL": FONTS / "Poppins-Light.ttf", "PM": FONTS / "Poppins-Medium.ttf",
                   "PB": FONTS / "Poppins-Bold.ttf", "L": HERE / "Lora-Medium.ttf", "LI": HERE / "Lora-MediumItalic.ttf"}.items():
    pdfmetrics.registerFont(TTFont(name, str(path)))

# ---------- Paleta cálida ----------
BG = HexColor("#FBF6EF"); PAPER = HexColor("#FFFDF9"); LINE = HexColor("#E6D9C7"); SOFT = HexColor("#F3EADF")
INK = HexColor("#4A3F35"); MUTED = HexColor("#9A8B7B"); TERRA = HexColor("#C8775B"); SAGE = HexColor("#8FA58C")
SAND = HexColor("#E8DCCB"); MUSTARD = HexColor("#D9A85B"); ROSE = HexColor("#D9A3A0")
ACCENTS = [TERRA, SAGE, MUSTARD, ROSE]

YEAR = 2027
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
MES_CORTO = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_C = ["L", "M", "X", "J", "V", "S", "D"]
cal = calendar.Calendar(firstweekday=0)

# Semanas de lunes a domingo que tocan 2027: del lunes 28/12/2026 al domingo 02/01/2028
FIRST_MONDAY = dt.date(YEAR, 1, 1) - dt.timedelta(days=dt.date(YEAR, 1, 1).weekday())
WEEKS = []
d = FIRST_MONDAY
while d.year <= YEAR:
    WEEKS.append(d); d += dt.timedelta(days=7)
assert WEEKS[0] == dt.date(2026, 12, 28) and WEEKS[-1] + dt.timedelta(days=6) == dt.date(2028, 1, 2) and len(WEEKS) == 53

def week_of(day):  # índice 1..53 de la semana que contiene ese día
    return (day - FIRST_MONDAY).days // 7 + 1

def fmt_range(mon):
    sun = mon + dt.timedelta(days=6)
    if mon.month == sun.month:
        return f"{mon.day}–{sun.day} de {MESES[mon.month-1].lower()} {sun.year}"
    return f"{mon.day} {MESES[mon.month-1][:3].lower()} {mon.year if mon.year != sun.year else ''}– {sun.day} {MESES[sun.month-1][:3].lower()} {sun.year}".replace("  ", " ")


class Planner:
    def __init__(self, path, W, H, mode):
        self.W, self.H, self.mode = W, H, mode  # mode: 'tablet' | 'movil'
        self.c = canvas.Canvas(str(path), pagesize=(W, H))
        self.c.setTitle(f"Mi Año en Mini · Planner Digital {YEAR}")
        self.c.setAuthor("Pixelia"); self.c.setSubject("Planner digital con hipervínculos")
        self.p = W / 1024 if mode == "tablet" else W / 600  # escala base
        self.TOP = 46 * (1 if mode == "tablet" else 1.15)
        self.BOTTOM = 0 if mode == "tablet" else 54
        self.M = 24 if mode == "tablet" else 18
        self.ctx_month = 1

    # ---------- utilidades ----------
    def Y(self, y): return self.H - y
    def rect(self, x, y, w, h, fill=None, stroke=None, r=0, lw=1):
        c = self.c; c.setLineWidth(lw)
        if fill: c.setFillColor(fill)
        if stroke: c.setStrokeColor(stroke)
        if r: c.roundRect(x, self.Y(y + h), w, h, r, stroke=1 if stroke else 0, fill=1 if fill else 0)
        else: c.rect(x, self.Y(y + h), w, h, stroke=1 if stroke else 0, fill=1 if fill else 0)
    def text(self, x, y, s, font="P", size=10, color=INK, align="l"):
        c = self.c; c.setFont(font, size); c.setFillColor(color)
        if align == "c": c.drawCentredString(x, self.Y(y), s)
        elif align == "r": c.drawRightString(x, self.Y(y), s)
        else: c.drawString(x, self.Y(y), s)
    def para(self, x, y, w, s, font="P", size=10, color=INK, lead=1.45):
        yy = y
        for block in s.split("\n"):
            for line in (simpleSplit(block, font, size, w) or [""]):
                self.text(x, yy, line, font, size, color); yy += size * lead
        return yy
    def link(self, x, y, w, h, dest):
        self.c.linkAbsolute("", dest, (x, self.Y(y + h), x + w, self.Y(y)))
    def lines(self, x, y, w, h, gap=22, color=LINE):
        c = self.c; c.setStrokeColor(color); c.setLineWidth(0.6)
        yy = y + gap
        while yy <= y + h - 2:
            c.line(x, self.Y(yy), x + w, self.Y(yy)); yy += gap
    def dots(self, x, y, w, h, gap=16):
        c = self.c; c.setFillColor(LINE)
        yy = y + gap
        while yy < y + h:
            xx = x + gap
            while xx < x + w:
                c.circle(xx, self.Y(yy), 0.9, stroke=0, fill=1); xx += gap
            yy += gap
    def circle(self, x, y, r, fill=None, stroke=LINE, lw=0.8):
        c = self.c; c.setLineWidth(lw)
        if fill: c.setFillColor(fill)
        c.setStrokeColor(stroke); c.circle(x, self.Y(y), r, stroke=1 if stroke else 0, fill=1 if fill else 0)
    def panel(self, x, y, w, h, title=None, accent=TERRA):
        self.rect(x, y, w, h, fill=PAPER, stroke=LINE, r=10)
        if title:
            self.rect(x + 14, y + 13, 4, 12, fill=accent, r=2)
            self.text(x + 24, y + 23, title.upper(), "PM", 8.5, INK)
        return (x + 14, y + (34 if title else 12), w - 28, h - (46 if title else 24))
    def button(self, x, y, w, h, label, dest, fill=SOFT, color=INK, size=9, font="PM"):
        self.rect(x, y, w, h, fill=fill, r=h / 2)
        self.text(x + w / 2, y + h / 2 + size * 0.35, label, font, size, color, "c")
        self.link(x, y, w, h, dest)

    # ---------- marco de página ----------
    def page(self, dest, month_ctx=None, nav=True):
        if month_ctx: self.ctx_month = month_ctx
        c = self.c
        if getattr(self, "_started", False): c.showPage()
        self._started = True
        c.bookmarkPage(dest)
        self.rect(0, 0, self.W, self.H, fill=BG)
        if nav: self.navbar()

    def navbar(self):
        W, M = self.W, self.M
        if self.mode == "tablet":
            y, h = 12, 24
            self.button(M, y, 62, h, "Índice", "indice", fill=INK, color=PAPER, size=8.5)
            self.button(M + 68, y, 50, h, YEAR.__str__(), "ano", size=8.5)
            left = M + 130; right = W - M - 3 * 70
            tw = (right - left) / 12
            for i in range(12):
                on = (i + 1) == self.ctx_month
                self.button(left + i * tw + 1.5, y, tw - 3, h, MES_CORTO[i], f"m{i+1}", fill=TERRA if on else SOFT, color=PAPER if on else INK, size=8)
            for j, (lab, dest) in enumerate([("Hábitos", f"h{self.ctx_month}"), ("Finanzas", f"f{self.ctx_month}"), ("Notas", "notas1")]):
                self.button(right + 6 + j * 70, y, 64, h, lab, dest, fill=SAND, size=8.5)
        else:
            y, h = 14, 26
            tw = (W - 2 * M) / 12
            for i in range(12):
                on = (i + 1) == self.ctx_month
                self.button(M + i * tw + 1, y, tw - 2, h, MES_CORTO[i], f"m{i+1}",
                            fill=TERRA if on else SOFT, color=PAPER if on else INK, size=7.5)
            by = self.H - 44; bw = (W - 2 * M) / 5
            for j, (lab, dest) in enumerate([("Índice", "indice"), (str(YEAR), "ano"), ("Hábitos", f"h{self.ctx_month}"),
                                             ("Finanzas", f"f{self.ctx_month}"), ("Notas", "notas1")]):
                self.button(M + j * bw + 2, by, bw - 4, 30, lab, dest, fill=INK if j == 0 else SAND, color=PAPER if j == 0 else INK, size=10)

    def area(self):  # zona útil
        top = 12 + self.TOP
        return self.M, top, self.W - 2 * self.M, self.H - top - self.M - self.BOTTOM

    def header(self, title, sub=None, accent=TERRA):
        x, y, w, h = self.area()
        big = 30 if self.mode == "tablet" else 32
        self.text(x + 2, y + big, title, "L", big, INK)
        if sub: self.text(x + w, y + big - 4, sub, "P", 10.5, MUTED, "r") if self.mode == "tablet" else self.text(x + 2, y + big + 22, sub, "P", 11, MUTED)
        hh = big + (16 if self.mode == "tablet" else 40)
        return x, y + hh, w, h - hh

    def mini_month(self, x, y, w, m, title=True, link_days=True, highlight_week=None):
        cw = w / 7; yy = y
        if title:
            self.text(x, yy + 11, MESES[m - 1], "PM", 10, INK); self.link(x, yy, w, 14, f"m{m}"); yy += 20
        for i, dc in enumerate(DIAS_C):
            self.text(x + i * cw + cw / 2, yy + 8, dc, "PM", 7, MUTED, "c")
        yy += 14
        for wk in cal.monthdatescalendar(YEAR, m):
            wi = week_of(wk[0])
            if highlight_week == wi: self.rect(x, yy - 1, w, cw * 0.82, fill=SOFT, r=4)
            for i, day in enumerate(wk):
                if day.month == m:
                    self.text(x + i * cw + cw / 2, yy + cw * 0.55, str(day.day), "P", 7.5, INK, "c")
            if link_days: self.link(x, yy - 1, w, cw * 0.82, f"w{wi}")
            yy += cw * 0.82
        return yy

    # ---------- páginas ----------
    def cover(self):
        self.page("portada", nav=False)
        W, H = self.W, self.H; c = self.c
        # formas decorativas
        c.setFillColor(SAND); c.circle(W * 0.82, self.Y(H * 0.22), min(W, H) * 0.30, stroke=0, fill=1)
        c.setFillColor(TERRA); c.circle(W * 0.82, self.Y(H * 0.22), min(W, H) * 0.12, stroke=0, fill=1)
        c.setFillColor(SAGE); c.circle(W * 0.92, self.Y(H * 0.95), min(W, H) * 0.22, stroke=0, fill=1)
        c.setFillColor(MUSTARD); c.circle(W * 0.74, self.Y(H * 0.86), min(W, H) * 0.05, stroke=0, fill=1)
        x = self.M * 2.5 if self.mode == "tablet" else self.M * 1.6
        top = H * (0.40 if self.mode == "tablet" else 0.40)
        self.text(x, top, "PLANNER DIGITAL", "PM", 12, MUTED)
        self.text(x, top + 64, "Mi Año", "L", 64 if self.mode == "tablet" else 60, INK)
        self.text(x, top + 130, "en Mini", "LI", 64 if self.mode == "tablet" else 60, TERRA)
        self.text(x, top + 200, str(YEAR), "PB", 54, INK)
        self.text(x, top + 248, "Este planner es de:", "P", 11, MUTED)
        c.setStrokeColor(INK); c.setLineWidth(0.8); c.line(x, self.Y(top + 284), x + 240, self.Y(top + 284))
        self.button(x, top + 312, 150, 38, "Empezar  →", "indice", fill=INK, color=PAPER, size=12)
        self.text(x, H - 24, "Pixelia · pixeliadigital.app", "P", 8.5, MUTED)

    def instructions(self):
        texts = [
            ("Bienvenida", f"""Gracias por elegir Mi Año en Mini {YEAR}. Es un planner pensado para usarse de verdad: pocas páginas, todo en español y con enlaces para moverte en un toque.

CÓMO ABRIRLO
1. Guarda el PDF en tu tablet o móvil.
2. Ábrelo en una app de notas que acepte PDF con enlaces (compatible con GoodNotes, Notability, Xodo, Samsung Notes, Noteshelf y similares).
3. Usa el modo "leer" o "enlace" para tocar los botones, y el modo "escribir" para tomar notas.

CÓMO MOVERTE
• La barra superior te lleva a cada mes. El mes en el que estás se ve resaltado.
• Índice, {YEAR}, Hábitos, Finanzas y Notas están siempre a mano.
• En cada mes, toca una semana para ir directo a ella.
• En cada semana, las flechas ‹ › te llevan a la anterior o a la siguiente."""),
            ("Trucos", f"""DUPLICA PÁGINAS
¿Necesitas más notas o más tareas? Duplica la página desde tu app (normalmente en el menú de la miniatura).

STICKERS
Importa la carpeta "Stickers" como imágenes o en el apartado de stickers de tu app y arrástralos a cualquier página.

CAMBIA LA PORTADA
En la carpeta "Portadas" tienes 4 colores. Inserta la imagen sobre la portada o reemplaza la página desde tu app.

SI UN ENLACE NO FUNCIONA
• Asegúrate de estar en modo lectura / enlace, no en modo lápiz.
• Algunas apps desactivan los enlaces al importar como "imagen": impórtalo como PDF.

EDICIÓN ESTUDIANTE
Al final encontrarás horario de clases, exámenes y entregas, y lista de tareas.

¿Dudas? Escríbenos desde pixeliadigital.app. ¡Que tengas un gran {YEAR}!"""),
        ]
        for i, (t, body) in enumerate(texts):
            self.page(f"instr{i+1}")
            x, y, w, h = self.header(t, f"Instrucciones {i+1}/2")
            ix, iy, iw, ih = self.panel(x, y, w, h)
            self.para(ix + 6, iy + 12, min(iw - 12, 640 if self.mode == "tablet" else iw - 12), body, "P", 10.5 if self.mode == "tablet" else 11.5)

    def index(self):
        self.page("indice")
        x, y, w, h = self.header("Índice", f"Planner {YEAR}")
        items = [("Visión del año", "vision", TERRA), (f"{YEAR} de un vistazo", "ano", SAGE), ("Metas por trimestre", "metas", MUSTARD),
                 ("Fechas importantes", "fechas", ROSE), ("Meses", "m1", TERRA), ("Semanas", "w1", SAGE), ("Hábitos", "h1", MUSTARD),
                 ("Finanzas", "f1", ROSE), ("Reto 52 semanas", "reto", TERRA), ("Reflexión mensual", "r1", SAGE),
                 ("Edición estudiante", "est_horario", MUSTARD), ("Notas", "notas1", ROSE)]
        cols = 3 if self.mode == "tablet" else 2
        rows = (len(items) + cols - 1) // cols
        gw, gh = 14, 14
        bw = (w - gw * (cols - 1)) / cols; bh = min((h - gh * (rows - 1)) / rows, 120)
        for k, (lab, dest, col) in enumerate(items):
            cx = x + (k % cols) * (bw + gw); cy = y + (k // cols) * (bh + gh)
            self.rect(cx, cy, bw, bh, fill=PAPER, stroke=LINE, r=12)
            self.rect(cx + 16, cy + 16, 26, 26, fill=col, r=13)
            self.text(cx + 29, cy + 33, str(k + 1), "PB", 10, PAPER, "c")
            self.text(cx + 16, cy + bh - 20, lab, "PM", 13, INK)
            self.link(cx, cy, bw, bh, dest)

    def vision(self):
        self.page("vision")
        x, y, w, h = self.header(f"Visión {YEAR}", "Lo que quiero para este año")
        if self.mode == "tablet":
            cw = (w - 14) / 2
            a = self.panel(x, y, cw, 110, "Mi palabra del año", TERRA)
            self.text(a[0] + a[2] / 2, a[1] + 46, "_______________", "L", 22, LINE, "c")
            b = self.panel(x, y + 124, cw, h - 124, "3 metas grandes", SAGE)
            for i in range(3):
                yy = b[1] + i * (b[3] / 3)
                self.rect(b[0], yy + 6, 22, 22, fill=SOFT, r=11); self.text(b[0] + 11, yy + 21, str(i + 1), "PB", 10, TERRA, "c")
                self.lines(b[0] + 32, yy, b[2] - 32, b[3] / 3 - 4, 24)
            qs = ["Quiero sentirme…", "Dejo atrás…", "Celebraré cuando…"]
            ph = (h - 28) / 3
            for i, q in enumerate(qs):
                p = self.panel(x + cw + 14, y + i * (ph + 14), cw, ph, q, ACCENTS[(i + 1) % 4]); self.lines(*p, gap=24)
        else:
            a = self.panel(x, y, w, 96, "Mi palabra del año", TERRA)
            self.text(a[0] + a[2] / 2, a[1] + 40, "_______________", "L", 22, LINE, "c")
            secs = [("3 metas grandes", 1.4), ("Quiero sentirme…", 1), ("Dejo atrás…", 1), ("Celebraré cuando…", 1)]
            avail = h - 110 - 14 * 3; tot = sum(s[1] for s in secs); yy = y + 110
            for i, (t, f) in enumerate(secs):
                ph = avail * f / tot; p = self.panel(x, yy, w, ph, t, ACCENTS[i % 4]); self.lines(*p, gap=26); yy += ph + 14

    def year_glance(self):
        self.page("ano")
        x, y, w, h = self.header(f"{YEAR} de un vistazo", "Toca un mes o una semana")
        cols = 4 if self.mode == "tablet" else 3
        rows = 12 // cols; g = 12
        cw = (w - g * (cols - 1)) / cols; ch = (h - g * (rows - 1)) / rows
        for m in range(1, 13):
            cx = x + ((m - 1) % cols) * (cw + g); cy = y + ((m - 1) // cols) * (ch + g)
            self.rect(cx, cy, cw, ch, fill=PAPER, stroke=LINE, r=10)
            mw = min(cw - 24, (ch - 34) / 0.82 / 6 * 7 * 0.98)
            self.mini_month(cx + (cw - mw) / 2, cy + 8, mw, m)

    def quarters(self):
        self.page("metas")
        x, y, w, h = self.header("Metas por trimestre", "Divide tus metas grandes en pasos")
        cols = 2; g = 14
        cw = (w - g) / cols; ch = (h - g) / 2
        names = ["T1 · Enero – Marzo", "T2 · Abril – Junio", "T3 · Julio – Septiembre", "T4 · Octubre – Diciembre"]
        for i, n in enumerate(names):
            if self.mode == "tablet": px, py, pw, ph = x + (i % 2) * (cw + g), y + (i // 2) * (ch + g), cw, ch
            else: ph = (h - 3 * g) / 4; px, py, pw = x, y + i * (ph + g), w
            p = self.panel(px, py, pw, ph, n, ACCENTS[i])
            gap = 24; n_lines = int(p[3] // gap)
            for k in range(n_lines):
                yy = p[1] + k * gap + 4
                self.rect(p[0], yy + 6, 11, 11, stroke=MUTED, r=3, lw=0.7)
                self.c.setStrokeColor(LINE); self.c.setLineWidth(0.6); self.c.line(p[0] + 18, self.Y(yy + 18), p[0] + p[2], self.Y(yy + 18))

    def important_dates(self):
        self.page("fechas")
        x, y, w, h = self.header("Fechas importantes", "Feriados de tu país, cumpleaños, aniversarios…")
        cols = 4 if self.mode == "tablet" else 2; rows = 12 // cols; g = 10
        cw = (w - g * (cols - 1)) / cols; ch = (h - g * (rows - 1)) / rows
        for m in range(12):
            cx = x + (m % cols) * (cw + g); cy = y + (m // cols) * (ch + g)
            p = self.panel(cx, cy, cw, ch, MESES[m], ACCENTS[m % 4]); self.lines(*p, gap=20)

    def month(self, m):
        self.page(f"m{m}", month_ctx=m)
        x, y, w, h = self.header(MESES[m - 1], f"{MESES[m-1]} {YEAR}")
        weeks = cal.monthdatescalendar(YEAR, m)
        if self.mode == "tablet":
            side = 230; gw = w - side - 14
            self.calendar_grid(x, y, gw, h, m, weeks)
            sx = x + gw + 14
            p = self.panel(sx, y, side, 150, "Prioridades del mes", TERRA)
            for i in range(3):
                yy = p[1] + i * 36 + 6
                self.circle(p[0] + 7, yy + 9, 6, stroke=MUTED); self.c.setStrokeColor(LINE); self.c.line(p[0] + 20, self.Y(yy + 16), p[0] + p[2], self.Y(yy + 16))
            q = self.panel(sx, y + 164, side, h - 164 - 120, "Notas del mes", SAGE); self.dots(*q, gap=16)
            by = y + h - 110
            for j, (lab, dest, col) in enumerate([("Hábitos del mes", f"h{m}", MUSTARD), ("Finanzas del mes", f"f{m}", ROSE), ("Reflexión del mes", f"r{m}", SAGE)]):
                self.button(sx, by + j * 37, side, 30, lab + "  →", dest, fill=col, color=PAPER, size=9.5)
        else:
            gh = h * 0.56
            self.calendar_grid(x, y, w, gh, m, weeks)
            yy = y + gh + 12
            p = self.panel(x, yy, w, 120, "Prioridades del mes", TERRA)
            for i in range(3):
                ly = p[1] + i * 26 + 4
                self.circle(p[0] + 7, ly + 9, 6, stroke=MUTED); self.c.setStrokeColor(LINE); self.c.line(p[0] + 20, self.Y(ly + 16), p[0] + p[2], self.Y(ly + 16))
            yy += 132
            bw = (w - 16) / 3
            for j, (lab, dest, col) in enumerate([("Hábitos", f"h{m}", MUSTARD), ("Finanzas", f"f{m}", ROSE), ("Reflexión", f"r{m}", SAGE)]):
                self.button(x + j * (bw + 8), yy, bw, 32, lab + " →", dest, fill=col, color=PAPER, size=10)
            yy += 44
            q = self.panel(x, yy, w, y + h - yy, "Notas del mes", SAGE); self.dots(*q, gap=16)

    def calendar_grid(self, x, y, w, h, m, weeks):
        self.rect(x, y, w, h, fill=PAPER, stroke=LINE, r=10)
        lab = 34; cw = (w - lab) / 7; head = 28
        for i, dname in enumerate(DIAS):
            self.text(x + lab + i * cw + cw / 2, y + 19, dname[:3].upper() if self.mode == "tablet" else DIAS_C[i], "PM", 8.5, MUTED, "c")
        rh = (h - head) / len(weeks); c = self.c
        for r, wk in enumerate(weeks):
            ry = y + head + r * rh
            wi = week_of(wk[0])
            self.rect(x + 6, ry + 6, lab - 10, rh - 12, fill=SOFT, r=6)
            self.text(x + lab / 2 + 1, ry + rh / 2 + 3, f"S{wi}", "PM", 7.5, TERRA, "c")
            self.link(x, ry, lab, rh, f"w{wi}")
            c.setStrokeColor(LINE); c.setLineWidth(0.6); c.line(x + lab, self.Y(ry), x + w, self.Y(ry))
            for i, day in enumerate(wk):
                cx = x + lab + i * cw
                if day.month == m:
                    self.text(cx + 7, ry + 15, str(day.day), "PM", 9.5, INK if i < 5 else TERRA)
                    self.link(cx, ry, cw, rh, f"w{wi}")
                else:
                    self.rect(cx + 1, ry + 1, cw - 2, rh - 2, fill=BG)
        for i in range(1, 7):
            c.setStrokeColor(LINE); c.line(x + lab + i * cw, self.Y(y + head), x + lab + i * cw, self.Y(y + h))
        c.line(x + lab, self.Y(y + head), x + lab, self.Y(y + h))

    def week(self, wi):
        mon = WEEKS[wi - 1]; ctx = min(max((mon + dt.timedelta(days=3)).month if (mon + dt.timedelta(days=3)).year == YEAR else (1 if mon.year < YEAR else 12), 1), 12)
        self.page(f"w{wi}", month_ctx=ctx)
        x, y, w, h = self.area()
        big = 26
        self.text(x + 2, y + big, f"Semana {wi}", "L", big, INK)
        self.text(x + 2, y + big + 20, fmt_range(mon), "P", 10.5, MUTED)
        # flechas
        if wi > 1: self.button(x + w - 74, y + 6, 34, 26, "‹", f"w{wi-1}", size=14)
        if wi < 53: self.button(x + w - 34, y + 6, 34, 26, "›", f"w{wi+1}", size=14)
        y += 58; h -= 58
        days = [mon + dt.timedelta(days=i) for i in range(7)]
        if self.mode == "tablet":
            side = 220; gw = w - side - 12
            cols = 4; g = 10; cw = (gw - g * 3) / cols; ch = (h - g) / 2
            for i, day in enumerate(days + [None]):
                cx = x + (i % cols) * (cw + g); cy = y + (i // cols) * (ch + g)
                if day is None:
                    p = self.panel(cx, cy, cw, ch, "Pendientes", MUSTARD)
                    for k in range(int(p[3] // 24)):
                        yy = p[1] + k * 24 + 4
                        self.rect(p[0], yy + 6, 10, 10, stroke=MUTED, r=3, lw=0.7)
                        self.c.setStrokeColor(LINE); self.c.line(p[0] + 16, self.Y(yy + 16), p[0] + p[2], self.Y(yy + 16))
                    continue
                self.day_box(cx, cy, cw, ch, day, i)
            self.week_side(x + gw + 12, y, side, h, mon, wi)
        else:
            sideh = 150
            self.week_side_mobile(x, y, w, sideh, mon, wi)
            yy = y + sideh + 10; rh = (h - sideh - 10 - 6 * 6) / 7
            for i, day in enumerate(days):
                self.day_box(x, yy, w, rh, day, i, row=True); yy += rh + 6

    def day_box(self, x, y, w, h, day, i, row=False):
        out = day.year != YEAR
        self.rect(x, y, w, h, fill=PAPER if not out else SOFT, stroke=LINE, r=10)
        col = TERRA if i >= 5 else SAGE
        if row:
            self.text(x + 14, y + 20, f"{DIAS[i][:3]} {day.day}", "PM", 10, col)
            self.text(x + 14, y + 33, MES_CORTO[day.month - 1], "P", 7.5, MUTED)
            self.lines(x + 64, y + 2, w - 78, h - 4, 20)
        else:
            self.text(x + 14, y + 24, str(day.day), "PB", 18, col)
            self.text(x + 40, y + 17, DIAS[i].upper(), "PM", 7.5, INK)
            self.text(x + 40, y + 27, MESES[day.month - 1].lower(), "P", 7.5, MUTED)
            self.lines(x + 12, y + 34, w - 24, h - 38, 21)

    def week_side(self, x, y, w, h, mon, wi):
        mm = (mon + dt.timedelta(days=3)).month if (mon + dt.timedelta(days=3)).year == YEAR else (1 if mon.year < YEAR else 12)
        p = self.panel(x, y, w, 150, "", None); self.mini_month(p[0] + 4, y + 10, p[2] - 8, mm, highlight_week=wi)
        p = self.panel(x, y + 160, w, 112, "Top 3 de la semana", TERRA)
        for k in range(3):
            yy = p[1] + k * 26 + 2
            self.text(p[0], yy + 15, f"{k+1}.", "PB", 10, TERRA); self.c.setStrokeColor(LINE); self.c.line(p[0] + 16, self.Y(yy + 18), p[0] + p[2], self.Y(yy + 18))
        hy = y + 282; hh = 150
        p = self.panel(x, hy, w, hh, "Hábitos", MUSTARD)
        cw = (p[2] - 70) / 7
        for i, dc in enumerate(DIAS_C): self.text(p[0] + 70 + i * cw + cw / 2, p[1] + 6, dc, "PM", 7, MUTED, "c")
        for r in range(4):
            yy = p[1] + 14 + r * 22
            self.c.setStrokeColor(LINE); self.c.line(p[0], self.Y(yy + 16), p[0] + 62, self.Y(yy + 16))
            for i in range(7): self.circle(p[0] + 70 + i * cw + cw / 2, yy + 10, 5.5, stroke=MUTED, lw=0.6)
        my = hy + hh + 10
        p = self.panel(x, my, w, y + h - my, "¿Cómo me fue?", SAGE)
        for k in range(5):
            self.circle(p[0] + 14 + k * ((p[2] - 28) / 4), p[1] + 12, 9, stroke=MUTED, lw=0.7)
            self.text(p[0] + 14 + k * ((p[2] - 28) / 4), p[1] + 15.5, str(k + 1), "PM", 8, MUTED, "c")
        self.lines(p[0], p[1] + 26, p[2], p[3] - 26, 20)

    def week_side_mobile(self, x, y, w, h, mon, wi):
        g = 10; cw = (w - g) / 2
        p = self.panel(x, y, cw, h, "Top 3", TERRA)
        for k in range(3):
            yy = p[1] + k * 30
            self.text(p[0], yy + 16, f"{k+1}.", "PB", 10, TERRA); self.c.setStrokeColor(LINE); self.c.line(p[0] + 16, self.Y(yy + 19), p[0] + p[2], self.Y(yy + 19))
        p = self.panel(x + cw + g, y, cw, h, "Hábitos", MUSTARD)
        hc = (p[2] - 50) / 7
        for i, dc in enumerate(DIAS_C): self.text(p[0] + 50 + i * hc + hc / 2, p[1] + 6, dc, "PM", 7, MUTED, "c")
        for r in range(4):
            yy = p[1] + 14 + r * 22
            self.c.setStrokeColor(LINE); self.c.line(p[0], self.Y(yy + 16), p[0] + 44, self.Y(yy + 16))
            for i in range(7): self.circle(p[0] + 50 + i * hc + hc / 2, yy + 10, 5, stroke=MUTED, lw=0.6)

    def habits(self, m):
        self.page(f"h{m}", month_ctx=m)
        x, y, w, h = self.header(f"Hábitos · {MESES[m-1]}", "Rellena un círculo cada día que lo cumplas")
        ndays = calendar.monthrange(YEAR, m)[1]
        self.rect(x, y, w, h, fill=PAPER, stroke=LINE, r=10)
        if self.mode == "tablet":
            namew = 170; cw = (w - namew - 20) / ndays; rows = 10; rh = (h - 40) / rows
            for d in range(ndays):
                self.text(x + namew + d * cw + cw / 2, y + 24, str(d + 1), "PM", 7, MUTED, "c")
            for r in range(rows):
                yy = y + 34 + r * rh
                self.rect(x + 12, yy + rh / 2 - 7, 6, 14, fill=ACCENTS[r % 4], r=3)
                self.c.setStrokeColor(LINE); self.c.line(x + 24, self.Y(yy + rh / 2 + 6), x + namew - 10, self.Y(yy + rh / 2 + 6))
                for d in range(ndays): self.circle(x + namew + d * cw + cw / 2, yy + rh / 2, min(cw, rh) * 0.32, stroke=LINE, lw=0.7)
        else:  # vertical: días en filas, 6 hábitos en columnas
            cols = 6; dayw = 40; cw = (w - dayw - 16) / cols; rh = (h - 60) / ndays
            for k in range(cols):
                cx = x + dayw + k * cw
                self.rect(cx + 4, y + 12, cw - 8, 30, fill=SOFT, r=6)
                self.rect(cx + cw / 2 - 8, y + 20, 16, 4, fill=ACCENTS[k % 4], r=2)
            for d in range(ndays):
                yy = y + 50 + d * rh
                self.text(x + 14, yy + rh / 2 + 3, str(d + 1), "PM", 7.5, MUTED)
                for k in range(cols): self.circle(x + dayw + k * cw + cw / 2, yy + rh / 2, min(cw, rh) * 0.34, stroke=LINE, lw=0.7)

    def finance(self, m):
        self.page(f"f{m}", month_ctx=m)
        x, y, w, h = self.header(f"Finanzas · {MESES[m-1]}")
        def table(px, py, pw, ph, title, accent, rows, cols=("Concepto", "Monto")):
            p = self.panel(px, py, pw, ph, title, accent)
            self.text(p[0], p[1] + 8, cols[0], "PM", 7.5, MUTED); self.text(p[0] + p[2], p[1] + 8, cols[1], "PM", 7.5, MUTED, "r")
            rh = (p[3] - 14) / rows
            for r in range(rows):
                yy = p[1] + 14 + (r + 1) * rh
                self.c.setStrokeColor(LINE); self.c.line(p[0], self.Y(yy), p[0] + p[2], self.Y(yy))
                self.c.line(p[0] + p[2] * 0.7, self.Y(yy - rh + 4), p[0] + p[2] * 0.7, self.Y(yy - 4))
        if self.mode == "tablet":
            cw = (w - 28) / 3
            table(x, y, cw, h * 0.42, "Ingresos", SAGE, 5)
            table(x, y + h * 0.42 + 14, cw, h * 0.58 - 14, "Ahorro y metas", MUSTARD, 6, ("Meta", "Ahorrado"))
            table(x + cw + 14, y, cw, h, "Gastos fijos", TERRA, 14)
            table(x + 2 * (cw + 14), y, cw, h * 0.66, "Gastos variables", ROSE, 9)
            p = self.panel(x + 2 * (cw + 14), y + h * 0.66 + 14, cw, h * 0.34 - 14, "Resumen", INK)
            for k, lab in enumerate(["Ingresos", "– Gastos", "= Me queda"]):
                yy = p[1] + 4 + k * (p[3] / 3)
                self.text(p[0], yy + 14, lab, "PM" if k == 2 else "P", 10, INK); self.c.setStrokeColor(LINE); self.c.line(p[0] + p[2] * 0.5, self.Y(yy + 17), p[0] + p[2], self.Y(yy + 17))
        else:
            cw = (w - 10) / 2; hh = (h - 2 * 12)
            table(x, y, cw, hh * 0.40, "Ingresos", SAGE, 5)
            table(x + cw + 10, y, cw, hh * 0.40, "Ahorro", MUSTARD, 5, ("Meta", "Ahorro"))
            table(x, y + hh * 0.40 + 12, cw, hh * 0.42, "Gastos fijos", TERRA, 9)
            table(x + cw + 10, y + hh * 0.40 + 12, cw, hh * 0.42, "Variables", ROSE, 9)
            p = self.panel(x, y + hh * 0.82 + 24, w, hh * 0.18, "Resumen", INK)
            for k, lab in enumerate(["Ingresos", "– Gastos", "= Me queda"]):
                cx = p[0] + k * (p[2] / 3)
                self.text(cx, p[1] + 10, lab, "PM" if k == 2 else "P", 9.5, INK); self.c.setStrokeColor(LINE); self.c.line(cx, self.Y(p[1] + 34), cx + p[2] / 3 - 12, self.Y(p[1] + 34))
        self.button(x + w - 170, y - 34 if self.mode == "tablet" else y - 26, 170, 24, "Reto 52 semanas  →", "reto", fill=MUSTARD, color=PAPER, size=8.5)

    def challenge(self):
        self.page("reto")
        x, y, w, h = self.header("Reto de ahorro 52 semanas", "Semana 1 ahorras 1, semana 2 ahorras 2… al final: 1.378")
        self.para(x, y + 4, w, "Multiplica por la cantidad que te funcione (×1, ×5, ×10…) en tu moneda. Rellena el círculo cada semana que cumplas.", "P", 9.5, MUTED)
        y += 30; h -= 30
        cols = 8 if self.mode == "tablet" else 4; rows = (52 + cols - 1) // cols; g = 8
        cw = (w - g * (cols - 1)) / cols; ch = (h - g * (rows - 1)) / rows
        acc = 0
        for k in range(52):
            acc += k + 1
            cx = x + (k % cols) * (cw + g); cy = y + (k // cols) * (ch + g)
            self.rect(cx, cy, cw, ch, fill=PAPER, stroke=LINE, r=8)
            self.text(cx + 10, cy + 16, f"Sem {k+1}", "PM", 8, MUTED)
            self.text(cx + 10, cy + ch / 2 + 9, str(k + 1), "PB", 15, TERRA)
            self.text(cx + 10, cy + ch - 9, f"total {acc}", "P", 7, MUTED)
            self.circle(cx + cw - 15, cy + 15, 7, stroke=SAGE, lw=0.9)

    def reflection(self, m):
        self.page(f"r{m}", month_ctx=m)
        x, y, w, h = self.header(f"Reflexión · {MESES[m-1]}", "Cierra el mes con calma")
        qs = [("¿Qué funcionó?", SAGE), ("¿Qué quiero cambiar?", TERRA), ("Mis logros del mes", MUSTARD), ("Agradezco…", ROSE)]
        if self.mode == "tablet":
            cw = (w - 14) / 2; ch = (h - 14 - 70) / 2
            for i, (q, col) in enumerate(qs):
                p = self.panel(x + (i % 2) * (cw + 14), y + (i // 2) * (ch + 14), cw, ch, q, col); self.lines(*p, gap=22)
            ry = y + 2 * ch + 28
        else:
            ch = (h - 3 * 12 - 82) / 4
            for i, (q, col) in enumerate(qs):
                p = self.panel(x, y + i * (ch + 12), w, ch, q, col); self.lines(*p, gap=22)
            ry = y + 4 * (ch + 12)
        p = self.panel(x, ry, w, y + h - ry, "Mi mes del 1 al 10", INK)
        n = 10; sp = (p[2] - 20) / (n - 1)
        for k in range(n):
            self.circle(p[0] + 10 + k * sp, p[1] + 6, 9, stroke=MUTED, lw=0.7)
            self.text(p[0] + 10 + k * sp, p[1] + 9.5, str(k + 1), "PM", 8, MUTED, "c")

    def student(self):
        self.page("est_horario")
        x, y, w, h = self.header("Horario de clases")
        dias = DIAS[:6]; rows = 10
        self.rect(x, y, w, h, fill=PAPER, stroke=LINE, r=10)
        lab = 54; cw = (w - lab) / len(dias); rh = (h - 30) / rows
        for i, dname in enumerate(dias): self.text(x + lab + i * cw + cw / 2, y + 20, dname[:3].upper() if self.mode == "movil" else dname, "PM", 8.5, MUTED, "c")
        for r in range(rows):
            yy = y + 30 + r * rh
            self.c.setStrokeColor(LINE); self.c.line(x, self.Y(yy), x + w, self.Y(yy))
            self.c.line(x + 8, self.Y(yy + rh - 6), x + lab - 8, self.Y(yy + rh - 6))
        for i in range(len(dias) + 1): self.c.line(x + lab + i * cw, self.Y(y + 30), x + lab + i * cw, self.Y(y + h))
        self.button(x + w - 230, y - 34 if self.mode == "tablet" else y - 26, 110, 24, "Exámenes →", "est_examenes", fill=MUSTARD, color=PAPER, size=8.5)
        self.button(x + w - 112, y - 34 if self.mode == "tablet" else y - 26, 112, 24, "Tareas →", "est_tareas", fill=SAGE, color=PAPER, size=8.5)
        for k in range(2):
            self.page("est_examenes" if k == 0 else "est_examenes2")
            x, y, w, h = self.header("Exámenes y entregas", f"Edición estudiante · {k+1}/2")
            self.rect(x, y, w, h, fill=PAPER, stroke=LINE, r=10)
            cols = [("Materia", .32), ("Fecha", .16), ("Tema / entrega", .36), ("Nota", .16)]
            xx = x + 12
            for name, f in cols: self.text(xx, y + 20, name.upper(), "PM", 8, MUTED); xx += (w - 24) * f
            self.lines(x + 12, y + 26, w - 24, h - 30, 26)
            xx = x + 12
            for name, f in cols[:-1]:
                xx += (w - 24) * f; self.c.setStrokeColor(LINE); self.c.line(xx - 6, self.Y(y + 30), xx - 6, self.Y(y + h - 8))
        self.page("est_tareas")
        x, y, w, h = self.header("Tareas", "Edición estudiante")
        cols = 2 if self.mode == "tablet" else 1; g = 14; cw = (w - g * (cols - 1)) / cols
        for k in range(cols):
            p = self.panel(x + k * (cw + g), y, cw, h, "Pendiente" if k == 0 else "Más tareas", ACCENTS[k])
            for r in range(int(p[3] // 26)):
                yy = p[1] + r * 26 + 4
                self.rect(p[0], yy + 6, 11, 11, stroke=MUTED, r=3, lw=0.7)
                self.c.setStrokeColor(LINE); self.c.line(p[0] + 18, self.Y(yy + 18), p[0] + p[2] - 60, self.Y(yy + 18))
                self.c.line(p[0] + p[2] - 52, self.Y(yy + 18), p[0] + p[2], self.Y(yy + 18))

    def notes(self, n=5):
        for k in range(n):
            self.page(f"notas{k+1}")
            x, y, w, h = self.header(f"Notas {k+1}/{n}")
            self.rect(x, y, w, h, fill=PAPER, stroke=LINE, r=10)
            if k % 2 == 0: self.lines(x + 16, y + 4, w - 32, h - 8, 24)
            else: self.dots(x, y, w, h, 18)
            if k < n - 1: self.button(x + w - 100, y - 34 if self.mode == "tablet" else y - 26, 100, 24, "Siguiente →", f"notas{k+2}", size=8.5)

    def build(self):
        self.cover(); self.instructions(); self.index(); self.vision(); self.year_glance(); self.quarters(); self.important_dates()
        for m in range(1, 13): self.month(m)
        for wi in range(1, 54): self.week(wi)
        for m in range(1, 13): self.habits(m)
        for m in range(1, 13): self.finance(m)
        self.challenge()
        for m in range(1, 13): self.reflection(m)
        self.student(); self.notes()
        self.c.save()


if __name__ == "__main__":
    Planner(OUT / f"Mi-Ano-en-Mini-{YEAR}-Tablet.pdf", 1024, 768, "tablet").build()
    Planner(OUT / f"Mi-Ano-en-Mini-{YEAR}-Movil.pdf", 600, 1300, "movil").build()
    print("ok")
