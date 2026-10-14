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
   def batch(root,selected):
    key=selected[0];calls.append(key);d=load(root/'data/market-status.json',{});old=d['sources'].get(key,{})
    if key=='blocked':new={'status':'blocked','error':'403'}
    elif key=='pages':new={'status':'partial','next_page':old.get('next_page',1)%3+1}
    else:new={'status':'partial','cursor':(old.get('cursor',0)+2)%5,'expected':5}
    d['sources'][key]=new;atomic(root/'data/market-status.json',d);return d
   with patch('full_sync.SOURCES',{'pages':None,'urls':None,'blocked':None}),patch('full_sync.run',side_effect=batch):r=full_pass(root,threading.Event())
   self.assertEqual(r['status'],'finished');self.assertEqual(set(r['completed']),{'pages','urls'});self.assertEqual(calls.count('blocked'),1);self.assertEqual(calls.count('pages'),3);self.assertEqual(calls.count('urls'),3)
 def test_cancel_after_checkpoint(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);stop=threading.Event()
   def batch(root,selected):
    stop.set();d={'sources':{'a':{'status':'partial','next_page':2}}};atomic(root/'data/market-status.json',d);return d
   with patch('full_sync.SOURCES',{'a':None,'b':None}),patch('full_sync.run',side_effect=batch):r=full_pass(root,stop)
   self.assertEqual(r['status'],'stopped');self.assertEqual(r['batches'],1);self.assertFalse(r['running']);self.assertEqual(load(root/'data/market-status.json',{})['sources']['a']['next_page'],2)
