"""Read-only HTTP client: GET/HEAD only, one audited host, polite throttling, retries.

The SEO engine never sends credentials. Redirects are followed manually so every hop is
recorded; an internal crawl never follows a redirect to another host.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import json
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from .common import host

RETRY_STATUS = {429, 500, 502, 503, 504}


class TransportError(Exception):
    pass


@dataclass
class Response:
    url: str
    status: int = 0
    headers: dict = field(default_factory=dict)
    body: bytes = b''
    final_url: str = ''
    redirects: list = field(default_factory=list)
    elapsed_ms: int = 0
    error: str = ''
    truncated: bool = False

    @property
    def ok(self):
        return 200 <= self.status < 300

    def text(self):
        charset = 'utf-8'
        ctype = self.headers.get('content-type', '')
        if 'charset=' in ctype:
            charset = ctype.split('charset=')[-1].split(';')[0].strip() or 'utf-8'
        try:
            return self.body.decode(charset, errors='replace')
        except LookupError:
            return self.body.decode('utf-8', errors='replace')

    def json(self):
        return json.loads(self.text())

    def summary(self):
        return {'status': self.status, 'final_url': self.final_url, 'redirects': self.redirects,
                'elapsed_ms': self.elapsed_ms, 'error': self.error}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class UrllibTransport:
    """Network transport without redirects, cookies or credentials."""

    def __init__(self):
        self.opener = urllib.request.build_opener(_NoRedirect())

    def __call__(self, method, url, headers, timeout, max_bytes):
        req = urllib.request.Request(url, method=method, headers=headers)
        try:
            with self.opener.open(req, timeout=timeout) as resp:
                body = resp.read(max_bytes + 1) if method == 'GET' else b''
                return resp.status, {k.lower(): v for k, v in resp.headers.items()}, body
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read(max_bytes + 1) if method == 'GET' else b''
            except Exception:  # noqa: BLE001 - body of an error page is optional evidence
                body = b''
            return exc.code, {k.lower(): v for k, v in (exc.headers or {}).items()}, body
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, ssl.SSLError, OSError) as exc:
            reason = getattr(exc, 'reason', exc)
            raise TransportError(type(reason).__name__ + ': ' + str(reason)[:160]) from None


class Fetcher:
    def __init__(self, cfg, transport=None, sleep=time.sleep):
        self.cfg = cfg
        http = cfg.get('http', {})
        self.timeout = http.get('timeout_seconds', 25)
        self.retries = http.get('retries', 3)
        self.min_interval = http.get('min_interval_seconds', 0.25)
        self.max_bytes = http.get('max_body_bytes', 6_000_000)
        self.transport = transport or UrllibTransport()
        self.sleep = sleep
        self.user_agent = cfg['user_agent']
        self._lock = threading.Lock()
        self._next_slot = {}
        self.requests_made = 0

    def _throttle(self, netloc):
        with self._lock:
            now_ = time.monotonic()
            slot = max(now_, self._next_slot.get(netloc, 0.0))
            self._next_slot[netloc] = slot + self.min_interval
            wait = slot - now_
        if wait > 0:
            self.sleep(wait)

    def _check_target(self, url, internal_only, allow_http):
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in ('https', 'http'):
            raise ValueError('Only http(s) URLs can be fetched')
        if internal_only:
            if parts.netloc.lower() not in self.cfg['allowed_hosts']:
                raise ValueError('Refused: host outside the audited website')
            if parts.scheme != 'https' and not allow_http:
                raise ValueError('Refused: internal fetch must use https')

    def fetch(self, url, method='GET', accept='text/html,application/xhtml+xml', internal_only=True,
              follow=True, max_redirects=5, allow_http=False, timeout=None, max_bytes=None):
        if method not in ('GET', 'HEAD'):
            raise ValueError('The SEO engine is read-only: GET and HEAD only')
        self._check_target(url, internal_only, allow_http)
        timeout = timeout or self.timeout
        max_bytes = max_bytes or self.max_bytes
        headers = {'User-Agent': self.user_agent, 'Accept': accept, 'Cache-Control': 'no-cache'}
        response = Response(url=url, final_url=url)
        started = time.monotonic()
        current = url
        hops = 0
        while True:
            status, resp_headers, body, error = self._attempt(method, current, headers, timeout, max_bytes)
            if status and 300 <= status < 400 and resp_headers.get('location') and follow:
                target = urllib.parse.urljoin(current, resp_headers['location'])
                response.redirects.append({'status': status, 'from': current, 'to': target})
                hops += 1
                cross = host(target) != host(current) and host(target) not in self.cfg['allowed_hosts']
                if hops > max_redirects:
                    response.error = 'redirect limit exceeded'
                elif internal_only and cross:
                    response.error = 'cross-host redirect not followed'
                else:
                    try:
                        self._check_target(target, internal_only, allow_http=allow_http)
                        current = target
                        continue
                    except ValueError as exc:
                        response.error = str(exc)
                response.status, response.headers, response.final_url = status, resp_headers, target
                break
            response.status, response.headers, response.final_url = status, resp_headers, current
            response.error = error
            if len(body) > max_bytes:
                body, response.truncated = body[:max_bytes], True
            response.body = body
            break
        response.elapsed_ms = int((time.monotonic() - started) * 1000)
        return response

    def _attempt(self, method, url, headers, timeout, max_bytes):
        last_error = ''
        for attempt in range(self.retries):
            self._throttle(host(url))
            self.requests_made += 1
            try:
                status, resp_headers, body = self.transport(method, url, headers, timeout, max_bytes)
            except TransportError as exc:
                last_error = str(exc)
                if attempt + 1 < self.retries:
                    self.sleep(2 ** attempt)
                continue
            if status in RETRY_STATUS and attempt + 1 < self.retries:
                retry_after = resp_headers.get('retry-after', '')
                delay = int(retry_after) if retry_after.isdigit() else 2 ** attempt
                self.sleep(min(delay, 30))
                last_error = f'HTTP {status}'
                continue
            return status, resp_headers, body, ''
        return 0, {}, b'', last_error or 'network failure'

    def head_or_get(self, url, internal_only=True, timeout=None):
        """Cheap status check: HEAD, falling back to GET when HEAD is refused or unsupported."""
        resp = self.fetch(url, method='HEAD', accept='*/*', internal_only=internal_only, timeout=timeout)
        if resp.status in (0, 403, 405, 501) or resp.status >= 500:
            resp = self.fetch(url, method='GET', accept='*/*', internal_only=internal_only,
                              timeout=timeout, max_bytes=200_000)
        return resp

    def get_json(self, url):
        resp = self.fetch(url, accept='application/json')
        if not resp.ok:
            raise RuntimeError(f'GET {url} returned HTTP {resp.status} {resp.error}'.strip())
        try:
            return resp.json(), resp
        except ValueError:
            raise RuntimeError(f'GET {url} did not return JSON') from None


def parallel(items, fn, workers):
    """Map fn over items with bounded concurrency; returns {item: result}."""
    items = list(dict.fromkeys(items))
    if not items:
        return {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return dict(zip(items, pool.map(fn, items)))
