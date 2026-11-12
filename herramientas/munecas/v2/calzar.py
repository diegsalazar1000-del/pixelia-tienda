"""Calza una prenda de Canva sobre v2/base.png: escala UNIFORME (no deforma) para que
el cuerpo de la prenda tape el torso de la muñeca, y la sube hasta el cuello."""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as nd
D = __file__.rsplit('/', 1)[0]
BASE = Image.open(D + '/base.png').convert('RGBA')
A = np.asarray(BASE.convert('RGB')).astype(int); H, W = A.shape[:2]; CX = W // 2

def fondo(a):
    wh = a.min(2) > 238; lb, _ = nd.label(wh)
    br = set(np.unique(np.r_[lb[0], lb[-1], lb[:, 0], lb[:, -1]])) - {0}
    return np.isin(lb, list(br))

FG = ~fondo(A)
def torso(y):
    row = FG[y]; l = r = CX
    while l > 0 and row[l-1]: l -= 1
    while r < W-1 and row[r+1]: r += 1
    return r - l
TORSO = max(torso(y) for y in range(int(H*0.40), int(H*0.47)))  # pecho a cintura, sin brazos
NECK = int(H*0.262)

def recorte(p):
    x = np.asarray(Image.open(p).convert('RGB')).astype(int)
    m = ~fondo(x); m = nd.binary_opening(m, iterations=2)
    ys, xs = np.where(m)
    return np.dstack([x, m*255]).astype(np.uint8)[ys.min():ys.max()+1, xs.min():xs.max()+1]

def calzar(p, margen=1.10):
    c = recorte(p); h = c.shape[0]; al = c[..., 3] > 40
    # ancho del cuerpo de la prenda: el más angosto entre 30% y 45% del alto (bajo las mangas)
    anch = [np.ptp(al[y].nonzero()[0]) for y in range(int(h*.30), int(h*.45)) if al[y].any()]
    s = TORSO*margen / min(anch)
    im = Image.fromarray(c).resize((round(c.shape[1]*s), round(h*s)), Image.LANCZOS)
    out = Image.new('RGBA', (W, H)); out.alpha_composite(im, (CX - im.width//2, NECK)) if im.height+NECK <= H else out.paste(im.crop((0,0,im.width,H-NECK)), (CX-im.width//2, NECK))
    return out

def piezas(p):
    """Separa las piezas grandes (ej. blusa y falda sueltas). Devuelve recortes RGBA de arriba a abajo."""
    x = np.asarray(Image.open(p).convert('RGB')).astype(int)
    m = ~fondo(x); m = nd.binary_opening(m, iterations=2); m = nd.binary_fill_holes(m)
    lb, n = nd.label(m); sz = nd.sum(m, lb, range(1, n+1))
    big = [i+1 for i in range(n) if sz[i] > 0.08*sz.max()]
    out = []
    for i in big:
        mi = lb == i; ys, xs = np.where(mi)
        al = (mi & ~fondo(x)) | mi
        rgba = np.dstack([x, mi*255]).astype(np.uint8)[ys.min():ys.max()+1, xs.min():xs.max()+1]
        out.append((ys.mean(), rgba))
    return [r for _, r in sorted(out, key=lambda t: t[0])]

def ancho_min(c, a, b):
    al = c[..., 3] > 40; h = c.shape[0]
    w = [np.ptp(al[y].nonzero()[0]) for y in range(int(h*a), int(h*b)) if al[y].any()]
    return min(w)

def vestir(p, margen=1.10):
    ps = piezas(p)
    if len(ps) == 1:
        return calzar(p, margen)
    top, fal = ps[0], ps[-1]
    s = TORSO*margen / ancho_min(top, .55, .85)   # cuerpo de la blusa bajo las mangas
    T = Image.fromarray(top); T = T.resize((round(T.width*s), round(T.height*s)), Image.LANCZOS)
    al = fal[..., 3] > 40; hf = fal.shape[0]
    cint = np.median([np.ptp(al[y].nonzero()[0]) for y in range(int(hf*.03), int(hf*.09)) if al[y].any()])
    tb = T.getchannel('A').point(lambda v: 255 if v > 40 else 0).getbbox()
    abajo = np.asarray(T.getchannel('A'))[int(T.height*0.95)] > 40
    sf = max(np.ptp(abajo.nonzero()[0]) if abajo.any() else TORSO, TORSO*margen) / cint  # cintura = ancho de la blusa abajo
    F = Image.fromarray(fal); F = F.resize((round(F.width*sf), round(F.height*sf)), Image.LANCZOS)
    out = Image.new('RGBA', (W, H))
    yf = NECK + int(T.height*0.80)
    out.alpha_composite(F.crop((0, 0, F.width, min(F.height, H-yf))), (CX-F.width//2, yf))
    out.alpha_composite(T, (CX-T.width//2, NECK))
    return out

if __name__ == '__main__':
    vestir(sys.argv[1]).save(sys.argv[2])
