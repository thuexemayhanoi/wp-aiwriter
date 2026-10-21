"""English pipeline safety: QA gates, duplicate detection, publisher gating; no network, no WordPress writes."""
import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('en_engine', ROOT / 'scripts/en_engine.py')
en = importlib.util.module_from_spec(spec)
spec.loader.exec_module(en)

POLICY = json.loads((ROOT / 'en/publication-policy.json').read_text(encoding='utf-8'))
BUSINESS = json.loads((ROOT / 'en/business.json').read_text(encoding='utf-8'))
TOPICS = en.load_topics(POLICY)

SENTENCES = [
    'Hanoi traffic looks chaotic from the pavement, but it follows a rhythm that most visitors pick up within a day.',
    'Riders move at a steady pace, keep to the right, and signal with a short horn tap before overtaking.',
    'A rental scooter should feel light at walking speed and stable when you brake on a wet patch of road.',
    'Check the mirrors, the horn and both brakes before you leave the shop, and photograph every scratch you find.',
    'Fuel stations are everywhere in the city, and the attendant fills the tank for you while you stay seated.',
    'Parking attendants hand you a numbered ticket and expect the same ticket back when you collect the bike.',
]


def para(n, m):
    rotated = SENTENCES[m % 6:] + SENTENCES[:m % 6]
    return f'Point {n}.{m}: ' + ' '.join(rotated)


def section(n):
    return para(n, 1) + '\n\n' + para(n, 2)


PARAGRAPH = para(0, 0)


def article(i=2, **overrides):
    topic = TOPICS[i]
    # Add unique paragraphs so the normal test manuscript meets the new limit.
    # The old-length fixture tests the immutable published exception.
    legacy_short = overrides.pop('legacy_short', False)
    expansion = '' if legacy_short else (
        f"{para(6, 1)}\n\n{para(7, 2)}\n\n"
        f"{para(8, 3)}\n\n{para(9, 4)}\n\n"
    )
    body = (f"{para(0, 1)}\n\n{para(0, 2)}\n\n## What the two scooters are\n\n{section(1)}\n\n## Comfort and storage\n\n{section(2)}\n\n"
            f"## Fuel and running costs\n\n{section(3)}\n\n## Which one to choose\n\n{section(4)}\n\n{expansion}"
            f"Read our [rental guide](https://blog.rentbikehanoi.com/en/rental-guide/) and the [price list](https://blog.rentbikehanoi.com/en/prices/).\n\n"
            f"## FAQ\n\n### Is the Vision enough for two people?\n\n{para(5, 1)}\n\n## Sources\n\n- [Honda Vietnam](https://www.honda.com.vn/)\n")
    meta = {'en_id': str(topic['id']), 'title': topic['title'], 'slug': topic['slug'], 'category_id': str(topic['category_id']),
            'description': 'A practical comparison of the Honda Vision and the Air Blade for a Hanoi rental: comfort, storage, fuel use and which rider each one suits.',
            'ready': 'true', **overrides.pop('meta', {})}
    body = overrides.pop('body', body)
    text = '---\n' + '\n'.join(f'{k}: {v}' for k, v in meta.items()) + '\n---\n' + body
    return meta, text


def write(tmp, i, text):
    path = pathlib.Path(tmp) / f'{i:04}.md'
    path.write_text(text, encoding='utf-8')
    return path


