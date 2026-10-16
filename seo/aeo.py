"""Phase 5: Yoast metadata, AEO/GEO extractability and entity consistency checks.

No ranking or AI-answer inclusion is promised; these checks only make content easier to
crawl, understand and quote accurately.
"""
from collections import Counter

from .issues import make
from .textutil import STOPWORDS, norm, syllables, word_count

QUESTION_HINTS = ('?', 'câu hỏi', 'hỏi đáp', 'faq', 'thắc mắc')
GENERIC_AUTHORS = {'admin', 'administrator', 'quản trị viên', 'editor', 'author', 'user', 'webmaster', 'root', 'test'}


def audit(cfg, corpus, records, site, discovery, duplicates=None):
    th = cfg['thresholds']
    issues = []
    copies = set(duplicates or {})
    org_names, website_names, org_sameas, org_nodes = Counter(), Counter(), False, 0
    author_names, generic_author_posts = Counter(), []
    for key, r in corpus.records.items():
        page = r.get('page') or {}
        if page.get('status') not in (200, None):
            continue
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
                    org_sameas = True
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
    if org_nodes and not org_sameas:
        issues.append(make('A-ORG-SAMEAS-MISSING', site_target, key_extra='org',
                           evidence=f'{org_nodes} node Organization, không node nào có sameAs'))
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
