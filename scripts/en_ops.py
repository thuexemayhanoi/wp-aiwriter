#!/usr/bin/env python3
"""Operate the English side of the live WordPress through the VI-EN Core 0.5.1 REST API, and verify it publicly.

Every write is explicit (one action per run, `--live` required, each write logged); without `--live` the script only
says what it would do. Reads print a fixed set of fields, never whole response bodies.

Actions:
  status               GET  nh-vien/v1/status
  enable | disable     POST nh-vien/v1/routes (enable needs --confirm on the production site)
  undo                 POST nh-vien/v1/routes/undo
  register-categories  POST nh-vien/v1/categories for each --ids, in the given order (parents first)
  link-pages           POST nh-vien/v1/pages for each --pairs vi:en
  publish-pages        set --ids pages to status publish through wp/v2/pages (only pages that are not published yet)
  verify               public checks of --urls: status, marker header, lang, canonical, title, H1, hreflang, no Vietnamese
"""
import argparse
import base64
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))
import engine  # noqa: E402
import seo_common  # noqa: E402

REPORT_DIR = ROOT / 'reports' / 'en-rollout'
EN_URLS = '/en/,/en/about/,/en/prices/,/en/contact/,/en/rental-guide/,/en/faq/,/en/motorbikes/'
VIETNAMESE = re.compile(r'\b(thuê xe máy|liên hệ|hướng dẫn|bảng giá|giới thiệu|xem thêm|bài viết|danh mục)\b', re.I)


