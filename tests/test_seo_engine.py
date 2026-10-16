"""Offline tests for the read-only SEO engine and the gated fix pipeline (no network)."""
import csv
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from seo import common, crawl, fixes, htmlparse, linking, net  # noqa: E402
from seo import __main__ as cli  # noqa: E402

SITE = 'https://blog.rentbikehanoi.com'
LOREM = ('Người thuê xe máy ở Hà Nội nên kiểm tra phanh, đèn, lốp và giấy tờ trước khi nhận xe. '
         'Việc chụp ảnh hiện trạng giúp tránh tranh chấp khi trả xe. ')


def post(i, title, body, cat=20, modified='2026-10-16T10:00:00', slug=None, extra_head='', h1s=None,
         canonical=None, description='Mô tả ngắn gọn về chủ đề thuê xe máy ở Hà Nội cho người mới đến thành phố.',
         robots='index, follow', theme_schema=False, matrix=None):
    slug = slug or f'excel-{i}-bai-{i}'
    return {'id': i, 'slug': slug, 'title': title, 'body': body, 'cat': cat, 'modified': modified,
            'extra_head': extra_head, 'h1s': h1s, 'canonical': canonical, 'description': description,
            'robots': robots, 'theme_schema': theme_schema, 'matrix': matrix or i + 100}