class Qa(unittest.TestCase):
    def read(self, i, text):
        with tempfile.TemporaryDirectory() as tmp:
            return en.read_article(write(tmp, i, text), TOPICS, BUSINESS, POLICY)

    def test_1600_word_gate_rejects_new_and_edited_articles_but_preserves_verified_legacy(self):
        meta, content = article(legacy_short=True)
        _, body = en.front_matter(content)
        word_count = len(en.words_of(en.engine.visible(en.engine.markdown_to_html(body))))
        self.assertGreaterEqual(word_count, 1000)
        self.assertLess(word_count, 1600)
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            path = write(root, 2, content)
            ledger_path = root / 'state.json'
            with patch.object(en, 'STATE_PATH', ledger_path):
                with self.assertRaisesRegex(ValueError, 'need 1600 to 5000'):
                    en.read_article(path, TOPICS, BUSINESS, POLICY)
                ledger_path.write_text(json.dumps({'posts': {'2': {
                    'phase': 'VERIFIED', 'status': 'publish',
                    'source_hash': en.seo_common.sha256_text(body),
                    'title': meta['title'], 'slug': meta['slug'],
                    'category_id': int(meta['category_id']),
                }}}), encoding='utf-8')
                self.assertTrue(en.read_article(path, TOPICS, BUSINESS, POLICY)['ready'])
                path.write_text(content + '\nAn additional revised sentence.', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'need 1600 to 5000'):
                    en.read_article(path, TOPICS, BUSINESS, POLICY)
                state = json.loads(ledger_path.read_text(encoding='utf-8'))
                state['posts']['2']['phase'] = 'DRAFT_CREATED'
                ledger_path.write_text(json.dumps(state), encoding='utf-8')
                path.write_text(content, encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'need 1600 to 5000'):
                    en.read_article(path, TOPICS, BUSINESS, POLICY)

    def test_1600_word_policy_cannot_be_weakened(self):
        self.assertEqual(POLICY['min_words'], 1600)
        invalid = copy.deepcopy(POLICY)
        invalid['min_words'] = 1000
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / 'policy.json'
            path.write_text(json.dumps(invalid), encoding='utf-8')
            with patch.object(en, 'POLICY_PATH', path):
                with self.assertRaisesRegex(ValueError, 'violates the pipeline safeguards'):
                    en.load_policy()

    def test_good_article_passes_with_score(self):
        _, text = article()
        result = self.read(2, text)
        self.assertTrue(result['ready'])
        self.assertGreaterEqual(result['score'], POLICY['min_score'])
        self.assertGreaterEqual(result['words'], 1000)

    def test_metadata_must_match_topics(self):
        meta, text = article()
        with self.assertRaisesRegex(ValueError, 'differs from en/topics.json'):
            self.read(2, text.replace(meta['slug'], 'another-slug'))
        with self.assertRaisesRegex(ValueError, 'en_id/filename'):
            self.read(3, text)

    def test_vietnamese_text_fails(self):
        _, text = article()
        text = text.replace('## Which one to choose', '## Lựa chọn\n\nThuê xe máy của chúng tôi với giá tốt và các dịch vụ được nhiều người chọn khi đến Hà Nội.\n\n## Which one to choose')
        with self.assertRaisesRegex(ValueError, 'Vietnamese text'):
            self.read(2, text)

    def test_other_business_phone_and_address_fail(self):
        _, text = article()
        with self.assertRaisesRegex(ValueError, 'forbidden business fragment'):
            self.read(2, text.replace('## FAQ', 'Call 0942 467 674 at 112 Nguyen Van Cu.\n\n## FAQ'))
        with self.assertRaisesRegex(ValueError, 'phone number that is not the business phone'):
            self.read(2, text.replace('## FAQ', 'Call 0912 345 678 for help.\n\n## FAQ'))
        result = self.read(2, text.replace('## FAQ', 'Call 0334 699 969 or +84 334 699 969.\n\n## FAQ'))
        self.assertTrue(result['ready'])

    def test_unverified_amounts_and_usd_fail(self):
        _, text = article()
        with self.assertRaisesRegex(ValueError, 'unverified VND amount: 250000'):
            self.read(2, text.replace('## FAQ', 'It costs VND 250,000 per day.\n\n## FAQ'))
        with self.assertRaisesRegex(ValueError, 'VND only'):
            self.read(2, text.replace('## FAQ', 'It costs about $8 per day.\n\n## FAQ'))
        result = self.read(2, text.replace('## FAQ', 'Automatic scooters cost VND 150,000 to 200,000 per day and 150k VND at the low end.\n\n## FAQ'))
        self.assertTrue(result['ready'])

    def test_internal_links_must_be_english(self):
        _, text = article()
        with self.assertRaisesRegex(ValueError, 'internal link outside /en/'):
            self.read(2, text.replace('## FAQ', 'See [prices](https://blog.rentbikehanoi.com/bang-gia/).\n\n## FAQ'))

    def test_legal_topic_needs_official_source_and_date(self):
        topic = TOPICS[1]
        meta, text = article(1, meta={'en_id': '1', 'title': topic['title'], 'slug': topic['slug'], 'category_id': str(topic['category_id'])})
        text = text.replace('- [Honda Vietnam](https://www.honda.com.vn/)', '- [A blog](https://example.com/blog)')
        with self.assertRaisesRegex(ValueError, 'official source'):
            self.read(1, text)
        text = text.replace('- [A blog](https://example.com/blog)', '- [Law 36/2024/QH15](https://thuvienphapluat.vn/van-ban/Giao-thong-Van-tai/Luat-Trat-tu-an-toan-giao-thong-duong-bo-2024-36-2024-QH15-543403.aspx)')
        with self.assertRaisesRegex(ValueError, 'effective date'):
            self.read(1, text)
        text = text.replace('## Sources', 'The law is effective from 1 January 2025.\n\n## Sources')
        self.assertTrue(self.read(1, text)['legal'])

    def test_structure_gates(self):
        _, text = article()
        with self.assertRaisesRegex(ValueError, 'words'):
            self.read(2, text.split('## Comfort and storage')[0] + '## A\n\nx\n\n## B\n\ny\n\n## C\n\nz')
        with self.assertRaisesRegex(ValueError, 'unsafe markup'):
            self.read(2, text.replace('## FAQ', '<script>alert(1)</script>\n\n## FAQ'))
        with self.assertRaisesRegex(ValueError, 'image without alt'):
            self.read(2, text.replace('## FAQ', '![](https://example.com/a.jpg)\n\n## FAQ'))

    def test_low_score_is_rejected(self):
        meta, text = article(meta={'description': ''})
        text = text.replace('## FAQ\n\n### Is the Vision enough for two people?\n\n' + para(5, 1) + '\n\n', '')
        text = text.replace('Read our [rental guide](https://blog.rentbikehanoi.com/en/rental-guide/) and the [price list](https://blog.rentbikehanoi.com/en/prices/).\n\n', '')
        with self.assertRaisesRegex(ValueError, 'QA score'):
            self.read(2, text)

    def test_amount_parser(self):
        self.assertEqual([a for a, _ in en.amounts_in('VND 150,000 and 1.000.000 VND and 150k VND and 2,000,000 dong')], [150000, 1000000, 150000, 2000000])
        self.assertEqual([a for a, _ in en.amounts_in('a deposit of VND 2–5 million and VND 150,000–200,000 per day')], [2000000, 5000000, 150000, 200000])
        self.assertEqual(en.amounts_in('the fine is VND 2–4 million for riding without a licence'), [(2000000, True), (4000000, True)])

    def test_fines_are_allowed_only_with_the_legal_gate(self):
        topic = TOPICS[1]
        meta, text = article(1, meta={'en_id': '1', 'title': topic['title'], 'slug': topic['slug'], 'category_id': str(topic['category_id'])})
        text = text.replace('## FAQ', 'Riding without a licence is fined VND 2–4 million, effective from 1 January 2025.\n\n## FAQ')
        text = text.replace('- [Honda Vietnam](https://www.honda.com.vn/)', '- [Decree 168/2024/ND-CP](https://thuvienphapluat.vn/van-ban/x.aspx)')
        self.assertTrue(self.read(1, text)['legal'])
        _, plain = article()
        with self.assertRaisesRegex(ValueError, 'unverified VND amount: 3000000'):
            self.read(2, plain.replace('## FAQ', 'A helmet costs VND 3 million here.\n\n## FAQ'))


