from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, subprocess, os
src=Image.open('/tmp/hab/pdf/c_hi-05.png').convert('RGB').crop((0,0,1880,490))
W,H=1080,1350; FPS=24
x0,dx=354,33.27; ys=[241+35*i for i in range(7)]; rh=34.5
def purple(p): return p[2]>230 and p[0]<200 and p[1]<190
empty=src.copy(); d=ImageDraw.Draw(empty); checked=[]
for r,y in enumerate(ys):
    for c in range(31):
        cx0=int(x0+c*dx)+2; cy0=int(y)+2
        if purple(src.getpixel((cx0+3,cy0+3))):
            checked.append((r,c)); d.rectangle([cx0,cy0,int(x0+(c+1)*dx)-2,int(y+rh)-2],fill=(255,255,255))
# tapar KPIs de arriba (se muestran animados abajo) y columnas de resultados
kpi_box=(386,18,1880,128)
d.rectangle(kpi_box,fill=(255,255,255))
F=lambda s,w='Bold': ImageFont.truetype(f'/usr/share/fonts/opentype/inter/Inter-{w}.otf',s)
def frame(t):
    T=12.0
    img=Image.new('RGB',(W,H),(14,11,30)); g=ImageDraw.Draw(img)
    for i in range(H):  # degradado
        k=i/H; g.line([(0,i),(W,i)],fill=(int(14+40*k),int(11+10*k),int(30+60*k)))
    g.text((60,70),'¿Anotas tus metas y a la',font=F(56),fill=(255,255,255))
    g.text((60,135),'semana ya ni te acuerdas?',font=F(56),fill=(255,155,210))
    g.text((60,215),'Ya no tienes que hacer esto: marca ✓ y mira tu racha crecer.',font=F(30,'Medium'),fill=(200,200,225))
    # avance: días revelados
    days=max(0,min(31,int((t-1.2)/7.0*31)+1)) if t>1.2 else 0
    sheet=empty.copy()
    if days: 
        m=Image.new('L',src.size,0); ImageDraw.Draw(m).rectangle([0,0,int(x0+days*dx),src.height],fill=255)
        m2=Image.new('L',src.size,255); ImageDraw.Draw(m2).rectangle(kpi_box,fill=0)
        from PIL import ImageChops
        sheet.paste(src,(0,0),ImageChops.multiply(m,m2))
    zoom=1.0+0.25*max(0,min(1,(t-8.6)/1.5))
    sw=int(980*1.0); sh=int(sheet.height*sw/sheet.width)
    view=sheet.crop((0,0,min(sheet.width,int(1390/zoom*1.0+ (1880-1390)*(1-min(1,max(0,(t-8.6)/1.5))))),sheet.height)) if False else sheet.crop((0,0,1390,490))
    view=view.resize((980,int(490*980/1390)),Image.LANCZOS)
    card=Image.new('RGB',(view.width+20,view.height+20),(255,255,255)); card.paste(view,(10,10))
    img.paste(card,(40,300))
    # contadores
    pct=[0,0]; streak=0
    done=sum(1 for (r,c) in checked if c<days); tot=7*days if days else 1
    p=round(100*done/max(1,sum(1 for (r,c) in checked)) *0.93) if days else 0
    st=min(23,max(0,days-8)) if days>8 else min(days,7)
    y0=300+card.height+50
    boxes=[('AVANCE',f'{p}%',(124,92,255)),('🔥RACHA'.replace('🔥',''),(f'{st} días' if st!=1 else '1 día'),(255,140,60)),('NIVEL','Imparable' if days>=31 else ('En racha' if days>14 else 'Arrancando'),(255,79,163))]
    bw=(W-80-2*20)//3
    for i,(lab,val,col) in enumerate(boxes):
        bx=40+i*(bw+20); g.rounded_rectangle([bx,y0,bx+bw,y0+170],radius=26,fill=(255,255,255))
        g.rounded_rectangle([bx,y0,bx+bw,y0+48],radius=26,fill=col); g.rectangle([bx,y0+26,bx+bw,y0+48],fill=col)
        g.text((bx+bw/2,y0+24),lab,font=F(24),fill=(255,255,255),anchor='mm')
        g.text((bx+bw/2,y0+110),val,font=F(46 if len(val)<9 else 34),fill=(30,25,60),anchor='mm')
    # final
    if t>9.4:
        a=min(1,(t-9.4)/0.5); s=0.7+0.3*(1-(1-a)**3)
        bh=int(150*s); bwid=int(900*s); bx=(W-bwid)//2; by=H-330
        g.rounded_rectangle([bx,by,bx+bwid,by+bh],radius=40,fill=(124,92,255))
        g.text((W/2,by+bh/2),'¡Imparable! Ya es tu estilo de vida',font=F(int(46*s)),fill=(255,255,255),anchor='mm')
    if t>10.3:
        g.text((W/2,H-120),'Mi 2027 en Hábitos · Excel y Google Sheets',font=F(34),fill=(255,255,255),anchor='mm')
        g.text((W/2,H-70),'pixeliadigital.app',font=F(30,'Medium'),fill=(255,155,210),anchor='mm')
    return img
os.makedirs('/tmp/vid/f',exist_ok=True)
N=int(12*FPS)
for i in range(N): frame(i/FPS).save(f'/tmp/vid/f/{i:04d}.jpg',quality=90)
frame(11.5).save('/tmp/vid/poster.jpg',quality=85)
