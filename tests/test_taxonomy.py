import unittest
import taxonomy as t
import bom

class TaxonomyTest(unittest.TestCase):
    def test_tree_unique_paths_and_existing_categories_mapped(self):
        paths=[tuple(p) for p in t.LEAVES.values()]
        self.assertEqual(len(paths),len(set(paths)))
        self.assertTrue(all(v in t.LEAVES for v in t.LEGACY.values()))
        self.assertEqual(t.LEAVES['building.timber.cladding'],['Byggingarefni','Timbur','Timburklæðningar'])
    def test_timber_and_boards(self):
        for name,leaf in [('Burðarvirkistimbur C24','building.timber.structural'),('Gagnvarið timbur','building.timber.treated'),('Pallaefni gagnvarið','building.timber.decking'),('Límtré GL30c','building.timber.glulam'),('LVL biti','building.timber.lvl'),('Fótlisti fura','building.timber.mouldings'),('Krossviður','building.boards.plywood'),('OSB 3','building.boards.osb'),('MDF plata','building.boards.mdf'),('Gifsplata','building.boards.gypsum')]:
            with self.subTest(name=name):self.assertEqual(t.enrich({'name':name})['classification']['id'],leaf)
    def test_tools_and_chemicals_not_building_materials(self):
        for name in ['Sagarblað fyrir MDF','MAKITA Gifsfræsari 18V','Gifsskrúfur á belti','Smurefni fyrir patrónur','Afeinangrunartöng','Einangrunarlímband','Steypuvíbrator']:
            with self.subTest(name=name):self.assertNotEqual(t.enrich({'name':name})['classification']['path'][0],'Byggingarefni')
    def test_explicit_dimensions_and_unknown_values(self):
        o=t.enrich({'name':'Burðarvirkistimbur 45x95 mm C24','description':'Lengd: 4,2 m. Greni.'})
        self.assertEqual(o['specifications'],{'thickness_mm':45,'width_mm':95,'length_mm':4200,'strength_class':'C24','material':'Greni'})
        self.assertIn('treatment',o['missing_specifications']);self.assertNotIn('unit',o['specifications'])
        self.assertEqual(t.enrich({'name':'Timbur 45x95'})['specifications'],{})
    def test_conflicting_evidence_is_not_guessed(self):
        o=t.enrich({'name':'Timbur 45x95 mm C24','description':'Þykkt 48 mm. C18.'})
        self.assertNotIn('thickness_mm',o['specifications']);self.assertNotIn('strength_class',o['specifications'])
        self.assertIn('thickness_mm',o['specification_conflicts'])
    def test_manual_override_survives_source_refresh_and_can_mark_unknown(self):
        override=t.validate_override({'classification_id':'building.timber.decking','specifications':{'width_mm':120,'thickness_mm':None},'search_tags':['Pallur']})
        for name in ['Timbur 45x95 mm','Timbur 48x98 mm']:
            o=t.enrich({'name':name},override)
            self.assertEqual(o['classification']['id'],'building.timber.decking')
            self.assertEqual(o['specifications']['width_mm'],120);self.assertNotIn('thickness_mm',o['specifications']);self.assertIn('Pallur',o['search_tags'])
    def test_manual_legacy_is_preserved_and_mapped(self):
        o=t.enrich({'name':'Skrúfa','manual_category':'Borar og snittvörur'})
        self.assertEqual(o['classification']['id'],'tools.drilling.unspecified');self.assertTrue(o['classification']['manual'])
    def test_description_category_evidence_and_unknown(self):
        self.assertEqual(t.enrich({'name':'ABC','description':'Krossviður úr birki.'})['classification']['id'],'building.boards.plywood')
        self.assertTrue(t.enrich({'name':'ABC'})['classification']['needs_review'])
    def test_validation_rejects_invalid_specs(self):
        for data in [{'classification_id':'fake'},{'specifications':{'width_mm':-1}},{'specifications':{'width_mm':float('nan')}},{'specifications':{'price':1}},{'search_tags':['x'*61]}]:
            with self.subTest(data=data),self.assertRaises(ValueError):t.validate_override(data)
    def test_bom_explicit_requirements_and_deduplication(self):
        rows,_=bom.parse('heiti,magn,eining,thykkt_mm,breidd_mm,lengd_mm,styrkleikaflokkur\nTimbur,2,m,45,95,4200,C24\nTimbur,1,m,45,95,4200,C18\n'.encode())
        self.assertEqual(len(rows),2);self.assertEqual(rows[0]['specifications']['length_mm'],4200)
        with self.assertRaises(ValueError):bom.parse('heiti,magn,eining,thykkt_mm\nTimbur,2,m,neikvætt\n'.encode())
    def test_structured_technical_data_units(self):
        from product_extras import page_details
        body='<script type="application/ld+json">{"@type":"Product","name":"Timbur","additionalProperty":[{"name":"Length","value":4.2,"unitCode":"MTR"},{"name":"Width","value":95},{"name":"Styrkleikaflokkur","value":"C24"}]}</script>'
        details=page_details(body,'https://example.com/timber')
        o=t.enrich({'name':'Timbur',**details})
        self.assertEqual(o['specifications']['length_mm'],4200)
        self.assertEqual(o['specifications']['strength_class'],'C24')
        self.assertNotIn('width_mm',o['specifications'])
    def test_windows_legacy_encoding_does_not_corrupt_taxonomy(self):
        import subprocess,sys
        script='''
from pathlib import Path
original=Path.read_text
def legacy_default(self,*args,**kwargs):
    if self.name in ('taxonomy.json','legacy-category-rules.json') and not args and 'encoding' not in kwargs:
        kwargs['encoding']='cp1252'
    return original(self,*args,**kwargs)
Path.read_text=legacy_default
import taxonomy
assert taxonomy.LEAVES['tools.hand.hand'][0]=='Verkfæri og fylgihlutir'
assert taxonomy.enrich({'name':'Hamar'})['classification']['id']=='tools.hand.unspecified'
'''
        result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
