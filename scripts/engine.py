#!/usr/bin/env python3
"""Deterministic QA and create-only WordPress publisher; never generates prose."""
import argparse
import base64
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import html
from html.parser import HTMLParser
import json
import os
import pathlib
import re
import socket
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

import markdown

ROOT = pathlib.Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / 'data/topics.json'
STATE_PATH = ROOT / 'data/publication-state.json'
WP_URL = 'https://blog.rentbikehanoi.com'
MATRIX_SHA256 = '01192fc9ae78d7ddced2b9c7afa85b0794081269c11b028fdcf56e18aba4ca60'
POLICY_PATH = ROOT / 'data/publication-policy.json'


def now():
    return datetime.now(timezone.utc).isoformat()


TYPOGRAPHIC = str.maketrans({'\u201c': '"', '\u201d': '"', '\u2018': "'", '\u2019': "'",
                               '\u2013': '-', '\u2014': '-', '\u00d7': 'x'})


def normalized(value):
    # WordPress wptexturize renders ..., quotes, dashes and digit-x-digit typographically; treat them as equal.
    text = unicodedata.normalize('NFC', html.unescape(value)).replace('\u2026', '...').translate(TYPOGRAPHIC)
    return ' '.join(text.casefold().split())


def matrix():
    raw = MATRIX_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MATRIX_SHA256:
        raise ValueError('Excel source checksum changed; restore the original data/topics.json')
    rows = json.loads(raw)
    if len(rows) != 355 or [r[0] for r in rows] != list(range(146, 501)):
        raise ValueError('Expected exact Excel IDs 146..500')
    return {i: {'id': i, 'title': title, 'category': category} for i, title, category in rows}


def publication_scope(topics):
    """Derive the category boundary and following group from the immutable Excel rows."""
    policy = json.loads(POLICY_PATH.read_text(encoding='utf-8'))
    if (policy.get('publication_mode') != 'qa_gated_autopublish'
            or policy.get('batch_choices') != [3, 4, 5]
            or policy.get('pause_at_category_end') is not True
            or policy.get('on_missing_or_ambiguous_category') != 'draft'
            or policy.get('on_trashed_posts') != 'do_not_touch'):
        raise ValueError('Publication policy violates approved safeguards')
    unique = list(dict.fromkeys(row['category'] for row in topics.values()))
    selected = policy.get('active_category')
    if selected not in unique:
        raise ValueError('Active category does not match the immutable Excel')
    ids = [i for i, row in topics.items() if row['category'] == selected]
    if ids != list(range(ids[0], ids[-1] + 1)):
        raise ValueError('Active Excel category rows are not contiguous')
    k = unique.index(selected)
    return {'category': selected, 'first_id': ids[0], 'last_id': ids[-1],
            'total': len(ids), 'next_category': unique[k + 1] if k + 1 < len(unique) else None}


def markdown_to_html(text):
    return markdown.markdown(text, extensions=['tables', 'sane_lists'], output_format='html')


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)


def visible(text):
    parser = TextParser()
    parser.feed(text)
    return normalized(' '.join(parser.parts))


def read_post(path, topics):
    match = re.fullmatch(r'---\n(.*?)\n---\n(.*)', path.read_text(encoding='utf-8'), re.S)
    if not match:
        raise ValueError('Missing front matter')
    metadata = {}
    for line in match[1].splitlines():
        if not line.strip():
            continue
        key, sep, val = line.partition(':')
        if not sep or key.strip() in metadata:
            raise ValueError('Malformed or duplicate front matter key')
        metadata[key.strip()] = val.strip().strip('"').strip("'")
    try:
        i = int(metadata['matrix_id'])
    except (KeyError, ValueError):
        raise ValueError('Invalid matrix_id')
    if i < 165 or i not in topics or path.name != f'{i:04}.md':
        raise ValueError('ID/filename must match remaining Excel row 165..500')
    topic = topics[i]
    if metadata.get('title') != topic['title'] or metadata.get('category_path') != topic['category']:
        raise ValueError(f'Title/category mismatch with Excel #{i}')
    if metadata.get('ready', 'false').lower() != 'true':
        return {'id': i, 'ready': False}
    body = match[2].strip()
    words = len(re.findall(r'\w+', visible(markdown_to_html(body))))
    minimum = 1000 if i >= 172 else 350  # preserve the seven pre-existing authored files
    if words < minimum or len(re.findall(r'^## .+', body, re.M)) < 3:
        raise ValueError(f'Insufficient substance/structure: {words} words; minimum {minimum}')
    if re.search(r'\b(TODO|TBD|Lorem ipsum)\b|^# |<\s*(script|iframe|style)\b|javascript:', body, re.I | re.M):
        raise ValueError('Placeholder, duplicate H1, or unsafe markup')
    paragraphs = [normalized(p) for p in re.split(r'\n\s*\n', body) if len(p) > 140]
    if len(set(paragraphs)) != len(paragraphs):
        raise ValueError('Repeated paragraph')
    return {**topic, 'ready': True, 'words': words, 'body': body,
            'hash': hashlib.sha256(body.encode()).hexdigest()}


