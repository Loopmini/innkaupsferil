import json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import closing
import app,supplier_registry as s,data_safety

class RegistryTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.a=patch.object(app,'ROOT',self.root);self.b=patch.object(app,'DB',self.root/'data/catalog.sqlite');self.a.start();self.b.start()
 def tearDown(self):self.a.stop();self.b.stop();self.tmp.cleanup()
 def sample(self):return {'name':'Test birgir','website':'example.com','registration_number':'123456-7890','address':'Gata 1','email':'sales@example.com','contacts':[{'name':'Anna','role':'Sala','email':'anna@example.com','phone':'5551234'}]}
 def test_save_edit_backup_restore_and_existing_supplier_link(self):
  value=s.save(app,{'supplier':self.sample()});self.assertEqual(value['website'],'https://example.com/')
  self.assertEqual(next(x for x in s.listing(app) if x.get('id')==value['id'])['contacts'][0]['name'],'Anna')
  backup=data_safety.create(self.root,app.DB)
  value['contacts'][0]['phone']='5559999';s.save(app,{'supplier':value})
  data_safety.restore(self.root,app.DB,backup['name'])
  self.assertEqual(next(x for x in s.listing(app) if x.get('id')==value['id'])['contacts'][0]['phone'],'5551234')
  known=s.save(app,{'supplier':{'name':'Húsasmiðjan','website':'https://www.husa.is'}})
  self.assertEqual(sum(x.get('catalogue_name')=='Húsasmiðjan' for x in s.listing(app)),1)
  known['name']='Húsasmiðjan — innkaup';changed=s.save(app,{'supplier':known});self.assertEqual(changed['catalogue_name'],'Húsasmiðjan')
 def test_duplicates_and_invalid_contacts_rejected(self):
  value=s.save(app,{'supplier':self.sample()})
  with self.assertRaises(ValueError):s.save(app,{'supplier':self.sample()})
  other=self.sample();other['name']='Other'
  with self.assertRaises(ValueError):s.save(app,{'supplier':other})
  value['contacts'][0]['email']='invalid'
  with self.assertRaises(ValueError):s.save(app,{'supplier':value})
 def test_probe_preserves_contacts_and_invalidates_changed_website(self):
  value=s.save(app,{'supplier':self.sample()})
  report={'website':value['website'],'status':'possible','findings':[]}
  with patch('supplier_registry.inspect',return_value=report):s.probe(app,{'id':value['id']})
  loaded=next(x for x in s.listing(app) if x.get('id')==value['id']);self.assertEqual(loaded['contacts'],value['contacts']);self.assertEqual(loaded['discovery'],report)
  loaded['website']='https://another.example.com';saved=s.save(app,{'supplier':loaded});self.assertNotIn('discovery',saved)

class DiscoveryTest(unittest.TestCase):
 def test_api_sitemap_and_document_are_reported_without_import(self):
  calls=[]
  def get(url,origin):
   calls.append(url)
   if url.endswith('/robots.txt'):return 404,'',url
   if 'sitemap' in url:return 200,'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/product</loc></url></urlset>',url
   if 'wp-json' in url:return 200,'[{"id":1,"name":"Bor"}]',url
   return 200,'<a href="/prices.csv">Verðlisti</a>',url
  with patch('supplier_registry.time.sleep'):r=s.inspect('https://example.com',get)
  self.assertEqual(r['status'],'possible');self.assertEqual({f['kind'] for f in r['findings']},{'api','sitemap','file'});self.assertEqual(len(calls),4)
 def test_denied_access_stops_and_robots_is_obeyed(self):
  calls=[]
  def blocked(url,origin):calls.append(url);return 403,'',url
  self.assertEqual(s.inspect('https://example.com',blocked)['status'],'blocked');self.assertEqual(len(calls),1)
  calls=[]
  def disallow(url,origin):calls.append(url);return 200,'User-agent: *\nDisallow: /',url
  with patch('supplier_registry.time.sleep'):s.inspect('https://example.com',disallow)
  self.assertEqual(len(calls),1)
 def test_private_targets_credentials_and_dns_rebinding_rejected(self):
  for url in ['https://127.0.0.1','https://10.0.0.1','https://localhost','https://user:pass@example.com','http://example.com']:
   with self.assertRaises(ValueError):s.website(url)
  with patch('supplier_registry.socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]),patch('supplier_registry.socket.create_connection') as connect:
   with self.assertRaises(ValueError):s.PublicHTTPS('example.com').connect()
   connect.assert_not_called()
