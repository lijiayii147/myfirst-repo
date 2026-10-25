"""Build a source-only distributable; excludes runtime uploads, credentials and venv."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib
ROOT=Path(__file__).resolve().parent.parent
NAME='Wenmai_Prototype_v0.1.0'
def main():
    target=ROOT/'releases';target.mkdir(exist_ok=True)
    files=[]
    for name in ['wenmai','scripts','tests','data','docs']:
        files.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    for name in ['README.md','LICENSE','requirements.txt','requirements-lock.txt','start.bat','start.sh','Dockerfile','.dockerignore','.gitignore','.gitattributes']:
        files.append(ROOT/name)
    package=target/(NAME+'.zip')
    with ZipFile(package,'w',ZIP_DEFLATED) as z:
        for path in sorted(files):z.write(path,NAME+'/'+path.relative_to(ROOT).as_posix())
    digest=hashlib.sha256(package.read_bytes()).hexdigest()
    (target/(NAME+'.sha256')).write_text(digest+'  '+package.name+'\n','utf-8')
    print(package,package.stat().st_size,'bytes',digest)
if __name__=='__main__':main()