class Duplicates(unittest.TestCase):
    def test_same_intent_and_near_duplicate(self):
        _, text2 = article(2)
        topic = TOPICS[29]
        _, text29 = article(29, meta={'en_id': '29', 'title': topic['title'], 'slug': topic['slug'], 'category_id': str(topic['category_id'])})
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, 2, text2)
            write(tmp, 29, text29)
            with patch.object(en, 'POSTS_DIR', pathlib.Path(tmp)):
                _, accepted, errors = en.load_articles(TOPICS, BUSINESS, POLICY)
        self.assertEqual([a['id'] for a in accepted], [2])
        self.assertTrue(any('duplicate' in e['reason'].lower() or 'intent' in e['reason'].lower() for e in errors))


class FakeRest:
    def __init__(self, status, register_http=200):
        self.status = status
        self.register_http = register_http
        self.calls = []

    def call(self, route, payload=None, method=None):
        self.calls.append((route, payload))
        if route == 'nh-vien/v1/status':
            return 200, copy.deepcopy(self.status)
        if route == 'nh-vien/v1/posts':
            if self.register_http == 200:
                self.status['public_en_posts'].append(payload['id'])
                return 200, {'saved': True}
            return self.register_http, {'code': 'nh_vien_invalid_posts'}
        raise AssertionError(route)


