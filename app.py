"""Local procurement catalogue. Python 3.11+, no external dependencies."""
import csv
import base64
import binascii
import io
import json
import math
import os
import threading
import time
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from supplements import read_supplements

ROOT = Path(__file__).parent
DB = Path(os.environ.get('INNKAUP_DB', ROOT / 'data/catalog.sqlite'))
FIELDS = ['supplier', 'sku', 'name', 'category', 'brand', 'gtin', 'manufacturer_part', 'price', 'currency', 'vat_included', 'vat_rate', 'pack_quantity', 'unit', 'url', 'observed_at']
SUPPLIERS = ['Ísól', 'Rúbix', 'Vatnsvirkinn', 'Vatn og veitur', 'Sindri', 'Fossberg', 'Röning', 'Ískraft', 'Reykjafell', 'Hampiðjan', 'Ísfell', 'Húsasmiðjan', 'BYKO', 'Þór hf.', 'Landvélar', 'Barki', 'Würth']

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.executescript('''CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY, supplier TEXT NOT NULL, sku TEXT NOT NULL,
        name TEXT NOT NULL, category TEXT, brand TEXT, gtin TEXT, manufacturer_part TEXT,
        price REAL NOT NULL, currency TEXT, vat_included INTEGER, vat_rate REAL,
        pack_quantity REAL, unit TEXT, url TEXT, observed_at TEXT,
        UNIQUE(supplier, sku));
        CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY, offer_id INTEGER, price REAL, currency TEXT,
        vat_included INTEGER, vat_rate REAL, pack_quantity REAL, unit TEXT, observed_at TEXT);
        CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS items (
        project_id INTEGER, offer_id INTEGER, quantity REAL NOT NULL,
        PRIMARY KEY(project_id, offer_id));
        CREATE TABLE IF NOT EXISTS product_overrides (offer_id INTEGER PRIMARY KEY, category TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS product_images (offer_id INTEGER PRIMARY KEY, url TEXT NOT NULL, checked_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS bom_lists (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL,
        rows_json TEXT NOT NULL, selections_json TEXT NOT NULL DEFAULT '{}', sheet TEXT);''')
    return db

def number(value, label, positive=False):
    try:
        n = float(value)
    except (ValueError, TypeError):
        raise ValueError(f'{label}: tölugildi vantar eða er ógilt (notaðu tugabrotspunkt).')
    if not math.isfinite(n) or n < 0 or (positive and n <= 0):
        raise ValueError(f'{label}: ógilt gildi.')
    return n

def validate(row):
    r = {k: str(row.get(k, '') or '').strip() for k in FIELDS}
    for k in ['supplier', 'sku', 'name', 'currency', 'unit', 'observed_at']:
        if not r[k]:
            raise ValueError(f'{k}: gildi vantar.')
    r['price'] = number(r['price'], 'price')
    r['pack_quantity'] = number(r['pack_quantity'], 'pack_quantity', True)
    r['vat_rate'] = number(r['vat_rate'], 'vat_rate')
    if r['vat_rate'] > 100 or r['vat_included'].lower() not in ('true', 'false', '1', '0'):
        raise ValueError('VSK þarf skýrt true/false og prósentu 0–100.')
    r['vat_included'] = int(r['vat_included'].lower() in ('true', '1'))
    r['currency'] = r['currency'].upper()
    if r['currency'] not in ('ISK', 'EUR', 'USD', 'NOK', 'DKK', 'GBP', 'SEK'):
        raise ValueError('Óstuddur gjaldmiðill.')
    if r['unit'] not in ('stk', 'm', 'm2', 'm3', 'kg', 'l'):
        raise ValueError('Eining verður að vera stk, m, m2, m3, kg eða l.')
    try:
        timestamp = datetime.fromisoformat(r['observed_at'].replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        if timestamp > datetime.now(timezone.utc):
            raise ValueError()
        r['observed_at'] = timestamp.astimezone(timezone.utc).isoformat()
    except ValueError:
        raise ValueError('observed_at þarf ISO-dagsetningu sem er ekki í framtíðinni.')
    if r['url'] and (urlsplit(r['url']).scheme not in ('http', 'https') or not urlsplit(r['url']).hostname):
        raise ValueError('Vörutengill þarf gilt http/https heimilisfang.')
    if r['gtin']:
        digits = r['gtin']
        if not digits.isdigit() or len(digits) not in (8, 12, 13, 14):
            raise ValueError('GTIN þarf 8, 12, 13 eða 14 tölustafi.')
        checksum = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits[:-1])))
        if (10 - checksum % 10) % 10 != int(digits[-1]):
            raise ValueError('GTIN vartala stenst ekki.')
        r['gtin'] = digits.zfill(14)
    return r

