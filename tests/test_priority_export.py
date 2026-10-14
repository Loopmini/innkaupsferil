import csv,io,json,sqlite3,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import sync_priority as p,market_sync,app,catalogue_export as ex

class PriorityTest(unittest.TestCase):
 def test_completed_waits_globally_and_blocked_does_not_hold_round(self):
  statuses={'a':{'status':'ok'},'b':{'status':'partial'},'c':{'status':'blocked'}}
  chosen,skipped,new=p.plan(statuses,statuses,['a'])
  self.assertEqual(chosen,[]);self.assertIn('a',skipped);self.assertFalse(new)
  statuses['b']['coverage_complete']=True
  chosen,skipped,new=p.plan(statuses,statuses)
  self.assertTrue(new);self.assertEqual(set(chosen),{'a','b'});self.assertIn('c',skipped)
  self.assertEqual(p.plan(statuses,statuses,['c'],True)[0],['c'])
 def test_unique_units_errors_and_changed_index(self):
  def state(units,errors=(),index='x'):return dict(status='partial',coverage_units=units,coverage_total=3,coverage_index=index,errors=list(errors))
  a=p.checkpoint({},state(['0','1']));b=p.checkpoint(a,state(['1']))
  self.assertEqual(b['coverage_done'],2);self.assertFalse(b['coverage_complete'])
  c=p.checkpoint(b,state(['2'],['error']));self.assertFalse(c['coverage_complete'])
  d=p.checkpoint(c,state(['2']));self.assertTrue(d['coverage_complete'])
  self.assertFalse(p.checkpoint(d,state(['0'],index='changed'))['coverage_complete'])
 def test_unknown_last_page_keeps_prior_pages(self):
  a=p.checkpoint({},dict(status='partial',coverage_units=['1'],coverage_total=None,coverage_index='pages'))
  b=p.checkpoint(a,dict(status='partial',coverage_units=['2'],coverage_total=2,coverage_index='pages'))
  self.assertTrue(b['coverage_complete'])
 def test_scheduler_survives_restart_and_does_not_fetch_completed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);market_sync.atomic(root/'data/market-status.json',{'sources':{'thor':{'status':'ok'},'husa':{'status':'partial'}}})
   with patch('market_sync.Client') as client:
    result=market_sync.run(root=root,selected=['thor'])
    client.assert_not_called();self.assertEqual(result['selected'],[]);self.assertIn('thor',result['skipped'])
   self.assertEqual(market_sync.load(root/'data/market-status.json',{})['sources']['thor']['status'],'ok')

class ExportTest(unittest.TestCase):
 def test_lossless_database_and_review_fields_without_secrets(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'data').mkdir();(root/'.env').write_text('NEVER-EXPORT-SECRET');(root/'data/market-live.json').write_text('{"products":[]}')
   offer={'id':1,'supplier':'A','sku':'000123','name':'=DANGEROUS()','description':'Original','classification':{'id':'tools.power.nailers','path':['T','P','N']},'identity':{'values':{'manufacturer':'Maker','model':'001-A','gtin':'04006381333931'},'status':'review'},'price':None,'image_url':'https://example.com/a.jpg','documents':[{'name':'Manual','url':'https://example.com/a.pdf','status':'review'}],'specifications':{'voltage_v':18},'specification_evidence':{'voltage_v':'bls. 2'}}
   cat={'offers':[offer],'metadata':{},'projects':[]}
   with patch.object(app,'ROOT',root),patch.object(app,'DB',root/'data/catalog.sqlite'),patch.object(app,'catalogue',return_value=cat):
    with app.connect() as db:db.execute("INSERT INTO projects(name) VALUES('Verk')")
    blob=ex.archive(app)
   z=zipfile.ZipFile(io.BytesIO(blob));self.assertFalse(any('.env' in n for n in z.namelist()));self.assertNotIn(b'NEVER-EXPORT-SECRET',blob)
   self.assertEqual(json.loads(z.read('catalogue.json'))['offers'][0]['sku'],'000123')
   rows=list(csv.DictReader(io.StringIO(z.read('review/vorur_og_birgjatilbod.csv').decode('utf-8-sig'))));self.assertEqual(rows[0]['supplier_sku'],'000123');self.assertEqual(rows[0]['price'],'');self.assertEqual(rows[0]['original_name'],"'=DANGEROUS()");self.assertIn('a.pdf',rows[0]['document_urls']);self.assertEqual(rows[0]['spec_voltage_v'],'18')
   with sqlite3.connect(':memory:') as db:
    db.executescript(z.read('database/catalog.sql').decode());self.assertEqual(db.execute('SELECT name FROM projects').fetchone()[0],'Verk')
