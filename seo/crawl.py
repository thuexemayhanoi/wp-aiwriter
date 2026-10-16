"""Phase 2 data collection: public HTML crawl, robots.txt, sitemaps, probes, link and image status.

Incremental: a post/page whose ``modified_gmt`` is unchanged and whose last crawl is newer
than ``recrawl_after_days`` keeps its previous crawl summary unless ``--full`` is given.
Site-level checks (home, archives, robots, sitemaps, probes) always run.
"""
from collections import Counter
import re
import secrets
import urllib.parse
import urllib.robotparser
import xml.etree.ElementTree as ET

from . import common
from .common import iso, normalize_url, older_than, read_json, write_json, write_jsonl
from .htmlparse import html_comments, jsonld_nodes, node_types, parse
from .net import parallel

THEME = re.compile(r'/wp-content/themes/([A-Za-z0-9_.-]+)/')
PLUGIN = re.compile(r'/wp-content/plugins/([A-Za-z0-9_.-]+)/')
YOAST_VERSION = re.compile(r'Yoast SEO(?: Premium)? plugin v([0-9.]+)', re.I)
AI_AGENTS = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'Google-Extended', 'ClaudeBot', 'Claude-SearchBot',
             'PerplexityBot', 'CCBot', 'Bingbot', 'Googlebot', 'Applebot-Extended']
NODE_KEYS = ['headline', 'name', 'datePublished', 'dateModified', 'author', 'image', 'publisher', 'telephone',
             'address', 'url', 'itemListElement', 'mainEntityOfPage', 'isPartOf', 'inLanguage', 'sameAs', 'logo']


def pages_cache_path():
    return common.path('data/seo/cache/pages.json.gz')


def link_status_path():
    return common.path('data/seo/link-status.json')


def site_cache_path():
    return common.path('data/seo/site-checks.json')


def summarize_page(resp, cfg, kind):
    text = resp.text() if resp.body else ''
    p = parse(text)
    nodes, errors, sources = jsonld_nodes(p)
    comments = html_comments(text)
    yoast_version = next((m.group(1) for c in comments for m in [YOAST_VERSION.search(c)] if m), None)
    internal = []
    for a in p.anchors:
        url = normalize_url(a.get('href', ''), resp.final_url or resp.url)
        if url and common.is_internal(url, cfg):
            internal.append(url)
    images = p.images
    return {
        'url': resp.url, 'kind': kind, 'status': resp.status, 'final_url': resp.final_url,
        'redirects': resp.redirects, 'elapsed_ms': resp.elapsed_ms, 'error': resp.error,
        'html_bytes': len(resp.body), 'truncated': resp.truncated,
        'content_type': resp.headers.get('content-type', ''),
        'x_robots_tag': resp.headers.get('x-robots-tag', ''),
        'cache_control': resp.headers.get('cache-control', ''),
        'title': p.title, 'meta_description': p.meta('description'),
        'meta_robots': ', '.join(filter(None, [p.meta('robots') or '', p.meta('googlebot') or ''])),
        'canonicals': p.canonicals(), 'rel_next': p.rel_links('next')[:1],
        'h1': [t for level, t in p.headings if level == 1],
        'headings_count': dict(Counter(f'h{level}' for level, _ in p.headings)),
        'heading_outline': [[level, t[:120]] for level, t in p.headings[:80]],
        'lang': p.lang, 'viewport': p.meta('viewport'),
        'og': {k: p.meta(k) for k in ('og:title', 'og:description', 'og:image', 'og:url', 'og:type') if p.meta(k)},
        'twitter_card': p.meta('twitter:card'),
        'generator': p.meta('generator'), 'yoast_version': yoast_version,
        'theme': sorted(set(THEME.findall(text))), 'plugins': sorted(set(PLUGIN.findall(text))),
        'jsonld': {'blocks': len(p.jsonld), 'sources': sources, 'errors': errors,
                   'types': dict(Counter(t for n in nodes for t in node_types(n))),
                   'nodes': [{'types': node_types(n), 'id': n.get('@id', ''), 'origin': n['_origin'],
                              'keys': [k for k in NODE_KEYS if n.get(k)],
                              'name': n.get('name') if isinstance(n.get('name'), str) else None,
                              'telephone': n.get('telephone') if isinstance(n.get('telephone'), str) else None}
                             for n in nodes]},
        'microdata_types': sorted(set(p.itemtypes)),
        'images_total': len(images),
        'images_missing_alt': [normalize_url(i['src'], resp.final_url) or i['src'] for i in images if i['alt'] is None][:50],
        'images_empty_alt': sum(1 for i in images if i['alt'] == ''),
        'images_no_dimensions': sum(1 for i in images if not (i['width'] and i['height'])),
        'mixed_content': sorted(set(p.http_resources))[:30],
        'internal_link_count': len(internal), 'iframes': len(p.iframes),
        'crawled_at': iso(),
    }, sorted(set(internal))


