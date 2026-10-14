"""Lossless review export: catalogue JSON, relational SQL/SQLite and Excel-readable CSV."""
import csv,io,json,sqlite3,tempfile,zipfile
from pathlib import Path
from datetime import datetime,timezone

def csv_bytes(rows):
 rows=list(rows);headers=list(dict.fromkeys(k for row in rows for k in row))
 buf=io.StringIO(newline='');writer=csv.writer(buf);writer.writerow(headers)
 def cell(v):
  if v is None:return ''
  if isinstance(v,(dict,list)):v=json.dumps(v,ensure_ascii=False)
  if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')):return "'"+v
  return v
 writer.writerows([[cell(r.get(k)) for k in headers] for r in rows])
 return buf.getvalue().encode('utf-8-sig')

def review_tables(cat):
 offers=[];docs=[];specs=[]
 for o in cat['offers']:
  identity=o.get('identity',{});v=identity.get('values',{});c=o.get('classification',{});path=c.get('path',[])
  row={'offer_id':str(o['id']),'supplier':o.get('supplier'),'supplier_sku':o.get('sku'),'original_name':o.get('name'),'original_description':o.get('description'),
       'family_id':c.get('id'),'top_category':path[0] if path else '', 'subcategory':path[1] if len(path)>1 else '', 'product_type':path[2] if len(path)>2 else '',
       'classification_source':c.get('source'),'classification_evidence':c.get('evidence'),'classification_review':c.get('needs_review'),'classification_conflicts':c.get('conflicts'),
       'manufacturer':v.get('manufacturer'),'brand':v.get('brand') or o.get('brand'),'model':v.get('model'),'mpn':v.get('manufacturer_part') or o.get('manufacturer_part'),'gtin':v.get('gtin') or o.get('gtin'),
       'identity_status':identity.get('status'),'identity_source':identity.get('source_url'),'match_key_unverified':o.get('match_key'),
       'supplier_category':o.get('category'),'supplier_subcategory':o.get('subcategory'),'supplier_categories':o.get('supplier_categories'),
       'price':o.get('price'),'currency':o.get('currency'),'vat_included':o.get('vat_included'),'vat_rate':o.get('vat_rate'),'net_price':o.get('net_price'),'unit_price':o.get('unit_price'),
       'unit':o.get('unit'),'pack_quantity':o.get('pack_quantity'),'terms':o.get('terms'),'availability':o.get('availability'),'price_observed_at':o.get('observed_at'),
       'product_url':o.get('url'),'image_url':o.get('image_url'),'document_urls':'\n'.join(d.get('url','') for d in o.get('documents',[])),
       'confirmed_datasheet_urls':'\n'.join(d.get('url','') for d in o.get('documents',[]) if d.get('type')=='datasheet' and d.get('status')=='confirmed' and d.get('scope')=='product'),
       'source':o.get('provenance'),'search_tags':o.get('search_tags'),'use_cases':o.get('use_cases'),'missing_specifications':o.get('missing_specifications'),
       'suggested_classification_id':'','review_notes':''}
  for key,value in o.get('specifications',{}).items():
   row['spec_'+key]=value
   specs.append({'offer_id':str(o['id']),'property':key,'value':value,'source':o.get('specification_evidence',{}).get(key),'conflict':key in o.get('specification_conflicts',[])})
  offers.append(row)
  for d in o.get('documents',[]):docs.append({'offer_id':str(o['id']),'supplier':o.get('supplier'),'supplier_sku':o.get('sku'),**d})
 return {'vorur_og_birgjatilbod.csv':offers,'skjol.csv':docs,'taeknieiginleikar.csv':specs}

def archive(app):
 # HTTP handler holds DATA_LOCK; database backup is a consistent SQLite snapshot.
 cat=app.catalogue();out=io.BytesIO();created=datetime.now(timezone.utc).isoformat()
 with tempfile.TemporaryDirectory() as folder:
  path=Path(folder)/'catalog.sqlite'
  with app.connect() as source,sqlite3.connect(path) as dest:source.backup(dest)
  with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
   z.write(path,'database/catalog.sqlite')
   with sqlite3.connect(path) as db:
    db.row_factory=sqlite3.Row
    z.writestr('database/catalog.sql','\n'.join(db.iterdump()))
    for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
     name=r[0];quoted='"'+name.replace('"','""')+'"'
     z.writestr('tables/'+name+'.csv',csv_bytes([dict(row) for row in db.execute('SELECT * FROM '+quoted)]))
   z.writestr('catalogue.json',json.dumps(cat,ensure_ascii=False,indent=2))
   for name,rows in review_tables(cat).items():z.writestr('review/'+name,csv_bytes(rows))
   # Supplement stores are not inside catalog.sqlite; preserve these separately.
   for p in sorted((app.ROOT/'data').glob('*.json')):
    z.write(p,'source-data/'+p.name)
   hist=app.ROOT/'data/market-history.sqlite'
   if hist.exists():
    copy=Path(folder)/'market-history.sqlite'
    with sqlite3.connect(hist.resolve().as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(copy) as dest:source.backup(dest)
    z.write(copy,'database/market-history.sqlite')
   z.writestr('LESTU_FYRST.txt',f'''NJÖRÐUR – HEILDARÚTFLUTNINGUR TIL YFIRFERÐAR
Útbúið: {created}
Birgjafærslur: {len(cat['offers'])}

Byrjaðu á review/vorur_og_birgjatilbod.csv. Hver röð er birgjatilboð, ekki sjálfkrafa einstök vara. family_id er núverandi vörutegund; match_key_unverified er eldri samsvörunarlykill, ekki ný tæknileg staðfesting.

Excel: Gögn > Úr texta/CSV, UTF-8. Stilltu offer_id, supplier_sku, MPN, GTIN og gerð sem TEXTA til að varðveita upphafsnúll og löng númer. Verð og tæknigildi nota tugabrotspunkt. Texti sem gæti orðið Excel-formúla hefur hlífðarpostul; óbreytt upprunagildi eru í JSON/SQLite.

Mynda- og skjalaslóðir eru dálkar; engin mynd eða PDF er felld inn. Skjöl og eiginleikar eru einnig sértöflur með offer_id. Óþekkt gildi eru tóm, aldrei fyllt með ágiskun eða núllverði. Skráðu tillögur í suggested_classification_id og review_notes; útflutningurinn breytir engu í forritinu. Innlestur leiðréttinga úr þessum pakka er ekki enn útfærður.

catalogue.json geymir allar núverandi birgjafærslur með óstyttum undirgögnum. database/catalog.sqlite og catalog.sql geyma allar staðbundnar töflur: birgja/tengiliði, lista/BOM, tengsl, yfirferðir, heimildir og sögu. Verðathuganir markaðar eru í aðskildri SQLite-skrá ef til. source-data geymir JSON-söfn sem liggja utan SQLite. tables eru CSV afrit af öllum SQLite-töflum.

API-lyklar, .env, afritasafn og loggar fylgja ekki. Upprunaleg PDF/Excel-viðhengi eru ekki sjálfkrafa innifalin; varðveitt skráning/slóðir þeirra fylgja gagnatöflunum. Þetta er yfirferðarpakki; ekki keyra SQL yfir virkan gagnagrunn.
''')
 return out.getvalue()
