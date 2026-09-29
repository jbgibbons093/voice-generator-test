"""Original PORTAL motion graphics synchronized to the supplied narration.
No speech edits, added music, or sound effects. Requires Pillow, NumPy,
CairoSVG, Windows Segoe UI fonts, and FFmpeg. Run --preview for stills.
"""
from pathlib import Path
from functools import lru_cache
from io import BytesIO
import math, json, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cairosvg

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/'build'/'generic-spending'
ROOT.mkdir(parents=True,exist_ok=True)
W,H,FPS=1920,1080,30
DURATION=55.32734693877551
NAVY='#171D4B'; BLUE='#416CF1'; CORAL='#ED795D'; LILAC='#DDE2FF'
PAPER='#F8F7F2'; WHITE='#FFFFFF'; GRAY='#61708B'; PALE='#EBEEFB'
SCENES=[
 (0,5.626304,'question','We wanted to understand how generic and brand-name medicines contribute to patients’ out-of-pocket costs,'),
 (5.626304,11.495986,'survey','so we analyzed a nationally representative survey of prescription use and spending in twenty twenty-two.'),
 (11.495986,17.833356,'use','More than half of Americans filled a generic prescription, compared with about one in six who filled a brand-name prescription.'),
 (17.833356,20.720567,'unit','Although brand-name drugs were more expensive per medicine,'),
 (20.720567,25.701429,'spending','generics accounted for fifty-five percent of total out-of-pocket prescription spending.'),
 (25.701429,30.347120,'both','Our findings suggest that policies to reduce patients’ costs should address both.'),
 (30.347120,35.011995,'brand','Lower brand-name prices could reduce what patients pay through deductibles and coinsurance.'),
 (35.011995,38.150068,'benefits','For generics, we highlight changes in insurance benefits:'),
 (38.150068,41.426100,'cap','limiting out-of-pocket costs for high-value generic medicines,'),
 (41.426100,44.221020,'cash','preventing patient charges from exceeding cash prices,'),
 (44.221020,47.069592,'zero','or eliminating generic copayments altogether.'),
 (47.069592,52.652086,'together','These approaches address both the prices of medicines and how insurance determines patients’ costs.'),
 (52.652086,DURATION,'end','You can read our full study in JAMA Network Open.'),
]
MODES=['dark','light','light','peach','dark','blue','light','dark','light','peach','dark','light','blue']

def clamp(x):return max(0.,min(1.,x))
def ease(x):return 1-(1-clamp(x))**3
def smooth(x):x=clamp(x);return x*x*(3-2*x)
def lerp(a,b,x):return a+(b-a)*x
def rgb(s):return tuple(int(s[i:i+2],16) for i in (1,3,5))
@lru_cache(None)
def font(n,style='regular'):
 name={'regular':'segoeui.ttf','bold':'segoeuib.ttf','light':'segoeuil.ttf'}[style]
 return ImageFont.truetype('C:/Windows/Fonts/'+name,int(n))
def text(d,s,x,y,n=36,c=NAVY,style='regular',anchor='lt'):
 d.text((round(x),round(y)),s,font=font(n,style),fill=c,anchor=anchor)
def box(d,b,c,r=24,outline=None,width=2):
 d.rounded_rectangle(tuple(round(v) for v in b),radius=r,fill=c,outline=outline,width=width)
def line(d,pts,c,w=3):d.line([(round(x),round(y)) for x,y in pts],fill=c,width=w,joint='curve')
def dot(d,x,y,r,c,outline=None,w=2):
 d.ellipse((round(x-r),round(y-r),round(x+r),round(y+r)),fill=c,outline=outline,width=w)
def reveal(im,s,x,y,n,u,delay=0,c=NAVY,style='bold'):
 q=ease((u-delay)/.55)
 if q<=0:return
 layer=Image.new('RGBA',(int(font(n,style).getlength(s))+20,int(n*1.45)))
 text(ImageDraw.Draw(layer),s,0,(1-q)*n*1.3,n,c,style)
 im.paste(layer,(round(x),round(y)),layer)
def lines(im,rows,x,y,n,u,c=NAVY,spacing=1.16):
 for j,s in enumerate(rows):reveal(im,s,x,y+j*n*spacing,n,u,j*.09,c)
