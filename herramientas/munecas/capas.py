import numpy as np, cv2
from PIL import Image
from scipy import ndimage as nd

U = '/mnt/user-data/uploads/'
L = lambda f: np.asarray(Image.open(U + f).convert('RGB')).astype(np.int16)
base = L('7eb160e9-image.jpg')
casual = L('783f6157-image.jpg')
vest = L('2e8d496b-image.jpg')
pelo = L('a536e471-image.jpg')
H, W, _ = base.shape
CROP = (800, 40, 1776, 1380)  # x0,y0,x1,y1


def mascara(a, b, ymin=0, ymax=None, thr=55):
    d = np.abs(a - b).sum(2)
    m = d > thr
    if ymin: m[:ymin] = False
    if ymax: m[ymax:] = False
    m = nd.binary_opening(m, iterations=2)
    lab, n = nd.label(m)
    if n:
        sizes = nd.sum(m, lab, range(1, n + 1))
        keep = np.isin(lab, 1 + np.where(sizes > 1500)[0])
        m = keep
    m = nd.binary_closing(m, iterations=6)
    m = nd.binary_fill_holes(m)
    m = nd.binary_dilation(m, iterations=3)  # include outline
    return m


def guardar(img, m, name):
    a = (cv2.GaussianBlur(m.astype(np.float32), (5, 5), 0) * 255).astype(np.uint8)
    rgba = np.dstack([img.astype(np.uint8), a])
    x0, y0, x1, y1 = CROP
    Image.fromarray(rgba[y0:y1, x0:x1]).save(name)


def figura(img):
    # everything not near-white, filled
    m = (255 * 3 - img.sum(2)) > 40
    m = nd.binary_closing(m, iterations=4)
    m = nd.binary_fill_holes(m)
    lab, n = nd.label(m)
    sizes = nd.sum(m, lab, range(1, n + 1))
    return lab == (1 + sizes.argmax())


guardar(base, figura(base), 'base.png')
mv = mascara(vest, base, ymin=640) & figura(vest)
guardar(vest, mv, 'vestido.png')
mc = mascara(casual, base, ymin=650) & figura(casual)
guardar(casual, mc, 'casual.png')
mp = mascara(pelo, casual, thr=50) & figura(pelo)
guardar(pelo, mp, 'pelo.png')
print('ok', mv.sum(), mc.sum(), mp.sum())
