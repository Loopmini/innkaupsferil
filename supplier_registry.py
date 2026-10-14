"""Supplier address book and bounded, public catalogue discovery."""
import ipaddress,json,re,socket,ssl,http.client,threading,time
from contextlib import closing
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit,urlunsplit,urljoin
from urllib.robotparser import RobotFileParser
from uuid import uuid4
import xml.etree.ElementTree as ET

PROBE_LOCK=threading.Lock()
AGENT='NjordurCatalogueCheck/1.0'

def setup(db):
 db.execute('CREATE TABLE IF NOT EXISTS supplier_profiles(id TEXT PRIMARY KEY,name_key TEXT UNIQUE NOT NULL,catalogue_name TEXT NOT NULL DEFAULT \'\',data TEXT NOT NULL)')
 db.execute("CREATE UNIQUE INDEX IF NOT EXISTS supplier_profile_catalogue ON supplier_profiles(catalogue_name) WHERE catalogue_name<>''")

def clean(value,limit=300):
 if not isinstance(value,str) or len(value)>limit:raise ValueError('Ógildur eða of langur textareitur.')
 return value.strip()

def website(value):
 value=clean(value,2000)
 if not value:return ''
 if '://' not in value:value='https://'+value
 p=urlsplit(value)
 if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443):raise ValueError('Notaðu opinbera HTTPS-slóð án innskráningarupplýsinga.')
 host=p.hostname.encode('idna').decode('ascii').lower()
 if host=='localhost' or host.endswith(('.local','.localhost')):raise ValueError('Slóð þarf að vera á opinberum vef.')
 try:
  if not ipaddress.ip_address(host).is_global:raise ValueError('Slóð þarf að vera á opinberum vef.')
 except ValueError as e:
  if ':' in host or re.fullmatch(r'[\d.]+',host):raise ValueError('Slóð þarf að vera á opinberum vef.') from e
 return urlunsplit(('https',host,p.path or '/',p.query,''))

def email(value):
 value=clean(value,254)
 if value and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):raise ValueError('Ógilt netfang.')
 return value

def known(app):
 from market_sync import SOURCES
 result={n:'' for n in app.SUPPLIERS}
 result.update({n:url+'/' for n,url in SOURCES.values()})
 with closing(app.connect()) as db:
  for row in db.execute('SELECT DISTINCT supplier FROM offers'):result.setdefault(row[0],'')
 return result

def listing(app):
 names=known(app)
 with closing(app.connect()) as db:rows=[json.loads(r['data']) for r in db.execute('SELECT data FROM supplier_profiles')]
 linked={r.get('catalogue_name') or r['name'] for r in rows}
 rows.extend({'id':None,'name':n,'catalogue_name':n,'website':url,'contacts':[]} for n,url in names.items() if n not in linked)
 return sorted(rows,key=lambda r:r['name'].casefold())

