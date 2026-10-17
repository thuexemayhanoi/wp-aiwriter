"""Shared helpers for the GitHub-only SEO systems (audit, internal link matrix, protection).

Everything here is read-only against WordPress: public HTTP GET/HEAD requests only, no credentials and
no WordPress writes. No WPVibe, WP Agent or plugin is needed; GitHub Actions plus the public WP REST API
and public pages are enough.
"""
import concurrent.futures
import hashlib
import html
import json
import math
import os
import pathlib
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))
import engine  # noqa: E402

SITE = os.getenv('SEO_SITE_URL', 'https://blog.rentbikehanoi.com').rstrip('/')
DATA_DIR = ROOT / 'data' / 'seo'
REPORT_DIR = ROOT / 'reports' / 'seo'
UA = os.getenv('SEO_USER_AGENT') or 'wp-aiwriter-seo-bot/1.0 (+https://github.com/thuexemayhanoi/wp-aiwriter; read-only)'
SEVERITIES = ('critical', 'high', 'medium', 'low', 'info')
PENALTY = {'critical': 25, 'high': 12, 'medium': 5, 'low': 2, 'info': 0}
STOPWORDS = set('''và của là có cho các một những được trong khi với để này thì không nên cần hay theo từ đến ở như
về hơn nào gì sao đã sẽ cũng mà nếu bị bằng ra vào lên người nhiều thế nhất rất khác giữa sau trước hơn mỗi'''.split())


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def finding(check, severity, message, **extra):
    assert severity in SEVERITIES, severity
    return {'check': check, 'severity': severity, 'message': message, **extra}


def score(findings):
    return max(0, 100 - sum(PENALTY[f['severity']] for f in findings))


def severity_counts(findings):
    counts = {s: 0 for s in SEVERITIES}
    for item in findings:
        counts[item['severity']] += 1
    return counts


