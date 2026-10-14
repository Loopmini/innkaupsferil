import hashlib,json,tempfile,threading,unittest
from pathlib import Path
from urllib.request import urlopen
from http.server import ThreadingHTTPServer
import app,update_install

class InstallationTest(unittest.TestCase):
 def test_real_static_routes_with_version_queries(self):
  server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
  try:
   base='http://127.0.0.1:'+str(server.server_port)
   with urlopen(base+'/api/version') as r:self.assertEqual(json.load(r)['version'],'0.18')
   for name,kind in [('theme.css','text/css'),('theme-ui.js','text/javascript'),('evidence-ui.js','text/javascript'),('boot-check.js','text/javascript')]:
    with urlopen(base+'/'+name+'?v=018') as r:
     self.assertTrue(r.headers['Content-Type'].startswith(kind));self.assertEqual(r.headers['Cache-Control'],'no-store');self.assertEqual(r.read(),(app.ROOT/'static'/name).read_bytes())
   with urlopen(base+'/') as r:self.assertIn(b'/theme.css?v=018',r.read())
  finally:server.shutdown();server.server_close();worker.join()
 def test_installer_preserves_data_and_rejects_partial_package_before_writes(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);source=root/'update';target=root/'current';source.mkdir();target.mkdir();(target/'static').mkdir();(target/'data').mkdir()
   (target/'app.py').write_text('old');(target/'static/index.html').write_text('old');(target/'data/catalog.sqlite').write_bytes(b'private-db');(target/'.env').write_text('private-key')
   files=['app.py','static/index.html','static/theme.css','static/theme-ui.js','static/evidence-ui.js','static/boot-check.js'];manifest={}
   for name in files:
    p=source/name;p.parent.mkdir(exist_ok=True);p.write_text('new '+name);manifest[name]=hashlib.sha256(p.read_bytes()).hexdigest()
   (source/'update-manifest.json').write_text(json.dumps({'files':manifest}))
   backup=update_install.apply(source,target)
   self.assertTrue(backup.exists());self.assertEqual((target/'data/catalog.sqlite').read_bytes(),b'private-db');self.assertEqual((target/'.env').read_text(),'private-key');self.assertEqual((target/'app.py').read_text(),'new app.py')
   (source/'static/theme.css').unlink()
   with self.assertRaises(ValueError):update_install.apply(source,target)
   self.assertEqual((target/'app.py').read_text(),'new app.py')