def import_csv(content):
    reader = csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
    if not reader.fieldnames or not set(FIELDS).issubset(reader.fieldnames):
        raise ValueError('CSV-dálka vantar. Sæktu sniðmátið.')
    rows, seen = [], set()
    for i, row in enumerate(reader, 2):
        if i > 10001:
            raise ValueError('Hámark 10.000 línur í innlestri.')
        try:
            r = validate(row)
            key = (r['supplier'], r['sku'])
            if key in seen:
                raise ValueError('Birgi/vörunúmer kemur tvisvar fyrir í sama innlestri.')
            seen.add(key)
            rows.append(r)
        except ValueError as e:
            raise ValueError(f'Lína {i}: {e}')
    if not rows:
        raise ValueError('Skráin inniheldur engar vörulínur.')
    with connect() as db:
        for r in rows:
            old = db.execute('SELECT * FROM offers WHERE supplier=? AND sku=?', (r['supplier'], r['sku'])).fetchone()
            if old and r['observed_at'] < old['observed_at']:
                raise ValueError(f'Eldri verðathugun fyrir {r["supplier"]} / {r["sku"]}. Engar línur vistaðar.')
            db.execute(f'INSERT INTO offers ({",".join(FIELDS)}) VALUES ({",".join("?" for _ in FIELDS)}) ON CONFLICT(supplier,sku) DO UPDATE SET ' + ','.join(f'{k}=excluded.{k}' for k in FIELDS), [r[k] for k in FIELDS])
            oid = db.execute('SELECT id FROM offers WHERE supplier=? AND sku=?', (r['supplier'], r['sku'])).fetchone()[0]
            history_fields = ['price', 'currency', 'vat_included', 'vat_rate', 'pack_quantity', 'unit', 'observed_at']
            if not old or any(old[k] != r[k] for k in history_fields):
                db.execute('INSERT INTO history (offer_id,' + ','.join(history_fields) + ') VALUES (?,?,?,?,?,?,?,?)', [oid] + [r[k] for k in history_fields])
    return len(rows)

def catalogue():
    with connect() as db:
        offers = [dict(r) for r in db.execute('SELECT * FROM offers ORDER BY name, supplier')]
        projects = [dict(r) for r in db.execute('SELECT * FROM projects ORDER BY id DESC')]
        items = [dict(r) for r in db.execute('SELECT * FROM items')]
        history = [dict(r) for r in db.execute('SELECT * FROM history ORDER BY observed_at DESC, id DESC')]
    for r in offers:
        r['source_kind'] = 'import'
        r['net_price'] = r['price'] / (1 + r['vat_rate'] / 100) if r['vat_included'] else r['price']
        r['unit_price'] = r['net_price'] / r['pack_quantity']
        r['match_key'] = ('gtin:' + r['gtin']) if r['gtin'] else ('mpn:' + r['brand'].casefold() + ':' + r['manufacturer_part'].casefold()) if r['brand'] and r['manufacturer_part'] else 'unmatched:' + str(r['id'])
    extra, metadata = read_supplements()
    with connect() as db:
        overrides={r['offer_id']:r['category'] for r in db.execute('SELECT * FROM product_overrides')}
        images={r['offer_id']:r['url'] for r in db.execute('SELECT * FROM product_images')}
    from product_extras import image_url
    for r in offers+extra:
        r['manual_category']=overrides.get(r['id'],'')
        r['image_url']=image_url(r.get('image_url') or images.get(r['id'],''))
    return dict(offers=offers + extra, projects=projects, items=items, history=history, suppliers=SUPPLIERS, metadata=metadata)

def save_classification(oid, category):
    if not isinstance(category,str) or len(category.strip())>120:
        raise ValueError('Flokkur má vera mest 120 stafir.')
    if not any(o['id']==oid for o in catalogue()['offers']):raise ValueError('Vara fannst ekki.')
    with connect() as db:
        if category.strip():db.execute('INSERT OR REPLACE INTO product_overrides VALUES(?,?)',(oid,category.strip()))
        else:db.execute('DELETE FROM product_overrides WHERE offer_id=?',(oid,))


