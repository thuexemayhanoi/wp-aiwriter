"""Phase 4: content quality, duplication, cannibalization, sources, NAP/price and gaps.

Similarity scores are signals, not verdicts: near-duplicates and cannibalization pairs are
NEEDS_REVIEW until a human (ideally with GSC query data) confirms them.
"""
from collections import Counter, defaultdict
import re

from . import common
from .corpus import key_of
from .issues import make
from .textutil import STOPWORDS, ascii_fold, candidate_pairs, cosine, jaccard, norm, syllables

LEGAL = re.compile(r'(nghị định|thông tư|(?<!quy )\bluật\b|xử phạt|mức phạt|bị phạt|giấy phép lái xe|bằng lái|'
                   r'nồng độ cồn|tốc độ tối đa|đăng ký xe|quy định của pháp luật|theo quy định pháp luật|'
                   r'cảnh sát giao thông)', re.I)
MONEY = re.compile(r'(?<![\w.,])(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s?(k|nghìn|ngàn|đ|đồng|vnđ|vnd|triệu|usd|\$)(?!\w)', re.I)
PHONE = re.compile(r'(?<![\d+])(?:\+84[\s.]?|0)(?:[235789]\d)(?:[\s.]?\d){7}(?!\d)')
EMAIL = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
YEAR = re.compile(r'(?<!\d)(20[12]\d)(?!\d)')
TRUST_PAGES = {'about': ('gioi-thieu', 'about', 've-chung-toi'), 'contact': ('lien-he', 'contact'),
               'privacy': ('bao-mat', 'privacy', 'quyen-rieng-tu'),
               'terms': ('dieu-khoan', 'terms', 'chinh-sach')}
UTILITY_PAGES = ('lien-he', 'contact')


def phone_digits(value):
    digits = re.sub(r'\D', '', value or '')
    return '0' + digits[2:] if digits.startswith('84') else digits


def snippet(text, start, end, pad=60):
    return '…' + ' '.join(text[max(0, start - pad):end + pad].split()) + '…'


def official(href, domains):
    h = common.host(href)
    return any(h == d or h.endswith('.' + d) for d in domains)


