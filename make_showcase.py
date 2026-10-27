"""Curated README animations, drawn from shipped sprites. Requires Pillow."""
from pathlib import Path
import json,math
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent
M=json.loads((P/'manifest.json').read_text());E=json.loads((P/'emotions.json').read_text());A=Image.open(P/'atlas.png');B=Image.open(P/'emotion_atlas.png')
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def f(n):return ImageFont.truetype(font,n)
BG='#0d1117';CARD='#161b22';EDGE='#30363d';WHITE='#f0f6fc';MUTED='#8b949e';GOLD='#f1c27d';MINT='#79d5b3'
def sprite(direction='front',emotion='neutral',mouth='REST',eye=0):
 if emotion=='neutral':x,y,w,h=M['frames'][f'{direction}/e{eye}_{mouth}'];im=A
 else:x,y,w,h=E['frames'][f'{direction}/{emotion}/{mouth}'];im=B
 return im.crop((x,y,x+w,y+h)).resize((256,256),Image.Resampling.NEAREST)
def center(draw,text,y,font,color,width,x=0):
 box=draw.textbbox((0,0),text,font=font);draw.text((x+(width-box[2])/2,y),text,font=font,fill=color)
def card(out,x,y,w,h):ImageDraw.Draw(out).rounded_rectangle((x,y,x+w,y+h),radius=16,fill=CARD,outline=EDGE,width=1)
def paste(out,im,x,y):out.paste(im,(x,y),im)
def eye(t):return 1 if t%38 in [27,30] else 2 if t%38 in [28,29] else 0
mouths=['REST','MBP','AA','EH','EE','OH','OO','L','AA','REST','EE','MBP']
poses=['front','left','up_left','up','up_right','right','down_right','down','down_left','front']
reactions=[('happy','JOY'),('wink_left','WINK'),('love','LOVE'),('surprised','SURPRISE'),('side_eye','SIDE EYE'),('sleepy','REST')]
def save(name,frames):
 # A shared global palette prevents GIF palette flicker. No interpolation.
 sample=Image.new('RGB',(frames[0].width,frames[0].height*len(frames[::12])))
 for i,im in enumerate(frames[::12]):sample.paste(im,(0,i*im.height))
 pal=sample.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
 quant=[im.quantize(palette=pal,dither=Image.Dither.NONE) for im in frames]
 quant[0].save(P/'previews'/name,save_all=True,append_images=quant[1:],duration=100,loop=0,optimize=True,disposal=1)
 print(name,(P/'previews'/name).stat().st_size)
hero=[];emotion=[];direction=[]
for t in range(96):
 out=Image.new('RGB',(960,432),BG);d=ImageDraw.Draw(out)
 d.text((32,20),'SMALL PIXELS. BIG PERSONALITY.',font=f(20),fill=GOLD)
 d.text((32,52),'A face for your next conversation.',font=f(30),fill=WHITE)
 current=reactions[(t//16)%len(reactions)];pose=poses[(t//8)%len(poses)];mo=mouths[(t//2)%12] if t%32<25 else 'REST'
 for i,(top,bottom,im) in enumerate([('TALK','12 mouth shapes',sprite(mouth=mo,eye=eye(t))),('FEEL','24 expressions',sprite(emotion=current[0])),('LOOK','9 directions',sprite(direction=pose,eye=eye(t+8)))]):
  x=24+i*312;card(out,x,108,288,296);center(d,top,126,f(14),MINT,288,x);paste(out,im,x+16,142+(0 if i!=1 else [0,-4,0,4][(t//4)%4]));center(d,bottom,370,f(16),MUTED,288,x)
 hero.append(out)
 for collection,is_emotion in [(emotion,True),(direction,False)]:
  panel=Image.new('RGB',(456,352),BG);dd=ImageDraw.Draw(panel);card(panel,8,8,440,336)
  label=current[1] if is_emotion else pose.replace('_',' ').upper();center(dd,'EXPRESS YOURSELF' if is_emotion else 'EVERY ANGLE',24,f(16),MINT,456)
  if is_emotion:im=sprite(emotion=current[0],mouth=mo if t%16 in range(6,12) else 'REST')
  else:im=sprite(direction=pose,mouth=mo,eye=eye(t))
  paste(panel,im,100,54);center(dd,label,302,f(18),GOLD,456);collection.append(panel)
save('showcase_hero.gif',hero);save('showcase_emotions.gif',emotion);save('showcase_directions.gif',direction)
(P/'showcase_checks.json').write_text(json.dumps({n:{'size':list(Image.open(P/'previews'/n).size),'frames':Image.open(P/'previews'/n).n_frames,'silent':True,'scaling':'nearest-neighbor 4x'} for n in ['showcase_hero.gif','showcase_emotions.gif','showcase_directions.gif']},indent=2))
