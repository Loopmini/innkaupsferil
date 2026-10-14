"""Read public observations and private V1 project exports without conflating them."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).parent

def safe_url(value):
    if not isinstance(value, str):
        return ''
    try:
        p = urlsplit(value)
        return value if p.scheme in ('http', 'https') and p.hostname and not p.username else ''
    except ValueError:
        return ''

def identifier(key):
    return -int(hashlib.sha256(key.encode()).hexdigest()[:12], 16)

def read_supplements(root=ROOT):
    records, metadata = [], {}
    public = root / 'seeds/public-market.json'
    if public.exists():
        payload = json.loads(public.read_text(encoding='utf-8'))
        metadata['market'] = payload['meta']
        for item in payload['products']:
            r = dict(item)
            r.update(id=identifier('market:' + r['key']), source_kind='market', quantity=None,
                     gtin=r.get('gtin', ''), manufacturer_part=r.get('manufacturer_part', ''),
                     match_key='market:' + r['key'], net_price=None, unit_price=None, lines=[])
            r['url'] = safe_url(r.get('url'))
            if r.get('price') is not None and r.get('vat_included') is not None and r.get('vat_rate') is not None:
                r['net_price'] = r['price'] / (1+r['vat_rate']/100) if r['vat_included'] else r['price']
                if r.get('pack_quantity'):
                    r['unit_price'] = r['net_price'] / r['pack_quantity']
            records.append(r)
    private = root / 'data/legacy-project.json'
    if private.exists():
        payload = json.loads(private.read_text(encoding='utf-8'))
        metadata['project'] = payload['meta']
        for p in payload['products']:
            records.append(dict(id=identifier('legacy:' + p['id']), name=p['name'], supplier=p['supplier'],
                sku=p['sku'], category=p.get('category',''), subcategory=p.get('subcategory',''),
                brand='', gtin='', manufacturer_part='', price=None, currency='ISK', vat_included=None,
                vat_rate=None, pack_quantity=None, unit=p.get('unit',''),
                url=safe_url(p.get('productUrl')), observed_at=max((l['date'] for l in p.get('lines',[]) if l.get('date')),default=''),
                net_price=None, unit_price=None, match_key='legacy:'+p['id'],
                source_kind='purchase' if p.get('sourceType')=='invoice' else 'reference',
                quantity=p.get('quantity'), quantities=p.get('quantities',{}), lines=p.get('lines',[]),
                note=p.get('note',''), classification_status=p.get('classificationStatus',''),
                availability='Núverandi framboð óstaðfest', link_note=p.get('linkNote','Tengill úr fyrri yfirferð; ekki endurstaðfestur.'),
                links=[dict(url=safe_url(l.get('url')), label=l.get('label','Heimild'), evidence=l.get('evidence','')) for l in p.get('links',[])],
                price_status='Kaupverð vantar í frumgögn' if p.get('sourceType')=='invoice' else 'Verð vantar',
                source_file=p.get('sourceWorkbook',''), source_row=p.get('sourceRow')))
    return records, metadata
