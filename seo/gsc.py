"""Optional Google Search Console monitor (read-only scope).

Runs only when GSC_SERVICE_ACCOUNT_JSON and GSC_PROPERTY are configured as GitHub secrets
and the service account was added as a user of the property. Without them it records
BLOCKED and never infers performance numbers.
"""
import base64
import csv
from datetime import timedelta
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from . import common
from .common import iso, write_json

SCOPE = 'https://www.googleapis.com/auth/webmasters.readonly'


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def access_token(info):
    from google.auth import crypt  # optional dependency, installed only by gsc-monitor.yml

    signer = crypt.RSASigner.from_service_account_info(info)
    now_ = int(time.time())
    header = {'alg': 'RS256', 'typ': 'JWT', 'kid': info.get('private_key_id')}
    claims = {'iss': info['client_email'], 'scope': SCOPE, 'aud': info['token_uri'],
              'iat': now_, 'exp': now_ + 3600}
    unsigned = f"{_b64(json.dumps(header).encode())}.{_b64(json.dumps(claims).encode())}"
    assertion = unsigned + '.' + _b64(signer.sign(unsigned.encode()))
    body = urllib.parse.urlencode({'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                                   'assertion': assertion}).encode()
    req = urllib.request.Request(info['token_uri'], data=body, method='POST',
                                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())['access_token']


def query(token, prop, body):
    url = ('https://www.googleapis.com/webmasters/v3/sites/' + urllib.parse.quote(prop, safe='')
           + '/searchAnalytics/query')
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method='POST',
                                 headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read()).get('rows', [])


def run(cfg, records):
    status_path = common.path('data/seo/gsc-summary.json')
    raw, prop = os.environ.get('GSC_SERVICE_ACCOUNT_JSON'), os.environ.get('GSC_PROPERTY')
    if not raw or not prop:
        summary = {'status': 'BLOCKED', 'reason': 'GSC_SERVICE_ACCOUNT_JSON / GSC_PROPERTY not configured',
                   'checked_at': iso()}
        write_json(status_path, summary)
        return summary
    try:
        info = json.loads(raw)
        token = access_token(info)
        end = (common.now() - timedelta(days=3)).date()
        start = end - timedelta(days=27)
        base = {'startDate': start.isoformat(), 'endDate': end.isoformat(), 'rowLimit': 25000, 'dataState': 'final'}
        pages = query(token, prop, {**base, 'dimensions': ['page']})
        pairs = query(token, prop, {**base, 'dimensions': ['query', 'page']})
    except ImportError:
        summary = {'status': 'BLOCKED', 'reason': 'google-auth not installed', 'checked_at': iso()}
        write_json(status_path, summary)
        return summary
    except (urllib.error.URLError, KeyError, ValueError) as exc:
        # Never echo response bodies or key material.
        summary = {'status': 'ERROR', 'reason': type(exc).__name__, 'checked_at': iso()}
        write_json(status_path, summary)
        return summary
    site_host = common.host(cfg['site_url'])
    pages = [r for r in pages if common.host(r['keys'][0]) == site_host]
    pairs = [r for r in pairs if common.host(r['keys'][1]) == site_host]
    out_dir = common.path('reports')
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / 'gsc-pages.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['page', 'clicks', 'impressions', 'ctr', 'position'])
        for r in sorted(pages, key=lambda x: -x['impressions']):
            w.writerow([r['keys'][0], r['clicks'], r['impressions'], round(r['ctr'], 4), round(r['position'], 1)])
    by_query = {}
    for r in pairs:
        by_query.setdefault(r['keys'][0], []).append(r)
    shared = {}
    for q, rows in by_query.items():
        rows = [r for r in rows if r['impressions'] >= 5]
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                key = f"{common.normalize_url(rows[i]['keys'][1])}|{common.normalize_url(rows[j]['keys'][1])}"
                shared[key] = shared.get(key, 0) + 1
    known = {common.normalize_url(r['url']) for r in records}
    in_gsc = {common.normalize_url(r['keys'][0]) for r in pages}
    summary = {'status': 'OK', 'property': prop, 'start': start.isoformat(), 'end': end.isoformat(),
               'pages_with_impressions': len(pages), 'published_without_impressions': len(known - in_gsc),
               'shared_query_pairs': shared, 'checked_at': iso(),
               'query_gaps': [{'evidence': f"'{q}' {sum(r['impressions'] for r in rows)} hiển thị, vị trí tốt nhất "
                                           f"{min(r['position'] for r in rows):.0f}"}
                              for q, rows in sorted(by_query.items(), key=lambda kv: -sum(r['impressions'] for r in kv[1]))
                              if min(r['position'] for r in rows) > 20][:50]}
    write_json(status_path, summary)
    return summary
