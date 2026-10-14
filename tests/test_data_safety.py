import csv,io,json,sqlite3,tempfile,unittest,subprocess,sys,os
from pathlib import Path
from unittest.mock import patch
import app,import_manager,data_safety

class SafetyTest(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);self.db=self.root/'data/catalog.sqlite'
  self.p1=patch.object(app,'ROOT',self.root);self.p2=patch.object(app,'DB',self.db);self.p1.start();self.p2.start();app.connect().close()
 def tearDown(self):self.p1.stop();self.p2.stop();self.t.cleanup()
 def content(self,price=100):
  row=dict(zip(app.FIELDS,['A','001','Bor','Borar','','','',str(price),'ISK','false','24','10','stk','https://example.com/bor','2026-01-01']))
  stream=io.StringIO();w=csv.DictWriter(stream,fieldnames=app.FIELDS);w.writeheader();w.writerow(row);return stream.getvalue()
 def test_preview_commit_repeat_undo_and_reopen(self):
  p=import_manager.preview(app,self.content(),'test.csv')
  with app.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM offers').fetchone()[0],0)
  r=import_manager.commit(app,p['token']);self.assertTrue(data_safety.path(self.root,r['backup']).exists())
  p2=import_manager.preview(app,self.content(),'again.csv');self.assertEqual(p2['counts']['unchanged'],1)
  import_manager.commit(app,p2['token'])
  with sqlite3.connect(self.db) as db:self.assertEqual(db.execute('SELECT count(*) FROM offers').fetchone()[0],1)
  import_manager.undo(app,p2['token'])
  with sqlite3.connect(self.db) as db:self.assertEqual(db.execute('SELECT price FROM offers').fetchone()[0],100)
  p3=import_manager.preview(app,self.content(200),'updated.csv');import_manager.commit(app,p3['token']);import_manager.undo(app,p3['token'])
  code='import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); assert c.execute("SELECT price FROM offers").fetchone()[0]==100'
  subprocess.run([sys.executable,'-c',code,str(self.db)],check=True)
 def test_stale_preview_rejected(self):
  p=import_manager.preview(app,self.content(),'test.csv');app.import_csv(self.content(200))
  with self.assertRaises(ValueError):import_manager.commit(app,p['token'])
 def test_backup_restore_keeps_secret_and_rescue(self):
  app.import_csv(self.content());(self.root/'.env').write_text('secret-test-only')
  b=data_safety.create(self.root,self.db,'manual');app.import_csv(self.content(300))
  r=data_safety.restore(self.root,self.db,b['name'])
  with app.connect() as db:self.assertEqual(db.execute('SELECT price FROM offers').fetchone()[0],100)
  self.assertTrue(data_safety.path(self.root,r['rescue_backup']).exists());self.assertEqual((self.root/'.env').read_text(),'secret-test-only')
 def test_undo_refuses_to_remove_used_product(self):
  p=import_manager.preview(app,self.content(),'test.csv');import_manager.commit(app,p['token'])
  with app.connect() as db:db.execute("INSERT INTO bom_lists VALUES(1,'B','now','[]','{\"1\":[1]}','test')")
  with self.assertRaises(ValueError):import_manager.undo(app,p['token'])

 def test_corrupt_snapshot_rejected_before_current_data_changes(self):
  import zipfile
  app.import_csv(self.content());b=data_safety.create(self.root,self.db)
  target=data_safety.path(self.root,b['name'])
  with zipfile.ZipFile(target) as z:entries={n:z.read(n) for n in z.namelist()}
  entries['catalog.sqlite']=b'corrupt'
  with zipfile.ZipFile(target,'w') as z:
   for n,raw in entries.items():z.writestr(n,raw)
  with self.assertRaises(ValueError):data_safety.restore(self.root,self.db,b['name'])
  with app.connect() as db:self.assertEqual(db.execute('SELECT price FROM offers').fetchone()[0],100)