def shingles(body):
    words = re.findall(r'\w+', visible(markdown_to_html(body)))
    return set(zip(*(words[n:] for n in range(7))))


def load_posts(topics):
    articles, errors = [], []
    for path in sorted((ROOT / 'posts').glob('[0-9][0-9][0-9][0-9].md')):
        try:
            articles.append(read_post(path, topics))
        except ValueError as exc:
            errors.append({'file': str(path.relative_to(ROOT)), 'reason': str(exc)})
    accepted, signatures = [], []
    for article in articles:
        if not article['ready']:
            continue
        sig = shingles(article['body'])
        duplicate = next((other for other, prior in signatures
                          if len(sig & prior) / max(1, min(len(sig), len(prior))) > .70), None)
        if duplicate is not None:
            errors.append({'id': article['id'], 'reason': f'Near-duplicate content of #{duplicate}'})
            continue
        signatures.append((article['id'], sig))
        accepted.append(article)
    return articles, accepted, errors


def slugify(text):
    text = unicodedata.normalize('NFKD', text.lower().replace('đ', 'd'))
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')[:75].rstrip('-')


def article_slug(article):
    return f"excel-{article['id']}-{slugify(article['title'])}"


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).netloc != urllib.parse.urlsplit(WP_URL).netloc or not newurl.startswith('https://'):
            raise RuntimeError('Refused WordPress redirect to a different origin')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class WPClient:
    def __init__(self, user=None, password=None):
        self.auth = None if not user else base64.b64encode(f'{user}:{password}'.encode()).decode()
        self.opener = urllib.request.build_opener(SafeRedirect())

    def request(self, path, payload=None, public=False, webpage=False):
        url = path if webpage else WP_URL + '/wp-json/wp/v2/' + path
        if urllib.parse.urlsplit(url).netloc != urllib.parse.urlsplit(WP_URL).netloc or not url.startswith('https://'):
            raise ValueError('Only the configured WordPress origin is allowed')
        headers = {'Accept': 'text/html' if webpage else 'application/json',
                   'User-Agent': 'wp-aiwriter/2.0', 'Cache-Control': 'no-cache'}
        if self.auth and not public:
            headers['Authorization'] = 'Basic ' + self.auth
        data = None
        if payload is not None:
            headers['Content-Type'] = 'application/json; charset=utf-8'
            data = json.dumps(payload, ensure_ascii=False).encode()
        for attempt in range(3 if payload is None else 1):
            try:
                req = urllib.request.Request(url, data=data, headers=headers)
                with self.opener.open(req, timeout=25) as response:
                    raw = response.read()
                    return (raw.decode('utf-8') if webpage else json.loads(raw)), response.headers
            except urllib.error.HTTPError as exc:
                # Never print response bodies: plugins may echo confidential fields.
                if payload is not None or exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise RuntimeError(f'WordPress HTTP {exc.code}; method {"POST" if payload else "GET"}') from None
            except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
                if payload is not None or attempt == 2:
                    raise RuntimeError(f'WordPress network failure; {"POST outcome UNKNOWN" if payload else "GET failed"}') from None
            time.sleep(attempt + 1)

    def get(self, path, public=False):
        return self.request(path, public=public)[0]

    def all(self, resource, **params):
        results, page = [], 1
        while True:
            query = urllib.parse.urlencode({**params, 'per_page': 100, 'page': page})
            rows, headers = self.request(resource + '?' + query, public=not self.auth)
            if not isinstance(rows, list):
                raise RuntimeError('WordPress collection is not an array')
            results.extend(rows)
            total_pages = int(headers.get('X-WP-TotalPages', page))
            if page >= total_pages:
                return results
            page += 1


