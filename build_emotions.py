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
states=['neutral','wink_left','wink_right','happy','sad','side_eye','sulky','surprised','angry','sleepy']
labels=['기본','왼쪽 윙크','오른쪽 윙크','행복','슬픔','눈치주기','삐짐','놀람','화남','졸림']
ink='#673b2c';white='#ffece0';iris='#74412a'
frames={};rects={};atlas=Image.new('RGBA',(len(states)*12*64,9*64));bases=Image.new('RGBA',(len(states)*64,9*64));checks=[]
for r,direction in enumerate(dirs):
 base=Image.open(P/direction/'base_e0.png').convert('RGBA');a=np.array(base);eye=meta['eye_centers'][direction];cx,cy=meta['mouth_anchors'][direction]
 for s,state in enumerate(states):
  im=base.copy();draw=ImageDraw.Draw(im)
  for i,(ex,ey) in enumerate(eye):
   close=(state=='wink_left' and i==1) or (state=='wink_right' and i==0)
   edit=close or state not in ['neutral','wink_left','wink_right']
   if not edit:continue
   # Replace lens interiors only; exact original rims are restored below.
   tone=tuple(a[min(ey+4,63),ex,:3]);draw.rectangle((ex-3,ey-3,ex+3,ey+2),fill=tone)
   if close or state=='happy':
    draw.line([(ex-3,ey),(ex-1,ey-2),(ex+1,ey-2),(ex+3,ey)],fill=ink,width=1)
   elif state=='sleepy':
    draw.line([(ex-3,ey),(ex,ey+1),(ex+3,ey)],fill=ink,width=1)
   else:
    draw.ellipse((ex-3,ey-3,ex+3,ey+2),fill=white)
    offset=-2 if state=='side_eye' else 0
    draw.rectangle((ex+offset-1,ey-2,ex+offset+1,ey+1),fill=iris)
    draw.point((ex+offset,ey-2),fill='#fff6dc')
    if state=='surprised':draw.ellipse((ex-3,ey-4,ex+3,ey+3),outline=ink)
    if state in ['side_eye','sulky']:
     draw.rectangle((ex-3,ey-3,ex+3,ey-1),fill=tone);draw.line((ex-3,ey-1,ex+3,ey-1),fill=ink)
    if state=='angry':
     pts=[(ex-3,ey-3),(ex+3,ey),(ex+3,ey-3)] if i==0 else [(ex-3,ey),(ex+3,ey-3),(ex-3,ey-3)]
     draw.polygon(pts,fill=tone);draw.line(pts[:2],fill=ink,width=1)
    if state=='sad':
     pts=[(ex-3,ey-1),(ex+3,ey-3)] if i==0 else [(ex-3,ey-3),(ex+3,ey-1)]
     draw.line(pts,fill=ink,width=1);draw.point((ex+( -2 if i==0 else 2),ey+2),fill='#82b9cf')
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
    if state=='happy':md.line([(cx-3,cy-1),(cx-2,cy+1),(cx+2,cy+1),(cx+3,cy-1)],fill=ink)
    elif state=='sad':md.line([(cx-3,cy+1),(cx-1,cy-1),(cx+1,cy-1),(cx+3,cy+1)],fill=ink)
    elif state=='sulky':md.line([(cx-2,cy),(cx+1,cy),(cx+2,cy-1)],fill=ink);md.line((cx-1,cy+2,cx+1,cy+2),fill='#ad6358')
    elif state=='surprised':md.ellipse((cx-1,cy-2,cx+1,cy+2),fill=ink)
    elif state=='side_eye':md.line([(cx-2,cy),(cx+1,cy),(cx+3,cy-1)],fill=ink)
    elif state=='angry':md.line([(cx-3,cy+1),(cx-1,cy),(cx+2,cy)],fill=ink)
    else:md.line((cx-2,cy,cx+2,cy),fill=ink)
    ma=np.array(mouth);rgb=a[:,:,:3].astype(int);skin=(rgb[:,:,0]>rgb[:,:,1])&(rgb[:,:,1]>rgb[:,:,2])&(rgb[:,:,1]>105)&(a[:,:,3]>0)
    safe=skin.copy()
    for shift in [(1,0),(-1,0),(0,1),(0,-1)]:safe &= np.roll(skin,shift,(0,1))
    ma[:,:,3]=np.where(safe,ma[:,:,3],0);final=Image.alpha_composite(final,Image.fromarray(ma))
   fa=np.array(final);assert np.array_equal(fa[:,:,3],a[:,:,3])
   assert np.array_equal(fa[np.array(rim,dtype=bool)],a[np.array(rim,dtype=bool)])
   xy=[(s*12+m)*64,r*64,64,64];atlas.paste(final,xy[:2]);rects[f'{direction}/{state}/{v}']=xy;frames[r,s,m]=final
  assert len({frames[r,s,m].tobytes() for m in range(1,12)})==11
 assert len({frames[r,s,0].tobytes() for s in range(len(states))})==len(states)
