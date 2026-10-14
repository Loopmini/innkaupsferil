"""Verified in-place Windows update. Never replaces data/ or .env."""
import hashlib,json,os,shutil,socket,sys,tempfile,zipfile
from datetime import datetime
from pathlib import Path


def apply(source,target):
 source=Path(source).resolve();target=Path(target).resolve()
 if source==target:raise ValueError('Veldu núverandi forritsmöppu, ekki afþjöppuðu uppfærslumöppuna.')
 if not (target/'app.py').is_file() or not (target/'static/index.html').is_file():raise ValueError('Þetta er ekki núverandi Njörður-forritsmappa (app.py og static/index.html þurfa að vera til).')
 manifest=json.loads((source/'update-manifest.json').read_text(encoding='utf-8'))
 entries=manifest['files']
 if not {'app.py','static/index.html','static/theme.css','static/theme-ui.js','static/boot-check.js','static/evidence-ui.js'}.issubset(entries):raise ValueError('Ófullkominn uppfærslupakki.')
 for name,digest in entries.items():
  p=Path(name)
  if p.is_absolute() or '..' in p.parts or p.parts[0] in ('data','.git') or p.name=='.env' or (target/p).is_symlink():raise ValueError('Óheimil skrá í uppfærslu: '+name)
  if (source/p).resolve()!=source/p or not (source/p).is_file():raise ValueError('Skrá vantar eða slóð er ógild: '+name)
  if not (target/p).resolve().is_relative_to(target):raise ValueError('Markslóð fer út fyrir forritsmöppuna.')
  if hashlib.sha256((source/p).read_bytes()).hexdigest()!=digest:raise ValueError('Skrá stenst ekki heilleikapróf: '+name)
 backup=target.parent/('Njordur-afrit-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.zip')
 with zipfile.ZipFile(backup,'x',zipfile.ZIP_DEFLATED) as z:
  for p in target.rglob('*'):
   rel=p.relative_to(target)
   if p.is_file() and not p.is_symlink() and not any(x in ('.git','__pycache__','node_modules') for x in rel.parts):z.write(p,str(rel))
 changed=[]
 try:
  for name in entries:
   src=source/name;dst=target/name;dst.parent.mkdir(parents=True,exist_ok=True);existed=dst.exists()
   fd,tmp=tempfile.mkstemp(prefix='.njordur-update-',dir=dst.parent);os.close(fd)
   try:shutil.copyfile(src,tmp);os.replace(tmp,dst)
   finally:
    if os.path.exists(tmp):os.unlink(tmp)
   changed.append((name,existed))
 except Exception:
  with zipfile.ZipFile(backup) as z:
   for name,existed in reversed(changed):
    dst=target/name
    if existed:dst.write_bytes(z.read(name))
    else:dst.unlink(missing_ok=True)
  raise
 return backup

if __name__=='__main__':
 try:
  # A live process may still have old routes, SQLite handles or background sync.
  with socket.socket() as check:
   check.settimeout(1)
   if check.connect_ex(('127.0.0.1',8000))==0:raise ValueError('Njörður er enn í gangi á porti 8000. Lokaðu skipanaglugganum sem keyrir forritið og reyndu aftur.')
  print('Uppfærir núverandi Njörð. Data og .env eru varðveitt. Afrit er tekið fyrst.')
  target=input('Límdu slóð núverandi forritsmöppu (þar sem app.py er): ').strip().strip('"')
  if not target:raise ValueError('Engin mappa valin.')
  backup=apply(Path(__file__).parent,target)
  print('Uppfærsla tókst. Afrit:',backup)
  print('Ræstu Starta-Windows.bat í:',Path(target).resolve())
  print('Neðst í valmynd á að standa: v0.18 · nýtt viðmót virkt.')
 except Exception as error:
  print('UPPFÆRSLA STÖÐVUÐ:',error);sys.exit(1)