def parse_robots(text, cfg, sample_urls):
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(text.splitlines())
    site = cfg['site_url'].rstrip('/') + '/'
    sitemaps = [line.split(':', 1)[1].strip() for line in text.splitlines()
                if line.lower().startswith('sitemap:')]
    agents = {}
    for agent in AI_AGENTS:
        agents[agent] = {'home': rp.can_fetch(agent, site),
                         'sample_posts_allowed': sum(rp.can_fetch(agent, u) for u in sample_urls),
                         'sample_size': len(sample_urls)}
    disallow_all = not rp.can_fetch('*', site)
    return {'sitemaps': sitemaps, 'agents': agents, 'disallow_all_for_star': disallow_all,
            'blocked_sample_for_googlebot': [u for u in sample_urls if not rp.can_fetch('Googlebot', u)][:20]}


def strip_ns(tag):
    return tag.split('}', 1)[-1]


def read_sitemaps(fetcher, cfg, roots, limit=300):
    """Return {'files': [...], 'urls': {url: {'lastmod', 'sitemap'}}}; follows sitemap indexes."""
    seen, queue, files, urls = set(), list(roots), [], {}
    while queue and len(seen) < limit:
        sm = queue.pop(0)
        if sm in seen or not common.is_internal(sm, cfg):
            continue
        seen.add(sm)
        resp = fetcher.fetch(sm, accept='application/xml,text/xml')
        entry = {'url': sm, 'status': resp.status, 'final_url': resp.final_url,
                 'redirects': len(resp.redirects), 'kind': None, 'count': 0, 'error': resp.error}
        files.append(entry)
        if not resp.ok or not resp.body:
            continue
        try:
            root = ET.fromstring(resp.body)
        except ET.ParseError as exc:
            entry['error'] = f'XML parse error: {str(exc)[:80]}'
            continue
        entry['kind'] = strip_ns(root.tag)
        for child in root:
            loc = lastmod = None
            for el in child:
                name = strip_ns(el.tag)
                if name == 'loc':
                    loc = (el.text or '').strip()
                elif name == 'lastmod':
                    lastmod = (el.text or '').strip()
            if not loc:
                continue
            entry['count'] += 1
            if entry['kind'] == 'sitemapindex':
                queue.append(loc)
            else:
                urls[normalize_url(loc)] = {'lastmod': lastmod, 'sitemap': sm}
    return {'files': files, 'urls': urls}


def site_probes(fetcher, cfg, records):
    site = cfg['site_url'].rstrip('/')
    out = {'checked_at': iso()}
    sample = [r['url'] for r in records if r['type'] == 'post'][:25]
    robots = fetcher.fetch(site + '/robots.txt', accept='text/plain')
    out['robots'] = {'status': robots.status, 'final_url': robots.final_url, 'error': robots.error,
                     'body': robots.text()[:4000] if robots.ok else ''}
    if robots.ok:
        out['robots'].update(parse_robots(robots.text(), cfg, sample))
    roots = list(dict.fromkeys((out['robots'].get('sitemaps') or []) + [site + '/sitemap_index.xml']))
    out['sitemaps'] = read_sitemaps(fetcher, cfg, roots)
    core = fetcher.fetch(site + '/wp-sitemap.xml', accept='application/xml,text/xml')
    out['core_wp_sitemap'] = core.summary()
    http = fetcher.fetch('http://' + common.host(site) + '/', allow_http=True)
    out['http_to_https'] = http.summary()
    probe = f"{site}/seo-audit-probe-{secrets.token_hex(6)}-not-a-page/"
    soft = fetcher.fetch(probe)
    out['not_found_probe'] = {**soft.summary(), 'url': probe}
    if sample:
        noslash = sample[0].rstrip('/')
        out['no_trailing_slash_probe'] = {**fetcher.fetch(noslash).summary(), 'url': noslash}
    llms = fetcher.fetch(site + '/llms.txt', accept='text/plain')
    out['llms_txt'] = {'status': llms.status, 'final_url': llms.final_url}
    return out