atlas.save(P/'emotion_atlas.png');bases.save(P/'emotion_bases.png')
result={'version':1,'frame_size':[64,64],'atlas':'emotion_atlas.png','directions':dirs,'emotions':states,'labels_ko':dict(zip(states,labels)),'visemes':vis,'wink_side':'character anatomical side; left appears on viewer right','frames':rects,'rest_behavior':'Emotion-specific resting mouth. Speech visemes keep the original v6 mouth while expression eyes stay active.'}
(P/'emotions.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
(P/'emotion_tests.json').write_text(json.dumps({'frames':len(frames),'alpha_preserved':True,'glasses_rims_and_bridge_exactly_preserved':True,'ten_distinct_rest_expressions_per_direction':True,'eleven_distinct_speech_visemes_per_expression':True,'actual_audio_sync_tested':False},indent=2))
parser=argparse.ArgumentParser();parser.add_argument('--font',help='Optional CJK font for Korean preview labels');args=parser.parse_args()
font=ImageFont.truetype(args.font,18) if args.font else ImageFont.load_default()
preview_labels=labels if args.font else states
contact=Image.new('RGB',(800,376),'#20232a');draw=ImageDraw.Draw(contact)
for s,label in enumerate(preview_labels):
 im=frames[4,s,0].resize((160,160),Image.Resampling.NEAREST);x=s%5*160;y=s//5*188;contact.paste(im,(x,y),im);draw.text((x+15,y+160),label,font=font,fill='white')
contact.save(P/'previews/emotions_contact.png')
def panel(s,m):
 out=Image.new('RGB',(384,418),'#20232a');dd=ImageDraw.Draw(out)
 for r in range(9):
  f=frames[r,s,m].resize((128,128),Image.Resampling.NEAREST);out.paste(f,(r%3*128,r//3*128),f)
 dd.text((10,388),preview_labels[s]+' / '+vis[m],font=font,fill='white');return out
ims=[panel(s,m) for s in range(10) for m in [0,0,2,4,6,1,0]];ims[0].save(P/'previews/emotions_9directions.gif',save_all=True,append_images=ims[1:],duration=250,loop=0)
ims=[panel(s,m) for s,m in [(0,0),(1,0),(1,2),(0,0),(2,0),(2,4),(0,0)]];ims[0].save(P/'previews/winks_9directions.gif',save_all=True,append_images=ims[1:],duration=300,loop=0)
html='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>타이리 표정</title><style>body{background:#20232a;color:#eee;font:16px sans-serif;text-align:center;padding:24px}canvas{width:256px;height:256px;image-rendering:pixelated}select,button{padding:10px;margin:6px}a{color:#f3c99b}</style><h1>타이리 · 기분과 윙크</h1><canvas width="64" height="64"></canvas><div><label>방향 <select id="direction"></select></label><label>표정 <select id="emotion"></select></label><label>입 <select id="mouth"></select></label></div><button id="talk">말하기 테스트</button><button id="cycle">표정 순환</button><p>윙크 좌우는 캐릭터 기준입니다. 무음 입 모양 테스트이며 실제 음성 인식은 포함하지 않습니다.</p><p>개인 및 비상업적 연구용 · <a href="LICENSE">라이선스</a> · <a href="preview.html">음성 타이밍 미리보기</a></p><script>
const dirs=DIRS,states=STATES,labels=LABELS,vis=VISEMES;const ds=document.querySelector('#direction'),es=document.querySelector('#emotion'),ms=document.querySelector('#mouth'),ctx=document.querySelector('canvas').getContext('2d'),atlas=new Image();dirs.forEach((v,i)=>ds.add(new Option(v,i)));labels.forEach((v,i)=>es.add(new Option(v,i)));vis.forEach((v,i)=>ms.add(new Option(v,i)));ds.value=4;let talk=false,cycle=false,loaded=false;document.querySelector('#talk').onclick=()=>talk=!talk;document.querySelector('#cycle').onclick=()=>cycle=!cycle;es.onchange=()=>cycle=false;ms.onchange=()=>talk=false;atlas.onload=()=>loaded=true;atlas.src='data:image/png;base64,DATA';function render(t){if(loaded){if(cycle)es.value=Math.floor(t/1800)%states.length;let m=talk?Math.floor(t/180)%12:+ms.value;ctx.clearRect(0,0,64,64);ctx.drawImage(atlas,(+es.value*12+m)*64,+ds.value*64,64,64,0,0,64,64)}requestAnimationFrame(render)}requestAnimationFrame(render);
</script></html>'''
for key,value in [('DIRS',dirs),('STATES',states),('LABELS',labels),('VISEMES',vis)]:html=html.replace(key,json.dumps(value,ensure_ascii=False))
html=html.replace('DATA',base64.b64encode((P/'emotion_atlas.png').read_bytes()).decode());(P/'emotion_preview.html').write_text(html)
print('Generated',len(frames),'frames, 10 expressions, 9 directions, 12 visemes')
