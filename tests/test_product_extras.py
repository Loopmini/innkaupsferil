import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import app
from product_extras import image_url,page_image
from market_sync import parse_thor

class ExtrasTest(unittest.TestCase):
 def test_images_and_unsafe_urls(self):
  self.assertEqual(page_image('<meta content="/p.jpg?a=1&amp;b=2" property="og:image">','https://supplier.is/product'),'https://supplier.is/p.jpg?a=1&b=2')
  for u in ['javascript:alert(1)','http://site.is/p.jpg','https://127.0.0.1/x','https://user:pass@site.is/x']:
   self.assertEqual(image_url(u),'')
  r=parse_thor(dict(id=1,name='Vara',permalink='https://thor.is/p',images=[{'src':'https://thor.is/p.jpg'}]))
  self.assertEqual(r['image_url'],'https://thor.is/p.jpg')
 def test_override_survives_source_refresh_and_reset(self):
  with tempfile.TemporaryDirectory() as td,patch.object(app,'DB',Path(td)/'test.sqlite'):
   row={'id':-100,'name':'Óþekkt vara','category':'Óflokkað','price':None}
   with patch.object(app,'read_supplements',return_value=([dict(row)],{})):
    app.save_classification(-100,'Lokar og lagnaefni')
   row['category']='Nýr birgjaflokkur'
   with patch.object(app,'read_supplements',return_value=([dict(row)],{})):
    actual=app.catalogue()['offers'][0]
    self.assertEqual(actual['manual_category'],'Lokar og lagnaefni')
    self.assertEqual(actual['category'],'Nýr birgjaflokkur')
    app.save_classification(-100,'')
    self.assertEqual(app.catalogue()['offers'][0]['manual_category'],'')
    with self.assertRaises(ValueError):app.save_classification(999,'Flokkur')
 def test_invoice_links_are_not_fetched_as_product_images(self):
  with tempfile.TemporaryDirectory() as td,patch.object(app,'DB',Path(td)/'test.sqlite'),patch.object(app,'read_supplements',return_value=([{'id':-5,'source_kind':'purchase','url':'https://thor.is/category'}],{})),patch('market_sync.Client') as client:
   self.assertEqual(app.supplier_image(-5),'');client.assert_not_called()
 def test_barki_description_category_and_image_without_price(self):
  from product_extras import page_details
  body='''<meta property="og:image" content="https://static.wixstatic.com/product.jpg"><script type="application/ld+json">{"@type":"Product","name":"1 1/2","description":"Hraðtengi m/ró. Þrýstiþol 300 bör.","offers":{"price":"10"}}</script><script id="wix-warmup-data" type="application/json">{"product":{"urlPart":"1-12","categories":[{"name":"Glussa"},{"name":"Hraðtengi"},{"name":"Vörur"}]}}</script>'''
  r=page_details(body,'https://www.barki.is/vorur/1-12')
  self.assertEqual(r['supplier_categories'],['Glussa','Hraðtengi']);self.assertIn('300 bör',r['description']);self.assertTrue(r['image_url']);self.assertNotIn('price',r)
 def test_csp_allows_supplier_images_only_as_images(self):
  import threading,urllib.request
  from http.server import ThreadingHTTPServer
  server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with urllib.request.urlopen('http://127.0.0.1:'+str(server.server_port)+'/') as response:
    csp=response.headers['Content-Security-Policy'];self.assertIn("img-src 'self' https:",csp);self.assertIn("script-src 'self'",csp)
  finally:server.shutdown();server.server_close()