def save(app,data):
 raw=data.get('supplier')
 if not isinstance(raw,dict):raise ValueError('Birgjaupplýsingar vantar.')
 name=clean(raw.get('name',''),180)
 if not name:raise ValueError('Nafn birgja vantar.')
 contacts=raw.get('contacts',[])
 if not isinstance(contacts,list) or len(contacts)>50:raise ValueError('Hámark 50 tengiliðir.')
 value={k:clean(raw.get(k,''),limit) for k,limit in [('address',300),('postal_code',30),('city',120),('country',120),('registration_number',40),('phone',60),('notes',3000)]}
 value.update(name=name,website=website(raw.get('website','')),email=email(raw.get('email','')),contacts=[])
 for c in contacts:
  if not isinstance(c,dict):raise ValueError('Ógildur tengiliður.')
  contact={k:clean(c.get(k,''),limit) for k,limit in [('name',180),('role',180),('phone',60),('notes',1000)]}
  contact['email']=email(c.get('email',''))
  if not contact['name']:raise ValueError('Nafn tengiliðar vantar.')
  value['contacts'].append(contact)
 names=known(app);requested=raw.get('id');key=' '.join(name.casefold().split())
 with closing(app.connect()) as db,db:
  old=db.execute('SELECT * FROM supplier_profiles WHERE id=?',(requested,)).fetchone() if requested else None
  if requested and not old:raise ValueError('Birgir fannst ekki; endurlesið skrána.')
  duplicate=db.execute('SELECT id FROM supplier_profiles WHERE name_key=?',(key,)).fetchone()
  if duplicate and duplicate[0]!=requested:raise ValueError('Birgir með þessu nafni er þegar skráður. Opnaðu hann til breytinga.')
  catalogue_name=old['catalogue_name'] if old else next((n for n in names if n.casefold()==name.casefold()),'')
  if not old and raw.get('catalogue_name'):
   if raw['catalogue_name'] not in names:raise ValueError('Óþekktur birgir í vörugrunni.')
   catalogue_name=raw['catalogue_name']
  if catalogue_name and db.execute('SELECT 1 FROM supplier_profiles WHERE catalogue_name=? AND id<>?',(catalogue_name,requested or '')).fetchone():raise ValueError('Upplýsingar þessa birgja eru þegar skráðar.')
  if value['website']:
   host=urlsplit(value['website']).hostname
   for r in db.execute('SELECT id,data FROM supplier_profiles'):
    if r['id']!=requested and urlsplit(json.loads(r['data']).get('website','')).hostname==host:raise ValueError('Þessi vefur er þegar tengdur öðrum skráðum birgi.')
  value.update(id=requested or uuid4().hex,catalogue_name=catalogue_name,updated_at=datetime.now(timezone.utc).isoformat())
  if old:
   previous=json.loads(old['data'])
   if previous.get('website')==value['website'] and previous.get('discovery'):value['discovery']=previous['discovery']
  db.execute('INSERT INTO supplier_profiles VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET name_key=excluded.name_key,data=excluded.data',(value['id'],key,catalogue_name,json.dumps(value,ensure_ascii=False)))
 return value

class PublicHTTPS(http.client.HTTPSConnection):
 def connect(self):
  addresses=socket.getaddrinfo(self.host,443,type=socket.SOCK_STREAM)
  if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise ValueError('Vefslóð vísar ekki eingöngu á opinber netföng.')
  # Pin the validated address for this connection; retain hostname for TLS verification.
  raw=socket.create_connection((addresses[0][4][0],443),self.timeout)
  try:self.sock=ssl.create_default_context().wrap_socket(raw,server_hostname=self.host)
  except Exception:raw.close();raise

def fetch(url,origin,allowed=None):
 for _ in range(3):
  url=website(url);p=urlsplit(url)
  if allowed and not allowed(url):raise ValueError('Aðgangsreglur vefs leyfa ekki þessa slóð.')
  if p.hostname!=urlsplit(origin).hostname:raise ValueError('Tilvísun á annan vef; skráðu lokaslóð birgis sérstaklega.')
  with closing(PublicHTTPS(p.hostname,timeout=8)) as con:
   con.request('GET',urlunsplit(('','',p.path or '/',p.query,'')),headers={'User-Agent':AGENT,'Accept-Encoding':'identity'})
   response=con.getresponse()
   if response.status in (301,302,303,307,308):
    url=urljoin(url,response.getheader('Location',''));continue
   raw=response.read(2_000_001)
   if len(raw)>2_000_000:raise ValueError('Svar yfir 2 MB; þarf sértengingu fyrir stóra skrá.')
   return response.status,raw.decode('utf-8',errors='replace'),url
 raise ValueError('Of margar tilvísanir.')

class Links(HTMLParser):
 def __init__(self):super().__init__();self.urls=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a' and a.get('href'):self.urls.append(a['href'])