def wrap(s,n,width):
 out=[];cur=''
 for w in s.split():
  candidate=(cur+' '+w).strip()
  if cur and font(n).getlength(candidate)>width:out.append(cur);cur=w
  else:cur=candidate
 if cur:out.append(cur)
 return out
def check(d,x,y,c=BLUE,size=24):
 line(d,[(x-size*.5,y),(x-size*.07,y+size*.38),(x+size*.65,y-size*.54)],c,max(3,round(size*.2)))
def arrow(d,a,b,c=BLUE,w=5):
 line(d,[a,b],c,w)
 th=math.atan2(b[1]-a[1],b[0]-a[0]);sz=18
 line(d,[(b[0]-sz*math.cos(th-.55),b[1]-sz*math.sin(th-.55)),b,(b[0]-sz*math.cos(th+.55),b[1]-sz*math.sin(th+.55))],c,w)
def person(d,x,y,s,c):
 dot(d,x,y-s*.46,s*.19,c)
 box(d,(x-s*.24,y-s*.15,x+s*.24,y+s*.41),c,s*.14)
 line(d,[(x-s*.15,y+s*.27),(x-s*.15,y+s*.74)],c,max(2,round(s*.13)))
 line(d,[(x+s*.15,y+s*.27),(x+s*.15,y+s*.74)],c,max(2,round(s*.13)))

@lru_cache(None)
def backdrop(mode):
 a,b={'dark':(NAVY,'#2A3064'),'light':(PAPER,'#ECEDFA'),'peach':('#FFF2E8','#F5E9E8'),'blue':('#335EDB','#203B98')}[mode]
 xx=np.linspace(0,1,W)[None,:,None];yy=np.linspace(0,1,H)[:,None,None]
 q=np.clip(xx*.55+yy*.24,0,1)
 return Image.fromarray(np.uint8(np.array(rgb(a))[None,None,:]*(1-q)+np.array(rgb(b))[None,None,:]*q))

@lru_cache(None)
def logo(dark,width):
 name='Portal_ReverseLogo_Hex' if dark else 'Portal_Logo_Hex'
 a=Image.open(REPO/'assets'/f'{name}.png').convert('RGBA')
 return a.resize((width,round(width*a.height/a.width)),Image.Resampling.LANCZOS)
def paste_logo(im,x,y,width,dark):
 a=logo(dark,width);im.paste(a,(int(x),int(y)),a)

