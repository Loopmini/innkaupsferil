"""Public catalogue discovery and resumable refresh. No credentials or private data."""
import argparse
import concurrent.futures
import html
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import time
import threading
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import urlsplit, urljoin, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

ROOT=Path(__file__).parent
AGENT='Innkaupsferil/0.3 (public catalogue reader)'
HOSTS={'thor.is','www.husa.is','byko.is','www.sindri.is','www.fossberg.is','www.isol.is'}
SOURCES={'thor':('Þór hf.','https://thor.is'),'husa':('Húsasmiðjan','https://www.husa.is'),'byko':('BYKO','https://byko.is'),'sindri':('Sindri','https://www.sindri.is'),'fossberg':('Fossberg','https://www.fossberg.is'),'isol':('Ísól','https://www.isol.is')}

SOURCES.update({'rubix':('Rúbix','https://rubix.is'),'vatnsvirkinn':('Vatnsvirkinn','https://vatnsvirkinn.is'),'vatnogveitur':('Vatn og veitur','https://www.vatnogveitur.is'),'ronning':('Röning','https://www.ronning.is'),'iskraft':('Ískraft','https://iskraft.husa.is'),'reykjafell':('Reykjafell','https://www.reykjafell.is'),'hampidjan':('Hampiðjan','https://verslun.hampidjan.is'),'isfell':('Ísfell','https://isfell.is'),'landvelar':('Landvélar','https://landvelar.is'),'barki':('Barki','https://www.barki.is'),'wurth':('Würth','https://wurth.is')})
SOURCES['tengi']=('Tengi','https://www.tengi.is')
SOURCES['dynjandi']=('Dynjandi','https://www.dynjandi.is')
HOSTS.update(urlsplit(origin).hostname for _,origin in SOURCES.values())

def now():return datetime.now(timezone.utc).isoformat()
def plain(s):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',str(s or '')))).strip()
def atomic(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8');os.replace(temp,path)
def load(path,default):return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def process_alive(pid):
 if pid<=0:return False
 if os.name=='nt':
  import ctypes
  kernel=ctypes.windll.kernel32
  kernel.OpenProcess.restype=ctypes.c_void_p
  kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
  kernel.CloseHandle.argtypes=[ctypes.c_void_p]
  handle=kernel.OpenProcess(0x1000,False,pid)
  if not handle:return kernel.GetLastError()==5
  code=ctypes.c_ulong()
  try:return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(code))) and code.value==259
  finally:kernel.CloseHandle(handle)
 try:os.kill(pid,0);return True
 except ProcessLookupError:return False
 except PermissionError:return True

def is_running(lock):
 if not lock.exists():return False
 try:return process_alive(int(lock.read_text()))
 except (ValueError,OSError):return time.time()-lock.stat().st_mtime<60

