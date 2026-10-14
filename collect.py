"""Fetch public JSON-LD product prices into a review CSV (never auto-import)."""
import argparse
import csv
import json
import time
from html.parser import HTMLParser
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser
from app import FIELDS
from datetime import datetime, timezone

# Explicit public supplier hosts only. No arbitrary targets or cross-host redirects.
HOSTS = {'byko.is', 'www.byko.is', 'husa.is', 'www.husa.is', 'wurth.is', 'www.wurth.is',
         'sindri.is', 'www.sindri.is', 'fossberg.is', 'www.fossberg.is'}
AGENT = 'InnkaupsferilPriceReview/0.1'

class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = urlsplit(req.full_url), urlsplit(newurl)
        if new.scheme != 'https' or new.hostname != old.hostname or new.port not in (None,443) or new.username or new.password:
            raise ValueError('Redirect outside approved origin; use canonical URL.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def fetch(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in HOSTS or p.port not in (None,443) or p.username or p.password:
        raise ValueError('Only approved supplier HTTPS origins are supported.')
    with build_opener(SafeRedirect()).open(Request(url, headers={'User-Agent':AGENT}), timeout=20) as response:
        data = response.read(4_000_001)
        if len(data)>4_000_000:
            raise ValueError('Response too large.')
        return data.decode('utf-8', errors='replace')

class JsonLD(HTMLParser):
    def __init__(self):
        super().__init__(); self.active=False; self.buffer=[]; self.blocks=[]
    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.active=dict(attrs).get('type','').lower()=='application/ld+json'; self.buffer=[]
    def handle_data(self, data):
        if self.active:self.buffer.append(data)
    def handle_endtag(self, tag):
        if tag=='script' and self.active:
            try:self.blocks.append(json.loads(''.join(self.buffer)))
            except json.JSONDecodeError:pass
            self.active=False

def walk(value):
    if isinstance(value,list):
        for item in value:yield from walk(item)
    elif isinstance(value,dict):
        yield value
        for item in value.values():yield from walk(item)

def extract(html, url, supplier):
    parser=JsonLD();parser.feed(html)
    rows=[];seen=set()
    for product in walk(parser.blocks):
        types=product.get('@type',[])
        if isinstance(types,str):types=[types]
        if 'Product' not in types:continue
        offers=product.get('offers',[])
        if isinstance(offers,dict):offers=[offers]
        for offer in offers:
            if not isinstance(offer,dict) or offer.get('price') is None:continue
            brand=product.get('brand','')
            if isinstance(brand,dict):brand=brand.get('name','')
            r={field:'' for field in FIELDS}
            r.update(supplier=supplier,sku=product.get('sku',''),name=product.get('name',''),
                     brand=brand,manufacturer_part=product.get('mpn',''),
                     gtin=next((product[k] for k in ('gtin14','gtin13','gtin12','gtin8','gtin') if product.get(k)),''),
                     price=offer['price'],currency=offer.get('priceCurrency',''),url=url,
                     observed_at=datetime.now(timezone.utc).isoformat())
            key=(str(r['sku']),str(r['name']),str(r['price']),str(r['currency']))
            if key not in seen:rows.append(r);seen.add(key)
    return rows

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--supplier',required=True)
    parser.add_argument('--urls',required=True,help='Text file with explicit product URLs, one per line')
    parser.add_argument('--output',default='data/price-review.csv')
    args=parser.parse_args()
    from pathlib import Path
    urls=[u.strip() for u in Path(args.urls).read_text().splitlines() if u.strip()]
    if len(urls)>100:raise SystemExit('Maximum 100 URLs per run.')
    rows=[];failures=[];last={}
    for url in urls:
        try:
            p=urlsplit(url)
            robots_url=f'{p.scheme}://{p.netloc}/robots.txt'
            robot=RobotFileParser();robot.parse(fetch(robots_url).splitlines())
            if not robot.can_fetch(AGENT,url):raise ValueError('robots.txt disallows collection.')
            delay=max(2,robot.crawl_delay(AGENT) or 0)
            rate=robot.request_rate(AGENT)
            if rate:delay=max(delay,rate.seconds/max(rate.requests,1))
            if delay>60:raise ValueError('Requested crawl delay exceeds 60 seconds; skip for manual collection.')
            time.sleep(max(0,delay-(time.monotonic()-last.get(p.hostname,0))))
            try:found=extract(fetch(url),url,args.supplier)
            finally:last[p.hostname]=time.monotonic()
            if not found:raise ValueError('No explicit Product/Offer JSON-LD price found; supplier adapter required.')
            rows.extend(found)
        except Exception as error:
            failures.append({'url':url,'error':str(error)})
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    output.with_suffix('.errors.json').write_text(json.dumps(failures,ensure_ascii=False,indent=2))
    print(f'{len(rows)} draft rows, {len(failures)} failed URLs. Review SKU, VAT, pack quantity, unit and category before import. No live supplier compatibility is guaranteed.')
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
