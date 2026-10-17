#!/usr/bin/env python3
"""SEO Audit: read-only audit of the repository sources and (optionally) the live WordPress site.

  python scripts/seo_audit.py --mode source            # offline: authored Markdown + ledger
  python scripts/seo_audit.py --mode live              # public REST + public pages, no credentials
  python scripts/seo_audit.py --mode full --check-links

Never writes to WordPress. Outputs reports/seo/audit.{json,md} and audit-pages.csv.
"""
import argparse
import collections
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seo_common as sc  # noqa: E402

MIN_WORDS_THIN = 1200
MAX_WORDS_LONG = 3000
TITLE_MAX = 70
DESC_MIN, DESC_MAX = 70, 165
SLOW_MS = 3000
HTML_KB_MAX = 600
TITLE_OVERLAP = 0.75
FAQ_RE = re.compile(r'câu hỏi thường gặp|faq', re.I)
SOURCES_RE = re.compile(r'nguồn', re.I)
BOT_BLOCKED = {401, 403, 405, 429, 999}


# ================================================================ source audit (offline) ============================
def audit_sources(topics, ready, errors, ledger, site=sc.SITE, known_urls=None):
    """known_urls: every public URL of the live site (live/full mode); None means offline."""
    published = {sc.norm_url(v['url']) for v in ledger.values() if v.get('url')}
    pages, site_findings = [], []
    for err in errors:
        site_findings.append(sc.finding('qa_error', 'critical', err.get('reason', 'QA error'),
                                        file=err.get('file'), id=err.get('id')))
    for art in ready:
        fs = []
        body, words = art['body'], art['words']
        heads = sc.md_headings(art['body'])
        h2 = [text for level, text in heads if level == '##']
        links = sc.md_links(body)
        internal = [u for _, u in links if sc.is_internal(u, site)]
        external = [u for _, u in links if not sc.is_internal(u, site)]
        if words < MIN_WORDS_THIN:
            fs.append(sc.finding('thin_content', 'medium', f'{words} words (< {MIN_WORDS_THIN})'))
        if words > MAX_WORDS_LONG:
            fs.append(sc.finding('long_content', 'info', f'{words} words (> {MAX_WORDS_LONG})'))
        if len(h2) < 5:
            fs.append(sc.finding('few_sections', 'low', f'only {len(h2)} H2 sections'))
        if len({sc.engine.normalized(h) for h in h2}) != len(h2):
            fs.append(sc.finding('duplicate_h2', 'low', 'duplicate H2 text inside the article'))
        if len(art['title']) > TITLE_MAX:
            fs.append(sc.finding('title_long', 'low', f'title is {len(art["title"])} characters (> {TITLE_MAX})'))
        first_para = ''
        match = re.search(r'^##\s.+?\n+(.+?)(?:\n\n|\Z)', body, re.S | re.M)
        if match:
            first_para = match.group(1)
        first_words = len(re.findall(r'\w+', first_para))
        if not 25 <= first_words <= 160:
            fs.append(sc.finding('answer_first', 'low', f'opening paragraph has {first_words} words; '
                                 'lead with a direct, quotable answer (25-160 words)'))
        if not any(FAQ_RE.search(h) for h in h2):
            fs.append(sc.finding('faq_missing', 'info', 'no FAQ section (optional for AEO/GEO)'))
        if not external and not any(SOURCES_RE.search(h) for h in h2):
            fs.append(sc.finding('no_sources', 'low', 'no external reference and no sources section'))
        if not internal:
            fs.append(sc.finding('no_internal_links', 'medium', 'no outgoing internal links'))
        if len(set(internal)) > 10:
            fs.append(sc.finding('many_internal_links', 'low', f'{len(set(internal))} distinct internal links'))
        for url in sorted(set(internal)):
            key = sc.norm_url(url)
            if key in published:
                continue
            if known_urls is None:  # offline: legacy #146-167 live outside the ledger, so only note it
                fs.append(sc.finding('link_not_in_ledger', 'info', f'internal link not in the ledger (verify live): {url}'))
            elif key not in known_urls:
                fs.append(sc.finding('link_unpublished', 'high', f'internal link is not a public page on the site: {url}'))
        for url in sorted(set(external)):
            if url.startswith('http://'):
                fs.append(sc.finding('insecure_external_link', 'medium', f'non-https external link: {url}'))
        entry = ledger.get(str(art['id']), {})
        slug = entry.get('slug', '')
        if slug and len(slug) > 80:
            fs.append(sc.finding('slug_long', 'low', f'slug is {len(slug)} characters'))
        pages.append({'id': art['id'], 'title': art['title'], 'category': art['category'],
                      'url': entry.get('url', ''), 'words': words, 'h2': len(h2),
                      'internal_links': len(set(internal)), 'external_links': len(set(external)),
                      'score': sc.score(fs), 'findings': fs})
    site_findings.extend(title_overlaps(ready))
    site_findings.extend(duplicate_titles(ready))
    return pages, site_findings