def supplier_image(oid):
    offer=next((o for o in catalogue()['offers'] if o['id']==oid),None)
    if not offer:raise ValueError('Vara fannst ekki.')
    if offer.get('image_url'):return offer['image_url']
    # Only known market product routes, never invoice/category links or arbitrary input.
    if offer.get('source_kind')!='market' or offer.get('link_kind')=='category':return ''
    with connect() as db:
        cached=db.execute('SELECT * FROM product_images WHERE offer_id=?',(oid,)).fetchone()
    if cached and (datetime.now(timezone.utc)-datetime.fromisoformat(cached['checked_at'])).total_seconds()<86400:return cached['url']
    from market_sync import Client,SOURCES
    from product_extras import page_image
    from urllib.parse import urlsplit
    url=offer.get('url','');origin=next((origin for name,origin in SOURCES.values() if name==offer['supplier'] and urlsplit(origin).hostname==urlsplit(url).hostname),None)
    if not origin:return ''
    try:body,_=Client(origin).get(url)
    except (OSError,ValueError) as e:raise ValueError('Ekki tókst að sækja mynd frá birgi.') from e
    image=page_image(body,url)
    with connect() as db:db.execute('INSERT OR REPLACE INTO product_images VALUES(?,?,?)',(oid,image,datetime.now(timezone.utc).isoformat()))
    return image

SYNC_THREAD = None
SYNC_MUTEX = threading.Lock()

def sync_status():
    path = ROOT / 'data/market-status.json'
    data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'sources': {}}
    from market_sync import is_running
    data['running'] = bool(SYNC_THREAD and SYNC_THREAD.is_alive()) or is_running(ROOT / 'data/market-sync.lock')
    return data

def start_sync():
    global SYNC_THREAD
    with SYNC_MUTEX:
        if sync_status()['running']:
            return False
        def worker():
            try:
                from market_sync import run
                run(root=ROOT)
            except Exception as error:
                print('Market refresh failed:', error, flush=True)
        SYNC_THREAD = threading.Thread(target=worker, daemon=True)
        SYNC_THREAD.start()
        return True

def refresh_loop():
    # Retry no more than daily; failed sources remain visible, no rapid retry loops.
    while True:
        status=sync_status()
        stamp=status.get('finished_at') or status.get('started_at')
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(stamp)).total_seconds() if stamp else 86401
        if age>=86400:start_sync()
        time.sleep(60)

