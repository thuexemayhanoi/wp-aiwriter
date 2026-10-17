"""SEO audit / internal link matrix / SEO protection: hermetic tests (no internet, no credentials)."""
import http.server
import importlib
import json
import pathlib
import sys
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sc = importlib.import_module('seo_common')
audit = importlib.import_module('seo_audit')
links = importlib.import_module('link_matrix')
prot = importlib.import_module('seo_protection')

HOST = 'https://blog.example.test'


def art(i, title, category, body, words=1500):
    return {'id': i, 'title': title, 'category': category, 'body': body, 'words': words, 'hash': f'hash{i}'}


def ledger_entry(i, slug=None, wp_id=None, category_id=7, source_hash=None, title='t'):
    slug = slug or f'post-{i}'
    return {'phase': 'VERIFIED', 'status': 'publish', 'slug': slug, 'wp_id': wp_id or 1000 + i,
            'url': f'{HOST}/{slug}/', 'category_id': category_id, 'source_hash': source_hash or f'hash{i}', 'title': title}


class CommonTests(unittest.TestCase):
    def test_norm_url_ignores_scheme_query_fragment_and_adds_slash(self):
        self.assertEqual(sc.norm_url('http://Blog.Example.test/a?utm=1#x'), sc.norm_url('https://blog.example.test/a/'))
        self.assertTrue(sc.norm_url('https://x.test/file.xml').endswith('/file.xml'))

    def test_markdown_links_skip_images_and_headings_levels(self):
        body = '## A\n\n[one](https://a.test/x) ![img](https://a.test/i.png) [two](https://b.test/y)\n\n### B'
        self.assertEqual(sc.md_links(body), [('one', 'https://a.test/x'), ('two', 'https://b.test/y')])
        self.assertEqual(sc.md_headings(body), [('##', 'A'), ('###', 'B')])

    def test_parse_page_extracts_seo_signals(self):
        page = '''<html lang="vi"><head><title> Tiêu đề  bài </title>
        <meta name="description" content="Mô tả"><meta name="robots" content="NOINDEX, follow">
        <meta name="viewport" content="width=device-width"><meta property="og:title" content="OG">
        <link rel="canonical" href="https://blog.example.test/a/">
        <script type="application/ld+json">{"@graph":[{"@type":"Article"},{"@type":["BreadcrumbList","Thing"]}]}</script>
        <script>var ignored = 1;</script></head><body><h1>Chính</h1><h2>Hai</h2>
        <img src="a.png" alt="ok"><img src="b.png"><a href="/x" rel="nofollow">x</a><p>một hai ba</p></body></html>'''
        info = sc.parse_page(page)
        self.assertEqual((info['title'], info['description'], info['lang']), ('Tiêu đề bài', 'Mô tả', 'vi'))
        self.assertEqual(info['canonical'], 'https://blog.example.test/a/')
        self.assertIn('noindex', info['robots'])
        self.assertEqual((info['h1_count'], info['h2_count'], info['h1_text']), (1, 1, 'Chính'))
        self.assertEqual((info['images_total'], info['images_missing_alt']), (2, 1))
        self.assertEqual(info['jsonld_types'], ['Article', 'BreadcrumbList', 'Thing'])
        self.assertEqual(info['word_count'], 6)  # "Chính Hai x một hai ba"; head and scripts are excluded

    def test_invalid_json_ld_is_reported(self):
        info = sc.parse_page('<html><head><script type="application/ld+json">{oops</script></head></html>')
        self.assertEqual(info['jsonld_types'], ['INVALID_JSON_LD'])

    def test_tfidf_ranks_related_text_above_unrelated(self):
        vectors = sc.tfidf_vectors({1: 'xe ga cốp rộng người đi làm', 2: 'xe ga cốp rộng mang laptop', 3: 'bản đồ ngoại tuyến mạng yếu'})
        self.assertGreater(sc.cosine(vectors[1], vectors[2]), sc.cosine(vectors[1], vectors[3]))


