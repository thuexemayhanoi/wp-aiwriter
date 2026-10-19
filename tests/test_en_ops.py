"""EN rollout safety: one idempotent pass through a fake VI-EN Core REST API; no network, no writes without --live."""
import importlib.util
import json
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('en_ops', ROOT / 'scripts/en_ops.py')
ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)

POLICY = json.loads((ROOT / 'en/publication-policy.json').read_text(encoding='utf-8'))
PARENTS = [int(x) for x in POLICY['category_ids']['parents']]
LEAVES = [int(x) for x in POLICY['category_ids']['leaves']]
PAIRS = [(int(p['vi']), int(p['en'])) for p in POLICY['page_pairs']]
SLUGS = {int(p['vi']): p['vi_slug'] for p in POLICY['page_pairs']}
SLUGS.update({int(p['en']): p['en_slug'] for p in POLICY['page_pairs']})


class FakeRest:
    """The subset of VI-EN Core 0.5.1 and wp/v2/pages the rollout talks to, with the plugin's idempotent answers."""

    def __init__(self, installed=True, version='0.5.1', live=False, categories=(), pairs=None, slugs=None, fail=None, site_name=None):
        self.installed, self.version = installed, version
        self.state = {'live': live, 'categories': set(categories), 'pairs': dict(pairs or {}), 'site_name': site_name}
        self.slugs = dict(slugs if slugs is not None else SLUGS)
        self.fail = fail or {}
        self.writes = []
        self.reads = []

    def snapshot(self):
        row = {'version': self.version, 'enabled': self.state['live'], 'source': 'setting_on' if self.state['live'] else 'unset',
               'live': self.state['live'], 'english_categories': sorted(self.state['categories']),
               'page_pairs': {str(k): v for k, v in self.state['pairs'].items()}, 'preflight': []}
        if self.state['site_name'] is not None:   # plugin 0.5.2 and later report the English site name
            row['site_name_en'] = self.state['site_name']
        return row

    def call(self, route, payload=None, method=None):
        if payload is None:
            self.reads.append(route)
            if route == 'nh-vien/v1/status':
                if not self.installed:
                    return 404, {'code': 'rest_no_route', 'message': 'No route was found matching the URL and request method.'}
                return 200, self.snapshot()
            if route.startswith('wp/v2/pages/'):
                page_id = int(route.split('/')[3].split('?')[0])
                slug = self.slugs.get(page_id)
                if slug is None:
                    return 404, {'code': 'rest_post_invalid_id', 'message': 'Invalid post ID.'}
                return 200, {'id': page_id, 'slug': slug, 'status': 'publish', 'link': f'https://example.test/{slug}/'}
            raise AssertionError(f'unexpected read {route}')
        self.writes.append((route, dict(payload)))
        if route == 'nh-vien/v1/routes':
            if self.fail.get('enable'):
                return 409, {'code': 'nh_vien_preflight_failed', 'message': 'Nothing was changed: the preflight found a conflict.'}
            self.state['live'] = True
            return 200, {'result': {'enabled': True, 'smoke': {'result': 'passed'}}, 'status': self.snapshot()}
        if route == 'nh-vien/v1/categories':
            if payload['id'] in self.fail.get('categories', ()):
                return 409, {'code': 'nh_vien_category_conflict', 'message': 'Choose an empty category whose parent is also English.'}
            self.state['categories'].add(payload['id'])
            return 200, {'english_categories': sorted(self.state['categories'])}
        if route == 'nh-vien/v1/pages':
            if (payload['vi'], payload['en']) in self.fail.get('pairs', ()):
                return 409, {'code': 'nh_vien_conflict', 'message': 'One of the pages is already linked.'}
            self.state['pairs'][payload['vi']] = payload['en']
            return 200, {'page_pairs': {str(k): v for k, v in self.state['pairs'].items()}}
        if route == 'nh-vien/v1/settings':
            if self.fail.get('site_name'):
                return 500, {'code': 'nh_vien_save_failed', 'message': 'The setting could not be saved.'}
            self.state['site_name'] = payload['site_name_en']
            return 200, {'result': {'site_name_en': payload['site_name_en']}, 'status': self.snapshot()}
        raise AssertionError(f'unexpected write {route}')