class FakeWP:
    def __init__(self):
        self.posts, self.calls = [], []

    def get(self, path, public=False):
        if path.startswith('users/me'):
            return {'id': 1}
        post_id = int(path.split('/')[1].split('?')[0])
        return next(p for p in self.posts if p['id'] == post_id)

    def all(self, kind, **params):
        return copy.deepcopy(self.posts)

    def request(self, path, payload=None, **kwargs):
        self.calls.append((path, payload))
        if path == 'posts':
            post = {**payload, 'id': len(self.posts) + 100, 'title': {'raw': payload['title']},
                    'content': {'raw': payload['content']}, 'link': en.WP_URL + '/' + payload['slug'] + '/'}
            self.posts.append(post)
            return post, {}
        post_id = int(path.split('/')[1])
        post = next(p for p in self.posts if p['id'] == post_id)
        post.update(payload)
        return post, {}


class FakeLedger:
    def __init__(self):
        self.data = {'posts': {}}

    def save(self):
        pass


def ready_articles():
    out = []
    for i in (2, 3):
        topic = TOPICS[i]
        _, text = article(i, meta={'en_id': str(i), 'title': topic['title'], 'slug': topic['slug'], 'category_id': str(topic['category_id'])})
        with tempfile.TemporaryDirectory() as tmp:
            out.append(en.read_article(write(tmp, i, text), TOPICS, BUSINESS, POLICY))
    return out


def report():
    return {'created': [], 'existing': [], 'duplicates': [], 'errors': []}


def live_status(categories=None):
    if categories is None:
        categories = sorted(set(POLICY['category_ids']['parents'] + POLICY['category_ids']['leaves']))
    return {'version': '0.5.1', 'enabled': True, 'live': True, 'english_categories': list(categories), 'public_en_posts': []}


def page_ok(url, **kwargs):
    slug = url.rstrip('/').rsplit('/', 1)[-1]
    title = next(t['title'] for t in TOPICS.values() if t['slug'] == slug)
    html = f'<html lang="en-US"><head><link rel="canonical" href="{en.EN_HOME}{slug}/"><title>{title}</title></head><body><h1>{title}</h1></body></html>'
    final = url if '/en/' in url else f'{en.EN_HOME}{slug}/'
    return seo_response(url, final, 200, {'x-nh-vien-lang': 'en'}, html)


def seo_response(url, final, status, headers, text):
    r = en.seo_common.Response(url, final, status, headers, text)
    return r