class LinkMatrixTests(unittest.TestCase):
    def setUp(self):
        site = HOST
        self.ready = [
            art(1, 'Xe ga cốp rộng cho người đi làm', 'Dịch vụ > Xe ga', f'## A\n\nXem [bài hai]({site}/post-2/) và [ngoài](https://x.test/).'),
            art(2, 'Xe ga cốp rộng mang laptop', 'Dịch vụ > Xe ga', f'## A\n\n[về bài một]({site}/post-1/) [cũ]({site}/legacy-post/)'),
            art(3, 'Bản đồ ngoại tuyến khi mạng yếu', 'Cẩm nang > Ứng dụng', '## A\n\nKhông có liên kết.'),
            art(4, 'Xe ga cốp rộng đi phố đông', 'Dịch vụ > Xe ga', f'## A\n\n[tự link]({site}/post-4/)')]
        self.ledger = {str(i): ledger_entry(i) for i in (1, 2, 3, 4)}
        self.graph = links.build_graph(self.ready, self.ledger, HOST)
        self.analysis = links.analyse(self.graph)

    def test_edges_unmapped_self_and_external(self):
        self.assertEqual(set(self.graph['edges']), {(1, 2), (2, 1)})
        self.assertEqual(self.graph['unmapped'], {2: [f'{HOST}/legacy-post/']})
        self.assertEqual(self.graph['self_links'], {4: 1})
        self.assertEqual(self.graph['external']['x.test'], 1)

    def test_orphans_dead_ends_reciprocity_and_clusters(self):
        nodes = self.graph['nodes']
        self.assertTrue(nodes[3]['orphan'] and nodes[3]['dead_end'] and nodes[4]['orphan'])
        self.assertFalse(nodes[1]['orphan'])
        self.assertEqual(self.analysis['reciprocal'], [(1, 2)])
        self.assertEqual(self.analysis['summary']['orphans'], 2)
        cluster = next(c for c in self.analysis['clusters'] if c['category'] == 'Dịch vụ > Xe ga')
        self.assertEqual(cluster['internal_edges'], 2)

    def test_pagerank_is_a_distribution_with_dangling_nodes(self):
        rank = links.pagerank(self.graph['nodes'], self.graph['edges'])
        self.assertAlmostEqual(sum(rank.values()), 1.0, places=6)

    def test_proposals_prefer_related_orphans_and_skip_existing_links(self):
        plan = links.propose(self.graph, self.ready)
        pairs = {(p['source_id'], p['target_id']) for p in plan}
        self.assertNotIn((1, 2), pairs)               # already linked
        self.assertIn((1, 4), pairs)                  # related and an orphan
        self.assertNotIn((1, 3), pairs)               # unrelated cluster/topic
        top = next(p for p in plan if (p['source_id'], p['target_id']) == (1, 4))
        self.assertIn('target is an orphan', top['reasons'])
        self.assertEqual(top['priority'], 'high')

    def test_markdown_report_mentions_policy(self):
        text = links.render_markdown(self.graph, self.analysis, links.propose(self.graph, self.ready))
        self.assertIn('Policy compliance', text)
        self.assertIn('Orphans', text)