def audit(cfg, corpus, records, terms, gsc=None, duplicates=None):
    th = cfg['thresholds']
    duplicates = duplicates or {}
    # A published copy is reported once (T-DUPLICATE-COPY); its original carries every comparison.
    copies = set(duplicates)
    issues, cannibal_rows, gap_rows = [], [], []
    published = {k: r for k, r in corpus.records.items()}
    domains = cfg.get('official_source_domains', [])
    phones_by_page = defaultdict(set)
    emails = Counter()
    current_year = common.now().year

    for key, r in published.items():
        text = corpus.text.get(key, '')
        for m in PHONE.finditer(text):
            phones_by_page[phone_digits(m.group(0))].add(r['url'])
        emails.update(e.lower() for e in EMAIL.findall(text))
        if key in copies:
            continue
        words = r.get('word_count', 0)
        if r['type'] == 'post':
            if words < th['thin_words_p1']:
                issues.append(make('C-THIN', r, priority='P1', evidence=f'{words} từ (âm tiết)'))
            elif words < th['thin_words_p2']:
                issues.append(make('C-THIN', r, evidence=f'{words} từ (âm tiết)'))
            if not r.get('external_links'):
                issues.append(make('C-NO-SOURCES', r, evidence='0 liên kết ra ngoài trong nội dung'))
        elif r['type'] == 'page' and words < th['thin_words_p1'] and not any(s in r.get('slug', '') for s in UTILITY_PAGES):
            issues.append(make('C-THIN-PAGE', r, evidence=f'{words} từ trong nội dung trang qua REST '
                                                          '(theme có thể hiển thị thêm phần động như danh sách bài)'))
        legal = LEGAL.findall(text)
        if legal and r['type'] == 'post':
            if not any(official(l['href'], domains) for l in r.get('external_links', [])):
                issues.append(make('C-LEGAL-NO-OFFICIAL-SOURCE', r,
                                   evidence='nhắc: ' + ', '.join(sorted({x.lower() for x in legal})[:6])))
        fines, prices = [], []
        for m in MONEY.finditer(text):
            window = norm(text[max(0, m.start() - 80):m.end() + 40])
            (fines if 'phạt' in window else prices).append(snippet(text, m.start(), m.end()))
        if fines:
            issues.append(make('C-FINE-AMOUNT', r, evidence=' | '.join(fines[:3]), impact=len(fines)))
        if prices:
            issues.append(make('C-PRICE-MENTION', r, evidence=' | '.join(prices[:3]), impact=len(prices)))
        years = sorted({int(y) for y in YEAR.findall(text) if int(y) < current_year})
        if years and (legal or MONEY.search(text)):
            issues.append(make('C-TIME-SENSITIVE', r, evidence=f'nhắc năm {years[-3:]} cùng nội dung pháp lý/giá'))

    # NAP consistency.
    business = cfg.get('business') or {}
    known = {phone_digits(p) for p in business.get('phones', [])}
    nap = {'phones': {p: sorted(u)[:10] for p, u in phones_by_page.items()},
           'phone_pages': {p: len(u) for p, u in phones_by_page.items()},
           'emails': dict(emails.most_common(10)), 'configured_business': bool(business.get('name')),
           'configured_phones': sorted(known)}
    unknown = [p for p in phones_by_page if known and p not in known]
    if unknown:
        issues.append(make('C-NAP-INCONSISTENT', url=cfg['site_url'] + '/', key_extra='nap',
                           verification='VERIFIED', evidence=f'số không khớp NAP đã cấu hình: {unknown[:5]}'))
    elif not known and len(phones_by_page) > 1:
        issues.append(make('C-NAP-INCONSISTENT', url=cfg['site_url'] + '/', key_extra='nap',
                           evidence='nhiều số điện thoại khác nhau: ' + '; '.join(
                               f'{p} ({len(u)} trang, ví dụ {sorted(u)[0]})'
                               for p, u in sorted(phones_by_page.items(), key=lambda kv: -len(kv[1]))[:6])))

    # Duplicates and near-duplicates (5-syllable shingles on candidate pairs).
    pairs = candidate_pairs(corpus.body_pruned, 0.35)
    near = []
    for (a, b), _ in sorted(pairs.items(), key=lambda kv: -kv[1]):
        if a in copies or b in copies:
            continue
        j = jaccard(corpus.shingle_set(a), corpus.shingle_set(b))
        if j >= th['near_duplicate_jaccard']:
            near.append((a, b, j))
    for a, b, j in near:
        ra, rb = published[a], published[b]
        code = 'C-DUPLICATE-CONTENT' if j >= th['duplicate_jaccard'] else 'C-NEAR-DUPLICATE'
        issues.append(make(code, ra, key_extra=key_of(rb), evidence=f'Jaccard 5-shingle={j:.2f} với {rb["url"]}',
                           impact=int(j * 10)))

    # Cannibalization: title similarity (all pairs) and body similarity.
    gsc_pairs = (gsc or {}).get('shared_query_pairs', {})
    keys = sorted(published)
    title_vecs = corpus.titles.vectors
    candidates = candidate_pairs({k: title_vecs.get(k, {}) for k in keys}, th['cannibal_title_cosine'])
    for (a, b), _ in candidates.items():
        if a in copies or b in copies:
            continue
        tcos = cosine(title_vecs.get(a, {}), title_vecs.get(b, {}))
        if tcos < th['cannibal_title_cosine']:
            continue
        bcos = corpus.body_cos(a, b)
        if bcos < th['cannibal_body_cosine']:
            continue
        ra, rb = published[a], published[b]
        shared = sorted((set(syllables(ra['title'])) & set(syllables(rb['title']))) - STOPWORDS)
        same_cluster = (ra.get('categories') or [None])[0] == (rb.get('categories') or [None])[0]
        gsc_shared = gsc_pairs.get(f"{ra['url']}|{rb['url']}") or gsc_pairs.get(f"{rb['url']}|{ra['url']}")
        verification = 'VERIFIED' if gsc_shared else 'NEEDS_REVIEW'
        recommendation = ('Hai bài cùng cụm, tiêu đề và nội dung rất gần: phân biệt rõ search intent hoặc hợp nhất (301) sau duyệt'
                          if same_cluster else 'Khác cụm nhưng trùng intent: làm rõ góc tiếp cận, liên kết qua lại thay vì cạnh tranh')
        cannibal_rows.append({
            'post_id_a': ra['id'], 'matrix_id_a': ra.get('matrix_id') or '', 'url_a': ra['url'], 'title_a': ra['title'],
            'category_a': (ra.get('category_paths') or [''])[0],
            'post_id_b': rb['id'], 'matrix_id_b': rb.get('matrix_id') or '', 'url_b': rb['url'], 'title_b': rb['title'],
            'category_b': (rb.get('category_paths') or [''])[0],
            'title_similarity': round(tcos, 3), 'body_similarity': round(bcos, 3),
            'shared_title_terms': ' '.join(shared[:10]), 'same_cluster': 'yes' if same_cluster else 'no',
            'gsc_shared_queries': gsc_shared or '', 'verification': verification,
            'recommendation': recommendation,
        })
        issues.append(make('C-CANNIBALIZATION', ra, key_extra=key_of(rb), verification=verification,
                           evidence=f'title cos={tcos:.2f}, body cos={bcos:.2f} với {rb["url"]}',
                           impact=int((tcos + bcos) * 5)))
    cannibal_rows.sort(key=lambda row: -(row['title_similarity'] + row['body_similarity']))

    gap_rows = content_gaps(cfg, corpus, published, terms, gsc)
    ext_hosts = Counter()
    for r in published.values():
        ext_hosts.update({common.host(l['href']) for l in r.get('external_links', [])})
    stats = {'near_duplicate_pairs': len(near), 'cannibalization_pairs': len(cannibal_rows),
             'gap_rows': len(gap_rows), 'nap': nap, 'duplicate_copies': len(duplicates),
             'top_external_domains': dict(ext_hosts.most_common(15))}
    return issues, cannibal_rows, gap_rows, stats


