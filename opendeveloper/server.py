import base64
import hashlib
import json
import mimetypes
import os
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from .core import Store, Agent, Model
from .net import request, public_target

class App:
    def __init__(self, store=None):
        self.store=store or Store(); self.config={}; self.csrf=secrets.token_urlsafe(32); self.oauth={}; self.config_lock=threading.Lock()
    def agent(self):
        with self.config_lock: config=dict(self.config)
        return Agent(self.store,Model(config))

def make_server(port=8765, app=None):
    app=app or App()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass  # never log OAuth query strings or credentials
        def send(self, value, status=200, kind='application/json', attachment=None):
            raw=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode()
            self.send_response(status); self.send_header('Content-Type',kind); self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-src 'none'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'")
            if attachment: self.send_header('Content-Disposition',f'attachment; filename="{attachment}"')
            self.end_headers(); self.wfile.write(raw)
        def host_ok(self): return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
        def do_GET(self):
            if not self.host_ok(): return self.send({'error':'Invalid Host'},403)
            p=urlsplit(self.path)
            try:
                if p.path=='/api/state':
                    return self.send({'csrf':app.csrf,'connected':bool(app.config.get('token') or os.getenv('OPENDEVELOPER_API_KEY')),'projects':app.store.list(),'oauth_enabled':bool(os.getenv('OPENDEVELOPER_OAUTH_CLIENT_ID'))})
                if p.path=='/oauth/callback':
                    q=parse_qs(p.query); state=q.get('state',[''])[0]
                    with app.config_lock: flow=app.oauth.pop(state,None)
                    if not flow or time.time()-flow['created']>600: raise ValueError('OAuth state가 없거나 만료되었습니다.')
                    if 'error' in q or 'code' not in q: raise ValueError('OAuth 승인이 취소되었거나 code가 없습니다.')
                    payload=urlencode({'grant_type':'authorization_code','client_id':os.environ['OPENDEVELOPER_OAUTH_CLIENT_ID'],'code':q['code'][0],'code_verifier':flow['verifier'],'redirect_uri':flow['redirect']}).encode()
                    raw,_=request(os.environ['OPENDEVELOPER_OAUTH_TOKEN_URL'],payload,{'Content-Type':'application/x-www-form-urlencoded'})
                    token=json.loads(raw)
                    if not isinstance(token.get('access_token'),str) or not token['access_token']: raise ValueError('OAuth access_token이 없습니다.')
                    with app.config_lock: app.config['token']=token['access_token']
                    return self.send(b'Connected. Close this tab and return to OpenDeveloper.',kind='text/plain; charset=utf-8')
                if p.path.startswith('/download/'):
                    parts=p.path.split('/')
                    if len(parts)!=4 or parts[3] not in ('index.html','project.zip'): raise ValueError('다운로드 경로 오류')
                    project=app.store.get(parts[2])
                    if project['status']!='complete': raise ValueError('아직 생성이 완료되지 않았습니다.')
                    path=app.store.root/project['id']/parts[3]
                    return self.send(path.read_bytes(),kind='application/zip' if path.suffix=='.zip' else 'text/html; charset=utf-8',attachment=parts[3])
                names={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
                if p.path not in names: return self.send({'error':'Not found'},404)
                path=Path(__file__).parent/'web'/names[p.path]
                return self.send(path.read_bytes(),kind=mimetypes.guess_type(path)[0]+'; charset=utf-8')
            except Exception as e: self.send({'error':str(e) if isinstance(e,ValueError) else '요청 실패. 연결·설정을 확인하세요.'},400)
        def do_POST(self):
            origin=self.headers.get('Origin')
            if not self.host_ok() or self.headers.get('X-OpenDeveloper-Token')!=app.csrf or (origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}')):
                return self.send({'error':'Forbidden'},403)
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=100_000: raise ValueError('요청 크기 오류')
                data=json.loads(self.rfile.read(length))
                if not isinstance(data,dict): raise ValueError('JSON 객체가 필요합니다.')
                route=self.path
                if route=='/api/config':
                    for key in ('base_url','model','token'):
                        if key in data and not isinstance(data[key],str): raise ValueError('설정은 문자열이어야 합니다.')
                    public_target(data.get('base_url',''))
                    if not data.get('model'): raise ValueError('모델 이름이 필요합니다.')
                    with app.config_lock:
                        app.config.update({k:v for k,v in data.items() if k in ('base_url','model','token') and v})
                    return self.send({'ok':True})
                if route=='/api/disconnect':
                    with app.config_lock: app.config.clear(); app.oauth.clear()
                    return self.send({'ok':True})
                if route=='/api/oauth/start':
                    client=os.getenv('OPENDEVELOPER_OAUTH_CLIENT_ID'); auth=os.getenv('OPENDEVELOPER_OAUTH_AUTH_URL'); token_url=os.getenv('OPENDEVELOPER_OAUTH_TOKEN_URL')
                    if not client or not auth or not token_url: raise ValueError('OAuth client ID·인증 URL·토큰 URL 환경변수를 설정하세요.')
                    public_target(auth); public_target(token_url)
                    verifier=secrets.token_urlsafe(48); state=secrets.token_urlsafe(32)
                    redirect=f'http://127.0.0.1:{self.server.server_port}/oauth/callback'
                    with app.config_lock:
                        app.oauth={k:v for k,v in app.oauth.items() if time.time()-v['created']<600}
                        if len(app.oauth)>=10: raise ValueError('OAuth 요청이 너무 많습니다.')
                        app.oauth[state]={'verifier':verifier,'redirect':redirect,'created':time.time()}
                    query={'response_type':'code','client_id':client,'redirect_uri':redirect,'state':state,'code_challenge':base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode(),'code_challenge_method':'S256','scope':os.getenv('OPENDEVELOPER_OAUTH_SCOPE','')}
                    return self.send({'url':auth+('&' if '?' in auth else '?')+urlencode(query)})
                agent=app.agent()
                if route=='/api/plan': result=agent.plan(str(data['url']),str(data.get('brief','')))
                elif route=='/api/revise': result=agent.revise(data['id'],str(data['feedback']))
                elif route=='/api/approve': result=agent.approve(data['id'],data['revision'])
                elif route=='/api/build': result=agent.build(data['id'])
                else: return self.send({'error':'Not found'},404)
                self.send(result)
            except Exception as e:
                self.send({'error':str(e) if isinstance(e,ValueError) else '요청 실패. 네트워크·연결 설정·입력값을 확인하세요.'},400)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.daemon_threads=True
    return server

def serve(port=8765, open_browser=True):
    server=make_server(port)
    print(f'OpenDeveloper → http://127.0.0.1:{server.server_port}  (Ctrl+C to stop)')
    if open_browser: webbrowser.open(f'http://127.0.0.1:{server.server_port}')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
