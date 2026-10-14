import csv
import io
import tempfile
import unittest
from pathlib import Path
import app
import collect

class CatalogueTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.old=app.DB;app.DB=Path(self.temp.name)/'test.sqlite'
    def tearDown(self):
        app.DB=self.old;self.temp.cleanup()
    def row(self,**overrides):
        r=dict(supplier='Test supplier',sku='TEST-1',name='TEST ONLY',category='Test',brand='Test brand',gtin='',manufacturer_part='ABC',price='1240',currency='ISK',vat_included='true',vat_rate='24',pack_quantity='10',unit='stk',url='https://example.com/product',observed_at='2026-01-01')
        r.update(overrides);return r
    def csv(self,*rows):
        stream=io.StringIO();w=csv.DictWriter(stream,fieldnames=app.FIELDS);w.writeheader();w.writerows(rows);return stream.getvalue()
    def test_vat_pack_normalization_and_history(self):
        app.import_csv(self.csv(self.row()))
        self.assertEqual(app.catalogue()['offers'][0]['unit_price'],100)
        app.import_csv(self.csv(self.row()))
        self.assertEqual(len(app.catalogue()['history']),1)
        app.import_csv(self.csv(self.row(price='2480',observed_at='2026-02-01')))
        self.assertEqual(len(app.catalogue()['history']),2)
        self.assertEqual(app.catalogue()['offers'][0]['unit_price'],200)
    def test_atomic_rejection_and_old_prices(self):
        app.import_csv(self.csv(self.row()))
        with self.assertRaises(ValueError):
            app.import_csv(self.csv(self.row(sku='NEW'),self.row(observed_at='2025-01-01')))
        self.assertEqual(len(app.catalogue()['offers']),1)
        with self.assertRaises(ValueError):app.import_csv(self.csv(self.row(sku='NEW'),self.row(pack_quantity='0')))
        self.assertEqual(len(app.catalogue()['offers']),1)
    def test_matching_identifiers_not_names(self):
        app.import_csv(self.csv(self.row(),self.row(supplier='Other'),self.row(sku='Unknown',manufacturer_part='')))
        rows=app.catalogue()['offers'];self.assertEqual(rows[0]['match_key'],rows[1]['match_key']);self.assertNotEqual(rows[0]['match_key'],rows[2]['match_key'])
    def test_bad_numbers_urls_and_gtin(self):
        for changes in [dict(price='NaN'),dict(price='-1'),dict(price='1,20'),dict(url='javascript:alert(1)'),dict(vat_included='unknown'),dict(gtin='1234567890123')]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):app.validate(self.row(**changes))
    def test_gtin_normalization(self):
        self.assertEqual(app.validate(self.row(gtin='4006381333931'))['gtin'],'04006381333931')
    def test_draft_collection_never_guesses_tax_or_units(self):
        html='<script type="application/ld+json">{"@type":"Product","name":"TEST","sku":"T","offers":{"@type":"Offer","price":"1240","priceCurrency":"ISK"}}</script>'
        rows=collect.extract(html,'https://example.com/product','Test')
        self.assertEqual(rows[0]['price'],'1240');self.assertEqual(rows[0]['vat_included'],'');self.assertEqual(rows[0]['pack_quantity'],'')
        with self.assertRaises(ValueError):app.validate(rows[0])
    def test_aggregate_low_price_is_not_a_product_offer(self):
        self.assertEqual(collect.extract('<script type="application/ld+json">{"@type":"Product","offers":{"@type":"AggregateOffer","lowPrice":100}}</script>','https://example.com','Test'),[])
    def test_collector_rejects_arbitrary_hosts_before_network(self):
        with self.assertRaises(ValueError):collect.fetch('http://127.0.0.1:8000/api/catalogue')

if __name__=='__main__':unittest.main()
