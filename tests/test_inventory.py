import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import market_sync as m

class InventoryTest(unittest.TestCase):
 def test_quick_index_compares_urls_without_fetching_products_or_removing_data(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);seen=[];urls=['https://www.husa.is/a/b/c/one','https://www.husa.is/a/b/c/two']
   row={'key':'old','supplier':'Húsasmiðjan','price':100,'currency':'ISK','availability':'unknown','observed_at':'2026-01-01'}
   m.atomic(root/'data/market-live.json',{'products':[row],'meta':{}})
   class Client:
    robot_status='test'
    def __init__(self,origin):self.origin=origin
    def get(self,url,**kwargs):
     seen.append(url)
     if not url.endswith('/sitemap.xml'):raise AssertionError('Quick check fetched a product')
     return '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+u+'</loc></url>' for u in urls)+'</urlset>',{}
   with patch('market_sync.Client',Client):
    first=m.run(root,selected=['husa'],index_only=True)['sources']['husa']['index']
    self.assertTrue(first['baseline']);self.assertIsNone(first['missing'])
    urls[:]=[urls[0],'https://www.husa.is/a/b/c/three']
    second=m.run(root,selected=['husa'],index_only=True)['sources']['husa']['index']
    self.assertEqual((second['added'],second['missing'],second['total']),(1,1,2))
    self.assertEqual(m.load(root/'data/market-live.json',{})['products'],[row])
    urls.clear()
    result=m.run(root,selected=['husa'],index_only=True)
    self.assertEqual(result['sources']['husa']['status'],'error')
    self.assertEqual(len(m.load(root/'data/market-index.json',{})['husa']['urls']),2)
   self.assertEqual(len(seen),3)
 def test_unsupported_quick_source_does_not_make_network_requests(self):
  with tempfile.TemporaryDirectory() as td:
   with patch('market_sync.Client') as client:
    r=m.run(Path(td),selected=['iskraft'],index_only=True)
    client.assert_not_called();self.assertIn('iskraft',r['skipped'])
