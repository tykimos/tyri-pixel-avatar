"""Tyri hands v2: small face-adjacent layers with anatomical hand/surface keys."""
from PIL import Image,ImageDraw,ImageFont,ImageOps
from pathlib import Path
import json,base64
P=Path(__file__).parent
names=['wave','write','peace','shush','heart','finger_heart','thumbs_up','ok','point','clap','thanks','cheer']
labels=['손흔들기','글씨 쓰기','V','쉿','양손 하트','손가락 하트','최고','OK','가리키기','박수','감사','응원']
singles=['wave','peace','shush','finger_heart','thumbs_up','ok','point','cheer']
paired=['heart','clap','thanks']
m=json.loads((P/'manifest.json').read_text());face=Image.open(P/'atlas.png').convert('RGBA')
old=Image.open(P/'sources/hands_source.png').convert('RGBA');new=Image.open(P/'sources/hands_orientation_source.png').convert('RGBA')
# One shared palette taken from Tyri skin, plus prop colors. All frames share it.
palette=[(74,37,28),(140,69,45),(196,104,66),(237,151,111),(255,191,153),(255,218,178),(255,236,202),(230,173,56),(125,92,35),(247,237,215),(218,83,92),(78,61,49)]
def extract(src,index,cols,rows,size):
 x=index%cols;y=index//cols;t=src.crop((x*src.width//cols,y*src.height//rows,(x+1)*src.width//cols,(y+1)*src.height//rows));t.putalpha(t.getchannel('A').point(lambda v:255 if v>=160 else 0));t=t.crop(t.getbbox());t.thumbnail(size,Image.Resampling.NEAREST)
 # Explicit nearest palette mapping, leaving transparent pixels untouched.
 pix=t.load()
 for yy in range(t.height):
  for xx in range(t.width):
   r,g,b,a=pix[xx,yy]
   if a:pix[xx,yy]=(*min(palette,key=lambda c:(c[0]-r)**2+(c[1]-g)**2+(c[2]-b)**2),255)
 return t
meta={'version':2,'atlas':'hands_atlas.png','frame_size':[24,24],'duration_ms':150,'canvas_size':[80,80],'face_offset':[8,4],'handedness':'anatomical: character right appears viewer-left in front view','surface':'palm = palm visible to viewer; back = back of hand visible to viewer','palette':palette,'gestures':{},'directions':{}}
variants=[]
for i,n in enumerate(names):
 g={'label_ko':labels[i],'variants':{},'default':'pair' if n in paired else 'right_prop' if n=='write' else 'right_palm'}
 if n in singles:
  for hand in ['right','left']:
   for surface in ['palm','back']:
    t=extract(new,singles.index(n)*2+(['palm','back'].index(surface)),4,4,(12,16))
    if hand=='left':t=ImageOps.mirror(t)
    variants.append((n,hand+'_'+surface,t));g['variants'][hand+'_'+surface]={'hand':hand,'surface':surface}
 elif n=='write':
  t=extract(old,i,4,3,(17,14))
  for hand in ['right','left']:
   variants.append((n,hand+'_prop',t if hand=='right' else ImageOps.mirror(t)));g['variants'][hand+'_prop']={'hand':hand,'surface':'prop grip'}
 else:
  t=extract(old,i,4,3,(19,14));variants.append((n,'pair',t));g['variants']['pair']={'hand':'both','surface':'paired gesture'}
 meta['gestures'][n]=g
