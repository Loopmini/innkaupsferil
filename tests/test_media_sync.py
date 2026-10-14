import unittest,json,tempfile,threading
from pathlib import Path
from unittest.mock import Mock,patch
import market_sync as m,app
from product_extras import page_details,preserve_media

class MediaSyncTest(unittest.TestCase):
 def test_product_image_beats_site_logo_and_uses_matching_product(self):
  body='<meta property="og:image" content="/logo.png"><script type="application/ld+json">'+json.dumps([{'@type':'Product','url':'https://shop.is/other','image':'/wrong.jpg'},{'@type':'Product','url':'https://shop.is/item','image':{'contentUrl':'/correct.jpg'},'subjectOf':{'@type':'DigitalDocument','url':'/download?id=1','name':'Tækniblað'}}])+'</script>'
  r=page_details(body,'https://shop.is/item');self.assertEqual(r['image_url'],'https://shop.is/correct.jpg');self.assertEqual(r['documents'][0]['url'],'https://shop.is/download?id=1');self.assertIn('format',r['documents'][0])
 def test_ambiguous_recommendations_do_not_supply_product_image(self):
  body='<script type="application/ld+json">'+json.dumps([{'@type':'Product','url':'/a','image':'/a.jpg'},{'@type':'Product','url':'/b','image':'/b.jpg'}])+'</script>'
  self.assertEqual(page_details(body,'https://shop.is/item')['image_url'],'')
 def test_lazy_product_image_and_query_pdf(self):
  r=page_details('<img src="/placeholder.png" data-src="/actual.jpg" class="product-image"><a href="/get?file=data.pdf">Gagnablað</a><a href="/terms.pdf">Skilmálar</a><a href="#technical">Tæknigögn</a>','https://shop.is/item')
  self.assertEqual(r['image_url'],'https://shop.is/actual.jpg');self.assertEqual(len(r['documents']),1)
 def test_husa_collects_documents_without_another_request(self):
  r=m.parse_husa('<span class="main-sku">1</span><h2>Vara</h2><a href="/doc.pdf">Handbók</a>','https://www.husa.is/item')
  self.assertEqual(len(r['documents']),1);self.assertEqual(r['details_version'],5);self.assertIn('details_checked_at',r)
 def test_missing_media_preserves_last_known_with_review_marker(self):
  old={'image_url':'https://shop.is/a.jpg','documents':[{'url':'https://shop.is/a.pdf','name':'A'}]}
  r=preserve_media({'image_url':'','documents':[]},old)
  self.assertTrue(r['image_retained']);self.assertTrue(r['documents'][0]['retained']);self.assertNotIn('retained',old['documents'][0])
 def test_three_timeouts_stop_supplier_and_success_resets_counter(self):
  c=m.Client.__new__(m.Client);c.robot=None;c.raw=Mock(side_effect=TimeoutError('timeout'))
  for _ in range(2):
   with self.assertRaises(TimeoutError):c.get('https://shop.is/item')
  with self.assertRaises(RuntimeError):c.get('https://shop.is/item')
  c.raw=Mock(return_value=('ok',{}));c.get('https://shop.is/item');self.assertEqual(c.failures,0)
 def test_four_suppliers_overlap(self):
  with tempfile.TemporaryDirectory() as td:
   barrier=threading.Barrier(4);seen=[]
   def work(*args):
    seen.append(threading.get_ident());barrier.wait(timeout=3);return [],{'status':'ok','loaded':0}
   with patch('market_sync.Client'),patch('market_sync.thor',side_effect=work),patch('market_sync.husa',side_effect=work),patch('supplier_catalogues.collect',side_effect=work):
    m.run(Path(td),selected=['thor','husa','barki','rubix'])
   self.assertEqual(len(set(seen)),4)
 def test_client_reused_between_batches(self):
  with tempfile.TemporaryDirectory() as td:
   cache={}
   with patch('market_sync.Client') as make,patch('market_sync.thor',return_value=([],{'status':'ok','loaded':0})):
    for _ in range(2):m.run(Path(td),selected=['thor'],client_cache=cache)
   self.assertEqual(make.call_count,1)
 def test_new_crawler_metadata_beats_old_detail_cache(self):
  with tempfile.TemporaryDirectory() as td,patch.object(app,'DB',Path(td)/'test.sqlite'),patch('app.read_supplements',return_value=([{'id':-9,'name':'Vara','details_checked_at':'2026-10-14T10:00:00+00:00','image_url':'https://shop.is/new.jpg'}],{})):
   with app.connect() as db:db.execute('INSERT INTO product_details VALUES(?,?,?)',(-9,json.dumps({'details_checked_at':'2026-10-13T10:00:00+00:00','image_url':'https://shop.is/old.jpg'}),'2026-10-13T10:00:00+00:00'))
   self.assertEqual(app.catalogue()['offers'][0]['image_url'],'https://shop.is/new.jpg')

 def test_gzip_response_is_decoded_and_size_limited(self):
  import io,gzip
  class Response(io.BytesIO):
   headers={'Content-Encoding':'gzip'}
  c=m.Client.__new__(m.Client);c.origin='https://thor.is';c.last=0;c.delay=0;c.opener=Mock()
  c.opener.open.return_value=Response(gzip.compress('Gögn'.encode()))
  self.assertEqual(c.raw('https://thor.is/item')[0],'Gögn')
  c.opener.open.return_value=Response(gzip.compress(b'A'*100))
  with self.assertRaises(ValueError):c.raw('https://thor.is/item',limit=10)
