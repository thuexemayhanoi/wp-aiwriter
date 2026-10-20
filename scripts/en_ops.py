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
  rollout              one idempotent pass of everything the English side needs once VI-EN Core 0.5.1 is installed:
                       status -> routes on (if not live) -> missing English categories -> missing page pairs (each
                       checked by slug first) -> English site name from en/business.json (plugin 0.5.2+) -> public
                       verify of --urls. Ends quietly (NOT_INSTALLED) while the site still runs an older plugin; stops
                       at the first failure; writes only with --live.
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
POLICY_PATH = ROOT / 'en' / 'publication-policy.json'
BUSINESS_PATH = ROOT / 'en' / 'business.json'
EN_URLS = '/en/,/en/about/,/en/prices/,/en/contact/,/en/rental-guide/,/en/faq/,/en/motorbikes/'
MIN_VERSION = (0, 5, 1)   # the first plugin version with the REST API and the admin switch
OUTCOMES = ('NOT_INSTALLED', 'DRY_RUN', 'VERIFIED', 'FAILED')
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


def version_tuple(text):
    return tuple(int(x) for x in re.findall(r'\d+', str(text or ''))[:3]) or (0,)


def load_policy():
    return json.loads(POLICY_PATH.read_text(encoding='utf-8'))


def load_business():
    return json.loads(BUSINESS_PATH.read_text(encoding='utf-8'))


def ordered_category_ids(policy):
    """Unique parent-first English category registration, also for deterministic dry runs."""
    seen = set()
    order = []
    for raw in list(policy['category_ids']['parents']) + list(policy['category_ids']['leaves']):
        term_id = int(raw)
        if term_id not in seen:
            seen.add(term_id)
            order.append(term_id)
    return order


