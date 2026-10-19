"""English pages: QA gates and the update-only publisher against a fake WordPress; no network, no writes without --live."""
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('en_pages', ROOT / 'scripts/en_pages.py')
pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pages)

BUSINESS = json.loads((ROOT / 'en/business.json').read_text(encoding='utf-8'))
SENTENCES = [
    'The shop in Long Bien hands over every scooter with the brakes, lights, horn and tyres checked in front of the renter.',
    'A rental day is twenty-four hours from the handover time written in the contract, and a shorter use still counts as a day.',
    'Weekly and monthly packages are priced on their own, so a long stay is cheaper than multiplying the daily rate.',
    'Riders cross the Chuong Duong or Vinh Tuy bridge to reach the Old Quarter in about twenty minutes outside the rush hours.',
    'The cash deposit is returned at the end of the rental once the bike comes back in the condition recorded at handover.',
    'Petrol stations are staffed, so you stay seated while the attendant fills the tank and you pay in cash or by QR code.',
    'Parking attendants hand out a numbered ticket, and the same ticket is needed to collect the bike again later.',
    'Helmets must be worn on every road in Vietnam, and the basic helmet that comes with the bike meets that requirement.',
]


def para(n, m):
    rotated = SENTENCES[m % 8:] + SENTENCES[:m % 8]
    return f'Point {n}.{m}: ' + ' '.join(rotated)


def body_of(sections, questions=0, extra=''):
    parts = [para(0, 1) + '\n\n' + para(0, 2)]
    for n in range(1, sections + 1):
        parts.append(f'## Section {n}\n\n' + para(n, 3) + '\n\n' + para(n, 4))
    if questions:
        parts.append('## FAQ')
        for q in range(questions):
            parts.append(f'### Question number {q}?\n\nAnswer {q}: ' + SENTENCES[q % 8])
    if extra:
        parts.append(extra)
    return '\n\n'.join(parts)


def text_of(page_id, body=None, **overrides):
    spec = pages.PAGES[page_id]
    meta = {'page_id': str(page_id), 'slug': spec['slug'], 'parent': str(spec['parent']),
            'title': f'A fine English page about {spec["slug"]}',
            'description': 'Family-run motorbike rental in Long Bien, Hanoi: Honda scooters, manual bikes and 50cc models with a 24-hour rental day.',
            'ready': 'true'}
    meta.update(overrides)
    body = body if body is not None else body_of(4, spec['min_questions'])
    return '---\n' + '\n'.join(f'{k}: {v}' for k, v in meta.items()) + '\n---\n' + body


def write(tmp, page_id, text, name=None):
    path = pathlib.Path(tmp) / (name or pages.PAGES[page_id]['file'])
    path.write_text(text, encoding='utf-8')
    return path


class Registry(unittest.TestCase):
    def test_seven_pages_below_en(self):
        self.assertEqual(sorted(pages.PAGES), [1758, 1759, 1760, 1761, 1762, 1763, 1764])
        self.assertEqual({p['slug'] for p in pages.PAGES.values()}, {'en', 'about', 'prices', 'contact', 'rental-guide', 'faq', 'motorbikes'})
        self.assertEqual(pages.PAGES[1758]['parent'], 0)
        self.assertTrue(all(p['parent'] == 1758 for i, p in pages.PAGES.items() if i != 1758))
        self.assertTrue(all(p['url'].startswith(pages.EN_HOME) for p in pages.PAGES.values()))


