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
