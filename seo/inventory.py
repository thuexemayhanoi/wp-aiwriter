"""Phase 0-1: verify the WordPress site and build a normalised content inventory.

Reads only public REST endpoints (published content), paginates every collection and syncs
incrementally by ``modified_gmt``. Full HTML bodies go to a local cache (GitHub Actions cache),
the committed ``data/posts-index.jsonl`` keeps the normalised, reviewable fields.
"""
import html as html_lib
import json
import re
import urllib.parse

from . import common
from .common import iso, normalize_url, read_json, read_jsonl, write_json, write_jsonl
from .crawl import compact_page
from .htmlparse import clean, html_comments, parse
from .textutil import norm, sha256, word_count

LIST_FIELDS = 'id,modified_gmt,link,slug'
POST_FIELDS = ('id,date_gmt,modified_gmt,slug,status,type,link,title,content,excerpt,author,'
               'featured_media,categories,tags,comment_status,template,yoast_head_json')
PAGE_FIELDS = ('id,date_gmt,modified_gmt,slug,status,type,link,title,content,excerpt,author,'
               'featured_media,parent,menu_order,template,yoast_head_json')
TERM_FIELDS = 'id,name,slug,parent,count,description,link,yoast_head_json'
MEDIA_FIELDS = 'id,source_url,alt_text,mime_type,media_details,post,link'
MARKER = re.compile(r'wp-aiwriter:matrix_id=(\d+)')
WARNINGS = []
SLUG_ID = re.compile(r'^excel-(\d+)-')


def index_path():
    return common.path('data/posts-index.jsonl')


def cache_path():
    return common.path('data/seo/cache/content.json.gz')


def state_path():
    return common.path('data/seo/state.json')


def api(cfg, route, params=None):
    url = cfg['site_url'].rstrip('/') + '/wp-json/' + route.lstrip('/')
    if params:
        url += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
    return url


def collection(fetcher, cfg, route, params=None):
    """Every item of a REST collection, following X-WP-TotalPages."""
    params = dict(params or {})
    params.setdefault('per_page', 100)
    items, page, total_pages, total = [], 1, 1, None
    while page <= total_pages:
        data, resp = fetcher.get_json(api(cfg, route, {**params, 'page': page}))
        if not isinstance(data, list):
            raise RuntimeError(f'{route} did not return a JSON array')
        items.extend(data)
        total_pages = int(resp.headers.get('x-wp-totalpages', total_pages) or 1)
        total = int(resp.headers.get('x-wp-total', len(items)) or len(items))
        page += 1
    if total is not None and len(items) != total:
        WARNINGS.append(f'{route}: received {len(items)} items but X-WP-Total says {total}')
    return items


def discover(fetcher, cfg):
    """Phase 0: confirm the REST root belongs to the configured site before anything else."""
    data, resp = fetcher.get_json(api(cfg, ''))
    site_host = urllib.parse.urlsplit(cfg['site_url']).netloc
    home = data.get('home') or data.get('url') or ''
    if urllib.parse.urlsplit(home).netloc.lower() != site_host:
        raise RuntimeError(f'REST root reports home {home!r}, not the configured site {site_host}; refusing to audit')
    namespaces = data.get('namespaces', [])
    return {
        'checked_at': iso(), 'name': clean(data.get('name', '')), 'description': clean(data.get('description', '')),
        'url': data.get('url'), 'home': home, 'gmt_offset': data.get('gmt_offset'),
        'timezone_string': data.get('timezone_string'), 'namespaces': namespaces,
        'yoast_rest_namespace': any(ns.startswith('yoast/') for ns in namespaces),
        'rest_status': resp.status,
    }


def term_paths(terms):
    by_id = {t['id']: t for t in terms}
    out = {}
    for term in terms:
        names, cur, seen = [], term, set()
        while cur and cur['id'] not in seen:
            seen.add(cur['id'])
            names.append(clean(cur.get('name', '')))
            cur = by_id.get(cur.get('parent') or 0)
        out[term['id']] = ' > '.join(reversed(names))
    return out


def yoast_summary(head):
    if not isinstance(head, dict):
        return None
    schema = head.get('schema') or {}
    graph = schema.get('@graph', []) if isinstance(schema, dict) else []
    types = []
    for node in graph:
        if isinstance(node, dict):
            value = node.get('@type', [])
            types.extend([value] if isinstance(value, str) else value)
    robots = head.get('robots') or {}
    return {
        'title': clean(head.get('title', '')), 'description': clean(head.get('description', '')),
        'canonical': head.get('canonical', ''), 'robots': {k: robots[k] for k in sorted(robots)},
        'og_image': bool(head.get('og_image')), 'og_type': head.get('og_type', ''),
        'article_modified_time': head.get('article_modified_time', ''),
        'twitter_card': head.get('twitter_card', ''), 'schema_types': sorted(set(types)),
    }


