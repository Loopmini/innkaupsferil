import unittest,tempfile,json
from pathlib import Path
from supplements import read_supplements,safe_url

class SupplementsTest(unittest.TestCase):
 def test_preserves_purchase_units_and_null_prices(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'data').mkdir()
   payload={'meta':{'invoiceRows':1},'products':[{'id':'private-test','name':'Test','supplier':'Test','sku':'001','sourceType':'invoice','quantity':7,'unit':'pk','quantities':{'2026':7},'lines':[{'date':'2026-01-01','quantity':7,'unit':'pk'}],'productUrl':'javascript:alert(1)'}]}
   (root/'data/legacy-project.json').write_text(json.dumps(payload))
   rows,meta=read_supplements(root)
   self.assertEqual(rows[0]['quantity'],7);self.assertEqual(rows[0]['unit'],'pk')
   self.assertIsNone(rows[0]['price']);self.assertIsNone(rows[0]['pack_quantity'])
   self.assertEqual(rows[0]['url'],'');self.assertEqual(len(rows[0]['lines']),1)
   self.assertEqual(read_supplements(root)[0][0]['id'],rows[0]['id'])
 def test_market_price_semantics(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'seeds').mkdir()
   (root/'seeds/public-market.json').write_bytes((Path(__file__).parents[1]/'seeds/public-market.json').read_bytes())
   rows,meta=read_supplements(root)
  public=[r for r in rows if r['source_kind']=='market']
  self.assertEqual(len(public),6)
  thor=next(r for r in public if r['sku']=='MAP-60707-10')
  self.assertEqual(thor['price'],3300);self.assertIsNone(thor['unit_price'])
  husa=next(r for r in public if r['sku']=='5029970')
  self.assertAlmostEqual(husa['unit_price'],3911/1.24/10)
  self.assertTrue(all(r['price'] is None for r in public if r['supplier'] in ('Fossberg','BYKO')))
 def test_safe_links(self):
  self.assertEqual(safe_url('javascript:evil'),'')
  self.assertEqual(safe_url('https://user:password@example.com'),'')
  self.assertEqual(safe_url('https://example.com'),'https://example.com')
