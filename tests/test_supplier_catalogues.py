import unittest
from supplier_catalogues import parse_directory,sitemap_urls

class DirectoriesTest(unittest.TestCase):
 def test_no_price_or_pack_inferred_from_nearby_cards(self):
  r=parse_directory('rubix','Rúbix','<h1>Stálbor 5mm</h1><p>frá 100 kr.</p>','https://rubix.is/vorur/001')
  self.assertIsNone(r['price']);self.assertIsNone(r['pack_quantity']);self.assertEqual(r['sku'],'001')
 def test_family_identifier_is_not_an_orderable_sku(self):
  r=parse_directory('barki','Barki','<h1>Tricoflex</h1><p>VNR: 20-10-XXXXXX</p>','https://www.barki.is/vorur/tricoflex')
  self.assertEqual(r['sku'],'');self.assertIsNone(r['price'])
 def test_wurth_preserves_order_number(self):
  r=parse_directory('wurth','Würth','<h1>Hnífur</h1><span id="sku-1">0715 66 530</span>','https://wurth.is/hnifur')
  self.assertEqual(r['sku'],'0715 66 530')
 def test_sitemap_excludes_embedded_image_urls(self):
  xml='<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"><url><loc>https://example.com/product</loc><image:image><image:loc>https://example.com/photo</image:loc></image:image></url></urlset>'
  self.assertEqual(sitemap_urls(xml),['https://example.com/product'])
 def test_iskraft_does_not_inherit_husa_tax_or_supplier(self):
  r=parse_directory('iskraft','Ískraft','<span class="main-sku">0001</span><h2>Töfluvír</h2>','https://iskraft.husa.is/a/b/c/d')
  self.assertEqual(r['supplier'],'Ískraft');self.assertIsNone(r['vat_included']);self.assertIsNone(r['price'])

 def test_unicode_url_is_encoded_without_changing_existing_escapes(self):
  from unittest.mock import patch,MagicMock
  from market_sync import Client
  client=Client.__new__(Client);client.origin='https://www.barki.is';client.last=0;client.delay=0
  response=MagicMock();response.read.return_value=b'ok';response.headers={}
  opener=MagicMock();opener.open.return_value.__enter__.return_value=response
  with patch('market_sync.build_opener',return_value=opener):
   client.raw('https://www.barki.is/vorur/þiltengi%20stál')
  url=opener.open.call_args.args[0].full_url
  self.assertIn('%C3%BE',url);self.assertIn('%20',url);self.assertNotIn('%2520',url)

 def test_rubix_main_price_ignores_related_products(self):
  body='<h1>Test</h1><p class="text-title-l">1.234 kr.</p><h2>Tengdar vörur</h2><p class="text-title-l">99 kr.</p>'
  r=parse_directory('rubix','Rúbix',body,'https://rubix.is/vorur/001')
  self.assertEqual(r['price'],1234);self.assertIsNone(r['vat_included'])
  body=body.replace('1.234 kr.','frá 1.234 kr.')
  self.assertIsNone(parse_directory('rubix','Rúbix',body,'https://rubix.is/vorur/001')['price'])

 def test_cookie_heading_is_not_a_product_name(self):
  r=parse_directory('isfell','Ísfell','<h1>Vafraköku</h1><h1>Öryggishjálmur &#8211; GeckoHead</h1>','https://isfell.is/vorur/hjalmur/')
  self.assertEqual(r['name'],'Öryggishjálmur – GeckoHead')

 def test_store_api_supplier_identity_and_cursor(self):
  import json
  from supplier_catalogues import collect
  class Client:
   origin='https://www.dynjandi.is'
   def get(self,url):
    assert 'page=2&' in url
    return json.dumps([dict(id=1,name='Öryggishjálmur',sku='001',permalink=self.origin+'/vara/',type='simple',prices=dict(price='0',currency_minor_unit=0))]),{'X-WP-TotalPages':'3','X-WP-Total':'250'}
  rows,state=collect('dynjandi','Dynjandi',Client(),[],{'next_page':2},lambda _:None)
  self.assertEqual(rows[0]['supplier'],'Dynjandi')
  self.assertEqual(rows[0]['key'],'dynjandi-api-1')
  self.assertEqual(rows[0]['sku'],'001')
  self.assertIsNone(rows[0]['price'])
  self.assertEqual(state['next_page'],3)
