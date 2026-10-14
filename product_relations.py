"""Explicit, bidirectional product relations; never merge identities or infer approval."""
import json, math
from datetime import datetime,timezone
import taxonomy

STATES={'confirmed','possible','related','incompatible'}
KINDS={'consumable','accessory','spare','alternative'}

def setup(db):
 db.executescript('''CREATE TABLE IF NOT EXISTS product_relations(id INTEGER PRIMARY KEY,a INTEGER NOT NULL,b INTEGER NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL,evidence TEXT NOT NULL,notes TEXT NOT NULL,updated_at TEXT NOT NULL,snapshot TEXT NOT NULL,UNIQUE(a,b,kind));
 CREATE TABLE IF NOT EXISTS product_audit(id INTEGER PRIMARY KEY,offer_id INTEGER NOT NULL,kind TEXT NOT NULL,before_json TEXT,after_json TEXT,source TEXT NOT NULL,created_at TEXT NOT NULL);''')

def stamp():return datetime.now(timezone.utc).isoformat()
def audit(db,oid,kind,before,after,source):
 db.execute('INSERT INTO product_audit(offer_id,kind,before_json,after_json,source,created_at) VALUES(?,?,?,?,?,?)',(oid,kind,json.dumps(before,ensure_ascii=False),json.dumps(after,ensure_ascii=False),source,stamp()))
def fingerprint(o):
 return {k:o.get(k) for k in ('name','brand','manufacturer_part','gtin','specifications','pack_quantity','unit')}
def save(app,data):
 if type(data.get('a')) is not int or type(data.get('b')) is not int or data['a']==data['b']:raise ValueError('Veldu tvær ólíkar nákvæmar vörufærslur.')
 a,b=sorted((data['a'],data['b']));offers={o['id']:o for o in app.catalogue()['offers']}
 if a not in offers or b not in offers:raise ValueError('Vara fannst ekki; engin tengsl vistuð.')
 kind=data.get('kind');status=data.get('status');evidence=data.get('evidence','');notes=data.get('notes','')
 if kind not in KINDS or status not in STATES:raise ValueError('Ógild tegund eða staða tengsla.')
 if any(not isinstance(x,str) or len(x)>2000 for x in (evidence,notes)):raise ValueError('Ógild heimild eða athugasemd.')
 if status in ('confirmed','incompatible') and not evidence.strip():raise ValueError('Heimild þarf fyrir staðfest samhæfi eða skráð ósamhæfi.')
 if status in ('confirmed','incompatible') and data.get('reviewed') is not True:raise ValueError('Staðfestu að heimild hafi verið yfirfarin fyrir þessar nákvæmu gerðir.')
 comparison=candidate(offers[a],offers[b])
 if status=='confirmed' and comparison and comparison['conflicts']:raise ValueError('Tæknilegir eiginleikar stangast á. Leiðréttu gögnin áður en samhæfi er staðfest.')
 value=dict(a=a,b=b,kind=kind,status=status,evidence=evidence.strip(),notes=notes.strip(),updated_at=stamp(),snapshot=json.dumps({str(a):fingerprint(offers[a]),str(b):fingerprint(offers[b])},ensure_ascii=False))
 with app.connect() as db:
  old=db.execute('SELECT * FROM product_relations WHERE a=? AND b=? AND kind=?',(a,b,kind)).fetchone()
  if old and data.get('expected_at')!=old['updated_at']:raise ValueError('Tengsl breyttust eftir opnun. Opnaðu þau aftur áður en þú vistar.')
  db.execute('INSERT INTO product_relations(a,b,kind,status,evidence,notes,updated_at,snapshot) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(a,b,kind) DO UPDATE SET status=excluded.status,evidence=excluded.evidence,notes=excluded.notes,updated_at=excluded.updated_at,snapshot=excluded.snapshot',tuple(value.values()))
  audit(db,a,'relation',dict(old) if old else None,value,evidence.strip() or 'Handvirkt tengt við notkun')
 return {'ok':True}
