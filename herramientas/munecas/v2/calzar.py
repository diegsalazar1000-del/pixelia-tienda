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

if __name__ == '__main__':
    calzar(sys.argv[1]).save(sys.argv[2])
