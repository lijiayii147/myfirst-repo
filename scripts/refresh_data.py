"""Refresh the checked-in, commit-pinned metadata subset; no images downloaded."""
import hashlib,json
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parent.parent

def main():
    path=ROOT/'data'/'catalog.json';records=json.loads(path.read_text('utf-8'))
    with httpx.Client(timeout=30,follow_redirects=True) as client:
        for record in records:
            response=client.get(record['metadata_url']);response.raise_for_status()
            raw=response.content
            if hashlib.sha256(raw).hexdigest()!=record['sha256']:
                raise RuntimeError('Pinned metadata checksum mismatch: '+record['id'])
            json.loads(raw)
            (ROOT/'data'/record['raw_file']).write_bytes(raw)
    print(f'Verified and refreshed {len(records)} commit-pinned metadata files; no images fetched.')

if __name__=='__main__':main()