SOURCE_LINE = re.compile(r'(truy cập|nguồn|tham khảo|accessed|retrieved)', re.I)
PHRASE_TOKEN = re.compile(r'\w+|[.!?;:,()"“”]', re.UNICODE)


def prose_tokens(blocks):
    """Syllables of a post's prose: citation/source lines and link lists are left out, and
    punctuation stays as a token so phrases never run across sentences."""
    toks = []
    for full, segments in blocks:
        linked = sum(len(t) for t, is_link in segments if is_link)
        if not full or SOURCE_LINE.search(full) or linked >= 0.5 * len(full):
            continue
        toks.extend(PHRASE_TOKEN.findall(norm(full)))
        toks.append('.')
    return toks


def frequent_bigrams(token_lists, min_share=0.3):
    """Bigrams present in at least ``min_share`` of the documents of one cluster."""
    df = Counter()
    for toks in token_lists:
        df.update(set(zip(toks, toks[1:])))
    floor = max(3, int(len(token_lists) * min_share))
    return {bg for bg, n in df.items() if n >= floor}


def cluster_subtopics(token_lists, titles, global_share, max_len=5, bind=0.6, min_lift=2.0, max_global=0.5,
                      widespread=frozenset()):
    """Phrases that characterise one cluster but no title names: [(phrase, docs), ...].

    Bigrams frequent in the cluster are kept only when they are cluster-specific (doc share at
    least ``min_lift`` times the site-wide share; boilerplate such as "kết luận" or "nguồn tham
    khảo" occurs everywhere), then grown along dominant neighbours so fragments such as
    "nguồn tham" or "hiểm cài" become whole phrases ("nguồn tham khảo", "mũ bảo hiểm cài quai").
    """
    def usable(tok):
        return tok[:1].isalnum() and tok not in STOPWORDS and not tok.isdigit() and len(tok) > 1
    size = max(1, len(token_lists))
    doc_bigrams = Counter()
    for toks in token_lists:
        doc_bigrams.update({(a, b) for a, b in zip(toks, toks[1:]) if usable(a) and usable(b)})
    floor = max(3, int(size * 0.3))
    candidates = []
    for (a, b), n in doc_bigrams.most_common(400):
        if n < floor:
            break
        if (a, b) in widespread:  # frequent in many clusters: generic vocabulary, not a subtopic
            continue
        share = global_share(a, b)
        if share > max_global or (n / size) < min_lift * share:
            continue
        candidates.append(((a, b), n))
    wanted = {bg for bg, _ in candidates}
    positions = defaultdict(list)
    for d, toks in enumerate(token_lists):
        for s in range(len(toks) - 1):
            if (toks[s], toks[s + 1]) in wanted:
                positions[(toks[s], toks[s + 1])].append((d, s))

    def grow(bigram):
        """Extend along the neighbour shared by most occurrences ("thông đường" → "an toàn giao thông đường bộ")."""
        phrase, occ = list(bigram), positions[bigram]
        while len(phrase) < max_len:
            right = Counter(token_lists[d][s + len(phrase)] for d, s in occ if s + len(phrase) < len(token_lists[d]))
            tok, cnt = right.most_common(1)[0] if right else ('', 0)
            if not usable(tok) or cnt < bind * len(occ):
                break
            occ = [(d, s) for d, s in occ if s + len(phrase) < len(token_lists[d]) and token_lists[d][s + len(phrase)] == tok]
            phrase.append(tok)
        while len(phrase) < max_len:
            left = Counter(token_lists[d][s - 1] for d, s in occ if s > 0)
            tok, cnt = left.most_common(1)[0] if left else ('', 0)
            if not usable(tok) or cnt < bind * len(occ):
                break
            occ = [(d, s - 1) for d, s in occ if s > 0 and token_lists[d][s - 1] == tok]
            phrase.insert(0, tok)
        return ' '.join(phrase)

    found = {}
    for bigram, n in candidates:
        phrase = grow(bigram)
        words = phrase.split()
        pairs = list(zip(words, words[1:]))
        if any(phrase in t for t in titles) or 2 * sum(p in widespread for p in pairs) >= len(pairs):
            continue
        found[phrase] = max(n, found.get(phrase, 0))
    longest = [p for p in found if not any(p != q and f' {p} ' in f' {q} ' for q in found)]
    return sorted(((p, found[p]) for p in longest), key=lambda kv: -kv[1])


