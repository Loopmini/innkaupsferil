import csv,io,json,sqlite3,tempfile,unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
import app,procurement,import_manager,assistant_reader,ai_support

class WorkspaceTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.patches=[patch.object(app,'ROOT',self.root),patch.object(app,'DB',self.root/'data/catalog.sqlite')]
  for p in self.patches:p.start()
  app.connect().close()
 def tearDown(self):
  for p in self.patches:p.stop()
  self.tmp.cleanup()
 def csv(self):
  out=io.StringIO();w=csv.DictWriter(out,fieldnames=app.FIELDS);w.writeheader()
  for sku in ('001','002'):
   w.writerow(dict(zip(app.FIELDS,['A',sku,'Bor '+sku,'Borar','','','','100','ISK','false','24','10','stk','https://example.com/bor','2026-01-01'])))
  return out.getvalue()
 def test_partial_commit_reopen_and_scoped_undo(self):
  p=import_manager.preview(app,self.csv(),'price.csv','A');r=import_manager.commit(app,p['token'],[0]);self.assertEqual(r['pending'],1)
  with closing(sqlite3.connect(app.DB)) as db:self.assertEqual(db.execute('SELECT sku FROM offers').fetchall(),[('001',)])
  with self.assertRaises(ValueError):import_manager.commit(app,p['token'],[0])
  pending=import_manager.pending(app,r['pending_token']);self.assertEqual(pending['rows'][0]['sku'],'002')
  import_manager.commit(app,r['pending_token'],[0]);import_manager.undo(app,p['token'])
  with closing(sqlite3.connect(app.DB)) as db:self.assertEqual(db.execute('SELECT sku FROM offers').fetchall(),[('002',)])
 def test_supplier_mismatch_and_empty_selection_write_nothing(self):
  with self.assertRaises(ValueError):import_manager.preview(app,self.csv(),'price.csv','B')
  p=import_manager.preview(app,self.csv(),'price.csv')
  for bad in ([],[0,0],[True],[-1],[2]):
   with self.assertRaises(ValueError):import_manager.commit(app,p['token'],bad)
  with closing(sqlite3.connect(app.DB)) as db:self.assertEqual(db.execute('SELECT count(*) FROM offers').fetchone()[0],0)
 def test_append_draft_preserves_list_and_existing_requirements(self):
  app.import_csv(self.csv());offers=app.catalogue()['offers'];offer=next(o for o in offers if o['supplier']=='A')
  bid=procurement.commit_bom(app,procurement.preview_bom(app,{'name':'Test','text':'heiti,magn,eining\nStálbor,3,stk\n'})['token'])['id']
  with app.connect() as db:before=json.loads(db.execute('SELECT rows_json FROM bom_lists WHERE id=?',(bid,)).fetchone()[0])
  procurement.draft(app,{'target_id':bid,'entries':[{'id':offer['id'],'quantity':2,'unit':'stk'}]})
  with closing(sqlite3.connect(app.DB)) as db:
   rows=json.loads(db.execute('SELECT rows_json FROM bom_lists WHERE id=?',(bid,)).fetchone()[0]);self.assertEqual(rows[0],before[0]);self.assertEqual(rows[1]['quantity'],2);self.assertEqual(len({r['line_id'] for r in rows}),2)
 def test_assistant_connection_cannot_write_or_attach(self):
  before=app.DB.read_bytes()
  with closing(assistant_reader.connect_readonly(app.DB)) as db:
   for sql in ('DELETE FROM offers','CREATE TABLE bad(x)',"ATTACH DATABASE ':memory:' AS bad",'PRAGMA query_only=OFF','INSERT INTO projects(name) VALUES (\'bad\')'):
    with self.assertRaises(sqlite3.DatabaseError):db.execute(sql)
  self.assertEqual(app.DB.read_bytes(),before)
  with self.assertRaises(ValueError):assistant_reader.context(app.DB,{'sql':'DELETE FROM offers'},[])
 def test_selected_product_is_grounded_without_any_mutation_tools(self):
  offers=[{'id':1,'name':'Klaufhamar','source_kind':'market'}]
  context,ids=assistant_reader.context(app.DB,{'offer_id':1},offers)
  reply={'answer':'Skoðum eiginleika','questions':[],'products':[{'id':1,'reason':'Valin vara'}]}
  with patch.object(ai_support,'ask',side_effect=[{'queries':[]},reply]) as ask:
   result=ai_support.chat('Hvað vantar?',[],offers,context,ids)
  self.assertEqual(result['reviewed'],1);self.assertEqual(ask.call_args.args[1]['active_context']['id'],1)
  with self.assertRaises(ValueError):assistant_reader.context(app.DB,{'offer_id':999},offers)
