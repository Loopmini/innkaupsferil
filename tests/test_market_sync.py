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

class LiveProgressTest(unittest.TestCase):
 def test_fast_supplier_reports_before_slow_and_change_counts(self):
  import threading,tempfile,json
  from pathlib import Path
  from unittest.mock import patch
  import market_sync as m
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);release=threading.Event();slow_started=threading.Event();observed=[];original=m.atomic
   prior={'key':'old','supplier':'Þór hf.','name':'Bor','price':100,'currency':'ISK','availability':'unknown','observed_at':'2026-01-01'}
   original(root/'data/market-live.json',{'products':[prior],'meta':{}})
   def save(path,data):
    original(path,data)
    if path.name=='market-status.json' and data.get('runtime',{}).get('husa',{}).get('phase')=='ok' and data.get('runtime',{}).get('thor',{}).get('phase')=='running':
     observed.append(json.loads(path.read_text(encoding='utf-8')));release.set()
   def slow(client,previous,state,progress):
    progress({'stage':'Síða 1/2','loaded':1,'expected':2});slow_started.set()
    if not release.wait(3):raise ValueError('fast source progress never arrived')
    return [{**prior,'price':120}],{'status':'ok','loaded':1}
   def fast(*args):
    if not slow_started.wait(3):raise ValueError('slow source never started')
    return [{'key':'new','supplier':'Húsasmiðjan','name':'Vara','price':50,'currency':'ISK','availability':'unknown','observed_at':'2026-01-01'}],{'status':'ok','loaded':1}
   with patch('market_sync.Client'),patch('market_sync.atomic',side_effect=save),patch('market_sync.thor',side_effect=slow),patch('market_sync.husa',side_effect=fast):
    r=m.run(root,selected=['thor','husa'])
   self.assertTrue(observed);self.assertEqual(observed[0]['runtime']['thor']['stage'],'Síða 1/2')
   self.assertEqual(r['runtime']['thor']['changed_products'],1);self.assertEqual(r['runtime']['husa']['new_products'],1)
   self.assertFalse(r['running']);self.assertEqual(r['phase'],'saved')
