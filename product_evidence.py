"""Reviewed product identity and document links, separate from supplier observations.

No network or model calls, no merging and no writes during catalogue reads.
"""
import hashlib
import json
import re
from urllib.parse import urlsplit, urlunsplit, urlencode
from product_extras import image_url
from product_relations import audit, stamp

FIELDS=('manufacturer','brand','model','manufacturer_part','gtin')
TYPES={'datasheet','drawing','manual','safety','certificate','brochure','other'}
STATES={'confirmed','review','rejected'}

def setup(db):
 db.executescript('''CREATE TABLE IF NOT EXISTS reviewed_identities(offer_id INTEGER PRIMARY KEY,data TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS evidence_documents(key TEXT PRIMARY KEY,url TEXT NOT NULL UNIQUE);
 CREATE TABLE IF NOT EXISTS evidence_links(offer_id INTEGER NOT NULL,document_key TEXT NOT NULL,data TEXT NOT NULL,PRIMARY KEY(offer_id,document_key));''')

def snapshot(o):
 return {k:o.get(k) for k in ('supplier','sku','name','brand','manufacturer','model','manufacturer_part','gtin','unit','pack_quantity','identity_observed')}

def canonical_url(value):
 value=image_url(value)
 if not value:raise ValueError('Heimild þarf opinbera HTTPS-slóð.')
 p=urlsplit(value)
 return urlunsplit((p.scheme,p.netloc,p.path,p.query,''))

def document_type(title):
 t=str(title or '').lower()
 for kind,pattern in [('safety',r'safety|öryggis|sds\b'),('drawing',r'drawing|teikning|dimension'),('manual',r'manual|instructions|leiðbeining'),('certificate',r'certificate|vottun|declaration'),('brochure',r'brochure|catalog|bækling'),('datasheet',r'data.?sheet|tæknibla|gagnabla')]:
  if re.search(pattern,t):return kind
 return 'other'

def identity(o,record=None):
 raw={k:str(o.get(k) or '') for k in FIELDS}
 # Structured identity is a supplier observation, not a verified manufacturer claim.
 raw.update({k:v for k,v in (o.get('identity_observed') or {}).items() if k in FIELDS and isinstance(v,str) and v})
 result={'values':raw,'status':'review' if any(raw.values()) else 'unknown','source_url':o.get('url',''),'reason':'Auðkenni frá birgi eru óstaðfest.'}
 if record:
  result={**record,'values':dict(record['values'])}
  if record.get('snapshot')!=snapshot(o):
   result.update(status='review',reason='Birgjagögn breyttust frá staðfestingu; fyrri auðkenni varðveitt til yfirferðar.')
 return result

def load(db):
 identities={r['offer_id']:json.loads(r['data']) for r in db.execute('SELECT * FROM reviewed_identities')}
 links={}
 for r in db.execute('SELECT * FROM evidence_links'):links.setdefault(r['offer_id'],[]).append(json.loads(r['data']))
 return identities,links

def enrich(o,record=None,links=()):
 i=identity(o,record);o['identity']=i
 docs={}
 for d in o.get('documents') or []:
  try:url=canonical_url(d.get('url',''))
  except ValueError:continue
  docs[url]={**d,'url':url,'type':document_type(d.get('name')),'status':'review','scope':'unknown','source_kind':'supplier','checked_at':o.get('details_checked_at',''),'reason':'Tengill fannst hjá birgi; nákvæm gerð hefur ekki verið staðfest.'}
 for d in links:
  d=dict(d)
  if d['status']=='confirmed' and (d.get('identity_values')!=i['values'] or i['status']!='confirmed' or d.get('product_snapshot')!=snapshot(o)):
   d.update(status='review',reason='Auðkenni eða vörugögn breyttust; tenging þarf endurmat.')
  docs[d['url']]=d
 o['documents']=list(docs.values())
 return o

def find(app,oid):
 if type(oid) is not int:raise ValueError('Ógilt vöruauðkenni.')
 o=next((o for o in app.catalogue()['offers'] if o['id']==oid),None)
 if not o:raise ValueError('Vara fannst ekki.')
 return o

def short(data,key,limit=300):
 v=data.get(key,'')
 if not isinstance(v,str) or len(v)>limit:raise ValueError('Ógildur texti: '+key)
 return v.strip()

