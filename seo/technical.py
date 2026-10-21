"""Phase 2: technical SEO audit from the inventory, crawl summaries and site probes."""
from collections import Counter, defaultdict

from . import common
from .common import normalize_url, same_page
from .issues import make
from .textutil import norm

KEY_SCHEMA_TYPES = {'Organization', 'LocalBusiness', 'WebSite', 'WebPage', 'Article', 'BlogPosting',
                    'NewsArticle', 'BreadcrumbList', 'FAQPage', 'Product', 'AutoRental'}
ARTICLE_TYPES = {'Article', 'BlogPosting', 'NewsArticle', 'TechArticle'}
OTHER_SEO_PLUGINS = {'seo-by-rank-math', 'all-in-one-seo-pack', 'autodescription', 'wp-seopress',
                     'slim-seo', 'squirrly-seo', 'seo-simple-pack'}
DEFAULT_CATEGORY_SLUGS = ('uncategorized', 'chua-phan-loai')


def _robots_text(page, record=None):
    parts = [page.get('meta_robots') or '', page.get('x_robots_tag') or '']
    if record and record.get('yoast'):
        robots = record['yoast'].get('robots') or {}
        parts.append(robots.get('index', ''))
    return ','.join(parts).lower()


def _status_of(url, link_status, records_by_url):
    page = (records_by_url.get(url) or {}).get('page')
    if page:
        return page.get('status')
    entry = link_status.get(url) or link_status.get(url.rstrip('/') + '/')
    return entry.get('status') if entry else None