def category_paths(cats):
    by_id = {c['id']: c for c in cats}
    paths = defaultdict(list)
    for cat in cats:
        parts, seen, cur, valid = [], set(), cat, True
        while cur:
            if cur['id'] in seen:
                valid = False
                break
            seen.add(cur['id'])
            parts.append(html.unescape(cur['name']).strip())
            parent = cur.get('parent', 0)
            if parent and parent not in by_id:
                valid = False
                break
            cur = by_id.get(parent)
        if valid:
            paths[' > '.join(reversed(parts))].append(cat['id'])
    # Duplicate ancestry is deliberately ambiguous, never last-entry-wins.
    return dict(paths)


def title_of(post):
    return html.unescape(post.get('title', {}).get('raw', post.get('title', {}).get('rendered', '')))


def duplicates(article, inventory):
    slug = article_slug(article)
    marker = f"wp-aiwriter:matrix_id={article['id']};"
    return [p for p in inventory if normalized(title_of(p)) == normalized(article['title'])
            or p['slug'] in (slug, slugify(article['title']))
            or marker in p.get('content', {}).get('raw', '')]


def git(*args, env=None, input_text=None):
    result = subprocess.run(['git', *args], cwd=ROOT, env=env, input=input_text,
                            text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError('Checkpoint Git operation failed: ' + args[0])
    return result.stdout.strip()


class Ledger:
    def __init__(self, persist_remote=False):
        self.data = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {'version': 1, 'posts': {}}
        self.remote = persist_remote
        self.expected_blob = git('rev-parse', 'HEAD:data/publication-state.json') if persist_remote and STATE_PATH.exists() else None

    def save(self):
        self.data['updated_at'] = now()
        STATE_PATH.parent.mkdir(exist_ok=True)
        STATE_PATH.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + '\n')
        if not self.remote:
            return
        # Commit only the ledger onto latest main, without resetting writer changes.
        for attempt in range(3):
            git('fetch', 'origin', 'main')
            base = git('rev-parse', 'origin/main')
            current = subprocess.run(['git', 'rev-parse', f'{base}:data/publication-state.json'], cwd=ROOT,
                                     capture_output=True, text=True)
            remote_blob = current.stdout.strip() if current.returncode == 0 else None
            if remote_blob != self.expected_blob:
                raise RuntimeError('Checkpoint changed outside this serialized publisher; reconcile before any POST')
            blob = git('hash-object', '-w', str(STATE_PATH))
            with tempfile.TemporaryDirectory() as tmp:
                env = {**os.environ, 'GIT_INDEX_FILE': str(pathlib.Path(tmp) / 'index')}
                git('read-tree', base, env=env)
                git('update-index', '--add', '--cacheinfo', f'100644,{blob},data/publication-state.json', env=env)
                tree = git('write-tree', env=env)
                commit = git('commit-tree', tree, '-p', base, input_text='chore: checkpoint WordPress publication\n')
            result = subprocess.run(['git', 'push', 'origin', f'{commit}:refs/heads/main'], cwd=ROOT,
                                    capture_output=True, text=True)
            if result.returncode == 0:
                self.expected_blob = blob
                return
        raise RuntimeError('Could not persist remote checkpoint; no further POST allowed')


def record(ledger, article, **fields):
    previous = ledger.data['posts'].get(str(article['id']), {})
    ledger.data['posts'][str(article['id'])] = {**previous, 'title': article['title'],
            'source_hash': article['hash'], 'checked_at': now(), **fields}
    ledger.save()


