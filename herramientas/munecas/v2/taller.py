"""Taller de ropa: dibuja vestidos por código siguiendo EXACTAMENTE el cuerpo de base.png
(calzan siempre). Estilo: relleno plano + sombra suave + contorno morado como la muñeca."""
import numpy as np, math
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as nd
D = __file__.rsplit('/', 1)[0]
BASE = Image.open(D + '/base.png').convert('RGBA')
A = np.asarray(BASE.convert('RGB')).astype(int); H, W = A.shape[:2]; CX = W // 2
_wh = A.min(2) > 240; _lb, _ = nd.label(_wh)
FG = ~np.isin(_lb, list(set(np.unique(np.r_[_lb[0], _lb[-1], _lb[:, 0], _lb[:, -1]])) - {0}))
_cl = (A.min(2) > 215) & (np.abs(A[..., 0]-A[..., 2]) < 25) & FG; _cl[:int(H*.28)] = False
CLOTH = nd.binary_dilation(nd.binary_opening(_cl, iterations=2), iterations=8)
YY, XX = np.mgrid[0:H, 0:W]
LINEA = (62, 36, 78)

def ext(m, y):
    r = np.where(m[y])[0]; return (r.min(), r.max()) if len(r) else None

def forma(largo=.80, vuelo=1.0, manga='corta', cuello='redondo'):
    """máscara del vestido: torso (sobre la camiseta) + mangas (sobre los brazos) + falda acampanada"""
    m = np.zeros((H, W), bool)
    yw = int(H*.47)                                   # cintura
    top = CLOTH.copy(); top[yw:] = False; m |= top
    if cuello == 'redondo':                           # sube el escote a un cuello redondo de niña
        cy = int(H*.275); m |= ((XX-CX)**2/(95**2) + (YY-cy)**2/(40**2) <= 1) & (YY >= cy) & FG
        m |= (YY > cy) & (YY < int(H*.31)) & np.abs(XX-CX) < 0  # (sin efecto, legible)
        for y in range(cy, int(H*.31)):
            e = ext(CLOTH, y) or ext(top, y)
            if e: m[y, e[0]:e[1]+1] = True
    if manga != 'sin':
        y1 = int(H*(.345 if manga == 'corta' else .335))
        arms = FG.copy(); arms[:int(H*.282)] = False; arms[y1:] = False
        for y in range(int(H*.282), y1):
            e = ext(CLOTH, y)
            if e: arms[y, e[0]-4:e[1]+5] = False
        arms = nd.binary_dilation(arms, iterations=10 if manga == 'globo' else 5)
        arms[:int(H*.282)] = False
        m |= arms
    # falda: de la cintura al ruedo, acampanada
    e = ext(CLOTH, yw); hw0 = (e[1]-e[0])/2 + 6
    yh = int(H*largo); hw1 = min(hw0 + (yh-yw)*0.42*vuelo, W/2 - 24)
    for y in range(yw, yh+1):
        t = (y-yw)/max(1, yh-yw); hw = hw0 + (hw1-hw0)*t**0.9
        m[y, int(CX-hw):int(CX+hw)+1] = True
    # ruedo redondeado (un poco más largo al centro)
    bott = (((XX-CX)/hw1)**2 <= 1) & (YY > yh) & (YY < yh + 18*np.sqrt(np.clip(1-((XX-CX)/hw1)**2, 0, 1)))
    m |= bott
    return nd.binary_fill_holes(nd.binary_closing(m, iterations=3)), yw, yh, hw1

