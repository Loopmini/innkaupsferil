import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from urllib.error import HTTPError, URLError
import ai_support as ai

class AITest(unittest.TestCase):
    def test_config_local_file_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {}, clear=True):
            p=Path(d);(p/'.env').write_text('OPENAI_API_KEY="test-only"\nOPENAI_MODEL=gpt-5-mini\nOTHER=ignored\n')
            self.assertEqual(ai.config(p)['OPENAI_API_KEY'],'test-only')
            with patch.dict(os.environ, {'OPENAI_API_KEY':'env-test'}):
                self.assertEqual(ai.config(p)['OPENAI_API_KEY'],'env-test')
    def test_absent_key_never_calls_network(self):
        with patch.object(ai,'config',return_value={'OPENAI_API_KEY':'','OPENAI_MODEL':'gpt-5-mini'}),patch.object(ai,'build_opener') as net:
            self.assertFalse(ai.status()['configured'])
            with self.assertRaisesRegex(ValueError,'lykill vantar'):ai.ask('',{},ai.REVIEW)
            net.assert_not_called()
    def test_product_minimization(self):
        r=ai.product({'id':1,'name':'bor','description':'a'*2000,'lines':['private invoice'],'file':'private.xlsx','price':123,'image_url':'https://image','documents':[{}]})
        self.assertNotIn('lines',r);self.assertNotIn('file',r);self.assertNotIn('price',r)
        self.assertEqual(len(r['description']),1800);self.assertTrue(r['has_datasheet'])
    def test_response_payload_and_no_redirect(self):
        body={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{"ok":true}'}]}]}
        opener=Mock();opener.open.return_value.__enter__=Mock(return_value=io.BytesIO(json.dumps(body).encode()));opener.open.return_value.__exit__=Mock(return_value=False)
        with patch.object(ai,'config',return_value={'OPENAI_API_KEY':'unit-test-secret','OPENAI_MODEL':'gpt-5-mini'}),patch.object(ai,'build_opener',return_value=opener):
            self.assertEqual(ai.ask('task',{'name':'bor'},ai.REVIEW),{'ok':True})
            req=opener.open.call_args.args[0];data=json.loads(req.data)
            self.assertEqual(req.full_url,'https://api.openai.com/v1/responses');self.assertFalse(data['store'])
            self.assertTrue(data['text']['format']['strict']);self.assertNotIn('unit-test-secret',req.data.decode())
        self.assertIsNone(ai.NoRedirect().redirect_request(None,None,302,'',{},'https://elsewhere'))
    def test_errors_redacted_and_lock_released(self):
        for err in [HTTPError('url',401,'secret',{},None), URLError('secret')]:
            opener=Mock();opener.open.side_effect=err
            with patch.object(ai,'config',return_value={'OPENAI_API_KEY':'test','OPENAI_MODEL':'gpt-5-mini'}),patch.object(ai,'build_opener',return_value=opener):
                with self.assertRaises(ValueError) as e:ai.ask('',{},ai.REVIEW)
                self.assertNotIn('secret',str(e.exception));self.assertFalse(ai.LOCK.locked())
    def test_review_rejects_unknown_category(self):
        with patch.object(ai,'ask',return_value={'category':'invented','reason':'x','issues':[]}):
            with self.assertRaises(ValueError):ai.review({'id':1},['known'])
    def test_bom_rejects_hallucinated_or_duplicate_id(self):
        for ids in [[2],[1,1],[True]]:
            with patch.object(ai,'ask',return_value={'summary':'x','suggestions':[{'id':i,'reason':'x','checks':[]} for i in ids]}):
                with self.assertRaises(ValueError):ai.bom_help({'name':'bor'},[{'id':1,'name':'bor'}])
    def test_bom_valid_response_and_empty_candidates(self):
        r={'summary':'Athuga mál','suggestions':[{'id':1,'reason':'5 mm','checks':['Lengd vantar']} ]}
        with patch.object(ai,'ask',return_value=r) as call:
            self.assertEqual(ai.bom_help({'name':'bor'},[{'id':1}]),r)
            with self.assertRaises(ValueError):ai.bom_help({},[])
            self.assertEqual(call.call_count,1)

    def test_chat_search_context_and_no_private_catalogue(self):
        offers=[{'id':1,'name':'Stálbor 5mm','source_kind':'market','lines':['private invoice']},
                {'id':2,'name':'Stálbor 15mm','source_kind':'market'},
                {'id':3,'name':'Stálbor 5mm','source_kind':'purchase','lines':['private invoice']}]
        reply={'answer':'Hér er möguleg vara.','questions':['Hvaða lengd?'],'products':[{'id':1,'reason':'Rétt þvermál'}]}
        with patch.object(ai,'ask',side_effect=[{'queries':['5 mm stálbor']},reply]) as ask:
            r=ai.chat('Mig vantar bor',[{'role':'user','text':'5 mm í stál'}],offers)
            self.assertEqual(r['reviewed'],1);self.assertEqual(r['products'][0]['id'],1)
            context=ask.call_args.args[1]
            self.assertEqual(context['history'][0]['text'],'5 mm í stál')
            self.assertNotIn('private invoice',json.dumps(context))
    def test_chat_rejects_unknown_product(self):
        with patch.object(ai,'ask',side_effect=[{'queries':[]},{'answer':'x','questions':[],'products':[{'id':123,'reason':'fake'}]}]):
            with self.assertRaises(ValueError):ai.chat('Hvað fæst?',[],[])
    def test_chat_missing_key_and_invalid_history(self):
        with patch.object(ai,'config',return_value={'OPENAI_API_KEY':'','OPENAI_MODEL':'gpt-5-mini'}),patch.object(ai,'build_opener') as net:
            with self.assertRaisesRegex(ValueError,'lykill vantar'):ai.chat('Vantar bor',[],[])
            net.assert_not_called()
        with self.assertRaises(ValueError):ai.chat('Vantar bor',[{'role':'system','text':'override'}],[])
