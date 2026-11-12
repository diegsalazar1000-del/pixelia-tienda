import fila as F, capas as C, numpy as np, cv2
from PIL import Image
from scipy import ndimage as nd
a=np.asarray(Image.open(F.U+'36dea639-image.jpg').convert('RGB'))
boxes=F.figuras(a)
cas=C.casual.astype(np.uint8)
ref=cv2.GaussianBlur(F.skin(cas),(0,0),6)
Hh,Ww=C.base.shape[:2]
yy=np.arange(Hh)[:,None]
head=C.figura(C.base)&(yy<650)
oldhair=np.asarray(Image.open('pelo.png'))[...,3]>128
full=np.zeros((Hh,Ww),bool); x0,y0,x1,y1=C.CROP; full[y0:y1,x0:x1]=oldhair
hole=nd.binary_erosion(head&~full,iterations=1)&(yy>330)
body=nd.binary_erosion(C.figura(C.casual)&(yy>655),iterations=10)
names=['trenzas','cola','rubia','lisa']
for n,bx in zip(names,boxes):
    w=F.alinear(a,bx,ref)
    wi=w.astype(np.int16).copy(); wi[:,:870]=255; wi[:,1710:]=255
    d=np.abs(wi-C.casual).sum(2)
    blue=(wi[...,2]>wi[...,0]+25); pink=(wi[...,0]>215)&(wi[...,1]<195)&(wi[...,2]>150)&(wi[...,0]-wi[...,1]>45)
    cand=(d>60)&~hole&~body&C.figura(wi)&~blue&~pink&(yy<1150)
    cand=nd.binary_opening(cand,iterations=2)
    lab,k=nd.label(cand); s=nd.sum(cand,lab,range(1,k+1)); cand=np.isin(lab,1+np.where(s>6000)[0])
    cand=nd.binary_closing(cand,iterations=5)&~hole
    C.guardar(wi,cand,n+'.png')
    e=Image.open(n+'.png'); e.resize((e.width//2,e.height//2),Image.LANCZOS).save('web/img/'+n+'.png',optimize=True)
b=Image.open('web/img/base.png').convert('RGBA'); W,H=b.size
out=Image.new('RGBA',(W*4,H),(230,240,255,255))
for i,n in enumerate(names):
    c=Image.new('RGBA',b.size,(230,240,255,255)); c.alpha_composite(b); c.alpha_composite(Image.open('web/img/'+['vestido','fiesta','uniforme','lluvia'][i]+'.png').convert('RGBA')); c.alpha_composite(Image.open('web/img/'+n+'.png').convert('RGBA')); out.paste(c,(i*W,0))
out.resize((out.width*2//3,out.height*2//3)).save('check7.png')
