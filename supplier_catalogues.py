"""Public product directories. Catalogue presence is not a price or stock claim."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, unquote, urljoin
from urllib.error import HTTPError
from market_sync import base, plain, now, parse_husa, parse_thor

DIRECTORIES = {
 'rubix': ('/sitemap/1.xml', '/vorur/'),
 'iskraft': ('/sitemap.xml', None),
 'isfell': ('/sitemap-custom-posts.xml', '/vorur/'),
 'barki': ('/store-products-sitemap.xml', '/vorur/'),
 'hampidjan': ('/sitemap.xml', '/vara/'),
 'wurth': ('/products.xml', None),
}

def sitemap_urls(body):
 root=ET.fromstring(body)
 return [e.text.strip() for item in root for e in item if e.tag.rsplit('}',1)[-1]=='loc' and e.text]

def parse_directory(key,supplier,body,url):
 if key=='iskraft':
  r=parse_husa(body,url)
  if r:
   r.update(key='iskraft-'+r['sku'],supplier=supplier,price=None,vat_included=None,vat_rate=None,
            price_status='Verð ekki innlesið; innskráning hjá birgi',note='Opinber vöruskrá. Verð og lagerstaða ekki staðfest.')
  return r
 titles=list(re.finditer(r'<h1\b[^>]*>(.*?)</h1>',body,re.S|re.I))
 title=next((m for m in titles if not any(w in plain(m[1]).lower() for w in ('vafrakök','cookie'))),None)
 if not title or not plain(title[1]):return None
 name=plain(title[1])
 if name.lower() in ('page not found','404','vara fannst ekki','innskráning','síðan fannst ekki.'):return None
 sku=''
 # Only explicit product identifiers. No IDs inferred from a descriptive URL.
 if key=='rubix':sku=unquote(urlsplit(url).path.split('/')[-1])
 if key=='barki':
  m=re.search(r'VNR:\s*([^<\n]+)',body,re.I)
  if m:sku=plain(m[1])
  if 'X' in sku.upper():sku=''  # Family code is not an orderable SKU.
 if key=='wurth':
  m=re.search(r'<[^>]+id=["\']sku-[^"\']+["\'][^>]*>(.*?)</[^>]+>',body,re.S|re.I)
  if m:sku=plain(m[1])
 if key=='hampidjan':
  m=re.search(r'Vörunúmer:\s*</[^>]+>\s*<[^>]+>(.*?)</',body,re.S|re.I)
  if m:sku=plain(m[1])
 r=base(key+'-directory-'+hashlib.sha256(url.encode()).hexdigest()[:20],supplier,name,url,sku)
 r.update(price_status='Verð ekki innlesið',availability='Vara í vöruskrá; lagerstaða óstaðfest',
          note='Vöruskrá lesin án verðtengingar. Færsla getur verið vörufjölskylda; stærð, afbrigði og kaupverð þarf að staðfesta.',collector='v0.4',catalogue_only=True)
 if key=='rubix':
  price=re.search(r'<p[^>]*class="[^"]*text-title-l[^"\n]*"[^>]*>(.*?)</p>',body[title.end():title.end()+3000].split('<h2',1)[0],re.S)
  if price:
   text=plain(price[1])
   amount=re.fullmatch(r'([\d.]+(?:,\d+)?)\s*kr\.',text)
   if amount:
    value=float(amount[1].replace('.','').replace(',','.'))
    if value>0:r.update(price=value,price_status='Birt vefverð; VSK og sölueining óstaðfest',catalogue_only=False,note='Verð úr aðalverðreit vörusíðu. Afbrigði, pakkning og VSK þarf að staðfesta.')
   elif 'frá' in text.lower():r['price_status']='Frá-verð afbrigða; nákvæmt verð vantar'
 return r

def collect(key,supplier,client,previous,state,progress,budget=25):
 records={r['key']:r for r in previous}
 if key=='iskraft':
  # Public sitemap currently lists company pages, not the actual product catalogue.
  # Keep the one verified direct product route until a catalogue feed is available.
  url=client.origin+'/strengir/idrattar-og-tofluvir/tofluvir/tofluvir-h07v-k-15-mm2-grar-100m/'
  body,_=client.get(url);r=parse_directory(key,supplier,body,url)
  if not r:raise ValueError('Verified product route did not expose product identity')
  records[r['key']]=r
  return list(records.values()),dict(status='partial',scope='Ein staðfest vöruslóð; heildarvörutenging ólokið. Verð ekki innlesið.',loaded=len(records),checked_at=now())
 if key=='hampidjan':
  page=int(state.get('next_page',1))
  body,_=client.get(client.origin+f'/vorur?page={page}')
  cards=re.findall(r'<article\b[^>]*class="single-article-product[^"\n]*"[^>]*>(.*?)</article>',body,re.S)
  urls=[urljoin(client.origin,m[1]) for card in cards if (m:=re.search(r'<a[^>]+href="([^"]+)"',card))]
  if not urls:raise ValueError('No product cards; previous catalogue retained')
  for url in urls:
   content,_=client.get(url);r=parse_directory(key,supplier,content,url)
   if r:records[r['key']]=r
  nxt='id="pagination--next"' in body
  return list(records.values()),dict(status='partial',scope='Vöruskrá í 20 færslu lotum; verð ekki innlesin',loaded=len(records),next_page=page+1 if nxt else 1,checked_at=now())
 if key=='landvelar':
  page=int(state.get('next_page',1))
  body,headers=client.get(client.origin+f'/wp-json/wc/store/v1/products?per_page=100&page={page}&orderby=id&order=asc')
  rows=json.loads(body)
  if not isinstance(rows,list):raise ValueError('Product API did not return a list')
  pages=int(next((v for k,v in headers.items() if k.lower()=='x-wp-totalpages'),1))
  total=int(next((v for k,v in headers.items() if k.lower()=='x-wp-total'),len(rows)))
  for p in rows:
   r=parse_thor(p);r.update(key='landvelar-api-'+str(p['id']),supplier=supplier,collector='v0.4')
   # Public zero prices are not free products. No signed-in prices are accessed.
   if r['price'] is None:r['price_status']='Verð vantar; óska eftir verði hjá birgi'
   records[r['key']]=r
  return list(records.values()),dict(status='partial',scope='Opinbert vöruviðmót í 100 færslu lotum; ekki tæmandi',loaded=len(records),expected=total,next_page=page+1 if page<pages else 1,checked_at=now())
 path,prefix=DIRECTORIES[key]
 body,_=client.get(client.origin+path,limit=40000000)
 urls=[u for u in sitemap_urls(body) if urlsplit(u).hostname==urlsplit(client.origin).hostname and (prefix is None or urlsplit(u).path.startswith(prefix))]
 if key=='iskraft':urls=[u for u in urls if len(urlsplit(u).path.strip('/').split('/'))>=4]
 urls=list(dict.fromkeys(urls))
 if not urls:raise ValueError('Engar staðfestar vöruslóðir í síðukorti; sértenging þarf frekari útfærslu')
 cursor=int(state.get('cursor',0))%len(urls);checked=0;rejected=0;errors=[]
 for i in range(min(budget,len(urls))):
  url=urls[(cursor+i)%len(urls)]
  try:
   page,_=client.get(url)
   row=parse_directory(key,supplier,page,url)
   if row:records[row['key']]=row
   else:rejected+=1
  except HTTPError as e:
   if e.code in (401,403,429):raise
   errors.append(dict(url=url,error=str(e)))
  checked+=1
  progress(dict(stage=f'Vöruskrá {checked}/{budget}',loaded=len(records),expected=len(urls)))
 # Individual HTTP failures remain explicit; successful rows and the next cursor are retained.
 return list(records.values()),dict(status='partial',scope='Vöruskrá í lotum; afbrigði og lagerstaða óstaðfest. Verð aðeins þar sem nákvæmur aðalverðreitur er lesinn.',loaded=len(records),expected=len(urls),cursor=(cursor+checked)%len(urls),rejected_this_run=rejected,errors=errors,checked_at=now())