def crawl(cfg, fetcher, records, full=False, max_pages=None):
    """Crawl public HTML. Mutates records[*]['page'] and writes caches; returns crawl report."""
    terms = read_json(common.path('data/seo/terms.json'), {}) or {}
    ccfg = cfg.get('crawl', {})
    workers = cfg.get('http', {}).get('max_workers', 4)
    recrawl_days = ccfg.get('recrawl_after_days', 7)
    previous_links = (read_json(pages_cache_path(), {}) or {}).get('links', {})
    page_links, archive_pages = {}, {}
    site = cfg['site_url'].rstrip('/') + '/'

    def get_page(url):
        return fetcher.fetch(url)

    # 1. posts and pages (incremental)
    due = []
    for r in records:
        prev = r.get('page')
        if full or not prev or older_than(prev.get('crawled_at'), recrawl_days) or r['url'] not in previous_links:
            due.append(r['url'])
        else:
            page_links[r['url']] = previous_links[r['url']]
    cap = max_pages or ccfg.get('max_pages', 3000)
    due = due[:cap]
    fetched = parallel(due, get_page, workers)
    by_url = {r['url']: r for r in records}
    for url, resp in fetched.items():
        summary, links = summarize_page(resp, cfg, by_url[url]['type'])
        by_url[url]['page'] = summary
        page_links[url] = links

    # 2. home + archives with pagination (always, they change whenever posts change)
    archive_seeds = [(site, 'home')]
    for c in terms.get('categories', []):
        if c.get('link'):
            archive_seeds.append((c['link'], 'category'))
    for t in terms.get('tags', []):
        if t.get('link') and t.get('count'):
            archive_seeds.append((t['link'], 'tag'))
    budget = ccfg.get('max_archive_pages', 250)
    frontier = archive_seeds[:]
    while frontier and len(archive_pages) < budget:
        batch, frontier = frontier[:max(1, workers * 2)], frontier[max(1, workers * 2):]
        batch = [(u, k) for u, k in batch if u not in archive_pages]
        kinds = dict(batch)
        results = parallel([u for u, _ in batch], get_page, workers)
        for url, resp in results.items():
            summary, links = summarize_page(resp, cfg, kinds[url])
            archive_pages[url] = summary
            nexts = [normalize_url(n, url) for n in summary['rel_next']]
            page_links[url] = sorted(set(links) | {n for n in nexts if n and common.is_internal(n, cfg)})
            base = url.rstrip('/') + '/page/'
            paged = [normalize_url(n, url) for n in summary['rel_next']]
            # Fallback when the theme/SEO plugin prints no rel=next: numbered pagination links.
            paged += [u for u in links if u.startswith(base) and re.match(r'^\d+/?$', u[len(base):])]
            queued = {u for u, _ in frontier}
            for nxt_url in dict.fromkeys(paged):
                if nxt_url and common.is_internal(nxt_url, cfg) and nxt_url not in archive_pages \
                        and nxt_url not in queued:
                    frontier.append((nxt_url, kinds[url].replace('-paged', '') + '-paged'))
                    queued.add(nxt_url)

    probes = site_probes(fetcher, cfg, records)

    # 3. status of every other internal link target (content + template links + sitemap-only URLs)
    crawled = {normalize_url(u) for u in list(by_url) + list(archive_pages)}
    targets = set()
    for links in page_links.values():
        targets.update(links)
    for r in records:
        targets.update(link['href'] for link in r.get('internal_links', []))
    targets.update(u for u in (probes.get('sitemaps') or {}).get('urls', {}) if common.is_internal(u, cfg))
    targets = sorted(u for u in targets if u not in crawled and u.rstrip('/') + '/' not in crawled)
    link_cap = ccfg.get('max_internal_link_checks', 1500)
    link_status = read_json(link_status_path(), {}) or {}
    checked = parallel(targets[:link_cap], lambda u: fetcher.head_or_get(u), workers)
    for url, resp in checked.items():
        link_status[url] = {'kind': 'internal', 'status': resp.status, 'final_url': resp.final_url,
                            'redirects': len(resp.redirects), 'error': resp.error, 'checked_at': iso()}
    for url, r in by_url.items():
        page = r.get('page') or {}
        link_status[url] = {'kind': 'internal', 'status': page.get('status'), 'final_url': page.get('final_url'),
                            'redirects': len(page.get('redirects') or []), 'error': page.get('error', ''),
                            'checked_at': page.get('crawled_at')}
    for url, page in archive_pages.items():
        link_status[url] = {'kind': 'internal', 'status': page['status'], 'final_url': page['final_url'],
                            'redirects': len(page['redirects']), 'error': page['error'], 'checked_at': page['crawled_at']}

    # 4. image weight (internal images only, HEAD content-length)
    images = {}
    for r in records:
        for img in r.get('images', []):
            if img.get('src', '').startswith('http') and common.is_internal(img['src'], cfg):
                images[img['src']] = None
        fi = r.get('featured_image') or {}
        if fi.get('url') and not fi.get('filesize') and common.is_internal(fi['url'], cfg):
            images[fi['url']] = None
    img_cap = ccfg.get('max_image_checks', 1500)
    img_results = parallel(sorted(images)[:img_cap], lambda u: fetcher.fetch(u, method='HEAD', accept='image/*'), workers)
    image_status = {u: {'status': resp.status, 'bytes': int(resp.headers.get('content-length') or 0) or None,
                        'content_type': resp.headers.get('content-type', '')} for u, resp in img_results.items()}

    write_jsonl(common.path('data/posts-index.jsonl'), sorted(records, key=lambda r: (r['type'], r['id'])))
    write_json(pages_cache_path(), {'links': page_links}, compress=True)
    write_json(link_status_path(), link_status)
    site_data = {'probes': probes, 'archives': archive_pages, 'images': image_status,
                 'crawl': {'at': iso(), 'full': full, 'posts_pages_crawled': len(fetched),
                           'posts_pages_reused': len(records) - len(fetched),
                           'archives_crawled': len(archive_pages), 'internal_targets_checked': len(checked),
                           'internal_targets_skipped_cap': max(0, len(targets) - link_cap),
                           'images_checked': len(img_results), 'requests': fetcher.requests_made}}
    write_json(site_cache_path(), site_data)
    state_file = common.path('data/seo/state.json')
    state = read_json(state_file, {}) or {}
    state['last_crawl'] = iso()
    if full:
        state['last_full_crawl'] = state['last_crawl']
    write_json(state_file, state)
    return site_data