def check_page(cfg, page, record, kind, link_status, records_by_url, issues, groups):
    th = cfg['thresholds']
    url = record.get('url') if record else page.get('url')
    target = record if record else {'url': url, 'type': kind}
    status = page.get('status', 0)
    if status == 0:
        issues.append(make('T-HTTP-UNREACHABLE', target, evidence=page.get('error', 'no response')))
        return
    if status >= 400:
        code = 'T-ARCHIVE-ERROR' if kind not in ('post', 'page') else 'T-HTTP-ERROR'
        issues.append(make(code, target, evidence=f'HTTP {status}; final={page.get("final_url")}'))
        return
    if page.get('redirects'):
        chain = ' → '.join(f"{h['status']} {h['to']}" for h in page['redirects'])
        if kind in ('post', 'page'):
            issues.append(make('T-REDIRECTED-URL', target, evidence=f'{url} → {chain}'))
    if status != 200:
        return
    if kind.endswith('-paged'):
        return
    robots = _robots_text(page, record)
    if 'noindex' in robots:
        code = 'T-NOINDEX' if kind in ('post', 'page', 'home') else 'T-ARCHIVE-NOINDEX'
        issues.append(make(code, target, evidence=f'meta robots="{page.get("meta_robots")}"; '
                                                  f'X-Robots-Tag="{page.get("x_robots_tag")}"'))
        # Yoast omits canonical/description on noindex URLs by design; other tag checks are moot.
        return
    final_url = page.get('final_url') or url
    canonicals = list(dict.fromkeys(normalize_url(c, final_url) for c in page.get('canonicals', []) if c))
    if not canonicals:
        issues.append(make('T-CANONICAL-MISSING', target, evidence='no <link rel="canonical"> in HTML'))
    else:
        if len(canonicals) > 1:
            issues.append(make('T-CANONICAL-MULTIPLE', target, evidence=' | '.join(canonicals)))
        canonical = canonicals[0]
        if not common.is_internal(canonical, cfg):
            issues.append(make('T-CANONICAL-CROSS-DOMAIN', target, evidence=f'canonical={canonical}'))
        elif not same_page(canonical, final_url):
            issues.append(make('T-CANONICAL-MISMATCH', target, evidence=f'page={final_url}; canonical={canonical}'))
            cstatus = _status_of(canonical, link_status, records_by_url)
            if cstatus is not None and cstatus != 200:
                issues.append(make('T-CANONICAL-TARGET-BAD', target, evidence=f'canonical {canonical} → HTTP {cstatus}'))
        if record and record.get('yoast') and record['yoast'].get('canonical'):
            ycanon = normalize_url(record['yoast']['canonical'])
            if ycanon and not same_page(ycanon, canonical):
                issues.append(make('T-YOAST-CANONICAL-DIFF', target, evidence=f'html={canonical}; yoast={ycanon}'))
    title = page.get('title') or ''
    if not title:
        issues.append(make('T-TITLE-MISSING', target))
    else:
        groups['title'][norm(title)].append((target, title))
        if len(title) > th['title_max_chars']:
            issues.append(make('T-TITLE-LONG', target, evidence=f'{len(title)} ký tự: {title}'))
        elif len(title) < th['title_min_chars']:
            issues.append(make('T-TITLE-SHORT', target, evidence=f'{len(title)} ký tự: {title}'))
    desc = page.get('meta_description') or ''
    if (page.get('meta_description_count') or 0) > 1:
        issues.append(make('T-META-DESC-MULTIPLE', target, evidence=f"{page['meta_description_count']} thẻ meta description"))
    if not desc:
        issues.append(make('T-META-DESC-MISSING', target, evidence='no <meta name="description">'))
    else:
        groups['description'][norm(desc)].append((target, desc))
        if len(desc) > th['description_max_chars']:
            issues.append(make('T-META-DESC-LONG', target, evidence=f'{len(desc)} ký tự'))
        elif len(desc) < th['description_min_chars']:
            issues.append(make('T-META-DESC-SHORT', target, evidence=f'{len(desc)} ký tự: {desc}'))
    h1 = page.get('h1') or []
    if not h1:
        issues.append(make('T-H1-MISSING', target))
    elif len(h1) > 1:
        issues.append(make('T-H1-MULTIPLE', target, evidence=' | '.join(h[:80] for h in h1[:5])))
    if record and h1 and kind == 'post':
        if not any(norm(record['title']) in norm(h) or norm(h) in norm(record['title']) for h in h1):
            issues.append(make('T-H1-TITLE-MISMATCH', target, evidence=f'H1="{h1[0][:100]}"; title="{record["title"][:100]}"'))
    if record and record.get('headings') is not None and kind in ('post', 'page'):
        # Content headings only: theme widgets/footers use arbitrary heading levels.
        outline = [int(h[0][1]) for h in record.get('headings', []) if int(h[0][1]) >= 2]
        jumps = [(a, b) for a, b in zip([2] + outline, outline) if b - a > 1]
        if jumps:
            issues.append(make('T-HEADING-SKIP', target, evidence=f'h{jumps[0][0]} → h{jumps[0][1]}'))
    if not page.get('viewport'):
        issues.append(make('T-VIEWPORT-MISSING', target))
    lang = (page.get('lang') or '').lower()
    if lang and not lang.startswith('vi'):
        issues.append(make('T-LANG-MISMATCH', target, evidence=f'lang="{lang}"'))
    if page.get('mixed_content'):
        issues.append(make('T-MIXED-CONTENT', target, evidence=', '.join(page['mixed_content'][:5])))
    jl = page.get('jsonld') or {}
    for err in jl.get('errors', [])[:1]:
        issues.append(make('T-SCHEMA-INVALID', target, evidence=err))
    types = Counter()
    for node in jl.get('nodes', []):
        for t in node.get('types', []):
            if t in KEY_SCHEMA_TYPES:
                types[t] += 1
    dupes = {t: n for t, n in types.items() if n > 1}
    if dupes:
        origins = Counter(n['origin'] for n in jl.get('nodes', []))
        issues.append(make('T-SCHEMA-DUPLICATE-TYPE', target,
                           evidence=f'{dupes}; JSON-LD blocks by origin={dict(origins)}'))
    if (jl.get('sources') or {}).get('other'):
        other_types = sorted({t for n in jl.get('nodes', []) if n.get('origin') == 'other' for t in n.get('types', [])})
        issues.append(make('T-SCHEMA-NON-YOAST', target,
                           evidence=f"{jl['sources']['other']} block JSON-LD ngoài Yoast; loại: {other_types}"))
    if kind == 'post':
        article = [n for n in jl.get('nodes', []) if ARTICLE_TYPES & set(n.get('types', []))]
        if not article:
            issues.append(make('T-SCHEMA-ARTICLE-MISSING', target, evidence=f"types={sorted(jl.get('types', {}))}"))
        else:
            wanted = ('headline', 'datePublished', 'author') + (('image',) if record.get('featured_media') else ())
            missing = [k for k in wanted if k not in article[0].get('keys', [])]
            if missing:
                issues.append(make('T-SCHEMA-ARTICLE-INCOMPLETE', target, evidence='thiếu: ' + ', '.join(missing)))
    if page.get('elapsed_ms', 0) > 3000:
        issues.append(make('T-SLOW-RESPONSE', target, evidence=f"{page['elapsed_ms']} ms HTML (GitHub runner)"))


