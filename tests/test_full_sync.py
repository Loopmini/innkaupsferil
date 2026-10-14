import unittest,tempfile,threading
from pathlib import Path
from unittest.mock import patch
from market_sync import atomic,load
from full_sync import full_pass

class FullSyncTest(unittest.TestCase):
 def test_complete_rotation_and_blocked_supplier(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);calls=[]
   atomic(root/'data/market-status.json',{'sources':{'pages':{'next_page':2},'urls':{'cursor':3}}})
   def batch(root,selected,**kwargs):
    calls.extend(selected);d=load(root/'data/market-status.json',{})
    for key in selected:
     old=d['sources'].get(key,{})
     if key=='blocked':new={'status':'blocked','error':'403'}
     elif key=='pages':new={'status':'partial','next_page':old.get('next_page',1)%3+1}
     else:new={'status':'partial','cursor':(old.get('cursor',0)+2)%5,'expected':5}
     d['sources'][key]=new
    atomic(root/'data/market-status.json',d);return d
   with patch('full_sync.SOURCES',{'pages':None,'urls':None,'blocked':None}),patch('full_sync.run',side_effect=batch):r=full_pass(root,threading.Event())
   self.assertEqual(r['status'],'finished');self.assertEqual(set(r['completed']),{'pages','urls'});self.assertEqual(calls.count('blocked'),1);self.assertEqual(calls.count('pages'),3);self.assertEqual(calls.count('urls'),3)
 def test_cancel_after_checkpoint(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);stop=threading.Event()
   def batch(root,selected,**kwargs):
    stop.set();d={'sources':{'a':{'status':'partial','next_page':2}}};atomic(root/'data/market-status.json',d);return d
   with patch('full_sync.SOURCES',{'a':None,'b':None}),patch('full_sync.run',side_effect=batch):r=full_pass(root,stop,selected=['a'])
   self.assertEqual(r['status'],'stopped');self.assertEqual(r['batches'],1);self.assertFalse(r['running']);self.assertEqual(load(root/'data/market-status.json',{})['sources']['a']['next_page'],2)

 def test_selected_supplier_only_and_invalid_selection(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   with patch('full_sync.run',return_value={'sources':{'thor':{'status':'ok'}}}) as run:
    r=full_pass(root,threading.Event(),selected=['thor'])
    self.assertEqual(r['completed'],['thor']);self.assertEqual(run.call_args.kwargs['selected'],['thor'])
    with self.assertRaises(ValueError):full_pass(root,threading.Event(),selected=[])
 def test_sources_overlap_and_unselected_data_survives(self):
  import market_sync
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);barrier=threading.Barrier(2);seen=[]
   old={'key':'keep','supplier':'Unselected','price':10,'currency':'ISK','availability':'unknown','observed_at':'2026-01-01'}
   atomic(root/'data/market-live.json',{'products':[old],'meta':{}})
   def worker(*args):
    seen.append(threading.get_ident());barrier.wait(timeout=3)
    return [],{'status':'ok','loaded':0}
   with patch('market_sync.Client'),patch('market_sync.thor',side_effect=worker),patch('market_sync.husa',side_effect=worker):
    market_sync.run(root=root,selected=['thor','husa'])
   self.assertEqual(len(set(seen)),2)
   self.assertEqual(load(root/'data/market-live.json',{})['products'],[old])
 def test_api_rejects_empty_or_unknown_selection(self):
  import app
  for selected in ([],['unknown'],'thor'):
   with self.assertRaises(ValueError):app.start_sync(selected=selected)
