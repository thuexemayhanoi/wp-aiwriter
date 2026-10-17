#!/usr/bin/env python3
"""SEO Protection: keep the SEO that is already working safe from accidental or silent change.

  python scripts/seo_protection.py --mode repo         # offline guard: ledger, sources and baseline invariants
  python scripts/seo_protection.py --mode baseline     # live: record the accepted state (append-only)
  python scripts/seo_protection.py --mode check        # live: compare the site with the baseline, alert on drift
  python scripts/seo_protection.py --mode baseline --accept 950,951 --reason "approved title fix"

Read-only against WordPress (public REST + public pages). The baseline is append-only: existing entries are
never overwritten except by an explicit, reasoned --accept that is also recorded in the allowlist file.
Exit codes: 0 clean, 1 drift/violation, 2 no baseline yet, 3 the live site could not be read.
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seo_audit as audit  # noqa: E402  (shares the robots/sitemap parsers)
import seo_common as sc  # noqa: E402

BASELINE_PATH = sc.DATA_DIR / 'protection-baseline.json'
ALLOWLIST_PATH = sc.DATA_DIR / 'protection-allowlist.json'
SITEMAP_DROP = 0.8   # alert when the sitemap shrinks below 80% of the baselined URL count
CONTENT_DRIFT_PCT = 10


# ================================================================ repo guard (offline) ==============================
def repo_guard(ledger, ready, topics, baseline=None):
    """Immutability invariants for everything already published. Returns a list of findings."""
    out = []
    by_id = {a['id']: a for a in ready}
    seen = {'wp_id': {}, 'url': {}, 'slug': {}}
    cat_ids = collections.defaultdict(set)
    for key, entry in sorted(ledger.items(), key=lambda kv: int(kv[0])):
        if entry.get('phase') != 'VERIFIED':
            out.append(sc.finding('ledger_unverified', 'high', f'#{key} is {entry.get("phase")} in the ledger', id=int(key)))
            continue
        i = int(key)
        art = by_id.get(i)
        if art is None:
            out.append(sc.finding('published_source_missing', 'critical',
                                  f'#{key} is published but posts/{i:04}.md is missing or no longer passes QA', id=i))
        else:
            if art['hash'] != entry.get('source_hash'):
                out.append(sc.finding('published_source_edited', 'critical',
                                      f'#{key}: posts/{i:04}.md differs from the content that was published '
                                      '(published posts are create-only; do not rewrite them)', id=i))
            if art['title'] != entry.get('title'):
                out.append(sc.finding('title_drift', 'critical', f'#{key}: title differs from the ledger', id=i))
            if engine_slug(art) != entry.get('slug'):
                out.append(sc.finding('slug_drift', 'critical', f'#{key}: slug differs from the published slug', id=i))
        if entry.get('status') != 'publish':
            out.append(sc.finding('not_published', 'high', f'#{key} is VERIFIED but status={entry.get("status")}', id=i))
        url = entry.get('url', '')
        if entry.get('slug') and entry['slug'] not in url:
            out.append(sc.finding('url_slug_mismatch', 'critical', f'#{key}: URL does not contain its slug', id=i))
        for field, value in (('wp_id', entry.get('wp_id')), ('url', sc.norm_url(url) if url else None),
                             ('slug', entry.get('slug'))):
            if value is None:
                continue
            if value in seen[field]:
                out.append(sc.finding(f'duplicate_{field}', 'critical',
                                      f'#{key} and #{seen[field][value]} share {field} {value}', ids=[i, seen[field][value]]))
            seen[field][value] = i
        if i in topics:
            cat_ids[topics[i]['category']].add(entry.get('category_id'))
    for category, ids in cat_ids.items():
        if len(ids) > 1:
            out.append(sc.finding('category_inconsistent', 'critical',
                                  f'{category} maps to several WordPress categories: {sorted(map(str, ids))}'))
    if baseline:
        for key, entry in baseline.get('entries', {}).items():
            ledger_entry = ledger.get(key)
            if ledger_entry and ledger_entry.get('url') and sc.norm_url(ledger_entry['url']) != sc.norm_url(entry['url']):
                out.append(sc.finding('baseline_url_mismatch', 'critical',
                                      f'#{key}: ledger URL {ledger_entry["url"]} != baseline {entry["url"]}', id=int(key)))
    return out


def engine_slug(article):
    return sc.engine.article_slug(article)


# ================================================================ live snapshot =====================================
def live_snapshot(site=sc.SITE, workers=6, max_pages=0):
    posts = sc.wp_list('posts', 'id,link,slug,title,status,categories,modified_gmt,content', site)
    pages = sc.wp_list('pages', 'id,link,slug,title,status,modified_gmt,content', site)
    rows = [('post', r) for r in posts] + [('page', r) for r in pages]
    if max_pages:
        rows = rows[:max_pages]
    replies = sc.fetch_many([r['link'] for _, r in rows], workers=workers)
    entries = {}
    for kind, row in rows:
        reply = replies[row['link']]
        info = sc.parse_page(reply.text) if reply.status == 200 else {}
        text = sc.engine.visible(row.get('content', {}).get('rendered', ''))
        entries[str(row['id'])] = {
            'type': kind, 'url': row['link'], 'slug': row.get('slug', ''),
            'title': sc.engine.title_of({'title': row.get('title', {})}), 'categories': row.get('categories', []),
            'http_status': reply.status, 'final_url': reply.final_url,
            'canonical': info.get('canonical', ''), 'robots': info.get('robots', ''),
            'noindex': 'noindex' in info.get('robots', '') or 'noindex' in reply.headers.get('x-robots-tag', '').lower(),
            'h1': info.get('h1_text', ''), 'jsonld_types': info.get('jsonld_types', []),
            'content_sha256': sc.sha256_text(text), 'word_count': len(text.split()),
            'modified_gmt': row.get('modified_gmt', '')}
    robots = sc.http_get(f'{site}/robots.txt', retries=1)
    parsed = audit.robots_info(robots.text) if robots.status == 200 else {'disallow_all': False, 'sitemaps': []}
    sitemap_url, urls = audit.collect_sitemap_urls(site, parsed.get('sitemaps', []))
    home = sc.http_get(f'{site}/', retries=1)
    home_info = sc.parse_page(home.text) if home.status == 200 else {}
    site_files = {'robots_status': robots.status, 'robots_sha256': sc.sha256_text(robots.text) if robots.status == 200 else '',
                  'robots_disallow_all': parsed['disallow_all'], 'sitemap_url': sitemap_url or '',
                  'sitemap_urls': len(urls), 'home_status': home.status, 'home_canonical': home_info.get('canonical', '')}
    return entries, site_files


# ================================================================ baseline (append-only) ============================
def merge_baseline(baseline, entries, site_files, accept=(), reason='', stamp=None, accept_site=False):
    """Return (baseline, allowlist_records, added, replaced). Existing entries only change through accept."""
    stamp = stamp or sc.now()
    baseline = baseline or {'version': 1, 'site': sc.SITE, 'created_at': stamp, 'entries': {}, 'site_files': {}}
    added, replaced, records = [], [], []
    accepted = {str(a) for a in accept}
    if accepted and not reason.strip():
        raise ValueError('--accept requires --reason so the approval is auditable')
    for key, entry in entries.items():
        if key not in baseline['entries']:
            baseline['entries'][key] = {**entry, 'first_seen': stamp}
            added.append(key)
        elif key in accepted:
            baseline['entries'][key] = {**entry, 'first_seen': baseline['entries'][key].get('first_seen', stamp),
                                        'accepted_at': stamp}
            replaced.append(key)
            records.append({'id': int(key), 'fields': ['*'], 'reason': reason.strip(), 'accepted_at': stamp})
    if not baseline.get('site_files') or accept_site:
        if accept_site and not reason.strip():
            raise ValueError('--accept-site requires --reason so the approval is auditable')
        baseline['site_files'] = site_files
    baseline['updated_at'] = stamp
    return baseline, records, added, replaced


# ================================================================ drift check =======================================
def allowed(allowlist, key, field):
    for rec in allowlist.get('records', []):
        if str(rec.get('id')) == str(key) and ('*' in rec.get('fields', []) or field in rec.get('fields', [])):
            return True
    return False


def compare(baseline, entries, site_files, allowlist=None, strict_high=False):
    allowlist = allowlist or {}
    out = []

    def add(key, check, severity, message):
        if not allowed(allowlist, key, check):
            out.append(sc.finding(check, severity, f'#{key}: {message}', id=int(key)))

    for key, base in baseline.get('entries', {}).items():
        live = entries.get(key)
        if live is None:
            add(key, 'removed', 'critical', f'{base["url"]} is no longer public (deleted, trashed or unpublished)')
            continue
        if live['http_status'] != 200:
            add(key, 'http_status', 'critical', f'{base["url"]} now returns HTTP {live["http_status"]}')
            continue
        if sc.norm_url(live['url']) != sc.norm_url(base['url']):
            add(key, 'url_changed', 'critical', f'URL changed: {base["url"]} → {live["url"]}')
        if live['slug'] != base['slug']:
            add(key, 'slug_changed', 'critical', f'slug changed: {base["slug"]} → {live["slug"]}')
        if sc.norm_url(live.get('final_url') or live['url'], False) != sc.norm_url(live['url'], False):
            add(key, 'redirected', 'critical', f'now redirects to {live["final_url"]}')
        if base.get('canonical') and sc.norm_url(live.get('canonical') or '/') != sc.norm_url(base['canonical']):
            add(key, 'canonical_changed', 'critical', f'canonical changed: {base["canonical"]} → {live.get("canonical") or "(none)"}')
        if live['noindex'] and not base.get('noindex'):
            add(key, 'noindex_added', 'critical', 'page became noindex')
        if live['title'] != base['title']:
            add(key, 'title_changed', 'high', f'title changed: "{base["title"]}" → "{live["title"]}"')
        if live['categories'] != base.get('categories'):
            add(key, 'category_changed', 'high', f'categories {base.get("categories")} → {live["categories"]}')
        lost = sorted(set(base.get('jsonld_types', [])) - set(live.get('jsonld_types', [])))
        if lost:
            add(key, 'structured_data_lost', 'medium', f'JSON-LD types disappeared: {lost}')
        if live['content_sha256'] != base['content_sha256']:
            words_b, words_l = max(1, base.get('word_count', 1)), live.get('word_count', 0)
            delta = abs(words_l - words_b) * 100 / words_b
            edited = live.get('modified_gmt') != base.get('modified_gmt')
            if edited and delta >= CONTENT_DRIFT_PCT:
                add(key, 'content_changed', 'high', f'content edited ({delta:.0f}% word-count change)')
            elif edited:
                add(key, 'content_edited', 'medium', f'content edited ({delta:.0f}% word-count change)')
            else:
                add(key, 'dynamic_content_changed', 'info', 'rendered text changed without a modified date change')
        if live['h1'] != base.get('h1'):
            add(key, 'h1_changed', 'low', f'H1 changed: "{base.get("h1")}" → "{live["h1"]}"')
    new = sorted(set(entries) - set(baseline.get('entries', {})), key=int)
    if new:
        out.append(sc.finding('unbaselined', 'info', f'{len(new)} public pages are not baselined yet: {new[:15]}', ids=new))
    base_site = baseline.get('site_files', {})
    if site_files.get('robots_disallow_all'):
        out.append(sc.finding('robots_blocks_all', 'critical', 'robots.txt now disallows the whole site'))
    if base_site.get('robots_sha256') and site_files.get('robots_sha256') != base_site['robots_sha256']:
        out.append(sc.finding('robots_changed', 'high', 'robots.txt changed since the baseline'))
    if base_site.get('sitemap_urls') and site_files.get('sitemap_urls', 0) < base_site['sitemap_urls'] * SITEMAP_DROP:
        out.append(sc.finding('sitemap_shrunk', 'high',
                              f'sitemap lists {site_files.get("sitemap_urls", 0)} URLs (baseline {base_site["sitemap_urls"]})'))
    if base_site.get('home_canonical') and sc.norm_url(site_files.get('home_canonical') or '/') != sc.norm_url(base_site['home_canonical']):
        out.append(sc.finding('home_canonical_changed', 'critical', 'home page canonical changed'))
    if site_files.get('home_status') != 200:
        out.append(sc.finding('home_unreachable', 'critical', f'home page HTTP {site_files.get("home_status")}'))
    return out


UNREADABLE_RATIO = 0.5   # more than half of the pages failing means the site/bot is blocked, not that SEO broke


def split_healthy(entries):
    ok = {k: v for k, v in entries.items() if v['http_status'] == 200}
    return ok, sorted(set(entries) - set(ok), key=int)


def unreadable(entries):
    if not entries:
        return True
    return (len(entries) - len(split_healthy(entries)[0])) / len(entries) > UNREADABLE_RATIO


def blocking(findings, strict_high=True):
    levels = {'critical', 'high'} if strict_high else {'critical'}
    return [f for f in findings if f['severity'] in levels]


def render(mode, findings, meta):
    counts = sc.severity_counts(findings)
    lines = [f'# SEO Protection ({mode}) — {sc.now()}', '',
             '| Severity | Findings |', '|---|---:|'] + [f'| {s} | {counts[s]} |' for s in sc.SEVERITIES]
    if meta:
        lines += ['', ' · '.join(f'{k}: {v}' for k, v in meta.items())]
    if findings:
        lines += ['', '## Findings', '']
        for item in sorted(findings, key=lambda f: sc.SEVERITIES.index(f['severity']))[:120]:
            lines.append(f'- **{item["severity"]}** `{item["check"]}` — {item["message"]}')
    else:
        lines += ['', 'No drift or violation found.']
    lines += ['', '_Read-only: this check never writes to WordPress. Approve an intentional change with '
              '`--mode baseline --accept ID --reason "…"` (recorded in data/seo/protection-allowlist.json)._']
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--mode', choices=['repo', 'baseline', 'check'], required=True)
    parser.add_argument('--site', default=sc.SITE)
    parser.add_argument('--out', default=str(sc.REPORT_DIR))
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--max-pages', type=int, default=0)
    parser.add_argument('--accept', default='', help='comma separated WP ids whose current state is approved')
    parser.add_argument('--accept-site', action='store_true', help='approve the current robots.txt/sitemap/home state')
    parser.add_argument('--reason', default='')
    parser.add_argument('--critical-only', action='store_true', help='only critical findings fail the run')
    args = parser.parse_args(argv)
    out = sc.pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    baseline = sc.read_json(BASELINE_PATH)
    meta, findings = {}, []
    if args.mode == 'repo':
        topics, ready, errors = sc.load_sources()
        findings = repo_guard(sc.load_ledger(), ready, topics, baseline)
        findings += [sc.finding('qa_error', 'critical', e.get('reason', ''), file=e.get('file')) for e in errors]
        meta = {'ledger_entries': len(sc.load_ledger()), 'baseline_entries': len((baseline or {}).get('entries', {}))}
    else:
        try:
            entries, site_files = live_snapshot(args.site, args.workers, args.max_pages)
        except sc.SeoFetchError as exc:
            print(f'LIVE READ FAILED: {exc}', file=sys.stderr)
            return 3
        meta = {'live_public_pages': len(entries), 'sitemap_urls': site_files['sitemap_urls']}
        if unreadable(entries):
            bad = len(split_healthy(entries)[1])
            print(f'LIVE READ FAILED: {bad} of {len(entries)} public pages did not return HTTP 200 '
                  '(bot blocking or an outage). Nothing was recorded or compared; set SEO_USER_AGENT or '
                  'allow the runner in the WAF.', file=sys.stderr)
            return 3
        if args.mode == 'baseline':
            entries, skipped = split_healthy(entries)
            meta['skipped_non_200'] = skipped[:20]
            accept = [a for a in args.accept.split(',') if a.strip()]
            try:
                baseline, records, added, replaced = merge_baseline(baseline, entries, site_files, accept, args.reason,
                                                                    accept_site=args.accept_site)
            except ValueError as exc:
                print(f'ERROR: {exc}', file=sys.stderr)
                return 1
            sc.write_json(BASELINE_PATH, baseline)
            if records:
                allow = sc.read_json(ALLOWLIST_PATH, {'version': 1, 'records': []})
                allow['records'].extend(records)
                sc.write_json(ALLOWLIST_PATH, allow)
            meta.update({'baseline_entries': len(baseline['entries']), 'added': len(added), 'accepted_replacements': len(replaced)})
        else:
            if not baseline:
                print('NO BASELINE: run `--mode baseline` once (workflow_dispatch) to record the accepted state.', file=sys.stderr)
                return 2
            allowlist = sc.read_json(ALLOWLIST_PATH, {'records': []})
            findings = compare(baseline, entries, site_files, allowlist)
            meta['baseline_entries'] = len(baseline['entries'])
    text = render(args.mode, findings, meta)
    (out / 'protection.md').write_text(text, encoding='utf-8')
    sc.write_json(out / 'protection.json', {'generated_at': sc.now(), 'mode': args.mode, 'meta': meta, 'findings': findings})
    sc.step_summary(text)
    bad = blocking(findings, strict_high=not args.critical_only)
    print(f'SEO protection ({args.mode}): {len(findings)} findings, {len(bad)} blocking')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
