"""Purchasing metadata, offer conditions and drafts; no outbound messaging."""
import csv,io,json,math
from datetime import date,datetime,timezone

UNITS=('stk','m','m2','m3','kg','l')
CURRENCIES=('ISK','EUR','NOK','USD','DKK','GBP','SEK')

def setup(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS bom_settings(bom_id INTEGER PRIMARY KEY,data TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS offer_terms(offer_id INTEGER PRIMARY KEY,data TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS bom_imports(digest TEXT PRIMARY KEY,bom_id INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS rfq_replies(id INTEGER PRIMARY KEY,bom_id INTEGER NOT NULL,line_id TEXT NOT NULL,supplier TEXT NOT NULL,data TEXT NOT NULL,UNIQUE(bom_id,line_id,supplier));
    CREATE TABLE IF NOT EXISTS staged_documents(id TEXT PRIMARY KEY,kind TEXT NOT NULL,data TEXT NOT NULL,created_at TEXT NOT NULL,status TEXT NOT NULL);''')

def string(v,limit=180):
    if not isinstance(v,str) or len(v)>limit:raise ValueError('Ógilt textagildi.')
    return v.strip()

def optional_date(v):
    if not v:return ''
    try:return date.fromisoformat(v).isoformat()
    except (ValueError,TypeError):raise ValueError('Dagsetning þarf ÁÁÁÁ-MM-DD.')

def optional_number(v,maximum=1e12):
    if v in (None,''):return None
    if type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=maximum:raise ValueError('Ógilt tölugildi.')
    return v

def validate_settings(value):
    if not isinstance(value,dict):raise ValueError('Ógildar listastillingar.')
    result={k:string(value.get(k,'')) for k in ('project','location')}
    result['wanted_date']=optional_date(value.get('wanted_date',''))
    currency=value.get('currency','ISK')
    if currency not in CURRENCIES:raise ValueError('Ógildur gjaldmiðill.')
    result['currency']=currency;terms=value.get('suppliers',{});result['suppliers']={}
    if not isinstance(terms,dict) or len(terms)>100:raise ValueError('Ógildir birgjaskilmálar.')
    for supplier,t in terms.items():
        string(supplier)
        if not isinstance(t,dict):raise ValueError('Ógildir birgjaskilmálar.')
        result['suppliers'][supplier]={k:optional_number(t.get(k),100 if k=='discount_percent' else 1e12) for k in ('shipping','other_fees','discount_percent')}
        result['suppliers'][supplier].update(currency=currency,delivery_date=optional_date(t.get('delivery_date')),
            source=string(t.get('source','')),status='confirmed' if t.get('status')=='confirmed' else 'estimated')
    choices=value.get('choices',{})
    if not isinstance(choices,dict) or len(choices)>500 or any(not isinstance(k,str) or type(v) is not int for k,v in choices.items()):raise ValueError('Ógilt birgjaval.')
    result['choices']=choices
    return result

def validate_offer_terms(v):
    if not isinstance(v,dict):raise ValueError('Ógildir vöruskilmálar.')
    return {'min_quantity':optional_number(v.get('min_quantity')),'discount_percent':optional_number(v.get('discount_percent'),100),
            'valid_until':optional_date(v.get('valid_until')),'delivery_date':optional_date(v.get('delivery_date')),
            'source':string(v.get('source','')),'status':'confirmed' if v.get('status')=='confirmed' else 'estimated'}

def get_settings(db,bid):
    row=db.execute('SELECT data FROM bom_settings WHERE bom_id=?',(bid,)).fetchone()
    return json.loads(row[0]) if row else {'project':'','location':'','wanted_date':'','currency':'ISK','suppliers':{},'choices':{}}

def csv_bytes(rows):
    # Neutralize spreadsheet formula injection in user/supplier-controlled text.
    out=io.StringIO();w=csv.writer(out)
    for row in rows:w.writerow([("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for v in row])
    return out.getvalue().encode('utf-8-sig')

def rfq(db,bid):
    row=db.execute('SELECT * FROM bom_lists WHERE id=?',(bid,)).fetchone()
    if not row:raise ValueError('BOM fannst ekki.')
    settings=get_settings(db,bid);lines=json.loads(row['rows_json'])
    headers=['bom_id','line_id','description','quantity','unit','supplier','sku','brand','manufacturer_part','price','currency','vat_included','vat_rate','pack_quantity','min_quantity','discount_percent','valid_until','delivery_date','url','source','observed_at','project','delivery_location','wanted_date','requested_specifications','offered_specifications','availability']
    rows=[headers]
    for l in lines:
        data={'bom_id':bid,'line_id':l['line_id'],'description':l['name'],'quantity':l['quantity'],'unit':l['unit'],
              'currency':settings['currency'],'project':settings['project'],'delivery_location':settings['location'],'wanted_date':settings['wanted_date'],
              'requested_specifications':json.dumps(l.get('specifications',{}),ensure_ascii=False)}
        rows.append([data.get(k,'') for k in headers])
    return csv_bytes(rows)

def reply_offers(db):
    result=[]
    for row in db.execute('SELECT * FROM rfq_replies'):
        o=json.loads(row['data']);o.update(id=-9000000000000000+row['id'],bom_id=row['bom_id'],bom_line_id=row['line_id'],source_kind='quote',category='',subcategory='',quantity=None,lines=[],gtin='',match_key='quote:'+str(row['id']))
        price=o.get('price');tax=o.get('vat_rate');vat=o.get('vat_included');pack=o.get('pack_quantity')
        o['net_price']=price/(1+tax/100) if price is not None and vat is True and tax is not None else price if vat is False else None
        o['unit_price']=o['net_price']/pack if o['net_price'] is not None and pack else None
        result.append(o)
    return result

def draft(app,data):
    """An explicitly reviewed cart becomes a saved BOM in a single transaction."""
    entries=data.get('entries')
    if not isinstance(entries,list) or not 1<=len(entries)<=100:raise ValueError('Drög þurfa 1–100 vörulínur.')
    offers={o['id']:o for o in app.catalogue()['offers']};rows=[];selections={}
    for entry in entries:
        if not isinstance(entry,dict):raise ValueError('Ógild vörulína.')
        offer=offers.get(entry.get('id'))
        if not offer:raise ValueError('Vara fannst ekki í núverandi grunni.')
        quantity=app.number(entry.get('quantity'),'Magn',True)
        if quantity>1e9:raise ValueError('Magn of hátt.')
        unit=entry.get('unit')
        if unit not in UNITS:raise ValueError('Veldu einingu á hverri línu.')
        lid=str(len(rows)+1);has_global=bool(offer.get('gtin') or offer.get('brand') and offer.get('manufacturer_part'))
        row={k:offer.get(k,'') for k in ('name','gtin','brand','manufacturer_part')}
        row.update(line_id=lid,quantity=quantity,unit=unit,source_rows=[],reference_offer_id=offer['id'],
                   supplier='' if has_global else offer.get('supplier',''),sku='' if has_global else offer.get('sku',''),specifications=offer.get('specifications',{}))
        rows.append(row);selections[lid]=[offer['id']]
    name=string(data.get('name',''),120)
    if not name:raise ValueError('Heiti lista vantar.')
    settings=validate_settings(data.get('settings',{}))
    with app.connect() as db:
        bid=db.execute('INSERT INTO bom_lists(name,created_at,rows_json,selections_json,sheet) VALUES(?,?,?,?,?)',
            (name,datetime.now(timezone.utc).isoformat(),json.dumps(rows,ensure_ascii=False),json.dumps(selections),'Yfirfarin innkaupadrög')).lastrowid
        db.execute('INSERT INTO bom_settings VALUES(?,?)',(bid,json.dumps(settings)))
    return {'id':bid,'rows':len(rows)}

def stage(db,kind,value):
    from uuid import uuid4
    token=uuid4().hex
    db.execute('INSERT INTO staged_documents VALUES(?,?,?,?,?)',(token,kind,json.dumps(value,ensure_ascii=False),datetime.now(timezone.utc).isoformat(),'preview'))
    return token

def parse_replies(app,bid,content,source):
    import taxonomy
    from supplements import safe_url
    with app.connect() as db:
        record=db.execute('SELECT rows_json FROM bom_lists WHERE id=?',(bid,)).fetchone()
        if not record:raise ValueError('BOM fannst ekki.')
        lines={r['line_id']:r for r in json.loads(record[0])};rows=[];seen=set();details=[]
        reader=csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
        required={'bom_id','line_id','supplier','price','currency','vat_included','vat_rate','pack_quantity','unit'}
        if not required.issubset(reader.fieldnames or []):raise ValueError('Dálka vantar. Notaðu svarssniðmátið úr tilboðsbeiðninni.')
        def numeric(r,key,maximum=1e12):
            raw=r.get(key,'').strip()
            if not raw:return None
            try:v=float(raw.replace(',','.'))
            except ValueError:raise ValueError('Ógilt tölugildi: '+key)
            return optional_number(v,maximum)
        for i,r in enumerate(reader,2):
            if i>501:raise ValueError('Hámark 500 tilboðslínur.')
            if str(r.get('bom_id','')).strip()!=str(bid) or r.get('line_id') not in lines:raise ValueError(f'Lína {i}: BOM eða línuauðkenni passar ekki.')
            supplier=string(r.get('supplier',''));lid=r['line_id']
            if not supplier:raise ValueError(f'Lína {i}: birgja vantar.')
            if (lid,supplier) in seen:raise ValueError(f'Lína {i}: tvítekið svar sama birgis á sömu línu.')
            seen.add((lid,supplier));currency=string(r.get('currency',''))
            if currency not in CURRENCIES:raise ValueError('Ógildur gjaldmiðill.')
            unit=string(r.get('unit',''))
            if unit and unit not in UNITS:raise ValueError('Ógild eining.')
            vatraw=r.get('vat_included','').strip().lower()
            if vatraw not in ('','true','false','1','0'):raise ValueError('vat_included þarf true/false eða tómt.')
            vat=None if vatraw=='' else vatraw in ('true','1')
            price=numeric(r,'price');pack=numeric(r,'pack_quantity')
            if pack is not None and pack<=0:raise ValueError('Pakkastærð þarf jákvætt gildi.')
            specs=json.loads(r.get('offered_specifications') or '{}')
            taxonomy.validate_override({'specifications':specs})
            url=string(r.get('url',''),1000)
            if url and not safe_url(url):raise ValueError('Ógild vöruslóð.')
            observed=string(r.get('observed_at',''),40)
            if observed:
                try:dt=datetime.fromisoformat(observed.replace('Z','+00:00'))
                except ValueError:raise ValueError('Verðdagsetning þarf ISO-snið.')
                if dt.date()>date.today():raise ValueError('Verðdagsetning má ekki vera í framtíð.')
            terms=validate_offer_terms({'min_quantity':numeric(r,'min_quantity'),'discount_percent':numeric(r,'discount_percent',100),
                'valid_until':r.get('valid_until',''),'delivery_date':r.get('delivery_date',''),'source':r.get('source') or source,'status':'confirmed'})
            offer={'name':string(r.get('description') or lines[lid]['name'],400),'supplier':supplier,'sku':string(r.get('sku','')),
                'brand':string(r.get('brand','')),'manufacturer_part':string(r.get('manufacturer_part','')),
                'price':price,'currency':currency,'vat_included':vat,'vat_rate':numeric(r,'vat_rate',100),'pack_quantity':pack,'unit':unit,
                'observed_at':observed,'url':url,'terms':terms,'specifications':specs,'availability':string(r.get('availability','')) or 'Óstaðfest',
                'provenance':{'source':string(r.get('source') or source),'imported_at':datetime.now(timezone.utc).isoformat()},'price_status':'Verð vantar í tilboð'}
            old=db.execute('SELECT * FROM rfq_replies WHERE bom_id=? AND line_id=? AND supplier=?',(bid,lid,supplier)).fetchone()
            old=dict(old) if old else None
            rows.append({'line_id':lid,'supplier':supplier,'offer':offer,'before':old})
            details.append({'line_id':lid,'supplier':supplier,'name':offer['name'],'price':price,'currency':currency,'action':'changed' if old else 'new','missing':[k for k in ('price','pack_quantity','unit','observed_at') if offer.get(k) in (None,'')]})
        if not rows:raise ValueError('Engar tilboðslínur.')
        token=stage(db,'rfq',{'bom_id':bid,'source':source,'rows':rows})
    return {'token':token,'rows':details}

def commit_replies(app,token):
    with app.connect() as db:
        record=db.execute("SELECT * FROM staged_documents WHERE id=? AND kind='rfq' AND status='preview'",(token,)).fetchone()
        if not record:raise ValueError('Forskoðun fannst ekki eða hefur þegar verið staðfest.')
        data=json.loads(record['data']);bid=data['bom_id']
        for r in data['rows']:
            old=db.execute('SELECT * FROM rfq_replies WHERE bom_id=? AND line_id=? AND supplier=?',(bid,r['line_id'],r['supplier'])).fetchone()
            if (dict(old) if old else None)!=r['before']:raise ValueError('Svar hefur breyst. Forskoðaðu aftur.')
    backup=app.data_safety.create(app.ROOT,app.DB,'before_rfq_import')
    with app.connect() as db:
        for r in data['rows']:
            db.execute('INSERT INTO rfq_replies(bom_id,line_id,supplier,data) VALUES(?,?,?,?) ON CONFLICT(bom_id,line_id,supplier) DO UPDATE SET data=excluded.data',(bid,r['line_id'],r['supplier'],json.dumps(r['offer'],ensure_ascii=False)))
        db.execute("UPDATE staged_documents SET status='committed' WHERE id=?",(token,))
    return {'imported':len(data['rows']),'backup':backup['name'],'id':bid}

def preview_bom(app,data):
    import base64,bom,hashlib
    name=string(data.get('name',''),120)
    if not name:raise ValueError('Heiti BOM vantar.')
    filename=str(data.get('filename','bom.csv'))
    content=base64.b64decode(data['base64'],validate=True) if 'base64' in data else str(data.get('text','')).encode()
    if len(content)>3_000_000:raise ValueError('Hámark 3 MB.')
    rows,sheet=bom.parse(content,filename);digest=hashlib.sha256((name+json.dumps(rows,sort_keys=True)).encode()).hexdigest()
    with app.connect() as db:
        old=db.execute('SELECT bom_id FROM bom_imports WHERE digest=?',(digest,)).fetchone()
        token=stage(db,'bom',{'name':name,'rows':rows,'sheet':sheet,'digest':digest,'source':filename})
    return {'token':token,'rows':rows,'existing_id':old[0] if old else None,'source':filename}

def commit_bom(app,token):
    with app.connect() as db:
        row=db.execute("SELECT * FROM staged_documents WHERE id=? AND kind='bom' AND status='preview'",(token,)).fetchone()
        if not row:raise ValueError('Ógild forskoðun.')
        data=json.loads(row['data']);old=db.execute('SELECT bom_id FROM bom_imports WHERE digest=?',(data['digest'],)).fetchone()
        if old:
            db.execute("UPDATE staged_documents SET status='reused' WHERE id=?",(token,))
            return {'id':old[0],'rows':len(data['rows']),'reused':True}
    backup=app.data_safety.create(app.ROOT,app.DB,'before_bom_import')
    with app.connect() as db:
        bid=db.execute('INSERT INTO bom_lists(name,created_at,rows_json,sheet) VALUES(?,?,?,?)',(data['name'],datetime.now(timezone.utc).isoformat(),json.dumps(data['rows'],ensure_ascii=False),data['source']+' · '+data['sheet'])).lastrowid
        db.execute('INSERT INTO bom_imports VALUES(?,?)',(data['digest'],bid));data['bom_id']=bid;db.execute("UPDATE staged_documents SET status='committed',data=? WHERE id=?",(json.dumps(data,ensure_ascii=False),token))
    return {'id':bid,'rows':len(data['rows']),'backup':backup['name'],'reused':False}

def undo_document(app,token):
    with app.connect() as db:
        doc=db.execute("SELECT * FROM staged_documents WHERE id=? AND status='committed'",(token,)).fetchone()
        if not doc:raise ValueError('Innflutningur fannst ekki eða hefur þegar verið afturkallaður.')
        data=json.loads(doc['data'])
        if doc['kind']=='rfq':
            for r in data['rows']:
                current=db.execute('SELECT * FROM rfq_replies WHERE bom_id=? AND line_id=? AND supplier=?',(data['bom_id'],r['line_id'],r['supplier'])).fetchone()
                if not current or json.loads(current['data'])!=r['offer']:raise ValueError('Nýrra svar hefur breytt þessum línum. Afturkallaðu það fyrst.')
                oid=-9000000000000000+current['id']
                for b in db.execute('SELECT selections_json FROM bom_lists'):
                    if any(oid in ids for ids in json.loads(b[0]).values()):raise ValueError('Tilboðið er samþykkt á innkaupalista. Afturkallaðu vöruvalið fyrst.')
        elif doc['kind']=='bom':
            bid=data.get('bom_id');b=db.execute('SELECT * FROM bom_lists WHERE id=?',(bid,)).fetchone()
            if not b or json.loads(b['rows_json'])!=data['rows'] or json.loads(b['selections_json']) or db.execute('SELECT 1 FROM bom_settings WHERE bom_id=?',(bid,)).fetchone() or db.execute('SELECT 1 FROM rfq_replies WHERE bom_id=?',(bid,)).fetchone():raise ValueError('Listinn hefur verið tekinn í vinnslu. Afturköllun eyðir honum ekki.')
        else:raise ValueError('Óþekkt skjalategund.')
    backup=app.data_safety.create(app.ROOT,app.DB,'before_undo_document')
    with app.connect() as db:
        if doc['kind']=='rfq':
            for r in data['rows']:
                if r['before']:
                    old=r['before'];db.execute('UPDATE rfq_replies SET data=? WHERE id=?',(old['data'],old['id']))
                else:db.execute('DELETE FROM rfq_replies WHERE bom_id=? AND line_id=? AND supplier=?',(data['bom_id'],r['line_id'],r['supplier']))
        else:
            db.execute('DELETE FROM bom_imports WHERE bom_id=?',(data['bom_id'],));db.execute('DELETE FROM bom_lists WHERE id=?',(data['bom_id'],))
        db.execute("UPDATE staged_documents SET status='undone' WHERE id=?",(token,))
    return {'ok':True,'backup':backup['name']}