def duplicate_titles(ready):
    seen = collections.defaultdict(list)
    for art in ready:
        seen[sc.engine.normalized(art['title'])].append(art['id'])
    return [sc.finding('duplicate_title', 'critical', f'identical title shared by #{ids}', ids=ids)
            for ids in seen.values() if len(ids) > 1]


def title_overlaps(ready, threshold=TITLE_OVERLAP):
    """Possible keyword cannibalisation: near-identical title token sets anywhere on the site."""
    items = [(art['id'], art['category'], set(sc.tokenize(art['title']))) for art in ready]
    out = []
    for i, (a_id, a_cat, a) in enumerate(items):
        for b_id, b_cat, b in items[i + 1:]:
            union = a | b
            if union and len(a & b) / len(union) >= threshold:
                where = a_cat if a_cat == b_cat else f'{a_cat} vs {b_cat}'
                out.append(sc.finding('title_overlap', 'medium',
                                      f'#{a_id} and #{b_id} have near-identical titles ({where}); keep intents distinct '
                                      'and cross-link them', ids=[a_id, b_id]))
    return out


# ================================================================ live audit (public HTTP only) =====================
def robots_info(text):
    group_all, disallow_all, sitemaps = False, False, []
    for raw in text.splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line or ':' not in line:
            continue
        key, value = (x.strip() for x in line.split(':', 1))
        key = key.lower()
        if key == 'user-agent':
            group_all = value == '*'
        elif key == 'disallow' and group_all and value == '/':
            disallow_all = True
        elif key == 'sitemap':
            sitemaps.append(value)
    return {'disallow_all': disallow_all, 'sitemaps': sitemaps}


def collect_sitemap_urls(site, hints, cap=80):
    candidates = list(dict.fromkeys(list(hints) + [f'{site}/sitemap_index.xml', f'{site}/wp-sitemap.xml',
                                                    f'{site}/sitemap.xml']))
    for entry in candidates:
        reply = sc.http_get(entry, retries=1)
        if reply.status != 200 or '<loc' not in reply.text:
            continue
        locs = re.findall(r'<loc>\s*([^<]+?)\s*</loc>', reply.text)
        if '<sitemapindex' in reply.text:
            urls = []
            for child in locs[:cap]:
                sub = sc.http_get(child, retries=1)
                if sub.status == 200:
                    urls.extend(re.findall(r'<loc>\s*([^<]+?)\s*</loc>', sub.text))
            return entry, urls
        return entry, locs
    return None, []


