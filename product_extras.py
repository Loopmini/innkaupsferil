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
        def __init__(self):super().__init__();self.meta={};self.scripts=[];self.current=None;self.links=[];self.anchor=None
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='a':self.anchor=[a.get('href',''),'']
            if tag=='meta':self.meta[a.get('property',a.get('name','')).lower()]=a.get('content','')
            if tag=='script' and (a.get('type')=='application/ld+json' or a.get('id')=='wix-warmup-data'):self.current=[a,'']
        def handle_data(self,data):
            if self.anchor is not None:self.anchor[1]+=data
            if self.current is not None:self.current[1]+=data
        def handle_endtag(self,tag):
            if tag=='a' and self.anchor is not None:self.links.append(self.anchor);self.anchor=None
            if tag=='script' and self.current is not None:self.scripts.append(self.current);self.current=None
    p=Parser();p.feed(body)
    result={'image_url':page_image(body,url),'description':'','supplier_categories':[],'documents':[],'technical_properties':[],'details_version':3}
    def walk(value):
        if isinstance(value,dict):
            yield value
            for v in value.values():yield from walk(v)
        elif isinstance(value,list):
            for v in value:yield from walk(v)
    def document(href,label):
        link=image_url(href,url)
        if not link or not urlsplit(link).path.lower().endswith('.pdf'):return
        label=text(label)[:180] or urlsplit(link).path.rsplit('/',1)[-1]
        if re.search(r'privacy|cookie|terms|persónuvernd|vafrakök|skilmál',label+' '+link,re.I):return
        if any(x['url']==link for x in result['documents']):return
        if len(result['documents'])<30:result['documents'].append({'url':link,'name':label,'source_url':url})
    for href,label in p.links:document(href,label)
    product_seen=False
    for attrs,raw in p.scripts:
        try:data=json.loads(raw)
        except (ValueError,TypeError):continue
        for item in walk(data):
            kind=item.get('@type',[]);kind=[kind] if isinstance(kind,str) else kind
            if 'Product' in kind and not product_seen:
                product_seen=True
                result['description']=text(item.get('description'))[:8000]
                props=item.get('additionalProperty',[])
                if isinstance(props,dict):props=[props]
                if isinstance(props,list):
                    for prop in props[:50]:
                        if isinstance(prop,dict) and isinstance(prop.get('value'),(str,int,float)):
                            result['technical_properties'].append({'name':text(prop.get('name'))[:120],
                                'value':text(prop['value'])[:200],'unit':text(prop.get('unitText') or prop.get('unitCode'))[:30]})
                imgs=item.get('image',[]);imgs=[imgs] if not isinstance(imgs,list) else imgs
                for im in imgs:
                    src=im.get('contentUrl',im.get('url','')) if isinstance(im,dict) else im
                    if not result['image_url']:result['image_url']=image_url(src,url)
                cat=item.get('category',[]);cat=[cat] if isinstance(cat,str) else cat
                if isinstance(cat,list):result['supplier_categories']=[text(c) for c in cat if isinstance(c,str) and text(c)][:20]
            # Wix exposes the actual product's categories in public hydration data.
            if attrs.get('id')=='wix-warmup-data' and item.get('urlPart')==urlsplit(url).path.rstrip('/').split('/')[-1]:
                for section in item.get('additionalInfo',[]):
                    if not isinstance(section,dict):continue
                    try:rich=json.loads(section.get('description',''))
                    except (ValueError,TypeError):continue
                    for node in walk(rich):
                        f=node.get('fileData',{});src=f.get('src',{}) if isinstance(f,dict) else {}
                        if not isinstance(src,dict) or src.get('private') is not False:continue
                        file_id=src.get('id','')
                        if isinstance(file_id,str) and re.fullmatch(r'ugd/[A-Za-z0-9_.-]+\.pdf',file_id,re.I):
                            document('https://'+ 'static.wixstatic.com/'+file_id,f.get('name',section.get('title','PDF')))
                cats=item.get('categories',[])
                if isinstance(cats,list):result['supplier_categories']=[text(c.get('name')) for c in cats if isinstance(c,dict) and c.get('name') not in ('Vörur','All Products')][:20]
    if not result['description']:result['description']=text(p.meta.get('og:description',''))[:8000]
    return result