@lru_cache(None)
def icon(name,variant='generic'):
 c=BLUE if variant=='generic' else CORAL
 if name=='pack':
  body=f'''<rect x="24" y="8" width="190" height="267" rx="17" fill="#FFFFFF" stroke="#171D4B" stroke-width="4"/><path d="M25 83h188v-59q0-15-15-15H40q-15 0-15 15z" fill="{c}"/><path d="M36 278l-16 17h176l18-20" fill="#BCC6E5"/><rect x="57" y="116" width="124" height="49" rx="24" fill="{c}" transform="rotate(-24 120 140)"/><path d="M118 118v47" stroke="#FFFFFF" stroke-width="4" transform="rotate(-24 120 140)"/><path d="M56 210h119m-119 18h92" stroke="#B0BDD8" stroke-width="8" stroke-linecap="round"/><text x="119" y="56" fill="#FFFFFF" text-anchor="middle" font-family="Arial" font-size="24" font-weight="bold">{'GENERIC' if variant=='generic' else 'BRAND'}</text>'''
  size=(240,310)
 elif name=='survey':
  body='''<path d="M28 12h213l64 67v287H28z" fill="#FFFFFF" stroke="#171D4B" stroke-width="4"/><path d="M240 12v70h65" fill="#DDE2FF"/><rect x="66" y="72" width="122" height="13" rx="6" fill="#416CF1"/><g stroke="#9CAAD0" stroke-width="8" stroke-linecap="round"><path d="M111 143h142m-142 65h142m-142 65h101"/></g><g fill="#DDE2FF"><rect x="60" y="125" width="31" height="31" rx="7"/><rect x="60" y="190" width="31" height="31" rx="7"/><rect x="60" y="255" width="31" height="31" rx="7"/></g><g fill="none" stroke="#416CF1" stroke-width="5"><path d="M65 140l8 8 13-18m-21 75l8 8 13-18m-21 75l8 8 13-18"/></g>'''
  size=(340,390)
 elif name=='insurance':
  body='''<rect x="14" y="16" width="412" height="245" rx="24" fill="#FFFFFF" stroke="#171D4B" stroke-width="5"/><path d="M15 92h410V41q0-25-25-25H40Q15 16 15 41z" fill="#416CF1"/><text x="43" y="67" font-family="Arial" font-weight="bold" font-size="25" fill="#FFFFFF">PRESCRIPTION COVERAGE</text><circle cx="86" cy="153" r="25" fill="#DDE2FF"/><path d="M43 226v-22q0-26 43-26t43 26v22" fill="#DDE2FF"/><path d="M164 139h205m-205 34h163m-163 35h112" stroke="#ACBAD5" stroke-width="10" stroke-linecap="round"/>'''
  size=(440,280)
 elif name=='tag':
  body=f'''<path d="M70 14h195q22 0 22 24v120q0 24-22 24H70L10 99z" fill="{c}"/><circle cx="65" cy="98" r="11" fill="#FFFFFF"/><text x="179" y="139" text-anchor="middle" font-family="Arial" font-size="105" font-weight="bold" fill="#FFFFFF">$</text>'''
  size=(310,200)
 elif name=='shield':
  body='''<path d="M126 12Q176 51 235 55v87q0 90-109 152Q17 232 17 142V55q59-4 109-43z" fill="#416CF1"/><path d="M65 151l39 43 86-103" fill="none" stroke="#FFFFFF" stroke-width="17" stroke-linecap="round" stroke-linejoin="round"/>'''
  size=(255,310)
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{size[0]}" height="{size[1]}" viewBox="0 0 {size[0]} {size[1]}">{body}</svg>'
 return Image.open(BytesIO(cairosvg.svg2png(bytestring=svg.encode(),scale=3))).convert('RGBA')
@lru_cache(maxsize=400)
def sized_icon(name,var,width):
 a=icon(name,var);return a.resize((width,round(a.height*width/a.width)),Image.Resampling.LANCZOS)
def sprite(im,name,x,y,width,angle=0,var='generic',opacity=1):
 a=sized_icon(name,var,round(width))
 if abs(angle)>.15:a=a.rotate(angle,Image.Resampling.BICUBIC,expand=True)
 if opacity<.999:
  a=a.copy();a.putalpha(a.getchannel('A').point(lambda z:round(z*clamp(opacity))))
 im.paste(a,(round(x-a.width/2),round(y-a.height/2)),a)
def coin(d,x,y,r=25,c=CORAL,flip=0):
 w=r*max(.22,abs(math.cos(flip)))
 d.ellipse((x-w,y-r,x+w,y+r),fill=c)
 if w>r*.6:text(d,'$',x,y-r*.8,round(r*1.45),WHITE,'bold','mt')
def pill(d,x,y,w=90,h=37,c=BLUE):
 box(d,(x-w/2,y-h/2,x+w/2,y+h/2),c,round(h/2))
 line(d,[(x,y-h/2+3),(x,y+h/2-3)],WHITE,3)
def background_motion(d,t,dark):
 c='#414774' if dark else '#D5DCEF'
 for k in range(7):
  x=1740+math.sin(t*.35+k)*65;y=218+k*82+8*math.cos(t*.5+k)
  line(d,[(x-48,y),(x+48,y)],c,2);dot(d,x+48,y,3,c)
def note(im,s,dark=False):
 text(ImageDraw.Draw(im),s,100,805,23,LILAC if dark else GRAY)
def eyebrow(im,s,dark,u=0):
 text(ImageDraw.Draw(im),s,100,163,25,CORAL if dark else BLUE,'bold')

