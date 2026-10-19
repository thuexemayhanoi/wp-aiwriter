#!/usr/bin/env python3
"""Read-only probe of the live WordPress: what is installed and published, and how the English side answers.

Runs on GitHub Actions (which can reach the site) with the administrator application password of the publisher. It only
sends GET requests and never prints response bodies wholesale: it reports a fixed set of fields (versions, statuses,
IDs, slugs, headers) so that a session without access to the site can decide what to do next.
"""
import argparse
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))
import engine  # noqa: E402
import seo_common  # noqa: E402

REPORT_DIR = ROOT / 'reports' / 'probe'
DEFAULT_PAGES = '1758,1759,1760,1761,1762,1763,1764'
DEFAULT_CATEGORIES = '46,47,48,49,50,51,52,53,54,55,56'
DEFAULT_URLS = ('/,/en/,/en/about/,/en/prices/,/en/contact/,/en/rental-guide/,/en/faq/,/en/motorbikes/,'
                '/en/category/hanoi-motorbike-rental/,/en/category/hanoi-motorbike-rental/manual-motorbikes/,'
                '/sitemap_index.xml,/robots.txt,/wp-json/nh-vien/v1/status')


def ids(text):
    return [int(x) for x in re.findall(r'\d+', text or '')]


class Probe:
    def __init__(self, client):
        self.client = client

    def rest(self, route, **params):
        """A REST GET below /wp-json/ as the administrator; returns (status, data)."""
        url = engine.WP_URL + '/wp-json/' + route.lstrip('/')
        if params:
            url += ('&' if '?' in url else '?') + '&'.join(f'{k}={v}' for k, v in params.items())
        try:
            text, headers = self.client.request(url, webpage=True)
        except RuntimeError as exc:
            match = re.search(r'HTTP (\d+)', str(exc))
            return (int(match.group(1)) if match else 0), None
        try:
            return 200, json.loads(text)
        except ValueError:
            return 200, None


def pick(row, fields):
    out = {}
    for field in fields:
        value = row.get(field)
        if isinstance(value, dict) and 'rendered' in value:
            value = value.get('raw', value.get('rendered'))
        out[field] = value
    return out