def content_gaps(cfg, corpus, published, terms, gsc):
    rows = []
    cats = terms.get('categories', [])
    for c in cats:
        if c.get('count', 0) == 0 and c.get('slug') not in ('uncategorized', 'chua-phan-loai'):
            rows.append({'cluster': c.get('path'), 'gap_type': 'EMPTY_CATEGORY', 'priority': 'P3',
                         'evidence': f"chuyên mục {c.get('link')} có 0 bài", 'verification': 'VERIFIED',
                         'suggested_action': 'Xác nhận có cần chuyên mục; nếu không, chủ sở hữu quyết định ẩn/gộp (không tự xóa).'})
    clusters = defaultdict(list)
    for k, r in published.items():
        if r['type'] == 'post' and r.get('categories'):
            clusters[r['categories'][0]].append(k)
    path_of = {c['id']: c.get('path') for c in cats}
    titles = [' '.join(syllables(r['title'])) for r in published.values()]
    n_docs = max(1, len(corpus.text))
    tokens = {cid: [prose_tokens(corpus.blocks(k)) for k in members] for cid, members in clusters.items()}
    spread = Counter()
    for toks in tokens.values():
        spread.update(frequent_bigrams(toks))
    widespread = frozenset(bg for bg, n in spread.items() if n >= max(3, len(clusters) // 4))
    for cid, members in clusters.items():
        if len(members) < 5:
            rows.append({'cluster': path_of.get(cid), 'gap_type': 'THIN_CLUSTER', 'priority': 'P3',
                         'evidence': f'{len(members)} bài', 'verification': 'VERIFIED',
                         'suggested_action': 'Cụm ít bài: cân nhắc bổ sung chủ đề hỗ trợ trong đợt viết sau (cần duyệt).'})
        uncovered = cluster_subtopics(tokens[cid], titles, lambda a, b: corpus.body.df.get(f'{a}_{b}', 0) / n_docs,
                                      widespread=widespread)
        if uncovered:
            rows.append({'cluster': path_of.get(cid), 'gap_type': 'FREQUENT_SUBTOPIC_WITHOUT_DEDICATED_TITLE',
                         'priority': 'P3', 'verification': 'NEEDS_REVIEW',
                         'evidence': ', '.join(f"{phrase} ({n}/{len(members)} bài)" for phrase, n in uncovered[:6]),
                         'suggested_action': 'Giả thuyết: chủ đề con đặc trưng của cụm được nhắc nhiều nhưng chưa có bài riêng. '
                                             'Xác minh nhu cầu tìm kiếm (GSC/keyword) trước khi lập kế hoạch.'})
    pages = [r for r in published.values() if r['type'] == 'page']
    names = ' '.join(f"{r['slug']} {ascii_fold(r['title']).replace(' ', '-')}" for r in pages)
    for name, needles in TRUST_PAGES.items():
        if not any(n in names for n in needles):
            rows.append({'cluster': 'Site', 'gap_type': f'TRUST_PAGE_MISSING:{name}', 'priority': 'P2',
                         'evidence': 'không tìm thấy trang có slug ' + '/'.join(needles) + ' trên blog',
                         'verification': 'NEEDS_REVIEW',
                         'suggested_action': 'Kiểm tra trang tương ứng có ở domain chính không; E-E-A-T cần thông tin minh bạch (không tự tạo nội dung doanh nghiệp).'})
    if not gsc or gsc.get('status') != 'OK':
        rows.append({'cluster': 'Site', 'gap_type': 'QUERY_GAPS_BLOCKED', 'priority': 'P3', 'verification': 'BLOCKED',
                     'evidence': 'không có dữ liệu Google Search Console',
                     'suggested_action': 'Kết nối GSC để tìm truy vấn có hiển thị nhưng chưa có trang phù hợp.'})
    else:
        for q in gsc.get('query_gaps', [])[:50]:
            rows.append({'cluster': 'GSC', 'gap_type': 'QUERY_WITHOUT_STRONG_PAGE', 'priority': 'P2',
                         'verification': 'VERIFIED', 'evidence': q['evidence'],
                         'suggested_action': 'Cập nhật bài gần nhất để trả lời truy vấn (ưu tiên cập nhật thay vì URL mới).'})
    return rows