class AuditSourceTests(unittest.TestCase):
    def test_source_findings(self):
        body = ('## Trả lời nhanh\n\n' + 'từ ' * 40 + '\n\n## B\n\nhttp://insecure.test không phải link markdown\n\n'
                f'[x](http://insecure.test/a) [y]({HOST}/missing/)')
        ready = [art(1, 'T' * 80, 'C > D', body, words=900),
                 art(2, 'Xe ga cốp rộng cho người đi làm', 'C > D', '## A\n\n' + 'từ ' * 40),
                 art(3, 'Xe ga cốp rộng cho người đi làm', 'C > D', '## A\n\n' + 'từ ' * 40)]
        ledger = {'1': ledger_entry(1)}
        pages, site = audit.audit_sources({}, ready, [{'file': 'posts/0009.md', 'reason': 'bad'}], ledger, HOST)
        checks = {f['check'] for f in pages[0]['findings']}
        self.assertTrue({'thin_content', 'title_long', 'few_sections', 'insecure_external_link', 'link_not_in_ledger'} <= checks)
        site_checks = {f['check'] for f in site}
        self.assertTrue({'qa_error', 'duplicate_title', 'title_overlap'} <= site_checks)
        pages_live, _ = audit.audit_sources({}, ready, [], ledger, HOST, known_urls=set())
        self.assertIn('link_unpublished', {f['check'] for f in pages_live[0]['findings']})
        self.assertLess(pages[0]['score'], 100)

    def test_robots_parser(self):
        info = audit.robots_info('User-agent: *\nDisallow: /\nSitemap: https://x.test/s.xml\n')
        self.assertTrue(info['disallow_all'])
        self.assertEqual(info['sitemaps'], ['https://x.test/s.xml'])
        self.assertFalse(audit.robots_info('User-agent: bot\nDisallow: /\n')['disallow_all'])