def probe_admin(probe, pages, categories):
    report = {}
    status, data = probe.rest('wp/v2/users/me', context='edit', _fields='id,roles,capabilities')
    caps = (data or {}).get('capabilities', {}) if isinstance(data, dict) else {}
    report['user'] = {'http': status, 'roles': (data or {}).get('roles') if isinstance(data, dict) else None,
                      'manage_options': bool(caps.get('manage_options')), 'activate_plugins': bool(caps.get('activate_plugins'))}

    status, data = probe.rest('wp/v2/plugins', _fields='plugin,status,version,name')
    report['plugins'] = {'http': status, 'items': [pick(p, ('plugin', 'status', 'version', 'name')) for p in data]
                         if isinstance(data, list) else None}

    status, data = probe.rest('wp/v2/themes', _fields='stylesheet,status,version,name,template')
    report['themes'] = {'http': status, 'items': [pick(t, ('stylesheet', 'status', 'version', 'template')) for t in data]
                        if isinstance(data, list) else None}

    status, data = probe.rest('wp/v2/settings')
    keys = ('title', 'description', 'url', 'language', 'timezone', 'permalink_structure', 'page_on_front', 'page_for_posts',
            'show_on_front', 'posts_per_page', 'default_category')
    report['settings'] = {'http': status, 'values': {k: data.get(k) for k in keys} if isinstance(data, dict) else None}

    status, data = probe.rest('wp/v2/pages', include=','.join(map(str, pages)), status='any', context='edit', per_page=100,
                              _fields='id,slug,status,parent,title,template,link,date,modified,excerpt,yoast_head_json')
    rows = []
    if isinstance(data, list):
        for page in data:
            row = pick(page, ('id', 'slug', 'status', 'parent', 'title', 'template', 'link', 'date', 'modified'))
            row['excerpt_chars'] = len((page.get('excerpt') or {}).get('raw', '') or '')
            yoast = page.get('yoast_head_json') or {}
            row['yoast_title'] = yoast.get('title')
            row['yoast_canonical'] = yoast.get('canonical')
            row['yoast_robots'] = yoast.get('robots')
            rows.append(row)
    report['pages'] = {'http': status, 'requested': pages, 'items': rows if isinstance(data, list) else None}

    status, data = probe.rest('wp/v2/categories', include=','.join(map(str, categories)), hide_empty='false', per_page=100,
                              _fields='id,name,slug,parent,count,link')
    report['categories'] = {'http': status, 'requested': categories,
                            'items': [pick(c, ('id', 'name', 'slug', 'parent', 'count', 'link')) for c in data]
                            if isinstance(data, list) else None}

    status, data = probe.rest('wp/v2/menus', per_page=100, _fields='id,name,slug,locations,count')
    report['menus'] = {'http': status, 'items': [pick(m, ('id', 'name', 'slug', 'locations', 'count')) for m in data]
                       if isinstance(data, list) else None}
    status, data = probe.rest('wp/v2/menu-locations')
    report['menu_locations'] = {'http': status, 'items': {k: v.get('menu') for k, v in data.items()}
                                if isinstance(data, dict) else None}

    for slug in ('primary-en', 'footer-en'):
        menu = next((m for m in (report['menus']['items'] or []) if m.get('slug') == slug), None)
        if menu:
            status, data = probe.rest('wp/v2/menu-items', menus=menu['id'], per_page=100,
                                      _fields='id,title,url,object,object_id,parent,menu_order,status')
            report[f'menu_items_{slug}'] = {'http': status, 'items': [pick(i, ('id', 'title', 'url', 'object', 'object_id', 'parent', 'menu_order', 'status'))
                                                                         for i in data] if isinstance(data, list) else None}

    status, data = probe.rest('nh-vien/v1/status')
    report['nh_vien_status'] = {'http': status, 'data': data if isinstance(data, dict) else None}

    status, data = probe.rest('wp/v2/posts', status='any', context='edit', per_page=100, categories=','.join(map(str, categories)),
                              _fields='id,slug,status,title,categories,link')
    report['posts_in_en_categories'] = {'http': status, 'items': [pick(p, ('id', 'slug', 'status', 'title', 'categories', 'link'))
                                                                  for p in data] if isinstance(data, list) else None}
    return report


def probe_public(urls):
    results = []
    for path in urls:
        url = path if path.startswith('http') else engine.WP_URL + path
        reply = seo_common.http_get(url, timeout=25, retries=1)
        row = {'url': url, 'status': reply.status, 'final_url': reply.final_url, 'error': reply.error,
               'x_nh_vien_lang': reply.headers.get('x-nh-vien-lang'), 'content_type': reply.headers.get('content-type'),
               'cache': reply.headers.get('x-litespeed-cache') or reply.headers.get('cf-cache-status') or reply.headers.get('x-cache')}
        if reply.text and 'html' in (reply.headers.get('content-type') or ''):
            page = seo_common.parse_page(reply.text)
            row.update({k: page.get(k) for k in ('title', 'lang', 'canonical', 'h1_text', 'h1_count', 'robots', 'description', 'jsonld_types', 'word_count')})
            row['hreflang'] = re.findall(r'<link[^>]+hreflang="([^"]+)"[^>]+href="([^"]+)"', reply.text)
            row['vietnamese_words_sample'] = len(re.findall(r'\b(thuê|xe máy|giá|liên hệ|hướng dẫn)\b', reply.text, re.I))
        elif reply.text and path.endswith('.xml'):
            row['sitemaps'] = re.findall(r'<loc>([^<]+)</loc>', reply.text)[:40]
        elif reply.text and path.endswith('robots.txt'):
            row['robots_txt'] = reply.text[:800]
        elif reply.text and 'json' in (reply.headers.get('content-type') or ''):
            try:
                data = json.loads(reply.text)
                row['json_keys'] = sorted(data)[:40] if isinstance(data, dict) else type(data).__name__
                row['json_code'] = data.get('code') if isinstance(data, dict) else None
            except ValueError:
                row['json_keys'] = None
        results.append(row)
    return results