def audit(cfg, records, site, terms, state, link_status, psi=None, duplicates=None):
    th = cfg['thresholds']
    issues = []
    by_key = {f"{r['type']}:{r['id']}": r for r in records}
    for copy_key, original_key in sorted((duplicates or {}).items()):
        copy, original = by_key[copy_key], by_key[original_key]
        issues.append(make('T-DUPLICATE-COPY', copy, impact=5,
                           evidence=(f"trùng {'nội dung' if copy.get('content_sha256') == original.get('content_sha256') else 'matrix_id'} "
                                     f"với WP {original['id']} {original['url']} (Excel #{original.get('matrix_id') or '?'}); "
                                     f"chuyên mục bản này: {(copy.get('category_paths') or [''])[0]}")))
    groups = {'title': defaultdict(list), 'description': defaultdict(list)}
    records_by_url = {r['url']: r for r in records}

    for matrix_id, wp_id in state.get('ledger_verified_missing_from_wordpress', []):
        issues.append(make('T-LEDGER-MISSING', {'id': wp_id, 'type': 'post', 'matrix_id': matrix_id, 'url': ''},
                           evidence=f'Excel #{matrix_id} → WP {wp_id} VERIFIED in data/publication-state.json, absent from public /wp/v2/posts'))
    for kind, stat in (state.get('sync_stats') or {}).items():
        for item_id in stat.get('removed', []):
            issues.append(make('T-INVENTORY-REMOVED', {'id': item_id, 'type': kind, 'url': ''},
                               evidence=f'{kind} {item_id} was in the previous index'))

    copies = set(duplicates or {})
    default_cats = {c['id'] for c in terms.get('categories', []) if c.get('slug') in DEFAULT_CATEGORY_SLUGS}
    for r in records:
        page = r.get('page')
        if not page or f"{r['type']}:{r['id']}" in copies:
            continue  # a published copy is reported once as T-DUPLICATE-COPY
        check_page(cfg, page, r, r['type'], link_status, records_by_url, issues, groups)
        if r['type'] == 'post' and set(r.get('categories') or []) & default_cats:
            issues.append(make('T-UNCATEGORIZED', r, evidence='chuyên mục: ' + ', '.join(r.get('category_paths') or [])))
        if page.get('status') != 200:
            continue
        missing_alt = [i['src'] for i in r.get('images', []) if i.get('alt') is None or not str(i.get('alt')).strip()]
        if missing_alt:
            issues.append(make('T-IMG-ALT-MISSING', r, evidence=f'{len(missing_alt)} ảnh trong nội dung: ' + ', '.join(missing_alt[:3]),
                               impact=len(missing_alt)))
        no_dims = [i['src'] for i in r.get('images', []) if not (i.get('width') and i.get('height'))]
        if no_dims:
            issues.append(make('T-IMG-NO-DIMENSIONS', r, evidence=f'{len(no_dims)} ảnh: ' + ', '.join(no_dims[:3])))
        heavy, broken = [], []
        for img in r.get('images', []) + ([{'src': r['featured_image']['url']}] if r.get('featured_image') else []):
            info = (site.get('images') or {}).get(img['src'])
            size = (r.get('featured_image') or {}).get('filesize') if img['src'] == (r.get('featured_image') or {}).get('url') else None
            size = size or (info or {}).get('bytes')
            if info and info.get('status') not in (200, None):
                broken.append(f"{img['src']} (HTTP {info['status']})")
            if size and size > th['image_max_bytes']:
                heavy.append(f"{img['src']} ({size // 1024} KB)")
        if heavy:
            issues.append(make('T-IMG-HEAVY', r, evidence='; '.join(heavy[:3]), impact=len(heavy)))
        if broken:
            issues.append(make('T-IMG-BROKEN', r, evidence='; '.join(broken[:3])))
        if r['type'] == 'post' and not r.get('featured_media'):
            issues.append(make('T-FEATURED-IMAGE-MISSING', r, evidence='featured_media=0'))
        if not (page.get('og') or {}).get('og:image') and not (r.get('yoast') or {}).get('og_image'):
            issues.append(make('T-OG-IMAGE-MISSING', r))

    # Home and archives.
    archives = site.get('archives') or {}
    cat_by_link = {c['link']: c for c in terms.get('categories', []) if c.get('link')}
    breadcrumbs_missing = 0
    microdata_pages = 0
    for url, page in archives.items():
        kind = page.get('kind', 'archive')
        pseudo = {'url': url, 'type': kind}
        if kind == 'category' and url in cat_by_link:
            pseudo['category_paths'] = [cat_by_link[url].get('path', '')]
        check_page(cfg, page, pseudo, kind, link_status, records_by_url, issues, groups)
        if kind == 'category' and url in cat_by_link and page.get('status') == 200:
            cat = cat_by_link[url]
            if not cat.get('description') and cat.get('count', 0) > 0 and cat.get('slug') not in DEFAULT_CATEGORY_SLUGS:
                issues.append(make('T-ARCHIVE-NO-DESCRIPTION', pseudo, evidence=f"{cat.get('path')} ({cat.get('count')} bài)"))
    for r in records:
        page = r.get('page') or {}
        if page.get('status') == 200:
            if 'BreadcrumbList' not in (page.get('jsonld') or {}).get('types', {}):
                breadcrumbs_missing += 1
            if page.get('microdata_types'):
                microdata_pages += 1
    if breadcrumbs_missing:
        issues.append(make('T-SCHEMA-BREADCRUMB-MISSING', url=cfg['site_url'] + '/',
                           evidence=f'{breadcrumbs_missing} bài/trang không có BreadcrumbList', impact=breadcrumbs_missing,
                           key_extra='site'))
    if microdata_pages:
        sample = next((r['page']['microdata_types'] for r in records if (r.get('page') or {}).get('microdata_types')), [])
        issues.append(make('T-SCHEMA-MICRODATA', url=cfg['site_url'] + '/',
                           evidence=f'{microdata_pages} trang có microdata: {sample[:4]}', impact=microdata_pages,
                           key_extra='site'))
    crawled_ok = [r for r in records if (r.get('page') or {}).get('status') == 200]
    not_yoast = [r for r in crawled_ok if r['page'].get('meta_description') and r.get('yoast') is not None
                 and not r['yoast'].get('description')]
    if not_yoast:
        issues.append(make('T-META-DESC-NOT-YOAST', url=cfg['site_url'].rstrip('/') + '/', key_extra='site',
                           impact=len(not_yoast), evidence=(
                               f'{len(not_yoast)}/{len(crawled_ok)} bài/trang: yoast_head_json không có description '
                               f'nhưng HTML có thẻ meta description (nguồn khác Yoast in ra); ví dụ: '
                               + ', '.join(r['url'] for r in not_yoast[:3]))))

    # Duplicate titles / descriptions (rule-verified, owner rewrites).
    for field_, code in (('title', 'T-TITLE-DUPLICATE'), ('description', 'T-META-DESC-DUPLICATE')):
        for value, members in groups[field_].items():
            if len(members) < 2:
                continue
            urls = [m['url'] for m, _ in members]
            for m, original in members:
                others = [u for u in urls if u != m['url']]
                issues.append(make(code, m, evidence=f'"{original[:90]}" cũng dùng ở: ' + ', '.join(others[:4]),
                                   impact=len(members)))

    issues.extend(site_issues(cfg, records, site, records_by_url, link_status))
    psi_summary = None
    if psi:
        psi_summary = psi
        for row in psi:
            lab = row.get('lab') or {}
            field = (row.get('field') or {})
            poor = []
            if lab.get('largest-contentful-paint') and lab['largest-contentful-paint'] > 4000:
                poor.append(f"lab LCP {lab['largest-contentful-paint'] / 1000:.1f}s")
            if lab.get('cumulative-layout-shift') and lab['cumulative-layout-shift'] > 0.25:
                poor.append(f"lab CLS {lab['cumulative-layout-shift']:.2f}")
            if lab.get('performance_score') is not None and lab['performance_score'] < 0.5:
                poor.append(f"lab score {lab['performance_score']:.2f}")
            if field.get('overall_category') == 'SLOW':
                poor.append('CrUX field overall SLOW')
            if poor:
                issues.append(make('T-PERF-POOR', url=row['url'], evidence='; '.join(poor), key_extra='psi'))
    if not psi or not any(row.get('lab') for row in psi):
        issues.append(make('T-CWV-NOT-MEASURED', url=cfg['site_url'] + '/', key_extra='site',
                           evidence='PageSpeed Insights không chạy hoặc không trả dữ liệu trong lần audit này'))
    return issues, {'psi': psi_summary}