class ProtectionLogicTests(unittest.TestCase):
    def setUp(self):
        self.topics = {1: {'category': 'A > B'}, 2: {'category': 'A > B'}}
        self.ready = [art(1, 'Một', 'A > B', 'x'), art(2, 'Hai', 'A > B', 'y')]
        for a in self.ready:
            a['slug_hint'] = f'post-{a["id"]}'
        self._orig_slug = prot.engine_slug
        prot.engine_slug = lambda article: f'post-{article["id"]}'
        self.ledger = {'1': ledger_entry(1, title='Một'), '2': ledger_entry(2, title='Hai')}

    def tearDown(self):
        prot.engine_slug = self._orig_slug

    def codes(self, findings):
        return {f['check'] for f in findings}

    def test_clean_repo_passes(self):
        self.assertEqual(prot.repo_guard(self.ledger, self.ready, self.topics), [])

    def test_edited_missing_duplicate_and_inconsistent_are_critical(self):
        self.ready[0]['hash'] = 'changed'
        self.ledger['2']['wp_id'] = self.ledger['1']['wp_id']
        self.ledger['2']['category_id'] = 99
        found = prot.repo_guard(self.ledger, self.ready[:1], self.topics)
        self.assertTrue({'published_source_edited', 'duplicate_wp_id', 'category_inconsistent',
                         'published_source_missing'} <= self.codes(found))
        self.assertTrue(all(f['severity'] == 'critical' for f in found))

    def test_baseline_is_joined_to_the_ledger_through_the_wordpress_id(self):
        # ledger_entry(1) has wp_id 1001; baseline keys are WordPress IDs, so '1' is an unrelated WP post.
        unrelated = {'entries': {'1': {'url': f'{HOST}/legacy-post/'}, '2': {'url': f'{HOST}/other-legacy/'}}}
        self.assertEqual(prot.repo_guard(self.ledger, self.ready, self.topics, unrelated), [])
        agreeing = {'entries': {'1001': {'url': f'{HOST}/post-1/'}}}
        self.assertEqual(prot.repo_guard(self.ledger, self.ready, self.topics, agreeing), [])
        moved = {'entries': {'1001': {'url': f'{HOST}/other/'}}}
        found = prot.repo_guard(self.ledger, self.ready, self.topics, moved)
        self.assertEqual([f['check'] for f in found], ['baseline_url_mismatch'])
        self.assertEqual(found[0]['id'], 1)

    def entry(self, **kw):
        base = {'type': 'post', 'url': f'{HOST}/a/', 'slug': 'a', 'title': 'A', 'categories': [7], 'http_status': 200,
                'final_url': f'{HOST}/a/', 'canonical': f'{HOST}/a/', 'robots': '', 'noindex': False, 'h1': 'A',
                'jsonld_types': ['Article'], 'content_sha256': 'h1', 'word_count': 1000, 'modified_gmt': '2026-01-01T00:00:00'}
        return {**base, **kw}

    def test_compare_detects_url_canonical_noindex_removed_and_new(self):
        baseline = {'entries': {'1': self.entry(), '2': self.entry(url=f'{HOST}/b/', slug='b'), '3': self.entry()},
                    'site_files': {'robots_sha256': 'r', 'sitemap_urls': 100, 'home_canonical': f'{HOST}/'}}
        live = {'1': self.entry(slug='renamed', canonical=f'{HOST}/else/', noindex=True, title='B', categories=[8],
                                jsonld_types=[], content_sha256='h2', word_count=500, modified_gmt='2026-02-01T00:00:00'),
                '2': self.entry(url=f'{HOST}/b/', slug='b', http_status=404),
                '9': self.entry()}
        site = {'robots_sha256': 'changed', 'sitemap_urls': 10, 'home_canonical': f'{HOST}/', 'home_status': 200}
        found = prot.compare(baseline, live, site)
        got = self.codes(found)
        self.assertTrue({'slug_changed', 'canonical_changed', 'noindex_added', 'title_changed', 'category_changed',
                         'structured_data_lost', 'content_changed', 'http_status', 'removed', 'unbaselined',
                         'robots_changed', 'sitemap_shrunk'} <= got)
        self.assertTrue(prot.blocking(found))

    def test_clean_state_and_dynamic_content_do_not_block(self):
        baseline = {'entries': {'1': self.entry()}, 'site_files': {'sitemap_urls': 5, 'home_canonical': f'{HOST}/'}}
        live = {'1': self.entry(content_sha256='widget-changed')}
        site = {'sitemap_urls': 5, 'home_canonical': f'{HOST}/', 'home_status': 200}
        found = prot.compare(baseline, live, site)
        self.assertEqual(self.codes(found), {'dynamic_content_changed'})
        self.assertFalse(prot.blocking(found))

    def test_allowlist_suppresses_only_approved_field(self):
        baseline = {'entries': {'1': self.entry()}, 'site_files': {}}
        live = {'1': self.entry(title='Mới', slug='mới')}
        allow = {'records': [{'id': 1, 'fields': ['title_changed'], 'reason': 'approved'}]}
        got = self.codes(prot.compare(baseline, live, {'home_status': 200}, allow))
        self.assertNotIn('title_changed', got)
        self.assertIn('slug_changed', got)

    def test_baseline_is_append_only_and_accept_needs_reason(self):
        first, _, added, replaced = prot.merge_baseline(None, {'1': self.entry()}, {'sitemap_urls': 1}, stamp='t1')
        self.assertEqual((added, replaced), (['1'], []))
        changed = {'1': self.entry(title='Khác'), '2': self.entry()}
        second, _, added, replaced = prot.merge_baseline(first, changed, {'sitemap_urls': 9}, stamp='t2')
        self.assertEqual((added, replaced), (['2'], []))
        self.assertEqual(second['entries']['1']['title'], 'A')            # untouched
        self.assertEqual(second['site_files'], {'sitemap_urls': 1})       # untouched
        with self.assertRaises(ValueError):
            prot.merge_baseline(second, changed, {}, accept=['1'])
        third, records, _, replaced = prot.merge_baseline(second, changed, {}, accept=['1'], reason='approved', stamp='t3')
        self.assertEqual(replaced, ['1'])
        self.assertEqual(third['entries']['1']['title'], 'Khác')
        self.assertEqual(records[0]['reason'], 'approved')