class Qa(unittest.TestCase):
    def read(self, page_id, text, name=None):
        with tempfile.TemporaryDirectory() as tmp:
            return pages.read_page(write(tmp, page_id, text, name), BUSINESS)

    def test_good_page_is_ready_with_a_stable_hash(self):
        page = self.read(1759, text_of(1759))
        self.assertTrue(page['ready'])
        self.assertEqual((page['slug'], page['parent'], page['url']), ('about', 1758, pages.EN_HOME + 'about/'))
        self.assertGreaterEqual(page['words'], 800)
        self.assertEqual(page['hash'], pages.page_hash(page['title'], page['description'], page['body']))
        self.assertTrue(pages.content_of(page).startswith(f"<!-- wp-aiwriter-en-page:id=1759;sha256={page['hash']} -->\n<p>"))

    def test_not_ready_page_is_skipped(self):
        self.assertEqual(self.read(1759, text_of(1759, ready='false')), {'id': 1759, 'ready': False})

    def test_file_name_must_match_the_page(self):
        with self.assertRaisesRegex(ValueError, 'filename'):
            self.read(1759, text_of(1759), name='prices.md')

    def test_slug_and_parent_must_match_the_registry(self):
        with self.assertRaisesRegex(ValueError, 'parent'):
            self.read(1759, text_of(1759, parent='0'))
        with self.assertRaisesRegex(ValueError, 'slug'):
            self.read(1759, text_of(1759, slug='about-us'))

    def test_short_page_fails(self):
        with self.assertRaisesRegex(ValueError, 'words'):
            self.read(1759, text_of(1759, body=body_of(1)))

    def test_contact_page_may_be_short(self):
        self.assertTrue(self.read(1761, text_of(1761, body=body_of(2)))['ready'])

    def test_description_length_is_a_gate(self):
        with self.assertRaisesRegex(ValueError, 'description'):
            self.read(1759, text_of(1759, description='Too short.'))

    def test_vietnamese_text_fails(self):
        body = body_of(4, 0, 'Giá thuê xe máy của chúng tôi là tốt nhất và bạn không cần lo về giá khi thuê.')
        with self.assertRaisesRegex(ValueError, 'Vietnamese'):
            self.read(1759, text_of(1759, body=body))

    def test_business_facts_are_guarded(self):
        with self.assertRaisesRegex(ValueError, 'forbidden business fragment'):
            self.read(1759, text_of(1759, body=body_of(4, 0, 'Call 0942 467 674 for the other shop.')))
        with self.assertRaisesRegex(ValueError, 'unverified VND amount: 250000'):
            self.read(1759, text_of(1759, body=body_of(4, 0, 'A scooter costs VND 250,000 per day.')))
        with self.assertRaisesRegex(ValueError, 'VND only'):
            self.read(1759, text_of(1759, body=body_of(4, 0, 'That is about $8 per day.')))
        with self.assertRaisesRegex(ValueError, 'not the business phone'):
            self.read(1759, text_of(1759, body=body_of(4, 0, 'Call 0912 345 678 today.')))
        self.assertTrue(self.read(1759, text_of(1759, body=body_of(4, 0, 'Call 0334 699 969 or +84 334 699 969; a day is VND 150,000 and the deposit VND 2–5 million.')))['ready'])

    def test_internal_links_stay_below_en(self):
        with self.assertRaisesRegex(ValueError, 'outside /en/'):
            self.read(1759, text_of(1759, body=body_of(4, 0, 'See the [Vietnamese prices](https://blog.rentbikehanoi.com/bang-gia/).')))
        with self.assertRaisesRegex(ValueError, 'https'):
            self.read(1759, text_of(1759, body=body_of(4, 0, 'See [this](http://example.com/).')))
        self.assertTrue(self.read(1759, text_of(1759, body=body_of(4, 0, 'See the [price guide](https://blog.rentbikehanoi.com/en/prices/).')))['ready'])

    def test_faq_page_needs_fifteen_questions(self):
        with self.assertRaisesRegex(ValueError, '14 questions'):
            self.read(1763, text_of(1763, body=body_of(3, 14)))
        page = self.read(1763, text_of(1763, body=body_of(3, 16)))
        self.assertEqual(page['questions'], 16)

    def test_placeholders_and_h1_fail(self):
        with self.assertRaisesRegex(ValueError, 'placeholder'):
            self.read(1759, text_of(1759, body=body_of(4, 0, '# Another H1')))
        with self.assertRaisesRegex(ValueError, 'placeholder'):
            self.read(1759, text_of(1759, body=body_of(4, 0, 'TODO write this')))

    def test_copied_paragraphs_between_pages_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, 1759, text_of(1759))
            write(tmp, 1760, text_of(1760, body=body_of(4)))
            with patch.object(pages, 'PAGES_DIR', pathlib.Path(tmp)):
                ready, errors = pages.load_pages(BUSINESS)
        self.assertEqual(len(ready), 2)
        self.assertEqual(len(errors), 1)
        self.assertIn('7-word phrases', errors[0]['reason'])

    def test_distinct_pages_load_without_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, 1759, text_of(1759))
            body = '\n\n'.join(['Intro ' + ' '.join(f'word{n}' for n in range(70))] + [f'## Part {n}\n\n' + ' '.join(f'token{n}x{m}' for m in range(160)) for n in range(5)])
            write(tmp, 1760, text_of(1760, body=body))
            with patch.object(pages, 'PAGES_DIR', pathlib.Path(tmp)):
                ready, errors = pages.load_pages(BUSINESS)
        self.assertEqual(([p['id'] for p in ready], errors), ([1759, 1760], []))