def site_issues(cfg, records, site, records_by_url, link_status):
    issues = []
    probes = site.get('probes') or {}
    home = cfg['site_url'].rstrip('/') + '/'
    robots = probes.get('robots') or {}
    site_target = {'url': home, 'type': 'site'}
    if robots.get('status') != 200:
        issues.append(make('T-ROBOTS-UNAVAILABLE', site_target, evidence=f"/robots.txt HTTP {robots.get('status')}", key_extra='robots'))
    else:
        if robots.get('disallow_all_for_star'):
            issues.append(make('T-ROBOTS-DISALLOW-ALL', site_target, evidence='User-agent: * cannot fetch /', key_extra='robots'))
        if not robots.get('sitemaps'):
            issues.append(make('T-ROBOTS-NO-SITEMAP', site_target, key_extra='robots'))
        for url in robots.get('blocked_sample_for_googlebot', []):
            issues.append(make('T-ROBOTS-BLOCKED', records_by_url.get(url) or {'url': url, 'type': 'url'},
                               evidence='robots.txt Disallow matches this URL for Googlebot'))
        blocked_ai = [a for a, v in (robots.get('agents') or {}).items() if not v.get('home')]
        issues.append(make('A-AI-CRAWLER-POLICY', site_target, key_extra='robots',
                           evidence=('Bị chặn: ' + ', '.join(blocked_ai)) if blocked_ai else
                           'Không crawler nào trong danh sách bị chặn ở trang chủ: ' + ', '.join(sorted(robots.get('agents') or {}))))
    sm = probes.get('sitemaps') or {}
    files = sm.get('files') or []
    ok_files = [f for f in files if f.get('status') == 200 and not f.get('error')]
    if not ok_files:
        issues.append(make('T-SITEMAP-UNAVAILABLE', site_target, evidence='; '.join(f"{f['url']} HTTP {f.get('status')} {f.get('error', '')}" for f in files[:3]), key_extra='sitemap'))
    for f in files:
        if f.get('status') != 200 or f.get('error'):
            issues.append(make('T-SITEMAP-FILE-ERROR', url=f['url'], evidence=f"HTTP {f.get('status')} {f.get('error', '')}"))
    sitemap_urls = sm.get('urls') or {}
    if ok_files:
        archive_links = set((site.get('archives') or {}).keys())
        indexable = []
        for r in records:
            page = r.get('page') or {}
            if page.get('status') == 200 and 'noindex' not in _robots_text(page, r):
                indexable.append(r)
        for r in indexable:
            if r['url'] not in sitemap_urls and r['url'].rstrip('/') not in {u.rstrip('/') for u in sitemap_urls}:
                issues.append(make('T-SITEMAP-MISSING-URL', r, evidence='không thấy trong ' + ', '.join(f['url'] for f in ok_files[:2])))
        known = {r['url'] for r in records}
        for url, meta in sitemap_urls.items():
            rec = records_by_url.get(url)
            if rec:
                page = rec.get('page') or {}
                if page.get('status') not in (200, None) or 'noindex' in _robots_text(page, rec):
                    issues.append(make('T-SITEMAP-BAD-URL', rec, evidence=f"HTTP {page.get('status')}; robots={page.get('meta_robots')}; sitemap={meta.get('sitemap')}"))
                continue
            if url in archive_links or url.rstrip('/') + '/' in archive_links:
                page = site['archives'].get(url) or site['archives'].get(url.rstrip('/') + '/') or {}
                if page.get('status') not in (200, None):
                    issues.append(make('T-SITEMAP-BAD-URL', url=url, evidence=f"archive HTTP {page.get('status')}"))
                continue
            status = (link_status.get(url) or {}).get('status')
            if url not in known and status not in (200,):
                issues.append(make('T-SITEMAP-BAD-URL', url=url,
                                   evidence=f"không thuộc inventory bài/trang/chuyên mục; HTTP {status}; sitemap={meta.get('sitemap')}"))
    core = probes.get('core_wp_sitemap') or {}
    if core.get('status') == 200 and not core.get('redirects') and ok_files and \
            not any('wp-sitemap' in f['url'] for f in ok_files):
        issues.append(make('T-SITEMAP-CORE-DUPLICATE', url=home + 'wp-sitemap.xml', evidence='HTTP 200, không chuyển hướng'))
    http = probes.get('http_to_https') or {}
    final = http.get('final_url', '')
    if http.get('status') and not final.startswith('https://'):
        issues.append(make('T-HTTPS-REDIRECT', site_target, evidence=f"http:// → HTTP {http.get('status')} {final}", key_extra='https'))
    soft = probes.get('not_found_probe') or {}
    if soft.get('status') == 200:
        issues.append(make('T-SOFT-404', url=soft.get('url', ''), evidence='URL ngẫu nhiên trả HTTP 200', key_extra='probe'))
    slash = probes.get('no_trailing_slash_probe') or {}
    if slash.get('status') == 200 and not slash.get('redirects'):
        issues.append(make('T-TRAILING-SLASH-DUP', url=slash.get('url', ''), evidence='không có / vẫn trả 200, không redirect', key_extra='probe'))
    plugins = set()
    yoast_seen = False
    for r in records:
        page = r.get('page') or {}
        plugins.update(page.get('plugins') or [])
        yoast_seen = yoast_seen or bool(page.get('yoast_version')) or bool(r.get('yoast'))
    clash = sorted(plugins & OTHER_SEO_PLUGINS)
    if clash and ('wordpress-seo' in plugins or yoast_seen):
        issues.append(make('T-DUPLICATE-SEO-PLUGIN', site_target, evidence='Yoast + ' + ', '.join(clash), key_extra='plugins'))
    if records and not any(r.get('yoast') for r in records):
        issues.append(make('A-YOAST-REST-MISSING', site_target, evidence='không bản ghi REST nào có yoast_head_json', key_extra='yoast'))
    return issues