# ---------------------------------------------------------------- fake WordPress site ------------------------------
class FakeSite:
    def __init__(self):
        self.posts = []
        self.noindex = set()
        self.canonical_override = {}
        self.sitemap_extra = []

    def page(self, post):
        slug = post['slug']
        canonical = self.canonical_override.get(slug, post['link'])
        robots = '<meta name="robots" content="noindex">' if slug in self.noindex else ''
        ld = '<script type="application/ld+json">{"@type":["Article","BreadcrumbList"]}</script>'
        return (f'<html lang="vi"><head><title>{post["title"]["rendered"]}</title><meta name="description" content="{"d" * 90}">'
                f'<meta name="viewport" content="width=device-width"><meta property="og:title" content="x">{robots}'
                f'<link rel="canonical" href="{canonical}">{ld}</head><body><h1>{post["title"]["rendered"]}</h1>'
                f'<img src="a.png" alt="a"><a href="/gone/">broken</a><a href="{self.base}/">home</a><p>nội dung</p></body></html>')


def make_server(site):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, body, ctype='text/html; charset=utf-8', headers=None):
            raw = body.encode()
            self.send_response(status)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(raw)))
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(raw)

        def do_GET(self):
            path, _, query = self.path.partition('?')
            params = dict(p.split('=', 1) for p in query.split('&') if '=' in p)
            if path == '/wp-json/wp/v2/posts':
                per, page = int(params.get('per_page', 100)), int(params.get('page', 1))
                total = max(1, -(-len(site.posts) // per))
                if page > total:
                    return self.send(400, '{"code":"rest_post_invalid_page_number"}', 'application/json')
                chunk = site.posts[(page - 1) * per: page * per]
                return self.send(200, json.dumps(chunk), 'application/json', {'X-WP-TotalPages': str(total)})
            if path in ('/wp-json/wp/v2/pages', '/wp-json/wp/v2/categories'):
                return self.send(200, '[]', 'application/json', {'X-WP-TotalPages': '1'})
            if path == '/robots.txt':
                return self.send(200, f'User-agent: *\nDisallow: /wp-admin/\nSitemap: {site.base}/sitemap_index.xml\n', 'text/plain')
            if path == '/sitemap_index.xml':
                return self.send(200, f'<sitemapindex><sitemap><loc>{site.base}/post-sitemap.xml</loc></sitemap></sitemapindex>', 'application/xml')
            if path == '/post-sitemap.xml':
                locs = ''.join(f'<url><loc>{p["link"]}</loc></url>' for p in site.posts[:-1]) + ''.join(site.sitemap_extra)
                return self.send(200, f'<urlset>{locs}</urlset>', 'application/xml')
            if path == '/':
                return self.send(200, '<html><head><title>Home</title><link rel="canonical" href="/"></head><body></body></html>')
            for post in site.posts:
                if path.strip('/') == post['slug']:
                    return self.send(200, site.page(post))
            return self.send(404, 'not found')

        def do_HEAD(self):
            self.do_GET()

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    site.base = f'http://127.0.0.1:{server.server_address[1]}'
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


class LiveModeTests(unittest.TestCase):
    def setUp(self):
        self.site = FakeSite()
        self.server = make_server(self.site)
        base = self.site.base
        self.site.posts = [{'id': 10 + i, 'slug': f'p{i}', 'link': f'{base}/p{i}/', 'status': 'publish', 'categories': [7],
                            'title': {'rendered': f'Bài {i}'}, 'modified_gmt': '2026-01-01T00:00:00',
                            'content': {'rendered': f'<p>Nội dung bài {i}</p>'}} for i in range(1, 4)]
        self.ledger = {'1': {'phase': 'VERIFIED', 'status': 'publish', 'wp_id': 11, 'slug': 'p1', 'url': f'{base}/p1/',
                             'category_id': 7, 'title': 'Bài 1'}}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_wp_list_paginates(self):
        rows = sc.wp_list('posts', 'id,link', self.site.base, per_page=2)
        self.assertEqual([r['id'] for r in rows], [11, 12, 13])

    def test_fetch_failure_is_a_status_zero_response_not_an_exception(self):
        reply = sc.http_get('http://127.0.0.1:9/', retries=0, timeout=2)
        self.assertEqual(reply.status, 0)

    def test_live_audit_flags_real_problems(self):
        self.site.noindex.add('p2')
        self.site.canonical_override['p3'] = 'https://elsewhere.test/p3/'
        pages, site_findings, meta = audit.audit_live(self.ledger, self.site.base, workers=2, with_links=True)
        by_url = {p['url'].rstrip('/').rsplit('/', 1)[-1]: {f['check'] for f in p['findings']} for p in pages}
        self.assertIn('noindex', by_url['p2'])
        self.assertIn('canonical_mismatch', by_url['p3'])
        self.assertNotIn('noindex', by_url['p1'])
        checks = {f['check'] for f in site_findings}
        self.assertIn('sitemap_coverage', checks)       # the last post is not in the fake sitemap
        self.assertIn('broken_link', checks)            # /gone/ returns 404
        self.assertEqual(meta['live_posts'], 3)
        self.assertEqual(meta['sitemap_urls'], 2)

    def test_ledger_vs_live_detects_url_and_missing_drift(self):
        self.site.posts[0]['slug'] = 'p1-renamed'
        self.site.posts[0]['link'] = f'{self.site.base}/p1-renamed/'
        live = sc.wp_list('posts', 'id,link,slug,categories', self.site.base)
        got = {f['check'] for f in audit.ledger_vs_live(self.ledger, live)}
        self.assertTrue({'url_changed', 'slug_changed'} <= got)
        got = {f['check'] for f in audit.ledger_vs_live(self.ledger, [])}
        self.assertEqual(got, {'missing_live'})

    def test_protection_baseline_then_clean_then_drift(self):
        entries, files = prot.live_snapshot(self.site.base, workers=2)
        baseline, _, added, _ = prot.merge_baseline(None, entries, files)
        self.assertEqual(len(added), 3)
        self.assertEqual(prot.compare(baseline, *prot.live_snapshot(self.site.base, workers=2)), [])
        self.site.noindex.add('p1')
        self.site.canonical_override['p2'] = 'https://elsewhere.test/p2/'
        del self.site.posts[2]                                     # p3 disappears from the public site
        found = prot.compare(baseline, *prot.live_snapshot(self.site.base, workers=2))
        got = {(f['check'], f['id']) for f in found if f['severity'] == 'critical'}
        self.assertIn(('noindex_added', 11), got)
        self.assertIn(('canonical_changed', 12), got)
        self.assertIn(('removed', 13), got)


class BlockedSiteTests(unittest.TestCase):
    def test_unreadable_site_is_not_baselined_or_reported_as_mass_removal(self):
        blocked = {str(i): {'http_status': 403} for i in range(10)}
        self.assertTrue(prot.unreadable(blocked))
        mostly_ok = {str(i): {'http_status': 200 if i else 404} for i in range(10)}
        self.assertFalse(prot.unreadable(mostly_ok))
        ok, skipped = prot.split_healthy(mostly_ok)
        self.assertEqual((len(ok), skipped), (9, ['0']))
        self.assertTrue(prot.unreadable({}))


class RealRepoSmokeTests(unittest.TestCase):
    """Run the tools on the real repository data: they must not crash (findings are reported, not asserted)."""

    def test_tools_run_on_repository_data(self):
        topics, ready, errors = sc.load_sources()
        ledger = sc.load_ledger()
        graph = links.build_graph(ready, ledger)
        analysis = links.analyse(graph)
        self.assertEqual(analysis['summary']['posts'], len(ready))
        plan = links.propose(graph, ready, per_source=1)
        self.assertTrue(all(p['source_id'] != p['target_id'] for p in plan))
        pages, site = audit.audit_sources(topics, ready, errors, ledger)
        self.assertEqual(len(pages), len(ready))
        self.assertIsInstance(prot.repo_guard(ledger, ready, topics), list)


if __name__ == '__main__':
    unittest.main()