def write_json(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')


def read_json(path, default=None):
    path = pathlib.Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def step_summary(markdown):
    target = os.getenv('GITHUB_STEP_SUMMARY')
    if target:
        with open(target, 'a', encoding='utf-8') as handle:
            handle.write(markdown + '\n')


# ---------------------------------------------------------------- URLs -----------------------------------------------
def norm_url(url, force_https=True):
    """Comparable form of a page URL: lowercase host, https, no fragment/query, trailing slash for pages."""
    parts = urllib.parse.urlsplit(str(url).strip())
    host = parts.netloc.lower()
    path = parts.path or '/'
    if not re.search(r'\.[a-z0-9]{2,5}$', path.rsplit('/', 1)[-1], re.I) and not path.endswith('/'):
        path += '/'
    scheme = 'https' if force_https else parts.scheme.lower()
    return f'{scheme}://{host}{path}'


def host_of(url):
    return urllib.parse.urlsplit(url).netloc.lower().split(':')[0]


def is_internal(url, site=SITE):
    return host_of(url) == host_of(site)


# ---------------------------------------------------------------- HTTP (read-only) -----------------------------------
class SeoFetchError(RuntimeError):
    pass


class Response:
    __slots__ = ('url', 'final_url', 'status', 'headers', 'text', 'elapsed_ms', 'error')

    def __init__(self, url, final_url=None, status=0, headers=None, text='', elapsed_ms=0, error=None):
        self.url, self.final_url, self.status = url, final_url or url, status
        self.headers, self.text, self.elapsed_ms, self.error = headers or {}, text, elapsed_ms, error


def _opener(url):
    if host_of(url) in ('127.0.0.1', 'localhost'):
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener()


def _decode(raw, headers):
    match = re.search(r'charset=([\w-]+)', headers.get('content-type', ''), re.I)
    try:
        return raw.decode(match.group(1) if match else 'utf-8', errors='replace')
    except LookupError:
        return raw.decode('utf-8', errors='replace')


def http_get(url, timeout=25, retries=2, method='GET', max_bytes=4_000_000):
    """Never raises: network failures come back as status 0 with `error` set."""
    last_error = None
    for attempt in range(retries + 1):
        started = time.monotonic()
        request = urllib.request.Request(url, method=method, headers={
            'User-Agent': UA, 'Accept': 'text/html,application/json,application/xml;q=0.9,*/*;q=0.8'})
        try:
            with _opener(url).open(request, timeout=timeout) as reply:
                headers = {k.lower(): v for k, v in reply.headers.items()}
                raw = b'' if method == 'HEAD' else reply.read(max_bytes)
                return Response(url, reply.geturl(), reply.status, headers, _decode(raw, headers),
                                int((time.monotonic() - started) * 1000))
        except urllib.error.HTTPError as exc:
            headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raw = b'' if method == 'HEAD' else exc.read(200_000)
            return Response(url, exc.geturl() if hasattr(exc, 'geturl') else url, exc.code, headers,
                            _decode(raw, headers), int((time.monotonic() - started) * 1000))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = str(exc)
            time.sleep(1 + attempt)
    return Response(url, status=0, error=last_error)


def fetch_many(urls, workers=6, delay=0.0, **kwargs):
    unique = list(dict.fromkeys(urls))
    results = {}

    def one(target):
        if delay:
            time.sleep(delay)
        return target, http_get(target, **kwargs)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for target, response in pool.map(one, unique):
            results[target] = response
    return results


def wp_list(resource, fields, site=SITE, per_page=100, max_pages=80):
    """All public items of a WP REST collection (published content only; Trash/drafts are never exposed)."""
    items, page = [], 1
    while page <= max_pages:
        reply = http_get(f'{site}/wp-json/wp/v2/{resource}?per_page={per_page}&page={page}&_fields={fields}')
        if reply.status == 400 and page > 1:  # past the last page
            break
        if reply.status != 200:
            raise SeoFetchError(f'WP REST {resource} page {page}: HTTP {reply.status} {reply.error or ""}'.strip())
        try:
            data = json.loads(reply.text)
        except ValueError as exc:
            raise SeoFetchError(f'WP REST {resource} page {page}: not JSON ({exc})')
        if not data:
            break
        items.extend(data)
        total = int(reply.headers.get('x-wp-totalpages', '0') or 0)
        if len(data) < per_page or (total and page >= total):
            break
        page += 1
    return items


# ---------------------------------------------------------------- HTML page parsing ----------------------------------
class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.meta, self.canonical = '', {}, None
        self.lang, self.h1, self.h2_count = None, [], 0
        self.images, self.anchors, self.jsonld_raw = [], [], []
        self.text_parts = []
        self._in_title = self._in_head = self._in_ld = False
        self._skip = 0
        self._collect = None
        self._buffer = []
        self._ld_buffer = []

    def handle_starttag(self, tag, attrs):
        attrs = {k.lower(): (v or '') for k, v in attrs}
        if tag == 'html':
            self.lang = attrs.get('lang') or self.lang
        elif tag == 'head':
            self._in_head = True
        elif tag == 'body':
            self._in_head = False
        elif tag == 'title':
            self._in_title = True
        elif tag == 'meta':
            key = (attrs.get('name') or attrs.get('property') or '').lower()
            if key and key not in self.meta:
                self.meta[key] = attrs.get('content', '')
        elif tag == 'link' and 'canonical' in attrs.get('rel', '').lower().split() and not self.canonical:
            self.canonical = attrs.get('href', '')
        elif tag == 'script':
            if attrs.get('type', '').lower() == 'application/ld+json':
                self._in_ld = True
                self._ld_buffer = []
            else:
                self._skip += 1
        elif tag in ('style', 'noscript'):
            self._skip += 1
        elif tag in ('h1', 'h2'):
            if tag == 'h2':
                self.h2_count += 1
            self._collect, self._buffer = tag, []
        elif tag == 'img':
            self.images.append({'src': attrs.get('src', ''), 'alt': attrs.get('alt'),
                                'decorative': attrs.get('role') == 'presentation' or attrs.get('aria-hidden') == 'true'})
        elif tag == 'a' and attrs.get('href'):
            self.anchors.append({'href': attrs['href'], 'rel': attrs.get('rel', '')})

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False
        elif tag == 'script':
            if self._in_ld:
                self._in_ld = False
                self.jsonld_raw.append(''.join(self._ld_buffer))
            elif self._skip:
                self._skip -= 1
        elif tag in ('style', 'noscript') and self._skip:
            self._skip -= 1
        elif tag in ('h1', 'h2') and self._collect == tag:
            if tag == 'h1':
                self.h1.append(' '.join(''.join(self._buffer).split()))
            self._collect = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_ld:
            self._ld_buffer.append(data)
        if self._collect:
            self._buffer.append(data)
        if not self._in_head and not self._skip and not self._in_ld:
            self.text_parts.append(data)


def _jsonld_types(raw_blocks):
    types = set()

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            kind = node.get('@type')
            for value in ([kind] if isinstance(kind, str) else kind or []):
                types.add(str(value))
            for value in node.values():
                if isinstance(value, (list, dict)):
                    walk(value)

    for raw in raw_blocks:
        try:
            walk(json.loads(raw))
        except ValueError:
            types.add('INVALID_JSON_LD')
    return sorted(types)


def parse_page(markup):
    parser = PageParser()
    parser.feed(markup or '')
    parser.close()
    words = len(re.findall(r'\w+', ' '.join(parser.text_parts)))
    meta = parser.meta
    return {
        'title': ' '.join(parser.title.split()), 'description': meta.get('description', '').strip(),
        'robots': meta.get('robots', '').strip().lower(), 'canonical': (parser.canonical or '').strip(),
        'h1_count': len(parser.h1), 'h1_text': parser.h1[0] if parser.h1 else '', 'h2_count': parser.h2_count,
        'images_total': len(parser.images),
        'images_missing_alt': sum(1 for i in parser.images if i['alt'] is None and not i['decorative']),
        'jsonld_types': _jsonld_types(parser.jsonld_raw), 'lang': parser.lang or '',
        'og_title': meta.get('og:title', ''), 'og_image': meta.get('og:image', ''),
        'viewport': meta.get('viewport', ''), 'anchors': parser.anchors, 'word_count': words,
    }


# ---------------------------------------------------------------- repo sources ---------------------------------------
def load_ledger(root=ROOT):
    data = read_json(pathlib.Path(root) / 'data/publication-state.json', {'posts': {}})
    return data.get('posts', {})


def load_sources():
    topics = engine.matrix()
    _, ready, errors = engine.load_posts(topics)
    return topics, ready, errors


MD_LINK = re.compile(r'(?<!!)\[([^\]]*)\]\((https?://[^)\s]+)\)')
MD_HEADING = re.compile(r'^(#{2,4})\s+(.+?)\s*$', re.M)


def md_links(body):
    return [(m.group(1).strip(), m.group(2).strip()) for m in MD_LINK.finditer(body)]


def md_headings(body):
    return [(m.group(1), m.group(2)) for m in MD_HEADING.finditer(body)]


def plain_text(body):
    return engine.visible(engine.markdown_to_html(body))


# ---------------------------------------------------------------- text similarity (TF-IDF, stdlib only) ---------------
def tokenize(text):
    words = re.findall(r'\w+', unicodedata.normalize('NFC', text).casefold())
    return [w for w in words if (w not in STOPWORDS and len(w) > 1) or w.isdigit()]


def grams(tokens):
    return tokens + [f'{a}_{b}' for a, b in zip(tokens, tokens[1:])]


def tfidf_vectors(documents):
    """documents: {key: text} -> {key: {term: weight}} (L2-normalised)."""
    counts = {key: {} for key in documents}
    df = {}
    for key, text in documents.items():
        for term in grams(tokenize(text)):
            counts[key][term] = counts[key].get(term, 0) + 1
        for term in counts[key]:
            df[term] = df.get(term, 0) + 1
    total = max(1, len(documents))
    vectors = {}
    for key, tf in counts.items():
        vec = {t: (1 + math.log(c)) * (math.log((1 + total) / (1 + df[t])) + 1) for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors[key] = {t: v / norm for t, v in vec.items()}
    return vectors


def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(term, 0.0) for term, weight in a.items())


def sha256_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