def summary(report):
    lines = ['### WordPress probe (read-only)', '']
    admin = report.get('admin') or {}
    if admin:
        user = admin.get('user', {})
        lines.append(f"- Authenticated: HTTP {user.get('http')}; roles {user.get('roles')}; manage_options={user.get('manage_options')}")
        plugins = admin.get('plugins', {}).get('items') or []
        interesting = [p for p in plugins if any(k in (p.get('plugin') or '') for k in ('nguyen-ha', 'wordpress-seo', 'deployer', 'litespeed', 'cache', 'polylang', 'wpml', 'wpcode'))]
        lines.append('- Plugins of interest: ' + '; '.join(f"{p.get('plugin')} {p.get('version')} ({p.get('status')})" for p in interesting))
        themes = [t for t in (admin.get('themes', {}).get('items') or []) if t.get('status') == 'active']
        lines.append('- Active theme: ' + '; '.join(f"{t.get('stylesheet')} {t.get('version')}" for t in themes))
        values = admin.get('settings', {}).get('values') or {}
        lines.append(f"- Permalinks: {values.get('permalink_structure')!r}; show_on_front={values.get('show_on_front')}; page_on_front={values.get('page_on_front')}; language={values.get('language')}")
        pages = admin.get('pages', {}).get('items') or []
        lines.append('- EN pages: ' + '; '.join(f"#{p['id']} /{p['slug']} {p['status']} parent={p['parent']} template={p.get('template') or '-'}" for p in pages))
        cats = admin.get('categories', {}).get('items') or []
        lines.append('- EN categories: ' + '; '.join(f"#{c['id']} {c['slug']} parent={c['parent']} count={c['count']}" for c in cats))
        menus = admin.get('menus', {}).get('items') or []
        lines.append('- Menus: ' + '; '.join(f"#{m['id']} {m['slug']} locations={m.get('locations')} items={m.get('count')}" for m in menus))
        lines.append(f"- Menu locations: {admin.get('menu_locations', {}).get('items')}")
        nh = admin.get('nh_vien_status', {})
        lines.append(f"- nh-vien/v1/status: HTTP {nh.get('http')}" + (f"; version {nh['data'].get('version')}; enabled={nh['data'].get('enabled')}; source={nh['data'].get('source')}; live={nh['data'].get('live')}; rules_stored={nh['data'].get('rules_stored')}; english_categories={nh['data'].get('english_categories')}; page_pairs={nh['data'].get('page_pairs')}" if nh.get('data') else ''))
        posts = admin.get('posts_in_en_categories', {}).get('items') or []
        lines.append(f"- Posts in EN categories: {len(posts)}")
    lines.append('')
    lines.append('| URL | HTTP | final | marker | lang | canonical | H1 |')
    lines.append('|---|---|---|---|---|---|---|')
    for row in report.get('public', []):
        lines.append(f"| {row['url']} | {row['status']} | {row['final_url'] if row['final_url'] != row['url'] else ''} | {row.get('x_nh_vien_lang') or ''} | {row.get('lang') or ''} | {row.get('canonical') or ''} | {(row.get('h1_text') or '')[:60]} |")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pages', default=DEFAULT_PAGES)
    parser.add_argument('--categories', default=DEFAULT_CATEGORIES)
    parser.add_argument('--urls', default=DEFAULT_URLS)
    parser.add_argument('--public-only', action='store_true')
    args = parser.parse_args()
    report = {'at': engine.now(), 'site': engine.WP_URL}
    user, password = os.getenv('WP_USERNAME'), os.getenv('WP_APPLICATION_PASSWORD')
    if not args.public_only and user and password:
        report['admin'] = probe_admin(Probe(engine.WPClient(user, password)), ids(args.pages), ids(args.categories))
    elif not args.public_only:
        report['admin_error'] = 'missing WP_USERNAME / WP_APPLICATION_PASSWORD; authenticated probe skipped'
    report['public'] = probe_public([u.strip() for u in args.urls.split(',') if u.strip()])
    seo_common.write_json(REPORT_DIR / 'probe.json', report)
    text = summary(report)
    (REPORT_DIR / 'summary.md').write_text(text, encoding='utf-8')
    print(text)
    seo_common.step_summary(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
