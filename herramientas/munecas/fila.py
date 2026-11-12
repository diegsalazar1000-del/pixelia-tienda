import numpy as np, cv2, sys
from PIL import Image
from scipy import ndimage as nd
import capas as C

U = '/mnt/user-data/uploads/'


def skin(a):
    a = a.astype(np.int16)
    return ((a[..., 0] > 225) & (a[..., 1] > 185) & (a[..., 1] < 235) & (a[..., 2] > 160) & (a[..., 2] < 220)
            & (a[..., 0] - a[..., 2] > 15)).astype(np.float32)


def figuras(a):
    m = (765 - a.astype(int).sum(2)) > 40
    m = nd.binary_closing(m, iterations=4); m = nd.binary_fill_holes(m)
    lab, n = nd.label(m); s = nd.sum(m, lab, range(1, n + 1))
    out = []
    for i in np.argsort(-s)[:4]:
        ys, xs = np.where(lab == i + 1); out.append((xs.min(), ys.min(), xs.max(), ys.max()))
    return sorted(out)


BASE = C.base.astype(np.uint8)
bb = (977, 106, 1601, 1331)
sb = cv2.GaussianBlur(skin(BASE), (0, 0), 6)
fb = cv2.GaussianBlur(C.figura(C.base).astype(np.float32), (0, 0), 6)


def alinear(a, box, ref=None):
    """affine-warp a so that the doll in box lands on the base doll"""
    x0, y0, x1, y1 = box
    sx = (bb[2] - bb[0]) / (x1 - x0); sy = (bb[3] - bb[1]) / (y1 - y0)
    M = np.array([[sx, 0, bb[0] - x0 * sx], [0, sy, bb[1] - y0 * sy]], np.float32)
    H, W = BASE.shape[:2]
    w = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
    tpl = sb if ref is None else ref
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)
    W2 = np.eye(2, 3, dtype=np.float32)
    try:
        _, W2 = cv2.findTransformECC(tpl, cv2.GaussianBlur(skin(w), (0, 0), 6), W2, cv2.MOTION_AFFINE, crit, None, 5)
        w = cv2.warpAffine(w, W2, (W, H), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderValue=(255, 255, 255))
    except cv2.error as e:
        print('ecc fail', e)
    return w
