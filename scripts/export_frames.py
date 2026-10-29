"""Export exact native-resolution atlas cells; no resampling or redraw."""
from pathlib import Path
from PIL import Image
import argparse,json
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'exports');args=p.parse_args()
m=json.loads((ROOT/'data/catalog.json').read_text());images={}
for k,s in m['sources'].items():
 im=Image.new('RGBA',(s['width'],s['height']))
 for part in s['parts']:im.paste(Image.open(ROOT/part['path']),part['rect'][:2])
 images[k]=im
args.output.mkdir(parents=True,exist_ok=True)
for r in m['regions']:
 x,y,w,h=r['rect'];images[r['source']].crop((x,y,x+w,y+h)).save(args.output/(r['id']+'.png'))
print(f"Exported {len(m['regions'])} native-resolution PNGs to {args.output}")
