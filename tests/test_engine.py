"""Safety scenarios; no network, credentials, or real WordPress writes."""
import copy
import importlib.util
import pathlib
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('engine', pathlib.Path(__file__).resolve().parents[1] / 'scripts/engine.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


def sample(i=172):
    row = e.matrix()[i]
    return {**row, 'ready': True, 'body': '## Nội dung\n\nMột bài kiểm thử đầy đủ.', 'hash': 'test-hash'}


class FakeLedger:
    def __init__(self):
        self.data = {'posts': {}}
        self.saves = []
    def save(self):
        self.saves.append(copy.deepcopy(self.data))


class FakeWP:
    def __init__(self, ledger, timeout_ids=()):
        self.posts = []
        self.ledger = ledger
        self.calls = []
        self.timeout_ids = set(timeout_ids)
        self.cats = [{'id': 15, 'name': 'Cẩm nang', 'parent': 0},
                     {'id': 19, 'name': 'Hãng xe', 'parent': 15},
                     {'id': 20, 'name': 'Hãng xe máy', 'parent': 19}]
    def get(self, path, public=False):
        if path.startswith('users/me'):
            return {'id': 1}
        post_id = int(path.split('/')[1].split('?')[0])
        return next(p for p in self.posts if p['id'] == post_id)
    def all(self, kind, **params):
        return copy.deepcopy(self.cats if kind == 'categories' else self.posts)
    def request(self, path, payload=None, **kwargs):
        if kwargs.get('webpage'):
            p = next(p for p in self.posts if p['link'] == path)
            return '<h1>' + p['title']['raw'] + '</h1>' + p['content']['raw'], {}
        self.calls.append(payload)
        i = int(payload['slug'].split('-')[1])
        assert self.ledger.data['posts'][str(i)]['phase'] == 'POST_INTENT'
        p = {**payload, 'id': len(self.posts) + 1, 'title': {'raw': payload['title']},
             'content': {'raw': payload['content'], 'rendered': payload['content']},
             'categories': payload.get('categories', [1]), 'link': e.WP_URL + '/' + payload['slug'] + '/'}
        self.posts.append(p)
        if i in self.timeout_ids:
            raise RuntimeError('POST outcome UNKNOWN')
        return p, {}


def report():
    return {'errors': [], 'existing': [], 'duplicates': [], 'created': []}


class PublicationSafety(unittest.TestCase):
    def test_markdown_tables_emphasis_links(self):
        value = e.markdown_to_html('**đậm** [nguồn](https://example.com/)\n\n| A | B |\n|---|---|\n|1|2|')
        self.assertIn('<table>', value)
        self.assertIn('<strong>đậm</strong>', value)
        self.assertIn('href="https://example.com/"', value)

    def test_wordpress_typographic_ellipsis_has_equivalent_visible_text(self):
        original = '<p>Yamaha bản ... và xe ... đang được kiểm tra.</p>'
        rendered = '<p>Yamaha bản &#8230; và xe &#8230; đang được kiểm tra.</p>'
        self.assertEqual(e.visible(original), e.visible(rendered))

    def test_wordpress_typographic_quotes_have_equivalent_visible_text(self):
        original = '<p>Con số "tối đa bốn giờ" và \'ví dụ\' trong thông báo.</p>'
        rendered = '<p>Con số &#8220;tối đa bốn giờ&#8221; và &#8216;ví dụ&#8217; trong thông báo.</p>'
        self.assertEqual(e.visible(original), e.visible(rendered))
        self.assertNotEqual(e.visible(original), e.visible('<p>Con số khác hẳn.</p>'))
        self.assertEqual(e.visible('<p>Đi 10x15 cm - rất gần ổn.</p>'),
                         e.visible('<p>Đi 10&#215;15 cm &#8211; rất gần ổn.</p>'))

    def test_category_ancestry_missing_parent_and_duplicate(self):
        cats = [{'id': 1, 'name': 'A', 'parent': 0}, {'id': 2, 'name': 'B', 'parent': 1},
                {'id': 3, 'name': 'B', 'parent': 1}, {'id': 4, 'name': 'C', 'parent': 99}]
        paths = e.category_paths(cats)
        self.assertEqual(paths['A > B'], [2, 3])
        self.assertNotIn('C', paths)

    def test_category_pagination_more_than_100(self):
        client = e.WPClient()
        with patch.object(client, 'request', side_effect=[([{'id': n} for n in range(100)], {'X-WP-TotalPages': '2'}),
                                                       ([{'id': 100}], {'X-WP-TotalPages': '2'})]) as request:
            self.assertEqual(len(client.all('categories')), 101)
            self.assertIn('page=2', request.call_args[0][0])

    def test_publish_limit_two_and_repeat_is_create_only(self):
        ledger = FakeLedger()
        client = FakeWP(ledger)
        articles = [sample(i) for i in [172, 173, 174]]
        r = report()
        e.sync(client, articles, ledger, 2, r)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(r['remaining_ready_ids'], [174])
        self.assertTrue(r['has_more'])
        self.assertEqual([p['categories'] for p in client.posts], [[20], [20]])
        self.assertTrue(all(v['phase'] == 'VERIFIED' for v in ledger.data['posts'].values()))
        e.sync(client, articles, ledger, 2, report())
        self.assertEqual(len(client.calls), 3)  # only #174; never overwrites #172 or #173


    def test_duplicate_wp_posts_are_reported_and_skip_without_failing_batch(self):
        ledger = FakeLedger()
        client = FakeWP(ledger)
        duplicate_title = sample(172)['title']
        client.posts = [{'id': i, 'title': {'raw': duplicate_title},
                         'slug': f'legacy-{i}', 'status': 'publish',
                         'link': e.WP_URL + f'/legacy-{i}/', 'categories': [20],
                         'content': {'raw': ''}} for i in (814, 830)]
        r = report()
        e.sync(client, [sample(172), sample(173)], ledger, 3, r)
        self.assertEqual(r['errors'], [])
        self.assertEqual(r['duplicates'][0]['wp_ids'], [814, 830])
        self.assertEqual([p['id'] for p in r['created']], [173])
        self.assertEqual(len(client.calls), 1)

    def test_missing_or_ambiguous_category_is_draft(self):
        for cats in ([], [{'id': 21, 'name': 'Hãng xe máy', 'parent': 19}]):
            ledger = FakeLedger()
            client = FakeWP(ledger)
            if not cats:
                client.cats = []
            else:
                client.cats.extend(cats)
            r = report()
            e.sync(client, [sample()], ledger, 2, r)
            self.assertEqual(client.posts[0]['status'], 'draft')
            self.assertNotIn('categories', client.calls[0])
            self.assertIn('ancestry', r['created'][0]['reason'])

    def test_accepted_post_timeout_recovers_without_duplicate(self):
        ledger = FakeLedger()
        client = FakeWP(ledger, timeout_ids=[172])
        r = report()
        e.sync(client, [sample(), sample(173)], ledger, 2, r)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(r['created'][0]['id'], 173)  # failure does not block the other article
        self.assertEqual(ledger.data['posts']['172']['phase'], 'POST_INTENT')
        e.sync(client, [sample(), sample(173)], ledger, 2, report())
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(ledger.data['posts']['172']['phase'], 'VERIFIED')

    def test_unknown_post_absence_never_reposts(self):
        ledger = FakeLedger()
        ledger.data['posts']['172'] = {'phase': 'POST_INTENT'}
        client = FakeWP(ledger)
        r = report()
        e.sync(client, [sample()], ledger, 2, r)
        self.assertEqual(client.calls, [])
        self.assertIn('reconcile', r['errors'][0]['reason'])

    def test_existing_draft_is_preserved(self):
        ledger = FakeLedger()
        client = FakeWP(ledger)
        client.posts = [{'id': 10, 'title': {'raw': sample()['title']}, 'slug': 'old-slug',
                         'status': 'draft', 'link': e.WP_URL + '/?p=10', 'categories': [1]}]
        before = copy.deepcopy(client.posts)
        e.sync(client, [sample()], ledger, 2, report())
        self.assertEqual(client.calls, [])
        self.assertEqual(client.posts, before)

    def test_verification_detects_changed_live_content(self):
        ledger = FakeLedger()
        client = FakeWP(ledger)
        e.sync(client, [sample()], ledger, 2, report())
        client.posts[0]['content']['rendered'] = 'Wrong public content'
        with self.assertRaisesRegex(RuntimeError, 'Public REST'):
            e.verify(client, sample(), 1, 'publish', 20, e.article_slug(sample()))

    def test_wrong_front_matter_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / '0172.md'
            path.write_text('---\nmatrix_id: 172\ntitle: wrong\ncategory_path: wrong\nready: true\n---\n\n## Wrong\n')
            with self.assertRaisesRegex(ValueError, 'mismatch'):
                e.read_post(path, e.matrix())

    def test_remote_checkpoint_preserves_concurrent_content_commit(self):
        import subprocess
        def run(*args, cwd):
            return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            origin, work, writer = root / 'origin.git', root / 'work', root / 'writer'
            run('init', '--bare', '--initial-branch=main', str(origin), cwd=root)
            run('clone', str(origin), str(work), cwd=root)
            for key, value in [('user.name', 'Test'), ('user.email', 'test@example.com')]:
                run('config', key, value, cwd=work)
            (work / 'README.md').write_text('original')
            run('add', '.', cwd=work)
            run('commit', '-m', 'initial', cwd=work)
            run('push', 'origin', 'main', cwd=work)
            run('clone', str(origin), str(writer), cwd=root)
            for key, value in [('user.name', 'Test'), ('user.email', 'test@example.com')]:
                run('config', key, value, cwd=writer)
            (writer / 'new-article.md').write_text('concurrent content')
            run('add', '.', cwd=writer)
            run('commit', '-m', 'another writer', cwd=writer)
            run('push', 'origin', 'main', cwd=writer)
            with patch.object(e, 'ROOT', work), patch.object(e, 'STATE_PATH', work / 'data/publication-state.json'):
                ledger = e.Ledger(persist_remote=True)
                ledger.data['posts']['172'] = {'phase': 'POST_INTENT'}
                ledger.save()
                remote_content = run('show', 'origin/main:new-article.md', cwd=work)
                self.assertEqual(remote_content, 'concurrent content')
                remote_state = run('show', 'origin/main:data/publication-state.json', cwd=work)
                self.assertIn('POST_INTENT', remote_state)
                ledger.data['posts']['172']['phase'] = 'VERIFIED'
                ledger.save()
                self.assertIn('VERIFIED', run('show', 'origin/main:data/publication-state.json', cwd=work))

    def test_publisher_category_scope_follows_immutable_excel(self):
        # Category changes are owner-approved. Guard the active *policy* category
        # against immutable Excel rows, rather than pinning one completed category.
        topics = e.matrix()
        scope = e.publication_scope(topics)
        policy = e.json.loads(e.POLICY_PATH.read_text(encoding='utf-8'))
        self.assertEqual(scope['category'], policy['active_category'])
        ids = [i for i, row in topics.items() if row['category'] == scope['category']]
        self.assertTrue(ids)
        self.assertEqual(ids, list(range(ids[0], ids[-1] + 1)))
        self.assertEqual((scope['first_id'], scope['last_id'], scope['total']),
                         (ids[0], ids[-1], len(ids)))
        categories = list(dict.fromkeys(row['category'] for row in topics.values()))
        idx = categories.index(scope['category'])
        self.assertEqual(scope['next_category'],
                         categories[idx + 1] if idx + 1 < len(categories) else None)

    def test_scope_produces_writer_queue_and_draft_when_taxonomy_absent(self):
        scope = e.publication_scope(e.matrix())
        ledger = FakeLedger()
        client = FakeWP(ledger)
        # A fixture must not accidentally contain the new active leaf ancestry.
        self.assertNotIn(scope['category'], e.category_paths(client.cats))
        r = report()
        e.sync(client, [sample(scope['first_id'])], ledger, 5, r, scope=scope)
        self.assertEqual(r['created'][0]['status'], 'draft')
        self.assertEqual(r['category_progress']['expected_wordpress_category_id'], None)
        self.assertEqual(r['category_progress']['source_ready'], 1)
        self.assertEqual(len(r['category_progress']['source_missing_ids']), scope['total'] - 1)
        self.assertFalse(r['category_complete'])
        self.assertEqual(len(r['category_progress']['draft_or_pending']), 1)

    def test_qa_pass_autopublish_trigger_safety(self):
        policy = e.json.loads(e.POLICY_PATH.read_text(encoding='utf-8'))
        self.assertEqual(policy['publication_mode'], 'qa_gated_autopublish')
        wf = (pathlib.Path(__file__).resolve().parents[1] /
              '.github/workflows/wordpress-publisher.yml').read_text(encoding='utf8')
        self.assertIn('workflow_run:', wf)
        self.assertIn("conclusion == 'success'", wf)
        self.assertIn("event == 'push'", wf)
        self.assertIn("head_branch == 'main'", wf)
        self.assertIn('--live --persist-state', wf)
        self.assertIn('has_more', wf)
        self.assertNotIn('schedule:', wf)
        self.assertNotIn('sleep ', wf)

    def test_invalid_category_is_rejected_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            policy = pathlib.Path(tmp) / 'policy.json'
            policy.write_text('{"active_category":"Unverified","publication_mode":"qa_gated_autopublish",'
                              '"batch_choices":[3,4,5],"pause_at_category_end":true,'
                              '"on_missing_or_ambiguous_category":"draft",'
                              '"on_trashed_posts":"do_not_touch"}', encoding='utf8')
            with patch.object(e, 'POLICY_PATH', policy):
                with self.assertRaisesRegex(ValueError, 'does not match'):
                    e.publication_scope(e.matrix())

    def test_qa_fail_blocks_live_sync_before_wordpress(self):
        args = type('Args', (), {'mode': 'sync', 'live': True, 'limit': 3, 'persist_state': False})()
        error = [{'file': 'posts/0999.md', 'reason': 'Test QA failure'}]
        with patch.object(e, 'load_posts', return_value=([], [], error)), \
             patch.object(e, 'write_report') as writer, \
             patch.object(e, 'WPClient') as client, \
             patch.dict(e.os.environ, {'WP_USERNAME': 'fake', 'WP_APPLICATION_PASSWORD': 'fake'}):
            self.assertEqual(e.run(args), 1)
            self.assertIn('QA errors present', writer.call_args[0][0]['errors'][0]['reason'])
            client.assert_not_called()

    def test_missing_secrets_is_failure_not_successful_dry_run(self):
        args = type('Args', (), {'mode': 'sync', 'live': True, 'limit': 2, 'persist_state': False})()
        with patch.dict(e.os.environ, {'WP_USERNAME': '', 'WP_APPLICATION_PASSWORD': ''}), patch.object(e, 'write_report') as writer:
            self.assertEqual(e.run(args), 1)
            self.assertIn('missing WP_USERNAME', writer.call_args[0][0]['errors'][0]['reason'])


if __name__ == '__main__':
    unittest.main()
