import copy,json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import app,taxonomy,product_evidence as e
from product_extras import page_details

class EvidenceTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.original={'id':1,'supplier':'A','sku':'00081-B','name':'Borvél','brand':'Brand','model':'001-X','manufacturer_part':'001-X','unit':'stk','pack_quantity':1,'documents':[]}
  self.other={**self.original,'id':2,'supplier':'B','sku':'987'}
  self.patches=[patch.object(app,'DB',Path(self.tmp.name)/'catalog.sqlite'),patch.object(app,'catalogue',side_effect=self.catalogue)]
  for p in self.patches:p.start()
  app.connect().close()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def catalogue(self):
  with app.connect() as db:ids,links=e.load(db)
  return {'offers':[e.enrich(copy.deepcopy(o),ids.get(o['id']),links.get(o['id'],[])) for o in (self.original,self.other)]}
 def identity(self,oid=1,**kw):
  return dict(id=oid,manufacturer='Maker',brand='Brand',model='001-X',manufacturer_part='001-X',gtin='',status='confirmed',source_url='https://example.com/product',evidence='Bls. 2; nákvæm útfærsla',reviewed=True,**kw)
 def document(self,oid=1,**kw):
  d=dict(id=oid,url='https://example.com/001.pdf',source_url='https://example.com/product',name='001-X Technical data',type='datasheet',scope='product',source_kind='manufacturer',status='confirmed',evidence='Bls. 3',coverage='001-X',document_manufacturer='Maker',document_identifier='001-X',reviewed=True)
  d.update(kw);return d
 def test_identifiers_keep_zero_suffix_and_never_copy_supplier_sku(self):
  r=page_details('<script type="application/ld+json">{"@type":"Product","sku":"00081-B","brand":{"name":"Brand"},"manufacturer":{"name":"Maker"},"model":"001-X","mpn":"00012-A"}</script>','https://example.com/p')
  self.assertEqual(r['identity_observed']['manufacturer_part'],'00012-A');self.assertEqual(r['identity_observed']['model'],'001-X')
  r=page_details('<script type="application/ld+json">{"@type":"Product","sku":"00081-B"}</script>','https://example.com/p')
  self.assertNotIn('manufacturer_part',r['identity_observed']);self.assertEqual(e.identity(self.original)['values']['manufacturer'],'')
 def test_persistence_changed_data_downgrades_without_overwriting(self):
  e.save_identity(app,self.identity());e.save_document(app,self.document())
  o=self.catalogue()['offers'][0];self.assertEqual(o['identity']['status'],'confirmed');self.assertEqual(o['documents'][0]['status'],'confirmed')
  self.original['pack_quantity']=2
  o=self.catalogue()['offers'][0];self.assertEqual(o['identity']['status'],'review');self.assertEqual(o['identity']['values']['model'],'001-X');self.assertEqual(o['documents'][0]['status'],'review')
  with sqlite3.connect(app.DB) as db:self.assertEqual(db.execute('SELECT count(*) FROM product_audit').fetchone()[0],2)
 def test_no_automatic_confirmation_and_exact_suffix_required(self):
  with self.assertRaises(ValueError):e.save_document(app,self.document())
  e.save_identity(app,self.identity())
  for change in ({'document_identifier':'001'},{'document_manufacturer':'Other'},{'reviewed':False},{'scope':'unknown'},{'coverage':''}):
   with self.subTest(change=change),self.assertRaises(ValueError):e.save_document(app,self.document(**change))
  e.save_document(app,self.document(status='review',scope='unknown'))
  self.assertEqual(e.metrics(self.catalogue()['offers'])['confirmed_datasheet'],0)
 def test_deduplication_per_url_and_optimistic_concurrency(self):
  for oid in (1,2):e.save_identity(app,self.identity(oid));e.save_document(app,self.document(oid))
  with app.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM evidence_documents').fetchone()[0],1)
  with self.assertRaises(ValueError):e.save_document(app,self.document())
  d=self.catalogue()['offers'][0]['documents'][0]
  e.save_document(app,self.document(status='rejected',expected_at=d['checked_at']))
  with app.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM evidence_links').fetchone()[0],2)
  self.assertEqual(self.catalogue()['offers'][0]['documents'][0]['status'],'rejected')
  self.assertEqual(self.original['sku'],'00081-B')
 def test_series_is_not_exact_datasheet_and_source_links_are_unconfirmed(self):
  e.save_identity(app,self.identity());e.save_document(app,self.document(scope='series'))
  self.assertEqual(e.metrics(self.catalogue()['offers'])['confirmed_datasheet'],0)
  r=e.enrich({'documents':[{'name':'Data sheet','url':'https://example.com/a.pdf'}]})
  self.assertEqual(r['documents'][0]['status'],'review')
 def test_source_priority_and_conflict_review(self):
  row={'name':'Borvél','identity':{'status':'confirmed','manufacturer_description':'Hleðslutæki fyrir borvél'}}
  c=taxonomy.classify(row,{})
  self.assertEqual(c['id'],'electrical.power.power');self.assertTrue(c['needs_review']);self.assertTrue(c['conflicts'])
  c=taxonomy.classify(row,{'classification_id':'tools.power.power'})
  self.assertEqual(c['id'],'tools.power.power');self.assertTrue(c['needs_review'])
  row={'name':'ABC','technical_properties':[{'name':'Product type','value':'Rörtengi'}]}
  self.assertEqual(taxonomy.classify(row,{})['id'],'plumbing.fittings.fittings')
 def test_diverse_product_heads(self):
  cases={'Naglar fyrir naglabyssu 20°':'fasteners.nails.collated','Naglabyssa 18V':'tools.power.nailers','MAKITA Hleðslutæki fyrir borvél':'electrical.power.power','MAKITA Borvél með hleðslutæki':'tools.power.power','MAKITA Borvél (2 rafhlöður + hleðslutæki)':'tools.power.power','Borbitar fyrir borvél':'tools.drilling.drills','Handsög fyrir krossvið':'tools.hand.handsaws','Krossviður 18 mm':'building.boards.plywood','Rör DN32 PN16':'plumbing.pipes.pipes','Rörtengi fyrir rör DN32':'plumbing.fittings.fittings'}
  for name,leaf in cases.items():
   with self.subTest(name=name):self.assertEqual(taxonomy.detect(name),leaf)
 def test_search_uses_identifiers_not_supplier_sku(self):
  self.assertFalse(e.search_plan({'sku':'000123','name':'ABC'})['links'])
  self.assertIn('001-X',e.search_plan(self.original)['query'])
 def test_external_page_discovery_is_preview_only_and_blocked_stops(self):
  calls=[]
  def get(url,origin):
   calls.append(url)
   return (200,'User-agent: *\nDisallow: /',url)
  with self.assertRaises(ValueError):e.discover(app,{'id':1,'url':'https://maker.example/product'},get)
  self.assertEqual(len(calls),1)
  def allowed(url,origin):return (404,'',url) if url.endswith('robots.txt') else (200,'<html><a href="/001.pdf">Technical datasheet</a></html>',url)
  with patch('time.sleep'):
   r=e.discover(app,{'id':1,'url':'https://maker.example/product'},allowed)
  self.assertEqual(r['documents'][0]['status'],'review')
  with app.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM evidence_links').fetchone()[0],0)