class FakeClient:
    """The two calls the publisher makes, answered from a dict of live pages; every write is recorded."""

    def __init__(self, live):
        self.live = live
        self.writes = []
        self.reads = []

    def get(self, path, public=False):
        self.reads.append(path)
        if path.startswith('users/me'):
            return {'id': 1}
        page_id = int(path.split('/')[1].split('?')[0])
        return json.loads(json.dumps(self.live[page_id]))

    def request(self, path, payload=None, public=False, webpage=False):
        page_id = int(path.split('/')[1].split('?')[0])
        self.writes.append((page_id, payload))
        row = self.live[page_id]
        row['title'] = {'raw': payload['title'], 'rendered': payload['title']}
        row['excerpt'] = {'raw': payload['excerpt'], 'rendered': payload['excerpt']}
        row['content'] = {'raw': payload['content'], 'rendered': payload['content']}
        return row, {}


def live_row(page_id, **overrides):
    spec = pages.PAGES[page_id]
    row = {'id': page_id, 'type': 'page', 'slug': spec['slug'], 'parent': spec['parent'], 'status': 'publish', 'link': spec['url'],
           'title': {'raw': 'Old title', 'rendered': 'Old title'}, 'excerpt': {'raw': 'Old excerpt', 'rendered': 'Old excerpt'},
           'content': {'raw': '<p>Old content</p>', 'rendered': '<p>Old content</p>'}, 'modified': '2026-10-20T02:40:12'}
    row.update(overrides)
    return row


def report():
    return {'refused': [], 'unchanged': [], 'would_update': [], 'updated': [], 'errors': [], 'backups': []}


