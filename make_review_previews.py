"""Create silent, manually timed multilingual sprite review animations.
Requires Pillow. Pass a Korean/Japanese-capable font using --font.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageSequence
import argparse,json

root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--font',required=True)
args=parser.parse_args();out=root/'previews';out.mkdir(exist_ok=True)
font=ImageFont.truetype(args.font,20);small=ImageFont.truetype(args.font,13)
names=['up_left','up','up_right','left','front','right','down_left','down','down_right']
vis=['REST','MBP','AA','EH','EE','OH','OO','NEUTRAL','FV','TH','L','RSH']
atlas=Image.open(root/'atlas.png').convert('RGBA')
sprites={(r,e,m):atlas.crop(((e*12+m)*64,r*64,(e*12+m+1)*64,(r+1)*64)) for r in range(9) for e in range(3) for m in range(12)}
# A small exact overview, without smoothing: all 324 existing frames.
sheet=Image.new('RGB',(1152,340),'#20232a');d=ImageDraw.Draw(sheet)
d.text((12,4),'ALL 324 FRAMES | 9 directions x (3 eye states x 12 mouths)',font=small,fill='white')
for e in range(3):d.text((e*384+8,25),['OPEN','HALF','CLOSED'][e],font=small,fill='#b9cadb')
im=atlas.resize((1152,288),Image.Resampling.NEAREST);sheet.paste(im,(0,52),im);sheet.save(out/'full_sheet_small.png')
# Each language includes a lead-in, three phrases and a tail pause.
specs={
 'ko':('한국어','안녕, 난 타이리야, 반가워',[
  ('안녕','AA L EH NEUTRAL', [160,100,150,210]),
  ('난 타이리야','L AA L L AA EE L EE AA',[90,140,80,80,140,140,90,150,190]),
  ('반가워','MBP AA L AA OO NEUTRAL',[90,160,80,180,130,220])]),
 'en':('English',"Hi, I’m Tyri. Nice to meet you!",[
  ('Hi','AA EE',[200,180]),
  ('I’m Tyri','AA EE MBP L AA EE RSH EE',[130,120,100,80,170,140,110,170]),
  ('Nice to meet you','L AA EE RSH L OO MBP EE L RSH OO',[70,140,130,90,80,140,100,170,70,100,210])]),
 'ja':('日本語','こんにちは、タイリだよ。よろしくね。',[
  ('こんにちは','OH L L EE RSH EE AA',[140,80,90,150,100,100,190]),
  ('タイリだよ','L AA EE L EE L AA OH',[70,140,130,80,140,70,140,200]),
  ('よろしくね','OH L OH RSH EE OO L EH',[140,80,140,100,110,130,90,200])])}
report={'timing':'manual phonetic approximation; no audio or forced alignment','languages':{}}
for code,(language,text,phrases) in specs.items():
 cues=[('REST',450,'')]
 for caption,seq,durations in phrases:
  assert len(seq.split())==len(durations)
  cues.extend(zip(seq.split(),durations,[caption]*len(durations)))
  cues.append(('REST',260,caption))
 cues.append(('REST',700,''))
 rendered=[];durations=[];timeline=[];t=0
 for mouth,ms,caption in cues:
  # Split each cue into 10ms units only at blink boundaries to retain timing.
  remaining=ms
  while remaining:
   step=min(remaining,50);eye=2 if 1900<=t%3000<2000 else 1 if 1850<=t%3000<1900 or 2000<=t%3000<2050 else 0
   bg=Image.new('RGB',(480,610),'#20232a');draw=ImageDraw.Draw(bg)
   draw.text((16,10),language+' · 9 directions',font=font,fill='white')
   for r,n in enumerate(names):
    im=sprites[r,eye,vis.index(mouth)].resize((128,128),Image.Resampling.NEAREST)
    x=(r%3)*160+16;y=(r//3)*160+50;bg.paste(im,(x,y),im)
    draw.text((x,y+128),n,font=small,fill='#b9cadb')
   draw.text((16,535),text,font=font,fill='white')
   draw.text((16,565),caption+'   ['+mouth+']',font=small,fill='#f6c67b')
   draw.text((16,588),'SILENT / MANUAL TIMING / CENTERED UP V6',font=small,fill='#aab7c5')
   rendered.append(bg);durations.append(step);remaining-=step;t+=step
  timeline.append({'end_ms':t,'viseme':mouth,'phrase':caption})
 # Quantize all frames against one palette; never independent per-frame colors.
 palette=Image.new('RGB',(480,610*len(rendered)))
 for i,im in enumerate(rendered):palette.paste(im,(0,610*i))
 palette=palette.quantize(colors=128,method=Image.Quantize.MEDIANCUT)
 quant=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in rendered]
 quant[0].save(out/f'greeting_{code}_9directions.gif',save_all=True,append_images=quant[1:],duration=durations,loop=0,optimize=False)
 rendered[len(rendered)//2].save(out/f'greeting_{code}_still.png')
 gif=Image.open(out/f'greeting_{code}_9directions.gif');total=0
 for frame in ImageSequence.Iterator(gif):frame.load();total+=frame.info.get('duration',0)
 assert total==sum(durations),(total,sum(durations))
 report['languages'][code]={'caption':text,'duration_ms':total,'frames':gif.n_frames,'timeline':timeline}
(out/'timing_and_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:{'frames':v['frames'],'duration_ms':v['duration_ms']} for k,v in report['languages'].items()}))
