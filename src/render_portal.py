"""PORTAL motion-graphics film with the unmodified user-provided MP3 audio.
Run python render_portal.py --preview, or python render_portal.py to encode MP4.
Uses Pillow, NumPy, SciPy, CairoSVG and FFmpeg. No credentials or network calls.
"""
from pathlib import Path
from functools import lru_cache
from io import BytesIO
import json, math, subprocess, sys, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import cairosvg

PROJECT=Path(__file__).resolve().parents[1]
ROOT=PROJECT/'build'
ROOT.mkdir(exist_ok=True)
W,H,FPS,DURATION=1920,1080,30,47.64734693877551
AUDIO_SOURCE=PROJECT/'media'/'narration-original.mp3'
VOICE_SPEED=1.0
VOICE_LEAD=0.0
INK='#132E3A'; CREAM='#F7F1E6'; TEAL='#178D8A'; MINT='#A7D9C8'; GOLD='#F0BD69'; CORAL='#DC7962'; DIM='#64808A'
SCENES=[
 (0,5.5,'We wanted to know whether making insulin more affordable could improve diabetes care,'),
 (5.5,10.5,'so we studied nearly five million Medicare beneficiaries with type two diabetes'),
 (10.5,19,'as the thirty-five-dollar monthly cap rolled out in twenty twenty-one and expanded in twenty twenty-three.'),
 (19,26,'After the expansion, insulin users paid about fifty-nine dollars less out of pocket per quarter'),
 (26,29,'and filled slightly more insulin.'),
 (29,34,'Among patients with lab results, average blood sugar also improved modestly,'),
 (34,40,'although serious low-blood-sugar events became slightly more common across the study population.'),
 (40,45.5,'Without an unaffected comparison group, we can’t establish cause and effect.'),
 (45.5,55.5,'Our findings suggest that lower costs can improve access, while persistent costs for other medicines point to the need for broader affordability policies.'),
 (55.5,60,'You can read our full study in JAMA Internal Medicine.'),
]
# Clause starts follow words in the newest audio; onset after silence is refined
# from its waveform. The supplied audio, including every pause, is unchanged.
SCENES.pop(7)
SCENE_VISUALS=[0,1,2,3,4,5,6,8,9]
def speech_time(t):
 return t
CLAUSE_STARTS=[0,5.20,9.82,16.641837,22.384762,24.694036,29.030113,35.03322,44.552268]
SCENES=[(speech_time(CLAUSE_STARTS[i]),
         speech_time(CLAUSE_STARTS[i+1]) if i<8 else DURATION,s)
        for i,(_,_,s) in enumerate(SCENES)]
PALETTES=['dark','light','sand','dark','light','light','coral','light','dark','teal']

def clamp(x): return max(0.,min(1.,x))
def ease(x): return 1-(1-clamp(x))**3
def smooth(x): x=clamp(x); return x*x*(3-2*x)
def lerp(a,b,q): return a+(b-a)*q
def color(s): return tuple(int(s[i:i+2],16) for i in (1,3,5))
def mix(a,b,q): return tuple(round(lerp(x,y,q)) for x,y in zip(color(a),color(b)))
@lru_cache(None)
def font(n,style='sans'):
 fn={'sans':'segoeui.ttf','bold':'segoeuib.ttf','serif':'georgia.ttf','italic':'georgiai.ttf'}[style]
 return ImageFont.truetype('C:/Windows/Fonts/'+fn,int(n))
def txt(d,s,x,y,n=40,c=INK,style='sans',anchor='lt'):
 d.text((round(x),round(y)),s,font=font(n,style),fill=c,anchor=anchor)
def rr(d,b,c,r=20,outline=None,width=2): d.rounded_rectangle(tuple(round(v) for v in b),r,fill=c,outline=outline,width=width)
def line(d,pts,c,w=4): d.line([(round(x),round(y)) for x,y in pts],fill=c,width=w,joint='curve')
def circle(d,x,y,r,c=None,outline=None,w=2):
 if r>0: d.ellipse((round(x-r),round(y-r),round(x+r),round(y+r)),fill=c,outline=outline,width=w)
def reveal(im,s,x,y,n,u,delay=0,c=INK,style='serif'):
 q=ease((u-delay)/.7)
 if q<=0:return
 f=font(n,style); ww=math.ceil(f.getlength(s))+10; hh=int(n*1.42)
 layer=Image.new('RGBA',(ww,hh)); d=ImageDraw.Draw(layer)
 txt(d,s,0,(1-q)*hh,n,c,style)
 im.paste(layer,(int(x),int(y)),layer)