class Publisher(unittest.TestCase):
    def policy(self, **overrides):
        return {**POLICY, 'enabled': True, 'mode': 'batch', **overrides}

    def test_blocked_when_routes_not_live_or_categories_unregistered(self):
        with self.assertRaisesRegex(RuntimeError, 'not live'):
            en.sync(FakeWP(), FakeRest({**live_status(), 'live': False}), ready_articles(), FakeLedger(), self.policy(), report())
        with self.assertRaisesRegex(RuntimeError, 'not registered'):
            en.sync(FakeWP(), FakeRest(live_status((46, 47, 48))), ready_articles(), FakeLedger(), self.policy(), report())

    def test_create_register_publish_verify(self):
        wp, rest, ledger, r = FakeWP(), FakeRest(live_status()), FakeLedger(), report()
        with patch.object(en.seo_common, 'http_get', side_effect=page_ok):
            en.sync(wp, rest, ready_articles(), ledger, self.policy(), r)
        self.assertEqual(len(r['created']), 2)
        self.assertEqual(r['remaining_ready_ids'], [])
        self.assertFalse(r['has_more'])
        self.assertEqual([c[0] for c in wp.calls], ['posts', 'posts/100', 'posts', 'posts/101'])
        self.assertEqual(wp.calls[0][1]['status'], 'draft')
        self.assertEqual(wp.calls[0][1]['categories'], [50])
        self.assertEqual(wp.calls[0][1]['meta']['nh_summary'], ready_articles()[0]['description'])
        self.assertEqual(wp.calls[1][1], {'status': 'publish'})
        self.assertIn(('nh-vien/v1/posts', {'id': 100}), rest.calls)
        self.assertEqual(ledger.data['posts']['2']['phase'], 'VERIFIED')
        self.assertEqual(ledger.data['posts']['2']['url'], en.EN_HOME + TOPICS[2]['slug'] + '/')
        self.assertEqual(ledger.data['posts']['3']['phase'], 'VERIFIED')

    def test_time_budget_pauses_safely_without_starting_a_wordpress_post(self):
        wp, rest, ledger, r = FakeWP(), FakeRest(live_status()), FakeLedger(), report()
        with patch.dict(en.os.environ, {'EN_PUBLISH_TIME_BUDGET_SECONDS': '1'}), patch.object(en.time, 'monotonic', return_value=100):
            en.sync(wp, rest, ready_articles(), ledger, self.policy(), r)
        self.assertEqual(r['created'], [])
        self.assertEqual(r['remaining_ready_ids'], [2, 3])
        self.assertTrue(r['has_more'])
        self.assertEqual(wp.calls, [])

    def test_wordpress_excel_prefix_rewrite_never_becomes_public(self):
        class RewritingWP(FakeWP):
            def request(self, path, payload=None, **kwargs):
                post, metadata = super().request(path, payload=payload, **kwargs)
                if path == 'posts':
                    post['slug'] = 'excel-2-' + post['slug']
                return post, metadata

        wp, rest, ledger, r = RewritingWP(), FakeRest(live_status()), FakeLedger(), report()
        en.sync(wp, rest, ready_articles(), ledger, self.policy(), r)
        self.assertEqual([c[0] for c in wp.calls], ['posts'])
        self.assertEqual(wp.posts[0]['status'], 'draft')
        self.assertEqual(ledger.data['posts']['2']['phase'], 'DRAFT_CREATED')
        self.assertFalse(any(route == 'nh-vien/v1/posts' for route, _ in rest.calls))
        self.assertEqual(r['created'], [])
        self.assertTrue(any('changed the EN draft slug' in e['reason'] for e in r['errors']))

    def test_registration_failure_leaves_a_draft_and_never_publishes(self):
        wp, rest, ledger, r = FakeWP(), FakeRest(live_status(), register_http=400), FakeLedger(), report()
        en.sync(wp, rest, ready_articles(), ledger, self.policy(), r)
        self.assertEqual(len(wp.calls), 1)
        self.assertEqual(wp.posts[0]['status'], 'draft')
        self.assertEqual(ledger.data['posts']['2']['phase'], 'REGISTER_FAILED')
        self.assertTrue(any('refused to register' in e['reason'] for e in r['errors']))

    def test_existing_posts_and_unresolved_phases_are_never_reposted(self):
        wp, rest, ledger, r = FakeWP(), FakeRest(live_status()), FakeLedger(), report()
        ready = ready_articles()
        wp.posts = [{'id': 5, 'title': {'raw': ready[0]['title']}, 'slug': 'other', 'status': 'publish', 'content': {'raw': ''}, 'categories': [50], 'link': ''}]
        ledger.data['posts']['3'] = {'phase': 'VERIFY_PENDING'}
        en.sync(wp, rest, ready, ledger, self.policy(), r)
        self.assertEqual(len(wp.calls), 0)
        self.assertEqual([x['id'] for x in r['existing']], [2])
        self.assertTrue(any('Unresolved prior write' in e['reason'] for e in r['errors']))

    def test_public_verification_failure_is_reported_not_retried(self):
        wp, rest, ledger, r = FakeWP(), FakeRest(live_status()), FakeLedger(), report()

        def no_marker(url, **kwargs):
            return seo_response(url, url, 200, {}, '<html lang="vi"><body>x</body></html>')
        with patch.object(en.seo_common, 'http_get', side_effect=no_marker):
            en.sync(wp, rest, ready_articles(), ledger, self.policy(), r)
        self.assertEqual(ledger.data['posts']['2']['phase'], 'VERIFY_PENDING')
        self.assertEqual(len(r['created']), 0)
        self.assertEqual(len([c for c in wp.calls if c[0] == 'posts']), 1)