def args(live=True, confirm=True, urls=ops.EN_URLS):
    return SimpleNamespace(live=live, confirm=confirm, urls=urls)


BUSINESS = json.loads((ROOT / 'en/business.json').read_text(encoding='utf-8'))


def run(rest, live=True, confirm=True, verified=True):
    log = []
    with patch.object(ops, 'verify', return_value=verified) as verify:
        outcome = ops.rollout(rest, args(live, confirm), log, POLICY, BUSINESS)
    return outcome, log, verify


class Rollout(unittest.TestCase):
    def test_policy_lists_the_four_page_pairs_with_their_slugs(self):
        self.assertEqual(PAIRS, [(14, 1759), (19, 1760), (25, 1761), (24, 1763)])
        self.assertEqual([p['vi_slug'] for p in POLICY['page_pairs']], ['gioi-thieu', 'bang-gia', 'lien-he', 'hoi-dap'])
        self.assertEqual([p['en_slug'] for p in POLICY['page_pairs']], ['about', 'prices', 'contact', 'faq'])
        self.assertEqual(len({p['vi'] for p in POLICY['page_pairs']}), 4)
        self.assertEqual(len({p['en'] for p in POLICY['page_pairs']}), 4)

    def test_not_installed_ends_quietly_without_writes(self):
        rest = FakeRest(installed=False)
        outcome, log, verify = run(rest)
        self.assertEqual(outcome, 'NOT_INSTALLED')
        self.assertEqual(rest.writes, [])
        self.assertFalse(verify.called)
        self.assertEqual(log[-1]['http'], 404)

    def test_older_plugin_counts_as_not_installed(self):
        rest = FakeRest(version='0.5.0')
        outcome, log, _ = run(rest)
        self.assertEqual(outcome, 'NOT_INSTALLED')
        self.assertEqual(rest.writes, [])
        self.assertEqual(log[-1]['version'], '0.5.0')
        self.assertEqual(ops.version_tuple('0.5.10'), (0, 5, 10))
        self.assertGreaterEqual(ops.version_tuple('0.6.0'), ops.MIN_VERSION)

    def test_dry_run_reads_everything_and_writes_nothing(self):
        rest = FakeRest()
        outcome, log, verify = run(rest, live=False)
        self.assertEqual(outcome, 'DRY_RUN')
        self.assertEqual(rest.writes, [])
        self.assertFalse(verify.called)
        self.assertEqual([e['id'] for e in log if e.get('action') == 'register-category' and e.get('dry_run')], PARENTS + LEAVES)
        self.assertEqual([(e['vi'], e['en']) for e in log if e.get('action') == 'link-pages' and e.get('dry_run')], PAIRS)
        self.assertEqual(log[-1]['writes'], 0)

    def test_full_pass_from_an_empty_site_in_the_right_order(self):
        rest = FakeRest()
        outcome, log, verify = run(rest)
        self.assertEqual(outcome, 'VERIFIED')
        self.assertEqual(rest.writes[0], ('nh-vien/v1/routes', {'enabled': True, 'confirm': True}))
        self.assertEqual([p['id'] for r, p in rest.writes[1:12]], PARENTS + LEAVES)
        self.assertEqual([(p['vi'], p['en']) for r, p in rest.writes[12:]], PAIRS)
        self.assertEqual(len(rest.writes), 1 + len(PARENTS) + len(LEAVES) + len(PAIRS))
        verify.assert_called_once()
        self.assertEqual(verify.call_args[0][0], ops.EN_URLS.split(','))
        self.assertTrue(rest.state['live'])
        self.assertEqual(log[-1]['outcome'], 'VERIFIED')
        self.assertEqual(log[-1]['writes'], len(rest.writes))
        self.assertEqual(log[-1]['english_categories'], sorted(PARENTS + LEAVES))
        self.assertEqual(log[-1]['page_pairs'], dict(PAIRS))

    def test_second_pass_skips_everything_already_done(self):
        rest = FakeRest(live=True, categories=PARENTS + LEAVES, pairs=dict(PAIRS))
        outcome, log, verify = run(rest)
        self.assertEqual(outcome, 'VERIFIED')
        self.assertEqual(rest.writes, [])
        verify.assert_called_once()
        self.assertEqual(sum(1 for e in log if e.get('skipped')), 1 + len(PARENTS) + len(LEAVES) + len(PAIRS))

    def test_partial_state_only_writes_what_is_missing(self):
        rest = FakeRest(live=True, categories=PARENTS + [49], pairs={14: 1759})
        outcome, _, _ = run(rest)
        self.assertEqual(outcome, 'VERIFIED')
        self.assertEqual([r for r, _ in rest.writes if r == 'nh-vien/v1/routes'], [])
        self.assertEqual([p['id'] for r, p in rest.writes if r == 'nh-vien/v1/categories'], [50, 51, 52, 53, 54, 55, 56])
        self.assertEqual([(p['vi'], p['en']) for r, p in rest.writes if r == 'nh-vien/v1/pages'], [(19, 1760), (25, 1761)])

    def test_confirmation_flag_is_passed_through(self):
        rest = FakeRest()
        outcome, _, _ = run(rest, confirm=False)
        self.assertEqual(outcome, 'VERIFIED')
        self.assertEqual(rest.writes[0][1]['confirm'], False)

    def test_failed_switch_stops_the_pass_before_any_other_write(self):
        rest = FakeRest(fail={'enable': True})
        outcome, log, verify = run(rest)
        self.assertEqual(outcome, 'FAILED')
        self.assertEqual(len(rest.writes), 1)
        self.assertFalse(verify.called)
        self.assertEqual(log[-1]['step'], 'enable')
        self.assertEqual(log[-1]['http'], 409)
        self.assertEqual(log[-1]['error']['code'], 'nh_vien_preflight_failed')

    def test_category_conflict_stops_before_the_page_pairs(self):
        rest = FakeRest(live=True, fail={'categories': (50,)})
        outcome, log, _ = run(rest)
        self.assertEqual(outcome, 'FAILED')
        self.assertEqual([p['id'] for r, p in rest.writes], [46, 47, 48, 49, 50])
        self.assertEqual(log[-1]['step'], 'register-category')
        self.assertEqual(log[-1]['id'], 50)

    def test_pair_with_an_unexpected_slug_is_never_written(self):
        rest = FakeRest(live=True, categories=PARENTS + LEAVES, slugs={**SLUGS, 19: 'something-else'})
        outcome, log, verify = run(rest)
        self.assertEqual(outcome, 'FAILED')
        self.assertEqual([(p['vi'], p['en']) for r, p in rest.writes], [(14, 1759)])
        self.assertEqual(log[-1]['step'], 'link-pages')
        self.assertEqual((log[-1]['vi'], log[-1]['page'], log[-1]['expected_slug']), (19, 19, 'bang-gia'))
        self.assertEqual(log[-1]['found']['slug'], 'something-else')
        self.assertFalse(verify.called)

    def test_missing_page_is_never_linked(self):
        slugs = {k: v for k, v in SLUGS.items() if k != 1761}
        rest = FakeRest(live=True, categories=PARENTS + LEAVES, slugs=slugs)
        outcome, log, _ = run(rest)
        self.assertEqual(outcome, 'FAILED')
        self.assertEqual([(p['vi'], p['en']) for r, p in rest.writes], [(14, 1759), (19, 1760)])
        self.assertEqual((log[-1]['page'], log[-1]['http']), (1761, 404))

    def test_pair_conflict_is_a_failure_not_a_skip(self):
        rest = FakeRest(live=True, categories=PARENTS + LEAVES, fail={'pairs': ((25, 1761),)})
        outcome, log, _ = run(rest)
        self.assertEqual(outcome, 'FAILED')
        self.assertEqual(log[-1]['error']['code'], 'nh_vien_conflict')

    def test_plugin_without_site_name_support_is_left_alone(self):
        rest = FakeRest(live=True, categories=PARENTS + LEAVES, pairs=dict(PAIRS))
        outcome, log, _ = run(rest)
        self.assertEqual(outcome, 'VERIFIED')
        self.assertEqual(rest.writes, [])
        self.assertEqual([e for e in log if e.get('action') == 'site-name'], [])

    def test_site_name_is_set_from_business_json_once(self):
        rest = FakeRest(live=True, categories=PARENTS + LEAVES, pairs=dict(PAIRS), version='0.5.2', site_name='')
        outcome, log, _ = run(rest)
        self.assertEqual(outcome, 'VERIFIED')
        self.assertEqual(rest.writes, [('nh-vien/v1/settings', {'site_name_en': BUSINESS['name_en']})])
        self.assertEqual(rest.state['site_name'], 'Nguyen Ha Motorbike Rental')
        rest.writes = []
        outcome, log, _ = run(rest)
        self.assertEqual((outcome, rest.writes), ('VERIFIED', []))
        self.assertEqual([e for e in log if e.get('action') == 'site-name'][0]['skipped'], 'already set')

    def test_site_name_dry_run_and_failure(self):
        rest = FakeRest(live=True, categories=PARENTS + LEAVES, pairs=dict(PAIRS), version='0.5.2', site_name='')
        outcome, log, _ = run(rest, live=False)
        self.assertEqual((outcome, rest.writes), ('DRY_RUN', []))
        self.assertTrue([e for e in log if e.get('action') == 'site-name'][0]['dry_run'])
        rest = FakeRest(live=True, categories=PARENTS + LEAVES, pairs=dict(PAIRS), version='0.5.2', site_name='', fail={'site_name': True})
        outcome, log, verify = run(rest)
        self.assertEqual(outcome, 'FAILED')
        self.assertEqual(log[-1]['step'], 'site-name')
        self.assertFalse(verify.called)

    def test_public_verification_failure_fails_the_pass(self):
        rest = FakeRest()
        outcome, log, verify = run(rest, verified=False)
        self.assertEqual(outcome, 'FAILED')
        verify.assert_called_once()
        self.assertEqual(log[-1]['step'], 'verify')

    def test_unreadable_status_is_a_failure(self):
        class Down(FakeRest):
            def call(self, route, payload=None, method=None):
                return 0, {'code': 'network', 'message': 'timed out'}
        outcome, log, _ = run(Down())
        self.assertEqual(outcome, 'FAILED')
        self.assertEqual(log[-1]['step'], 'status')


