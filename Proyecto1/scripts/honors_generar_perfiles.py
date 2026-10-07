"""Distinct horizontal plan marker; declared print size, physical calibration pending."""
import json,hashlib,random
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
REPO=Path(__file__).resolve().parents[2]
asset=REPO/'Proyecto1/edificio_G8/Assets';data=asset/'Resources/estructura_p1l4_unity.json'
u=json.loads(data.read_text(encoding='utf-8'));nodes={n['id']:n for n in u['nodes']}
xmin=min(n['x'] for n in nodes.values());xmax=max(n['x'] for n in nodes.values());ymin=min(n['y'] for n in nodes.values());ymax=max(n['y'] for n in nodes.values())
ppm=min((1600-220)/(xmax-xmin),(1600-230-110-160)/(ymax-ymin));cy=230+(1600-230-110-160)/2
center=[(xmin+xmax)/2,(ymin+ymax)/2-(800-cy)/ppm,0]
def xy(n):return (800+(n['x']-center[0])*ppm,800-(n['y']-center[1])*ppm)
im=Image.new('RGB',(1600,1600),'white');d=ImageDraw.Draw(im);rng=random.Random(287)
for _ in range(1800):
    x,y=rng.randrange(18,1550),rng.randrange(18,1550);w,h=rng.randrange(12,65),rng.randrange(12,65);tone=rng.randrange(90,230)
    d.polygon([(x,y),(x+w,y+rng.randrange(0,h)),(x+rng.randrange(0,w),y+h)],fill=(tone,tone,tone))
for _ in range(230):
    x,y=rng.randrange(12,1580),rng.choice([rng.randrange(12,190),rng.randrange(1430,1580)])
    d.rectangle((x,y,x+rng.randrange(8,34),y+rng.randrange(8,32)),fill=(rng.randrange(20,190),rng.randrange(20,150),rng.randrange(20,150)))
for e in u['elements']:
    if e['type']=='rigido' or e['nodeI'] not in nodes or e['nodeJ'] not in nodes:continue
    a,b=nodes[e['nodeI']],nodes[e['nodeJ']]
    if abs(a['z']-3.96)>.05 or abs(b['z']-3.96)>.05:continue
    d.line((xy(a),xy(b)),fill=(20,40,85),width=4)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',40)
d.rectangle((155,62,1490,128),fill='white');d.rectangle((125,1335,1510,1400),fill='white')
d.text((170,70),'MCOC G8 / HONORS / PLANO HORIZONTAL',fill='black',font=font)
d.text((140,1340),'Imagen distinta. Impresion objetivo 20 x 20 cm.',fill='black',font=font)
path=asset/'AR/Marcador_Honors_Plano.png';im.save(path)
modelhash=hashlib.sha256(data.read_bytes()).hexdigest()
common=dict(modelSHA256=modelhash,source='Modelo validado; algoritmo ARStructure.LoadModel / generar_marcador_ar.py',date='2026-10-06',responsible='MCOC G8',declaredWidthMeters=.2,measuredWidthMeters=0,physicalVerified=False)
profiles=[dict(common,markerId='Marcador_E1_243',imageGuid='',reference={'x':.35,'y':-7.25,'z':5.16},mx={'x':0,'y':1,'z':0},my={'x':1,'y':0,'z':0},mz={'x':0,'y':0,'z':1},scale=1,mode=0,sector=True,minimum={'x':-1,'y':-12,'z':3.96},maximum={'x':8.5,'y':.5,'z':7.92},enabled=True,calibrationStatus='DOCUMENTADA; verificacion fisica PENDIENTE'),dict(common,markerId='Marcador_Honors_Plano',imageGuid='',reference=dict(zip(('x','y','z'),center)),mx={'x':1,'y':0,'z':0},my={'x':0,'y':0,'z':1},mz={'x':0,'y':1,'z':0},scale=ppm*.2/1600,mode=2,sector=False,minimum={'x':xmin,'y':ymin,'z':0},maximum={'x':xmax,'y':ymax,'z':50},enabled=False,calibrationStatus='PENDIENTE: medir impresion y confirmar escala/dibujo; no maqueta fisica')]
out=asset/'Resources/Honors/marker_profiles.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(dict(profiles=profiles),indent=2,ensure_ascii=False),encoding='utf-8')
evidence=REPO/'entrega/honors/H2';evidence.mkdir(parents=True,exist_ok=True)
(evidence/'plan_mapping.json').write_text(json.dumps(dict(center=center,pixelsPerModelMeter=ppm,scale=ppm*.2/1600,declaredPrintWidth=.2,physicalCalibration='PENDIENTE',markerSHA256=hashlib.sha256(path.read_bytes()).hexdigest()),indent=2),encoding='utf-8')
print(out)