def rollout(rest, args, log, policy=None, business=None):
    """One idempotent pass: status -> routes on (if not live) -> missing English categories (parents first) -> missing
    page pairs (both pages checked by slug before the write) -> English site name (0.5.2+) -> public verify. Stops at
    the first failure, writes only with --live, and ends quietly with NOT_INSTALLED while the site still runs a plugin
    older than 0.5.1."""
    policy = policy or load_policy()
    business = business if business is not None else load_business()

    def fail(step, **detail):
        log.append({'action': 'rollout', 'outcome': 'FAILED', 'step': step, **detail})
        return 'FAILED'

    status, data = rest.call('nh-vien/v1/status')
    version = data.get('version') if isinstance(data, dict) else None
    if status == 404 or (status == 200 and version_tuple(version) < MIN_VERSION):
        log.append({'action': 'rollout', 'outcome': 'NOT_INSTALLED', 'http': status, 'version': version,
                    'message': 'VI-EN Core 0.5.1 is not installed on the site yet; nothing was done'})
        return 'NOT_INSTALLED'
    if status != 200 or not isinstance(data, dict):
        return fail('status', http=status, error=data)
    log.append({'action': 'status', 'http': status, 'result': brief_status(data)})
    writes = 0
    # 1. The English routes (the plugin runs its preflight, smoke test and rollback inside this one call).
    payload = {'enabled': True, 'confirm': bool(args.confirm)}
    if data.get('live'):
        log.append({'action': 'enable', 'skipped': 'routes already live'})
    elif not args.live:
        log.append({'action': 'enable', 'dry_run': True, 'would_post': 'nh-vien/v1/routes', 'payload': payload})
    else:
        status, reply = rest.call('nh-vien/v1/routes', payload)
        writes += 1
        if status != 200 or not isinstance(reply, dict):
            return fail('enable', http=status, error=reply)
        data = reply.get('status') if isinstance(reply.get('status'), dict) else {}
        log.append({'action': 'enable', 'http': status, 'write': True, 'result': reply.get('result'), 'status_after': brief_status(data)})
        if not data.get('live'):
            return fail('enable', message='the switch answered 200 but the routes are not live')
    # 2. The English categories, parents before leaves; the plugin answers true for a category that is English already.
    registered = {int(x) for x in data.get('english_categories') or []}
    for term_id in ordered_category_ids(policy):
        if term_id in registered:
            log.append({'action': 'register-category', 'id': term_id, 'skipped': 'already English'})
            continue
        if not args.live:
            log.append({'action': 'register-category', 'id': term_id, 'dry_run': True})
            continue
        status, reply = rest.call('nh-vien/v1/categories', {'id': term_id})
        writes += 1
        if status != 200 or not isinstance(reply, dict):
            return fail('register-category', id=term_id, http=status, error=reply)
        registered = {int(x) for x in reply.get('english_categories') or []} | {term_id}
        log.append({'action': 'register-category', 'id': term_id, 'http': status, 'write': True, 'result': sorted(registered)})
    # 3. The page pairs (Vietnamese page -> its English equivalent): both pages must be published with the expected slug.
    linked = {int(k): int(v) for k, v in (data.get('page_pairs') or {}).items()}
    for pair in policy.get('page_pairs', []):
        vi, en = int(pair['vi']), int(pair['en'])
        if linked.get(vi) == en:
            log.append({'action': 'link-pages', 'vi': vi, 'en': en, 'skipped': 'already linked'})
            continue
        for side, page_id in (('vi', vi), ('en', en)):
            status, page = rest.call(f'wp/v2/pages/{page_id}?_fields=id,slug,status,link')
            expected = pair.get(f'{side}_slug')
            found = {k: page.get(k) for k in ('slug', 'status', 'link')} if isinstance(page, dict) else page
            if status != 200 or not isinstance(page, dict) or page.get('status') != 'publish' or (expected and page.get('slug') != expected):
                return fail('link-pages', vi=vi, en=en, page=page_id, http=status, expected_slug=expected, found=found,
                            message=f'page {page_id} is not the published page /{expected}/; the pair was not written')
        if not args.live:
            log.append({'action': 'link-pages', 'vi': vi, 'en': en, 'dry_run': True})
            continue
        status, reply = rest.call('nh-vien/v1/pages', {'vi': vi, 'en': en})
        writes += 1
        if status != 200 or not isinstance(reply, dict):
            return fail('link-pages', vi=vi, en=en, http=status, error=reply)
        linked[vi] = en
        log.append({'action': 'link-pages', 'vi': vi, 'en': en, 'http': status, 'write': True, 'result': reply.get('page_pairs')})
    # 4. The English site name (plugin 0.5.2 and later report it): the one en/business.json gives the business.
    wanted_name = (business or {}).get('name_en', '')
    if 'site_name_en' in data and wanted_name:
        if (data.get('site_name_en') or '') == wanted_name:
            log.append({'action': 'site-name', 'skipped': 'already set', 'site_name_en': wanted_name})
        elif not args.live:
            log.append({'action': 'site-name', 'dry_run': True, 'would_post': 'nh-vien/v1/settings', 'payload': {'site_name_en': wanted_name}})
        else:
            status, reply = rest.call('nh-vien/v1/settings', {'site_name_en': wanted_name})
            writes += 1
            if status != 200 or not isinstance(reply, dict):
                return fail('site-name', http=status, error=reply)
            log.append({'action': 'site-name', 'http': status, 'write': True, 'result': reply.get('result')})
    if not args.live:
        log.append({'action': 'rollout', 'outcome': 'DRY_RUN', 'writes': 0, 'message': 'nothing was written; run with --live'})
        return 'DRY_RUN'
    # 5. The English pages as the public sees them.
    if not verify([u.strip() for u in args.urls.split(',') if u.strip()], log):
        return fail('verify', message='an English page did not verify; see the rows above')
    log.append({'action': 'rollout', 'outcome': 'VERIFIED', 'writes': writes, 'english_categories': sorted(registered), 'page_pairs': linked})
    return 'VERIFIED'


def write_report(log, name):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / f'{name}.json').write_text(json.dumps(log, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    text = f'### EN rollout: {name}\n\n```json\n' + json.dumps(log, ensure_ascii=False, indent=2)[:60000] + '\n```\n'
    print(text)
    seo_common.step_summary(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['status', 'enable', 'disable', 'undo', 'register-categories', 'link-pages', 'publish-pages', 'verify', 'rollout'])
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
    if args.action == 'rollout':
        outcome = rollout(Rest(user, password), args, log)
        write_report(log, 'rollout')
        print(f'EN rollout outcome: {outcome}')
        if os.getenv('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as handle:
                handle.write(f'outcome={outcome}\n')
        return 0 if outcome != 'FAILED' else 1
    ok = act(Rest(user, password), args, log)
    write_report(log, args.action)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
