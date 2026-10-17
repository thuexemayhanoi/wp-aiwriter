"""Phase 5: Yoast metadata, AEO/GEO extractability and entity consistency checks.

No ranking or AI-answer inclusion is promised; these checks only make content easier to
crawl, understand and quote accurately.
"""
from collections import Counter, defaultdict
import re

from . import common
from .issues import make
from .textutil import STOPWORDS, ascii_fold, norm, syllables, word_count

QUESTION_HINTS = ('?', 'câu hỏi', 'hỏi đáp', 'faq', 'thắc mắc')
BRAND_LEAD = re.compile(r'thuê\s+xe\s+máy\s+', re.I)
BRAND_PREFIX = re.compile(r'^(cho\s+)?thuê\s+xe\s+máy\s+', re.I)


def brand_mentions(text, first_word):
    """Business names written as "(Cho) Thuê Xe Máy <Name>" whose first word matches the site brand's."""
    found = Counter()
    for m in BRAND_LEAD.finditer(text):
        words = []
        for tok in text[m.end():m.end() + 40].split()[:3]:
            word = tok.strip('.,;:!?()[]"“”')
            if not (word[:1].isupper() and word.isalpha()):
                break
            words.append(word)
            if word != tok:
                break
        if words and words[0] == first_word:
            found[' '.join(words)] += 1
    return found


def brand_audit(cfg, corpus, copies, brand):
    """Compare the brand in schema/site settings with business names written in the content."""
    core = BRAND_PREFIX.sub('', (brand or '').strip()).strip()
    if not core:
        return None
    names = defaultdict(set)
    for key, r in corpus.records.items():
        if key in copies:
            continue
        for name in brand_mentions(corpus.text.get(key, ''), core.split()[0]):
            # "Nguyễn Hà Địa(chỉ)" is the site brand followed by the next block's first word.
            same = norm(name).startswith(norm(core)) or norm(core).startswith(norm(name))
            names[core if same else name].add(r['url'])
    others = {n: urls for n, urls in names.items() if n != core}
    if not others:
        return None
    parts = []
    for name, urls in sorted(others.items(), key=lambda kv: -len(kv[1])):
        slug = ascii_fold(name).replace(' ', '')
        linking = {r['url'] for r in corpus.records.values()
                   if any(slug in common.host(l['href']) for l in r.get('external_links', []))}
        parts.append(f'"{name}" ({len(urls)} URL, ví dụ {sorted(urls)[0]}'
                     + (f'; {len(linking)} URL liên kết tới domain chứa "{slug}"' if linking else '') + ')')
    same = len(names.get(core, ()))
    return make('A-BRAND-MISMATCH', {'url': cfg['site_url'].rstrip('/') + '/', 'type': 'site'}, key_extra='brand',
                impact=sum(len(u) for u in others.values()),
                evidence=f'schema/site: "{brand}"; nội dung: ' + '; '.join(parts)
                         + (f'; "{core}" ({same} URL)' if same else f'; "{core}" không xuất hiện trong nội dung'))
GENERIC_AUTHORS = {'admin', 'administrator', 'quản trị viên', 'editor', 'author', 'user', 'webmaster', 'root', 'test'}


