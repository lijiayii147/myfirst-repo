import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
os.environ['WENMAI_RUNTIME']=tempfile.mkdtemp(prefix='wenmai-test-')
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient
from wenmai.app import app,ROOT
from wenmai import engine

class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.client=TestClient(app)
    def demo(self):
        r=self.client.post('/api/demo');self.assertEqual(r.status_code,200);return r.json()
    def create(self,**changes):
        body={'asset_id':self.demo()['id'],'margin_mm':0,'min_width_mm':0};body.update(changes)
        return self.client.post('/api/designs',json=body)
    def test_full_demo_to_download(self):
        response=self.create(layout='repeat');self.assertEqual(response.status_code,200)
        result=response.json();self.assertFalse(result['report']['diffusion_model_used'])
        self.assertEqual(result['source_card']['review_status'],'pending_human_review')
        png=self.client.get(result['preview_url']);self.assertEqual(png.status_code,200)
        image=Image.open(io.BytesIO(png.content));self.assertEqual(image.size,(640,640))
        package=self.client.get(result['download_url']);self.assertEqual(package.status_code,200)
        with ZipFile(io.BytesIO(package.content)) as z:
            self.assertEqual(set(z.namelist()),{'design.png','design.svg','source_card.json','changes.txt'})
            card=json.loads(z.read('source_card.json'));self.assertEqual(card['parameters']['layout'],'repeat')
            self.assertIn(b'<svg',z.read('design.svg'))
    def test_traditional_locked(self):
        response=self.create(mode='traditional');self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['report']['source_unit_iou'],1)
        self.assertEqual(self.create(mode='traditional',layout='mirror').status_code,400)
        self.assertEqual(self.create(mode='traditional',repair=True).status_code,400)
    def test_rights_gate(self):
        for rights in ['unknown','display_only']:
            raw=engine.png_bytes(engine.demo_image())
            upload=self.client.post('/api/assets',files={'file':('demo.png',raw,'image/png')},data={'rights':rights})
            self.assertEqual(upload.status_code,200)
            r=self.client.post('/api/designs',json={'asset_id':upload.json()['id']})
            self.assertEqual(r.status_code,403)
    def test_invalid_and_oversized_uploads(self):
        self.assertEqual(self.client.post('/api/assets',files={'file':('bad.png',b'not png','image/png')}).status_code,400)
        self.assertEqual(self.client.post('/api/assets',files={'file':('huge.png',b'x'*(8*1024*1024+1),'image/png')}).status_code,413)
    def test_blank_rejected(self):
        b=io.BytesIO();Image.new('RGB',(100,100),'white').save(b,'PNG')
        self.assertEqual(self.client.post('/api/assets',files={'file':('blank.png',b.getvalue(),'image/png')}).status_code,400)
    def test_structure_edit_versioning(self):
        original=self.demo()
        response=self.client.post('/api/assets/'+original['id']+'/edit',json={'operations':[{'x':150,'y':150,'width':20,'height':20,'action':'erase'}]})
        self.assertEqual(response.status_code,200)
        edited=response.json();self.assertNotEqual(edited['id'],original['id'])
        self.assertEqual(edited['parent_asset_id'],original['id'])
        self.assertEqual(edited['origin'],'user_structure_edit')
        outside=self.client.post('/api/assets/'+original['id']+'/edit',json={'operations':[{'x':319,'y':319,'width':10,'height':10,'action':'erase'}]})
        self.assertEqual(outside.status_code,400)

    def test_color_injection_rejected(self):
        self.assertEqual(self.create(color='red\" onload=\"alert(1)').status_code,400)
    def test_invalid_identifiers(self):
        self.assertEqual(self.client.get('/api/assets/not-a-valid-id/preview').status_code,404)
        self.assertEqual(self.client.get('/api/designs/'+'0'*32+'/bundle').status_code,404)
    def test_evidence_binding(self):
        records=json.loads((ROOT/'data/catalog.json').read_text())
        r=self.create(evidence_ids=[records[0]['id']]);self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['source_card']['references'][0]['source_url'],records[0]['source_url'])
        self.assertEqual(self.create(evidence_ids=['fake']).status_code,400)
    def test_metadata_checksums(self):
        records=json.loads((ROOT/'data/catalog.json').read_text())
        self.assertGreater(len(records),0)
        for r in records:
            raw=(ROOT/'data'/r['raw_file']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),r['sha256'])
            self.assertIn('metadata only',r['license'])
    def test_thin_and_disconnected_detection(self):
        mask=np.zeros((100,100),dtype=bool);mask[10:30,10:30]=True;mask[70:90,70:90]=True;mask[5,40:60]=True
        result=engine.check(mask,100,3,0)
        types={x['type'] for x in result['issues']}
        self.assertIn('disconnected',types);self.assertIn('thin_feature_estimate',types)
        self.assertFalse(result['production_ready'])
    def test_safety_margin(self):
        mask=np.zeros((100,100),dtype=bool);mask[0:8,10:30]=True
        self.assertGreater(engine.check(mask,100,0,3)['margin_violation_pixels'],0)
    def test_invalid_dimensions(self):
        self.assertEqual(self.create(width_mm=0).status_code,422)
        self.assertEqual(self.create(width_mm=20,margin_mm=15).status_code,400)
    def test_search_and_health(self):
        self.assertEqual(self.client.get('/api/health').json()['status'],'ok')
        self.assertGreater(self.client.get('/api/knowledge?q=flower').json()['total_matches'],0)
        self.assertEqual(self.client.get('/').status_code,200)
    def test_transparency_background(self):
        img=Image.new('RGBA',(50,50),(0,0,0,0))
        from PIL import ImageDraw
        ImageDraw.Draw(img).rectangle((15,15,30,30),fill=(0,0,0,255))
        mask,_=engine.mask_image(img);self.assertFalse(mask[0,0]);self.assertTrue(mask[20,20])

if __name__=='__main__':unittest.main()
