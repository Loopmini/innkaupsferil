"""Staged price imports with optimistic validation and scoped undo."""
import hashlib,json
from datetime import datetime,timezone
from uuid import uuid4

def setup(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS import_batches(id TEXT PRIMARY KEY,created_at TEXT NOT NULL,source TEXT NOT NULL,status TEXT NOT NULL,rows_json TEXT NOT NULL,before_json TEXT NOT NULL,after_json TEXT,history_ids TEXT);
    CREATE TABLE IF NOT EXISTS offer_sources(offer_id INTEGER PRIMARY KEY,source TEXT NOT NULL,imported_at TEXT NOT NULL,batch_id TEXT NOT NULL);''')

def state(db,rows):
    return [dict(r) if (r:=db.execute('SELECT * FROM offers WHERE supplier=? AND sku=?',(o['supplier'],o['sku'])).fetchone()) else None for o in rows]

def preview(app,content,source,expected_supplier=None):
    rows=app.parse_csv(content);source=str(source or 'Verðlisti')[:180]
    if expected_supplier and any(r['supplier']!=expected_supplier for r in rows):raise ValueError('Birgir í skjali passar ekki við forvalinn birgi. Leiðréttu skjalið eða birgjavalið; engin færsla vistuð.')
    with app.connect() as db:
        setup(db);before=state(db,rows);details=[]
        for r,old in zip(rows,before):
            changed=[k for k in app.FIELDS if old and r[k]!=old[k]]
            possible=[dict(x) for x in db.execute('SELECT supplier,sku,name FROM offers WHERE supplier=? AND lower(name)=lower(?) AND sku<>?',(r['supplier'],r['name'],r['sku']))]
            details.append({'supplier':r['supplier'],'sku':r['sku'],'name':r['name'],'action':'new' if old is None else 'changed' if changed else 'unchanged','changed_fields':changed,'before':old,'after':r,'possible_duplicates':possible})
        token=uuid4().hex
        db.execute('INSERT INTO import_batches VALUES(?,?,?,?,?,?,?,?)',(token,datetime.now(timezone.utc).isoformat(),source,'preview',json.dumps(rows),json.dumps(before),None,None))
    return {'token':token,'source':source,'rows':details,'counts':{s:sum(r['action']==s for r in details) for s in ('new','changed','unchanged')},'possible_duplicates':sum(bool(r['possible_duplicates']) for r in details)}

def commit(app,token,selected=None):
    with app.connect() as db:
        setup(db);batch=db.execute('SELECT * FROM import_batches WHERE id=?',(token,)).fetchone()
        if not batch or batch['status']!='preview':raise ValueError('Forskoðun er ekki lengur gild. Forskoðaðu aftur.')
        all_rows=json.loads(batch['rows_json']);all_before=json.loads(batch['before_json'])
        indices=list(range(len(all_rows))) if selected is None else selected
        if not isinstance(indices,list) or not indices or any(type(i) is not int or not 0<=i<len(all_rows) for i in indices) or len(set(indices))!=len(indices):raise ValueError('Veldu gildar línur til innflutnings.')
        rows=[all_rows[i] for i in indices];before=[all_before[i] for i in indices]
        remaining=[i for i in range(len(all_rows)) if i not in indices]
        if state(db,rows)!=before:raise ValueError('Gögn breyttust eftir forskoðun. Forskoðaðu aftur.')
    backup=app.data_safety.create(app.ROOT,app.DB,'before_price_import')
    with app.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        current=db.execute('SELECT status FROM import_batches WHERE id=?',(token,)).fetchone()
        if not current or current[0]!='preview':raise ValueError('Innflutningur hefur þegar verið staðfestur.')
        if state(db,rows)!=before:raise ValueError('Gögn breyttust. Forskoðaðu aftur.')
        history_start=db.execute('SELECT coalesce(max(id),0) FROM history').fetchone()[0]
        app.apply_rows(db,rows);after=state(db,rows)
        stamp=datetime.now(timezone.utc).isoformat()
        # Keep prior provenance in journal for undo as well.
        provenance=[dict(r) if (r:=db.execute('SELECT * FROM offer_sources WHERE offer_id=?',(a['id'],)).fetchone()) else None for a in after]
        for a in after:db.execute('INSERT OR REPLACE INTO offer_sources VALUES(?,?,?,?)',(a['id'],batch['source'],stamp,token))
        ids=[r[0] for r in db.execute('SELECT id FROM history WHERE id>?',(history_start,))]
        db.execute('UPDATE import_batches SET rows_json=?,before_json=? WHERE id=?',(json.dumps(rows),json.dumps(before),token))
        pending_token=None
        if remaining:
            pending_token=uuid4().hex
            db.execute('INSERT INTO import_batches VALUES(?,?,?,?,?,?,?,?)',(pending_token,datetime.now(timezone.utc).isoformat(),batch['source']+' · óafgreiddar línur','preview',json.dumps([all_rows[i] for i in remaining]),json.dumps([all_before[i] for i in remaining]),None,None))
        db.execute('UPDATE import_batches SET status=?,after_json=?,history_ids=? WHERE id=?',('committed',json.dumps({'offers':after,'provenance':provenance,'backup':backup['name']}),json.dumps(ids),token))
    return {'imported':len(rows),'backup':backup['name'],'batch_id':token,'pending_token':pending_token,'pending':len(remaining)}

def undo(app,token):
    with app.connect() as db:
        setup(db);batch=db.execute('SELECT * FROM import_batches WHERE id=?',(token,)).fetchone()
        if not batch or batch['status']!='committed':raise ValueError('Þennan innflutning er ekki hægt að afturkalla.')
        rows=json.loads(batch['rows_json']);before=json.loads(batch['before_json']);after=json.loads(batch['after_json'])
        if state(db,rows)!=after['offers']:raise ValueError('Vörur hafa breyst síðan. Afturkallaðu nýrri innflutning fyrst eða leiðréttu þær sérstaklega.')
        for a in after['offers']:
            provenance=db.execute('SELECT batch_id FROM offer_sources WHERE offer_id=?',(a['id'],)).fetchone()
            if not provenance or provenance[0]!=token:raise ValueError('Nýrri innflutningur notar þessar vörur. Afturkallaðu hann fyrst.')
        for old,a in zip(before,after['offers']):
            if old is None:
                oid=a['id']
                used=db.execute('SELECT 1 FROM items WHERE offer_id=?',(oid,)).fetchone() or db.execute('SELECT 1 FROM product_enrichment WHERE offer_id=?',(oid,)).fetchone() or db.execute('SELECT 1 FROM product_overrides WHERE offer_id=?',(oid,)).fetchone()
                for b in db.execute('SELECT rows_json,selections_json FROM bom_lists'):
                    used=used or any(oid in ids for ids in json.loads(b['selections_json']).values()) or any(r.get('reference_offer_id')==oid for r in json.loads(b['rows_json']))
                if used:raise ValueError('Ný vara úr innflutningnum er nú notuð á lista eða hefur leiðréttingar. Fjarlægðu þær tengingar áður en innflutningur er afturkallaður.')
    backup=app.data_safety.create(app.ROOT,app.DB,'before_undo_import')
    with app.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if state(db,rows)!=after['offers']:raise ValueError('Gögn breyttust; afturköllun stöðvuð.')
        for old,a,provenance in zip(before,after['offers'],after['provenance']):
            oid=a['id']
            if old is None:
                db.execute('DELETE FROM offers WHERE id=?',(oid,))
                db.execute('DELETE FROM product_details WHERE offer_id=?',(oid,));db.execute('DELETE FROM product_images WHERE offer_id=?',(oid,))
            else:db.execute('UPDATE offers SET '+','.join(k+'=?' for k in app.FIELDS)+' WHERE id=?',[old[k] for k in app.FIELDS]+[oid])
            db.execute('DELETE FROM offer_sources WHERE offer_id=?',(oid,))
            if provenance:db.execute('INSERT INTO offer_sources VALUES(?,?,?,?)',tuple(provenance[k] for k in ('offer_id','source','imported_at','batch_id')))
        for hid in json.loads(batch['history_ids']):db.execute('DELETE FROM history WHERE id=?',(hid,))
        db.execute('UPDATE import_batches SET status=? WHERE id=?',('undone',token))
    return {'ok':True,'backup':backup['name']}


def pending(app,token):
    """Reopen saved uncommitted rows; commit still checks their original baseline."""
    with app.connect() as db:
        batch=db.execute("SELECT * FROM import_batches WHERE id=? AND status='preview'",(token,)).fetchone()
        if not batch:raise ValueError('Óstaðfest drög fundust ekki.')
        rows=json.loads(batch['rows_json']);before=json.loads(batch['before_json']);details=[]
        for r,old in zip(rows,before):
            changed=[k for k in app.FIELDS if old and r[k]!=old[k]]
            duplicates=[dict(x) for x in db.execute('SELECT supplier,sku,name FROM offers WHERE supplier=? AND lower(name)=lower(?) AND sku<>?',(r['supplier'],r['name'],r['sku']))]
            details.append({'supplier':r['supplier'],'sku':r['sku'],'name':r['name'],'action':'new' if old is None else 'changed' if changed else 'unchanged','changed_fields':changed,'before':old,'after':r,'possible_duplicates':duplicates})
    return {'token':token,'source':batch['source'],'rows':details,'counts':{s:sum(r['action']==s for r in details) for s in ('new','changed','unchanged')},'possible_duplicates':sum(bool(r['possible_duplicates']) for r in details)}
