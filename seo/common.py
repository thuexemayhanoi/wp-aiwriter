"""Shared paths, configuration, time and file helpers."""
from datetime import datetime, timezone, timedelta
import gzip
import json
import os
import pathlib
import urllib.parse

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def root():
    """Output root; tests point SEO_ROOT at a temporary directory."""
    return pathlib.Path(os.environ.get('SEO_ROOT', REPO_ROOT))


def path(*parts):
    return root().joinpath(*parts)


def now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(value=None):
    return (value or now()).isoformat()


def parse_time(value):
    if not value:
        return None
    text = value.replace('Z', '+00:00')
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def older_than(value, days):
    stamp = parse_time(value)
    return stamp is None or now() - stamp > timedelta(days=days)


def load_config():
    cfg_path = path('data/seo/config.json')
    if not cfg_path.exists():
        cfg_path = REPO_ROOT / 'data/seo/config.json'
    cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
    site = urllib.parse.urlsplit(cfg['site_url'])
    if site.scheme != 'https' or site.netloc not in cfg['allowed_hosts']:
        raise ValueError('site_url must be https and listed in allowed_hosts')
    if len(cfg['allowed_hosts']) != 1:
        # One engine run audits exactly one website; never mix domains.
        raise ValueError('Exactly one allowed host per configuration')
    return cfg


def read_json(p, default=None):
    p = pathlib.Path(p)
    if not p.exists():
        return default
    if p.suffix == '.gz':
        with gzip.open(p, 'rt', encoding='utf-8') as fh:
            return json.load(fh)
    return json.loads(p.read_text(encoding='utf-8'))


def write_json(p, data, compress=False):
    p = pathlib.Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=None if compress else 2, sort_keys=not compress)
    if compress:
        with gzip.open(p, 'wt', encoding='utf-8') as fh:
            fh.write(text)
    else:
        p.write_text(text + '\n', encoding='utf-8')


def read_jsonl(p):
    p = pathlib.Path(p)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding='utf-8').splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(p, rows):
    p = pathlib.Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8') as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')


def normalize_url(url, base=None):
    """Canonical comparison form: absolute, no fragment, lowercase host, default path '/'."""
    if not url:
        return ''
    if base:
        url = urllib.parse.urljoin(base, url)
    parts = urllib.parse.urlsplit(url.strip())
    if parts.scheme not in ('http', 'https'):
        return ''
    netloc = parts.netloc.lower()
    if netloc.endswith(':443') and parts.scheme == 'https':
        netloc = netloc[:-4]
    if netloc.endswith(':80') and parts.scheme == 'http':
        netloc = netloc[:-3]
    path_ = urllib.parse.quote(urllib.parse.unquote(parts.path or '/'), safe="/%:@!$&'()*+,;=-._~")
    return urllib.parse.urlunsplit((parts.scheme, netloc, path_, parts.query, ''))


def same_page(a, b):
    """True when two URLs point to the same page ignoring a trailing slash and scheme case."""
    na, nb = normalize_url(a), normalize_url(b)
    return bool(na) and na.rstrip('/') == nb.rstrip('/')


def host(url):
    return urllib.parse.urlsplit(url).netloc.lower()


def is_internal(url, cfg):
    return host(url) in cfg['allowed_hosts']