def inspect(url,get=fetch):
 url=website(url)
 if not url:raise ValueError('Vefslóð vantar.')
 p=urlsplit(url);origin='https://'+p.netloc
 report={'checked_at':datetime.now(timezone.utc).isoformat(),'website':url,'findings':[],'status':'unknown','note':'Afmörkuð könnun; ekki staðfest að vöruskrá sé tæmandi eða að innlestur virki.'}
 code,body,_=get(origin+'/robots.txt',origin)
 if code in (401,403,429):return {**report,'status':'blocked','note':f'Aðgangi hafnað ({code}); engar frekari beiðnir gerðar.'}
 robot=RobotFileParser();delay=2
 if code==200:
  if body.lstrip().startswith('<'):return {**report,'note':'robots.txt skilar HTML. Þarfnast yfirferðar; könnun stöðvuð.'}
  robot.parse(body.splitlines());delay=max(2,robot.crawl_delay(AGENT) or 0)
  rate=robot.request_rate(AGENT)
  if rate:delay=max(delay,rate.seconds/max(1,rate.requests))
  if delay>10:return {**report,'note':'Biðreglur vefs krefjast sértengingar; könnun stöðvuð.'}
 elif code!=404:return {**report,'note':f'Ekki tókst að athuga aðgangsreglur (HTTP {code}).'}
 def allowed(u):return code==404 or robot.can_fetch(AGENT,u)
 # Only three further public reads; supplier/contact data are never sent.
 targets=[('website',url),('sitemap',(robot.site_maps() or [origin+'/sitemap.xml'])[0]),('api',origin+'/wp-json/wc/store/v1/products?per_page=1')]
 for kind,target in targets:
  if urlsplit(target).hostname!=p.hostname or not allowed(target):
   report['findings'].append({'kind':kind,'url':target if urlsplit(target).hostname==p.hostname else origin,'status':'not_checked','detail':'Ekki kannað vegna aðgangsreglna eða annars léns.'});continue
  time.sleep(delay)
  status,text,final=fetch(target,origin,allowed) if get is fetch else get(target,origin)
  if status in (401,403,429):
   report['findings'].append({'kind':kind,'url':target,'status':'blocked','detail':f'Aðgangi hafnað ({status}).'});report['status']='blocked';break
  if status!=200:continue
  if kind=='website':
   links=Links();links.feed(text)
   for href in links.urls:
    try:candidate=website(urljoin(final,href))
    except ValueError:continue
    if urlsplit(candidate).hostname!=p.hostname:continue
    if re.search(r'\.(csv|xlsx?|xml|pdf)$',urlsplit(candidate).path,re.I):
     report['findings'].append({'kind':'file','url':candidate,'status':'candidate','detail':'Skjalatengill fannst; innihald og hvort þetta sé vöruskrá er óstaðfest.'})
     if len(report['findings'])>=20:break
  elif kind=='sitemap':
   try:
    root=ET.fromstring(text);tag=root.tag.rsplit('}',1)[-1]
    if tag in ('urlset','sitemapindex'):report['findings'].append({'kind':'sitemap','url':final,'status':'detected','detail':f'Síðukort fannst ({tag}); þarf að greina hvaða slóðir eru vörur.'})
   except ET.ParseError:pass
  else:
   try:
    rows=json.loads(text)
    if isinstance(rows,list) and rows and isinstance(rows[0],dict) and rows[0].get('id') and rows[0].get('name'):
     report['findings'].append({'kind':'api','url':final,'status':'detected','detail':'Opinbert WooCommerce-vöruviðmót svaraði með vörudæmi; verðgrunnur og heildarþekja óstaðfest.'})
   except (ValueError,TypeError):pass
 if report['status']!='blocked':report['status']='possible' if any(f['status']=='detected' for f in report['findings']) else 'unknown'
 return report

def probe(app,data):
 if not PROBE_LOCK.acquire(blocking=False):raise ValueError('Önnur birgjakönnun er í gangi.')
 try:
  with closing(app.connect()) as db:row=db.execute('SELECT data FROM supplier_profiles WHERE id=?',(data.get('id'),)).fetchone()
  if not row:raise ValueError('Vistaðu birgjann fyrst.')
  supplier=json.loads(row[0]);url=supplier.get('website','')
  try:report=inspect(url)
  except (OSError,ValueError,http.client.HTTPException) as e:report={'status':'error','checked_at':datetime.now(timezone.utc).isoformat(),'website':url,'findings':[],'note':str(e)[:350]}
  with closing(app.connect()) as db,db:
   current=db.execute('SELECT data FROM supplier_profiles WHERE id=?',(supplier['id'],)).fetchone()
   if not current:raise ValueError('Birgjaskrá breyttist meðan könnun stóð yfir. Endurlesið skrána.')
   value=json.loads(current[0])
   if value.get('website')!=url:raise ValueError('Slóð breyttist meðan könnun stóð yfir. Keyrðu könnun aftur.')
   value['discovery']=report;db.execute('UPDATE supplier_profiles SET data=? WHERE id=?',(json.dumps(value,ensure_ascii=False),supplier['id']))
  return report
 finally:PROBE_LOCK.release()
