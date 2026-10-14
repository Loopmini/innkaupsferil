"""Local recoverable snapshots. No secrets, no arbitrary extraction paths."""
import hashlib
import json
import re
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

FILES=('legacy-project.json','market-live.json','market-status.json','full-sync.json','market-history.sqlite')

def create(root,dbpath=None,reason='manual'):
    root=Path(root);data=root/'data';folder=data/'backups';folder.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    name=stamp+'-'+uuid4().hex[:10]+'.zip';target=folder/name
    manifest={'created_at':datetime.now(timezone.utc).isoformat(),'reason':reason,'files':{}}
    with tempfile.TemporaryDirectory() as td:
        entries={}
        paths=[(data/n,n) for n in FILES]+[(Path(dbpath) if dbpath else data/'catalog.sqlite','catalog.sqlite')]
        for source,n in paths:
            if not source.exists():continue
            if n.endswith('.sqlite'):
                copy=Path(td)/n
                with closing(sqlite3.connect(source)) as src, closing(sqlite3.connect(copy)) as dst:
                    src.backup(dst)
                raw=copy.read_bytes()
            else:raw=source.read_bytes()
            entries[n]=raw;manifest['files'][n]=hashlib.sha256(raw).hexdigest()
        with zipfile.ZipFile(target.with_suffix('.tmp'),'w',zipfile.ZIP_DEFLATED) as z:
            for n,raw in entries.items():z.writestr(n,raw)
            z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False))
        target.with_suffix('.tmp').replace(target)
    return {'name':name,**manifest}

def path(root,name):
    if not isinstance(name,str) or not re.fullmatch(r'\d{8}T\d{6}-[a-f0-9]{10}\.zip',name):raise ValueError('Ógilt afrit.')
    p=Path(root)/'data/backups'/name
    if not p.is_file():raise ValueError('Afrit fannst ekki.')
    return p

def listing(root):
    result=[]
    for p in sorted((Path(root)/'data/backups').glob('*.zip'),reverse=True):
        try:
            with zipfile.ZipFile(p) as z:m=json.loads(z.read('manifest.json'))
            result.append({'name':p.name,'created_at':m['created_at'],'reason':m.get('reason'),'size':p.stat().st_size})
        except (OSError,ValueError,KeyError,zipfile.BadZipFile):continue
    return result

def restore(root,dbpath,name):
    """Validate everything before touching current data; keep a rescue snapshot."""
    p=path(root,name)
    with zipfile.ZipFile(p) as z:
        manifest=json.loads(z.read('manifest.json'));entries={}
        for n,digest in manifest['files'].items():
            if n not in FILES+('catalog.sqlite',):raise ValueError('Óþekkt skrá í afriti.')
            raw=z.read(n)
            if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Afrit stenst ekki heilleikapróf.')
            if n.endswith('.json'):json.loads(raw.decode('utf-8'))
            entries[n]=raw
    with tempfile.TemporaryDirectory() as td:
        for n,raw in entries.items():
            f=Path(td)/n;f.write_bytes(raw)
            if n.endswith('.sqlite'):
                with closing(sqlite3.connect(f)) as con:
                    if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Gagnagrunnur í afriti er skemmdur.')
        rescue=create(root,dbpath,'before_restore')
        for n,raw in entries.items():
            dest=Path(dbpath) if n=='catalog.sqlite' else Path(root)/'data'/n
            dest.parent.mkdir(parents=True,exist_ok=True)
            if n.endswith('.sqlite'):
                with closing(sqlite3.connect(Path(td)/n)) as src, closing(sqlite3.connect(dest)) as dst:
                    src.backup(dst)
            else:
                temp=dest.with_suffix(dest.suffix+'.restore');temp.write_bytes(raw);temp.replace(dest)
    return {'restored':name,'rescue_backup':rescue['name']}
