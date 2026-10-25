"""Optional official Met API importer. Not required for offline application startup."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
import httpx
from PIL import Image
from io import BytesIO

ROOT=Path(__file__).resolve().parent.parent
BASE='https://collectionapi.metmuseum.org/public/collection/v1'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query',default='Chinese textile')
    parser.add_argument('--limit',type=int,default=10)
    parser.add_argument('--download-images',action='store_true')
    args=parser.parse_args()
    if not 1<=args.limit<=50:parser.error('--limit must be 1..50')
    target=ROOT/'runtime'/'met_import';target.mkdir(parents=True,exist_ok=True)
    records=[];skipped=0
    try:
        with httpx.Client(timeout=30,follow_redirects=False) as client:
            response=client.get(BASE+'/search',params={'q':args.query,'hasImages':'true'})
            response.raise_for_status();ids=response.json().get('objectIDs') or []
            for oid in ids[:args.limit]:
                response=client.get(BASE+'/objects/'+str(int(oid)));response.raise_for_status();data=response.json()
                if data.get('isPublicDomain') is not True:
                    skipped+=1;continue
                record={'id':data['objectID'],'title':data.get('title'),'source_url':data.get('objectURL'),
                        'metadata_url':BASE+'/objects/'+str(oid),'isPublicDomain':True,
                        'image_url':data.get('primaryImageSmall'),'metadata':data,
                        'license_policy':'https://github.com/metmuseum/openaccess/blob/master/README.md'}
                if args.download_images and record['image_url']:
                    url=record['image_url'];parsed=urlparse(url)
                    if parsed.scheme!='https' or not (parsed.hostname or '').endswith('.metmuseum.org'):
                        raise ValueError('Unrecognized image destination; manual review required')
                    chunks=[];size=0
                    with client.stream('GET',url) as image_response:
                        image_response.raise_for_status()
                        for chunk in image_response.iter_bytes():
                            size+=len(chunk)
                            if size>12*1024*1024:raise ValueError('Image exceeds 12 MB limit')
                            chunks.append(chunk)
                    raw=b''.join(chunks)
                    with Image.open(BytesIO(raw)) as im:
                        if im.width*im.height>16_000_000:raise ValueError('Image exceeds pixel limit')
                        im.verify()
                    name=f'met_{oid}.image';(target/name).write_bytes(raw)
                    record['image_file']=name;record['image_sha256']=hashlib.sha256(raw).hexdigest()
                records.append(record)
        (target/'records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),'utf-8')
        print(f'Saved {len(records)} public-domain records; skipped {skipped} without public-domain flag. Output: {target}')
    except (httpx.HTTPError,ValueError,OSError) as exc:
        parser.exit(2,f'Import incomplete: {exc}\nCheck network access and official API availability. Bundled data remains unchanged.\n')

if __name__=='__main__':main()