def page_findings(item, reply, site):
    """Checks for one live URL; `item` carries expected values from WP REST / ledger."""
    fs = []
    url = item['url']
    if reply.status != 200:
        return [sc.finding('http_status', 'critical', f'HTTP {reply.status or "unreachable"} {reply.error or ""}'.strip())], {}
    info = sc.parse_page(reply.text)
    if sc.norm_url(reply.final_url, False) != sc.norm_url(url, False):
        fs.append(sc.finding('redirected', 'high', f'final URL differs: {reply.final_url}'))
    if not info['canonical']:
        fs.append(sc.finding('canonical_missing', 'high', 'no canonical link'))
    elif sc.norm_url(info['canonical']) != sc.norm_url(url):
        fs.append(sc.finding('canonical_mismatch', 'high', f'canonical points to {info["canonical"]}'))
    if 'noindex' in info['robots']:
        fs.append(sc.finding('noindex', 'critical', f'meta robots = {info["robots"]}'))
    if 'noindex' in reply.headers.get('x-robots-tag', '').lower():
        fs.append(sc.finding('noindex_header', 'critical', 'X-Robots-Tag contains noindex'))
    if not info['title']:
        fs.append(sc.finding('title_missing', 'critical', 'empty <title>'))
    elif len(info['title']) > TITLE_MAX:
        fs.append(sc.finding('title_tag_long', 'low', f'<title> is {len(info["title"])} characters'))
    if not info['description']:
        fs.append(sc.finding('meta_description_missing', 'medium', 'no meta description'))
    elif not DESC_MIN <= len(info['description']) <= DESC_MAX:
        fs.append(sc.finding('meta_description_length', 'low', f'meta description is {len(info["description"])} characters'))
    if info['h1_count'] != 1:
        fs.append(sc.finding('h1_count', 'medium', f'{info["h1_count"]} H1 elements'))
    types = set(info['jsonld_types'])
    if not types:
        fs.append(sc.finding('jsonld_missing', 'medium', 'no JSON-LD structured data'))
    else:
        if 'INVALID_JSON_LD' in types:
            fs.append(sc.finding('jsonld_invalid', 'high', 'a JSON-LD block is not valid JSON'))
        if not types & {'Article', 'BlogPosting', 'NewsArticle'}:
            fs.append(sc.finding('jsonld_article_missing', 'low', f'no Article/BlogPosting type ({sorted(types)})'))
        if 'BreadcrumbList' not in types:
            fs.append(sc.finding('breadcrumb_schema_missing', 'low', 'no BreadcrumbList JSON-LD'))
    if not info['og_title']:
        fs.append(sc.finding('og_missing', 'low', 'no Open Graph title'))
    if info['images_missing_alt']:
        fs.append(sc.finding('image_alt_missing', 'medium',
                             f'{info["images_missing_alt"]} of {info["images_total"]} images have no alt attribute'))
    if not info['viewport']:
        fs.append(sc.finding('viewport_missing', 'medium', 'no responsive viewport meta'))
    if reply.elapsed_ms > SLOW_MS:
        fs.append(sc.finding('slow_response', 'low', f'{reply.elapsed_ms} ms to first full response'))
    if len(reply.text) > HTML_KB_MAX * 1024:
        fs.append(sc.finding('html_heavy', 'low', f'{len(reply.text) // 1024} KB of HTML'))
    if url.startswith('https://') and re.search(r'(?:src|href)=["\']http://', reply.text):
        fs.append(sc.finding('mixed_content', 'medium', 'http:// resources on an https page'))
    if item.get('expected_title') and sc.engine.normalized(item['expected_title']) not in sc.engine.normalized(info['title']):
        fs.append(sc.finding('title_differs_from_ledger', 'high', 'page <title> no longer contains the published title'))
    return fs, info


def ledger_vs_live(ledger, live_posts):
    out, by_id = [], {int(p['id']): p for p in live_posts}
    for key, entry in ledger.items():
        if entry.get('phase') != 'VERIFIED' or not entry.get('wp_id'):
            continue
        live = by_id.get(int(entry['wp_id']))
        if live is None:
            out.append(sc.finding('missing_live', 'critical', f'#{key} (WP {entry["wp_id"]}) is not public on the site',
                                  id=int(key)))
            continue
        if sc.norm_url(live.get('link', '')) != sc.norm_url(entry.get('url', '')):
            out.append(sc.finding('url_changed', 'critical', f'#{key}: live URL {live.get("link")} != ledger {entry.get("url")}',
                                  id=int(key)))
        if live.get('slug') != entry.get('slug'):
            out.append(sc.finding('slug_changed', 'critical', f'#{key}: live slug {live.get("slug")} != {entry.get("slug")}',
                                  id=int(key)))
        cid = entry.get('category_id')
        if cid is not None and live.get('categories') != [cid]:
            out.append(sc.finding('category_changed', 'high',
                                  f'#{key}: live categories {live.get("categories")} != [{cid}]', id=int(key)))
    return out


