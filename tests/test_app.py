import copy
import io
import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
import zipfile
from unittest.mock import patch
from opendeveloper.core import Agent,Store,validate_files,digest
from opendeveloper.net import public_target
from opendeveloper.server import App,make_server

PLAN={'summary':'Original dashboard','observed_features':['search'],'original_features':['map','compare','favorites'],'ui_style':{'layout':'editorial','palette':'sage'},'acceptance':['search filters work'],'notes':['Static HTML only']}
HTML='<!doctype html><html><body><button>Hello</button></body></html>'
class FakeModel:
    def ask(self,instruction,payload):
        if 'Implement approved' in instruction: return {'files':{'index.html':HTML},'notes':['Implemented interactions']}
        if 'review' in instruction.lower(): return {'passed':True,'findings':[],'notes':['Static inspection']}
        return copy.deepcopy(PLAN)

class FlowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.store=Store(self.temp.name);self.agent=Agent(self.store,FakeModel())
    def plan(self):
        with patch('opendeveloper.core.request',return_value=(b'<html><title>Example</title><button>Find</button></html>','text/html')): return self.agent.plan('https://example.com','Make it unique')
    def test_approval_build_zip_and_persistence(self):
        p=self.plan()
        with self.assertRaises(ValueError): self.agent.build(p['id'])
        self.agent.approve(p['id'],p['revision']); result=self.agent.build(p['id'])
        self.assertEqual(result['status'],'complete')
        with zipfile.ZipFile(self.store.root/p['id']/'project.zip') as z:
            self.assertEqual(z.read('index.html').decode(),HTML);self.assertIn('REVIEW.md',z.namelist())
        self.assertEqual(Store(self.temp.name).get(p['id'])['status'],'complete')
    def test_revise_invalidates_approval(self):
        p=self.plan();self.agent.approve(p['id'],p['revision']);self.agent.revise(p['id'],'Change layout')
        with self.assertRaises(ValueError): self.agent.build(p['id'])
    def test_stale_and_tampered_plan_rejected(self):
        p=self.plan()
        with self.assertRaises(ValueError):self.agent.approve(p['id'],'bad')
        p=self.agent.approve(p['id'],p['revision']);p['plan']['summary']='tampered';self.store.save(p)
        with self.assertRaises(ValueError):self.agent.build(p['id'])
    def test_failed_build_can_retry(self):
        p=self.plan();self.agent.approve(p['id'],p['revision'])
        with patch.object(self.agent.model,'ask',side_effect=ValueError('bad model')):
            with self.assertRaises(ValueError):self.agent.build(p['id'])
        self.assertEqual(self.store.get(p['id'])['status'],'approved')
    def test_review_failure_prevents_delivery(self):
        p=self.plan();self.agent.approve(p['id'],p['revision'])
        with patch.object(self.agent.model,'ask',side_effect=[{'files':{'index.html':HTML}},{'passed':False}]):
            with self.assertRaises(ValueError):self.agent.build(p['id'])
        self.assertFalse((self.store.root/p['id']/'project.zip').exists())
    def test_file_paths(self):
        for name in ('../escape.js','/tmp/x.js','C:/x.js','a\\b.js','x.exe','./x.js','a/../x.js'):
            with self.subTest(name=name),self.assertRaises(ValueError):validate_files({'index.html':HTML,name:'bad'})
    def test_large_output(self):
        with self.assertRaises(ValueError):validate_files({'index.html':'x'*2_000_001})
    def test_ssrf(self):
        for url in ('http://example.com','https://127.0.0.1','https://[::1]','https://user:pass@example.com','https://example.com:8080'):
            with self.subTest(url=url),self.assertRaises(ValueError):public_target(url)
    def test_private_dns(self):
        with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('10.0.0.1',443))]):
            with self.assertRaises(ValueError):public_target('https://reference.example')

class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.app=App(Store(self.temp.name));self.server=make_server(0,self.app)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.base=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):self.server.shutdown();self.server.server_close();self.temp.cleanup()
    def fetch(self,path,data=None,headers=None):
        r=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers or {})
        return urllib.request.urlopen(r)
    def test_ui_assets(self):
        for path in ('/','/style.css','/app.js'):
            with self.fetch(path) as r:self.assertEqual(r.status,200);self.assertIn("frame-src 'none'",r.headers['Content-Security-Policy'])
    def test_csrf_and_host(self):
        for headers in ({},{'X-OpenDeveloper-Token':self.app.csrf,'Origin':'https://evil.example'},{'Host':'evil.example'}):
            with self.subTest(headers=headers),self.assertRaises(urllib.error.HTTPError) as ctx:self.fetch('/api/build',{'id':'x'},headers)
            self.assertEqual(ctx.exception.code,403)
    def test_full_http_flow_and_attachment(self):
        headers={'X-OpenDeveloper-Token':self.app.csrf}
        with patch('opendeveloper.server.Model',return_value=FakeModel()),patch('opendeveloper.core.request',return_value=(b'<html>Demo</html>','text/html')):
            with self.fetch('/api/plan',{'url':'https://example.com'},headers) as r:p=json.load(r)
            with self.assertRaises(urllib.error.HTTPError):self.fetch('/api/build',{'id':p['id']},headers)
            self.fetch('/api/approve',{'id':p['id'],'revision':p['revision']},headers).close()
            with self.fetch('/api/build',{'id':p['id']},headers) as r:self.assertEqual(json.load(r)['status'],'complete')
            with self.fetch('/download/'+p['id']+'/project.zip') as r:
                self.assertIn('attachment',r.headers['Content-Disposition']);self.assertIn('index.html',zipfile.ZipFile(io.BytesIO(r.read())).namelist())
    def test_oauth_invalid_state(self):
        with self.assertRaises(urllib.error.HTTPError):self.fetch('/oauth/callback?state=bad&code=secret')
    def test_oauth_pkce_and_single_use(self):
        env={'OPENDEVELOPER_OAUTH_CLIENT_ID':'client','OPENDEVELOPER_OAUTH_AUTH_URL':'https://auth.example/authorize','OPENDEVELOPER_OAUTH_TOKEN_URL':'https://auth.example/token'}
        with patch.dict('os.environ',env),patch('opendeveloper.server.public_target'),patch('opendeveloper.server.request',return_value=(b'{"access_token":"fixture-token"}','application/json')) as exchange:
            with self.fetch('/api/oauth/start',{}, {'X-OpenDeveloper-Token':self.app.csrf}) as r:url=json.load(r)['url']
            from urllib.parse import urlsplit,parse_qs
            q=parse_qs(urlsplit(url).query);self.assertEqual(q['code_challenge_method'],['S256']);state=q['state'][0]
            self.fetch('/oauth/callback?state='+state+'&code=fixture').close()
            self.assertEqual(self.app.config['token'],'fixture-token');self.assertIn(b'code_verifier=',exchange.call_args.args[1])
            with self.assertRaises(urllib.error.HTTPError):self.fetch('/oauth/callback?state='+state+'&code=fixture')

if __name__=='__main__':unittest.main()
