"""Reconstruct original-size RGBA sheets from lossless PNG tiles."""
from pathlib import Path
from PIL import Image
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'data/catalog.json').read_text())
for key,s in m['sources'].items():
 im=Image.new('RGBA',(s['width'],s['height']))
 for part in s['parts']:
  f=ROOT/part['path'];assert hashlib.sha256(f.read_bytes()).hexdigest()==part['sha256'],f
  tile=Image.open(f);tile.load();im.paste(tile,part['rect'][:2])
 assert hashlib.sha256(im.tobytes()).hexdigest()==s['pixel_sha256'],key
 target=ROOT/s['path'];target.parent.mkdir(parents=True,exist_ok=True);im.save(target)
 print(key,im.size,'pixel-perfect')