def check_links(pages_info, site, cap, workers, include_external=False):
    """HEAD-check anchors found on live pages. Returns findings keyed to the source pages."""
    targets = collections.defaultdict(set)
    for page_url, info in pages_info.items():
        for anchor in info.get('anchors', []):
            href = sc.urllib.parse.urljoin(page_url, anchor['href'].split('#', 1)[0].strip())
            if not href.startswith(('http://', 'https://')) or '/wp-admin' in href or '/wp-json' in href:
                continue
            if sc.is_internal(href, site) or include_external:
                targets[href].add(page_url)
    urls = sorted(targets)[:cap]
    results = sc.fetch_many(urls, workers=workers, method='HEAD', retries=1, timeout=20)
    out = []
    for url, reply in results.items():
        if reply.status in (405, 501):
            reply = sc.http_get(url, retries=0, timeout=20)
        if reply.status == 0:
            sev = 'high' if sc.is_internal(url, site) else 'low'
            out.append(sc.finding('link_unreachable', sev, f'{url} unreachable ({reply.error})', url=url,
                                  sources=sorted(targets[url])[:5]))
        elif reply.status >= 400 and reply.status not in BOT_BLOCKED:
            sev = 'high' if sc.is_internal(url, site) else 'medium'
            out.append(sc.finding('broken_link', sev, f'{url} returned HTTP {reply.status}', url=url,
                                  sources=sorted(targets[url])[:5]))
    return out, len(urls), max(0, len(targets) - len(urls))


def pagespeed(urls, key, strategy='mobile'):
    results = []
    for url in urls:
        api = ('https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=performance&strategy='
               f'{strategy}&key={key}&url={sc.urllib.parse.quote(url, safe="")}')
        reply = sc.http_get(api, timeout=90, retries=1)
        if reply.status != 200:
            results.append({'url': url, 'error': f'HTTP {reply.status}'})
            continue
        data = json.loads(reply.text)
        audits = data.get('lighthouseResult', {}).get('audits', {})

        def num(name):
            return audits.get(name, {}).get('numericValue')

        results.append({'url': url, 'score': (data.get('lighthouseResult', {}).get('categories', {})
                                              .get('performance', {}).get('score')),
                        'lcp_ms': num('largest-contentful-paint'), 'cls': num('cumulative-layout-shift'),
                        'tbt_ms': num('total-blocking-time')})
    findings = []
    for item in results:
        if 'error' in item:
            findings.append(sc.finding('pagespeed_error', 'info', f'{item["url"]}: {item["error"]}'))
            continue
        if item['lcp_ms'] and item['lcp_ms'] > 2500:
            findings.append(sc.finding('cwv_lcp', 'medium', f'{item["url"]}: LCP {int(item["lcp_ms"])} ms (> 2500)'))
        if item['cls'] is not None and item['cls'] > 0.1:
            findings.append(sc.finding('cwv_cls', 'medium', f'{item["url"]}: CLS {item["cls"]:.3f} (> 0.1)'))
    return results, findings