atlas=Image.new('RGBA',(96,24*len(variants)));out=P/'hands_v2';out.mkdir(exist_ok=True)
for row,(n,key,t) in enumerate(variants):
 frames=[]
 for f in range(4):
  tile=t.copy();dx=dy=0
  if n=='wave':tile=tile.rotate([-10,0,10,0][f],resample=Image.Resampling.NEAREST,expand=True)
  elif n=='write':dx=[0,1,0,-1][f]
  elif n=='clap':tile=tile.resize((tile.width-[0,1,2,1][f],tile.height),Image.Resampling.NEAREST)
  elif n!='shush':dy=[0,0,-1,0][f]
  fr=Image.new('RGBA',(24,24));fr.alpha_composite(tile,((24-tile.width)//2+dx,(24-tile.height)//2+dy));atlas.alpha_composite(fr,(f*24,row*24));fr.save(out/f'{n}_{key}_{f}.png');frames.append([f*24,row*24,24,24])
 g=meta['gestures'][n]['variants'][key];g['frames']=frames;g['anchor']=[12,12]
 if n=='shush':
  bb=fr.getbbox();top=[x for x in range(24) if fr.getpixel((x,bb[1]))[3]];g['anchor']=[sum(top)//len(top),bb[1]]
for d in m['directions']:
 mx,my=m['mouth_anchors'][d];placements={}
 for n,g in meta['gestures'].items():
  placements[n]={}
  for key,v in g['variants'].items():
   side=-1 if v['hand']=='right' else 1
   if n=='shush':p=[mx+8,my+4-1]
   elif v['hand']=='both' or n=='write':p=[mx+8,my+4+8]
   else:p=[mx+8+side*13,my+4+1]
   placements[n][key]={'position':p,'layer':'foreground'}
 meta['directions'][d]={'placements':placements,'default_hand':'left' if 'right' in d else 'right'}
atlas.save(P/'hands_atlas.png');(P/'hands.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
def compose(d,n,f,key=None):
 if key is None:key=meta['gestures'][n]['default']
 im=Image.new('RGBA',(80,80),(22,27,34,255));x,y,w,h=m['frames'][d+'/e0_REST'];im.alpha_composite(face.crop((x,y,x+w,y+h)),(8,4));v=meta['gestures'][n]['variants'][key];x,y,w,h=v['frames'][f];px,py=meta['directions'][d]['placements'][n][key]['position'];ax,ay=v['anchor'];im.alpha_composite(atlas.crop((x,y,x+w,y+h)),(px-ax,py-ay));return im.convert('RGB')
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
contact=Image.new('RGB',(640,552),(13,17,23))
for i,n in enumerate(names):
 x=(i%4)*160;y=(i//4)*184;contact.paste(compose('front',n,0).resize((160,160),Image.Resampling.NEAREST),(x,y));ImageDraw.Draw(contact).text((x+8,y+163),n,font=font,fill='white')
contact.save(P/'previews/hands_contact.png')
comparison=Image.new('RGB',(640,552),(13,17,23))
for j,n in enumerate(['wave','peace','shush']):
 for i,key in enumerate(['right_palm','right_back','left_palm','left_back']):
  x=i*160;y=j*184;comparison.paste(compose('front',n,0,key).resize((160,160),Image.Resampling.NEAREST),(x,y));ImageDraw.Draw(comparison).text((x+4,y+163),key,font=font,fill='white')
comparison.save(P/'previews/hands_orientation.png')
frames=[]
for n in names:
 for f in range(8):
  sheet=Image.new('RGB',(480,504),(13,17,23))
  for j,d in enumerate(m['directions']):sheet.paste(compose(d,n,f%4).resize((160,160),Image.Resampling.NEAREST),((j%3)*160,(j//3)*160))
  ImageDraw.Draw(sheet).text((12,483),n+' | smaller, face-adjacent hands',font=font,fill='white');frames.append(sheet)
frames[0].save(P/'previews/hands_9directions.gif',save_all=True,append_images=frames[1:],duration=150,loop=0,optimize=False)
html='''<!doctype html><meta charset="utf-8"><title>Tyri | Hands v2</title><style>body{background:#0d1117;color:#eee;font:16px system-ui;text-align:center}canvas{image-rendering:pixelated;width:400px;max-width:90vw}select,button{font:inherit;padding:8px;margin:6px}p{color:#aab}</style><h1>타이리 · Tyri — Hands v2</h1><select id="direction" aria-label="방향"></select><select id="gesture" aria-label="동작"></select><select id="variant" aria-label="손과 면"></select><button id="play">Pause</button><br><canvas id="c" width="80" height="80"></canvas><p>왼손·오른손 = 타이리 기준 / 손바닥·손등 = 화면에 보이는 면</p><script>const M=MANIFEST,H=HANDMETA;const face=new Image(),hands=new Image();face.src='data:image/png;base64,FACE';hands.src='data:image/png;base64,HANDS';const ds=document.querySelector('#direction'),gs=document.querySelector('#gesture'),vs=document.querySelector('#variant');for(const d of M.directions)ds.add(new Option(d,d));ds.value='front';for(const [k,v] of Object.entries(H.gestures))gs.add(new Option(v.label_ko+' / '+k,k));function variants(){vs.innerHTML='';for(const [k,v] of Object.entries(H.gestures[gs.value].variants))vs.add(new Option(k.replace('right','오른손').replace('left','왼손').replace('palm','손바닥').replace('back','손등').replace('pair','양손').replace('prop','도구'),k))}gs.onchange=variants;variants();let playing=true,t=0,last=0;document.querySelector('#play').onclick=e=>{playing=!playing;e.target.textContent=playing?'Pause':'Play'};const ctx=document.querySelector('#c').getContext('2d');ctx.imageSmoothingEnabled=false;function draw(now){if(playing&&now-last>=150){t++;last=now}ctx.clearRect(0,0,80,80);if(face.complete&&face.naturalWidth&&hands.complete&&hands.naturalWidth){let r=M.frames[ds.value+'/e0_REST'];ctx.drawImage(face,...r,8,4,64,64);let v=H.gestures[gs.value].variants[vs.value],p=H.directions[ds.value].placements[gs.value][vs.value].position;ctx.drawImage(hands,...v.frames[t%4],p[0]-v.anchor[0],p[1]-v.anchor[1],24,24)}requestAnimationFrame(draw)}requestAnimationFrame(draw);</script>'''
for k,v in [('MANIFEST',json.dumps(m)),('HANDMETA',json.dumps(meta)),('FACE',base64.b64encode((P/'atlas.png').read_bytes()).decode()),('HANDS',base64.b64encode((P/'hands_atlas.png').read_bytes()).decode())]:html=html.replace(k,v)
(P/'hands_preview.html').write_text(html)
count=0
for d in m['directions']:
 for n,g in meta['gestures'].items():
  for key,v in g['variants'].items():
   px,py=meta['directions'][d]['placements'][n][key]['position'];ax,ay=v['anchor'];assert 0<=px-ax<=56 and 0<=py-ay<=56,(d,n,key)
   for f in range(4):assert compose(d,n,f,key).size==(80,80);count+=1
checks={'version':2,'gestures':12,'variants':len(variants),'frame_slots':len(variants)*4,'compositions_checked':count,'alpha_binary':set(atlas.getchannel('A').getdata())<={0,255},'shared_palette_colors':len(palette),'canvas_bounds_valid':True,'single_hand_max_size':[12,16],'paired_max_size':[19,14],'explicit_anatomical_hand_keys':True,'palm_and_back_separate_source_drawings':True,'projection_note':'Two surface views; no independent 3D rotation for each head direction.'}
assert checks['alpha_binary'];(P/'hands_tests.json').write_text(json.dumps(checks,indent=2));print(checks)
