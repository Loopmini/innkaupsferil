import csv,io,json,tempfile,unittest,sqlite3
from pathlib import Path
from unittest.mock import patch
import app,procurement as p

class ProcurementTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.a=patch.object(app,'ROOT',self.root);self.b=patch.object(app,'DB',self.root/'data/catalog.sqlite');self.a.start();self.b.start();app.connect().close()
 def tearDown(self):self.a.stop();self.b.stop();self.tmp.cleanup()
 def make_bom(self):
  data={'name':'Prófun','text':'heiti,magn,eining\nBor,11,stk\n'}
  pre=p.preview_bom(app,data);self.assertEqual(len(pre['rows']),1);return p.commit_bom(app,pre['token'])['id'],data
 def test_bom_duplicate_preview_and_settings(self):
  bid,data=self.make_bom();again=p.commit_bom(app,p.preview_bom(app,data)['token']);self.assertTrue(again['reused']);self.assertEqual(again['id'],bid)
  value=p.validate_settings({'project':'Verk','location':'Hús','wanted_date':'2030-01-01','currency':'ISK','suppliers':{'A':{'shipping':0,'other_fees':None,'status':'confirmed'}}})
  self.assertIsNone(value['suppliers']['A']['other_fees'])
  with app.connect() as db:db.execute('INSERT INTO bom_settings VALUES(?,?)',(bid,json.dumps(value)))
  with app.connect() as db:self.assertEqual(p.get_settings(db,bid)['location'],'Hús')
 def reply(self,bid,price='100'):
  with app.connect() as db:raw=p.rfq(db,bid).decode('utf-8-sig')
  reader=csv.DictReader(io.StringIO(raw));rows=list(reader);rows[0].update(supplier='Birgir A',price=price,currency='ISK',vat_included='false',vat_rate='24',pack_quantity='10',min_quantity='0',observed_at='2026-01-01',source='Tilboð A',sku='A1')
  out=io.StringIO();w=csv.DictWriter(out,fieldnames=reader.fieldnames);w.writeheader();w.writerows(rows);return out.getvalue()
 def test_rfq_preview_repeat_update_undo_same_line_and_unknown_price(self):
  bid,_=self.make_bom();pre=p.parse_replies(app,bid,self.reply(bid),'reply.csv')
  with app.connect() as db:self.assertEqual(len(p.reply_offers(db)),0)
  p.commit_replies(app,pre['token'])
  with app.connect() as db:first=p.reply_offers(db)[0]
  pre2=p.parse_replies(app,bid,self.reply(bid,'200'),'reply2.csv');p.commit_replies(app,pre2['token'])
  with app.connect() as db:
   offers=p.reply_offers(db);self.assertEqual(len(offers),1);self.assertEqual(offers[0]['id'],first['id']);self.assertEqual(offers[0]['net_price'],200);self.assertEqual(offers[0]['bom_line_id'],'1')
  p.undo_document(app,pre2['token'])
  with app.connect() as db:self.assertEqual(p.reply_offers(db)[0]['net_price'],100)
  pre3=p.parse_replies(app,bid,self.reply(bid,''),'reply3.csv');p.commit_replies(app,pre3['token'])
  with app.connect() as db:self.assertIsNone(p.reply_offers(db)[0]['net_price'])
 def test_wrong_bom_line_rejected(self):
  bid,_=self.make_bom();text=self.reply(bid).replace(str(bid)+',1,',str(bid)+',999,',1)
  with self.assertRaises(ValueError):p.parse_replies(app,bid,text,'wrong.csv')
 def test_quote_specs_not_assumed_from_request(self):
  bid,_=self.make_bom();pre=p.parse_replies(app,bid,self.reply(bid),'reply.csv');p.commit_replies(app,pre['token'])
  with app.connect() as db:self.assertEqual(p.reply_offers(db)[0]['specifications'],{})