def multi(im,strings,x,y,n,u,c=INK,style='serif',spacing=1.15):
 for k,s in enumerate(strings): reveal(im,s,x,y+k*n*spacing,n,u,k*.12,c,style)
def wrap(s,n,maxw):
 ls=[]; cur=''
 for word in s.split():
  q=(cur+' '+word).strip()
  if font(n).getlength(q)>maxw and cur: ls.append(cur);cur=word
  else:cur=q
 if cur:ls.append(cur)
 return ls
def dashed(d,a,b,c=TEAL,w=4,dash=15):
 length=math.dist(a,b)
 for v in np.arange(0,length,dash*1.8):
  p=v/length;q=min(v+dash,length)/length
  line(d,[(lerp(a[0],b[0],p),lerp(a[1],b[1],p)),(lerp(a[0],b[0],q),lerp(a[1],b[1],q))],c,w)
def dashed_box(d,b,c):
 x1,y1,x2,y2=b
 for a,z in [((x1,y1),(x2,y1)),((x2,y1),(x2,y2)),((x2,y2),(x1,y2)),((x1,y2),(x1,y1))]:dashed(d,a,z,c,3,12)
def curve_point(a,b,c,p):
 return ((1-p)**2*a[0]+2*(1-p)*p*b[0]+p*p*c[0],(1-p)**2*a[1]+2*(1-p)*p*b[1]+p*p*c[1])

@lru_cache(None)
def backdrop(kind):
 a,b={'dark':('#132E3A','#20434B'),'light':('#F7F1E6','#E3ECE3'),'sand':('#F8E9C8','#F7F1E6'),'coral':('#F7E4D6','#F7F1E6'),'teal':('#125754','#163C43')}[kind]
 xx=np.linspace(0,1,W)[None,:,None]; yy=np.linspace(0,1,H)[:,None,None]
 q=np.clip(.15+xx*.56+yy*.16,0,1)
 arr=np.array(color(a))[None,None,:]*(1-q)+np.array(color(b))[None,None,:]*q
 return Image.fromarray(np.uint8(arr),'RGB')

SVGS={
 'vial':'''<rect x="57" y="10" width="86" height="42" rx="8" fill="#203B47"/><path d="M62 53h76v26c0 9 28 17 28 43v135c0 21-13 31-33 31H67c-20 0-33-10-33-31V122c0-26 28-34 28-43z" fill="#FCF8EE" stroke="#173D46" stroke-width="5"/><path d="M39 192h122v65q0 25-28 25H67q-28 0-28-25z" fill="#178D8A"/><rect x="33" y="131" width="134" height="86" rx="4" fill="#E1EDE4"/><text x="100" y="177" text-anchor="middle" font-family="Arial" font-weight="bold" font-size="19" fill="#173D46">INSULIN</text><path d="M54 240v23" stroke="#A7D9C8" stroke-width="7" stroke-linecap="round"/><path d="M65 20v22m15-22v22m15-22v22m15-22v22m15-22v22m15-22v22" stroke="#48636B" stroke-width="3"/>''',
 'wallet':'''<rect x="22" y="46" width="258" height="164" rx="24" fill="#527982"/><path d="M38 47V29q0-12 16-12h195q17 0 17 16v16" fill="#EFBC68"/><path d="M31 78h239" stroke="#94B4B5" stroke-width="4"/><rect x="194" y="101" width="104" height="69" rx="12" fill="#178D8A"/><circle cx="218" cy="135" r="9" fill="#F7F1E6"/><path d="M45 181h89" stroke="#A1BEC0" stroke-width="3" stroke-linecap="round"/>''',
 'receipt':'''<path d="M20 10h180v278l-15-10-15 10-15-10-15 10-15-10-15 10-15-10-15 10-15-10-15 10-15-10-15 10z" fill="#FFFCF3" stroke="#D4D9CE" stroke-width="3"/><rect x="47" y="39" width="126" height="11" rx="5" fill="#178D8A"/><path d="M47 85h126M47 111h105M47 137h126M47 163h87" stroke="#BCCFC7" stroke-width="8" stroke-linecap="round"/><path d="M44 197h132" stroke="#178D8A" stroke-width="3"/><text x="110" y="249" text-anchor="middle" font-family="Georgia" font-size="35" fill="#173D46">$</text>''',
 'person':'''<circle cx="45" cy="24" r="19" fill="#178D8A"/><path d="M15 100V70c0-17 13-26 30-26s30 9 30 26v30z" fill="#178D8A"/><path d="M28 96v28m34-28v28" stroke="#178D8A" stroke-width="16" stroke-linecap="round"/>''',
 'pharmacy':'''<rect x="35" y="86" width="292" height="177" rx="12" fill="#FFF9EC" stroke="#173D46" stroke-width="5"/><path d="M15 89l22-54h288l25 54z" fill="#178D8A"/><path d="M43 35v55m53-55v55m53-55v55m53-55v55m53-55v55m53-55v55" stroke="#A7D9C8" stroke-width="22"/><rect x="148" y="151" width="77" height="112" rx="5" fill="#B5D9CE"/><rect x="56" y="136" width="66" height="68" rx="6" fill="#DBE7D8"/><rect x="251" y="136" width="53" height="68" rx="6" fill="#DBE7D8"/><path d="M179 106v30m-15-15h30" stroke="#178D8A" stroke-width="11"/>''',
 'drop':'''<path d="M100 14C78 61 27 107 27 158a73 73 0 0 0 146 0c0-51-51-97-73-144z" fill="#178D8A"/><path d="M53 164q-1 42 40 49" fill="none" stroke="#B6E0C8" stroke-width="12" stroke-linecap="round"/>''',
 'pill':'''<rect x="14" y="43" width="211" height="90" rx="45" fill="#F7F1E6" stroke="#234953" stroke-width="5"/><path d="M118 45h63a43 43 0 0 1 0 86h-63z" fill="#E1B06A"/><path d="M119 45v86" stroke="#234953" stroke-width="4"/>''',
}
VIEW={'vial':(200,300),'wallet':(320,230),'receipt':(220,300),'person':(90,138),'pharmacy':(365,285),'drop':(200,245),'pill':(240,180)}
@lru_cache(None)
def asset(name):
 w,h=VIEW[name]
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{SVGS[name]}</svg>'
 return Image.open(BytesIO(cairosvg.svg2png(bytestring=svg.encode(),scale=3))).convert('RGBA')
