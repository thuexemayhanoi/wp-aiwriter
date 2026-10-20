#!/usr/bin/env python3
"""The English pages of the live site, kept in the repository: QA, then an update-only publisher.

  python scripts/en_pages.py --mode qa            # the gates below; no network
  python scripts/en_pages.py --mode sync          # preview: reads only locally authored, QA-ready EN page files; no writes
  python scripts/en_pages.py --mode sync --live   # updates the pages whose content changed (GitHub Actions)

Scope: only the English pages listed in PAGES (the original seven and twelve EN pages created for the 500-topic expansion) are ever
written, and only when an EN Markdown page exists, passes QA and the live page answered with the expected slug, parent, type, status and address. No page is
created, deleted, unpublished, moved or renamed; a Vietnamese page is never written. WordPress keeps a revision of
every update, and the previous title, excerpt and content are saved in the run's report before the write. Nothing is
written while any page file fails QA. The content is Markdown with front matter, rendered like the English articles.
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))
import en_engine  # noqa: E402
import engine  # noqa: E402
import seo_common  # noqa: E402

PAGES_DIR = ROOT / 'en' / 'pages'
REPORT_DIR = ROOT / 'reports' / 'en-pages'
MARKER = 'wp-aiwriter-en-page:id={id};sha256={hash}'
EN_HOME = en_engine.EN_HOME
PAGES = {
    1758: {'slug': 'en', 'parent': 0, 'file': 'home.md', 'url': EN_HOME, 'min_words': 450, 'min_questions': 0},
    1759: {'slug': 'about', 'parent': 1758, 'file': 'about.md', 'url': EN_HOME + 'about/', 'min_words': 800, 'min_questions': 0},
    1760: {'slug': 'prices', 'parent': 1758, 'file': 'prices.md', 'url': EN_HOME + 'prices/', 'min_words': 700, 'min_questions': 0},
    1761: {'slug': 'contact', 'parent': 1758, 'file': 'contact.md', 'url': EN_HOME + 'contact/', 'min_words': 250, 'min_questions': 0},
    1762: {'slug': 'rental-guide', 'parent': 1758, 'file': 'rental-guide.md', 'url': EN_HOME + 'rental-guide/', 'min_words': 900, 'min_questions': 0},
    1763: {'slug': 'faq', 'parent': 1758, 'file': 'faq.md', 'url': EN_HOME + 'faq/', 'min_words': 900, 'min_questions': 15},
    1764: {'slug': 'motorbikes', 'parent': 1758, 'file': 'motorbikes.md', 'url': EN_HOME + 'motorbikes/', 'min_words': 700, 'min_questions': 0},
    1827: {'slug': 'services', 'parent': 1758, 'file': 'services.md', 'url': EN_HOME + 'services/', 'min_words': 350, 'min_questions': 0},
    1828: {'slug': '50cc-bikes', 'parent': 1758, 'file': '50cc-bikes.md', 'url': EN_HOME + '50cc-bikes/', 'min_words': 330, 'min_questions': 0},
    1829: {'slug': 'electric-scooters', 'parent': 1758, 'file': 'electric-scooters.md', 'url': EN_HOME + 'electric-scooters/', 'min_words': 330, 'min_questions': 0},
    1830: {'slug': 'guides', 'parent': 1758, 'file': 'guides.md', 'url': EN_HOME + 'guides/', 'min_words': 300, 'min_questions': 0},
    1831: {'slug': 'areas', 'parent': 1758, 'file': 'areas.md', 'url': EN_HOME + 'areas/', 'min_words': 300, 'min_questions': 0},
    1832: {'slug': 'hoan-kiem', 'parent': 1758, 'file': 'hoan-kiem.md', 'url': EN_HOME + 'hoan-kiem/', 'min_words': 280, 'min_questions': 0},
    1833: {'slug': 'old-quarter', 'parent': 1758, 'file': 'old-quarter.md', 'url': EN_HOME + 'old-quarter/', 'min_words': 280, 'min_questions': 0},
    1834: {'slug': 'long-bien', 'parent': 1758, 'file': 'long-bien.md', 'url': EN_HOME + 'long-bien/', 'min_words': 280, 'min_questions': 0},
    1835: {'slug': 'ba-dinh', 'parent': 1758, 'file': 'ba-dinh.md', 'url': EN_HOME + 'ba-dinh/', 'min_words': 280, 'min_questions': 0},
    1836: {'slug': 'gia-lam', 'parent': 1758, 'file': 'gia-lam.md', 'url': EN_HOME + 'gia-lam/', 'min_words': 280, 'min_questions': 0},
    1837: {'slug': 'privacy', 'parent': 1758, 'file': 'privacy.md', 'url': EN_HOME + 'privacy/', 'min_words': 300, 'min_questions': 0},
    1838: {'slug': 'terms', 'parent': 1758, 'file': 'terms.md', 'url': EN_HOME + 'terms/', 'min_words': 350, 'min_questions': 0},
}
MAX_WORDS = 4000
OVERLAP = 0.3   # share of the 7-word phrases of the shorter page that may also appear in another page


def page_hash(title, description, body):
    return hashlib.sha256('\n'.join((title, description, body)).encode('utf-8')).hexdigest()


def marker_of(page):
    return f"<!-- {MARKER.format(id=page['id'], hash=page['hash'])} -->"


def content_of(page):
    return marker_of(page) + '\n' + engine.markdown_to_html(page['body'])


def read_page(path, business):
    """One page file through the gates; ValueError names every problem. Returns the page, or {'ready': False}."""
    metadata, body = en_engine.front_matter(path.read_text(encoding='utf-8'))
    try:
        page_id = int(metadata['page_id'])
    except (KeyError, ValueError):
        raise ValueError('Invalid page_id')
    spec = PAGES.get(page_id)
    if not spec or spec['file'] != path.name:
        raise ValueError('page_id/filename must match a page of PAGES')
    if metadata.get('slug') != spec['slug'] or metadata.get('parent') != str(spec['parent']):
        raise ValueError(f'slug or parent differs from PAGES for page {page_id}')
    if metadata.get('ready', 'false').lower() != 'true':
        return {'id': page_id, 'ready': False}
    title = metadata.get('title', '').strip()
    description = metadata.get('description', '').strip()
    html = engine.markdown_to_html(body)
    text = engine.visible(html)
    words = en_engine.words_of(text)
    problems = []
    if not 10 <= len(title) <= 70:
        problems.append(f'title is {len(title)} characters (10-70)')
    if not 110 <= len(description) <= 175:
        problems.append(f'description is {len(description)} characters (110-175: it is the excerpt and the meta description)')
    if not spec['min_words'] <= len(words) <= MAX_WORDS:
        problems.append(f'{len(words)} words; this page needs {spec["min_words"]} to {MAX_WORDS}')
    if re.search(r'\b(TODO|TBD|Lorem ipsum)\b|^# |<\s*(script|iframe|style)\b|javascript:', body, re.I | re.M):
        problems.append('placeholder, duplicate H1, or unsafe markup')
    letters = re.findall(r'[A-Za-zÀ-ỹ]', text)
    vietnamese = en_engine.VI_LETTERS.findall(text)
    if letters and len(vietnamese) / len(letters) > 0.02 or len(en_engine.VI_STOPWORDS.findall(text)) >= 5:
        problems.append('Vietnamese text in an English page')
    for fragment in business['forbidden_fragments']:
        if fragment.lower() in text.lower() or fragment.lower() in body.lower():
            problems.append(f'forbidden business fragment: {fragment}')
    phones = {re.sub(r'\D', '', business['phone_local']), re.sub(r'\D', '', business['phone_international'])}
    for phone in set(en_engine.PHONE_RE.findall(text)):
        if re.sub(r'\D', '', phone) not in phones:
            problems.append(f'phone number that is not the business phone: {phone}')
    allowed = set(business['allowed_amounts_vnd'])
    for amount, _ in en_engine.amounts_in(text):
        if amount not in allowed:
            problems.append(f'unverified VND amount: {amount}')
    if en_engine.USD_RE.search(text):
        problems.append('prices must be stated in VND only (no USD conversions)')
    for _, url in seo_common.md_links(body):
        if seo_common.is_internal(url, en_engine.WP_URL) and not url.startswith(EN_HOME):
            problems.append(f'internal link outside /en/: {url}')
        if not url.startswith('https://'):
            problems.append(f'link must be https: {url}')
    for alt, src in re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', body):
        if not alt.strip():
            problems.append(f'image without alt text: {src}')
    secs = en_engine.sections(body)
    if len(secs) < 2:
        problems.append('fewer than 2 level-2 sections')
    questions = len(re.findall(r'^### .+\?\s*$', body, re.M))
    if questions < spec['min_questions']:
        problems.append(f'{questions} questions ("### ...?"); this page needs {spec["min_questions"]}')
    paragraphs = [engine.normalized(p) for p in re.split(r'\n\s*\n', body) if len(p) > 140]
    if len(set(paragraphs)) != len(paragraphs):
        problems.append('repeated paragraph')
    if problems:
        raise ValueError('; '.join(problems))
    return {'id': page_id, 'ready': True, 'slug': spec['slug'], 'parent': spec['parent'], 'url': spec['url'], 'title': title,
            'description': description, 'body': body, 'words': len(words), 'questions': questions,
            'hash': page_hash(title, description, body)}


def load_pages(business):
    """Every page file that exists: the ready ones, and the QA errors (one per failing file, plus copied paragraphs)."""
    ready, errors = [], []
    for page_id, spec in sorted(PAGES.items()):
        path = PAGES_DIR / spec['file']
        if not path.exists():
            continue
        try:
            page = read_page(path, business)
            if page['ready']:
                ready.append(page)
        except ValueError as exc:
            errors.append({'file': spec['file'], 'reason': str(exc)})
    phrases = {page['id']: engine.shingles(page['body']) for page in ready}
    for first in ready:
        for second in ready:
            if first['id'] >= second['id']:
                continue
            smaller = min(len(phrases[first['id']]), len(phrases[second['id']])) or 1
            ratio = len(phrases[first['id']] & phrases[second['id']]) / smaller
            if ratio > OVERLAP:
                errors.append({'file': f"{PAGES[first['id']]['file']}, {PAGES[second['id']]['file']}",
                               'reason': f'{ratio:.0%} of the 7-word phrases of one page also appear in the other; write each page in its own words'})
    return ready, errors


def live_page(client, page):
    """The live page and the checks that must all hold before it is written."""
    row = client.get(f"pages/{page['id']}?context=edit")
    spec = PAGES[page['id']]
    checks = {
        'type': row.get('type') == 'page',
        'slug': row.get('slug') == spec['slug'],
        'parent': int(row.get('parent') or 0) == spec['parent'],
        'status': row.get('status') == 'publish',
        'link': seo_common.norm_url(row.get('link') or '') == seo_common.norm_url(spec['url']),
    }
    return row, checks


def sync(client, ready, live, report):
    client.get('users/me?context=edit&_fields=id')
    for page in ready:
        entry = {'id': page['id'], 'slug': page['slug'], 'url': page['url'], 'words': page['words'], 'hash': page['hash']}
        try:
            row, checks = live_page(client, page)
            if not all(checks.values()):
                entry.update({'result': 'REFUSED', 'checks': checks, 'reason': 'the live page is not the expected English page; nothing was written'})
                report['refused'].append(entry)
                continue
            raw = (row.get('content') or {}).get('raw', '') or ''
            if raw.startswith(marker_of(page)):
                entry['result'] = 'UNCHANGED'
                report['unchanged'].append(entry)
                continue
            entry['previous'] = {'title': engine.title_of(row), 'excerpt': (row.get('excerpt') or {}).get('raw', '') or '',
                                 'content_sha256': seo_common.sha256_text(raw), 'modified': row.get('modified')}
            if not live:
                entry['result'] = 'WOULD_UPDATE'
                report['would_update'].append(entry)
                continue
            report['backups'].append({**entry['previous'], 'id': page['id'], 'content': raw})
            client.request(f"pages/{page['id']}", payload={'title': page['title'], 'excerpt': page['description'], 'content': content_of(page)})
            back = client.get(f"pages/{page['id']}?context=edit")
            raw_after = (back.get('content') or {}).get('raw', '') or ''
            if (back.get('status') != 'publish' or back.get('slug') != page['slug'] or int(back.get('parent') or 0) != page['parent']
                    or not raw_after.startswith(marker_of(page)) or engine.normalized(engine.title_of(back)) != engine.normalized(page['title'])):
                raise RuntimeError('the readback after the update does not match; check the page in WordPress (a revision of the previous content exists)')
            public = seo_common.http_get(page['url'], timeout=30, retries=1)
            entry['public'] = {'status': public.status, 'title_seen': engine.normalized(page['title']) in engine.normalized(public.text or '')}
            entry['result'] = 'UPDATED'
            report['updated'].append(entry)
        except (RuntimeError, ValueError, KeyError) as exc:
            entry.update({'result': 'ERROR', 'reason': str(exc)})
            report['errors'].append(entry)


def write_report(report):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / 'latest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = [f"### EN pages ({report['mode']}{', live' if report['live'] else ''}): {report['status']}", '']
    for page in report['ready']:
        lines.append(f"- ready: #{page['id']} /{page['slug']}/ {page['words']} words, {page['questions']} questions, {page['hash'][:12]}")
    for error in report['qa_errors']:
        lines.append(f"- QA error {error['file']}: {error['reason']}")
    for key in ('refused', 'unchanged', 'would_update', 'updated', 'errors'):
        for entry in report[key]:
            lines.append(f"- {entry['result']} #{entry['id']} {entry['url']}" + (f": {entry['reason']}" if entry.get('reason') else '')
                         + (f" (public HTTP {entry['public']['status']}, title seen: {entry['public']['title_seen']})" if entry.get('public') else ''))
    text = '\n'.join(lines) + '\n'
    (REPORT_DIR / 'summary.md').write_text(text, encoding='utf-8')
    print(text)
    seo_common.step_summary(text)


def run(args):
    business = en_engine.load_business()
    ready, errors = load_pages(business)
    report = {'generated_at': en_engine.now(), 'mode': args.mode, 'live': bool(args.live),
              'ready': [{k: page[k] for k in ('id', 'slug', 'words', 'questions', 'hash')} for page in ready],
              'qa_errors': errors, 'refused': [], 'unchanged': [], 'would_update': [], 'updated': [], 'errors': [], 'backups': [],
              'status': 'QA_FAILED' if errors else 'QA_PASSED'}
    code = 1 if errors else 0
    if args.mode == 'sync' and not errors:
        user, password = os.getenv('WP_USERNAME'), os.getenv('WP_APPLICATION_PASSWORD')
        if not user or not password:
            report['status'] = 'BLOCKED: missing WP_USERNAME / WP_APPLICATION_PASSWORD; zero WordPress writes'
            code = 2
        else:
            sync(engine.WPClient(user, password), ready, bool(args.live), report)
            report['status'] = 'SYNC_FAILED' if report['errors'] or report['refused'] else ('SYNCED' if args.live else 'PREVIEW')
            code = 1 if report['errors'] or report['refused'] else 0
    elif args.mode == 'sync':
        report['status'] = 'BLOCKED: a page file fails QA; zero WordPress writes'
    write_report(report)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--mode', choices=['qa', 'sync'], required=True)
    parser.add_argument('--live', action='store_true')
    return run(parser.parse_args())


if __name__ == '__main__':
    sys.exit(main())