def verify(client, article, post_id, expected_status, category_id, slug):
    post = client.get(f'posts/{post_id}?context=edit')
    expected_html = markdown_to_html(article['body'])
    raw = post.get('content', {}).get('raw', '')
    marker = f"wp-aiwriter:matrix_id={article['id']};sha256={article['hash']}"
    if (post.get('status') != expected_status or post.get('slug') != slug
        or title_of(post) != article['title'] or marker not in raw
        or visible(raw) != visible(expected_html)
        or (category_id is not None and post.get('categories') != [category_id])):
        raise RuntimeError('Post-readback verification failed; preserve existing post and investigate')
    if expected_status == 'publish':
        public = client.get(f'posts/{post_id}', public=True)
        if (public.get('status') != 'publish' or public.get('categories') != [category_id]
            or visible(public.get('content', {}).get('rendered', '')) != visible(expected_html)):
            raise RuntimeError('Public REST verification failed')
        page, _ = client.request(post['link'], public=True, webpage=True)
        # The public page must contain the first substantive paragraph as well as the title.
        first = next((p for p in expected_html.split('\n') if p.startswith('<p>')), '')
        if visible(first) not in visible(page) or normalized(article['title']) not in visible(page):
            raise RuntimeError('Public permalink does not display expected title/content')
    return post


def sync(client, ready, ledger, limit, report, scope=None):
    client.get('users/me?context=edit&_fields=id')  # validate credentials before all writes
    paths = category_paths(client.all('categories', hide_empty='false', _fields='id,name,parent'))
    inventory = client.all('posts', context='edit', status='any', _fields='id,title,slug,status,link,categories,content')
    report['auth_ok'] = True
    report['site_published'] = sum(p['status'] == 'publish' for p in inventory)
    topics = matrix()
    report['excel_published_ids'] = [i for i, row in topics.items() if any(
        p['status'] == 'publish' and normalized(title_of(p)) == normalized(row['title']) for p in inventory)]
    attempts, created, eligible = 0, 0, []
    for article in ready:
        matches = duplicates(article, inventory)
        old = ledger.data['posts'].get(str(article['id']), {})
        if len(matches) > 1:
            report['duplicates'].append({'id': article['id'], 'wp_ids': [p['id'] for p in matches],
                                         'reason': 'Multiple matching WordPress posts; skipped for owner review'})
            continue
        if matches:
            post = matches[0]
            marker = f"wp-aiwriter:matrix_id={article['id']};"
            if marker in post.get('content', {}).get('raw', '') and old.get('phase') in ('POST_INTENT', 'VERIFY_PENDING'):
                try:
                    verified = verify(client, article, post['id'], old['expected_status'], old.get('category_id'), old['slug'])
                    record(ledger, article, phase='VERIFIED', wp_id=verified['id'], status=verified['status'], url=verified['link'])
                except RuntimeError as exc:
                    report['errors'].append({'id': article['id'], 'reason': str(exc)})
            report['existing'].append({'id': article['id'], 'wp_id': post['id'], 'status': post['status'], 'url': post['link']})
            continue
        if old.get('phase') in ('POST_INTENT', 'VERIFY_PENDING', 'VERIFIED'):
            # An interrupted POST may still complete, or a user may have removed the post.
            # Absence is never authorization to issue a second POST automatically.
            report['errors'].append({'id': article['id'], 'reason': 'Unresolved prior POST; reconcile ledger instead of reposting'})
            continue
        eligible.append(article)
    remaining = []
    published_links = {p.get('link', '').rstrip('/') for p in inventory if p['status'] == 'publish'}
    for article in eligible:
        if attempts >= limit:
            remaining.append(article['id'])
            continue
        attempts += 1
        try:
            internal = re.findall(r'\]\((https://blog\.rentbikehanoi\.com[^\s)]*)\)', article['body'])
            if any(url.rstrip('/') not in published_links for url in internal):
                raise ValueError('Internal link is not a verified published post URL')
            # Full ancestry must resolve uniquely; do not infer a similarly named leaf.
            ids = paths.get(article['category'], [])
            category_id = ids[0] if len(ids) == 1 else None
            status = 'publish' if category_id is not None else 'draft'
            reason = None if category_id else 'Missing or ambiguous full Excel category ancestry'
            slug = article_slug(article)
            payload = {'title': article['title'], 'slug': slug, 'status': status,
                       'content': f"<!-- wp-aiwriter:matrix_id={article['id']};sha256={article['hash']} -->\n" + markdown_to_html(article['body'])}
            if category_id is not None:
                payload['categories'] = [category_id]
            # Durable write-ahead intent: a crash, timeout, or verification error never causes blind POST retry.
            record(ledger, article, phase='POST_INTENT', expected_status=status,
                   category_id=category_id, slug=slug, reason=reason)
            result = client.request('posts', payload=payload)[0]  # exactly one attempt
            record(ledger, article, phase='VERIFY_PENDING', wp_id=result['id'])
            post = verify(client, article, result['id'], status, category_id, slug)
            record(ledger, article, phase='VERIFIED', wp_id=post['id'], status=post['status'], url=post['link'])
            inventory.append(post)
            report['created'].append({'id': article['id'], 'wp_id': post['id'], 'status': status,
                                      'category_id': category_id, 'url': post['link'], 'reason': reason})
            created += 1
        except (RuntimeError, ValueError, KeyError) as exc:
            report['errors'].append({'id': article['id'], 'reason': str(exc)})
            # Git persistence errors must halt before another potentially uncheckpointed write.
            if 'Checkpoint' in str(exc) or 'checkpoint' in str(exc):
                raise
    report['created_count'] = created
    report['remaining_ready_ids'] = remaining
    report['has_more'] = bool(remaining)
    report['site_published'] += sum(x['status'] == 'publish' for x in report['created'])
    report['excel_published_ids'] += [x['id'] for x in report['created'] if x['status'] == 'publish']
    if scope is not None:
        expected_ids = range(scope['first_id'], scope['last_id'] + 1)
        matched_term = paths.get(scope['category'], [])
        term_id = matched_term[0] if len(matched_term) == 1 else None
        complete, wrong_category, drafts, duplicates_in_category = [], [], [], []
        missing_posts = []
        for i in expected_ids:
            matched = duplicates(topics[i], inventory)
            if len(matched) > 1:
                duplicates_in_category.append({'id': i, 'wp_ids': [p['id'] for p in matched]})
            elif len(matched) == 1:
                p = matched[0]
                if p['status'] == 'publish' and term_id is not None and p['categories'] == [term_id]:
                    complete.append(i)
                elif p['status'] == 'publish':
                    wrong_category.append({'id': i, 'wp_id': p['id'], 'categories': p['categories'],
                                           'expected_category_id': term_id})
                else:
                    drafts.append({'id': i, 'wp_id': p['id'], 'status': p['status']})
            else:
                missing_posts.append(i)
        source_ids = {article['id'] for article in ready}
        authored_ids = [i for i in expected_ids if i in source_ids]
        report['category_progress'] = {
            **scope, 'expected_wordpress_category_id': term_id,
            'published_correct_category': len(complete), 'published_ids': complete,
            'source_ready': len(authored_ids),
            'source_missing_ids': [i for i in expected_ids if i not in source_ids],
            'unpublished_ids': missing_posts, 'wrong_category': wrong_category,
            'draft_or_pending': drafts, 'duplicate_wp_titles': duplicates_in_category,
        }
        report['category_complete'] = len(complete) == scope['total']
        report['category_review_required'] = (report['category_complete']
                                              or bool(wrong_category) or bool(duplicates_in_category))