@lru_cache(maxsize=500)
def sized_asset(name,width):
 a=asset(name);return a.resize((width,round(a.height*width/a.width)),Image.Resampling.LANCZOS)
def sprite(im,name,x,y,width,angle=0,opacity=1):
 a=sized_asset(name,max(1,round(width)))
 if abs(angle)>.15:a=a.rotate(round(angle,1),Image.Resampling.BICUBIC,expand=True)
 if opacity<.995:
  a=a.copy();a.putalpha(a.getchannel('A').point(lambda v:int(v*clamp(opacity))))
 im.paste(a,(round(x-a.width/2),round(y-a.height/2)),a)
@lru_cache(None)
def portal_asset(dark,width):
 name='Portal_ReverseLogo_Hex' if dark else 'Portal_Logo_Hex'
 a=Image.open(PROJECT/'assets'/f'{name}.png').convert('RGBA')
 return a.resize((width,round(a.height*width/a.width)),Image.Resampling.LANCZOS)
def portal_logo(im,x,y,width,dark):
 a=portal_asset(dark,width);im.paste(a,(x,y),a)
def coin(im,x,y,size=64,angle=0):
 d=ImageDraw.Draw(im)
 ww=size*max(.18,abs(math.cos(angle)))
 d.ellipse((x-ww,y-size,x+ww,y+size),fill=GOLD,outline='#D49B46',width=4)
 if ww>size*.65:txt(d,'$',x,y-size*.67,round(size*1.3),INK,'serif','mt')
def tag(im,label,x,y,w=246,h=111,angle=0,col=TEAL):
 a=Image.new('RGBA',(w+30,h+30));d=ImageDraw.Draw(a)
 rr(d,(15,15,w+15,h+15),col,24);txt(d,label,w/2+15,27,int(h*.60),CREAM,'bold','mt')
 a=a.rotate(angle,Image.Resampling.BICUBIC,expand=True)
 im.paste(a,(int(x-a.width/2),int(y-a.height/2)),a)
def orbit(d,x,y,r,u,dark=False):
 c='#35545A' if dark else '#D3DDD2'
 for k in range(3):circle(d,x,y,r+k*44,None,c,2)
 for k in range(4):
  theta=u*.24+k*math.pi*.5;circle(d,x+(r+44)*math.cos(theta),y+(r+44)*math.sin(theta),5,GOLD if dark else TEAL)
