import io, unittest
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
from wenmai.app import app
class MiaoMVPTests(unittest.TestCase):
 def setUp(self): self.c=TestClient(app)
 def test_catalog_and_filters(self):
  r=self.c.get('/api/miao/catalog'); self.assertEqual(r.status_code,200); self.assertGreaterEqual(r.json()['total'],139)
  self.assertGreater(self.c.get('/api/miao/catalog?region=台江').json()['total'],0)
 def test_analyze_and_correction(self):
  b=io.BytesIO(); im=Image.new('RGB',(64,64),'white'); ImageDraw.Draw(im).rectangle((16,16,48,48),fill='black'); im.save(b,'PNG')
  r=self.c.post('/api/miao/analyze',files={'file':('蝴蝶纹.png',b.getvalue(),'image/png')}); self.assertEqual(r.status_code,200); self.assertEqual(r.json()['subject'],'蝴蝶纹'); self.assertEqual(len(r.json()['retrieval']),5)
  r=self.c.post('/api/miao/corrections',json={'image_id':'MIAO_0001','subject':'鸟纹','stitch':'平绣','reviewer':'test'}); self.assertEqual(r.status_code,200)
 def test_invalid_upload(self): self.assertEqual(self.c.post('/api/miao/analyze',files={'file':('x.txt',b'no','text/plain')}).status_code,400)
