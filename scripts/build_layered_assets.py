"""Pack generated transparent artwork into independent, registered sprites.

This only slices atlas cells and writes placement metadata. It does not redraw,
recolor, or rescale the generated source pixels. The locked face is shared by
every animation, including 'none'.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import statistics

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CONFIG = {
    'wave': {'label':'손 흔들기','side':'right','surface':'palm','target_height':225,'anchor':[225,710]},
    'peace': {'label':'브이','side':'right','surface':'palm','target_height':220,'anchor':[280,720]},
    'shush': {'label':'쉿','side':'right','surface':'mixed','target_height':235,'tip_target':[512,594]},
    'heart': {'label':'하트','side':'both','surface':'mixed','target_width':300,'anchor':[512,845]},
    'write': {'label':'글쓰기','side':'both','surface':'mixed','target_width':350,'anchor':[512,930]},
    'think': {'label':'생각하기','side':'right','surface':'mixed','target_height':270,'tip_target':[308,438]},
}


def bounds(im, threshold=128):
    return im.getchannel('A').point(lambda a:255 if a>=threshold else 0).getbbox()


def point_near_edge(im, box, upper=False):
    left,top,right,bottom=box
    depth=max(3,round((bottom-top)*.035))
    y0,y1=(top,top+depth) if upper else (bottom-depth,bottom)
    alpha=im.getchannel('A')
    xs=[]
    for y in range(y0,y1):
        for x in range(left,right):
            if alpha.getpixel((x,y))>=128:xs.append(x)
    return [float(statistics.median(xs)) if xs else (left+right)/2, float(top if upper else bottom-1)]


def image_metadata(path,im,role):
    b=bounds(im)
    if b is None:raise ValueError('Empty sprite: '+str(path))
    return {'path':path.relative_to(ROOT).as_posix(),'role':role,
            'source_size':list(im.size),'content_bbox':[b[0],b[1],b[2]-b[0],b[3]-b[1]],
            'pixel_sha256':hashlib.sha256(im.tobytes()).hexdigest(),
            'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--generated-dir',type=Path)
    args=p.parse_args()
    face_path=ROOT/'assets/sprites/face/neutral.png'
    source_dir=ROOT/'assets/sprites/source'
    source_dir.mkdir(parents=True,exist_ok=True);face_path.parent.mkdir(parents=True,exist_ok=True)
    if args.generated_dir:
        shutil.copyfile(args.generated_dir/'canonical-face.png',face_path)
        for name in ('hands-primary.png','hands-secondary.png'):
            shutil.copyfile(args.generated_dir/name,source_dir/name)
    face=Image.open(face_path).convert('RGBA')
    if face.getchannel('A').getextrema()[0]!=0:raise ValueError('The face needs a genuinely transparent background')
    sprites={'face.neutral':image_metadata(face_path,face,'face')}
    b=bounds(face);head_scale=680/(b[2]-b[0])
    head_transform=[head_scale,0,0,head_scale,512-(b[0]+b[2])/2*head_scale,136-b[1]*head_scale]
    head={'sprite':'face.neutral','transform':head_transform,'z':100,'locked':True}
    animations={'none':{'label':'손 없음','frames':[{'duration_ms':3200,'instances':[]}],'loop':True}}
    raw_actions={}
    for sheet_name,actions in [('hands-primary.png',['wave','peace','shush']),('hands-secondary.png',['heart','write','think'])]:
        sheet=Image.open(source_dir/sheet_name).convert('RGBA')
        if sheet.getchannel('A').getextrema()[0]!=0:raise ValueError(sheet_name+' has no transparent pixels')
        for row,key in enumerate(actions):
            config=CONFIG[key];frames=[]
            for col in range(3):
                box=(round(col*sheet.width/3),round(row*sheet.height/3),round((col+1)*sheet.width/3),round((row+1)*sheet.height/3))
                im=sheet.crop(box)
                alternate_left = key=='peace' and col==2
                sprite_side = 'left' if alternate_left else config['side']
                number = 1 if alternate_left else col+1
                out=ROOT/'assets/sprites/hands'/sprite_side/f'{key}-{number:02d}.png'
                out.parent.mkdir(parents=True,exist_ok=True);im.save(out,compress_level=9)
                sprite_id=f'hand.{sprite_side}.{key}.{number:02d}'
                role='hand-prop' if key=='write' else 'hand'
                meta=image_metadata(out,im,role);bbox=bounds(im)
                pivot=point_near_edge(im,bbox)
                if config['side']=='both':pivot=[(bbox[0]+bbox[2])/2,bbox[3]-1]
                meta.update({'side':sprite_side,'surface':config['surface'],'pivot':pivot,
                             'atlas_source':'assets/sprites/source/'+sheet_name,'atlas_rect':[box[0],box[1],box[2]-box[0],box[3]-box[1]],
                             'components':(['right-hand-with-pencil','left-hand-with-notebook'] if key=='write' else ['left-hand','right-hand'] if key=='heart' else [sprite_side+'-hand'])})
                if alternate_left:
                    meta['usage']='Left-hand alternate pose; not used in the default right-hand peace animation.'
                sprites[sprite_id]=meta
                if not alternate_left:
                    frames.append({'id':sprite_id,'image':im,'bbox':bbox,'pivot':pivot})
            median_w=statistics.median(f['bbox'][2]-f['bbox'][0] for f in frames)
            median_h=statistics.median(f['bbox'][3]-f['bbox'][1] for f in frames)
            scale=config['target_width']/median_w if 'target_width' in config else config['target_height']/median_h
            if 'tip_target' in config:
                tip=point_near_edge(frames[0]['image'],frames[0]['bbox'],upper=True)
                anchor=[config['tip_target'][0]+(frames[0]['pivot'][0]-tip[0])*scale,
                        config['tip_target'][1]+(frames[0]['pivot'][1]-tip[1])*scale]
            else:anchor=config['anchor']
            instances=[]
            for f in frames:
                px,py=f['pivot']
                instances.append({'sprite':f['id'],'transform':[scale,0,0,scale,anchor[0]-px*scale,anchor[1]-py*scale],
                                  'z':200})
            order=([0,1,2,1] if len(frames)==3 else [0,1,0,1])*2+[0]
            cycle=[280,240,280,240] if key in ('write','think') else [260,200,260,200]
            times=cycle*2+[3200-2*sum(cycle)]
            animations[key]={'label':config['label'],'loop':True,'attachment':{'pivot':'wrist' if config['side']=='right' else 'pair-bottom-center',
                              'stage_anchor':anchor,'shared_scale':scale},
                              'frames':[{'duration_ms':ms,'instances':[instances[index]]} for index,ms in zip(order,times)]}
    manifest={'schema':'tyri.layered.v1','character':'타이리 (Tyri)',
              'credit':'Tyri Pixel Avatar by Taeyoung Kim (tykimos)',
              'canvas':{'width':1024,'height':1024,'alpha':'straight'},
              'coordinates':{'origin':'top-left','positive_x':'screen-right','positive_y':'screen-down',
                             'handedness':'character-anatomical','face_scale_policy':'locked; independent of hand visibility'},
              'head':head,'sprites':sprites,'animations':animations,
              'notes':['The same face PNG and transform are used in every state.',
                       'Heart uses a paired-hands sprite; writing groups both hands and their props.',
                       'The front-facing neutral head is the only face layer in this rig; legacy composed atlases are reference material.']}
    data=ROOT/'data';data.mkdir(exist_ok=True)
    payload=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
    (data/'layers.json').write_text(payload)
    (data/'layers.js').write_text('window.TYRI_LAYERS = '+payload.rstrip()+';\n')
    print(json.dumps({'sprites':len(sprites),'hand_frames':len(sprites)-1,'animations':len(animations),
                      'head_source':face.size,'head_visible_bbox':sprites['face.neutral']['content_bbox'],
                      'head_transform':head_transform},ensure_ascii=False))


if __name__=='__main__':main()
