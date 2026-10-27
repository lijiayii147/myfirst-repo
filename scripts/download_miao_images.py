#!/usr/bin/env python3
"""Download traceable Miao embroidery source images into data/miao/raw/."""
import csv, hashlib, json, re, sys
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
CSV_PATH=ROOT/'data/miao_metadata.csv'; OUT=ROOT/'data/miao/raw'; REPORT=ROOT/'data/miao/download_report.json'
OUT.mkdir(parents=True, exist_ok=True)
rows=list(csv.DictReader(CSV_PATH.open(encoding='utf-8-sig', newline='')))
results=[]
headers={'User-Agent':'Wenmai-Miao-MVP/0.1 (traceable dataset preparation)'}
with httpx.Client(follow_redirects=True, timeout=20, headers=headers) as client:
 for row in rows:
  iid=row.get('image_id','').strip(); url=row.get('图片链接或馆藏文件名','').strip()
  result={'image_id':iid,'url':url,'status':'failed'}
  if not re.fullmatch(r'MIAO_\d{4}',iid) or not url.startswith(('http://','https://')):
   result['error']='invalid id or URL'; results.append(result); continue
  dest=OUT/(iid+'.jpg')
  try:
   if dest.exists() and dest.stat().st_size>0:
    raw=dest.read_bytes(); result.update(status='existing',path=str(dest.relative_to(ROOT)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()); results.append(result); continue
   resp=client.get(url); resp.raise_for_status(); raw=resp.content
   if len(raw)<100: raise ValueError('response too small')
   dest.write_bytes(raw)
   result.update(status='downloaded',path=str(dest.relative_to(ROOT)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),content_type=resp.headers.get('content-type',''))
  except Exception as exc: result['error']=str(exc)[:300]
  results.append(result); print(iid, result['status'], result.get('error',''))
REPORT.write_text(json.dumps({'total':len(results),'downloaded':sum(x['status']=='downloaded' for x in results),'existing':sum(x['status']=='existing' for x in results),'failed':sum(x['status']=='failed' for x in results),'items':results},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('report:',REPORT)