def save_identity(app,data):
 o=find(app,data.get('id'));values={k:short(data,k) for k in FIELDS};status=data.get('status','review')
 if status not in STATES:raise ValueError('Ógild staða.')
 source=canonical_url(data.get('source_url',''));note=short(data,'evidence',2000)
 if status=='confirmed' and (data.get('reviewed') is not True or not note or not values['manufacturer'] or not any(values[k] for k in ('model','manufacturer_part','gtin'))):
  raise ValueError('Staðfesting þarf framleiðanda, nákvæmt auðkenni, heimild og yfirferð útfærslu.')
 if values['gtin']:
  g=values['gtin']
  if not g.isascii() or not g.isdigit() or len(g) not in (8,12,13,14) or (10-sum(int(v)*(3 if n%2==0 else 1) for n,v in enumerate(reversed(g[:-1])))%10)%10!=int(g[-1]):raise ValueError('GTIN vartala stenst ekki.')
 value=dict(manufacturer_description=short(data,'manufacturer_description',2000),values=values,status=status,source_url=source,evidence=note,snapshot=snapshot(o),checked_at=stamp(),reason='Handvirk yfirferð auðkenna')
 with app.connect() as db:
  old=db.execute('SELECT data FROM reviewed_identities WHERE offer_id=?',(o['id'],)).fetchone();previous=json.loads(old[0]) if old else None
  if data.get('expected_at')!=(previous or {}).get('checked_at'):raise ValueError('Auðkenni breyttust eftir opnun. Opnaðu vöruna aftur.')
  db.execute('INSERT OR REPLACE INTO reviewed_identities VALUES(?,?)',(o['id'],json.dumps(value,ensure_ascii=False)))
  audit(db,o['id'],'identity',previous,value,source)
 return {'ok':True}

def save_document(app,data):
 o=find(app,data.get('id'));url=canonical_url(data.get('url',''));source=canonical_url(data.get('source_url',''))
 status=data.get('status','review');kind=data.get('type','other');scope=data.get('scope','unknown')
 if status not in STATES or kind not in TYPES or scope not in ('product','series','unknown'):raise ValueError('Ógild staða, skjalategund eða gildissvið.')
 value={k:short(data,k,2000 if k in ('evidence','coverage') else 300) for k in ('name','language','version','date','evidence','coverage','locator')}
 if not value['name']:raise ValueError('Titil skjals vantar.')
 source_kind=data.get('source_kind','other')
 if source_kind not in ('manufacturer','distributor','supplier','other'):raise ValueError('Ógild tegund heimildar.')
 i=o.get('identity',identity(o));ids=i['values']
 if status=='confirmed':
  if i['status']!='confirmed' or data.get('reviewed') is not True or scope=='unknown' or not value['evidence'] or not value['coverage']:
   raise ValueError('Staðfestu fyrst auðkenni vörunnar og yfirfarðu gerð, viðskeyti og gildissvið skjals.')
  # Reviewer must record exact identifiers seen in the document, not only a URL/title.
  if short(data,'document_manufacturer').casefold()!=ids['manufacturer'].casefold():raise ValueError('Framleiðandi skjals passar ekki við staðfest auðkenni.')
  code=short(data,'document_identifier')
  if not code or code.casefold() not in {ids[k].casefold() for k in ('model','manufacturer_part','gtin') if ids[k]}:raise ValueError('Nákvæmt auðkenni, með viðskeyti, þarf að vera skráð í skjalinu.')
  value.update(document_manufacturer=short(data,'document_manufacturer'),document_identifier=code)
 value.update(url=url,source_url=source,type=kind,status=status,scope=scope,source_kind=source_kind,identity_values=ids,product_snapshot=snapshot(o),checked_at=stamp(),reason='Handvirk yfirferð skjals; engin tæknigildi yfirfærð sjálfkrafa.')
 key=hashlib.sha256(url.encode()).hexdigest()
 with app.connect() as db:
  old=db.execute('SELECT data FROM evidence_links WHERE offer_id=? AND document_key=?',(o['id'],key)).fetchone();previous=json.loads(old[0]) if old else None
  if data.get('expected_at')!=(previous or {}).get('checked_at'):raise ValueError('Skjalatenging breyttist eftir opnun. Opnaðu vöruna aftur.')
  db.execute('INSERT OR IGNORE INTO evidence_documents VALUES(?,?)',(key,url))
  db.execute('INSERT OR REPLACE INTO evidence_links VALUES(?,?,?)',(o['id'],key,json.dumps(value,ensure_ascii=False)))
  audit(db,o['id'],'document',previous,value,source)
 return {'ok':True}