def check_external(cfg, fetcher, records, force=False):
    """Status of outbound links (read-only GET/HEAD); cached for recheck_after_days."""
    ecfg = cfg.get('external_links', {})
    link_status = read_json(link_status_path(), {}) or {}
    urls = sorted({link['href'] for r in records for link in r.get('external_links', [])})
    due = [u for u in urls if force or u not in link_status
           or older_than(link_status[u].get('checked_at'), ecfg.get('recheck_after_days', 14))]
    cap = ecfg.get('max_checks', 3000)
    timeout = ecfg.get('timeout_seconds', 15)
    results = parallel(due[:cap], lambda u: fetcher.head_or_get(u, internal_only=False, timeout=timeout),
                       ecfg.get('max_workers', 6))
    for url, resp in results.items():
        link_status[url] = {'kind': 'external', 'status': resp.status, 'final_url': resp.final_url,
                            'redirects': len(resp.redirects), 'error': resp.error, 'checked_at': iso()}
    write_json(link_status_path(), link_status)
    return {'external_unique': len(urls), 'checked_now': len(results), 'skipped_cap': max(0, len(due) - cap)}


def pagespeed(cfg, fetcher, urls, api_key=None):
    """Optional Lighthouse lab data + CrUX field data via the public PageSpeed Insights API."""
    out = []
    pcfg = cfg.get('psi', {})
    for url in urls[:pcfg.get('max_urls', 4)]:
        query = {'url': url, 'strategy': pcfg.get('strategy', 'mobile'), 'category': 'performance'}
        if api_key:
            query['key'] = api_key
        endpoint = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed?' + urllib.parse.urlencode(query)
        resp = fetcher.fetch(endpoint, accept='application/json', internal_only=False, timeout=120,
                             max_bytes=20_000_000)
        row = {'url': url, 'status': resp.status, 'error': resp.error, 'measured_at': iso()}
        if resp.ok:
            try:
                data = resp.json()
            except ValueError:
                data = {}
            lh = data.get('lighthouseResult', {})
            audits = lh.get('audits', {})
            score = (lh.get('categories', {}).get('performance') or {}).get('score')
            row['lab'] = {'performance_score': score,
                          **{k: (audits.get(k) or {}).get('numericValue') for k in
                             ('largest-contentful-paint', 'cumulative-layout-shift', 'total-blocking-time',
                              'first-contentful-paint', 'speed-index')}}
            field = data.get('loadingExperience', {})
            row['field'] = {'overall_category': field.get('overall_category'),
                            'origin_fallback': field.get('origin_fallback', False),
                            'metrics': {k: {'percentile': v.get('percentile'), 'category': v.get('category')}
                                        for k, v in (field.get('metrics') or {}).items()}}
        elif not row['error']:
            row['error'] = f'HTTP {resp.status}'
        out.append(row)
    return out