def audit(cfg, corpus, records, site, discovery, duplicates=None):
    th = cfg['thresholds']
    issues = []
    copies = set(duplicates or {})
    org_names, website_names, org_nodes = Counter(), Counter(), 0
    sameas_origins = set()
    author_names, generic_author_posts = Counter(), []
    home_url = cfg['site_url'].rstrip('/') + '/'
    home = ((site.get('archives') or {}).get(home_url)) or {}
    pages = [(key, r, r.get('page') or {}) for key, r in corpus.records.items()]
    pages.append(('home', {'type': 'home', 'url': home_url}, home))
    for key, r, page in pages:
        if page.get('status') not in (200, None):
            continue
        if key == 'home':
            blocks = []
        else:
            blocks = corpus.blocks(key)
        if r['type'] == 'post' and key not in copies:
            first = next((full for full, _ in blocks if full), '')
            n = word_count(first)
            title_terms = {t for t in syllables(r['title']) if t not in STOPWORDS and len(t) > 1}
            overlap = len(title_terms & set(syllables(first))) / max(1, len(title_terms))
            if not (th['direct_answer_min_words'] <= n <= th['direct_answer_max_words']) or overlap < 0.3:
                issues.append(make('A-NO-DIRECT-ANSWER', r,
                                   evidence=f'đoạn đầu {n} từ, trùng {overlap:.0%} thuật ngữ tiêu đề: "{first[:140]}"'))
            headings = [h for _, h in r.get('headings', [])]
            if r['title'].strip().endswith('?') and not any(any(x in norm(h) for x in QUESTION_HINTS) for h in headings):
                issues.append(make('A-NO-FAQ', r, evidence=f'{len(headings)} heading, không heading dạng câu hỏi/FAQ'))
            parser = corpus.parsed.get(key)
            has_structure = any(b['tag'] in ('li', 'td', 'th') for b in (parser.blocks if parser else []))
            if not has_structure:
                issues.append(make('A-NO-STRUCTURE', r, evidence='không có danh sách hoặc bảng'))
            article = [n_ for n_ in (page.get('jsonld') or {}).get('nodes', [])
                       if {'Article', 'BlogPosting', 'NewsArticle'} & set(n_.get('types', []))]
            modified_later = (r.get('modified_gmt') or '')[:10] > (r.get('date_gmt') or '')[:10]
            if article and modified_later and 'dateModified' not in article[0].get('keys', []):
                issues.append(make('A-SCHEMA-DATE-MISSING', r, evidence=(
                    f"bài sửa {r.get('modified_gmt', '')[:10]} sau ngày đăng {r.get('date_gmt', '')[:10]} nhưng Article thiếu dateModified")))
        for node in (page.get('jsonld') or {}).get('nodes', []):
            types = set(node.get('types', []))
            if types & {'Organization', 'LocalBusiness', 'AutoRental'}:
                org_nodes += 1
                if node.get('name'):
                    org_names[node['name'].strip()] += 1
                if 'sameAs' in node.get('keys', []):
                    sameas_origins.add(node.get('origin') or 'other')
            if 'WebSite' in types and node.get('name'):
                website_names[node['name'].strip()] += 1
        if r['type'] == 'post' and key not in copies:
            people = [n_['name'].strip() for n_ in (page.get('jsonld') or {}).get('nodes', [])
                      if 'Person' in n_.get('types', []) and isinstance(n_.get('name'), str)]
            author_names.update(set(people))
            if any(norm(p) in GENERIC_AUTHORS for p in people):
                generic_author_posts.append(r['url'])
    site_target = {'url': cfg['site_url'].rstrip('/') + '/', 'type': 'site'}
    if generic_author_posts:
        issues.append(make('A-AUTHOR-GENERIC', site_target, key_extra='author', impact=len(generic_author_posts),
                           evidence=(f'{len(generic_author_posts)} bài có schema Person (tác giả) tên chung chung: '
                                     + ', '.join(f'"{k}" ({v})' for k, v in author_names.most_common(3) if norm(k) in GENERIC_AUTHORS)
                                     + '; ví dụ: ' + ', '.join(generic_author_posts[:2]))))
    if len(org_names) > 1:
        issues.append(make('A-ENTITY-INCONSISTENT', site_target, key_extra='org',
                           evidence='Organization names: ' + '; '.join(f'{k} ({v})' for k, v in org_names.most_common(5))))
    if len(website_names) > 1:
        issues.append(make('A-ENTITY-INCONSISTENT', site_target, key_extra='website',
                           evidence='WebSite names: ' + '; '.join(f'{k} ({v})' for k, v in website_names.most_common(5))))
    brand = (org_names.most_common(1)[0][0] if org_names else None) or (discovery or {}).get('name')
    mismatch = brand_audit(cfg, corpus, copies, brand)
    if mismatch:
        issues.append(mismatch)
    if org_nodes and 'yoast' not in sameas_origins:
        issues.append(make('A-ORG-SAMEAS-MISSING', site_target, key_extra='org', evidence=(
            f'{org_nodes} node Organization/LocalBusiness; Organization của Yoast không có sameAs'
            + ('; sameAs chỉ có trong schema ngoài Yoast (theme/plugin)' if sameas_origins else ''))))
    issues.append(make('A-FOCUS-KEYPHRASE-BLOCKED', site_target, key_extra='yoast',
                       evidence='focus keyphrase là post meta riêng tư của Yoast; REST công khai không trả về'))
    summary = {
        'organization_names': dict(org_names), 'website_names': dict(website_names),
        'author_names': dict(author_names.most_common(10)), 'generic_author_posts': len(generic_author_posts),
        'rest_site_name': (discovery or {}).get('name'),
        'llms_txt_status': ((site.get('probes') or {}).get('llms_txt') or {}).get('status'),
        'ai_crawlers': ((site.get('probes') or {}).get('robots') or {}).get('agents'),
    }
    return issues, summary
