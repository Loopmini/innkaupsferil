"""Supplier image metadata and local classification overrides."""
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, unquote
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
        def __init__(self):super().__init__();self.meta={};self.scripts=[];self.current=None;self.links=[];self.anchor=None;self.product_images=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='a':self.anchor=[a.get('href',''),a.get('title','')]
            if tag=='img' and (a.get('itemprop')=='image' or re.search(r'product[-_ ](?:image|photo)|(?:image|photo)[-_ ]product|wp-post-image',a.get('class',''),re.I)):
                self.product_images.append(a.get('data-src') or a.get('data-lazy-src') or a.get('src',''))
            if tag=='meta':self.meta[a.get('property',a.get('name','')).lower()]=a.get('content','')
            if tag=='script' and (a.get('type')=='application/ld+json' or a.get('id')=='wix-warmup-data'):self.current=[a,'']
        def handle_data(self,data):
            if self.anchor is not None:self.anchor[1]+=data
            if self.current is not None:self.current[1]+=data
        def handle_endtag(self,tag):
            if tag=='a' and self.anchor is not None:self.links.append(self.anchor);self.anchor=None
            if tag=='script' and self.current is not None:self.scripts.append(self.current);self.current=None
    p=Parser();p.feed(body)
    result={'image_url':next((src for key in ('og:image:secure_url','og:image','twitter:image') if (src:=usable_image(p.meta.get(key,''),url))),''),'description':'','supplier_categories':[],'documents':[],'technical_properties':[],'details_version':5}
    def walk(value,depth=0):
        if depth>20:return
        if isinstance(value,dict):
            yield value
            for v in value.values():yield from walk(v,depth+1)
        elif isinstance(value,list):
            for v in value:yield from walk(v,depth+1)
    def document(href,label):
        link=image_url(href,url)
        if not link:return
        if link.split('#')[0].rstrip('/')==url.split('#')[0].rstrip('/'):return
        pdf=bool(re.search(r'\.pdf(?:$|[?&#])',unquote(link),re.I))
        technical=bool(re.search(r'data.?sheet|technical|manual|safety data|gagnabla|tæknibla|tæknigögn|öryggisbla|leiðbeining',str(label),re.I))
        if not pdf and not technical:return
        label=text(label)[:180] or urlsplit(link).path.rsplit('/',1)[-1]
        if re.search(r'privacy|cookie|terms|persónuvernd|vafrakök|skilmál',label+' '+link,re.I):return
        if any(x['url']==link for x in result['documents']):return
        if len(result['documents'])<30:result['documents'].append({'url':link,'name':label,'source_url':url,**({'format':'Óstaðfest skjalasnið'} if not pdf else {})})
    for href,label in p.links:document(href,label)
    product_seen=False
    parsed=[]
    for attrs,raw in p.scripts:
        try:parsed.append((attrs,json.loads(raw)))
        except (ValueError,TypeError):continue
    def types(item):
        value=item.get('@type',[])
        return [value] if isinstance(value,str) else value if isinstance(value,list) else []
    products=[item for attrs,data in parsed for item in walk(data) if 'Product' in types(item)]
    def same_page(value):
        return isinstance(value,str) and urljoin(url,value).split('#')[0].rstrip('/')==url.split('#')[0].rstrip('/')
    matching=[item for item in products if same_page(item.get('url')) or same_page(item.get('@id'))]
    selected=matching[0] if len(matching)==1 else products[0] if len(products)==1 else None
    for attrs,data in parsed:
        for item in walk(data):
            kind=item.get('@type',[]);kind=[kind] if isinstance(kind,str) else kind
            if item is selected and not product_seen:
                product_seen=True
                observed={}
                for field,key in [('manufacturer','manufacturer'),('brand','brand'),('model','model'),('manufacturer_part','mpn')]:
                    value=item.get(key)
                    if isinstance(value,dict):value=value.get('name')
                    if isinstance(value,str) and value.strip():observed[field]=value.strip()[:300]
                for key in ('gtin14','gtin13','gtin12','gtin8','gtin'):
                    value=item.get(key)
                    if isinstance(value,str) and value.strip():observed['gtin']=value.strip();break
                result['identity_observed']=observed
                result['description']=text(item.get('description'))[:8000]
                props=item.get('additionalProperty',[])
                if isinstance(props,dict):props=[props]
                if isinstance(props,list):
                    for prop in props[:50]:
                        if isinstance(prop,dict) and isinstance(prop.get('value'),(str,int,float)):
                            result['technical_properties'].append({'name':text(prop.get('name'))[:120],
                                'value':text(prop['value'])[:200],'unit':text(prop.get('unitText') or prop.get('unitCode'))[:30]})
                imgs=item.get('image',[]);imgs=[imgs] if not isinstance(imgs,list) else imgs
                selected_image=''
                for im in imgs:
                    src=im.get('contentUrl',im.get('url','')) if isinstance(im,dict) else im
                    if not selected_image:selected_image=usable_image(src,url)
                if selected_image:result['image_url']=selected_image
                for key in ('subjectOf','associatedMedia'):
                    for media in walk(item.get(key,[])):
                        document(media.get('contentUrl') or media.get('url',''),media.get('name') or media.get('description',''))
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
    if not usable_image(result['image_url'],url):result['image_url']=''
    if not result['image_url']:
        result['image_url']=next((src for raw in p.product_images if (src:=usable_image(raw,url))),'')
    if not result['description']:result['description']=text(p.meta.get('og:description','') or p.meta.get('description',''))[:8000]
    from datetime import datetime,timezone
    result['details_checked_at']=datetime.now(timezone.utc).isoformat()
    return result


def usable_image(value,base=''):
    import re
    link=image_url(value,base)
    if re.search(r'(?:placeholder|no[-_]?image|image[-_]?not[-_]?available|vantar[-_]?mynd|logo)(?:[./_?\-]|$)',urlsplit(link).path,re.I):return ''
    return link


def preserve_media(current,previous):
    """Keep last-known media on incomplete extraction, visibly marked for review."""
    current=dict(current)
    if current.get('image_url'):current['image_retained']=bool(current.get('image_retained',False))
    if not current.get('image_url') and previous.get('image_url'):
        current['image_url']=previous['image_url'];current['image_retained']=True
    if not current.get('documents') and previous.get('documents'):
        current['documents']=[{**d,'retained':True} for d in previous['documents']]
    return current