def write_report(report):
    directory = ROOT / 'reports'
    directory.mkdir(exist_ok=True)
    (directory / 'latest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    summary = (f"### WP AIWriter — {report['mode']}\n\n"
               f"- Authored: {report['authored']}; QA PASS: {report['qa_pass']}; QA FAIL: {len(report['qa_errors'])}\n"
               f"- WordPress auth verified: {report.get('auth_ok', False)}\n"
               f"- Newly created and verified: {len(report['created'])}\n"
               f"- Site published: {report.get('site_published', 'UNVERIFIED')}\n"
               f"- Excel #146–500 published: {len(report['excel_published_ids']) if 'excel_published_ids' in report else 'UNVERIFIED'}\n"
               f"- Duplicate groups requiring review: {len(report['duplicates'])}; errors: {len(report['errors'])}; "
               f"next ready: {report.get('remaining_ready_ids', [])[:5]}\n")
    if report.get('category_boundary') and not report.get('category_progress'):
        cat = report['category_boundary']
        summary += (f"\n#### Approved Excel category: {cat['category']} — #{cat['first_id']}–#{cat['last_id']}\n"
                    f"- QA-ready in the current group: {cat['total'] - len(report.get('source_queue', []))}/{cat['total']}\n"
                    f"- Writer queue, still missing or failing QA: {report.get('source_queue', [])}\n"
                    f"- Next category (blocked): {cat['next_category']}\n")
    if report.get('category_progress'):
        cat = report['category_progress']
        summary += (f"\n#### Excel category: {cat['category']} — #{cat['first_id']}–{cat['last_id']}\n"
                    f"- Correctly published in child category: {cat['published_correct_category']}/{cat['total']}\n"
                    f"- Source articles QA-ready: {cat['source_ready']}/{cat['total']}; "
                    f"unwritten/unready IDs: {cat['source_missing_ids'][:30]}\n"
                    f"- Wrong category: {len(cat['wrong_category'])}; drafts: {len(cat['draft_or_pending'])}; "
                    f"duplicate live titles: {len(cat['duplicate_wp_titles'])}\n"
                    f"- Category complete, requires owner review before advancing: {report.get('category_complete', False)}\n"
                    f"- Next Excel category: {cat['next_category']}\n")
        if cat['wrong_category'] or cat['draft_or_pending'] or cat['duplicate_wp_titles']:
            summary += '\nCategory issues:\n```json\n' + json.dumps({
                'wrong_category': cat['wrong_category'],
                'draft_or_pending': cat['draft_or_pending'],
                'duplicate_wp_titles': cat['duplicate_wp_titles'],
            }, ensure_ascii=False, indent=2) + '\n```\n'
    for key in ['created', 'existing', 'duplicates', 'errors', 'qa_errors']:
        if report[key]:
            summary += '\n' + key + ':\n```json\n' + json.dumps(report[key], ensure_ascii=False, indent=2) + '\n```\n'
    (directory / 'summary.md').write_text(summary)
    print(summary)
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as out:
            out.write(summary)
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
            for key in ['has_more', 'auth_ok', 'category_complete']:
                out.write(f'{key}={str(report.get(key, False)).lower()}\n')
            if report.get('category_complete'):
                cat = report['category_progress']
                out.write(f"category_first_id={cat['first_id']}\n")
                out.write(f"category_last_id={cat['last_id']}\n")