def search_plan(o):
 i=o.get('identity',identity(o));v=i['values'];code=v.get('manufacturer_part') or v.get('model') or v.get('gtin')
 if not code:return {'query':'','reason':'Nákvæmt gerðar-/vörunúmer eða GTIN vantar. Ekki leita eftir vörunúmeri birgis sem MPN.','links':[]}
 query=' '.join('"'+x.replace('"','')+'"' for x in (v.get('manufacturer') or v.get('brand'),code) if x)
 return {'query':query,'reason':'Leit er hjálpartæki; niðurstöður eru óstaðfestar. Veldu fyrst opinberan framleiðanda og skjala-/stuðningssafn hans.','links':[{'name':label,'url':'https://www.google.com/search?'+urlencode({'q':query+' '+suffix})} for label,suffix in [('Framleiðandi og stuðningssafn','manufacturer support'),('Tækniblað','datasheet filetype:pdf'),('Leiðbeiningar','manual filetype:pdf'),('Málteikning','dimensional drawing')]]}

def metrics(offers):
 # Explicitly counts supplier offers; not an invented count of canonical products.
 return {'supplier_offers':len(offers),'confirmed_identity':sum(o.get('identity',{}).get('status')=='confirmed' for o in offers),'observed_identity':sum(any(o.get('identity',{}).get('values',{}).values()) for o in offers),'reviewed_classification':sum(o.get('classification',{}).get('manual',False) and not o.get('classification',{}).get('needs_review',True) for o in offers),'classification_review':sum(o.get('classification',{}).get('needs_review',True) for o in offers),'confirmed_datasheet':sum(any(d.get('status')=='confirmed' and d.get('scope')=='product' and d.get('type')=='datasheet' for d in o.get('documents',[])) for o in offers),'document_candidates':sum(bool(o.get('documents')) for o in offers),'conflicts':sum(bool(o.get('specification_conflicts') or o.get('classification',{}).get('conflicts')) for o in offers)}

def discover(app,data,get=None):
 """Inspect a chosen manufacturer/support/distributor page; return unsaved candidates."""
 import time
 from urllib.robotparser import RobotFileParser
 from supplier_registry import fetch,website,AGENT
 from product_extras import page_details
 get=get or fetch
 o=find(app,data.get('id'));url=website(data.get('url',''))
 if not url:raise ValueError('Veldu vörusíðu eða stuðningssíðu til að skoða.')
 if urlsplit(url).path.lower().endswith('.pdf'):raise ValueError('Skráðu beinan PDF-tengil í skjalayfirferð. Hér er lesin HTML-vörusíða.')
 origin='https://'+urlsplit(url).netloc
 code,body,_=get(origin+'/robots.txt',origin)
 robot=RobotFileParser();delay=2
 if code==200:
  if body.lstrip().startswith('<'):raise ValueError('Aðgangsreglur skiluðu HTML; könnun stöðvuð.')
  robot.parse(body.splitlines());delay=max(2,robot.crawl_delay(AGENT) or 0)
  rate=robot.request_rate(AGENT)
  if rate:delay=max(delay,rate.seconds/max(1,rate.requests))
 elif code!=404:raise ValueError('Ekki tókst að kanna aðgangsreglur. HTTP '+str(code))
 if delay>10:raise ValueError('Biðreglur vefs krefjast sérstakrar tengingar.')
 def allowed(u):return code==404 or robot.can_fetch(AGENT,u)
 if not allowed(url):raise ValueError('Aðgangsreglur vefs leyfa ekki lestur síðunnar.')
 time.sleep(delay)
 status,body,final=get(url,origin,allowed) if get is fetch else get(url,origin)
 if status!=200:raise ValueError('Ekki tókst að sækja síðu. HTTP '+str(status))
 if '<html' not in body.lower() and '<a ' not in body.lower():raise ValueError('Síðan skilaði ekki læsilegu HTML; ekkert skjal staðfest.')
 result=page_details(body,final)
 return {'source_url':final,'checked_at':stamp(),'identity_observed':result.get('identity_observed',{}),'documents':[{**d,'type':document_type(d['name']),'status':'review','scope':'unknown'} for d in result['documents']], 'note':'Óvistuð leitardrög. Tenglar geta átt við aðrar gerðir; yfirfarðu skjal áður en það er tengt.'}
