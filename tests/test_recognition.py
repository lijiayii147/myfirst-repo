import io
import json
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
import numpy as np
from wenmai import recognition,engine,samples
from wenmai.app import app

class RecognitionTests(unittest.TestCase):
    def setUp(self):self.client=TestClient(app);self.ids=[]
    def tearDown(self):
        for eid in self.ids:self.client.delete('/api/recognition/examples/'+eid)
    def upload(self,label,seed,rights='derivatives_allowed'):
        r=self.client.post('/api/assets',files={'file':('motif.png',engine.png_bytes(samples.sample(label,seed)),'image/png')},data={'rights':rights,'source':'Synthetic test fixture, not heritage artwork'})
        self.assertEqual(r.status_code,200);return r.json()['id']
    def register(self,aid,label,consent=True):
        r=self.client.post('/api/recognition/examples',json={'asset_id':aid,'label':label,'training_consent':consent})
        if r.status_code==200:self.ids.append(r.json()['id'])
        return r
    def test_features_are_finite_and_normalized(self):
        mask,_=engine.mask_image(samples.sample('鱼',1));f=recognition.features(mask)
        self.assertTrue(np.isfinite(f).all());self.assertAlmostEqual(float(np.linalg.norm(f)),1,places=5)
    def test_reference_classification_with_independent_image(self):
        for label in ['花卉','鱼']:
            for seed in range(3):self.assertEqual(self.register(self.upload(label,seed),label).status_code,200)
        aid=self.upload('鱼',301);r=self.client.get(f'/api/assets/{aid}/recognition').json()
        self.assertEqual(r['status'],'matched');self.assertEqual(r['predicted_label'],'鱼')
        self.assertEqual(r['data_scope'],'user_labeled_references')
    def test_same_asset_is_excluded(self):
        aid=self.upload('鸟',1);self.register(aid,'鸟')
        r=self.client.get(f'/api/assets/{aid}/recognition').json()
        self.assertEqual(r['status'],'no_examples');self.assertTrue(r['excluded_self_reference'])
    def test_consent_and_rights_required(self):
        aid=self.upload('鸟',2);self.assertEqual(self.register(aid,'鸟',False).status_code,403)
        aid=self.upload('鸟',2,'display_only');self.assertEqual(self.register(aid,'鸟').status_code,403)
    def test_duplicates_rejected_and_delete(self):
        aid=self.upload('鸟',3);r=self.register(aid,'鸟');self.assertEqual(r.status_code,200)
        self.assertEqual(self.register(aid,'鸟').status_code,409)
        eid=self.ids.pop();self.assertEqual(self.client.delete('/api/recognition/examples/'+eid).status_code,200)
        self.assertEqual(self.client.delete('/api/recognition/examples/'+eid).status_code,404)
    def test_ambiguous_is_unknown(self):
        f=np.array([1.,0.],dtype='float32')
        refs=[{'label':x,'feature':[1.,0.],'id':x,'asset_id':x,'source':'test'} for x in ['a','b']]
        r=recognition.rank(f,refs);self.assertEqual(r['status'],'unknown');self.assertIsNone(r['predicted_label'])
    def test_low_similarity_is_unknown(self):
        f=np.array([0.,1.],dtype='float32')
        refs=[{'label':x,'feature':[1.,0.],'id':x,'asset_id':x,'source':'test'} for x in ['a','b']]
        self.assertEqual(recognition.rank(f,refs)['status'],'unknown')
    def test_demo_not_mixed_with_user_gallery(self):
        aid=self.client.post('/api/recognition/demo?label=花卉').json()['id']
        r=self.client.get(f'/api/assets/{aid}/recognition?gallery=demo').json()
        self.assertEqual(r['data_scope'],'synthetic_demo_only');self.assertEqual(r['predicted_label'],'花卉')
        self.assertEqual(r['reference_count'],80)
        self.assertEqual(self.client.get(f'/api/assets/{aid}/recognition?gallery=invalid').status_code,400)
    def test_synthetic_reference_registration_blocked(self):
        aid=self.client.post('/api/recognition/demo?label=鸟').json()['id']
        self.assertEqual(self.register(aid,'鸟').status_code,400)

    def test_single_class_cannot_be_confident(self):
        f=np.array([1.,0.],dtype='float32')
        refs=[{'label':'one','feature':[1.,0.],'id':'a','asset_id':'a','source':'test'}]
        self.assertEqual(recognition.rank(f,refs)['status'],'unknown')
    def test_label_validation(self):
        aid=self.upload('鱼',1)
        self.assertEqual(self.register(aid,'   ').status_code,400)
        self.assertEqual(self.register(aid,'a\nb').status_code,400)

if __name__=='__main__':unittest.main()
