from pathlib import Path
from PIL import Image
import unittest,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
class AssetTests(unittest.TestCase):
 def test_sources_and_rectangles(self):
  m=json.loads((ROOT/'data/catalog.json').read_text())
  self.assertEqual(len(m['regions']),149)
  for key,s in m['sources'].items():
   restored=Image.new('RGBA',(s['width'],s['height']))
   for part in s['parts']:
    p=ROOT/part['path'];self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),part['sha256'])
    im=Image.open(p);im.load();self.assertEqual(im.size,tuple(part['rect'][2:]));restored.paste(im,part['rect'][:2])
   self.assertEqual(hashlib.sha256(restored.tobytes()).hexdigest(),s['pixel_sha256'])
  for r in m['regions']:
   x,y,w,h=r['rect'];s=m['sources'][r['source']]
   self.assertGreaterEqual(min(w,h),224);self.assertGreaterEqual(min(x,y),0)
   self.assertLessEqual(x+w,s['width']);self.assertLessEqual(y+h,s['height'])
  for r in m['reactions']:
   self.assertEqual(len(r['frames']),len(r['durations']))
   for x,y,w,h in r['frames']:
    s=m['sources'][r['source']];self.assertLessEqual(x+w,s['width']);self.assertLessEqual(y+h,s['height'])
 def test_manifest_parity(self):
  s=(ROOT/'data/catalog.js').read_text();self.assertEqual(json.loads(s.removeprefix('window.TYRI_CATALOG = ').strip().removesuffix(';')),json.loads((ROOT/'data/catalog.json').read_text()))
if __name__=='__main__':unittest.main()