def repo_file(rel):
    candidate = common.path(rel)
    return candidate if candidate.exists() else common.REPO_ROOT / rel


def topic_lookup():
    rows = json.loads(repo_file('data/topics.json').read_text(encoding='utf-8'))
    by_title = {norm(title): (i, title, category) for i, title, category in rows}
    by_id = {i: (i, title, category) for i, title, category in rows}
    return by_title, by_id


def ledger_by_wp_id():
    ledger = read_json(repo_file('data/publication-state.json'), {'posts': {}}) or {'posts': {}}
    out = {}
    for matrix_id, entry in ledger.get('posts', {}).items():
        if entry.get('wp_id'):
            out[int(entry['wp_id'])] = {'matrix_id': int(matrix_id), **entry}
    return out


def link_lists(parser, base, cfg):
    internal, external = [], []
    for a in parser.anchors:
        href = a.get('href', '').strip()
        if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:', 'sms:')):
            continue
        url = normalize_url(href, base)
        if not url:
            continue
        item = {'href': url, 'anchor': a.get('text', ''), 'rel': a.get('rel', ''),
                'in_heading': a.get('in_heading', False)}
        (internal if common.is_internal(url, cfg) else external).append(item)
    return internal, external


def build_record(item, kind, cfg, paths, tag_names, media_by_id, ledger, topics_by_title, synced_at):
    content_html = (item.get('content') or {}).get('rendered', '')
    title = clean(html_lib.unescape((item.get('title') or {}).get('rendered', '')))
    parser = parse(content_html)
    text = parser.visible_text()
    link = normalize_url(item.get('link', ''))
    internal, external = link_lists(parser, link, cfg)
    matrix_id = None
    for comment in html_comments(content_html):
        found = MARKER.search(comment)
        if found:
            matrix_id = int(found.group(1))
    if matrix_id is None and SLUG_ID.match(item.get('slug', '')):
        matrix_id = int(SLUG_ID.match(item['slug']).group(1))
    if matrix_id is None and kind == 'post' and int(item['id']) in ledger:
        matrix_id = ledger[int(item['id'])]['matrix_id']
    if matrix_id is None and kind == 'post' and norm(title) in topics_by_title:
        matrix_id = topics_by_title[norm(title)][0]
    featured = media_by_id.get(item.get('featured_media') or 0)
    categories = item.get('categories', []) if kind == 'post' else []
    excerpt = clean(parse((item.get('excerpt') or {}).get('rendered', '')).visible_text())
    return {
        'id': int(item['id']), 'type': kind, 'url': link, 'slug': item.get('slug', ''),
        'status': item.get('status', ''), 'title': title, 'matrix_id': matrix_id,
        'date_gmt': item.get('date_gmt', ''), 'modified_gmt': item.get('modified_gmt', ''),
        'author': item.get('author'), 'template': item.get('template', ''),
        'parent': item.get('parent', 0) if kind == 'page' else None,
        'categories': categories, 'category_paths': [paths.get(c, str(c)) for c in categories],
        'tags': [tag_names.get(t, str(t)) for t in item.get('tags', [])] if kind == 'post' else [],
        'excerpt': excerpt[:300], 'featured_media': item.get('featured_media') or 0,
        'featured_image': ({'id': featured['id'], 'url': featured.get('source_url', ''),
                            'alt': clean(featured.get('alt_text', '')),
                            'width': (featured.get('media_details') or {}).get('width'),
                            'height': (featured.get('media_details') or {}).get('height'),
                            'filesize': (featured.get('media_details') or {}).get('filesize')}
                           if featured else None),
        'content_sha256': sha256(content_html), 'word_count': word_count(text),
        'headings': [[f'h{level}', textv] for level, textv in parser.headings],
        'internal_links': internal, 'external_links': external,
        'images': [{'src': normalize_url(img['src'], link) or img['src'], 'alt': img['alt'],
                    'width': img['width'], 'height': img['height']} for img in parser.images],
        'yoast': yoast_summary(item.get('yoast_head_json')),
        'synced_at': synced_at,
    }


def fetch_items(fetcher, cfg, route, ids, fields):
    out = []
    ids = list(ids)
    for start in range(0, len(ids), 50):
        batch = ids[start:start + 50]
        out.extend(collection(fetcher, cfg, route, {'include': ','.join(map(str, batch)),
                                                    '_fields': fields, 'per_page': len(batch)}))
    return out


