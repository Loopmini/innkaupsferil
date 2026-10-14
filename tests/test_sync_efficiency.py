import unittest
from unittest.mock import Mock
from market_sync import Client,AccessBlocked,husa
import taxonomy

class SyncEfficiencyTest(unittest.TestCase):
 def test_hand_saw_not_target_material(self):
  for name in ('Handsög krossviður 550mm','Stanley handsög fyrir krossvið','Krossviðarsög 350mm'):
   self.assertEqual(taxonomy.detect(name),'tools.hand.handsaws')
  self.assertEqual(taxonomy.detect('Handsagarblað fyrir krossvið'),'tools.cutting.sawblades')
  self.assertEqual(taxonomy.detect('Krossviður 18 mm'),'building.boards.plywood')
 def test_robots_rejection_never_fetches_product(self):
  c=Client.__new__(Client);c.robot=Mock();c.robot.can_fetch.return_value=False;c.raw=Mock()
  with self.assertRaises(AccessBlocked):c.get('https://www.husa.is/a/b/c/d')
  c.raw.assert_not_called()
 def test_sitemap_reused_in_pass_but_products_are_fresh(self):
  c=Client.__new__(Client);c.robot=None;c.sitemap_cache={};c.raw=Mock(return_value=('body',{}))
  for _ in range(2):c.get('https://www.husa.is/sitemap.xml')
  self.assertEqual(c.raw.call_count,1)
  for _ in range(2):c.get('https://www.husa.is/a/b/c/d')
  self.assertEqual(c.raw.call_count,3)
  c.sitemap_cache={};c.get('https://www.husa.is/sitemap.xml');self.assertEqual(c.raw.call_count,4)
 def test_husa_old_products_are_not_fetched_twice_per_batch(self):
  urls=['https://www.husa.is/a/b/c/'+str(i) for i in range(3)]
  class Fake:
   robot_status='test';index_only=False
   def __init__(self):self.calls=[]
   def get(self,url,**kw):
    self.calls.append(url)
    if 'sitemap' in url:return '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+u+'</loc></url>' for u in urls)+'</urlset>',{}
    return '<span class="main-sku">'+url[-1]+'</span><h2>Vara</h2>',{}
  c=Fake();previous=[{'key':'keep','url':urls[0],'observed_at':'2020-01-01T00:00:00+00:00'}]
  rows,state=husa(c,previous,{},lambda x:None,3)
  self.assertEqual(c.calls[1:],urls);self.assertEqual(state['checked_this_run'],3);self.assertEqual(state['cursor'],0)
  self.assertTrue(any(r['key']=='keep' for r in rows))
