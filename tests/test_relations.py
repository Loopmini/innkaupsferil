import copy,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import app,product_relations as relations,taxonomy

class RelationsTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.offers=[dict(id=1,name='Naglabyssa A',classification={'id':'tools.power.nailers'},unit='stk',specifications=dict(nail_length_min_mm=50,nail_length_max_mm=90,nail_diameter_min_mm=2.8,nail_diameter_max_mm=3.4,collation_angle_deg=21,collation_type='plast',nail_head_type='hringur')),dict(id=2,name='Byssunaglar 60 mm',classification={'id':'fasteners.nails.collated'},unit='stk',pack_quantity=1000,specifications=dict(length_mm=60,diameter_mm=3.1,collation_angle_deg=21.0,collation_type='plast',nail_head_type='hringur'))]
  self.patches=[patch.object(app,'ROOT',self.root),patch.object(app,'DB',self.root/'data/catalog.sqlite'),patch.object(app,'catalogue',side_effect=lambda:{'offers':self.offers})]
  for p in self.patches:p.start()
  app.connect().close()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def payload(self,**kwargs):return dict(a=1,b=2,kind='consumable',status='confirmed',evidence='Framleiðandaskjal A, bls. 4',reviewed=True,**kwargs)
 def test_suggestions_are_never_confirmed_and_missing_is_not_possible(self):
  self.assertEqual(relations.candidate(*self.offers)['status'],'possible')
  del self.offers[1]['specifications']['nail_head_type']
  self.assertEqual(relations.candidate(*self.offers)['status'],'related')
  self.offers[1]['specifications']['length_mm']=95
  self.assertIn('length_mm',relations.candidate(*self.offers)['conflicts'])
  with self.assertRaises(ValueError):relations.save(app,self.payload())
 def test_source_and_explicit_review_required(self):
  for change in ({'reviewed':False},{'evidence':''},{'b':1},{'b':999}):
   data=self.payload();data.update(change)
   with self.assertRaises(ValueError):relations.save(app,data)
 def test_bidirectional_persistent_and_no_identity_merge(self):
  before=copy.deepcopy(self.offers);relations.save(app,self.payload())
  for oid,target in [(1,2),(2,1)]:
   result=relations.listing(app,oid);self.assertEqual(result['relations'][0]['target_id'],target);self.assertEqual(result['relations'][0]['status'],'confirmed');self.assertEqual(len(result['history']),1)
  self.assertEqual(before,self.offers)
  with sqlite3.connect(app.DB) as db:self.assertEqual(db.execute('SELECT count(*) FROM product_relations').fetchone()[0],1)
 def test_new_specs_demote_confirmation_and_preserve_history(self):
  relations.save(app,self.payload());self.offers[1]['pack_quantity']=500
  result=relations.listing(app,1)['relations'][0]
  self.assertTrue(result['needs_review']);self.assertEqual(result['status'],'related');self.assertEqual(result['stored_status'],'confirmed')
  with self.assertRaises(ValueError):relations.save(app,self.payload())
  data=self.payload(expected_at=result['updated_at']);data['status']='incompatible';relations.save(app,data)
  self.offers[1]['specifications']['length_mm']=70
  self.assertEqual(relations.listing(app,2)['relations'][0]['status'],'incompatible')
  self.assertEqual(len(relations.listing(app,2)['history']),2)
 def test_deleted_target_remains_visible(self):
  relations.save(app,self.payload());self.offers.pop()
  r=relations.listing(app,1)['relations'][0];self.assertTrue(r['needs_review']);self.assertEqual(r['status'],'related')
 def test_classification_and_manual_correction_survive_incoming_conflict(self):
  self.assertEqual(taxonomy.detect('Naglabyssa 18V'),'tools.power.nailers')
  self.assertEqual(taxonomy.detect('Byssunaglar 60mm'),'fasteners.nails.collated')
  override=taxonomy.validate_override({'classification_id':'fasteners.nails.collated','specifications':{'length_mm':60},'use_cases':['Timburverk']})
  o={'name':'Byssunaglar','specifications':{'length_mm':70}}
  taxonomy.enrich(o,override)
  self.assertEqual(o['specifications']['length_mm'],60)
  self.assertIn('length_mm',o['specification_conflicts'])
  self.assertIn('Timburverk',o['search_tags'])

 def test_changed_source_flags_classification_without_replacing_manual_choice(self):
  o={'name':'Naglabyssa A'}
  override={'classification_id':'tools.power.nailers','source_snapshot':taxonomy.source_snapshot(o)}
  self.assertFalse(taxonomy.classify(o,override)['needs_review'])
  o['name']='Byssunaglar 60 mm'
  c=taxonomy.classify(o,override);self.assertEqual(c['id'],'tools.power.nailers');self.assertTrue(c['needs_review'])