def sync(cfg, fetcher, full=False):
    """Refresh the inventory; returns (records, report)."""
    synced_at = iso()
    WARNINGS.clear()
    previous = {(r['type'], r['id']): r for r in read_jsonl(index_path())}
    cache = {} if full else (read_json(cache_path(), {}) or {})
    discovery = discover(fetcher, cfg)
    categories = collection(fetcher, cfg, 'wp/v2/categories', {'_fields': TERM_FIELDS, 'hide_empty': 'false'})
    tags = collection(fetcher, cfg, 'wp/v2/tags', {'_fields': TERM_FIELDS, 'hide_empty': 'false'})
    media = collection(fetcher, cfg, 'wp/v2/media', {'_fields': MEDIA_FIELDS})
    paths = term_paths(categories)
    tag_names = {t['id']: clean(t.get('name', '')) for t in tags}
    media_by_id = {m['id']: m for m in media}
    ledger = ledger_by_wp_id()
    topics_by_title, _ = topic_lookup()
    records, stats, new_cache = [], {}, {}
    for kind, route, fields in (('post', 'wp/v2/posts', POST_FIELDS), ('page', 'wp/v2/pages', PAGE_FIELDS)):
        listing = collection(fetcher, cfg, route, {'_fields': LIST_FIELDS})
        wanted = []
        for row in listing:
            key = f'{kind}:{row["id"]}'
            cached = cache.get(key)
            if full or not cached or cached.get('modified_gmt') != row.get('modified_gmt'):
                wanted.append(row['id'])
            else:
                new_cache[key] = cached
        fetched = fetch_items(fetcher, cfg, route, wanted, fields) if wanted else []
        for item in fetched:
            new_cache[f'{kind}:{item["id"]}'] = item
        listed_ids = {row['id'] for row in listing}
        stat = {'listed': len(listing), 'fetched': len(fetched), 'reused': len(listing) - len(fetched),
                'new': 0, 'updated': 0, 'removed': []}
        for item_id in sorted(listed_ids):
            item = new_cache.get(f'{kind}:{item_id}')
            if not item:
                raise RuntimeError(f'{kind} {item_id} listed but not fetched')
            record = build_record(item, kind, cfg, paths, tag_names, media_by_id, ledger, topics_by_title, synced_at)
            old = previous.get((kind, item_id))
            if old is None:
                stat['new'] += 1
            elif old.get('content_sha256') != record['content_sha256'] or old.get('modified_gmt') != record['modified_gmt']:
                stat['updated'] += 1
            elif old.get('synced_at'):
                record['synced_at'] = old['synced_at']  # unchanged record: keep the index line stable
            if old and old.get('page') and old.get('modified_gmt') == record['modified_gmt']:
                record['page'] = compact_page(old['page'])  # keep last crawl result until re-crawled
            records.append(record)
        stat['removed'] = sorted(i for (k, i) in previous if k == kind and i not in listed_ids)
        stats[kind] = stat
    terms = {
        'categories': [{'id': c['id'], 'name': clean(c.get('name', '')), 'slug': c.get('slug'),
                        'parent': c.get('parent', 0), 'count': c.get('count', 0), 'path': paths.get(c['id']),
                        'link': normalize_url(c.get('link', '')),
                        'description': clean(parse(c.get('description', '')).visible_text()),
                        'yoast': yoast_summary(c.get('yoast_head_json'))} for c in categories],
        'tags': [{'id': t['id'], 'name': clean(t.get('name', '')), 'count': t.get('count', 0),
                  'link': normalize_url(t.get('link', ''))} for t in tags],
        'media_count': len(media),
        'media_missing_alt': sum(1 for m in media if (m.get('mime_type') or '').startswith('image/')
                                 and not clean(m.get('alt_text', ''))),
    }
    published_post_ids = {r['id'] for r in records if r['type'] == 'post'}
    ledger_missing = sorted((e['matrix_id'], wp_id) for wp_id, e in ledger.items()
                            if e.get('phase') == 'VERIFIED' and e.get('status') == 'publish'
                            and wp_id not in published_post_ids)
    records.sort(key=lambda r: (r['type'], r['id']))
    write_jsonl(index_path(), records)
    write_json(cache_path(), {k: v for k, v in new_cache.items()}, compress=True)
    write_json(common.path('data/seo/terms.json'), terms)
    state = read_json(state_path(), {}) or {}
    state.update({'last_sync': synced_at, 'discovery': discovery, 'sync_stats': stats,
                  'counts': {'posts': len(published_post_ids),
                             'pages': sum(1 for r in records if r['type'] == 'page'),
                             'categories': len(categories), 'tags': len(tags), 'media': len(media)},
                  'ledger_verified_missing_from_wordpress': ledger_missing,
                  'rest_warnings': list(WARNINGS),
                  'requests': fetcher.requests_made})
    if full:
        state['last_full_sync'] = synced_at
    write_json(state_path(), state)
    return records, {'discovery': discovery, 'stats': stats, 'terms': terms, 'ledger_missing': ledger_missing}


def load_index():
    return read_jsonl(index_path())


def load_content_cache():
    return read_json(cache_path(), {}) or {}


def load_terms():
    return read_json(common.path('data/seo/terms.json'), {}) or {}