class Main(unittest.TestCase):
    def test_rollout_exit_code_and_github_output(self):
        import os
        import tempfile
        rest = FakeRest(installed=False)
        with tempfile.TemporaryDirectory() as tmp:
            output = pathlib.Path(tmp) / 'out'
            env = {'WP_USERNAME': 'u', 'WP_APPLICATION_PASSWORD': 'p', 'GITHUB_OUTPUT': str(output)}
            with patch.dict(os.environ, env), patch.object(ops, 'Rest', return_value=rest), \
                    patch.object(ops, 'REPORT_DIR', pathlib.Path(tmp) / 'reports'), patch.object(ops.seo_common, 'step_summary'), \
                    patch('sys.argv', ['en_ops.py', 'rollout', '--live', '--confirm']):
                self.assertEqual(ops.main(), 0)
            self.assertEqual(output.read_text(encoding='utf-8'), 'outcome=NOT_INSTALLED\n')
            report = json.loads((pathlib.Path(tmp) / 'reports' / 'rollout.json').read_text(encoding='utf-8'))
            self.assertEqual(report[-1]['outcome'], 'NOT_INSTALLED')
        self.assertEqual(rest.writes, [])

    def test_rollout_without_secrets_is_blocked(self):
        import os
        with patch.dict(os.environ, {'WP_USERNAME': '', 'WP_APPLICATION_PASSWORD': ''}), \
                patch('sys.argv', ['en_ops.py', 'rollout', '--live']):
            self.assertEqual(ops.main(), 2)


if __name__ == '__main__':
    unittest.main()