def audit_live(ledger, site=sc.SITE, max_pages=0, workers=6, with_links=False, with_external=False,
               link_cap=1500, psi=0):
    posts = sc.wp_list('posts', 'id,link,slug,title,categories,modified_gmt', site)
    wp_pages = sc.wp_list('pages', 'id,link,slug,title,modified_gmt', site)
    expected = {int(v['wp_id']): v for v in ledger.values() if v.get('wp_id')}
    items = []
    for kind, rows in (('post', posts), ('page', wp_pages)):
        for row in rows:
            ledger_entry = expected.get(int(row['id']), {})
            items.append({'id': int(row['id']), 'type': kind, 'url': row['link'], 'slug': row.get('slug', ''),
                          'wp_title': sc.engine.title_of({'title': row.get('title', {})}),
                          'expected_title': ledger_entry.get('title')})
    if max_pages:
        items = items[:max_pages]
    replies = sc.fetch_many([i['url'] for i in items], workers=workers)
    pages, infos = [], {}
    for item in items:
        reply = replies[item['url']]
        fs, info = page_findings(item, reply, site)
        infos[item['url']] = info
        pages.append({'id': item['id'], 'type': item['type'], 'url': item['url'], 'title': item['wp_title'],
                      'status': reply.status, 'ms': reply.elapsed_ms, 'score': sc.score(fs), 'findings': fs,
                      'jsonld_types': info.get('jsonld_types', []), 'words': info.get('word_count', 0)})
    site_findings = ledger_vs_live(ledger, posts)
    failing = sum(1 for p in pages if p['status'] != 200)
    if pages and failing / len(pages) > 0.5:
        site_findings.append(sc.finding('audit_bot_blocked', 'high',
                                        f'{failing} of {len(pages)} pages failed to load: the audit bot may be blocked by a WAF/CDN '
                                        '(set the SEO_USER_AGENT secret/variable or allow the runner); page-level results are unreliable'))
    robots = sc.http_get(f'{site}/robots.txt', retries=1)
    robots_data = {'status': robots.status}
    if robots.status != 200:
        site_findings.append(sc.finding('robots_missing', 'medium', f'robots.txt returned HTTP {robots.status}'))
    else:
        parsed = robots_info(robots.text)
        robots_data.update(parsed)
        if parsed['disallow_all']:
            site_findings.append(sc.finding('robots_blocks_all', 'critical', 'robots.txt has Disallow: / for User-agent: *'))
        if not parsed['sitemaps']:
            site_findings.append(sc.finding('robots_no_sitemap', 'low', 'robots.txt does not declare a sitemap'))
    sitemap_url, sitemap_urls = collect_sitemap_urls(site, robots_data.get('sitemaps', []))
    if not sitemap_url:
        site_findings.append(sc.finding('sitemap_missing', 'high', 'no XML sitemap found'))
    else:
        listed = {sc.norm_url(u) for u in sitemap_urls}
        missing = [i['url'] for i in items if i['type'] == 'post' and sc.norm_url(i['url']) not in listed]
        if missing:
            site_findings.append(sc.finding('sitemap_coverage', 'medium',
                                            f'{len(missing)} published posts are not in the sitemap', sample=missing[:10]))
    home = sc.http_get(f'{site}/', retries=1)
    if home.status == 200:
        home_info = sc.parse_page(home.text)
        if not set(home_info['jsonld_types']) & {'WebSite', 'Organization', 'WebPage'}:
            site_findings.append(sc.finding('home_schema_missing', 'low', 'home page has no WebSite/Organization JSON-LD'))
    else:
        site_findings.append(sc.finding('home_unreachable', 'critical', f'home page HTTP {home.status}'))
    link_stats = {}
    if with_links:
        broken, checked, skipped = check_links({u: i for u, i in infos.items() if i}, site, link_cap, workers, with_external)
        site_findings.extend(broken)
        link_stats = {'checked': checked, 'skipped_over_cap': skipped}
    psi_results = []
    key = os.getenv('PAGESPEED_API_KEY')
    if psi and key:
        sample = [i['url'] for i in items if i['type'] == 'post'][:psi]
        psi_results, psi_findings = pagespeed(sample, key)
        site_findings.extend(psi_findings)
    known = {sc.norm_url(i['url']) for i in items}
    return pages, site_findings, {'known_urls': known, 'robots': robots_data, 'sitemap': sitemap_url, 'sitemap_urls': len(sitemap_urls),
                                  'live_posts': len(posts), 'live_pages': len(wp_pages), 'links': link_stats,
                                  'pagespeed': psi_results}


# ================================================================ reporting =========================================
def build_report(mode, source_pages, source_site, live_pages, live_site, live_meta):
    all_findings = [f for p in source_pages + live_pages for f in p['findings']] + source_site + live_site
    by_check = collections.defaultdict(lambda: collections.Counter())
    for item in all_findings:
        by_check[item['check']][item['severity']] += 1
    return {'generated_at': sc.now(), 'mode': mode, 'site': sc.SITE,
            'totals': {'source_posts': len(source_pages), 'live_pages': len(live_pages),
                       'findings': len(all_findings), 'severity': sc.severity_counts(all_findings)},
            'checks': {k: dict(v) for k, v in sorted(by_check.items())},
            'source_pages': source_pages, 'source_site_findings': source_site,
            'live_pages': live_pages, 'live_site_findings': live_site, 'live_meta': live_meta}