class FakeSite:
    def __init__(self):
        self.calls = []
        long_text = ' '.join([LOREM] * 25)
        dup_text = ('Bài này hướng dẫn cách gửi xe máy ở trung tâm Hà Nội, chọn bãi có vé, ghi biển số và chụp ảnh vị trí. '
                    * 30)
        self.posts = [
            post(101, 'Kiểm tra xe máy trước khi thuê ở Hà Nội',
                 f'<p>{long_text}</p><h2>Bước kiểm tra phanh</h2><p>Hãy xem <a href="{SITE}/excel-102-bai-102/">cách chụp ảnh hiện trạng xe</a> '
                 f'và <a href="{SITE}/missing-post/">bài đã xóa</a>.</p><p>Nguồn: <a href="https://www.csgt.vn/luat">CSGT</a></p>'),
            post(102, 'Chụp ảnh hiện trạng xe máy khi nhận xe thuê',
                 f'<p>{long_text}</p><h2>Ảnh cần chụp</h2><p>Quay lại <a href="{SITE}/excel-101-bai-101/">kiểm tra xe máy trước khi thuê</a>.</p>'
                 '<p>Theo nghị định, mức phạt từ 800.000 đồng đến 1.000.000 đồng khi không mang giấy tờ.</p>'
                 '<p>Liên hệ 0912 345 678 nếu cần hỗ trợ. Tham khảo <a href="https://dead.example.com/x">tài liệu</a>.</p>',
                 robots='noindex, follow'),
            post(103, 'Gửi xe máy ở trung tâm Hà Nội', f'<p>{dup_text}</p><h2>Bãi gửi</h2><p>{long_text}</p>'),
            post(104, 'Bãi gửi xe máy ở trung tâm Hà Nội', f'<p>{dup_text}</p><h2>Bãi gửi</h2><p>{long_text}</p>',
                 h1s=['Bãi gửi xe máy ở trung tâm Hà Nội', 'Tên website'], theme_schema=True),
            post(105, 'Kiểm tra xe máy trước khi thuê ở Hà Nội',
                 f'<p>{long_text} Ở trung tâm, việc gửi xe máy cần chọn bãi có vé rõ ràng và chụp ảnh hiện trạng xe.</p>'
                 '<h2>Ghi chú</h2><h4>Nhảy cấp</h4><p>Liên hệ 0987 654 321 để được tư vấn.</p>',
                 canonical=f'{SITE}/excel-101-bai-101/', description=''),
            post(106, 'Bài mồ côi về đường một chiều', f'<p>{long_text}</p><h2>Đường một chiều</h2><p>{long_text}</p>'),
        ]
        self.cats = [{'id': 15, 'name': 'Cẩm nang', 'parent': 0, 'slug': 'cam-nang', 'count': 0},
                     {'id': 19, 'name': 'Hãng xe', 'parent': 15, 'slug': 'hang-xe', 'count': 0},
                     {'id': 20, 'name': 'Hãng xe máy', 'parent': 19, 'slug': 'hang-xe-may', 'count': 6},
                     {'id': 30, 'name': 'Trống', 'parent': 0, 'slug': 'trong', 'count': 0}]
        self.pages = [{'id': 7, 'slug': 'lien-he', 'title': 'Liên hệ', 'body': '<p>Liên hệ chúng tôi qua email.</p>',
                       'modified': '2026-10-01T00:00:00'}]

    # ---- helpers ------------------------------------------------------------------------
    def url_of(self, p):
        return f"{SITE}/{p['slug']}/"

    def cat_link(self, c):
        return f"{SITE}/category/{c['slug']}/"

    def rest_post(self, p):
        content = f"<!-- wp-aiwriter:matrix_id={p['matrix']};sha256=x -->\n" + p['body']
        return {'id': p['id'], 'slug': p['slug'], 'status': 'publish', 'type': 'post', 'link': self.url_of(p),
                'date_gmt': '2026-10-15T00:00:00', 'modified_gmt': p['modified'],
                'title': {'rendered': p['title']}, 'content': {'rendered': content},
                'excerpt': {'rendered': '<p>Tóm tắt</p>'}, 'author': 1, 'featured_media': 0,
                'categories': [p['cat']], 'tags': [],
                'yoast_head_json': {'title': p['title'] + ' - Blog', 'description': p.get('yoast_description', p['description']),
                                    'canonical': p['canonical'] or self.url_of(p),
                                    'robots': {'index': p['robots'].split(',')[0].strip(), 'follow': 'follow'},
                                    'og_image': [], 'schema': {'@graph': [{'@type': 'Article'}]}}}

    def rest_page(self, p):
        return {'id': p['id'], 'slug': p['slug'], 'status': 'publish', 'type': 'page', 'link': self.url_of(p),
                'date_gmt': '2026-10-01T00:00:00', 'modified_gmt': p['modified'],
                'title': {'rendered': p['title']}, 'content': {'rendered': p['body']},
                'excerpt': {'rendered': ''}, 'author': 1, 'featured_media': 0, 'parent': 0, 'yoast_head_json': None}

    def html(self, title, body, canonical, description='', robots='index, follow', h1s=None, schema=None, extra=''):
        graph = schema if schema is not None else [{'@type': 'WebPage'}, {'@type': 'Organization', 'name': 'Thuê Xe'}]
        head = (f'<title>{title}</title><meta name="viewport" content="width=device-width">'
                f'<meta name="robots" content="{robots}">'
                + (f'<meta name="description" content="{description}">' if description else '')
                + f'<link rel="canonical" href="{canonical}">'
                + '<script type="application/ld+json" class="yoast-schema-graph">'
                + json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False) + '</script>'
                + '<!-- This site is optimized with the Yoast SEO plugin v23.5 -->' + extra)
        h1 = ''.join(f'<h1>{h}</h1>' for h in (h1s or [title]))
        nav = f'<nav><a href="{SITE}/">Trang chủ</a><a href="{SITE}/category/hang-xe-may/">Hãng xe máy</a></nav>'
        return f'<!doctype html><html lang="vi"><head>{head}</head><body>{nav}{h1}{body}</body></html>'

    def response(self, status, body=b'', headers=None):
        h = {'content-type': 'text/html; charset=utf-8', **(headers or {})}
        return status, h, body if isinstance(body, bytes) else body.encode()

    # ---- transport ----------------------------------------------------------------------
    def __call__(self, method, url, headers, timeout, max_bytes):
        self.calls.append((method, url, dict(headers)))
        parts = urllib.parse.urlsplit(url)
        q = dict(urllib.parse.parse_qsl(parts.query))
        if parts.netloc == 'dead.example.com':
            return self.response(404, 'gone')
        if parts.netloc == 'www.csgt.vn':
            return self.response(200, 'ok')
        if parts.scheme == 'http':
            return self.response(301, '', {'location': SITE + parts.path})
        path = parts.path
        if path.startswith('/wp-json/'):
            return self.rest(path[len('/wp-json/'):], q)
        if path == '/robots.txt':
            return self.response(200, f'User-agent: *\nDisallow: /wp-admin/\nUser-agent: GPTBot\nDisallow: /\n'
                                      f'Sitemap: {SITE}/sitemap_index.xml\n', {'content-type': 'text/plain'})
        if path == '/sitemap_index.xml':
            return self.response(200, f'<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                      f'<sitemap><loc>{SITE}/post-sitemap.xml</loc></sitemap></sitemapindex>',
                                 {'content-type': 'application/xml'})
        if path == '/post-sitemap.xml':
            urls = [self.url_of(p) for p in self.posts if p['id'] not in (106,)] + [f'{SITE}/old-deleted-url/']
            body = ''.join(f'<url><loc>{u}</loc><lastmod>2026-10-16</lastmod></url>' for u in urls)
            return self.response(200, f'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>',
                                 {'content-type': 'application/xml'})
        if path == '/wp-sitemap.xml':
            return self.response(301, '', {'location': f'{SITE}/sitemap_index.xml'})
        if path in ('/missing-post/', '/old-deleted-url/', '/llms.txt') or 'seo-audit-probe' in path:
            return self.response(404, '<html><title>Not found</title></html>')
        if path == '/':
            links = ''.join(f'<a href="{self.cat_link(c)}">{c["name"]}</a>' for c in self.cats)
            return self.response(200, self.html('Blog thuê xe', links, SITE + '/', 'Trang chủ blog về thuê xe máy ở Hà Nội cho khách mới'))
        for c in self.cats:
            base = f"/category/{c['slug']}/"
            if path == base or path == base + 'page/2/':
                members = [p for p in self.posts if p['cat'] == c['id']]
                if path.endswith('page/2/'):
                    members, nxt = members[3:], ''
                else:
                    members, nxt = members[:3], (f'<link rel="next" href="{SITE}{base}page/2/">' if len(members) > 3 else '')
                links = ''.join(f'<a href="{self.url_of(p)}">{p["title"]}</a>' for p in members)
                return self.response(200, self.html(c['name'] + ' - Blog', links, SITE + path,
                                                    'Các bài trong chuyên mục ' + c['name'] + ' dành cho người thuê xe', extra=nxt))
        for p in self.posts:
            if path == f"/{p['slug']}":
                return self.response(301, '', {'location': self.url_of(p)})
            if path == f"/{p['slug']}/":
                schema = [{'@type': 'WebPage'}, {'@type': 'Article', 'headline': p['title'], 'datePublished': 'x',
                                                  'author': {'name': 'A'}}, {'@type': 'BreadcrumbList', 'itemListElement': [1]},
                          {'@type': 'Organization', 'name': 'Thuê Xe'}, {'@type': 'Person', 'name': 'admin'}]
                extra = p['extra_head'] + ('<script type="application/ld+json">{"@type":"Article","headline":"theme"}</script>'
                                           if p['theme_schema'] else '')
                return self.response(200, self.html(p['title'] + ' - Blog', p['body'], p['canonical'] or self.url_of(p),
                                                    p['description'], p['robots'], p['h1s'], schema, extra))
        for p in self.pages:
            if path == f"/{p['slug']}/":
                return self.response(200, self.html(p['title'], p['body'], self.url_of(p), 'Trang liên hệ của blog thuê xe máy'))
        return self.response(404, 'not found')

    def rest(self, route, q):
        route = route.rstrip('/')
        if route == '':
            return self.response(200, json.dumps({'name': 'Blog', 'url': SITE, 'home': SITE,
                                                  'namespaces': ['wp/v2', 'yoast/v1']}), {'content-type': 'application/json'})
        if route == 'wp/v2/categories':
            items = [{**c, 'link': self.cat_link(c), 'description': ''} for c in self.cats]
        elif route == 'wp/v2/tags' or route == 'wp/v2/media':
            items = []
        elif route == 'wp/v2/posts':
            items = [self.rest_post(p) for p in self.posts]
        elif route == 'wp/v2/pages':
            items = [self.rest_page(p) for p in self.pages]
        else:
            return self.response(404, '{}', {'content-type': 'application/json'})
        if 'include' in q:
            wanted = {int(x) for x in q['include'].split(',')}
            items = [i for i in items if i['id'] in wanted]
        per_page, page = int(q.get('per_page', 10)), int(q.get('page', 1))
        total_pages = max(1, -(-len(items) // per_page))
        chunk = items[(page - 1) * per_page: page * per_page]
        return self.response(200, json.dumps(chunk, ensure_ascii=False),
                             {'content-type': 'application/json', 'x-wp-total': str(len(items)),
                              'x-wp-totalpages': str(total_pages)})


class SEOEngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ['SEO_ROOT'] = self.tmp
        (pathlib.Path(self.tmp) / 'data/seo').mkdir(parents=True)
        cfg = json.loads((ROOT / 'data/seo/config.json').read_text())
        cfg['http']['min_interval_seconds'] = 0
        (pathlib.Path(self.tmp) / 'data/seo/config.json').write_text(json.dumps(cfg))
        ledger = {'posts': {'300': {'wp_id': 991, 'phase': 'VERIFIED', 'status': 'publish', 'url': SITE + '/x/'},
                            '201': {'wp_id': 101, 'phase': 'VERIFIED', 'status': 'publish'}}}
        (pathlib.Path(self.tmp) / 'data/publication-state.json').write_text(json.dumps(ledger))
        self.site = FakeSite()
        self._orig = cli.fetcher
        cli.fetcher = lambda cfg: net.Fetcher(cfg, transport=self.site, sleep=lambda s: None)
        for k in ('GSC_SERVICE_ACCOUNT_JSON', 'GSC_PROPERTY', 'GITHUB_STEP_SUMMARY'):
            os.environ.pop(k, None)

    def tearDown(self):
        cli.fetcher = self._orig
        os.environ.pop('SEO_ROOT', None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def matrix(self):
        with open(pathlib.Path(self.tmp) / 'reports/seo-matrix.csv', encoding='utf-8-sig') as fh:
            return list(csv.DictReader(fh))

    def codes_for(self, rows, post_id):
        return {r['Issue Code'] for r in rows if str(r['Post ID']) == str(post_id)}

    def test_full_run_detects_seeded_problems_read_only(self):
        self.assertEqual(cli.main(['run', '--full', '--external']), 0)
        out = pathlib.Path(self.tmp)
        for name in ('data/posts-index.jsonl', 'reports/seo-matrix.csv', 'reports/internal-link-matrix.csv',
                     'reports/cannibalization.csv', 'reports/content-gaps.csv', 'reports/technical-audit.json',
                     'reports/seo-dashboard.md', 'reports/change-log.md'):
            self.assertTrue((out / name).exists(), name)
        rows = self.matrix()
        self.assertEqual(list(rows[0].keys()), ['Issue Key', 'Post ID', 'Matrix ID', 'URL', 'Category', 'Issue Code',
                                                'Issue', 'Evidence', 'Priority', 'Suggested Fix', 'Risk', 'Status',
                                                'Last Checked', 'QA Result'])
        self.assertEqual([r['Priority'] for r in rows], sorted((r['Priority'] for r in rows)))
        self.assertIn('T-NOINDEX', self.codes_for(rows, 102))
        self.assertIn('T-CANONICAL-MISMATCH', self.codes_for(rows, 105))
        self.assertIn('T-META-DESC-MISSING', self.codes_for(rows, 105))
        self.assertIn('T-HEADING-SKIP', self.codes_for(rows, 105))
        self.assertIn('T-TITLE-DUPLICATE', self.codes_for(rows, 101))
        self.assertIn('T-H1-MULTIPLE', self.codes_for(rows, 104))
        self.assertIn('T-SCHEMA-NON-YOAST', self.codes_for(rows, 104))
        self.assertIn('T-SCHEMA-DUPLICATE-TYPE', self.codes_for(rows, 104))
        self.assertIn('L-BROKEN-INTERNAL', self.codes_for(rows, 101))
        self.assertIn('L-BROKEN-EXTERNAL', self.codes_for(rows, 102))
        self.assertIn('L-ORPHAN', self.codes_for(rows, 106))
        self.assertIn('T-SITEMAP-MISSING-URL', self.codes_for(rows, 106))
        self.assertIn('C-FINE-AMOUNT', self.codes_for(rows, 102))
        self.assertIn('C-LEGAL-NO-OFFICIAL-SOURCE', self.codes_for(rows, 102))
        self.assertTrue({'C-NEAR-DUPLICATE', 'C-DUPLICATE-CONTENT'} & self.codes_for(rows, 103) | self.codes_for(rows, 104))
        all_codes = {r['Issue Code'] for r in rows}
        for code in ('T-SITEMAP-BAD-URL', 'T-LEDGER-MISSING', 'G-GSC-NOT-CONFIGURED', 'C-NAP-INCONSISTENT',
                     'A-AI-CRAWLER-POLICY', 'T-CWV-NOT-MEASURED', 'T-FEATURED-IMAGE-MISSING', 'A-AUTHOR-GENERIC'):
            self.assertIn(code, all_codes)
        self.assertNotIn('T-DUPLICATE-COPY', all_codes)  # near-duplicates are not published copies
        self.assertNotIn('T-HTTPS-REDIRECT', all_codes)
        self.assertNotIn('T-SOFT-404', all_codes)
        self.assertNotIn('T-TRAILING-SLASH-DUP', all_codes)
        ledger_rows = [r for r in rows if r['Issue Code'] == 'T-LEDGER-MISSING']
        self.assertEqual([r['Post ID'] for r in ledger_rows], ['991'])
        verified = {r['QA Result'].split(' ')[0] for r in rows}
        self.assertTrue({'VERIFIED', 'NEEDS'} <= verified)
        # Read-only: only GET/HEAD and never an Authorization header.
        self.assertTrue(all(m in ('GET', 'HEAD') for m, _, _ in self.site.calls))
        self.assertFalse(any('Authorization' in h for _, _, h in self.site.calls))
        tech = json.loads((out / 'reports/technical-audit.json').read_text())
        self.assertTrue(tech['read_only'])
        self.assertEqual(tech['counts']['posts'], 6)
        self.assertEqual(tech['stack']['yoast_version'], '23.5')
        self.assertIn('GPTBot', ' '.join(r['Evidence'] for r in rows if r['Issue Code'] == 'A-AI-CRAWLER-POLICY'))
        index = [json.loads(l) for l in (out / 'data/posts-index.jsonl').read_text().splitlines()]
        self.assertTrue(all(r.get('page', {}).get('status') for r in index))
        self.assertEqual({r['matrix_id'] for r in index if r['type'] == 'post'}, {201, 202, 203, 204, 205, 206})

    def test_link_suggestions_use_existing_unlinked_text(self):
        cli.main(['run', '--full'])
        with open(pathlib.Path(self.tmp) / 'reports/internal-link-matrix.csv', encoding='utf-8-sig') as fh:
            rows = list(csv.DictReader(fh))
        self.assertTrue(rows)
        orphan_rows = [r for r in rows if r['target_post_id'] == '106']
        self.assertTrue(orphan_rows and orphan_rows[0]['priority'] == 'P1')
        cache = common.read_json(pathlib.Path(self.tmp) / 'data/seo/cache/content.json.gz')
        for r in rows:
            if r['suggested_anchor']:
                body = cache[f"post:{r['source_post_id']}"]['content']['rendered']
                hits = fixes.find_occurrences(body, r['suggested_anchor'])
                self.assertTrue(hits, r['suggested_anchor'])
        pairs = {(r['source_post_id'], r['target_post_id']) for r in rows}
        self.assertNotIn(('101', '102'), pairs)  # already linked

    def test_incremental_sync_fetches_only_changed(self):
        cli.main(['run', '--full'])
        calls_before = len(self.site.calls)
        cli.main(['sync'])
        state = common.read_json(pathlib.Path(self.tmp) / 'data/seo/state.json')
        self.assertEqual(state['sync_stats']['post']['fetched'], 0)
        self.site.posts[0]['modified'] = '2026-10-17T00:00:00'
        cli.main(['sync'])
        state = common.read_json(pathlib.Path(self.tmp) / 'data/seo/state.json')
        self.assertEqual(state['sync_stats']['post']['fetched'], 1)
        self.assertEqual(state['sync_stats']['post']['updated'], 1)
        self.assertGreater(len(self.site.calls), calls_before)

    def test_change_log_and_delta(self):
        cli.main(['run', '--full'])
        self.site.posts[1]['robots'] = 'index, follow'
        cli.main(['run', '--full'])
        log = (pathlib.Path(self.tmp) / 'reports/change-log.md').read_text()
        self.assertEqual(log.count('<!-- seo-engine-entry -->'), 2)
        self.assertIn('T-NOINDEX|post:102', log)

    def test_overrides_set_status(self):
        cli.main(['run', '--full'])
        key = next(r['Issue Key'] for r in self.matrix() if r['Issue Code'] == 'T-NOINDEX')
        (pathlib.Path(self.tmp) / 'data/seo/issue-overrides.json').write_text(
            json.dumps({'issues': {key: {'status': 'ACCEPTED', 'note': 'trang cố ý noindex'}}}))
        cli.main(['audit'])
        row = next(r for r in self.matrix() if r['Issue Key'] == key)
        self.assertEqual(row['Status'], 'ACCEPTED — trang cố ý noindex')

    def test_refuses_mixed_domains(self):
        cfg = common.load_config()
        cfg['allowed_hosts'] = ['blog.rentbikehanoi.com', 'rentbikehanoi.com']
        (pathlib.Path(self.tmp) / 'data/seo/config.json').write_text(json.dumps(cfg))
        with self.assertRaises(ValueError):
            common.load_config()

    def test_published_copy_reported_once_and_kept_out_of_linking(self):
        original = self.site.posts[0]
        self.site.posts.append(post(107, original['title'], original['body'], slug='excel-101-bai-101-2',
                                    matrix=original['matrix']))
        cli.main(['run', '--full'])
        rows = self.matrix()
        copy_rows = [r for r in rows if r['Issue Code'] == 'T-DUPLICATE-COPY']
        self.assertEqual([r['Post ID'] for r in copy_rows], ['107'])
        self.assertIn('WP 101', copy_rows[0]['Evidence'])
        self.assertEqual(self.codes_for(rows, 107), {'T-DUPLICATE-COPY'})
        cannibal_ids = {r['Post ID'] for r in rows if r['Issue Code'] == 'C-CANNIBALIZATION'}
        self.assertNotIn('107', cannibal_ids)
        self.assertFalse([r for r in rows if r['Issue Code'] == 'C-CANNIBALIZATION' and 'excel-101-bai-101-2' in r['Evidence']])
        with open(pathlib.Path(self.tmp) / 'reports/internal-link-matrix.csv', encoding='utf-8-sig') as fh:
            links = list(csv.DictReader(fh))
        self.assertFalse([r for r in links if '107' in (r['source_post_id'], r['target_post_id'])])
        dashboard = (pathlib.Path(self.tmp) / 'reports/seo-dashboard.md').read_text()
        self.assertIn('bản sao trùng lặp đang xuất bản', dashboard)

    def test_noindex_page_skips_tag_checks(self):
        self.site.posts[1]['description'] = ''
        cli.main(['run', '--full'])
        codes = self.codes_for(self.matrix(), 102)
        self.assertIn('T-NOINDEX', codes)
        self.assertNotIn('T-META-DESC-MISSING', codes)

    def test_meta_description_sources(self):
        self.site.posts[0]['extra_head'] = '<meta name="description" content="Mô tả do theme in thêm">'
        self.site.posts[2]['yoast_description'] = ''
        cli.main(['run', '--full'])
        rows = self.matrix()
        self.assertIn('T-META-DESC-MULTIPLE', self.codes_for(rows, 101))
        evidence = ' '.join(r['Evidence'] for r in rows if r['Issue Code'] == 'T-META-DESC-NOT-YOAST')
        self.assertIn('excel-103-bai-103', evidence)
        index = [json.loads(l) for l in (pathlib.Path(self.tmp) / 'data/posts-index.jsonl').read_text().splitlines()]
        page = next(r['page'] for r in index if r['id'] == 101)
        self.assertNotIn('heading_outline', page)
        self.assertEqual(page['meta_description_count'], 2)


class CompactAndHostTest(unittest.TestCase):
    def test_compact_page_is_idempotent_and_keeps_audited_fields(self):
        page = {'url': SITE + '/a/', 'final_url': SITE + '/a/', 'heading_outline': [[2, 'x']],
                'og': {'og:title': 't', 'og:image': 'https://img/x.jpg'},
                'jsonld': {'types': {'WebPage': 1}, 'nodes': [
                    {'types': ['WebPage'], 'id': SITE + '/a/', 'origin': 'yoast', 'keys': ['name'], 'name': 'Tiêu đề',
                     'telephone': None},
                    {'types': ['Organization'], 'id': SITE + '/#org', 'origin': 'yoast', 'keys': ['name'],
                     'name': 'Thuê xe', 'telephone': '0900000000'}]}}
        once = crawl.compact_page(page)
        self.assertEqual(once, crawl.compact_page(once))
        self.assertNotIn('heading_outline', once)
        self.assertNotIn('url', once)
        self.assertEqual(once['final_url'], SITE + '/a/')
        self.assertEqual(once['og'], {'og:image': 'https://img/x.jpg'})
        self.assertNotIn('name', once['jsonld']['nodes'][0])
        self.assertEqual(once['jsonld']['nodes'][1]['name'], 'Thuê xe')
        self.assertEqual(once['jsonld']['nodes'][1]['telephone'], '0900000000')
        self.assertTrue(all('id' not in n for n in once['jsonld']['nodes']))

    def test_failed_head_is_confirmed_with_get_and_legacy_failures_rechecked(self):
        tmp = tempfile.mkdtemp()
        os.environ['SEO_ROOT'] = tmp
        try:
            cfg = {'site_url': SITE, 'allowed_hosts': ['blog.rentbikehanoi.com'], 'user_agent': 'test',
                   'http': {'min_interval_seconds': 0, 'retries': 1}, 'external_links': {'recheck_after_days': 14}}
            calls = []

            def transport(method, url, headers, timeout, max_bytes):
                calls.append((method, url))
                return (404, {}, b'') if method == 'HEAD' else (200, {}, b'ok')
            f = net.Fetcher(cfg, transport=transport, sleep=lambda s: None)
            with self.assertRaises(ValueError):
                f.head_or_get('https://vendor.example/p')  # internal checks never leave the audited host
            self.assertEqual(f.head_or_get('https://vendor.example/p', internal_only=False).status, 200)
            fresh = common.iso()
            common.write_json(crawl.link_status_path(), {
                'https://vendor.example/old': {'kind': 'external', 'status': 404, 'checked_at': fresh},
                'https://vendor.example/ok': {'kind': 'external', 'status': 200, 'checked_at': fresh}})
            records = [{'external_links': [{'href': 'https://vendor.example/old'}, {'href': 'https://vendor.example/ok'}]}]
            calls.clear()
            result = crawl.check_external(cfg, f, records)
            self.assertEqual(result['checked_now'], 1)  # only the HEAD-only failure, the fresh success is cached
            status = common.read_json(crawl.link_status_path())
            self.assertEqual(status['https://vendor.example/old']['status'], 200)
            self.assertEqual(status['https://vendor.example/old']['method'], crawl.CHECK_METHOD)
            self.assertEqual({u for _, u in calls}, {'https://vendor.example/old'})
        finally:
            os.environ.pop('SEO_ROOT', None)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_subtopic_gaps_are_cluster_specific_whole_phrases(self):
        from seo import content
        cluster = [content.prose_tokens([(t, [(t, False)])]) for t in [
            'Khu vực trung tâm có vùng phát thải thấp. Kết luận ngắn.',
            'Người đi xe nên biết vùng phát thải thấp. Kết luận ngắn.',
            'Vùng phát thải thấp áp dụng theo giai đoạn. Kết luận ngắn.']]
        cited = content.prose_tokens([('Nguồn: Sở Xây dựng Hà Nội, truy cập ngày 1/10', [('Nguồn', False)])])
        self.assertEqual(cited, [])
        found = dict(content.cluster_subtopics(cluster, ['đi xe máy ở hoàn kiếm'], lambda a, b: 0.05,
                                               widespread=frozenset({('kết', 'luận')})))
        self.assertEqual(found, {'vùng phát thải thấp': 3})

    def test_hosts_answering_404_to_everything_are_not_dead_links(self):
        status = {f'https://help.example/{i}': {'kind': 'external', 'status': 404} for i in range(6)}
        status.update({f'https://ok.example/{i}': {'kind': 'external', 'status': 404 if i == 0 else 200} for i in range(6)})
        self.assertEqual(linking.suspicious_hosts(status), {'help.example'})


class FetcherTest(unittest.TestCase):
    def cfg(self):
        return {'site_url': SITE, 'allowed_hosts': ['blog.rentbikehanoi.com'], 'user_agent': 'test',
                'http': {'min_interval_seconds': 0, 'retries': 3}}

    def test_read_only_and_single_host(self):
        f = net.Fetcher(self.cfg(), transport=lambda *a: (200, {}, b'ok'), sleep=lambda s: None)
        with self.assertRaises(ValueError):
            f.fetch(SITE + '/', method='POST')
        with self.assertRaises(ValueError):
            f.fetch('https://rentbikehanoi.com/')
        self.assertEqual(f.fetch('https://example.org/', internal_only=False).status, 200)

    def test_retry_and_cross_host_redirect(self):
        seq = [(503, {}, b''), (200, {}, b'ok')]
        f = net.Fetcher(self.cfg(), transport=lambda *a: seq.pop(0), sleep=lambda s: None)
        self.assertEqual(f.fetch(SITE + '/').status, 200)
        f2 = net.Fetcher(self.cfg(), transport=lambda *a: (301, {'location': 'https://evil.example/'}, b''),
                         sleep=lambda s: None)
        resp = f2.fetch(SITE + '/')
        self.assertEqual(resp.status, 301)
        self.assertEqual(resp.error, 'cross-host redirect not followed')


class ParserAndAnchorTest(unittest.TestCase):
    def test_blocks_mark_linked_text_and_jsonld_errors(self):
        p = htmlparse.parse('<p>Đọc <a href="/a">bài cũ</a> rồi kiểm tra phanh xe.</p>'
                            '<script type="application/ld+json">{bad json</script>')
        segs = htmlparse.block_texts(p)[0][1]
        self.assertIn(('bài cũ', True), segs)
        nodes, errors, _ = htmlparse.jsonld_nodes(p)
        self.assertTrue(errors and not nodes)

    def test_find_anchor_vietnamese_plain_text_only(self):
        blocks = [('x', [('Trước khi đi, hãy ', False), ('kiểm tra phanh', True),
                         (' rồi chụp ảnh hiện trạng xe máy ở bãi.', False)])]
        title = 'Chụp ảnh hiện trạng xe máy khi nhận xe thuê'
        anchor, context, score = linking.find_anchor(blocks, ['hiện', 'trạng', 'chụp', 'ảnh'], lambda t: 2.0,
                                                     title_tokens=title.split())
        self.assertEqual(anchor, 'chụp ảnh hiện trạng xe máy')
        self.assertIn('chụp ảnh hiện trạng xe máy ở bãi', context)
        none = linking.find_anchor(blocks, ['phanh', 'kiểm'], lambda t: 2.0,
                                   title_tokens='Kiểm tra phanh trước khi thuê'.split())
        self.assertIsNone(none[0])  # only occurs inside an existing link

    def test_find_anchor_only_uses_phrases_that_name_the_target(self):
        blocks = [('x', [('Xe số 50cc dễ dắt trong ngõ nhỏ.', False)])]
        title = 'Xe ga 50cc có phù hợp với người thấp không?'.split()
        self.assertIsNone(linking.find_anchor(blocks, ['ga', '50cc', 'thấp'], lambda t: 2.0, title_tokens=title)[0])
        cited = [('Honda Việt Nam, truy cập ngày 16/10/2026', [('Honda Việt Nam, truy cập ngày 16/10/2026', False)])]
        self.assertIsNone(linking.find_anchor(cited, ['honda', 'việt'], lambda t: 2.0,
                                              title_tokens='Honda Việt Nam có những mẫu xe nào'.split())[0])

    def test_find_anchor_specificity_and_compounds(self):
        blocks = [('x', [('Bạn có thể chụp ảnh hiện trạng xe máy trước khi nhận.', False)])]
        terms = ['chụp', 'ảnh', 'hiện', 'trạng', 'xe']
        idf = lambda t: 0.5 if t in ('xe', 'máy') else 2.0  # noqa: E731 - "xe" is generic site-wide
        title = 'Chụp ảnh hiện trạng xe khi nhận'.split()
        plain = linking.find_anchor(blocks, terms, idf, title_tokens=title)
        self.assertEqual(plain[0], 'chụp ảnh hiện trạng xe')
        aware = linking.find_anchor(blocks, terms, idf, title_tokens=title,
                                    is_compound=lambda a, b: (a, b) == ('xe', 'máy'))
        self.assertEqual(aware[0], 'chụp ảnh hiện trạng')  # never "… xe|máy"
        counts = linking.title_ngram_counts(['Chụp ảnh hiện trạng xe khi nhận'] * 4)
        self.assertIsNone(linking.find_anchor(blocks, terms, idf, title_tokens=title,
                                              title_df=counts, max_titles=3)[0])  # shared by 4 titles
        place = [('x', [('Gần Hàng Mã có bãi gửi xe.', False)])]
        hang_ma = 'Đi xe máy quanh Hàng Mã và Đồng Xuân'.split()
        self.assertEqual(linking.find_anchor(place, ['mã', 'hàng', 'xuân'], lambda t: 2.0, title_tokens=hang_ma)[0],
                         'Hàng Mã')


class FakeWPForFixes:
    def __init__(self, raw, modified='2026-10-16T10:00:00'):
        self.raw = raw
        self.modified = modified
        self.writes = []

    def public_post(self, post_id):
        return {'id': post_id, 'status': 'publish', 'modified_gmt': self.modified,
                'link': SITE + '/excel-201-a/', 'content': {'rendered': self.raw}}

    def raw_post(self, post_id):
        return {'id': post_id, 'status': 'publish', 'modified_gmt': self.modified, 'slug': 'excel-201-a',
                'link': SITE + '/excel-201-a/', 'content': {'raw': self.raw}}

    def update_content(self, post_id, content):
        self.writes.append(content)
        self.raw = content
        self.modified = '2026-10-20T00:00:00'
        return {'id': post_id}


class FixPipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ['SEO_ROOT'] = self.tmp
        root = pathlib.Path(self.tmp)
        (root / 'data/seo').mkdir(parents=True)
        (root / 'posts').mkdir()
        (root / 'data/posts-index.jsonl').write_text(json.dumps({'type': 'post', 'id': 202, 'url': SITE + '/excel-202-b/'}) + '\n')
        (root / 'posts/0201.md').write_text('---\nmatrix_id: 201\n---\n\n## Mục\n\nHãy chụp ảnh hiện trạng xe trước khi nhận.\n')
        self.cfg = common.load_config()
        self.raw = ('<!-- wp-aiwriter:matrix_id=201;sha256=x -->\n<h2>Chụp ảnh hiện trạng</h2>'
                    '<p>Hãy chụp ảnh hiện trạng xe trước khi nhận.</p>')
        self.fix = {'id': 'FIX-1', 'type': 'insert_internal_link', 'post_id': 201,
                    'target_url': SITE + '/excel-202-b/', 'anchor_text': 'chụp ảnh hiện trạng xe',
                    'expected_modified_gmt': '2026-10-16T10:00:00', 'approved_by': 'owner', 'approved_at': '2026-10-17',
                    'status': 'approved'}

    def tearDown(self):
        os.environ.pop('SEO_ROOT', None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_fixes(self, items):
        (pathlib.Path(self.tmp) / 'data/seo/approved-fixes.json').write_text(json.dumps({'fixes': items}))

    def test_insert_link_skips_headings_and_existing_links(self):
        out = fixes.insert_link(self.raw, 'chụp ảnh hiện trạng xe', SITE + '/excel-202-b/')
        self.assertIn('<a href="https://blog.rentbikehanoi.com/excel-202-b/">chụp ảnh hiện trạng xe</a>', out)
        self.assertIn('<h2>Chụp ảnh hiện trạng</h2>', out)
        with self.assertRaises(ValueError):
            fixes.insert_link('<p><a href="/x">chụp ảnh hiện trạng xe</a></p>', 'chụp ảnh hiện trạng xe', SITE + '/y/')
        with self.assertRaises(ValueError):
            fixes.insert_link('<p>chụp ảnh hiện trạng xe, chụp ảnh hiện trạng xe</p>', 'chụp ảnh hiện trạng xe', SITE + '/y/')

    def test_validate_never_writes_and_flags_problems(self):
        wp = FakeWPForFixes(self.raw)
        self.write_fixes([self.fix, {**self.fix, 'id': 'FIX-2', 'approved_by': ''},
                          {**self.fix, 'id': 'FIX-3', 'target_url': 'https://rentbikehanoi.com/x'},
                          {**self.fix, 'id': 'FIX-4', 'expected_modified_gmt': 'old'}])
        results = {r['id']: r for r in fixes.validate(self.cfg, wp)}
        self.assertEqual(results['FIX-1']['status'], 'VALID')
        self.assertEqual(results['FIX-2']['status'], 'INVALID')
        self.assertEqual(results['FIX-3']['status'], 'INVALID')
        self.assertEqual(results['FIX-4']['status'], 'INVALID')
        self.assertEqual(wp.writes, [])

    def test_apply_requires_confirmation_then_backs_up_verifies_and_rolls_back(self):
        wp = FakeWPForFixes(self.raw)
        self.write_fixes([self.fix])
        with self.assertRaises(RuntimeError):
            fixes.apply(self.cfg, wp, confirm=False)
        self.assertEqual(wp.writes, [])
        results = fixes.apply(self.cfg, wp, confirm=True)
        self.assertTrue(results[0]['applied'])
        self.assertEqual(len(wp.writes), 1)
        applied = common.read_json(pathlib.Path(self.tmp) / 'data/seo/applied-fixes.json')
        entry = applied['fixes']['FIX-1']
        self.assertEqual(entry['phase'], 'VERIFIED')
        backup = common.read_json(pathlib.Path(self.tmp) / entry['backup'])
        self.assertEqual(backup['content_raw_before'], self.raw)
        md = (pathlib.Path(self.tmp) / 'posts/0201.md').read_text()
        self.assertIn('[chụp ảnh hiện trạng xe](https://blog.rentbikehanoi.com/excel-202-b/)', md)
        again = fixes.apply(self.cfg, wp, confirm=True)
        self.assertFalse(again[0]['applied'])  # never applied twice
        fixes.rollback(self.cfg, wp, 'FIX-1', confirm=True)
        self.assertEqual(wp.raw, self.raw)

    def test_rollback_refuses_when_post_edited_later(self):
        wp = FakeWPForFixes(self.raw)
        self.write_fixes([self.fix])
        fixes.apply(self.cfg, wp, confirm=True)
        wp.modified = '2026-10-25T00:00:00'
        with self.assertRaises(RuntimeError):
            fixes.rollback(self.cfg, wp, 'FIX-1', confirm=True)


if __name__ == '__main__':
    unittest.main()
