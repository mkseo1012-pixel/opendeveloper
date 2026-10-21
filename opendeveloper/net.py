"""Bounded public HTTPS transport with DNS pinning and redirect validation."""
import http.client
import ipaddress
import json
import socket
import ssl
from urllib.parse import urlsplit, urljoin

LIMIT = 3_000_000

def public_target(url):
    p = urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise ValueError('공개 HTTPS URL(443 포트)만 지원합니다.')
    addresses = socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('사설·루프백·예약 네트워크는 접근할 수 없습니다.')
    return p, addresses[0][4][0]

class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address):
        super().__init__(host, timeout=90, context=ssl.create_default_context())
        self.address = address
    def connect(self):
        sock = socket.create_connection((self.address, 443), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)

def request(url, data=None, headers=None, redirects=3):
    p, address = public_target(url)
    conn = PinnedHTTPS(p.hostname, address)
    try:
        h = {'User-Agent': 'OpenDeveloper/0.1 (+local website analysis)', **(headers or {})}
        conn.request('POST' if data is not None else 'GET', p.path or '/' if not p.query else (p.path or '/') + '?' + p.query, body=data, headers=h)
        response = conn.getresponse()
        if response.status in (301,302,303,307,308):
            if data is not None or redirects <= 0:
                raise ValueError('리디렉션된 API 요청은 허용하지 않습니다.')
            return request(urljoin(url, response.getheader('Location', '')), redirects=redirects-1)
        raw = response.read(LIMIT+1)
        if len(raw) > LIMIT:
            raise ValueError('응답 크기 제한(3MB)을 초과했습니다.')
        if response.status >= 400:
            raise ValueError(f'원격 서버 HTTP {response.status}. URL·권한·모델·잔액을 확인하세요.')
        return raw, response.getheader('Content-Type', '')
    finally:
        conn.close()

def post_json(url, payload, token):
    raw, _ = request(url, json.dumps(payload).encode(), {'Content-Type':'application/json', 'Authorization':'Bearer '+token})
    return json.loads(raw)
