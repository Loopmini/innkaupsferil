"""Supplier image metadata and local classification overrides."""
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
import ipaddress


def image_url(value, base=''):
    if not isinstance(value,str) or not value.strip(): return ''
    value=urljoin(base,value.strip())
    try:
        p=urlsplit(value)
        if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443):return ''
        if p.hostname=='localhost' or '.' not in p.hostname:return ''
        try:
            if not ipaddress.ip_address(p.hostname).is_global:return ''
        except ValueError:pass
        return value
    except ValueError:return ''


def page_image(body,url):
    class Parser(HTMLParser):
        def __init__(self):super().__init__();self.images={}
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='meta':
                key=a.get('property',a.get('name','')).lower()
                if key in ('og:image','og:image:secure_url','twitter:image'):
                    self.images.setdefault(key,image_url(a.get('content',''),url))
    p=Parser();p.feed(body)
    return next((p.images[k] for k in ('og:image:secure_url','og:image','twitter:image') if p.images.get(k)),'')


def page_details(body,url):
    """Read public product metadata; never interpret embedded placeholder prices."""
    import json,re,html
    def text(value):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',str(value or '')))).strip()
    class Parser(HTMLParser):
        def __init__(self):super().__init__();self.meta={};self.scripts=[];self.current=None
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='meta':self.meta[a.get('property',a.get('name','')).lower()]=a.get('content','')
            if tag=='script' and (a.get('type')=='application/ld+json' or a.get('id')=='wix-warmup-data'):self.current=[a,'']
        def handle_data(self,data):
            if self.current is not None:self.current[1]+=data
        def handle_endtag(self,tag):
            if tag=='script' and self.current is not None:self.scripts.append(self.current);self.current=None
    p=Parser();p.feed(body)
    result={'image_url':page_image(body,url),'description':'','supplier_categories':[]}
    def walk(value):
        if isinstance(value,dict):
            yield value
            for v in value.values():yield from walk(v)
        elif isinstance(value,list):
            for v in value:yield from walk(v)
    product_seen=False
    for attrs,raw in p.scripts:
        try:data=json.loads(raw)
        except (ValueError,TypeError):continue
        for item in walk(data):
            kind=item.get('@type',[]);kind=[kind] if isinstance(kind,str) else kind
            if 'Product' in kind and not product_seen:
                product_seen=True
                result['description']=text(item.get('description'))[:8000]
                imgs=item.get('image',[]);imgs=[imgs] if not isinstance(imgs,list) else imgs
                for im in imgs:
                    src=im.get('contentUrl',im.get('url','')) if isinstance(im,dict) else im
                    if not result['image_url']:result['image_url']=image_url(src,url)
                cat=item.get('category',[]);cat=[cat] if isinstance(cat,str) else cat
                if isinstance(cat,list):result['supplier_categories']=[text(c) for c in cat if isinstance(c,str) and text(c)][:20]
            # Wix exposes the actual product's categories in public hydration data.
            if attrs.get('id')=='wix-warmup-data' and item.get('urlPart')==urlsplit(url).path.rstrip('/').split('/')[-1]:
                cats=item.get('categories',[])
                if isinstance(cats,list):result['supplier_categories']=[text(c.get('name')) for c in cats if isinstance(c,dict) and c.get('name') not in ('Vörur','All Products')][:20]
    if not result['description']:result['description']=text(p.meta.get('og:description',''))[:8000]
    return result
