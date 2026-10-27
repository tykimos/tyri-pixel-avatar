"""Build independent hand layers from the generated 4x3 source sheet."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json,base64,math
P=Path(__file__).parent
names=['wave','write','peace','shush','heart','finger_heart','thumbs_up','ok','point','clap','thanks','cheer']
labels=['손흔들기','글씨 쓰기','V','쉿','양손 하트','손가락 하트','최고','OK','가리키기','박수','감사','응원']
src=Image.open(P/'sources/hands_source.png').convert('RGBA')
(P/'hands').mkdir(exist_ok=True)
atlas=Image.new('RGBA',(128,384))
meta={'version':1,'atlas':'hands_atlas.png','frame_size':[32,32],'duration_ms':150,'canvas_size':[96,96],'face_offset':[16,8],'layer':'foreground','gestures':{},'directions':{}}
for i,n in enumerate(names):
 c,r=i%4,i//4
 tile=src.crop((c*src.width//4,r*src.height//3,(c+1)*src.width//4,(r+1)*src.height//3))
 a=tile.getchannel('A').point(lambda v:255 if v>=128 else 0);tile.putalpha(a)
 tile=tile.crop(tile.getbbox());tile.thumbnail((26,26),Image.Resampling.NEAREST)
 tile=tile.quantize(colors=12,method=Image.Quantize.FASTOCTREE,dither=Image.Dither.NONE).convert('RGBA')
 frames=[]
 for f in range(4):
  t=tile.copy();dx=dy=0
  if n=='wave':t=t.rotate([-15,0,15,0][f],resample=Image.Resampling.NEAREST,expand=True)
  if n=='write':dx=[-2,0,2,0][f];dy=[0,1,0,1][f]
  if n in ['heart','finger_heart','cheer','thumbs_up']:dy=[0,-1,-2,-1][f]
  if n in ['peace','ok','point','thanks']:dy=[0,0,-1,-1][f]
  if n=='clap':t=t.resize((tile.width-[0,3,5,3][f],tile.height),Image.Resampling.NEAREST)
  frame=Image.new('RGBA',(32,32));frame.alpha_composite(t,((32-t.width)//2+dx,(32-t.height)//2+dy))
  atlas.alpha_composite(frame,(f*32,i*32));frame.save(P/'hands'/f'{n}_{f}.png');frames.append([f*32,i*32,32,32])
 # Topmost visible pixel serves as fingertip anchor for shush.
 first=atlas.crop((0,i*32,32,(i+1)*32));bb=first.getbbox()
 top=[x for x in range(32) if first.getpixel((x,bb[1]))[3]]
 meta['gestures'][n]={'label_ko':labels[i],'frames':frames,'anchor':[sum(top)//len(top),bb[1]] if n=='shush' else [16,16],'loop':True}
m=json.load(open(P/'manifest.json'))
for d in m['directions']:
 mx,my=m['mouth_anchors'][d]
 meta['directions'][d]={'positions':{n:([mx+16,my+8-2] if n=='shush' else [48,72] if n in ['heart','write','clap','thanks'] else [76 if 'left' not in d else 20,54]) for n in names},'projection':'screen-facing hand; direction-specific placement'}
atlas.save(P/'hands_atlas.png');(P/'hands.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
face=Image.open(P/'atlas.png').convert('RGBA')
def compose(d,n,f):
 out=Image.new('RGBA',(96,96),(22,27,34,255));rect=m['frames'][d+'/e0_REST'];x,y,w,h=rect;out.alpha_composite(face.crop((x,y,x+w,y+h)),(16,8))
 g=meta['gestures'][n];x,y,w,h=g['frames'][f];ax,ay=g['anchor'];px,py=meta['directions'][d]['positions'][n];out.alpha_composite(atlas.crop((x,y,x+w,y+h)),(px-ax,py-ay));return out.convert('RGB')
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
contact=Image.new('RGB',(768,648),(13,17,23))
for i,n in enumerate(names):
 x=(i%4)*192;y=(i//4)*216;contact.paste(compose('front',n,0).resize((192,192),Image.Resampling.NEAREST),(x,y));ImageDraw.Draw(contact).text((x+12,y+194),n,font=font,fill='white')
contact.save(P/'previews/hands_contact.png')
frames=[]
for n in names:
 for f in range(8):
  sheet=Image.new('RGB',(576,600),(13,17,23))
  for j,d in enumerate(m['directions']):sheet.paste(compose(d,n,f%4).resize((192,192),Image.Resampling.NEAREST),((j%3)*192,(j//3)*192))
  ImageDraw.Draw(sheet).text((12,579),n+' | 9 directions',font=font,fill='white');frames.append(sheet)
frames[0].save(P/'previews/hands_9directions.gif',save_all=True,append_images=frames[1:],duration=150,loop=0,optimize=False)
html='''<!doctype html><meta charset="utf-8"><title>Tyri | Hands</title><style>body{background:#0d1117;color:#eee;font:16px system-ui;text-align:center}canvas{image-rendering:pixelated;width:384px;max-width:90vw}select,button{font:inherit;padding:8px;margin:8px}p{color:#aab}</style><h1>타이리 · Tyri — Hand gestures</h1><select id="direction"></select><select id="gesture"></select><button id="play">Pause</button><br><canvas id="c" width="96" height="96"></canvas><p>Independent foreground sprites · 12 gestures · 9 direction placements</p><p>Hands face the viewer; placement follows the head direction.</p><script>const M=MANIFEST,H=HANDMETA;const face=new Image(),hands=new Image();face.src='data:image/png;base64,FACE';hands.src='data:image/png;base64,HANDS';const ds=document.querySelector('#direction'),gs=document.querySelector('#gesture');for(const d of M.directions)ds.add(new Option(d,d));ds.value='front';for(const [k,v] of Object.entries(H.gestures))gs.add(new Option(v.label_ko+' / '+k,k));let playing=true,t=0,last=0;document.querySelector('#play').onclick=e=>{playing=!playing;e.target.textContent=playing?'Pause':'Play'};const ctx=document.querySelector('#c').getContext('2d');ctx.imageSmoothingEnabled=false;function draw(now){if(playing&&now-last>=150){t++;last=now}ctx.clearRect(0,0,96,96);if(face.complete&&hands.complete){let r=M.frames[ds.value+'/e0_REST'];ctx.drawImage(face,...r,16,8,64,64);let g=H.gestures[gs.value],p=H.directions[ds.value].positions[gs.value];ctx.drawImage(hands,...g.frames[t%4],p[0]-g.anchor[0],p[1]-g.anchor[1],32,32)}requestAnimationFrame(draw)}requestAnimationFrame(draw);</script>'''
for k,v in [('MANIFEST',json.dumps(m)),('HANDMETA',json.dumps(meta)),('FACE',base64.b64encode((P/'atlas.png').read_bytes()).decode()),('HANDS',base64.b64encode((P/'hands_atlas.png').read_bytes()).decode())]:html=html.replace(k,v)
(P/'hands_preview.html').write_text(html)
checks={'gestures':12,'frames':48,'directions':9,'compositions_checked':432,'alpha_binary':set(atlas.getchannel('A').getdata())<={0,255},'canvas_bounds_valid':True,'perspective_note':'Screen-facing hands, not 9 independently drawn hand perspectives.'}
for d in m['directions']:
 for n in names:
  g=meta['gestures'][n];px,py=meta['directions'][d]['positions'][n];ax,ay=g['anchor'];assert 0<=px-ax<=64 and 0<=py-ay<=64,(d,n)
  for f in range(4):assert compose(d,n,f).size==(96,96)
assert checks['alpha_binary'];(P/'hands_tests.json').write_text(json.dumps(checks,indent=2));print(checks)
