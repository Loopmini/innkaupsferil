"""Read-only, bounded context retrieval for the local single-owner assistant.

The model receives JSON only. No connection, SQL executor or mutation tool is exposed.
This is not a multi-user authorization service.
"""
import json
import sqlite3
from contextlib import closing


def connect_readonly(path):
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    allowed={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION}
    db.set_authorizer(lambda action,*args: sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY)
    return db


def context(path,selection,offers):
    if not isinstance(selection,dict) or set(selection)-{'offer_id','bom_id','supplier','query'}:
        raise ValueError('Ógilt samhengi aðstoðar.')
    result={};preferred=[]
    if 'offer_id' in selection:
        oid=selection['offer_id']
        if type(oid) is not int:raise ValueError('Ógilt vöruauðkenni.')
        offer=next((o for o in offers if o['id']==oid),None)
        if not offer:raise ValueError('Vara fannst ekki.')
        preferred=[oid];result={'kind':'product','id':oid,'name':offer['name']}
    elif 'bom_id' in selection:
        bid=selection['bom_id']
        if type(bid) is not int:raise ValueError('Ógilt listaauðkenni.')
        with closing(connect_readonly(path)) as db:
            row=db.execute('SELECT id,name,rows_json FROM bom_lists WHERE id=?',(bid,)).fetchone()
        if not row:raise ValueError('Listi fannst ekki.')
        rows=json.loads(row['rows_json'])
        result={'kind':'bom','id':bid,'name':row['name'],'total_lines':len(rows),
                'lines':[{k:r.get(k) for k in ('line_id','name','quantity','unit','specifications')} for r in rows[:40]]}
        preferred=[r.get('reference_offer_id') for r in rows if r.get('reference_offer_id') is not None][:40]
    else:
        for k in ('supplier','query'):
            v=selection.get(k,'')
            if not isinstance(v,str) or len(v)>300:raise ValueError('Ógilt leitarsamhengi.')
            result[k]=v
    return result,preferred
