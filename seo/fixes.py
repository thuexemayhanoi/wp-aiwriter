"""Phase 8: Safe Fix → Test → Approval → Apply → Verify → Rollback.

Only fixes listed in data/seo/approved-fixes.json with approval fields are considered.
``validate`` (default) uses public data and never writes. ``apply`` needs an explicit
confirmation flag plus WordPress credentials, handles ONE supported fix type
(insert_internal_link), backs up the raw post content first, checks optimistic concurrency
(modified_gmt), verifies the result and records a rollback point. ``rollback`` restores a
backup only if nobody edited the post after the fix.
"""
import base64
import html as html_lib
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from . import common
from .common import iso, normalize_url, read_json, read_jsonl, write_json

SUPPORTED = {'insert_internal_link'}
REQUIRED = ('id', 'type', 'post_id', 'target_url', 'anchor_text', 'expected_modified_gmt', 'approved_by', 'approved_at')
TOKEN = re.compile(r'(<!--.*?-->|<[^>]+>)', re.S)
TAG_NAME = re.compile(r'^</?\s*([a-zA-Z0-9]+)')
BLOCKED_CONTEXT = {'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'script', 'style', 'code', 'pre', 'button', 'title'}


def approved_path():
    return common.path('data/seo/approved-fixes.json')


def applied_path():
    return common.path('data/seo/applied-fixes.json')


def anchor_pattern(anchor):
    words = [re.escape(html_lib.escape(w, quote=False)) for w in anchor.split()]
    return re.compile(r'(?<![\w])' + r'\s+'.join(words) + r'(?![\w])')


def find_occurrences(markup, anchor):
    """Occurrences of anchor inside a single text node that is not in a link/heading/code."""
    pattern = anchor_pattern(anchor)
    parts = TOKEN.split(markup or '')
    stack = []
    hits = []
    offset = 0
    for part in parts:
        if part.startswith('<!--'):
            pass
        elif part.startswith('<'):
            m = TAG_NAME.match(part)
            name = m.group(1).lower() if m else ''
            if part.startswith('</'):
                if name in stack:
                    while stack and stack.pop() != name:
                        pass
            elif name in BLOCKED_CONTEXT and not part.endswith('/>'):
                stack.append(name)
        elif not stack:
            for found in pattern.finditer(part):
                hits.append((offset + found.start(), offset + found.end()))
        offset += len(part)
    return hits


def insert_link(markup, anchor, target_url):
    hits = find_occurrences(markup, anchor)
    if len(hits) != 1:
        raise ValueError(f'anchor must occur exactly once in linkable text; found {len(hits)}')
    start, end = hits[0]
    href = html_lib.escape(target_url, quote=True)
    return markup[:start] + f'<a href="{href}">' + markup[start:end] + '</a>' + markup[end:]


def links_to(markup, target_url):
    target = normalize_url(target_url).rstrip('/')
    for href in re.findall(r'<a\s[^>]*href="([^"]+)"', markup or '', re.I):
        if normalize_url(html_lib.unescape(href)).rstrip('/') == target:
            return True
    return False


def load_fixes():
    data = read_json(approved_path(), {'fixes': []}) or {'fixes': []}
    return data.get('fixes', [])


def static_checks(fix, cfg, index_by_url):
    problems = [f'missing field {k}' for k in REQUIRED if not fix.get(k)]
    if fix.get('type') not in SUPPORTED:
        problems.append(f"unsupported type {fix.get('type')!r}; supported: {sorted(SUPPORTED)}")
    if str(fix.get('status', 'approved')).lower() != 'approved':
        problems.append('status is not "approved"')
    target = normalize_url(fix.get('target_url', ''))
    if not target or not common.is_internal(target, cfg) or not target.startswith('https://'):
        problems.append('target_url must be an https URL on the audited site')
    elif target not in index_by_url and target.rstrip('/') + '/' not in index_by_url:
        problems.append('target_url is not a published post/page in data/posts-index.jsonl')
    anchor = (fix.get('anchor_text') or '').strip()
    if anchor and (len(anchor) < 3 or len(anchor.split()) > 12):
        problems.append('anchor_text must be 3 chars to 12 words')
    return problems


def require_trusted_operator(fix=None):
    """Production writes are owner-only; a free-form approved_by field is not authorization."""
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        return  # Unit tests use a fake WordPress; CI is the production entry point.
    actor = os.environ.get('GITHUB_ACTOR')
    owner = os.environ.get('GITHUB_REPOSITORY_OWNER')
    branch = os.environ.get('GITHUB_REF_NAME')
    if not actor or not owner or actor != owner or branch != 'main':
        raise RuntimeError('BLOCKED: only repository owner may write WordPress from main')
    if fix is not None and fix.get('approved_by') != actor:
        raise RuntimeError('BLOCKED: approved_by must exactly match the authenticated GitHub owner')


def persist_prewrite_backup(backup_file):
    """Push the backup and write-ahead receipt BEFORE any WordPress POST.

    If GitHub cannot persist the safety checkpoint, abort without changing WordPress.
    A crash after the POST leaves APPLY_INTENT on the remote branch and prohibits blind retry.
    """
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        return
    relative = str(backup_file.relative_to(common.root()))
    for command in (
        ['git', 'add', '--', relative, 'data/seo/applied-fixes.json'],
        ['git', 'commit', '-m', 'chore(seo): durable pre-write backup and intent [skip ci]'],
        ['git', 'push', 'origin', 'HEAD:main'],
    ):
        result = subprocess.run(command, cwd=common.root(), capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError('BLOCKED: could not persist pre-write backup on GitHub; WordPress unchanged: '
                               + (result.stderr or result.stdout)[-300:])


class WordPress:
    """Minimal REST client for the fix pipeline (the only code path that may write)."""

    def __init__(self, cfg, user=None, password=None, opener=None):
        self.cfg = cfg
        self.auth = base64.b64encode(f'{user}:{password}'.encode()).decode() if user else None
        self.opener = opener or urllib.request.build_opener(_NoRedirect())

    def _url(self, route):
        url = self.cfg['site_url'].rstrip('/') + '/wp-json/' + route
        if not common.is_internal(url, self.cfg):
            raise ValueError('refusing non-site URL')
        return url

    def call(self, route, payload=None, auth=True):
        headers = {'Accept': 'application/json', 'User-Agent': self.cfg['user_agent']}
        if auth:
            if not self.auth:
                raise RuntimeError('credentials required')
            headers['Authorization'] = 'Basic ' + self.auth
        data = None
        if payload is not None:
            headers['Content-Type'] = 'application/json; charset=utf-8'
            data = json.dumps(payload, ensure_ascii=False).encode()
        req = urllib.request.Request(self._url(route), data=data, headers=headers,
                                     method='POST' if payload is not None else 'GET')
        try:
            with self.opener.open(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f'WordPress HTTP {exc.code} ({"POST" if payload is not None else "GET"})') from None
        except (urllib.error.URLError, OSError):
            raise RuntimeError('WordPress network failure; ' +
                               ('POST outcome UNKNOWN — verify manually before retrying' if payload is not None else 'GET failed')) from None

    def public_post(self, post_id):
        return self.call(f'wp/v2/posts/{int(post_id)}?_fields=id,modified_gmt,link,status,content', auth=False)

    def raw_post(self, post_id):
        return self.call(f'wp/v2/posts/{int(post_id)}?context=edit&_fields=id,modified_gmt,link,status,slug,content')

    def update_content(self, post_id, content):
        return self.call(f'wp/v2/posts/{int(post_id)}', payload={'content': content})


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate(cfg, wp, fixes=None):
    index_by_url = {r['url']: r for r in read_jsonl(common.path('data/posts-index.jsonl'))}
    applied = read_json(applied_path(), {'fixes': {}}) or {'fixes': {}}
    results = []
    for fix in (fixes if fixes is not None else load_fixes()):
        res = {'id': fix.get('id'), 'post_id': fix.get('post_id'), 'type': fix.get('type'), 'checked_at': iso()}
        problems = static_checks(fix, cfg, index_by_url)
        if (applied['fixes'].get(fix.get('id')) or {}).get('phase') in ('VERIFIED', 'APPLY_INTENT', 'POST_SENT'):
            problems.append(f"already processed: {applied['fixes'][fix['id']]['phase']}")
        if not problems:
            try:
                post = wp.public_post(fix['post_id'])
                rendered = (post.get('content') or {}).get('rendered', '')
                if post.get('status') != 'publish':
                    problems.append('source post is not published')
                if post.get('modified_gmt') != fix['expected_modified_gmt']:
                    problems.append(f"post changed since approval: modified_gmt={post.get('modified_gmt')}")
                if links_to(rendered, fix['target_url']):
                    problems.append('source already links to target')
                hits = find_occurrences(rendered, fix['anchor_text'])
                if len(hits) != 1:
                    problems.append(f'anchor found {len(hits)} times in linkable text (need exactly 1)')
                if normalize_url(post.get('link', '')).rstrip('/') == normalize_url(fix['target_url']).rstrip('/'):
                    problems.append('target is the source itself')
            except RuntimeError as exc:
                problems.append(str(exc))
        res['status'] = 'VALID' if not problems else 'INVALID'
        res['problems'] = problems
        results.append(res)
    return results


def apply(cfg, wp, max_fixes=1, confirm=False):
    if not confirm:
        raise RuntimeError('apply requires explicit confirmation (SEO_APPLY_CONFIRM=yes)')
    applied = read_json(applied_path(), {'fixes': {}}) or {'fixes': {}}
    fixes = {f.get('id'): f for f in load_fixes()}
    results = []
    require_trusted_operator()
    for res in validate(cfg, wp):
        if res['status'] != 'VALID':
            results.append({**res, 'applied': False, 'reason': 'validation_failed'})
            continue
        if len([r for r in results if r.get('applied')]) >= max_fixes:
            results.append({**res, 'applied': False, 'reason': 'max_fixes_limit'})
            continue
        fix = fixes[res['id']]
        require_trusted_operator(fix)
        entry = {'post_id': fix['post_id'], 'target_url': fix['target_url'], 'anchor_text': fix['anchor_text'],
                 'approved_by': fix['approved_by'], 'approved_at': fix['approved_at']}
        try:
            raw_post = wp.raw_post(fix['post_id'])
            before = (raw_post.get('content') or {}).get('raw', '')
            if raw_post.get('modified_gmt') != fix['expected_modified_gmt']:
                raise RuntimeError('post changed since approval (raw check)')
            after = insert_link(before, fix['anchor_text'], fix['target_url'])
            backup = {'fix_id': fix['id'], 'post_id': fix['post_id'], 'link': raw_post.get('link'),
                      'slug': raw_post.get('slug'), 'modified_gmt_before': raw_post.get('modified_gmt'),
                      'content_raw_before': before, 'saved_at': iso()}
            backup_file = common.path(f"data/seo/backups/{fix['id']}-post{fix['post_id']}.json")
            write_json(backup_file, backup)
            entry.update({'phase': 'APPLY_INTENT', 'backup': str(backup_file.relative_to(common.root())), 'at': iso()})
            applied['fixes'][fix['id']] = entry
            write_json(applied_path(), applied)
            # The backup and intent must be visible remotely before the REST update.
            persist_prewrite_backup(backup_file)
            entry['phase'] = 'POST_SENT'
            write_json(applied_path(), applied)
            wp.update_content(fix['post_id'], after)
            check = wp.raw_post(fix['post_id'])
            raw_after = (check.get('content') or {}).get('raw', '')
            public = wp.public_post(fix['post_id'])
            if (raw_after != after or check.get('slug') != raw_post.get('slug') or check.get('link') != raw_post.get('link')
                    or check.get('status') != raw_post.get('status')
                    or not links_to((public.get('content') or {}).get('rendered', ''), fix['target_url'])):
                raise RuntimeError('post-apply verification failed; use rollback after manual review')
            entry.update({'phase': 'VERIFIED', 'modified_gmt_after': check.get('modified_gmt'), 'verified_at': iso()})
            write_json(applied_path(), applied)
            entry['markdown_mirror'] = mirror_markdown(fix, raw_post)
            write_json(applied_path(), applied)
            results.append({**res, 'applied': True, 'phase': 'VERIFIED'})
        except (RuntimeError, ValueError) as exc:
            if fix['id'] in applied['fixes']:
                applied['fixes'][fix['id']]['error'] = str(exc)
                write_json(applied_path(), applied)
            results.append({**res, 'applied': False, 'error': str(exc)})
            break  # stop the batch on the first failure
    return results


def rollback(cfg, wp, fix_id, confirm=False):
    if not confirm:
        raise RuntimeError('rollback requires explicit confirmation (SEO_APPLY_CONFIRM=yes)')
    applied = read_json(applied_path(), {'fixes': {}}) or {'fixes': {}}
    require_trusted_operator()
    entry = applied['fixes'].get(fix_id)
    if not entry or not entry.get('backup'):
        raise RuntimeError(f'no backup recorded for {fix_id}')
    # NEVER roll back an uncertain/unfinished POST; a concurrent edit could be lost.
    if entry.get('phase') != 'VERIFIED' or not entry.get('modified_gmt_after'):
        raise RuntimeError('BLOCKED: prior write not fully verified; reconcile manually before rollback')
    backup = read_json(common.root() / entry['backup'])
    if (backup.get('fix_id') != fix_id or backup.get('post_id') != entry['post_id']):
        raise RuntimeError('BLOCKED: rollback backup identity mismatch')
    current = wp.raw_post(entry['post_id'])
    if (current.get('status') != 'publish'
            or current.get('slug') != backup.get('slug')
            or current.get('link') != backup.get('link')):
        raise RuntimeError('BLOCKED: source URL, slug or publication status changed')
    if current.get('modified_gmt') != entry['modified_gmt_after']:
        raise RuntimeError('post edited after the fix; manual rollback required to avoid overwriting newer edits')
    wp.update_content(entry['post_id'], backup['content_raw_before'])
    check = wp.raw_post(entry['post_id'])
    if (check.get('content') or {}).get('raw', '') != backup['content_raw_before']:
        raise RuntimeError('rollback verification failed')
    entry.update({'phase': 'ROLLED_BACK', 'rolled_back_at': iso()})
    write_json(applied_path(), applied)
    return entry


def mirror_markdown(fix, raw_post):
    """Keep posts/NNNN.md (GitHub source of truth) consistent with the WordPress edit."""
    marker = re.search(r'wp-aiwriter:matrix_id=(\d+)', (raw_post.get('content') or {}).get('raw', ''))
    if not marker:
        return 'no matrix marker; mirror manually'
    md_path = common.path(f'posts/{int(marker.group(1)):04}.md')
    if not md_path.exists():
        return f'{md_path.name} not found; mirror manually'
    text = md_path.read_text(encoding='utf-8')
    head, sep, body = text.partition('\n---\n')
    if not sep:
        return 'unexpected front matter; mirror manually'
    pattern = re.compile(r'(?<![\w\[])' + r'\s+'.join(re.escape(w) for w in fix['anchor_text'].split()) + r'(?![\w\]])')
    hits = []
    for m in pattern.finditer(body):
        line_start = body.rfind('\n', 0, m.start()) + 1
        line = body[line_start:body.find('\n', m.end()) if body.find('\n', m.end()) != -1 else len(body)]
        inside_link = body.rfind('[', line_start, m.start()) > body.rfind(']', line_start, m.start())
        if not line.lstrip().startswith('#') and not inside_link:
            hits.append(m)
    if len(hits) != 1:
        return f'anchor found {len(hits)} times in Markdown; mirror manually'
    m = hits[0]
    body = body[:m.start()] + f"[{m.group(0)}]({fix['target_url']})" + body[m.end():]
    md_path.write_text(head + sep + body, encoding='utf-8')
    return f'updated {md_path.name}'


def credentials():
    return os.environ.get('WP_USERNAME') or os.environ.get('WP_USER'), os.environ.get('WP_APPLICATION_PASSWORD')
