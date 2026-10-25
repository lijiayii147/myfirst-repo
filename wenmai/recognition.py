"""Inspectable local exemplar recognizer: shape retrieval, not cultural attribution."""
import json
import math
import sqlite3
from pathlib import Path
import numpy as np
from PIL import Image

VERSION='shape-hog-v1'
# Conservative defaults; tune only using a separate real validation set.
MIN_SIMILARITY=.82
MIN_MARGIN=.035


def features(mask):
    ys,xs=np.where(mask)
    if len(xs)<4:raise ValueError('有效前景不足')
    crop=Image.fromarray(mask[ys.min():ys.max()+1,xs.min():xs.max()+1].astype('uint8')*255)
    crop.thumbnail((56,56))
    canvas=Image.new('L',(64,64));canvas.paste(crop,((64-crop.width)//2,(64-crop.height)//2))
    a=np.array(canvas,dtype=float)/255
    grid=np.array(canvas.resize((24,24),Image.Resampling.BILINEAR),dtype=float).ravel()/255
    gy,gx=np.gradient(a);mag=np.hypot(gx,gy);angle=(np.arctan2(gy,gx)+np.pi)%(2*np.pi)
    hist=[]
    for y in range(0,64,16):
        for x in range(0,64,16):
            h,_=np.histogram(angle[y:y+16,x:x+16],bins=8,range=(0,2*np.pi),weights=mag[y:y+16,x:x+16])
            h=h/(np.linalg.norm(h)+1e-8);hist.extend(h)
    # Normalize each block separately, then combine. Shape dominates texture.
    blocks=[grid,np.array(hist),np.concatenate((a.mean(axis=0),a.mean(axis=1)))]
    weights=[.65,.25,.10]
    vec=np.concatenate([w*b/(np.linalg.norm(b)+1e-8) for w,b in zip(weights,blocks)])
    return (vec/(np.linalg.norm(vec)+1e-8)).astype('float32')


def initialize(db):
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS recognition_examples (id TEXT PRIMARY KEY,label TEXT NOT NULL,asset_id TEXT NOT NULL,source TEXT NOT NULL,feature TEXT NOT NULL,feature_version TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(label,asset_id))')


def composition(mask):
    """Describe measurable properties rather than assigning heritage semantics."""
    def iou(other):return float((mask&other).sum()/max(1,(mask|other).sum()))
    scores={'horizontal_mirror_iou':round(iou(np.fliplr(mask)),4),'vertical_mirror_iou':round(iou(np.flipud(mask)),4)}
    tags=[]
    if scores['horizontal_mirror_iou']>=.82:tags.append('左右近似对称')
    if scores['vertical_mirror_iou']>=.82:tags.append('上下近似对称')
    if not tags:tags.append('未检出高匹配镜像对称')
    return {'tags':tags,'measurements':scores,'method':'binary_mask_mirror_iou','note':'对称描述不是母题类别、朝代、地域或工艺鉴定。'}


def rank(vector,examples,minimum=MIN_SIMILARITY,margin=MIN_MARGIN):
    classes={}
    for example in examples:
        feature=np.array(example['feature'],dtype='float32')
        if feature.shape!=vector.shape or not np.isfinite(feature).all():continue
        similarity=float(np.dot(vector,feature)/(np.linalg.norm(feature)*np.linalg.norm(vector)+1e-8))
        if example['label'] not in classes or similarity>classes[example['label']]['similarity']:
            classes[example['label']]={'label':example['label'],'similarity':round(similarity,5),
                                      'example_id':example['id'],'asset_id':example['asset_id'],'source':example['source']}
    candidates=sorted(classes.values(),key=lambda x:-x['similarity'])[:5]
    enough=len(classes)>=2
    gap=(candidates[0]['similarity']-candidates[1]['similarity']) if len(candidates)>=2 else 0
    accepted=bool(enough and candidates[0]['similarity']>=minimum and gap>=margin)
    return {'status':'matched' if accepted else ('no_examples' if not candidates else 'unknown'),
            'predicted_label':candidates[0]['label'] if accepted else None,'candidates':candidates,
            'margin':round(gap,5),'thresholds':{'min_similarity':minimum,'min_margin':margin,'minimum_classes':2},
            'feature_version':VERSION,'method':'nearest_labeled_shape_example',
            'score_note':'余弦相似度是形状匹配分数，不是准确率或经过校准的概率；阈值尚未经真实非遗验证集标定。'}


def examples(db):
    with sqlite3.connect(db) as conn:
        conn.row_factory=sqlite3.Row
        rows=conn.execute('SELECT * FROM recognition_examples WHERE feature_version=?',(VERSION,)).fetchall()
    return [{**dict(r),'feature':json.loads(r['feature'])} for r in rows]


def predict(mask,db):
    result=rank(features(mask),examples(db));result['composition']=composition(mask)
    result['limitations']=['依赖用户正确标注的参考图库','旋转、复杂背景、遮挡和不同材质可能降低匹配','不自动判断文化寓意、地域、年代、真假或授权']
    return result
