"""Build independent emotion x viseme atlas. Requires Pillow and numpy.
Existing v6 direction assets are inputs and are never overwritten.
Left/right wink refer to the character's own side, not the viewer's.
"""
from pathlib import Path
import json,base64,argparse
import numpy as np
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent
meta=json.loads((P/'manifest.json').read_text());dirs=meta['directions'];vis=meta['visemes']
states=['neutral','wink_left','wink_right','happy','sad','side_eye','sulky','surprised','angry','sleepy','laughing','crying','sobbing','pleading','love','star_eyes','thinking','confused','embarrassed','smug','unimpressed','scared','dizzy','relieved']
labels=['기본','왼쪽 윙크','오른쪽 윙크','행복','슬픔','눈치주기','삐짐','놀람','화남','졸림','크게 웃음','눈물','펑펑 울음','애원','하트 눈','별 눈','생각 중','혼란','부끄러움','능청','무덤덤','겁먹음','어지러움','안도']
ink='#673b2c';white='#ffece0';iris='#74412a'
frames={};rects={};atlas=Image.new('RGBA',(12*64,9*len(states)*64));bases=Image.new('RGBA',(len(states)*64,9*64));checks=[]
for r,direction in enumerate(dirs):
 base=Image.open(P/direction/'base_e0.png').convert('RGBA');a=np.array(base);eye=meta['eye_centers'][direction];cx,cy=meta['mouth_anchors'][direction]
 for s,state in enumerate(states):
  im=base.copy();draw=ImageDraw.Draw(im)
  for i,(ex,ey) in enumerate(eye):
   close=(state=='wink_left' and i==1) or (state=='wink_right' and i==0)
   # Clear the WHOLE lens before drawing, including the old lashes. Skin
   # is sampled at the mouth-free cheek, never from a lens rim or iris.
   rad=7 if r in [1,4,7] else 6
   skin_samples=[]
   for yy in range(cy-2,cy+2):
    for xx in range(cx-2,cx+3):
     rr,gg,bb,aa=map(int,a[yy,xx])
     if aa and rr>gg>bb and gg>110:skin_samples.append((rr,gg,bb))
   tone=tuple(map(int,np.median(skin_samples,axis=0))) if skin_samples else (247,177,143)
   draw.rectangle((ex-rad+1,ey-5,ex+rad-1,ey+4),fill=tone)
   # Neutral eyes are also rebuilt from the clean bed, so all states share
   # identical per-direction alignment and no source iris can leak through.
   tile=Image.new('RGBA',(13,13));ed=ImageDraw.Draw(tile);ox=oy=6
   def line(points,fill=ink,width=2):ed.line([(ox+x,oy+y) for x,y in points],fill=fill,width=width)
   def dot(x,y,color):ed.point((ox+x,oy+y),fill=color)
   def open_eye(dx=0,dy=0,wide=False):
    ed.ellipse((2,2 if wide else 3,10,10 if wide else 9),fill=white)
    ed.ellipse((5+dx,3+dy,7+dx,8+dy),fill=iris);dot(dx,-2+dy,'#fff6dc')
    line([(-4,-1),(-3,-3),(2,-3),(4,-1)])
   if state=='relieved':line([(-4,-1),(-2,1),(2,1),(4,-1)])
   elif close or state=='happy':
    line([(-4,0),(-2,-2),(0,-3),(2,-2),(4,0)])
   elif state=='laughing':line([(-4,-3),(0,0),(-4,3)] if i==0 else [(4,-3),(0,0),(4,3)],width=2)
   elif state=='sleepy':line([(-4,0),(-2,1),(2,1),(4,0)]);line([(3,0),(4,2)])
   elif state=='love':
    ed.polygon([(2,3),(4,2),(6,4),(8,2),(10,3),(10,5),(6,9),(2,5)],fill='#d94b66')
   elif state=='star_eyes':
    ed.polygon([(6,1),(7,4),(11,4),(8,6),(9,10),(6,8),(3,10),(4,6),(1,4),(5,4)],fill='#cc8b27');dot(0,-1,'#fff0a5')
   elif state=='dizzy':
    line([(-3,-3),(3,3)],width=2);line([(3,-3),(-3,3)],width=2)
   elif state=='sobbing':
    line([(-4,-2),(-2,-3),(2,-3),(4,-2)],width=2)
    ed.rectangle((3,5,5,10),fill='#71b7de');ed.rectangle((7,5,9,10),fill='#71b7de')
   elif state=='crying':
    open_eye();line([(-4,-1),(0,-3),(4,-4)] if i==0 else [(-4,-4),(0,-3),(4,-1)])
    ed.rectangle((2 if i==0 else 8,7,4 if i==0 else 10,10),fill='#71b7de')
   elif state=='pleading':
    ed.ellipse((2,2,10,10),fill=iris);ed.rectangle((3,3,5,5),fill=white);ed.rectangle((7,7,8,8),fill=white)
   elif state in ['surprised','scared']:
    open_eye(wide=True)
    if state=='scared':line([(-4,-4),(0,-5),(4,-4)])
   elif state in ['side_eye','sulky','unimpressed','smug','thinking']:
    open_eye(dx=-2 if state in ['side_eye','thinking'] else 1 if state=='smug' else 0)
    ed.rectangle((2,2,10,5 if state!='unimpressed' else 6),fill=tone)
    line([(-4,-1),(4,-1)] if state!='smug' else [(-4,-2),(4,0)])
    if state=='thinking' and i==1:line([(-3,-4),(0,-5),(3,-4)])
   elif state=='angry':
    open_eye();ed.polygon([(2,2),(10,2),(10,6)] if i==0 else [(2,2),(10,2),(2,6)],fill=tone)
    line([(-4,-4),(4,0)] if i==0 else [(-4,0),(4,-4)],width=2)
   elif state=='sad':
    open_eye();ed.polygon([(2,2),(10,2),(2,6)] if i==0 else [(2,2),(10,2),(10,6)],fill=tone)
    line([(-4,0),(4,-4)] if i==0 else [(-4,-4),(4,0)])
   elif state=='confused':
    open_eye(dx=1 if i==0 else -1);line([(-3,-4),(3,-2)] if i==0 else [(-3,-2),(3,-4)])
   elif state=='embarrassed':open_eye(dy=1)
   else:open_eye()
   # Scale local eye artwork to each actual lens; distant eye is narrower.
   far=(i==0 and r in [0,3,6]) or (i==1 and r in [2,5,8])
   tw=9 if far else 11;th=8 if r in [1,6,7,8] else 9
   tile=tile.resize((tw,th),Image.Resampling.NEAREST)
   im.alpha_composite(tile,(ex-tw//2,ey-th//2))
   draw=ImageDraw.Draw(im)
   # Draw closed-eye curves directly on the final pixel grid: downsampling
   # thin diagonal lines can otherwise turn a smile into disconnected dots.
   if close or state=='happy':
    draw.rectangle((ex-4,ey-3,ex+4,ey+2),fill=tone)
    draw.line([(ex-3,ey),(ex-2,ey-1),(ex,ey-2),(ex+2,ey-1),(ex+3,ey)],fill=ink,width=1)
   if state=='embarrassed':
    for dx in [-2,0,2]:draw.line((ex+dx,ey+6,ex+dx-1,ey+7),fill='#d97873')
  # Restore exact lens rims / bridge: expressions cannot erase accessories.
  rim=Image.new('1',(64,64));rd=ImageDraw.Draw(rim);rad=7 if r in [1,4,7] else 6
  for ex,ey in eye:rd.ellipse((ex-rad,ey-5,ex+rad,ey+5),outline=1);rd.line((ex-2,ey+5,ex+2,ey+5),fill=1)
  (lx,ly),(rx,ry)=eye;rd.line((lx+rad,ly-1,rx-rad,ry-1),fill=1)
  im.paste(base,(0,0),rim);im.putalpha(base.getchannel('A'));bases.paste(im,(s*64,r*64))
  for m,v in enumerate(vis):
   final=im.copy()
   if m or state in ['neutral','wink_left','wink_right']:
    original=np.array(Image.open(P/direction/f'e0_{v}.png').convert('RGBA'));delta=np.any(original!=a,axis=2)
    arr=np.array(final);arr[delta]=original[delta];final=Image.fromarray(arr)
   else:
    mouth=Image.new('RGBA',(64,64));md=ImageDraw.Draw(mouth)
    if state in ['happy','relieved','love','star_eyes','embarrassed']:md.line([(cx-3,cy-1),(cx-2,cy+1),(cx+2,cy+1),(cx+3,cy-1)],fill=ink)
    elif state in ['sad','crying','pleading','scared']:md.line([(cx-3,cy+1),(cx-1,cy-1),(cx+1,cy-1),(cx+3,cy+1)],fill=ink)
    elif state=='sulky':md.line([(cx-2,cy),(cx+1,cy),(cx+2,cy-1)],fill=ink);md.line((cx-1,cy+2,cx+1,cy+2),fill='#ad6358')
    elif state in ['surprised','sobbing']:md.ellipse((cx-1,cy-2,cx+1,cy+2),fill=ink)
    elif state in ['side_eye','smug']:md.line([(cx-2,cy),(cx+1,cy),(cx+3,cy-1)],fill=ink)
    elif state=='angry':md.line([(cx-3,cy+1),(cx-1,cy),(cx+2,cy)],fill=ink)
    elif state=='laughing':md.polygon([(cx-3,cy-1),(cx+3,cy-1),(cx+2,cy+2),(cx-2,cy+2)],fill=ink)
    elif state in ['confused','dizzy']:md.line([(cx-3,cy),(cx-1,cy-1),(cx+1,cy+1),(cx+3,cy)],fill=ink)
    elif state=='thinking':md.line((cx,cy,cx+3,cy),fill=ink)
    else:md.line((cx-2,cy,cx+2,cy),fill=ink)
    ma=np.array(mouth);rgb=a[:,:,:3].astype(int);skin=(rgb[:,:,0]>rgb[:,:,1])&(rgb[:,:,1]>rgb[:,:,2])&(rgb[:,:,1]>105)&(a[:,:,3]>0)
    safe=skin.copy()
    for shift in [(1,0),(-1,0),(0,1),(0,-1)]:safe &= np.roll(skin,shift,(0,1))
    ma[:,:,3]=np.where(safe,ma[:,:,3],0);final=Image.alpha_composite(final,Image.fromarray(ma))
   fa=np.array(final);assert np.array_equal(fa[:,:,3],a[:,:,3])
   assert np.array_equal(fa[np.array(rim,dtype=bool)],a[np.array(rim,dtype=bool)])
   xy=[m*64,(r*len(states)+s)*64,64,64];atlas.paste(final,xy[:2]);rects[f'{direction}/{state}/{v}']=xy;frames[r,s,m]=final
  assert len({frames[r,s,m].tobytes() for m in range(1,12)})==11
 assert len({frames[r,s,0].tobytes() for s in range(len(states))})==len(states), (direction,[(states[i],states[j]) for i in range(len(states)) for j in range(i) if frames[r,i,0].tobytes()==frames[r,j,0].tobytes()])
atlas.save(P/'emotion_atlas.png');bases.save(P/'emotion_bases.png')
result={'version':2,'layout':'12 viseme columns; row = direction_index * emotion_count + emotion_index','frame_size':[64,64],'atlas':'emotion_atlas.png','directions':dirs,'emotions':states,'labels_ko':dict(zip(states,labels)),'visemes':vis,'wink_side':'character anatomical side; left appears on viewer right','frames':rects,'rest_behavior':'Emotion-specific resting mouth. Speech visemes keep the original v6 mouth while expression eyes stay active.'}
(P/'emotions.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
(P/'emotion_tests.json').write_text(json.dumps({'frames':len(frames),'alpha_preserved':True,'glasses_rims_and_bridge_exactly_preserved':True,'expression_count':len(states),'distinct_rest_expressions_per_direction':True,'lens_interiors_fully_cleared':True,'eleven_distinct_speech_visemes_per_expression':True,'actual_audio_sync_tested':False},indent=2))
parser=argparse.ArgumentParser();parser.add_argument('--font',help='Optional CJK font for Korean preview labels');args=parser.parse_args()
font=ImageFont.truetype(args.font,18) if args.font else ImageFont.load_default()
preview_labels=labels if args.font else states
contact=Image.new('RGB',(960,752),'#20232a');draw=ImageDraw.Draw(contact)
for s,label in enumerate(preview_labels):
 im=frames[4,s,0].resize((160,160),Image.Resampling.NEAREST);x=s%6*160;y=s//6*188;contact.paste(im,(x,y),im);draw.text((x+15,y+160),label,font=font,fill='white')
contact.save(P/'previews/emotions_contact.png')
def panel(s,m):
 out=Image.new('RGB',(384,418),'#20232a');dd=ImageDraw.Draw(out)
 for r in range(9):
  f=frames[r,s,m].resize((128,128),Image.Resampling.NEAREST);out.paste(f,(r%3*128,r//3*128),f)
 dd.text((10,388),preview_labels[s]+' / '+vis[m],font=font,fill='white');return out
panel(states.index('happy'),0).save(P/'previews/happy_9directions.png')
ims=[panel(s,m) for s in range(len(states)) for m in [0,0,2,4,6,1,0]];ims[0].save(P/'previews/emotions_9directions.gif',save_all=True,append_images=ims[1:],duration=250,loop=0)
ims=[panel(s,m) for s,m in [(0,0),(1,0),(1,2),(0,0),(2,0),(2,4),(0,0)]];ims[0].save(P/'previews/winks_9directions.gif',save_all=True,append_images=ims[1:],duration=300,loop=0)
html='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>타이리 표정</title><style>body{background:#20232a;color:#eee;font:16px sans-serif;text-align:center;padding:24px}canvas{width:256px;height:256px;image-rendering:pixelated}select,button{padding:10px;margin:6px}a{color:#f3c99b}</style><h1>타이리 · 기분과 윙크</h1><canvas width="64" height="64"></canvas><div><label>방향 <select id="direction"></select></label><label>표정 <select id="emotion"></select></label><label>입 <select id="mouth"></select></label></div><button id="talk">말하기 테스트</button><button id="cycle">표정 순환</button><p>윙크 좌우는 캐릭터 기준입니다. 무음 입 모양 테스트이며 실제 음성 인식은 포함하지 않습니다.</p><p>개인 및 비상업적 연구용 · <a href="LICENSE">라이선스</a> · <a href="preview.html">음성 타이밍 미리보기</a></p><script>
const dirs=DIRS,states=STATES,labels=LABELS,vis=VISEMES;const ds=document.querySelector('#direction'),es=document.querySelector('#emotion'),ms=document.querySelector('#mouth'),ctx=document.querySelector('canvas').getContext('2d'),atlas=new Image();dirs.forEach((v,i)=>ds.add(new Option(v,i)));labels.forEach((v,i)=>es.add(new Option(v,i)));vis.forEach((v,i)=>ms.add(new Option(v,i)));ds.value=4;let talk=false,cycle=false,loaded=false;document.querySelector('#talk').onclick=()=>talk=!talk;document.querySelector('#cycle').onclick=()=>cycle=!cycle;es.onchange=()=>cycle=false;ms.onchange=()=>talk=false;atlas.onload=()=>loaded=true;atlas.src='data:image/png;base64,DATA';function render(t){if(loaded){if(cycle)es.value=Math.floor(t/1800)%states.length;let m=talk?Math.floor(t/180)%12:+ms.value;ctx.clearRect(0,0,64,64);ctx.drawImage(atlas,m*64,(+ds.value*states.length+(+es.value))*64,64,64,0,0,64,64)}requestAnimationFrame(render)}requestAnimationFrame(render);
</script></html>'''
for key,value in [('DIRS',dirs),('STATES',states),('LABELS',labels),('VISEMES',vis)]:html=html.replace(key,json.dumps(value,ensure_ascii=False))
html=html.replace('DATA',base64.b64encode((P/'emotion_atlas.png').read_bytes()).decode());(P/'emotion_preview.html').write_text(html)
print('Generated',len(frames),'frames,',len(states),'expressions, 9 directions, 12 visemes')
