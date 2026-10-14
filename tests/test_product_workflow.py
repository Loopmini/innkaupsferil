import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import app

class ProductWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=app.DB;app.DB=Path(self.tmp.name)/'test.sqlite'
        self.offer={'id':-1,'name':'Burðarvirkistimbur 45x95 mm C24','supplier':'A','sku':'A1','unit':'m','pack_quantity':1,'price':100,'source_kind':'market','gtin':'','brand':'','manufacturer_part':''}
        self.mock=patch('app.read_supplements',side_effect=lambda:([dict(self.offer)],{}));self.mock.start()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url='http://127.0.0.1:'+str(self.server.server_port)
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.mock.stop();app.DB=self.old;self.tmp.cleanup()
    def post(self,path,data):
        req=Request(self.url+'/api/'+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':self.url})
        with urlopen(req) as r:return json.load(r)
    def test_persistence_refresh_and_bom_creation(self):
        self.post('product-enrichment',{'id':-1,'classification_id':'building.timber.decking','specifications':{'width_mm':120},'search_tags':['pallur']})
        self.offer['name']='Nýtt heiti 45x95 mm'
        o=app.catalogue()['offers'][0]
        self.assertEqual(o['classification']['id'],'building.timber.decking');self.assertEqual(o['specifications']['width_mm'],120)
        r=self.post('bom-add',{'offer_id':-1,'name':'Pallur','quantity':20,'unit':'m'})
        with urlopen(self.url+'/api/bom?id='+str(r['id'])) as response:b=json.load(response)
        self.assertEqual(b['rows'][0]['specifications']['width_mm'],120);self.assertEqual(b['selections']['1'],[-1])
        self.assertEqual(b['rows'][0]['reference_offer_id'],-1)
        self.post('product-enrichment',{'id':-1,'reset':True})
        self.assertNotEqual(app.catalogue()['offers'][0]['specifications'].get('width_mm'),120)
    def test_invalid_enrichment_and_ai_candidates_rejected(self):
        for path,data in [('product-enrichment',{'id':-1,'classification_id':'invented'}),('bom-add',{'offer_id':-1,'name':'A','quantity':2,'unit':'madeup'})]:
            with self.assertRaises(HTTPError) as e:self.post(path,data)
            self.assertEqual(e.exception.code,400)
    def test_no_key_static_routes_and_secrets_not_served(self):
        with patch('ai_support.config',return_value={'OPENAI_API_KEY':'','OPENAI_MODEL':'gpt-5-mini'}):
            with urlopen(self.url+'/api/ai-status') as r:self.assertFalse(json.load(r)['configured'])
            with self.assertRaises(HTTPError) as e:self.post('ai-review',{'id':-1,'categories':['x']})
            self.assertEqual(e.exception.code,400)
        with urlopen(self.url+'/taxonomy-ui.js') as r:self.assertEqual(r.status,200)
        with self.assertRaises(HTTPError) as e:urlopen(self.url+'/.env')
        self.assertEqual(e.exception.code,404)