# ---------- telas ----------
def liso(c): return np.ones((H, W, 3))*np.array(c)
def lunares(c, d, r=11, paso=46):
    img = liso(c); gx = (XX % paso) - paso/2; gy = ((YY + (XX//paso % 2)*paso//2) % paso) - paso/2
    img[gx**2+gy**2 < r*r] = d; return img
def cuadritos(c, d, paso=34):
    a = ((XX//paso) % 2) ^ ((YY//paso) % 2); img = liso(c)
    img[((XX//paso) % 2) == 1] = np.array(c)*.5+np.array(d)*.5
    img[((YY//paso) % 2) == 1] = np.array(c)*.5+np.array(d)*.5
    img[(((XX//paso) % 2) == 1) & (((YY//paso) % 2) == 1)] = d; return img
def rayas(c, d, paso=40):
    img = liso(c); img[(YY//(paso//2)) % 2 == 1] = d; return img
def flores(c, cols, paso=90, r=13):
    img = Image.fromarray(liso(c).astype(np.uint8)); dr = ImageDraw.Draw(img)
    rng = np.random.default_rng(7)
    for j, y in enumerate(range(0, H, paso)):
        for i, x in enumerate(range(-paso, W+paso, paso)):
            x2 = x + (paso//2 if j % 2 else 0) + rng.integers(-14, 15); y2 = y + rng.integers(-14, 15)
            col = cols[(i+j) % len(cols)]; s = r*(0.75+0.5*rng.random())
            for k in range(5):
                an = k*2*math.pi/5 + rng.random()
                px, py = x2+math.cos(an)*s, y2+math.sin(an)*s
                dr.ellipse((px-s*.75, py-s*.75, px+s*.75, py+s*.75), fill=col)
            dr.ellipse((x2-s*.45, y2-s*.45, x2+s*.45, y2+s*.45), fill=(255, 214, 90))
    return np.asarray(img).astype(float)
def estrellas(c, d, paso=70):
    img = Image.fromarray(liso(c).astype(np.uint8)); dr = ImageDraw.Draw(img)
    for j, y in enumerate(range(0, H, paso)):
        for x in range((j % 2)*paso//2, W, paso):
            pts = [(x+math.cos(k*math.pi/5-math.pi/2)*(12 if k % 2 == 0 else 5), y+math.sin(k*math.pi/5-math.pi/2)*(12 if k % 2 == 0 else 5)) for k in range(10)]
            dr.polygon(pts, fill=d)
    return np.asarray(img).astype(float)

def pintar(m, tela, yw, yh, hw1, falda=None, cinta=None, encaje=None, botones=None, cuello_col=None):
    img = tela.copy()
    if falda is not None:
        sk = m & (YY >= yw); img[sk] = falda[sk]
    # sombra: bordes más oscuros + pliegues verticales en la falda
    dist = nd.distance_transform_edt(m)
    sh = 1 - 0.18*np.exp(-dist/18)
    plie = 1 - 0.07*(0.5+0.5*np.cos((XX-CX)/max(1, hw1)*math.pi*4.0)) * np.clip((YY-yw)/(yh-yw+1), 0, 1) * (YY >= yw)
    img = img * (sh*plie)[..., None]
    rgba = np.zeros((H, W, 4), np.uint8); rgba[..., :3] = np.clip(img, 0, 255); rgba[..., 3] = m*255
    im = Image.fromarray(rgba); dr = ImageDraw.Draw(im)
    if cinta:
        band = m & (YY >= yw-14) & (YY <= yw+14); a = np.asarray(im).copy(); a[band, :3] = cinta; im = Image.fromarray(a); dr = ImageDraw.Draw(im)
    if encaje:  # volado de encaje en el ruedo
        a = np.asarray(im).copy(); hem = m & (YY > yh-34); a[hem, :3] = encaje
        im = Image.fromarray(a); dr = ImageDraw.Draw(im)
        for x in range(int(CX-hw1), int(CX+hw1), 26):
            yb = yh + 18*math.sqrt(max(0, 1-((x+13-CX)/hw1)**2))
            dr.ellipse((x, yb-12, x+26, yb+12), fill=encaje+(255,))
            dr.ellipse((x+10, yb-22, x+16, yb-16), fill=LINEA+(255,))
    if cuello_col:
        cy = int(H*.275)
        for sx in (-1, 1):
            dr.pieslice((CX-62 if sx < 0 else CX-2, cy-6, CX+2 if sx < 0 else CX+62, cy+56), 0, 180, fill=cuello_col+(255,), outline=LINEA+(255,), width=4)
    if botones:
        for k in range(3):
            y = int(H*.33) + k*48; dr.ellipse((CX-11, y-11, CX+11, y+11), fill=botones+(255,), outline=LINEA+(255,), width=3)
    # contorno como la muñeca
    a = np.asarray(im).copy(); mm = a[..., 3] > 0
    borde = nd.binary_dilation(mm, iterations=5) & ~nd.binary_erosion(mm, iterations=1)
    a[borde, :3] = LINEA; a[borde, 3] = 255
    linea_c = (np.abs(YY-yw) <= 2) & mm; a[linea_c, :3] = LINEA
    im = Image.fromarray(a).filter(ImageFilter.SMOOTH)
    return im

CAT = {
 'flores-rosado': lambda: (forma(.78, 1.0, 'globo'), dict(tela=liso((255, 214, 230)), falda=flores((255, 160, 196), [(255, 255, 255), (255, 236, 120), (190, 120, 230)]), cinta=(240, 90, 150), encaje=(255, 250, 245))),
 'lunares-azul': lambda: (forma(.74, 1.1, 'corta'), dict(tela=lunares((120, 160, 240), (255, 255, 255)), cinta=(255, 255, 255), cuello_col=(255, 255, 255))),
 'cuadritos-lila': lambda: (forma(.76, 1.0, 'globo'), dict(tela=cuadritos((246, 236, 255), (176, 140, 230)), encaje=(255, 252, 240), botones=(255, 140, 180), cuello_col=(255, 255, 255))),
 'estrellas-noche': lambda: (forma(.80, 1.2, 'sin'), dict(tela=liso((60, 70, 160)), falda=estrellas((70, 90, 190), (255, 225, 110)), cinta=(255, 215, 90))),
 'rayas-marinero': lambda: (forma(.74, 1.0, 'corta'), dict(tela=liso((255, 255, 255)), falda=rayas((255, 255, 255), (60, 90, 170)), cinta=(220, 50, 60), cuello_col=(60, 90, 170))),
 'joropo': lambda: (forma(.90, 1.45, 'globo'), dict(tela=liso((255, 255, 255)), falda=flores((40, 70, 170), [(235, 50, 60), (255, 205, 40), (255, 140, 190)]), cinta=(235, 50, 60), encaje=(255, 205, 40))),
}

def hacer(nombre):
    (m, yw, yh, hw1), kw = CAT[nombre]()
    return pintar(m, yw=yw, yh=yh, hw1=hw1, **kw)

if __name__ == '__main__':
    import sys
    for n in CAT: hacer(n).save(f'{D}/ropa_{n}.png')