class Topics(unittest.TestCase):
    def test_no_excel_or_row_identifiers_in_new_english_permalinks(self):
        for slug in ('excel-478-motorbike-rental', 'excel-motorbike-rental',
                     'matrix-23-rental-prices', 'sheet-7-hanoi-guide'):
            with self.subTest(slug=slug):
                with self.assertRaisesRegex(ValueError, 'internal Excel/row prefix'):
                    en.assert_public_en_slug(slug)
        for slug in ('hanoi-motorbike-rental', 'motorbike-rental-50cc-hanoi'):
            self.assertEqual(en.assert_public_en_slug(slug), slug)
        for topic in TOPICS.values():
            self.assertEqual(en.assert_public_en_slug(topic['slug']), topic['slug'])

    def test_english_topic_matrix_rejects_spreadsheet_prefixed_slug(self):
        rows = json.loads(en.TOPICS_PATH.read_text(encoding='utf-8'))
        rows[9]['slug'] = 'excel-10-long-bien-red-river'
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / 'en-topics.json'
            path.write_text(json.dumps(rows), encoding='utf-8')
            with patch.object(en, 'TOPICS_PATH', path):
                with self.assertRaisesRegex(ValueError, 'internal Excel/row prefix'):
                    en.load_topics(POLICY)

    def test_publisher_refuses_excel_slug_before_wordpress_request(self):
        with self.assertRaisesRegex(ValueError, 'internal Excel/row prefix'):
            en.sync(None, None, [{'id': 10, 'slug': 'excel-10-bad-url'}],
                    None, POLICY, {})

    def test_topics_are_unique_and_routable(self):
        self.assertGreaterEqual(len(TOPICS), 40)
        for topic in TOPICS.values():
            self.assertIn(topic['category_id'], POLICY['category_ids']['leaves'])
            self.assertNotIn(topic['slug'], en.EN_PAGE_SLUGS)

    def test_policy_defaults_are_safe(self):
        # EN autopilot intentionally changes enabled=False to True only after
        # production VI/EN Core preflight and public-route verification. The QA
        # must accept that rollout without disabling QA or route checks.
        self.assertIsInstance(POLICY['enabled'], bool)
        self.assertIn(POLICY['mode'], ('pilot', 'batch'))
        self.assertEqual(POLICY['pilot_ids'], [1, 2, 3])
        self.assertTrue(POLICY['require_live_routes'])
        self.assertGreaterEqual(POLICY['min_score'], 85)
        # Unlimited QA-gated EN publishing: no count-based policy caps.
        # The GitHub runner deadline is handled by a resumable soft stop.
        self.assertNotIn('batch_size', POLICY)
        self.assertNotIn('max_batches_per_run', POLICY)


if __name__ == '__main__':
    unittest.main()