def scene(index,t):
 a,b,name,narr=SCENES[index];u=t-a;dark=MODES[index] in ('dark','blue')
 im=backdrop(MODES[index]).copy();d=ImageDraw.Draw(im)
 fg=WHITE if dark else NAVY
 background_motion(d,t,dark)
 if name=='question':
  eyebrow(im,'RESEARCH LETTER',True)
  lines(im,['Patient Out-of-Pocket Spending','on Generic and Brand-Name','Prescription Drugs'],96,235,70,u,WHITE)
  for j,(who,x) in enumerate([('Christopher L. Cai',100),('Aaron S. Kesselheim',665),('Benjamin N. Rome',1230)]):
   q=ease((u-.55-j*.1)/.6);box(d,(x,574+45*(1-q),x+521,647+45*(1-q)),'#303865',15)
   reveal(im,who,x+20,592,32,u,.55+j*.1,WHITE,'regular')
  text(d,'JAMA Network Open · 2026;9(9):e2633401',102,688,28,LILAC)
  text(d,'doi:10.1001/jamanetworkopen.2026.33401',1818,696,22,LILAC,'regular','rt')
  text(d,'PORTAL · Brigham and Women’s Hospital · Harvard Medical School',102,745,23,LILAC)
  text(d,'Christopher L. Cai: now at the University of Minnesota School of Medicine',102,788,22,LILAC)
  sprite(im,'pack',1539,333+math.sin(u)*9,151,-10,var='generic')
  sprite(im,'pack',1705,386+math.sin(u+1)*9,145,11,var='brand')
 elif name=='survey':
  eyebrow(im,'THE STUDY',False)
  lines(im,['A national picture','of prescription costs.'],98,235,79,u)
  reveal(im,'2022',101,455,144,u,.3,BLUE,'light')
  text(d,'Medical Expenditure Panel Survey',106,650,34,NAVY)
  text(d,'Prescription use + patient spending',106,713,30,GRAY)
  # Survey pages collect individual medication and spending records.
  for k in [2,1,0]:
   q=ease((u-.1-k*.1)/1.15)
   sprite(im,'survey',1480+(k-1)*68*q,453+(k-1)*18,365,(-8+8*k)*q)
  for k in range(7):
   p=(u*.22+k*.143)%1;x=1030+310*p;y=683-300*p+math.sin(p*math.pi)*40
   pill(d,x,y,60,25,BLUE if k%2 else CORAL)
  note(im,'Nationally representative, cross-sectional survey of the noninstitutionalized US population.')
 elif name=='use':
  eyebrow(im,'WHO FILLED A PRESCRIPTION?',False)
  lines(im,['Generic medicines were used more widely.'],98,224,62,u)
  panels=[(100,BLUE,'GENERIC','51.9%',.519,0),(998,CORAL,'BRAND-NAME','15.8%',.158,14.383129-a)]
  for x,c,label,val,pct,delay in panels:
   q=ease((u-delay)/.85)
   box(d,(x,351,x+820,754),WHITE,25)
   text(d,label,x+30,378,30,c,'bold')
   text(d,val,x+30,434,104,c,'light')
   text(d,'More than half' if label=='GENERIC' else 'About one in six',x+33,572,29,GRAY)
   # Two separate scales; these groups overlap.
   box(d,(x+32,649,x+785,680),'#E8ECF8',15)
   if q>0:box(d,(x+32,649,x+32+753*pct*q,680),c,15)
   for k in range(12):
    xx=x+356+(k%6)*69;yy=463+(k//6)*100
    person(d,xx,yy,50,c if (k+.5)/12<pct*q else '#DFE4F4')
  note(im,'Share of the population with at least one fill in 2022. The two groups overlap.')
 elif name=='unit':
  eyebrow(im,'COST PER MEDICINE',False)
  lines(im,['Brand-name drugs','cost more per medicine.'],98,237,77,u)
  text(d,'Per-drug cost and total patient spending tell different parts of the story.',104,716,29,GRAY)
  sprite(im,'pack',1178,482+math.sin(u)*6,231,-6,var='generic')
  sprite(im,'pack',1550,434+math.sin(u+1)*6,275,5,var='brand')
  for k in range(2):coin(d,1125+k*67,693,24,BLUE,u*.7+k)
  for k in range(4):coin(d,1438+k*68,654,24,CORAL,u*.7+k)
  note(im,'Source: Cai, Kesselheim, and Rome · JAMA Network Open · 2026')
 elif name=='spending':
  eyebrow(im,'TOTAL ANNUAL PATIENT SPENDING',True)
  lines(im,['Generics accounted for the larger share.'],98,225,65,u,WHITE)
  cx,cy,r=460,527,206
  d.arc((cx-r,cy-r,cx+r,cy+r),-90,270,fill='#444B76',width=54)
  q=ease(u/1.55);angle=360*.552*q
  d.arc((cx-r,cy-r,cx+r,cy+r),-90,-90+angle,fill='#86A4FF',width=54)
  if q>.01:d.arc((cx-r,cy-r,cx+r,cy+r),-90+angle+1,270,fill=CORAL,width=54)
  text(d,f'{55.2*q:.1f}%',cx,459,97,WHITE,'light','mt')
  text(d,'GENERICS',cx,582,29,LILAC,'bold','mt')
  for j,(label,value,c) in enumerate([('Generic medicines',16.8,'#86A4FF'),('Brand-name medicines',13.7,CORAL)]):
   yy=365+j*206
   text(d,label,885,yy,32,WHITE)
   text(d,f'${value:.1f} billion',1720,yy-14,54,c,'bold','rt')
   box(d,(886,yy+82,1721,yy+124),'#353E6C',15)
   qq=ease((u-.3-j*.25)/1.1)
   if qq>0:box(d,(886,yy+82,886+835*(value/18)*qq,yy+124),c,15)
  note(im,'Estimated national out-of-pocket spending · 2022, expressed in 2026 dollars',True)
 elif name=='both':
  eyebrow(im,'POLICY IMPLICATIONS',True)
  lines(im,['Affordability policy','should address both.'],98,227,82,u,WHITE)
  for j,(x,lab,var) in enumerate([(1140,'BRAND-NAME','brand'),(1570,'GENERIC','generic')]):
   q=ease((u-.25-j*.12)/.9);yy=lerp(720,410,q)
   box(d,(x-180,yy-176,x+180,yy+210),WHITE,25)
   sprite(im,'pack',x,yy-9,159,4*math.sin(u+j),var)
   text(d,lab,x,yy+138,28,NAVY,'bold','mt')
  text(d,'Drug prices',1139,696,36,WHITE,'bold','mt')
  text(d,'Insurance benefits',1570,696,36,WHITE,'bold','mt')
  note(im,'Policy proposals discussed by Cai, Kesselheim, and Rome.',True)
 elif name=='brand':
  eyebrow(im,'BRAND-NAME DRUGS',False)
  lines(im,['Lower prices can reduce patient costs.'],98,222,66,u)
  # A price tag feeds both benefit mechanisms, then the patient payment.
  box(d,(100,378,579,731),WHITE,28)
  sprite(im,'tag',339,535+45*ease(u/1.4),266,-5,var='brand')
  text(d,'Drug price',339,674,29,NAVY,'bold','mt')
  box(d,(738,365,1210,529),'#DFE6FE',23)
  box(d,(738,567,1210,731),'#E8E0FA',23)
  text(d,'Deductibles',974,422,40,NAVY,'bold','mt')
  text(d,'Coinsurance',974,625,40,NAVY,'bold','mt')
  box(d,(1384,378,1819,731),WHITE,28)
  person(d,1600,502,121,BLUE)
  text(d,'Patient payment',1600,674,29,NAVY,'bold','mt')
  for yy in [447,649]:
   arrow(d,(590,550),(717,yy),CORAL,4);arrow(d,(1227,yy),(1366,550),BLUE,4)
   p=(u*.44+(yy==649)*.5)%1
   coin(d,lerp(1240,1350,p),lerp(yy,550,p),16,BLUE,u)
  note(im,'When deductibles or coinsurance tie patient payments to the drug’s price.')
 elif name=='benefits':
  eyebrow(im,'GENERIC MEDICINES',True)
  lines(im,['Change how insurance','shares the cost.'],98,231,84,u,WHITE)
  text(d,'Three options from the paper',105,541,36,LILAC)
  for j,lab in enumerate(['LIMIT COSTS','CASH-PRICE PROTECTION','ZERO COPAYS']):
   y=635+j*55;q=ease((u-.25-j*.16)/.65)
   dot(d,123,y+14,14,CORAL)
   text(d,lab,155+40*(1-q),y,25,WHITE,'bold')
  sprite(im,'insurance',1445,477+9*math.sin(u*1.2),615,-4+2*math.sin(u))
  sprite(im,'pack',1637,691+6*math.sin(u),158,10,var='generic')
 elif name=='cap':
  eyebrow(im,'GENERIC POLICY OPTION 01',False)
  lines(im,['Limit out-of-pocket costs','for high-value generics.'],98,244,69,u)
  sprite(im,'shield',296,640,177,-5+2*math.sin(u))
  text(d,'Put a ceiling on patient costs.',430,640,31,GRAY)
  cap_y=350
  box(d,(1132,cap_y,1773,cap_y+34),BLUE,12)
  text(d,'COST LIMIT',1453,293,31,BLUE,'bold','mt')
  for j in range(3):
   x=1255+j*180
   for k in range(4):
    q=ease((u-.1-k*.15-j*.1)/1.2);yy=lerp(764,665-k*76,q)
    coin(d,x,yy,32,BLUE,u*.4+k)
   pill(d,x,742,114,40,CORAL)
  note(im,'Policy options discussed in the paper · High-value generic medicines')
 elif name=='cash':
  eyebrow(im,'GENERIC POLICY OPTION 02',False)
  lines(im,['Keep patient charges','at or below cash prices.'],98,244,68,u)
  text(d,'Insurance should not leave patients paying more.',105,482,31,GRAY)
  x1,x2,y=1273,1616,719;h=221
  q=ease(u/1.85);patient_h=lerp(342,h,q)
  box(d,(x1-91,y-h,x1+91,y),BLUE,16)
  box(d,(x2-91,y-patient_h,x2+91,y),CORAL,16)
  line(d,[(1103,y-h),(1785,y-h)],NAVY,3)
  text(d,'Cash price',x1,753,28,NAVY,'bold','mt')
  text(d,'Patient charge',x2,753,28,NAVY,'bold','mt')
  if q>.98:
   text(d,'≥',1470,518,83,NAVY,'bold','mt')
   check(d,1616,446,BLUE,40)
  note(im,'Policy options discussed in the paper · Protection against charges above cash prices')
 elif name=='zero':
  eyebrow(im,'GENERIC POLICY OPTION 03',True)
  lines(im,['Consider eliminating','generic copayments.'],98,249,81,u,WHITE)
  text(d,'Remove the patient’s copayment.',105,535,35,LILAC)
  cx,cy=1471,491;q=ease(u/1.6)
  for k in range(8):
   th=k*math.pi/4+u*.15;rr=lerp(200,390,q)
   opacity=1-q
   if opacity>.01:
    # Coins dissolve into the background as the zero takes their place.
    col=tuple(round(lerp(z,b,q)) for z,b in zip(rgb(CORAL),rgb('#293263')))
    coin(d,cx+rr*math.cos(th),cy+rr*.7*math.sin(th),27,col,u+k)
  reveal(im,'$0',1257,318,236,u,.18,WHITE,'light')
  text(d,'GENERIC COPAY',1471,630,31,LILAC,'bold','mt')
  sprite(im,'pack',492,706,150,-9,var='generic')
  note(im,'Policy options discussed in the paper · Eliminating generic copayments',True)
 elif name=='together':
  eyebrow(im,'THE POLICY IMPLICATION',False)
  lines(im,['What patients pay depends on both.'],98,222,69,u)
  # Two moving inputs meet at the patient's out-of-pocket payment.
  box(d,(103,395,605,715),WHITE,27)
  box(d,(1315,395,1818,715),WHITE,27)
  sprite(im,'tag',350,492,230,-5,var='brand')
  sprite(im,'insurance',1567,491,292,4)
  text(d,'Drug prices',353,641,36,NAVY,'bold','mt')
  text(d,'Insurance benefits',1567,641,36,NAVY,'bold','mt')
  cx,cy=959,545
  dot(d,cx,cy,151,BLUE);person(d,cx,cy-13,141,WHITE)
  text(d,'Patient costs',cx,741,36,BLUE,'bold','mt')
  for left in [True,False]:
   xstart,xend=(623,785) if left else (1297,1133)
   arrow(d,(xstart,cy),(xend,cy),CORAL,6)
   for k in range(3):
    p=(u*.34+k/3)%1;dot(d,lerp(xstart,xend,p),cy,8,BLUE)
  note(im,'Affordability policies should address generic and brand-name medicines.')
 elif name=='end':
  paste_logo(im,101,207,634,True)
  lines(im,['Read our full study.'],99,467,69,u,WHITE)
  text(d,'Cai · Kesselheim · Rome',104,600,34,WHITE,'bold')
  text(d,'JAMA Network Open · September 2026',104,661,29,LILAC)
  text(d,'doi:10.1001/jamanetworkopen.2026.33401',105,765,25,WHITE)
  q=ease(u/.65);xx=lerp(1545,1450,q)
  box(d,(xx-347,211,xx+347,775),WHITE,28)
  text(d,'RESEARCH LETTER',xx-307,250,25,BLUE,'bold')
  line(d,[(xx-307,310),(xx+307,310)],CORAL,6)
  for j,s in enumerate(['Patient Out-of-Pocket','Spending on Generic','and Brand-Name','Prescription Drugs']):
   text(d,s,xx-307,354+j*63,45,NAVY,'bold')
  text(d,'2026;9(9):e2633401',xx-307,640,29,GRAY)
  box(d,(xx-308,701,xx+308,752),BLUE,13)
  text(d,'READ AT JAMA NETWORK',xx-18,710,25,WHITE,'bold','mt')
  line(d,[(xx+227,735),(xx+248,714)],WHITE,3)
  line(d,[(xx+232,714),(xx+248,714),(xx+248,730)],WHITE,3)
 return im

def transition(old,new,p,kind):
 q=smooth(p)
 if kind=='split':
  out=new.copy();dx=round(W*q/2)
  out.paste(old.crop((0,0,W//2,H)),(-dx,0));out.paste(old.crop((W//2,0,W,H)),(W//2+dx,0));return out
 if kind=='lift':
  out=Image.new('RGB',(W,H),NAVY);dy=round(H*q)
  out.paste(old,(0,-dy));out.paste(new,(0,H-dy));return out
 mask=Image.new('L',(W,H));d=ImageDraw.Draw(mask)
 if kind=='round':
  r=q*2080;d.ellipse((420-r,490-r,420+r,490+r),fill=255)
 elif kind=='bands':
  for k in range(8):
   qq=ease((q-k*.023)/.84);x=k*W/8
   if k%2:d.rectangle((x,0,x+W/8+1,H*qq),fill=255)
   else:d.rectangle((x,H*(1-qq),x+W/8+1,H),fill=255)
 else:
  x=-500+(W+1000)*q;d.polygon([(0,0),(x,0),(x+500,H),(0,H)],fill=255)
 return Image.composite(new,old,mask)

def frame(t):
 i=next((j for j,(a,b,_,_) in enumerate(SCENES) if a<=t<b),len(SCENES)-1)
 a,b,name,narr=SCENES[i];dark=MODES[i] in ('dark','blue');im=scene(i,t)
 if i and t-a<.38:
  kind=['split','round','bands','lift','round','split','diagonal','bands','lift','round','split','diagonal'][i-1]
  im=transition(scene(i-1,a-1/FPS),im,(t-a)/.38,kind)
 d=ImageDraw.Draw(im);fg=WHITE if dark else NAVY
 if name!='end':paste_logo(im,100,28,282,dark)
 else:text(d,'GENERIC + BRAND-NAME MEDICINES',103,66,22,WHITE,'bold')
 text(d,'JAMA NETWORK OPEN  ·  2026',1819,61,23,fg,'regular','rt')
 line(d,[(100,143),(1820,143)],'#5A6597' if dark else '#CBD3E9',2)
 if i>0:
  text(d,'FULL STUDY' if name=='end' else ('FINDINGS' if i<=4 else 'POLICY IMPLICATIONS'),959,74,19,LILAC if dark else GRAY,'bold','mt')
 box(d,(79,874,1841,1028),'#10183C' if dark else WHITE,20)
 rows=wrap(narr,32,1640);yy=947-(len(rows)-1)*22
 for j,s in enumerate(rows):text(d,s,960,yy+j*44,32,fg,'regular','mt')
 text(d,f'{i+1:02d} / {len(SCENES):02d}',1818,836,18,LILAC if dark else GRAY,'regular','rt')
 text(d,'STUDY SUMMARY',103,837,17,LILAC if dark else GRAY,'bold')
 # A continuous sweep replaces the previous video's segmented progress bar.
 line(d,[(100,1054),(1820,1054)],'#55608A' if dark else '#CBD3E9',3)
 line(d,[(100,1054),(100+1720*t/DURATION,1054)],CORAL,5)
 return im

def docs():
 (ROOT/'timeline.json').write_text(json.dumps([{'start':a,'end':b,'scene':n,'narration':s} for a,b,n,s in SCENES],indent=2,ensure_ascii=False),encoding='utf-8')
 def ts(t):
  ms=round(t*1000);return f'00:{ms//60000:02d}:{ms//1000%60:02d},{ms%1000:03d}'
 (ROOT/'captions.srt').write_text('\n\n'.join(f'{i+1}\n{ts(a)} --> {ts(b)}\n{s}' for i,(a,b,_,s) in enumerate(SCENES))+'\n',encoding='utf-8')
 (ROOT/'recording_script.txt').write_text(' '.join(s for _,_,_,s in SCENES)+'\n',encoding='utf-8')
 (ROOT/'README.md').write_text('''# PORTAL generic and brand-name drug spending video

Original indigo, periwinkle, and coral motion design. Thirteen scenes follow the actual supplied 55.327-second narration. All speech and pauses are preserved; no music, noise processing, normalization, time stretching, or new speech is added.

The primary sharing MP4 uses H.264/AAC-LC for browser compatibility. The original-audio master copies the original MP3 bitstream. The narration-original.mp3 file is byte-identical to the supplied file.

Paper: Cai CL, Kesselheim AS, Rome BN. Patient Out-of-Pocket Spending on Generic and Brand-Name Prescription Drugs. JAMA Network Open. 2026;9(9):e2633401. doi:10.1001/jamanetworkopen.2026.33401.
https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2853920

Graphics distinguish findings from policy options discussed in the paper. 51.9% and 15.8% are rounded population shares with at least one fill; these groups overlap. Generic and brand-name shares of aggregate patient spending are 55.2% and 44.8%. National totals are $16.8B and $13.7B in 2026 dollars. People, medicine packs, coins, and policy effects are schematic illustrations, not extra observations or estimated intervention effects.

Official PORTAL logos are reused from https://portalresearch.org/about-portal/. Authors are listed in published order. This is an original study summary, not an official journal production.
''',encoding='utf-8')

def previews():
 sheet=Image.new('RGB',(1920,1080),PAPER)
 for j,(a,b,_,_) in enumerate(SCENES):
  t=a+(b-a)*.65;im=frame(t);im.save(ROOT/f'preview_{j+1:02d}.jpg',quality=96)
  sheet.paste(im.resize((480,270),Image.Resampling.LANCZOS),((j%4)*480,(j//4)*270))
 d=ImageDraw.Draw(sheet);text(d,'PORTAL / A NEW MOTION STUDY',550,885,36,NAVY,'bold');text(d,'Original narration · all pauses preserved · 55 seconds',550,951,28,GRAY)
 sheet.save(ROOT/'storyboard.jpg',quality=96)

def render():
 master=ROOT/'PORTAL_Generic_Drug_Costs_Original_Audio.mp4'
 cmd=['ffmpeg','-y','-hide_banner','-loglevel','warning','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-i',str(REPO/'media'/'generic-spending-narration-original.mp3'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(master)]
 p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 try:
  for f in range(math.ceil(DURATION*FPS)):
   p.stdin.write(frame(f/FPS).tobytes())
   if f%300==0:print(f'Rendered {f/FPS:.0f}/{DURATION:.2f} seconds',flush=True)
 finally:p.stdin.close()
 if p.wait()!=0:raise RuntimeError('Video encoding failed')
 compatible=ROOT/'PORTAL_Generic_Drug_Costs.mp4'
 subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','warning','-i',str(master),'-map','0:v:0','-map','0:a:0','-c:v','copy','-c:a','aac','-profile:a','aac_low','-b:a','192k','-disposition:a:0','default','-movflags','+faststart',str(compatible)],check=True)
 print(compatible,flush=True)

if __name__=='__main__':
 docs();previews()
 if '--preview' not in sys.argv:render()