def render_markdown(report):
    totals = report['totals']
    lines = [f'# SEO Audit ({report["mode"]}) — {report["generated_at"]}', '',
             f'Site: {report["site"]} · source posts audited: {totals["source_posts"]} · '
             f'live pages audited: {totals["live_pages"]}', '',
             '| Severity | Findings |', '|---|---:|']
    lines += [f'| {s} | {totals["severity"][s]} |' for s in sc.SEVERITIES]
    lines += ['', '## Findings by check', '', '| Check | critical | high | medium | low | info |', '|---|---:|---:|---:|---:|---:|']
    for check, counts in report['checks'].items():
        lines.append(f'| {check} | ' + ' | '.join(str(counts.get(s, 0)) for s in sc.SEVERITIES) + ' |')
    site_findings = report['source_site_findings'] + report['live_site_findings']
    if site_findings:
        lines += ['', '## Site-level findings', '']
        for item in sorted(site_findings, key=lambda f: sc.SEVERITIES.index(f['severity']))[:60]:
            lines.append(f'- **{item["severity"]}** `{item["check"]}` — {item["message"]}')
    for label, rows in (('Lowest-scoring source posts', report['source_pages']),
                        ('Lowest-scoring live pages', report['live_pages'])):
        worst = sorted((r for r in rows if r['findings']), key=lambda r: r['score'])[:15]
        if worst:
            lines += ['', f'## {label}', '', '| Score | ID | Title / URL | Top issues |', '|---:|---:|---|---|']
            for row in worst:
                top = ', '.join(sorted({f['check'] for f in row['findings'] if f['severity'] != 'info'})[:5])
                lines.append(f'| {row["score"]} | {row.get("id", "")} | {(row.get("title") or row.get("url", ""))[:70]} | {top} |')
    meta = report.get('live_meta') or {}
    if meta:
        lines += ['', '## Live site facts', '', f'- Sitemap: {meta.get("sitemap")} ({meta.get("sitemap_urls")} URLs)',
                  f'- Live posts: {meta.get("live_posts")} · pages: {meta.get("live_pages")}',
                  f'- robots.txt: {json.dumps(meta.get("robots", {}), ensure_ascii=False)}',
                  f'- Link check: {json.dumps(meta.get("links", {}))}']
    lines += ['', '_Read-only audit: no WordPress write was performed. Metrics that need a browser (visual CWV) '
              'are only sampled when PAGESPEED_API_KEY is configured._']
    return '\n'.join(lines) + '\n'


def write_outputs(report, out):
    out.mkdir(parents=True, exist_ok=True)
    sc.write_json(out / 'audit.json', report)
    (out / 'audit.md').write_text(render_markdown(report), encoding='utf-8')
    with open(out / 'audit-pages.csv', 'w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['scope', 'id', 'url', 'score', 'critical', 'high', 'medium', 'low', 'checks'])
        for scope, rows in (('source', report['source_pages']), ('live', report['live_pages'])):
            for row in rows:
                counts = sc.severity_counts(row['findings'])
                writer.writerow([scope, row.get('id', ''), row.get('url', ''), row['score'], counts['critical'],
                                 counts['high'], counts['medium'], counts['low'],
                                 ';'.join(sorted({f['check'] for f in row['findings']}))])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--mode', choices=['source', 'live', 'full'], default='source')
    parser.add_argument('--site', default=sc.SITE)
    parser.add_argument('--out', default=str(sc.REPORT_DIR))
    parser.add_argument('--max-pages', type=int, default=0)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--check-links', action='store_true')
    parser.add_argument('--check-external', action='store_true')
    parser.add_argument('--link-cap', type=int, default=1500)
    parser.add_argument('--psi', type=int, default=0, help='sample size for PageSpeed (needs PAGESPEED_API_KEY)')
    parser.add_argument('--strict', action='store_true', help='exit 1 when any critical finding exists')
    args = parser.parse_args(argv)
    ledger = sc.load_ledger()
    source_pages, source_site, live_pages, live_site, live_meta = [], [], [], [], {}
    known = None
    if args.mode in ('live', 'full'):
        try:
            live_pages, live_site, live_meta = audit_live(
                ledger, args.site, args.max_pages, args.workers, args.check_links, args.check_external,
                args.link_cap, args.psi)
        except sc.SeoFetchError as exc:
            print(f'LIVE AUDIT FAILED: {exc}', file=sys.stderr)
            return 3
        known = live_meta.pop('known_urls') if not args.max_pages else None  # a page cap makes the set incomplete
        live_meta.pop('known_urls', None)
    if args.mode in ('source', 'full'):
        topics, ready, errors = sc.load_sources()
        source_pages, source_site = audit_sources(topics, ready, errors, ledger, args.site, known)
    report = build_report(args.mode, source_pages, source_site, live_pages, live_site, live_meta)
    write_outputs(report, sc.pathlib.Path(args.out))
    summary = render_markdown(report)
    sc.step_summary(summary)
    sev = report['totals']['severity']
    print(f'SEO audit ({args.mode}): {report["totals"]["findings"]} findings — ' +
          ', '.join(f'{s}={sev[s]}' for s in sc.SEVERITIES))
    return 1 if args.strict and sev['critical'] else 0


if __name__ == '__main__':
    sys.exit(main())