class Publisher(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.page = pages.read_page(write(tmp, 1759, text_of(1759)), BUSINESS)

    def test_preview_reads_and_writes_nothing(self):
        client = FakeClient({1759: live_row(1759)})
        out = report()
        pages.sync(client, [self.page], False, out)
        self.assertEqual(client.writes, [])
        self.assertEqual(out['would_update'][0]['result'], 'WOULD_UPDATE')
        self.assertEqual(out['would_update'][0]['previous']['title'], 'Old title')

    def test_unchanged_page_is_skipped_even_live(self):
        client = FakeClient({1759: live_row(1759, content={'raw': pages.content_of(self.page), 'rendered': ''})})
        out = report()
        pages.sync(client, [self.page], True, out)
        self.assertEqual(client.writes, [])
        self.assertEqual(out['unchanged'][0]['result'], 'UNCHANGED')

    def test_unexpected_live_page_is_refused_without_a_write(self):
        for bad in ({'slug': 'gioi-thieu'}, {'parent': 0}, {'status': 'draft'}, {'type': 'post'}, {'link': 'https://blog.rentbikehanoi.com/gioi-thieu/'}):
            client = FakeClient({1759: live_row(1759, **bad)})
            out = report()
            pages.sync(client, [self.page], True, out)
            self.assertEqual(client.writes, [], bad)
            self.assertEqual(out['refused'][0]['result'], 'REFUSED', bad)
            self.assertFalse(all(out['refused'][0]['checks'].values()))

    def test_live_update_writes_once_reads_back_and_backs_up(self):
        client = FakeClient({1759: live_row(1759)})
        out = report()
        reply = SimpleNamespace(status=200, text='<html><h1>A fine English page about about</h1></html>')
        with patch.object(pages.seo_common, 'http_get', return_value=reply):
            pages.sync(client, [self.page], True, out)
        self.assertEqual(len(client.writes), 1)
        page_id, payload = client.writes[0]
        self.assertEqual(page_id, 1759)
        self.assertEqual(sorted(payload), ['content', 'excerpt', 'title'])
        self.assertTrue(payload['content'].startswith(pages.marker_of(self.page)))
        self.assertEqual(payload['excerpt'], self.page['description'])
        self.assertEqual(out['updated'][0]['result'], 'UPDATED')
        self.assertEqual(out['updated'][0]['public'], {'status': 200, 'title_seen': True})
        self.assertEqual(out['backups'][0]['content'], '<p>Old content</p>')
        self.assertEqual(out['backups'][0]['title'], 'Old title')
        self.assertEqual(out['errors'], [])

    def test_failed_readback_is_an_error(self):
        class Flaky(FakeClient):
            def request(self, path, payload=None, public=False, webpage=False):
                self.writes.append((path, payload))
                return {}, {}
        client = Flaky({1759: live_row(1759)})
        out = report()
        pages.sync(client, [self.page], True, out)
        self.assertEqual(len(client.writes), 1)
        self.assertEqual(out['errors'][0]['result'], 'ERROR')
        self.assertIn('readback', out['errors'][0]['reason'])


class Run(unittest.TestCase):
    def test_qa_mode_reports_and_sync_needs_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, 1759, text_of(1759))
            with patch.object(pages, 'PAGES_DIR', pathlib.Path(tmp)), patch.object(pages, 'REPORT_DIR', pathlib.Path(tmp) / 'reports'), \
                    patch.object(pages.seo_common, 'step_summary'), patch.dict(os.environ, {'WP_USERNAME': '', 'WP_APPLICATION_PASSWORD': ''}):
                self.assertEqual(pages.run(SimpleNamespace(mode='qa', live=False)), 0)
                latest = json.loads((pathlib.Path(tmp) / 'reports' / 'latest.json').read_text(encoding='utf-8'))
                self.assertEqual(latest['status'], 'QA_PASSED')
                self.assertEqual(pages.run(SimpleNamespace(mode='sync', live=True)), 2)
                latest = json.loads((pathlib.Path(tmp) / 'reports' / 'latest.json').read_text(encoding='utf-8'))
                self.assertIn('BLOCKED', latest['status'])

    def test_sync_is_blocked_while_a_file_fails_qa(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, 1759, text_of(1759, body=body_of(1)))
            with patch.object(pages, 'PAGES_DIR', pathlib.Path(tmp)), patch.object(pages, 'REPORT_DIR', pathlib.Path(tmp) / 'reports'), \
                    patch.object(pages.seo_common, 'step_summary'), patch.dict(os.environ, {'WP_USERNAME': 'u', 'WP_APPLICATION_PASSWORD': 'p'}), \
                    patch.object(pages.engine, 'WPClient', side_effect=AssertionError('no client while QA fails')):
                self.assertEqual(pages.run(SimpleNamespace(mode='sync', live=True)), 1)
                latest = json.loads((pathlib.Path(tmp) / 'reports' / 'latest.json').read_text(encoding='utf-8'))
                self.assertIn('BLOCKED', latest['status'])


if __name__ == '__main__':
    unittest.main()
