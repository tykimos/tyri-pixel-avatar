"""Build repaired sprite atlas from generated mouth-free heads.
Run from any directory; requires Pillow and numpy. Review anchors visually.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np,json,base64,re
P=Path(__file__).resolve().parent
src=Image.open(P/'sources/glasses_head_sheet.png').convert('RGBA');a=np.array(src)
mask=~((a[:,:,1]>130)&(a[:,:,1]>a[:,:,0]*1.35)&(a[:,:,1]>a[:,:,2]*1.35));a[:,:,3]=mask*255
def runs(v):
 ids=np.where(v)[0];return [(int(g[0]),int(g[-1])+1) for g in np.split(ids,np.where(np.diff(ids)>1)[0]+1) if len(g)>8]
raw=[]
for y0,y1 in runs(mask.sum(1)>20):
 cols=runs(mask[y0:y1].sum(0)>5);assert len(cols)==3
 x0,x1=cols[0];im=Image.fromarray(a[y0:y1,x0:x1]);im.thumbnail((56,56),Image.Resampling.NEAREST)
 out=Image.new('RGBA',(64,64));out.paste(im,((64-im.width)//2,(64-im.height)//2));raw.append(out)
assert len(raw)==9
# Match left and right pitch precisely with explicit mirrored counterparts.
for right,left in [(2,0),(5,3),(8,6)]:raw[right]=raw[left].transpose(Image.Transpose.FLIP_LEFT_RIGHT)
# Face landmarks are defined on the final 64px images, not the source canvas.
anchors=[(25,43),(31,42),(38,43),(22,43),(31,43),(41,43),(23,43),(31,45),(40,43)]
eyes=[[(18,34),(32,36)],[(23,33),(39,33)],[(31,36),(45,34)],[(15,34),(29,36)],[(22,35),(40,35)],[(34,36),(48,34)],[(16,35),(30,38)],[(22,37),(40,37)],[(33,38),(47,35)]]
meta=json.loads((P/'manifest.json').read_text());names=meta['directions'];vis=meta['visemes']
mouths=[Image.open(P/'mouths'/f'{v}.png').convert('RGBA') for v in vis]
allrgb=np.concatenate([np.array(im)[:,:,:3][np.array(im)[:,:,3]>0] for im in raw])
q=Image.fromarray(allrgb.reshape(1,-1,3)).quantize(colors=32,method=Image.Quantize.MEDIANCUT);pal=q.getpalette()
def quant(im):
 alpha=im.getchannel('A');out=im.convert('RGB').quantize(palette=q,dither=Image.Dither.NONE).convert('RGBA');out.putalpha(alpha);return out
raw=[quant(im) for im in raw]
# Correct UP yaw using a dedicated frontal, upward-pitched source. Preserve
# the shared original quantizer so all other directional pixels stay unchanged.
up=Image.open(P/'sources/up_head.png').convert('RGBA')
up.putalpha(up.getchannel('A').point(lambda v:255 if v>=128 else 0))
up=up.crop(up.getbbox());up.thumbnail((56,56),Image.Resampling.NEAREST)
canvas=Image.new('RGBA',(64,64));canvas.paste(up,((64-up.width)//2,(64-up.height)//2))
raw[1]=quant(canvas)
atlas=Image.new('RGBA',(2304,576));frames={};checks=[]
for r,base in enumerate(raw):
 cx,cy=anchors[r];basearr=np.array(base)
 # Restrict every mouth pixel to actual skin, with margin from the silhouette.
 rgb=basearr[:,:,:3].astype(int);skin=(rgb[:,:,0]>rgb[:,:,1])&(rgb[:,:,1]>rgb[:,:,2])&((rgb[:,:,0]-rgb[:,:,1])<100)&((rgb[:,:,1]-rgb[:,:,2])<65)&(rgb[:,:,1]>105)&(basearr[:,:,3]>0)
 safe=skin.copy()
 for dy,dx in [(1,0),(-1,0),(0,1),(0,-1)]:safe &= np.roll(skin,(dy,dx),(0,1))
 for e in range(3):
  clean=base.copy()
  if e:
   draw=ImageDraw.Draw(clean)
   # Sample actual cheek skin, not the lower rim (which may be dark brown).
   samples=basearr[cy-2:cy+2,cx-2:cx+3,:3].reshape(-1,3).astype(int)
   good=samples[(samples[:,0]>samples[:,1])&(samples[:,1]>samples[:,2])&(samples[:,1]>110)]
   tone=tuple(map(int,np.median(good,axis=0))) if len(good) else (247,177,143)
   rad=7 if r in [1,4,7] else 6
   for ex,ey in eyes[r]:
    # Clear the entire iris/lash bed before painting the final native pixels.
    draw.rectangle((ex-rad+1,ey-5,ex+rad-1,ey+4),fill=tone)
    if e==1:
     draw.line((ex-3,ey,ex+3,ey),fill='#673b2c',width=1)
     draw.rectangle((ex,ey+1,ex+1,ey+2),fill='#673b2c')
    else:
     draw.line([(ex-3,ey),(ex-1,ey+1),(ex+1,ey+1),(ex+3,ey)],fill='#673b2c',width=1)
  # Reinforce generated gold rims on the final pixel grid so downsampling
  # cannot erase them. Bridge and lens centres also define the mouth axis.
  draw=ImageDraw.Draw(clean)
  for ex,ey in eyes[r]:
   rx=7 if r in [1,4,7] else 6
   draw.ellipse((ex-rx,ey-5,ex+rx,ey+5),outline='#956327',width=1)
   draw.line((ex-2,ey+5,ex+2,ey+5),fill='#e6b65a',width=1)
  (lx,ly),(rx,ry)=eyes[r];rad=7 if r in [1,4,7] else 6
  draw.line((lx+rad,ly-1,rx-rad,ry-1),fill='#956327',width=1)
  clean.save(P/names[r]/f'base_e{e}.png')
  for m,mouth in enumerate(mouths):
   mo=mouth.copy();w=mo.width;h=mo.height
   if r not in [1,4,7]:w=max(3,w-1)
   if r>=6:w=max(3,w-1);h=max(1,h-1)
   mo=mo.resize((w,h),Image.Resampling.NEAREST)
   # Optical centre is based on the visible alpha, not the component canvas.
   mo=mo.crop(mo.getbbox());x=cx-mo.width//2;y=cy-mo.height//2
   layer=Image.new('RGBA',(64,64));layer.paste(mo,(x,y));la=np.array(layer)
   before=int((la[:,:,3]>0).sum());la[:,:,3]=np.where(safe,la[:,:,3],0)
   assert (la[:,:,3]>0).any();im=Image.alpha_composite(clean,Image.fromarray(la))
   key=f'{names[r]}/e{e}_{vis[m]}';im.save(P/(key+'.png'));atlas.paste(im,((e*12+m)*64,r*64));frames[r,e,m]=im
   assert np.array_equal(np.array(im)[:,:,3],basearr[:,:,3])
   checks.append({'frame':key,'mouth_pixels':int((la[:,:,3]>0).sum()),'clipped_pixels':before-int((la[:,:,3]>0).sum())})
atlas.save(P/'atlas.png');meta['mouth_anchors']=dict(zip(names,anchors));meta['revision']='clean-blinks-v7';meta['direction_mouth_projection']='horizontal compression; down-view mouths also reduced vertically';meta['eye_centers']=dict(zip(names,eyes));(P/'manifest.json').write_text(json.dumps(meta,indent=2))
rgba=np.array(atlas);colors=sorted({tuple(p[:3]) for p in rgba.reshape(-1,4) if p[3]});(P/'palette.json').write_text(json.dumps({'colors':['#%02x%02x%02x'%c for c in colors],'transparency':'alpha=0'},indent=2))
html=(P/'preview.html').read_text();html=re.sub(r'data:image/png;base64,[A-Za-z0-9+/=]+','data:image/png;base64,'+base64.b64encode((P/'atlas.png').read_bytes()).decode(),html);(P/'preview.html').write_text(html)
def gif(name,seq):
 ims=[]
 for r,e,m in seq:
  im=frames[r,e,m].resize((256,256),Image.Resampling.NEAREST);bg=Image.new('RGB',(256,256),'#20232a');bg.paste(im,(0,0),im);ims.append(bg)
 ims[0].save(P/name,save_all=True,append_images=ims[1:],duration=220,loop=0)
gif('mouths_12.gif',[(4,0,m) for m in range(12)]);gif('blink.gif',[(4,e,0) for e in [0,1,2,1,0]]);gif('directions.gif',[(r,0,3) for r in range(9)]);gif('combined.gif',[(r,(m//4)%3,m) for r in range(9) for m in range(12)])
contact=Image.new('RGB',(1024,834),'#20232a');d=ImageDraw.Draw(contact)
for m,v in enumerate(vis):
 im=frames[4,0,m].resize((256,256),Image.Resampling.NEAREST);x=m%4*256;y=m//4*278;contact.paste(im,(x,y),im);d.text((x+100,y+256),v,fill='white')
contact.save(P/'viseme_contact.png')
diagnostic=Image.new('RGB',(576,576),'#20232a')
for r in range(9):
 im=frames[r,0,2].resize((192,192),Image.Resampling.NEAREST);diagnostic.paste(im,((r%3)*192,(r//3)*192),im)
diagnostic.save(P/'previews/repaired_9directions.png')
duplicates=[]
for r in range(9):
 for e in range(3):
  if len({frames[r,e,m].tobytes() for m in range(12)})!=12:duplicates.append((r,e))
assert not duplicates,duplicates
closed_counts=[]
for r,name in enumerate(names):
 closed=np.array(Image.open(P/name/'base_e2.png'))
 for ex,ey in eyes[r]:
  region=closed[ey-3:ey+3,ex-3:ex+4,:3]
  dark=(region[:,:,0]<150)&(region[:,:,1]<115)&(region[:,:,2]<100)
  count=int(dark.sum());assert count<=9,(name,ex,ey,count);closed_counts.append(count)
tests={'closed_eye_dark_pixels_max':max(closed_counts),'closed_eye_dark_pixels_limit':9,'closed_eye_lenses_checked':len(closed_counts),'frames':324,'all_12_visemes_distinct_per_direction_and_eye':True,'mouth_changes_preserve_alpha':True,'mouth_pixels_restricted_to_interior_skin':True,'max_clipped_pixels':max(c['clipped_pixels'] for c in checks),'real_speech_sync_tested':False}
(P/'test_results.json').write_text(json.dumps(tests,indent=2));(P/'previews/mouth_boundary_checks.json').write_text(json.dumps(checks,indent=2));print(tests)