def hospital(im,x,y,u):
 d=ImageDraw.Draw(im);q=ease((u-.6)/1.8)
 rr(d,(x-238,y-151,x+238,y+157),'#FFF7EB',22,outline='#D8BFB0',width=4)
 rr(d,(x-252,y-199,x+252,y-139),CORAL,14)
 txt(d,'EMERGENCY',x,y-184,32,CREAM,'bold','mt')
 for j in [-1,1]:
  rr(d,(x+j*162-47,y-85,x+j*162+47,y+27),'#C9DAD0',8)
 rr(d,(x-80,y-61,x+80,y+157),INK,7)
 rr(d,(x-80-61*q,y-59,x-61*q,y+154),'#96C0B7',4)
 rr(d,(x+61*q,y-59,x+80+61*q,y+154),'#96C0B7',4)
 rr(d,(x-28,y-127,x+28,y-77),CREAM,5)
 line(d,[(x,y-121),(x,y-82)],CORAL,10);line(d,[(x-20,y-102),(x+20,y-102)],CORAL,10)
 line(d,[(x-257,y+166),(x+257,y+166)],'#B4917E',8)

def scene(i,t):
 a,b,narr=SCENES[i];u=t-a;dur=b-a;i=SCENE_VISUALS[i];dark=PALETTES[i] in ('dark','teal')
 im=backdrop(PALETTES[i]).copy();d=ImageDraw.Draw(im)
 fg=CREAM if dark else INK;sub=MINT if dark else DIM
 # A drifting radial field gives depth without moving the reading area.
 if i not in (1,5,7):orbit(d,1450,440,247+8*math.sin(u*.5),u,dark)
 if i==0:
  txt(d,'ORIGINAL INVESTIGATION',104,148,25,GOLD,'bold')
  multi(im,['Out-of-Pocket Spending for Insulin','by Medicare Beneficiaries','After Monthly Caps'],101,203,61,u,CREAM,spacing=1.19)
  sprite(im,'vial',1640,313+9*math.sin(u*1.3),145,-5+3*math.sin(u))
  tag(im,'$35',1720,190,155,76,angle=3*math.sin(u*1.2))
  txt(d,'AUTHORS',106,477,21,MINT,'bold')
  authors=['Dongzhe Hong','Krystal Cantos','Diana Morgenstern','Sonali Dasgupta',
           'Aaron S. Kesselheim','Zirui Song','Angela Y. Tong','Rohit Chadaram',
           'Danielle Potter','Elisabetta Patorno','Jerry Avorn','Benjamin N. Rome']
  for k,name in enumerate(authors):
   xx=105+(k%4)*438;yy=522+(k//4)*63;qq=ease((u-.55-k*.047)/.65)
   rr(d,(xx,yy+20*(1-qq),xx+402,yy+49+20*(1-qq)),'#24464D',10)
   reveal(im,name,xx+14,yy+10,28,u,.55+k*.047,CREAM,'sans')
  txt(d,'Brigham and Women’s Hospital · Harvard Medical School · IQVIA · UCLA',108,731,24,MINT)
  txt(d,'JAMA Internal Medicine · 2026;186(6):723–731',108,785,23,CREAM)
  txt(d,'doi:10.1001/jamainternmed.2026.0255',1815,785,23,MINT,'sans','rt')
 elif i==1:
  txt(d,'OUR STUDY',104,151,27,TEAL,'bold')
  q=ease((u-.25)/1.55);v=4.8*q
  txt(d,f'{v:.1f}',99,226,166,INK,'serif');txt(d,'million',400,288,87,TEAL,'serif')
  multi(im,['Medicare beneficiaries','with type 2 diabetes'],108,445,46,u,INK,'sans')
  txt(d,'2019–2023 · National claims data',110,594,31,DIM)
  for k in range(48):
   ee=ease((u-.2-k*.028)/1.25);x=1094+(k%8)*91;y=250+(k//8)*81
   sprite(im,'person',x+160*(1-ee)*math.sin(k*2.1),y+240*(1-ee)+3*math.sin(u*1.5+k*.25),45,opacity=ee)
  for j,yr in enumerate(range(2019,2024)):
   x=115+j*347;qq=clamp((u-1.5-j*.48)/.65)
   rr(d,(x,717,x+265,782),TEAL if qq>=1 else '#DEE5DA',16)
   txt(d,str(yr),x+133,729,30,CREAM if qq>=1 else INK,'bold','mt')
  txt(d,'4,759,136 unique patients · quarterly cohorts',110,813,23,DIM)
 elif i==2:
  txt(d,'THE POLICY ROLLOUT',102,151,27,TEAL,'bold')
  multi(im,['A monthly','limit on cost.'],98,234,80,u,INK)
  tag(im,'$35',353,533,392,160,angle=1.1*math.sin(u*.8),col=TEAL)
  txt(d,'Per 30-day supply of each covered insulin',108,670,28,DIM)
  # A calendar turns from the initial rollout to the broader expansion.
  qq=smooth((u-4.65)/.9);stage=qq>.5
  x=1330;y=424
  rr(d,(956,211,1738,670),'#E2D9BE',28)
  rr(d,(932,192,1714,652),'#FFFAEF',28)
  rr(d,(932,192,1714,286),TEAL,24)
  for xx in [1065,1583]:line(d,[(xx,166),(xx,222)],INK,15)
  txt(d,'MEDICARE PART D',1323,217,29,CREAM,'bold','mt')
  txt(d,'2023' if stage else '2021',1323,326,125,INK,'serif','mt')
  txt(d,'Expanded across Part D' if stage else 'Participating plans',1323,503,35,TEAL,'bold','mt')
  if 0<qq<1:
   zz=932+782*qq;d.polygon([(zz-80,287),(zz+15,287),(zz+125,650),(zz+15,650)],fill=GOLD)
  for k in range(8):
   xx=987+k*94;ee=ease((u-(5.0 if stage else .8)-k*.09)/.5)
   rr(d,(xx,707+36*(1-ee),xx+65,769+36*(1-ee)),TEAL if stage or k<3 else '#DADBD0',12)
   if stage or k<3:line(d,[(xx+17,737+36*(1-ee)),(xx+29,749+36*(1-ee)),(xx+49,726+36*(1-ee))],CREAM,5)
  txt(d,'Coverage illustrated schematically; total monthly costs can exceed $35 for multiple insulin products.',103,817,22,DIM)
 elif i==3:
  txt(d,'AFTER THE 2023 EXPANSION',104,151,27,GOLD,'bold')
  reveal(im,'$58.59',94,218,159,u,2.35,CREAM)
  reveal(im,'less per quarter',106,423,63,u,2.95,GOLD,'bold')
  multi(im,['Out of pocket for insulin','among insulin users'],108,543,36,u,CREAM,'sans',1.4)
  txt(d,'95% CI: $57.27–$59.91 less',110,699,29,MINT)
  sprite(im,'receipt',1484,336+7*math.sin(u),223,-7+2*math.sin(u*.7))
  # Money travels from the bill to the wallet, illustrating reduced patient costs.
  for k in range(5):
   p=((u*.28+k*.19)%1);xx,yy=curve_point((1530,422),(1114,470),(1465,644),p)
   coin(im,xx,yy,26,u*2+k)
  sprite(im,'wallet',1455,652,440,2*math.sin(u*.8))
  txt(d,'Estimated immediate change in mean quarterly spending · Table 2',108,817,22,MINT)
 elif i==4:
  txt(d,'ACCESS TO INSULIN',102,151,27,TEAL,'bold')
  multi(im,['A little more insulin','filled by existing users.'],100,224,70,u,INK)
  reveal(im,'+1.16 units per day',104,423,48,u,.4,TEAL,'bold')
  txt(d,'2023 estimate · 95% CI: +0.89 to +1.44',105,490,26,DIM)
  line(d,[(323,704),(1680,704)],'#C6D7CB',16)
  for k in range(18):circle(d,357+k*70+20*math.sin(u*2),704,6,TEAL)
  sprite(im,'pharmacy',269,640,310)
  for k in range(4):
   p=(u*.17+k*.255)%1;xx=520+930*p
   sprite(im,'vial',xx,642,92,2*math.sin(u*2+k),min(p*7,(1-p)*7,1))
  sprite(im,'person',1674,616,119)
  tag(im,'Rx',1668,458,122,80,angle=3*math.sin(u))
  txt(d,'Prescription fills measure insulin obtained, not injections taken.',104,817,23,DIM)
 elif i==5:
  txt(d,'BLOOD SUGAR',104,151,27,TEAL,'bold')
  reveal(im,'A small average improvement.',100,211,69,u,0,INK)
  reveal(im,'−0.06',104,327,123,u,.25,TEAL)
  txt(d,'percentage points in mean A1c',111,489,38,INK)
  rr(d,(1140,351,1770,512),'#E0EADC',22)
  txt(d,'207,197',1172,373,62,TEAL,'serif')
  txt(d,'patients with laboratory data',1178,457,27,DIM)
  sprite(im,'drop',1665,251+6*math.sin(u*1.4),97,-6+3*math.sin(u))
  # The effect and uncertainty are drawn on a real, labeled scale.
  lo,hi=220,1690;y=672
  def xx(v):return lo+(v+.10)/.10*(hi-lo)
  line(d,[(lo,y),(hi,y)],'#B9CFC2',4)
  for v in [-.10,-.08,-.06,-.04,-.02,0]:
   xp=xx(v);line(d,[(xp,y-8),(xp,y+8)],INK,3);txt(d,'0' if v==0 else f'{v:.2f}',xp,705,26,DIM,'sans','mt')
  dashed(d,(hi,572),(hi,686),DIM,2,8)
  q=ease((u-1.35)/1.65);cx=xx(-.06*q);left=lerp(cx,xx(-.08),q);right=lerp(cx,xx(-.03),q)
  line(d,[(left,y),(right,y)],TEAL,11)
  for z in [left,right]:line(d,[(z,y-18),(z,y+18)],TEAL,5)
  circle(d,cx,y,15,TEAL);circle(d,cx,y,26,None,TEAL,2)
  txt(d,'95% confidence interval: −0.08 to −0.03',955,768,27,DIM,'sans','mt')
  txt(d,'Adjusted change after January 2023 · HbA1c reflects average blood sugar',107,817,22,DIM)
 elif i==6:
  txt(d,'WATCHING SAFETY, TOO',103,151,27,CORAL,'bold')
  multi(im,['A small increase','in severe lows.'],98,239,86,u,INK)
  multi(im,['Low blood sugar requiring','emergency care or hospitalization'],104,485,35,u,INK,'sans',1.5)
  hospital(im,1435,523,u)
  for k in range(2):circle(d,1435,421,165+(u*.15+k*.5)%1*73,None,'#D8AA98',2)
  txt(d,'Clinical benefits and harms both matter.',104,759,32,CORAL,'bold')
  txt(d,'Small increases in severe hypoglycemia were reported alongside the benefits.',105,817,23,DIM)
 elif i==7:
  txt(d,'UNDERSTANDING THE EVIDENCE',104,151,27,TEAL,'bold')
  multi(im,['An observational study.'],101,223,78,u,INK)
  # A real observed cohort beside the missing comparison makes the design limit visible.
  rr(d,(104,397,839,726),'#DEEBDF',24)
  txt(d,'What we observed',139,420,33,TEAL,'bold')
  for k in range(7):sprite(im,'person',180+k*92,546+6*math.sin(u+k*.4),51)
  txt(d,'Policy changes and patient outcomes',140,642,28,INK)
  q=ease((u-.65)/1.1);dashed_box(d,(1068,397,1804,726),'#96B4AA')
  txt(d,'What we could not compare',1104,420,33,DIM,'bold')
  txt(d,'?',1434,484,105,DIM,'serif','mt')
  txt(d,'An unaffected group',1436,642,30,DIM,'sans','mt')
  circle(d,954,561,53,TEAL);txt(d,'≠',954,519,74,CREAM,'sans','mt')
  if q<1:d.rectangle((1067+737*q,395,1807,728),fill=backdrop('light').getpixel((1550,400)))
  txt(d,'The cap alone cannot be established as the cause of these changes.',106,812,27,DIM)
 elif i==8:
  txt(d,'BEYOND INSULIN',103,151,27,GOLD,'bold')
  change=38.72-35.03322
  if u<change:
   multi(im,['Lower costs can','improve access.'],97,228,83,u,CREAM)
   reveal(im,'What might broader affordability policies do?',106,486,32,u,.3,MINT,'sans')
  else:
   multi(im,['Other medicines','were still expensive.'],97,228,83,u-change,CREAM)
   reveal(im,'Affordability goes beyond one prescription.',106,486,34,u-change,.3,MINT,'sans')
  # A fan of bills opens to show costs extending beyond one insulin prescription.
  for k in range(3):
   q=ease((u-k*.19)/1.0)
   sprite(im,'receipt',1440+(k-1)*170*q,390+abs(k-1)*45,268,(k-1)*14*q+2*math.sin(u+k))
  sprite(im,'pill',1303,650+11*math.sin(u*1.2),184,-25)
  sprite(im,'pill',1631,642+11*math.sin(u*1.2+1),160,24)
  sprite(im,'wallet',1464,689,349,2*math.sin(u))
  rr(d,(109,628,845,710),'#31545B',17)
  txt(d,'Broader cost policies could help.',135,651,32,CREAM,'bold')
  txt(d,'Observational study: the cap alone cannot be established as the cause.',106,817,23,MINT)
 elif i==9:
  portal_logo(im,105,170,570,True)
  multi(im,['Read our','full study.'],98,414,80,u,CREAM)
  txt(d,'Hong and colleagues',109,639,33,GOLD,'bold')
  txt(d,'JAMA Internal Medicine · 2026',109,694,31,MINT)
  txt(d,'doi:10.1001/jamainternmed.2026.0255',109,770,25,CREAM)
  q=ease(u/.9);xx=lerp(1530,1439,q);yy=446
  rr(d,(xx-345+17,yy-272+22,xx+345+17,yy+283+22),'#183B3F',17)
  rr(d,(xx-345,yy-272,xx+345,yy+283),'#FFFAEF',17)
  txt(d,'ORIGINAL INVESTIGATION',xx-304,yy-231,24,TEAL,'bold')
  line(d,[(xx-303,yy-180),(xx+298,yy-180)],TEAL,5)
  for k,s in enumerate(['Out-of-Pocket Spending','for Insulin by Medicare','Beneficiaries After','Monthly Caps']):txt(d,s,xx-303,yy-142+k*58,43,INK,'serif')
  txt(d,'Hong et al. · 2026;186(6):723–731',xx-303,yy+133,25,DIM)
  rr(d,(xx-303,yy+198,xx+298,yy+260),TEAL,14)
  txt(d,'READ AT JAMA NETWORK  →',xx,yy+215,25,CREAM,'bold','mt')
 return im

def transition(old,new,q,kind):
 q=smooth(q)
 if kind=='push':
  out=Image.new('RGB',(W,H),INK);x=round(W*q)
  out.paste(old,(-x,0));out.paste(new,(W-x,0));return out
 mask=Image.new('L',(W,H),0);d=ImageDraw.Draw(mask)
 if kind=='iris':
  r=2200*q;d.ellipse((1450-r,440-r,1450+r,440+r),fill=255)
 elif kind=='diagonal':
  x=-H+(W+2*H)*q;d.polygon([(0,0),(x,0),(x-H,H),(0,H)],fill=255)
 elif kind=='rise':d.rectangle((0,H*(1-q),W,H),fill=255)
 else:
  for k in range(6):
   p=ease((q-k*.035)/.825);y=k*H/6
   if k%2:d.rectangle((W*(1-p),y,W,y+H/6+1),fill=255)
   else:d.rectangle((0,y,W*p,y+H/6+1),fill=255)
 return Image.composite(new,old,mask)

def frame(t):
 i=next((j for j,(a,b,_) in enumerate(SCENES) if a<=t<b),len(SCENES)-1);a,b,narr=SCENES[i]
 im=scene(i,t)
 if i and t-a<.48:
  im=transition(scene(i-1,a-1/FPS),im,(t-a)/.48,['iris','diagonal','shutter','push','iris','rise','shutter','diagonal','push'][i-1])
 # Captions stay fixed through transitions so the narration cues remain exact.
 d=ImageDraw.Draw(im);dark=PALETTES[SCENE_VISUALS[i]] in ('dark','teal')
 fg=CREAM if dark else INK
 if SCENE_VISUALS[i]!=9:portal_logo(im,100,17,310,dark)
 else:txt(d,'INSULIN, ACCESS & HEALTH',101,63,22,GOLD,'bold')
 txt(d,'JAMA INTERNAL MEDICINE  ·  2026',1819,63,21,fg,'sans','rt')
 line(d,[(100,135),(1820,135)],'#54716F' if dark else '#CCD7CA',2)
 rr(d,(77,875,1843,1024),'#0B2630' if dark else '#EEE8DA',20)
 ls=wrap(narr,33,1640);y=930-(len(ls)-1)*22
 for j,s in enumerate(ls):txt(d,s,960,y+j*44,33,fg,'sans','mt')
 txt(d,'STUDY SUMMARY',101,841,16,MINT if dark else DIM,'bold')
 txt(d,f'{i+1:02d} / {len(SCENES):02d}',1818,841,18,MINT if dark else DIM,'sans','rt')
 # Markers connect the film's rhythm to the actual narration.
 for k,(aa,bb,_) in enumerate(SCENES):
  x1=100+1720*aa/DURATION;x2=100+1720*bb/DURATION-5
  line(d,[(x1,1051),(x2,1051)],'#55716F' if dark else '#CBD5C8',4)
  if t>aa:line(d,[(x1,1051),(min(x2,100+1720*t/DURATION),1051)],GOLD if dark else TEAL,4)
 return im

def docs():
 (ROOT/'recording_script.txt').write_text(' '.join(s for _,_,s in SCENES)+'\n',encoding='utf-8')
 def ts(t):
  return f'{int(t)//60:02d}:{t%60:05.2f}'
 (ROOT/'timed_script.txt').write_text('\n\n'.join(f'{ts(a)}–{ts(b)}\n{s}' for a,b,s in SCENES)+'\n',encoding='utf-8')
 (ROOT/'timeline.json').write_text(json.dumps([dict(start=a,end=b,narration=s) for a,b,s in SCENES],indent=2,ensure_ascii=False),encoding='utf-8')
 def st(t):
  ms=round(t*1000);return f'00:{ms//60000:02d}:{(ms//1000)%60:02d},{ms%1000:03d}'
 (ROOT/'captions.srt').write_text('\n\n'.join(f'{i+1}\n{st(a)} --> {st(b)}\n{s}' for i,(a,b,s) in enumerate(SCENES)),encoding='utf-8')
 count=len(re.findall(r'[A-Za-z]+', ' '.join(s for _,_,s in SCENES)))
 (ROOT/'README.md').write_text(f'''# PORTAL insulin study promo

47.65 seconds, 1920 × 1080, 30 fps. The newest user-provided MP3 is copied directly into the video without audio processing, volume changes, music, trimming, or speed changes. Every original pause is preserved.

The connected script contains approximately {count} spoken words and follows the newest supplied recording, media/narration-original.mp3. The audio stream is copied with FFmpeg -c:a copy. Transitions follow clause starts measured in that original recording, with phrase onsets after silence refined from the waveform; see timeline.json and timed_script.txt. The comparison-group sentence is absent from this recording, so that separate scene was removed and the observational limitation retained on screen. The video runs for the full audio duration, rounded up to the next 30 fps frame.


Official standard and reverse PORTAL logo assets were obtained from https://portalresearch.org/about-portal/ and are recorded in assets/source.txt. The logo appears throughout the video and is featured on the closing card. The opening card lists all twelve authors in published order.

New motion: eight varied scene transitions; an opening card with the full title, all twelve authors, affiliations and article citation; population assembly; a turning policy calendar; savings flowing into a wallet; pharmacy-to-patient prescription fills; an animated confidence interval; emergency-department doors; bills opening into a fan; and a PORTAL article end card.

Counts, coins, people and policy tiles are illustrative, not additional study measurements. The A1c interval is the actual reported estimate and 95% CI. The confidence interval settles before the scene ends. All quantitative findings retain their population and time units.

Source: Hong et al. *Out-of-Pocket Spending for Insulin by Medicare Beneficiaries After Monthly Caps*. JAMA Internal Medicine. 2026;186(6):723–731. https://doi.org/10.1001/jamainternmed.2026.0255

The 'nearly five million' narration is a conversational rounding of 4,759,136; the screen retains 4.8 million. This is an original adaptation, not an official journal production.
''',encoding='utf-8')
 print(f'Conversational narration: about {count} spoken words',flush=True)

def previews():
 ts=[(a+b)/2 for a,b,_ in SCENES]
 sheet=Image.new('RGB',(1920,1080),color(CREAM))
 for j,t in enumerate(ts):
  im=frame(t);im.save(ROOT/f'preview_{j+1:02d}.jpg',quality=95)
  sheet.paste(im.resize((480,270),Image.Resampling.LANCZOS),((j%4)*480,(j//4)*270))
 d=ImageDraw.Draw(sheet);txt(d,'PORTAL / ORIGINAL AUDIO',1020,849,36,INK,'bold');txt(d,'Every pause preserved · nine synchronized scenes',1020,919,24,DIM)
 sheet.save(ROOT/'storyboard.jpg',quality=95)

def render():
 out=ROOT/'PORTAL_Insulin_Study_Original_Audio.mp4'
 cmd=['ffmpeg','-y','-hide_banner','-loglevel','warning','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-i',str(AUDIO_SOURCE),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(out)]
 p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 try:
  for f in range(math.ceil(FPS*DURATION)):
   p.stdin.write(frame(f/FPS).tobytes())
   if f%300==0:print(f'Rendered {f//FPS}/{DURATION:.2f} seconds',flush=True)
 finally:p.stdin.close()
 if p.wait()!=0:raise RuntimeError('Video encoder failed')
 print(out,flush=True)

if __name__=='__main__':
 docs();previews()
 if '--preview' not in sys.argv:render()
