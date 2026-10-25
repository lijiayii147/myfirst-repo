import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import numpy as np
from PIL import Image, UnidentifiedImageError
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import engine

ROOT=Path(__file__).resolve().parent.parent
RUNTIME=Path(os.environ.get('WENMAI_RUNTIME',ROOT/'runtime')).resolve()
RUNTIME.mkdir(parents=True,exist_ok=True)
app=FastAPI(title='Wenmai 纹脉',version='0.1.0')
app.mount('/static',StaticFiles(directory=ROOT/'wenmai'/'static'),name='static')
DB=RUNTIME/'audit.sqlite3'
with sqlite3.connect(DB) as db:
    db.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, timestamp TEXT, payload TEXT)')


def catalog():
    p=ROOT/'data'/'catalog.json'
    return json.loads(p.read_text('utf-8')) if p.exists() else []


def valid_id(value):
    if not re.fullmatch('[0-9a-f]{32}',value):raise HTTPException(404,'任务不存在')
    return value


def read_asset(value):
    p=RUNTIME/valid_id(value)/'asset.json'
    if not p.exists():raise HTTPException(404,'任务不存在')
    return json.loads(p.read_text('utf-8'))


def save_asset(image,rights,source,origin):
    mask,analysis=engine.analyze(image)
    aid=uuid.uuid4().hex;directory=RUNTIME/aid;directory.mkdir()
    np.save(directory/'mask.npy',mask,allow_pickle=False)
    content=engine.png_bytes(engine.render(mask));(directory/'preview.png').write_bytes(content)
    record={'id':aid,'analysis':analysis,'rights':rights,'source':source,
            'origin':origin,'created_at':datetime.now(timezone.utc).isoformat(),
            'normalized_sha256':hashlib.sha256(content).hexdigest(),
            'preview_url':f'/api/assets/{aid}/preview'}
    (directory/'asset.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf-8')
    return record


@app.get('/')
def index():return FileResponse(ROOT/'wenmai'/'static'/'index.html')


@app.get('/api/health')
def health():return {'status':'ok','version':'0.1.0','data_records':len(catalog()),'mode':'local_geometric_prototype'}


@app.post('/api/demo')
def demo():return save_asset(engine.demo_image(),'derivatives_allowed','Original procedural geometry by Wenmai; not an authentic heritage object','synthetic_demo')


@app.post('/api/assets')
async def upload(file:UploadFile=File(...),rights:str=Form('unknown'),source:str=Form('')):
    if rights not in ('unknown','display_only','derivatives_allowed'):
        raise HTTPException(400,'无效权利状态')
    if len(source)>2000:raise HTTPException(400,'来源说明过长')
    raw=await file.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:raise HTTPException(413,'上传限8 MB')
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.width*image.height>engine.MAX_PIXELS:raise ValueError('图片不得超过1600万像素')
            if image.format not in ('PNG','JPEG','WEBP'):raise ValueError('仅支持PNG、JPEG、WebP')
            image.load();return save_asset(image,rights,source,'user_upload')
    except (ValueError,UnidentifiedImageError,OSError,Image.DecompressionBombError) as exc:
        raise HTTPException(400,str(exc))


@app.get('/api/assets/{asset_id}/preview')
def preview(asset_id:str):
    read_asset(asset_id);return FileResponse(RUNTIME/asset_id/'preview.png')


class RectangleEdit(BaseModel):
    x: int = Field(ge=0, le=383)
    y: int = Field(ge=0, le=383)
    width: int = Field(gt=0, le=384)
    height: int = Field(gt=0, le=384)
    action: str


class EditRequest(BaseModel):
    operations: list[RectangleEdit] = Field(min_length=1, max_length=100)


