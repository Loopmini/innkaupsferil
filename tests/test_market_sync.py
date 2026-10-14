import unittest
from market_sync import parse_thor,parse_husa

class MarketTest(unittest.TestCase):
 def product(self,**overrides):
  p={'id':1,'name':'Test bor 5mm (10 stk)','permalink':'https://thor.is/vara/test/','sku':'T01','type':'simple','prices':{'price':'330000','currency_code':'ISK','currency_minor_unit':2,'price_range':None},'is_in_stock':True}
  p.update(overrides);return p
 def test_currency_and_pack(self):
  r=parse_thor(self.product());self.assertEqual(r['price'],3300);self.assertEqual(r['pack_quantity'],10);self.assertIsNone(r['vat_included'])
 def test_variants_and_zero_not_quoted(self):
  self.assertIsNone(parse_thor(self.product(type='variable'))['price'])
  self.assertIsNone(parse_thor(self.product(prices={'price':'0','currency_code':'ISK','currency_minor_unit':0}))['price'])
 def test_missing_pack_not_assumed(self):
  self.assertIsNone(parse_thor(self.product(name='Test hammer'))['pack_quantity'])
 def test_bad_currency_precision_rejected(self):
  with self.assertRaises(ValueError):parse_thor(self.product(prices={'price':'123','currency_minor_unit':None}))
 def test_husa_main_price_not_unrelated_card(self):
  html='<div class="main-price"><span class="price-wrapper">999<span class="unit">kr.</span></span></div><span class="main-sku">001</span><h2>Stálbor 5mm</h2><div class="main-price"><span class="price-wrapper">1.290<span class="unit">kr.</span></span></div>'
  r=parse_husa(html,'https://www.husa.is/verkfaeri/product')
  self.assertEqual(r['sku'],'001');self.assertEqual(r['price'],1290);self.assertIsNone(r['vat_rate'])
 def test_category_pages_not_products(self):
  self.assertIsNone(parse_husa('<h2>Borar</h2><div>1.290 kr.</div>','https://www.husa.is/category'))

class PersistenceTest(unittest.TestCase):
 def test_failed_run_preserves_previous_snapshot(self):
  import tempfile,json
  from pathlib import Path
  from unittest.mock import patch
  from market_sync import run
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'data').mkdir()
   prior={'products':[{'key':'old','supplier':'Þór hf.','price':100,'currency':'ISK','availability':'unknown','observed_at':'2026-01-01T00:00:00+00:00'}],'meta':{}}
   (root/'data/market-live.json').write_text(json.dumps(prior))
   with patch('market_sync.Client',side_effect=ValueError('Network down')):result=run(root,selected=['thor'])
   actual=json.loads((root/'data/market-live.json').read_text())
   self.assertEqual(actual['products'],prior['products']);self.assertEqual(result['sources']['thor']['status'],'error')
   self.assertFalse((root/'data/market-sync.lock').exists())
 def test_incomplete_pagination_not_published_as_full(self):
  from market_sync import thor
  class Client:
   robot_status='test'
   def get(self,url):return '[]',{'X-WP-Total':'10','X-WP-TotalPages':'1'}
  with self.assertRaises(ValueError):thor(Client(),[],{},lambda x:None)