class Rest:
    """Authenticated JSON client for the site's REST API; errors come back as (status, {code, message})."""

    def __init__(self, user, password):
        self.auth = base64.b64encode(f'{user}:{password}'.encode()).decode()

    def call(self, route, payload=None, method=None):
        url = engine.WP_URL + '/wp-json/' + route.lstrip('/')
        if urllib.parse.urlsplit(url).netloc != urllib.parse.urlsplit(engine.WP_URL).netloc:
            raise ValueError('Only the configured WordPress origin is allowed')
        headers = {'Accept': 'application/json', 'Authorization': 'Basic ' + self.auth,
                   'User-Agent': 'wp-aiwriter-en-ops/1.0', 'Cache-Control': 'no-cache'}
        data = None
        if payload is not None:
            headers['Content-Type'] = 'application/json; charset=utf-8'
            data = json.dumps(payload).encode()
        request = urllib.request.Request(url, data=data, headers=headers, method=method or ('POST' if payload is not None else 'GET'))
        try:
            with urllib.request.urlopen(request, timeout=40) as reply:
                return reply.status, self._json(reply.read())
        except urllib.error.HTTPError as exc:
            body = self._json(exc.read(200_000))
            safe = {k: body.get(k) for k in ('code', 'message') if isinstance(body, dict) and k in body}
            if isinstance(body, dict) and isinstance(body.get('data'), dict):
                safe['data'] = {k: body['data'].get(k) for k in ('status', 'checks', 'smoke') if k in body['data']}
            return exc.code, safe
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return 0, {'code': 'network', 'message': str(exc)[:200]}

    @staticmethod
    def _json(raw):
        try:
            return json.loads(raw.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return None


def ids_of(text):
    return [int(x) for x in re.findall(r'\d+', text or '')]


def pairs_of(text):
    return [(int(a), int(b)) for a, b in re.findall(r'(\d+)\s*:\s*(\d+)', text or '')]


def brief_status(data):
    if not isinstance(data, dict):
        return data
    keys = ('version', 'enabled', 'source', 'environment', 'rules_stored', 'live', 'home_page', 'home_url', 'pretty_permalinks',
            'yoast', 'pairs', 'independent_posts', 'english_categories', 'page_pairs', 'public_en_posts', 'last_change')
    out = {k: data.get(k) for k in keys}
    out['preflight'] = [{'id': c.get('id'), 'level': c.get('level'), 'ok': c.get('ok'), 'message': c.get('message')}
                        for c in data.get('preflight', []) if isinstance(c, dict)]
    return out


def act(rest, args, log):
    if args.action == 'status':
        status, data = rest.call('nh-vien/v1/status')
        log.append({'action': 'status', 'http': status, 'result': brief_status(data) if status == 200 else data})
        return status == 200
    if args.action in ('enable', 'disable', 'undo'):
        route = 'nh-vien/v1/routes/undo' if args.action == 'undo' else 'nh-vien/v1/routes'
        payload = {} if args.action == 'undo' else {'enabled': args.action == 'enable', 'confirm': bool(args.confirm)}
        if not args.live:
            log.append({'action': args.action, 'dry_run': True, 'would_post': route, 'payload': payload})
            return True
        status, data = rest.call(route, payload)
        entry = {'action': args.action, 'http': status, 'write': True}
        if status == 200 and isinstance(data, dict):
            entry['result'] = data.get('result')
            entry['status_after'] = brief_status(data.get('status'))
        else:
            entry['error'] = data
        log.append(entry)
        return status == 200
    if args.action == 'register-categories':
        ok = True
        for term_id in ids_of(args.ids):
            if not args.live:
                log.append({'action': 'register-category', 'id': term_id, 'dry_run': True})
                continue
            status, data = rest.call('nh-vien/v1/categories', {'id': term_id})
            log.append({'action': 'register-category', 'id': term_id, 'http': status, 'write': True,
                        'result': data.get('english_categories') if status == 200 and isinstance(data, dict) else data})
            ok = ok and status == 200
        return ok
    if args.action == 'link-pages':
        ok = True
        for vi, en in pairs_of(args.pairs):
            if not args.live:
                log.append({'action': 'link-pages', 'vi': vi, 'en': en, 'dry_run': True})
                continue
            status, data = rest.call('nh-vien/v1/pages', {'vi': vi, 'en': en})
            already = status == 409 and isinstance(data, dict) and data.get('code') == 'nh_vien_conflict'
            log.append({'action': 'link-pages', 'vi': vi, 'en': en, 'http': status, 'write': True,
                        'result': data.get('page_pairs') if status == 200 and isinstance(data, dict) else data})
            ok = ok and (status == 200 or already)
        return ok
    if args.action == 'publish-pages':
        ok = True
        for page_id in ids_of(args.ids):
            status, page = rest.call(f'wp/v2/pages/{page_id}?context=edit&_fields=id,slug,status,parent,title,link')
            if status != 200 or not isinstance(page, dict):
                log.append({'action': 'publish-page', 'id': page_id, 'http': status, 'error': page})
                ok = False
                continue
            if page.get('status') == 'publish':
                log.append({'action': 'publish-page', 'id': page_id, 'already': 'publish', 'link': page.get('link')})
                continue
            if not args.live:
                log.append({'action': 'publish-page', 'id': page_id, 'dry_run': True, 'from': page.get('status'), 'slug': page.get('slug')})
                continue
            status, result = rest.call(f'wp/v2/pages/{page_id}', {'status': 'publish'})
            entry = {'action': 'publish-page', 'id': page_id, 'http': status, 'write': True}
            if status == 200 and isinstance(result, dict):
                entry.update({'status_after': result.get('status'), 'link': result.get('link'), 'slug': result.get('slug')})
            else:
                entry['error'] = result
            log.append(entry)
            ok = ok and status == 200
        return ok
    raise ValueError(args.action)


def verify(urls, log):
    ok = True
    for path in urls:
        url = path if path.startswith('http') else engine.WP_URL + path
        reply = seo_common.http_get(url, timeout=30, retries=1)
        row = {'url': url, 'status': reply.status, 'final_url': reply.final_url, 'marker': reply.headers.get('x-nh-vien-lang'),
               'error': reply.error, 'problems': []}
        if reply.status != 200:
            row['problems'].append(f'HTTP {reply.status}')
        if seo_common.norm_url(reply.final_url) != seo_common.norm_url(url):
            row['problems'].append('redirected')
        if row['marker'] != 'en':
            row['problems'].append('no X-NH-VIEN-Lang: en header')
        if reply.text:
            page = seo_common.parse_page(reply.text)
            row.update({k: page.get(k) for k in ('title', 'lang', 'canonical', 'h1_text', 'h1_count', 'robots', 'description', 'jsonld_types', 'word_count')})
            row['hreflang'] = re.findall(r'<link[^>]+hreflang="([^"]+)"[^>]+href="([^"]+)"', reply.text)
            vietnamese = VIETNAMESE.findall(re.sub(r'<script.*?</script>|<style.*?</style>', '', reply.text, flags=re.S))
            row['vietnamese_hits'] = len(vietnamese)
            if not (page.get('lang') or '').lower().startswith('en'):
                row['problems'].append(f"html lang is {page.get('lang')!r}")
            if page.get('canonical') and seo_common.norm_url(page['canonical']) != seo_common.norm_url(url):
                row['problems'].append(f"canonical is {page['canonical']}")
            if not page.get('canonical'):
                row['problems'].append('no canonical')
            if page.get('h1_count') != 1:
                row['problems'].append(f"{page.get('h1_count')} H1")
            if not page.get('title'):
                row['problems'].append('no <title>')
            if 'noindex' in (page.get('robots') or ''):
                row['problems'].append('noindex')
            if len(vietnamese) > 2:
                row['problems'].append(f'{len(vietnamese)} Vietnamese phrases in the markup')
        ok = ok and not row['problems']
        log.append(row)
    return ok


def write_report(log, name):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / f'{name}.json').write_text(json.dumps(log, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    text = f'### EN rollout: {name}\n\n```json\n' + json.dumps(log, ensure_ascii=False, indent=2)[:60000] + '\n```\n'
    print(text)
    seo_common.step_summary(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['status', 'enable', 'disable', 'undo', 'register-categories', 'link-pages', 'publish-pages', 'verify'])
    parser.add_argument('--ids', default='')
    parser.add_argument('--pairs', default='')
    parser.add_argument('--urls', default=EN_URLS)
    parser.add_argument('--confirm', action='store_true')
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    log = []
    if args.action == 'verify':
        ok = verify([u.strip() for u in args.urls.split(',') if u.strip()], log)
        write_report(log, 'verify')
        return 0 if ok else 1
    user, password = os.getenv('WP_USERNAME'), os.getenv('WP_APPLICATION_PASSWORD')
    if not user or not password:
        print('BLOCKED: missing WP_USERNAME / WP_APPLICATION_PASSWORD; nothing was done')
        return 2
    ok = act(Rest(user, password), args, log)
    write_report(log, args.action)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