def run(args):
    topics = matrix()
    all_items, ready, errors = load_posts(topics)
    report = {'at': now(), 'mode': args.mode, 'live': args.live, 'authored': len(all_items),
              'qa_pass': len(ready), 'qa_errors': errors, 'created': [], 'existing': [], 'duplicates': [], 'errors': [], 'has_more': False}
    try:
        scope = publication_scope(topics)
        report['category_boundary'] = scope
        approved = [a for a in ready if scope['first_id'] <= a['id'] <= scope['last_id']
                    and a['category'] == scope['category']]
        report['blocked_other_categories'] = len(ready) - len(approved)
        report['source_queue'] = [i for i in range(scope['first_id'], scope['last_id'] + 1)
                                  if i not in {a['id'] for a in approved}]
        if args.mode == 'sync':
            if not args.live:
                report['remaining_ready_ids'] = [x['id'] for x in approved]
                report['notice'] = 'DRY RUN — no WordPress authentication or writes'
            else:
                if errors:
                    raise ValueError('QA errors present; publishing aborted with zero new WordPress writes')
                user, password = os.getenv('WP_USERNAME'), os.getenv('WP_APPLICATION_PASSWORD')
                if not user or not password:
                    raise RuntimeError('BLOCKED: missing WP_USERNAME / WP_APPLICATION_PASSWORD GitHub Secrets; zero WordPress writes')
                ledger = Ledger(args.persist_state)
                sync(WPClient(user, password), approved, ledger, args.limit, report, scope=scope)
    except (RuntimeError, ValueError) as exc:
        report['errors'].append({'reason': str(exc)})
    finally:
        write_report(report)
    return 1 if errors or report['errors'] else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['qa', 'sync'], default='qa')
    parser.add_argument('--limit', type=int, choices=[1, 2, 3, 4, 5], default=3)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--persist-state', action='store_true')
    args = parser.parse_args()
    sys.exit(run(args))