class Handler(BaseHTTPRequestHandler):
    def send(self, data, status=200, content_type='application/json; charset=utf-8'):
        body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/boms':
            with connect() as db:
                rows=[dict(r) for r in db.execute('SELECT id,name,created_at,sheet FROM bom_lists ORDER BY id DESC')]
            return self.send(rows)
        if path == '/api/bom':
            try:bid=int(parse_qs(urlsplit(self.path).query).get('id',['0'])[0])
            except ValueError:return self.send({'error':'Ógilt BOM-auðkenni'},400)
            with connect() as db:r=db.execute('SELECT * FROM bom_lists WHERE id=?',(bid,)).fetchone()
            if not r:return self.send({'error':'BOM fannst ekki'},404)
            value=dict(r);value['rows']=json.loads(value.pop('rows_json'));value['selections']=json.loads(value.pop('selections_json'))
            return self.send(value)
        if path == '/api/bom-template':
            return self.send('heiti,magn,eining,birgir,vorunumer,gtin,framleidandi,mpn\n5mm stálbor,20,stk,,,,,\n'.encode('utf-8-sig'),content_type='text/csv; charset=utf-8')
        if path == '/api/market-history':
            key=parse_qs(urlsplit(self.path).query).get('key',[''])[0]
            dbpath=ROOT/'data/market-history.sqlite'
            if not dbpath.exists():return self.send([])
            with sqlite3.connect(dbpath) as db:
                db.row_factory=sqlite3.Row
                rows=[dict(r) for r in db.execute('SELECT observed_at,price,currency,availability FROM observations WHERE product_key=? ORDER BY id DESC LIMIT 30',(key,))]
            return self.send(rows)
        if path == '/api/sync-status':
            return self.send(sync_status())
        if path == '/api/catalogue':
            return self.send(catalogue())
        if path == '/api/template':
            return self.send((','.join(FIELDS) + '\n').encode(), content_type='text/csv; charset=utf-8')
        files = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/search.js': ('search.js', 'text/javascript'), '/groups.js': ('groups.js','text/javascript'), '/bom-core.js': ('bom-core.js','text/javascript'), '/bom-ui.js': ('bom-ui.js','text/javascript'), '/style.css': ('style.css', 'text/css')}
        if path in files:
            name, kind = files[path]
            return self.send((ROOT / 'static' / name).read_bytes(), content_type=kind + '; charset=utf-8')
        self.send({'error': 'Fannst ekki'}, 404)

    def do_POST(self):
        # JSON and same-origin checks prevent cross-site form submissions to this local service.
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.send({'error': 'JSON required'}, 415)
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            return self.send({'error': 'Origin rejected'}, 403)
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length <= 0 or length > 5_000_000:
                raise ValueError('Ógild stærð; hámark 5 MB.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Ógild beiðni.')
            if self.path == '/api/product-classification':
                save_classification(int(data['id']),data.get('category',''))
                return self.send({'ok':True})
            if self.path == '/api/product-image':
                return self.send({'image_url':supplier_image(int(data['id']))})
            if self.path == '/api/refresh-market':
                return self.send({'started': start_sync()})
            if self.path == '/api/import':
                return self.send({'imported': import_csv(str(data.get('csv', '')))})
            if self.path == '/api/bom-import':
                import bom
                name=str(data.get('name','')).strip()
                if not name or len(name)>120:raise ValueError('Heiti BOM þarf 1–120 stafi.')
                filename=str(data.get('filename','bom.csv'))
                content=base64.b64decode(data['base64'],validate=True) if 'base64' in data else str(data.get('text','')).encode()
                if len(content)>3_000_000:raise ValueError('Hámark 3 MB fyrir BOM.')
                rows,sheet=bom.parse(content,filename)
                with connect() as db:
                    cursor=db.execute('INSERT INTO bom_lists(name,created_at,rows_json,sheet) VALUES(?,?,?,?)',(name,datetime.now(timezone.utc).isoformat(),json.dumps(rows,ensure_ascii=False),sheet))
                    bid=cursor.lastrowid
                return self.send({'id':bid,'rows':len(rows),'sheet':sheet})
            if self.path == '/api/bom-selection':
                bid=int(data['id']);selections=data.get('selections',{})
                with connect() as db:
                    row=db.execute('SELECT rows_json FROM bom_lists WHERE id=?',(bid,)).fetchone()
                    if not row:raise ValueError('BOM fannst ekki.')
                    ids={r['line_id'] for r in json.loads(row[0])}
                    if not isinstance(selections,dict) or any(k not in ids or not isinstance(v,list) or len(v)>1000 or any(not isinstance(x,int) for x in v) for k,v in selections.items()):raise ValueError('Ógilt vöruval.')
                    db.execute('UPDATE bom_lists SET selections_json=? WHERE id=?',(json.dumps(selections),bid))
                return self.send({'ok':True})
            with connect() as db:
                if self.path == '/api/projects':
                    name = str(data.get('name', '')).strip()
                    if not name or len(name) > 120:
                        raise ValueError('Heiti verkefnis þarf 1–120 stafi.')
                    db.execute('INSERT INTO projects(name) VALUES (?)', (name,))
                elif self.path == '/api/items':
                    pid, oid = int(data['project_id']), int(data['offer_id'])
                    qty = number(data['quantity'], 'Magn')
                    offer = next((o for o in catalogue()['offers'] if o['id'] == oid), None)
                    if not db.execute('SELECT 1 FROM projects WHERE id=?', (pid,)).fetchone() or not offer:
                        raise ValueError('Verkefni eða vara fannst ekki.')
                    if qty and offer['net_price'] is None:
                        raise ValueError('Staðfest verð án VSK vantar; ekki hægt að reikna innkaupalista.')
                    if qty == 0:
                        db.execute('DELETE FROM items WHERE project_id=? AND offer_id=?', (pid, oid))
                    else:
                        if not qty.is_integer():
                            raise ValueError('Panta þarf heilar pakkningar.')
                        db.execute('INSERT INTO items VALUES (?,?,?) ON CONFLICT(project_id,offer_id) DO UPDATE SET quantity=excluded.quantity', (pid, oid, qty))
                else:
                    return self.send({'error': 'Fannst ekki'}, 404)
            self.send({'ok': True})
        except (ValueError, KeyError, TypeError, binascii.Error) as e:
            self.send({'error': str(e)}, 400)

if __name__ == '__main__':
    connect().close()
    print('Innkaupsferil: http://127.0.0.1:8000 (local access only)', flush=True)
    if os.environ.get('INNKAUP_AUTO_REFRESH', '1') == '1':
        threading.Thread(target=refresh_loop, daemon=True).start()
    server = ThreadingHTTPServer(('127.0.0.1', 8000), Handler)
    import sys
    if '--open' in sys.argv:
        import threading, webbrowser
        threading.Timer(0.5, lambda: webbrowser.open('http://127.0.0.1:8000')).start()
    server.serve_forever()