@app.post('/api/assets/{asset_id}/edit')
def edit_structure(asset_id: str, req: EditRequest):
    parent = read_asset(asset_id)
    if parent['rights'] != 'derivatives_allowed':
        raise HTTPException(403, '素材未确认允许衍生，不能修改结构。')
    mask = np.load(RUNTIME/asset_id/'mask.npy', allow_pickle=False)
    h, w = mask.shape
    for operation in req.operations:
        if operation.action not in ('add', 'erase'):
            raise HTTPException(400, '仅支持add或erase结构操作')
        if operation.x+operation.width > w or operation.y+operation.height > h:
            raise HTTPException(400, '编辑区域超出图像边界')
        mask[operation.y:operation.y+operation.height,
             operation.x:operation.x+operation.width] = operation.action == 'add'
    image = Image.fromarray(np.where(mask, 0, 255).astype('uint8'))
    try:
        record = save_asset(image, parent['rights'], parent['source'], 'user_structure_edit')
    except ValueError as e:
        raise HTTPException(400, str(e))
    record['parent_asset_id'] = asset_id
    record['operations'] = [o.model_dump() for o in req.operations]
    (RUNTIME/record['id']/'asset.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), 'utf-8')
    return record


@app.get('/api/knowledge')
def knowledge(q:str='',limit:int=10):
    if len(q)>200:raise HTTPException(400,'检索词过长')
    limit=max(1,min(30,limit));items=catalog()
    tokens=[t.lower() for t in re.findall(r'[\w\u4e00-\u9fff]+',q)]
    synonyms={'剪纸':['paper','cut'],'花':['flower','floral'],'中国':['china','chinese'],'纺织':['textile'],'纹样':['pattern','design','ornament']}
    for k,words in synonyms.items():
        if k in q:tokens.extend(words)
    scored=[]
    for item in items:
        text=json.dumps(item,ensure_ascii=False).lower()
        score=sum(t in text for t in tokens)
        if score or not tokens:scored.append((score,item))
    scored.sort(key=lambda x:-x[0])
    return {'items':[x[1] for x in scored[:limit]],'total_matches':len(scored),
            'method':'keyword_metadata_search','note':'馆藏元数据检索，不代表图像识别或自动文化释义。'}


class DesignRequest(BaseModel):
    asset_id:str
    mode:str='contemporary'
    layout:str='single'
    color:str='#b92535'
    repair:bool=False
    width_mm:float=Field(ge=20,le=1000,default=120)
    min_width_mm:float=Field(ge=0,le=10,default=.3)
    margin_mm:float=Field(ge=0,le=100,default=3)
    evidence_ids:list[str]=Field(default_factory=list,max_length=20)


@app.post('/api/designs')
def design(req:DesignRequest):
    asset=read_asset(req.asset_id)
    if asset['rights']!='derivatives_allowed':raise HTTPException(403,'素材未确认允许衍生，不能进入共创。请核对来源与许可后重新上传。')
    if not re.fullmatch('#[0-9a-fA-F]{6}',req.color):raise HTTPException(400,'颜色格式应为#RRGGBB')
    known={x['id']:x for x in catalog()}
    if any(k not in known for k in req.evidence_ids):raise HTTPException(400,'未知证据编号')
    mask=np.load(RUNTIME/req.asset_id/'mask.npy',allow_pickle=False)
    try:result,report=engine.create_design(mask,req.mode,req.layout,req.color,req.repair,req.width_mm,req.min_width_mm,req.margin_mm)
    except ValueError as e:raise HTTPException(400,str(e))
    did=uuid.uuid4().hex;directory=RUNTIME/did;directory.mkdir()
    np.save(directory/'mask.npy',result,allow_pickle=False)
    (directory/'design.svg').write_text(engine.svg(result,req.color),'utf-8')
    (directory/'design.png').write_bytes(engine.png_bytes(engine.render(result,req.color)))
    evidence=[{'id':k,'title':known[k]['title'],'source_url':known[k]['source_url'],
               'role':'用户选择的参考资料，不自动证明上传图的出处或寓意'} for k in req.evidence_ids]
    card={'task_id':did,'created_at':datetime.now(timezone.utc).isoformat(),
          'asset':asset,'parameters':req.model_dump(),'report':report,'references':evidence,
          'ai_label':'机器辅助几何共创；未使用扩散模型；未经文化与实体工艺审核',
          'review_status':'pending_human_review','engine_version':'0.1.0',
          'limitations':['未训练母题分类模型','未执行文化寓意自动判定','SVG为二值逐行矢量化，未优化为加工刀路','未确认上传资料的实际权属，用户需提供有效许可']}
    (directory/'source_card.json').write_text(json.dumps(card,ensure_ascii=False,indent=2),'utf-8')
    (directory/'changes.txt').write_text('\n'.join(report['changes'])+'\n'+card['ai_label'],'utf-8')
    with sqlite3.connect(DB) as db:
        db.execute('INSERT INTO events VALUES (?,?,?)',(did,card['created_at'],json.dumps(card,ensure_ascii=False)))
    return {'id':did,'report':report,'preview_url':f'/api/designs/{did}/png',
            'download_url':f'/api/designs/{did}/bundle','source_card':card}


@app.get('/api/designs/{design_id}/{kind}')
def download(design_id:str,kind:str):
    directory=RUNTIME/valid_id(design_id)
    if not (directory/'source_card.json').exists():raise HTTPException(404,'结果不存在')
    names={'png':('design.png','image/png'),'svg':('design.svg','image/svg+xml'),
           'card':('source_card.json','application/json')}
    if kind in names:
        name,mime=names[kind];return FileResponse(directory/name,media_type=mime,filename=name)
    if kind=='bundle':
        b=BytesIO()
        with ZipFile(b,'w',ZIP_DEFLATED) as z:
            for name in ('design.png','design.svg','source_card.json','changes.txt'):z.write(directory/name,name)
        return Response(b.getvalue(),media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="Wenmai_Design_{design_id[:8]}.zip"'})
    raise HTTPException(404,'未知格式')