class Redirect(HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  target=urlsplit(newurl)
  if target.scheme!='https' or target.hostname!=urlsplit(req.full_url).hostname or target.port not in (None,443) or target.username:
   raise ValueError('Redirect leaves approved origin')
  return super().redirect_request(req,fp,code,msg,headers,newurl)

class Client:
 def __init__(self,origin):
  self.origin=origin;self.last=0;self.delay=2;self.robot=None;self.robot_status=''
  try:
   body,_=self.raw(origin+'/robots.txt',limit=250000)
   if body.lstrip().startswith('<'):raise ValueError('robots.txt returns HTML; manual review required')
   self.robot=RobotFileParser();self.robot.parse(body.splitlines())
   self.delay=max(2,self.robot.crawl_delay(AGENT) or 0)
   rate=self.robot.request_rate(AGENT)
   if rate:self.delay=max(self.delay,rate.seconds/max(rate.requests,1))
   if self.delay>60:raise ValueError('Crawl delay above supported limit')
   self.robot_status='robots.txt checked'
  except HTTPError as e:
   if e.code==404:self.robot_status='robots.txt absent (404)'
   else:raise
 def raw(self,url,limit=15000000):
  p=urlsplit(url)
  if p.scheme!='https' or p.hostname not in HOSTS or p.hostname!=urlsplit(self.origin).hostname or p.port not in (None,443) or p.username or p.password:raise ValueError('Unapproved URL')
  time.sleep(max(0,self.delay-(time.monotonic()-self.last)))
  self.last=time.monotonic()
  encoded=quote(url,safe=":/?&=%#@!$'()*+,;[]~")
  with build_opener(Redirect()).open(Request(encoded,headers={'User-Agent':AGENT,'Accept-Encoding':'identity'}),timeout=30) as response:
   body=response.read(limit+1)
   if len(body)>limit:raise ValueError('Response limit exceeded')
   return body.decode('utf-8',errors='replace'),dict(response.headers)
 def get(self,url,limit=15000000):
  if self.robot and not self.robot.can_fetch(AGENT,url):raise ValueError('robots.txt disallows URL')
  try:return self.raw(url,limit)
  except HTTPError as e:
   if e.code not in (502,503,504):raise
   return self.raw(url,limit)

def base(key,supplier,name,url,sku='',category='',subcategory=''):
 return dict(key=key,supplier=supplier,name=plain(name),url=url,sku=str(sku or ''),category=category,subcategory=subcategory,brand='',price=None,currency='ISK',vat_included=None,vat_rate=None,pack_quantity=None,unit='',observed_at=now(),availability='Lagerstaða óstaðfest',price_status='Verð vantar',note='',collector='v0.3')

def pack(row,text):
 # Only explicit quantities, never infer all packs contain one item.
 m=re.search(r'(?i)(\d+)\s*(?:stk\b|stykki\b)',text)
 if m and int(m[1])>0:row.update(pack_quantity=int(m[1]),unit='stk')

def parse_thor(p):
 if not isinstance(p,dict) or not p.get('id') or not p.get('name') or not p.get('permalink'):raise ValueError('Invalid Store API product')
 cats=p.get('categories') or []
 r=base('thor-api-'+str(p['id']),'Þór hf.',p['name'],p['permalink'],p.get('sku'),plain(cats[0]['name']) if cats else '', ' / '.join(plain(c['name']) for c in cats))
 prices=p.get('prices') or {};r['currency']=prices.get('currency_code') or 'ISK'
 price=prices.get('price');minor=prices.get('currency_minor_unit')
 if p.get('type') in ('simple','variation') and prices.get('price_range') is None and price not in (None,''):
  if not isinstance(minor,int) or not 0<=minor<=4:raise ValueError('Invalid currency precision')
  value=float(price)/(10**minor)
  if not math.isfinite(value) or value<0:raise ValueError('Invalid price')
  if value>0:r.update(price=value,price_status='Birt vefverð; VSK óstaðfest')
  else:r['price_status']='Núllverð frá birgi; þarf staðfestingu'
 else:r['price_status']='Afbrigði/verðbil; velja þarf stærð hjá birgi'
 pack(r,r['name'])
 r['availability']='Til samkvæmt birgjaviðmóti' if p.get('is_in_stock') else 'Ekki á lager samkvæmt birgjaviðmóti'
 r['note']='Opinbert Store API. Verð nær til sölueiningar; pakkastærð og VSK eru ekki áætluð. '+('Afbrigðisvara; grunnverð ekki notað sem verð afbrigðis.' if p.get('type')=='variable' else '')
 from product_extras import image_url
 r['image_url']=next((u for img in p.get('images',[]) if isinstance(img,dict) and (u:=image_url(img.get('src','')))), '')
 from product_extras import page_details
 r['documents']=page_details((p.get('description') or '')+' '+(p.get('short_description') or ''),r['url'])['documents']
 r['description']=plain(p.get('short_description') or p.get('description'))[:8000]
 r['supplier_categories']=[plain(c.get('name')) for c in cats if c.get('name')]
 r['product_type']=p.get('type','')
 return r

def parse_husa(body,url):
 sku=re.search(r'<span[^>]*class=["\'][^"\']*\bmain-sku\b[^"\']*["\'][^>]*>(.*?)</span>',body,re.S|re.I)
 if not sku:return None
 # Product title and price are scoped after the main SKU, excluding navigation/catalogue cards.
 region=body[sku.end():]
 title=re.search(r'<h2[^>]*>(.*?)</h2>',region,re.S|re.I)
 if not title:return None
 name=plain(title[1]);r=base('husa-'+plain(sku[1]),'Húsasmiðjan',name,url,plain(sku[1]),' / '.join(urlsplit(url).path.strip('/').split('/')[:2]))
 price=re.search(r'<div[^>]*class=["\']main-price["\'][^>]*>\s*<span[^>]*class=["\']price-wrapper["\'][^>]*>\s*([\d.]+(?:,\d+)?)\s*<span[^>]*class=["\']unit["\'][^>]*>\s*kr\.',region,re.S|re.I)
 if price:
  value=float(price[1].replace('.','').replace(',','.'))
  if value>0:r.update(price=value,vat_included=True,price_status='Birt vefverð með VSK; skatthlutfall óstaðfest')
 from product_extras import page_image
 r['image_url']=page_image(body,url)
 pack(r,name)
 r['availability']='Ekki til á vef samkvæmt birgi' if 'Ekki til á vef' in plain(region) else 'Lagerstaða þarf staðfestingu hjá birgi'
 r['note']='Vörusíða lesin sjálfvirkt. VSK innifalinn samkvæmt söluskilmálum; skatthlutfall og magn einingar eru ekki áætluð.'
 return r

def inspect_index(client,urls):
 """Compare complete discovered URL sets, never infer product deletion."""
 record=getattr(client,'record_index',None)
 return record(urls) if callable(record) else {}

def thor(client,previous,state,progress):
 records={};total=None;pages=1;page=1
 while page<=pages:
  body,headers=client.get(f'https://thor.is/wp-json/wc/store/v1/products?per_page=100&page={page}&orderby=id&order=asc')
  data=json.loads(body)
  if not isinstance(data,list):raise ValueError('Store API did not return a list')
  if page==1:
   total=int(next((v for k,v in headers.items() if k.lower()=='x-wp-total'),len(data)))
   pages=int(next((v for k,v in headers.items() if k.lower()=='x-wp-totalpages'),1))
   if pages>500:raise ValueError('Unexpectedly large catalogue')
  for p in data:
   r=parse_thor(p);records[r['key']]=r
  progress(dict(stage=f'Síða {page}/{pages}',loaded=len(records),expected=total,work_done=page,work_total=pages))
  page+=1
 if len(records)!=total:raise ValueError(f'Incomplete API traversal: {len(records)}/{total}; previous snapshot retained')
 # API covers public parent products; variable child selections are not separate prices.
 return list(records.values()),dict(status='ok',scope='Allar færslur sem opinbert Store API skilaði; afbrigðaverð ekki öll sérgreind',loaded=len(records),expected=total,checked_at=now(),robots=client.robot_status)

def husa(client,previous,state,progress,budget):
 body,_=client.get('https://www.husa.is/sitemap.xml',limit=40000000)
 root=ET.fromstring(body)
 urls=sorted(set(e.text for e in root.iter() if e.tag.endswith('}loc') and e.text and urlsplit(e.text).hostname=='www.husa.is' and len(urlsplit(e.text).path.strip('/').split('/'))>=4))
 # Prioritize drills initially, then rotate through every candidate without claiming each URL is a product.
 urls.sort(key=lambda u:(0 if '/borar-og-borasett/' in u else 1,u))
 if not urls:raise ValueError('No sitemap candidates')
 index=inspect_index(client,urls)
 if getattr(client,'index_only',False) is True:return previous,{**state,'status':'partial','error':None,'loaded':len(previous),'index':index,'index_check':'Síðukort skoðað; verð og vörusíður ekki endurlesin'}
 cursor=int(state.get('cursor',0))%len(urls);records={r['key']:r for r in previous};errors=[];checked=0
 stale=sorted([r for r in previous if (datetime.now(timezone.utc)-datetime.fromisoformat(r['observed_at'])).total_seconds()>86400],key=lambda r:r['observed_at'])[:min(50,budget)]
 work_total=len(stale)+min(budget,len(urls));work_done=0
 for old in stale:
  try:
   page,_=client.get(old['url']);fresh=parse_husa(page,old['url'])
   if fresh:records[fresh['key']]=fresh
  except HTTPError as e:
   if e.code in (401,403,429):raise
   errors.append(dict(url=old['url'],error=str(e)))
  except (ValueError,TimeoutError) as e:errors.append(dict(url=old['url'],error=str(e)))
  work_done+=1;progress(dict(stage='Endurskoðar eldri vörur',work_done=work_done,work_total=work_total,loaded=len(records)))
 for n in range(min(budget,len(urls))):
  url=urls[(cursor+n)%len(urls)]
  try:
   page,_=client.get(url);r=parse_husa(page,url)
   if r:records[r['key']]=r
  except HTTPError as e:
   if e.code in (401,403,429):raise
   errors.append(dict(url=url,error=str(e)))
  except (ValueError,TimeoutError) as e:errors.append(dict(url=url,error=str(e)))
  checked+=1;work_done+=1;progress(dict(stage=f'Vörusíða {checked}/{min(budget,len(urls))}',loaded=len(records),expected=len(urls),work_done=work_done,work_total=work_total,scan_done=checked,scan_total=len(urls)))
 return list(records.values()),dict(status='partial',scope='Síðukort í lotum; ekki allar slóðir eru vörur',loaded=len(records),expected=len(urls),index=index,cursor=(cursor+checked)%len(urls),checked_this_run=checked,errors=errors[:30],checked_at=now(),robots=client.robot_status)

def run(root=ROOT,husa_limit=100,selected=None,index_only=False):
 directory=root/'data';directory.mkdir(exist_ok=True)
 lock=directory/'market-sync.lock'
 if lock.exists() and not is_running(lock):lock.unlink(missing_ok=True)
 try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
 except FileExistsError:raise RuntimeError('Önnur uppfærsla er í gangi.')
 os.write(fd,str(os.getpid()).encode());os.close(fd)
 old=load(directory/'market-live.json',{'products':[],'meta':{}})
 statuses=load(directory/'market-status.json',{'sources':{}}).get('sources',{})
 indexes=load(directory/'market-index.json',{})
 results={};started=now();chosen=selected or list(SOURCES)
 guard=threading.Lock();completed=[]
 runtime={k:{'phase':'queued','updated_at':started} for k in chosen}
 def snapshot(**extra):
  atomic(directory/'market-status.json',{'running':True,'started_at':started,'selected':chosen,
      'completed':completed.copy(),'runtime':runtime,'sources':statuses,**extra})
 def progress(source,info):
  with guard:
   runtime[source].update(info,phase='running',updated_at=now())
   snapshot()

 def record_index(key,urls):
  current=sorted(set(urls));previous=indexes.get(key)
  summary={'checked_at':now(),'total':len(current),'baseline':previous is None,
    'added':None if previous is None else len(set(current)-set(previous['urls'])),
    'missing':None if previous is None else len(set(previous['urls'])-set(current))}
  with guard:indexes[key]={'urls':current,'checked_at':summary['checked_at']}
  return summary
 def worker(key):
  supplier,origin=SOURCES[key];previous=[r for r in old['products'] if r['supplier']==supplier]
  try:
   if index_only and key not in ('husa','rubix','isfell','barki','wurth'):
    return key,(previous,{**statuses.get(key,{}),'status':statuses.get(key,{}).get('status','not_connected'),'loaded':len(previous),'index_check':'Hraðskoðun síðukorts ekki útfærð fyrir þennan birgi'})
   progress(key,{'stage':'Tengist birgi og athugar aðgang','started_at':now()})
   c=Client(origin)
   c.index_only=index_only;c.record_index=lambda urls:record_index(key,urls)
   if key=='thor':return key,thor(c,previous,statuses.get(key,{}),lambda i:progress(key,i))
   if key=='husa':return key,husa(c,previous,statuses.get(key,{}),lambda i:progress(key,i),husa_limit)
   from supplier_catalogues import DIRECTORIES, collect
   if key in DIRECTORIES or key in ('landvelar','dynjandi','tengi'):return key,collect(key,supplier,c,previous,statuses.get(key,{}),lambda i:progress(key,i))
   return key,(previous,dict(status='not_connected',scope='Sérstök vörutenging ekki tilbúin',loaded=len(previous),checked_at=now()))
  except Exception as e:
   return key,(previous,{**statuses.get(key,{}),'status':'blocked' if isinstance(e,HTTPError) and e.code in (401,403,429) else 'error','error':str(e),'loaded':len(previous),'checked_at':now(),'scope':'Fyrri athuganir varðveittar; engin fersk uppfærsla'})
 try:
  snapshot()
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   futures=[pool.submit(worker,key) for key in chosen]
   for future in concurrent.futures.as_completed(futures):
    key,(rows,status)=future.result()
    previous={r['key']:r for r in old['products'] if r['supplier']==SOURCES[key][0]}
    added=sum(r['key'] not in previous for r in rows)
    changed=sum(r['key'] in previous and any(v!=previous[r['key']].get(k) for k,v in r.items() if k!='observed_at') for r in rows)
    with guard:
     results[key]=rows;statuses[key]=status;completed.append(key)
     runtime[key].update(phase=status['status'],updated_at=now(),new_products=added,changed_products=changed,
                         loaded=status.get('loaded',len(rows)),stage='Lota lesin; bíður vistunar')
     snapshot()
  with guard:snapshot(phase='saving')
  products=[r for r in old['products'] if r['supplier'] not in {SOURCES[k][0] for k in chosen}]
  for rows in results.values():products.extend(rows)
  payload={'meta':{'checked_at':now(),'scope':'Sjálfvirkar opinberar athuganir. Þekja og síðasta árangursríka söfnun eru mismunandi eftir birgjum. Ekki tæmandi markaðsskrá.'},'products':products}
  # Public price observations only; append on price/availability change, never rewrite old observations.
  with sqlite3.connect(directory/'market-history.sqlite') as db:
   db.execute('CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY, product_key TEXT, observed_at TEXT, price REAL, currency TEXT, availability TEXT)')
   for r in products:
    prev=db.execute('SELECT price,currency,availability FROM observations WHERE product_key=? ORDER BY id DESC LIMIT 1',(r['key'],)).fetchone()
    current=(r['price'],r['currency'],r['availability'])
    if prev!=current:db.execute('INSERT INTO observations(product_key,observed_at,price,currency,availability) VALUES(?,?,?,?,?)',(r['key'],r['observed_at'],*current))
  atomic(directory/'market-live.json',payload)
  atomic(directory/'market-index.json',indexes)
  result={'running':False,'started_at':started,'finished_at':now(),'sources':statuses,'loaded':len(products),'selected':chosen,'completed':completed,'runtime':runtime,'phase':'saved'}
  atomic(directory/'market-status.json',result)
  return result
 except Exception:
  with guard:snapshot(running=False,phase='error',finished_at=now(),error='Vistun eða keyrsla mistókst. Skoðaðu fyrri gögn áður en þú reynir aftur.')
  raise
 finally:lock.unlink(missing_ok=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--husa-limit',type=int,default=100);p.add_argument('--sources',nargs='+',choices=list(SOURCES));a=p.parse_args()
 if not 1<=a.husa_limit<=5000:p.error('husa-limit must be 1..5000')
 print(json.dumps(run(husa_limit=a.husa_limit,selected=a.sources),ensure_ascii=False),flush=True)
