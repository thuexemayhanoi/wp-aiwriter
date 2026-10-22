"""One-time owner-approved cleanup of internal links pointing to migrated VI slugs.

Only previously VERIFIED Excel VI posts are eligible. The site has already
migrated their slugs on WordPress, with WordPress _wp_old_slug redirects.
The script never creates a post, changes a slug, touches EN or edits GitHub
publication receipts. All mutation is through WordPress's posts REST route
(with revisions/cache hooks), never SQL. Safe to resume after an uncertain
batch response: each retry reads the live content first and applies only
remaining original URL strings.
"""
import argparse
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import engine

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / 'data/publication-state.json'
REPORT_PATH = ROOT / 'reports/vi-excel-url-cleanup.json'
OLD_RE = re.compile(r'https://blog\.rentbikehanoi\.com/excel-[0-9]+-[a-z0-9-]+/')
BATCH_LIMIT = 5


def migrations(ledger, site=engine.WP_URL):
    if site != 'https://blog.rentbikehanoi.com':
        raise RuntimeError('Incorrect destination WordPress site')
    mapping, expected, seen = {}, {}, set()
    for topic_id, rec in ledger['posts'].items():
        slug = rec.get('slug', '')
        if not re.fullmatch(r'excel-([0-9]+)-[a-z0-9-]+', slug):
            continue
        if int(slug.split('-')[1]) != int(topic_id):
            raise RuntimeError('Matrix ID disagrees with old slug')
        if rec.get('phase') != 'VERIFIED' or rec.get('status') != 'publish':
            raise RuntimeError('Migration requires a VERIFIED public post')
        post_id = rec.get('wp_id')
        if not isinstance(post_id, int) or post_id in seen:
            raise RuntimeError('Duplicate/missing VI WordPress ID')
        old = site + '/' + slug + '/'
        if rec.get('url') != old:
            raise RuntimeError('Existing ledger URL inconsistent with original slug')
        new_slug = re.sub(r'^excel-[0-9]+-', '', slug)
        mapping[old] = site + '/' + new_slug + '/'
        expected[post_id] = new_slug
        seen.add(post_id)
    if len(expected) != 333:
        raise RuntimeError(f'Expected 333 verified VI migrations, got {len(expected)}; refuse writes')
    return mapping, expected


def rewrite_known_links(content, mapping):
    unknown = sorted(set(OLD_RE.findall(content)) - set(mapping))
    if unknown:
        raise RuntimeError(f'Unregistered VI legacy link in post body: {unknown[0][:140]}')
    updated, replacements = content, 0
    for old, new in mapping.items():
        count = updated.count(old)
        if count:
            updated = updated.replace(old, new)
            replacements += count
    return updated, replacements


def get_live_posts(client, expected):
    results = {}
    ids = sorted(expected)
    for start in range(0, len(ids), 20):
        subset = ids[start:start+20]
        query = urllib.parse.urlencode({
            'context':'edit','status':'publish','include':','.join(map(str, subset)),
            'per_page':len(subset),'_fields':'id,slug,status,content'})
        rows = client.get('posts?' + query)
        if not isinstance(rows, list) or {p['id'] for p in rows} != set(subset):
            raise RuntimeError('WordPress live readback incomplete; no changes made')
        for post in rows:
            ident = post['id']
            if post.get('status') != 'publish' or post.get('slug') != expected[ident]:
                raise RuntimeError(f'WordPress VI post {ident} has unexpected status or migrated slug')
            raw = post.get('content',{}).get('raw')
            if not isinstance(raw, str):
                raise RuntimeError(f'Raw WordPress HTML unavailable for {ident}')
            results[ident] = raw
    return results


def post_batch(client, updates, site=engine.WP_URL):
    """Use standard WordPress post updates: one safe, non-retried REST write each.

    Some site middleware refuses WordPress /batch/v1 for large post_content.
    The regular core posts/{id} endpoint saves a revision and invalidates
    caches. If a write response is uncertain, STOP; a rerun reads live
    content and skips already-replaced strings, so it is idempotent.
    """
    applied = 0
    for post_id, updated in updates:
        post = client.request(
            f'posts/{post_id}?_fields=id,slug,status',
            payload={'content': updated})[0]
        if (post.get('id') != post_id or
            post.get('status') != 'publish' or
            not isinstance(post.get('slug'), str) or
            post['slug'].startswith('excel-')):
            raise RuntimeError(f'WordPress readback for {post_id} requires manual review')
        applied += 1
    return applied


def execute(dry_run=False):
    ledger = json.loads(LEDGER_PATH.read_text(encoding='utf-8'))
    mapping, expected = migrations(ledger)
    user = os.environ.get('WP_USERNAME') or os.environ.get('WP_USER')
    password = os.environ.get('WP_APPLICATION_PASSWORD')
    if not user or not password:
        raise RuntimeError('Existing WordPress publisher credentials unavailable')
    client = engine.WPClient(user, password)
    client.get('users/me?context=edit&_fields=id')
    before = get_live_posts(client, expected)
    edits = []
    replacements = 0
    for post_id, body in before.items():
        updated, count = rewrite_known_links(body, mapping)
        if count:
            edits.append((post_id, updated))
            replacements += count
    result = {'mode':'dry-run' if dry_run else 'apply',
              'verified_legacy_slugs':len(mapping), 'posts_with_old_links':len(edits),
              'old_link_occurrences':replacements, 'posts_updated':0,
              'link_replacements_applied':0}
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(result,indent=2)+'\n', encoding='utf-8')
    print('PREFLIGHT '+json.dumps(result))
    if dry_run or not edits:
        return result
    for n in range(0, len(edits), BATCH_LIMIT):
        group = edits[n:n+BATCH_LIMIT]
        count = post_batch(client, group)
        result['posts_updated'] += count
        result['link_replacements_applied'] += sum(
            before[pid].count(old)
            for pid,_ in group for old in mapping)
        REPORT_PATH.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print('PROGRESS '+str(result['posts_updated'])+'/'+str(len(edits)), flush=True)
        time.sleep(2)
    # Read back all migrated VI posts once more and require zero stale Excel links.
    after = get_live_posts(client, expected)
    remaining = sum(len(OLD_RE.findall(s)) for s in after.values())
    result['remaining_legacy_links'] = remaining
    REPORT_PATH.write_text(json.dumps(result,indent=2)+'\n', encoding='utf-8')
    if remaining:
        raise RuntimeError(f'{remaining} old VI links remain; verify before retrying')
    print('VI_LINK_CLEANUP_VERIFIED '+json.dumps(result))
    return result


def main():
    arg = argparse.ArgumentParser()
    mode = arg.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = arg.parse_args()
    execute(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