def kind(o):
 c=o.get('classification',{}).get('id','')
 return 'gun' if c=='tools.power.nailers' else 'nails' if c=='fasteners.nails.collated' else None

def candidate(a,b):
 if {kind(a),kind(b)}!={'gun','nails'}:return None
 gun,nails=(a,b) if kind(a)=='gun' else (b,a)
 g=gun.get('specifications',{});n=nails.get('specifications',{});missing=[];conflicts=[]
 for low,high,key in [('nail_length_min_mm','nail_length_max_mm','length_mm'),('nail_diameter_min_mm','nail_diameter_max_mm','diameter_mm')]:
  if any(type(v) not in (int,float) or not math.isfinite(v) for v in (g.get(low),g.get(high),n.get(key))):missing.append(key);continue
  if not g[low]<=n[key]<=g[high]:conflicts.append(key)
 for key in ('collation_angle_deg','collation_type','nail_head_type'):
  if g.get(key) is None or n.get(key) is None or not str(g[key]).strip() or not str(n[key]).strip():missing.append(key)
  elif key=='collation_angle_deg' and type(g[key]) in (int,float) and type(n[key]) in (int,float):
   if not math.isfinite(g[key]) or not math.isfinite(n[key]):missing.append(key)
   elif g[key]!=n[key]:conflicts.append(key)
  elif taxonomy.norm(g[key])!=taxonomy.norm(n[key]):conflicts.append(key)
 if conflicts:return {'status':'related','reason':'Tengt við notkun; eiginleikar stangast á: '+', '.join(conflicts)+'. Ekki nota sem staðfesta samsvörun.','conflicts':conflicts}
 if missing:return {'status':'related','reason':'Tengt við notkun. Samhæfi óþekkt; vantar: '+', '.join(missing),'conflicts':[]}
 return {'status':'possible','reason':'Skráð lengd, þvermál, halli, samsetning og hausgerð passa. Staðfesting framleiðanda vantar.','conflicts':[]}

def listing(app,oid):
 offers={o['id']:o for o in app.catalogue()['offers']}
 if oid not in offers:raise ValueError('Vara fannst ekki.')
 with app.connect() as db:
  saved=[dict(r) for r in db.execute('SELECT * FROM product_relations WHERE a=? OR b=? ORDER BY updated_at DESC',(oid,oid))]
  history=[dict(r) for r in db.execute("SELECT * FROM product_audit WHERE offer_id=? OR (kind='relation' AND (json_extract(after_json,'$.a')=? OR json_extract(after_json,'$.b')=?)) ORDER BY id DESC LIMIT 100",(oid,oid,oid))]
 related=set();result=[]
 for r in saved:
  target=r['b'] if r['a']==oid else r['a'];related.add(target);snap=json.loads(r.pop('snapshot'));changed=any(str(i) not in snap or i not in offers or snap[str(i)]!=fingerprint(offers[i]) for i in (r['a'],r['b']))
  r.update(target_id=target,target_name=offers.get(target,{}).get('name','Vara ekki lengur í núverandi gögnum'),needs_review=changed,stored_status=r['status'],automatic=False)
  if changed and r['status']=='confirmed':r['status']='related'
  if changed:r['review_reason']='Vörugögn hafa breyst frá staðfestingu; yfirfara þarf heimild og nákvæmar gerðir.'
  result.append(r)
 suggestions=[]
 for target,o in offers.items():
  if target==oid or target in related:continue
  c=candidate(offers[oid],o)
  if c:suggestions.append(dict(c,target_id=target,target_name=o['name'],kind='consumable',automatic=True,evidence='Skráðir eiginleikar / núverandi vörutegund',needs_review=True))
 suggestions.sort(key=lambda r:(r['status']!='possible',r['target_name']))
 return {'relations':result+suggestions[:80],'suggestion_count':len(suggestions),'history':history}
