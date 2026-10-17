"""Phase 3: internal linking engine.

Architecture: Homepage → Pillar (top-level category) → Hub (2nd level) → Silo (3rd level) →
Topic cluster (leaf category) → Supporting posts. Every suggestion carries an anchor that
already exists as plain (unlinked) text in the source article, or is explicitly marked as
needing a newly written sentence. Nothing here edits WordPress.
"""
from collections import Counter, defaultdict, deque
import math
import re

from . import common
from .common import normalize_url
from .corpus import key_of
from .issues import make
from .textutil import STOPWORDS, norm, syllables

WEAK_ANCHORS = {'tại đây', 'ở đây', 'xem thêm', 'bấm vào đây', 'nhấn vào đây', 'click', 'click here', 'link',
                'đây', 'bài viết này', 'bài này', 'chi tiết', 'tham khảo', 'xem', 'đọc thêm', 'here',
                'read more', 'more', 'xem tại đây', 'xem chi tiết', 'nguồn'}
TOKEN = re.compile(r'\w+', re.UNICODE)


class LinkIndex:
    def __init__(self, records, link_status):
        self.by_url = {}
        for r in records:
            for u in {r['url'], ((r.get('page') or {}).get('final_url') or r['url'])}:
                nu = normalize_url(u)
                self.by_url[nu] = key_of(r)
                self.by_url[nu.rstrip('/')] = key_of(r)
        self.link_status = link_status

    def resolve(self, url):
        u = normalize_url(url)
        hit = self.by_url.get(u) or self.by_url.get(u.rstrip('/'))
        if hit:
            return hit
        final = (self.link_status.get(u) or {}).get('final_url')
        if final:
            nf = normalize_url(final)
            return self.by_url.get(nf) or self.by_url.get(nf.rstrip('/'))
        return None


def category_layers(terms):
    cats = {c['id']: c for c in terms.get('categories', [])}

    def chain(cid):
        out, seen = [], set()
        while cid and cid in cats and cid not in seen:
            seen.add(cid)
            out.append(cats[cid])
            cid = cats[cid].get('parent') or 0
        return list(reversed(out))
    return cats, chain


def click_depths(home, page_links, resolve_url):
    """BFS over every crawled page's links (template + content)."""
    graph = defaultdict(set)
    for src, links in page_links.items():
        s = normalize_url(src)
        for dst in links:
            graph[s].add(normalize_url(dst))
    depth = {normalize_url(home): 0}
    queue = deque([normalize_url(home)])
    while queue:
        cur = queue.popleft()
        for nxt in graph.get(cur, ()):  # also follow canonical/final URL aliases
            for alias in {nxt, resolve_url(nxt) or nxt}:
                if alias not in depth:
                    depth[alias] = depth[cur] + 1
                    queue.append(alias)
    return depth


CITATION = re.compile(r'(truy cập|nguồn\s*:|tham khảo\s*:|accessed|retrieved)', re.I)
INNER_PUNCT = '.,!?;:()[]"“”/–—…|'
# Syllables that make a weak anchor edge in Vietnamese ("sang Long Biên", "NVX phù hợp").
EDGE_WEAK = STOPWORDS | {'sang', 'dùng', 'phù', 'hợp', 'nhiều', 'cách', 'nên', 'chọn', 'đi',
                         'khác', 'nhau', 'gì', 'nào', 'gần', 'nhất', 'hằng', 'luôn', 'mới', 'cũ', 'quanh'}


def _cuts_title_compound(window, title, is_compound):
    """True when the window ends (or starts) inside a compound of the title ("tình trạng trạm|sạc")."""
    if not is_compound:
        return False
    size = len(window)
    for k in range(len(title) - size + 1):
        if tuple(title[k:k + size]) != window:
            continue
        if k > 0 and title[k - 1] not in STOPWORDS and is_compound(title[k - 1], title[k]):
            return True
        if k + size < len(title) and title[k + size] not in STOPWORDS and is_compound(title[k + size - 1], title[k + size]):
            return True
    return False


def title_ngram_counts(titles, min_len=2, max_len=8):
    """{syllable n-gram: number of titles containing it}; measures how specific an anchor is."""
    counts = Counter()
    for title in titles:
        toks = [norm(t) for t in syllables(title)]
        counts.update({tuple(toks[a:b]) for a in range(len(toks))
                       for b in range(a + min_len, min(len(toks), a + max_len) + 1)})
    return counts


def find_anchor(segments_list, key_terms, idf, title_tokens=(), is_compound=None, min_len=2, max_len=8,
                title_df=None, max_titles=3):
    """Best natural phrase in the source's plain (unlinked) text that names the target.

    Only phrases that occur contiguously in the target title qualify, so the anchor always
    describes the target (never "xe số 50cc" for a "xe ga 50cc" article). A phrase has 2-8
    syllables, no function word at either end, does not split a frequent compound or a title
    phrase, and contains one of the target's two most distinctive title syllables with enough
    of the title's distinctive weight. With ``title_df`` the phrase must also be specific: it
    may occur in at most ``max_titles`` published titles ("Long Biên" names dozens of posts).
    Citation lines ("truy cập ngày ...") are skipped. Returns (anchor, context, score) or
    (None, None, 0).
    """
    best = (None, None, 0.0)
    key_terms = list(key_terms)
    keyset = set(key_terms)
    distinctive = set(key_terms[:2])
    reference = sum(idf(t) for t in key_terms[:4]) or 1.0
    weights = sorted(idf(t) for t in key_terms)
    strong_idf = weights[len(weights) // 2] if weights else 0.0

    def strong(tok):  # a distinctive neighbour ("Hàng" in "Hàng Mã"), not a generic one ("xe")
        return tok not in STOPWORDS and idf(tok) >= strong_idf
    title = [norm(t) for t in title_tokens]
    title_pairs = set(zip(title, title[1:]))
    ngrams = {tuple(title[a:b]) for a in range(len(title)) for b in range(a + min_len, min(len(title), a + max_len) + 1)}
    for full, segments in segments_list:
        if CITATION.search(full or ''):
            continue
        raw, mask = '', []
        for text, linked in segments:
            raw += text
            mask.extend([linked] * len(text))
        toks = [(m.group(0), m.start(), m.end()) for m in TOKEN.finditer(raw)]
        low = [norm(t) for t, _, _ in toks]
        n = len(toks)
        for i in range(n):
            if low[i] not in title or low[i] in EDGE_WEAK:
                continue
            for j in range(i + min_len - 1, min(n, i + max_len)):
                window = tuple(low[i:j + 1])
                if window not in ngrams:
                    break
                if window[-1] in EDGE_WEAK:
                    continue
                # Two syllables are too generic unless they form a proper name ("Kim Mã", "Hồ Tây").
                if len(window) == 2 and not (toks[i][0][:1].isupper() and toks[j][0][:1].isupper()):
                    continue
                if title_df is not None and title_df.get(window, 1) > max_titles:
                    continue
                if _cuts_title_compound(window, title, is_compound):
                    continue
                # Do not cut a title phrase or a frequent compound ("bộ nhớ", "Hàng Mã") in half.
                left = low[i - 1] if i > 0 else None
                right = low[j + 1] if j + 1 < n else None
                if left and left not in STOPWORDS and (((left, low[i]) in title_pairs and strong(left)) or
                                                       (is_compound and is_compound(left, low[i]))):
                    continue
                if right and right not in STOPWORDS and (((low[j], right) in title_pairs and strong(right)) or
                                                         (is_compound and is_compound(low[j], right))):
                    continue
                start, end = toks[i][1], toks[j][2]
                if any(mask[start:end]) or any(ch in raw[start:end] for ch in INNER_PUNCT):
                    continue
                matched = {t for t in window if t in keyset}
                weight = sum(idf(t) for t in matched)
                if not (matched & distinctive) or weight < 0.4 * reference:
                    continue
                score = weight + 0.3 * len(window)
                if score > best[2]:
                    context_start = max(0, raw.rfind('.', 0, start) + 1)
                    context_end = raw.find('.', end)
                    context_end = len(raw) if context_end == -1 else context_end + 1
                    context = ' '.join(raw[context_start:context_end].split())[:260]
                    best = (' '.join(raw[start:end].split()), context, score)
    return best


def target_terms(corpus, key, limit=10):
    title = corpus.records[key]['title']
    toks = [t for t in syllables(title) if t not in STOPWORDS and not t.isdigit() and len(t) > 1]
    ranked = sorted(dict.fromkeys(toks), key=lambda t: corpus.idf(t), reverse=True)
    return ranked[:limit]



MEDIA = re.compile(r'(/wp-content/|\.(jpe?g|png|gif|webp|avif|svg|pdf|mp4|zip)(\?.*)?$)', re.I)


def suspicious_hosts(link_status, min_urls=5, share=0.9):
    """Hosts that answer 404/410 to almost every URL from the runner (bot blocking, not dead links)."""
    total, missing = Counter(), Counter()
    for url, entry in link_status.items():
        if entry.get('kind') != 'external':
            continue
        h = common.host(url)
        total[h] += 1
        if entry.get('status') in (404, 410):
            missing[h] += 1
    return {h for h, n in total.items() if n >= min_urls and missing[h] / n >= share}


def audit(cfg, corpus, records, site, terms, link_status, page_links, exclude=()):
    th = cfg['thresholds']
    issues = []
    exclude = set(exclude)
    index = LinkIndex(records, link_status)
    odd_hosts = suspicious_hosts(link_status)
    edges = defaultdict(set)
    inbound = Counter()
    anchor_uses = defaultdict(Counter)
    published = {key_of(r): r for r in records if r.get('status') == 'publish'}

    for key, r in published.items():
        if key in exclude:
            continue  # a published copy: reported once, its links would double-count inbound signals
        seen_targets = set()
        broken, redirected, weak, long_, nofollow, self_links = [], [], [], [], [], []
        for link in r.get('internal_links', []):
            href = link['href']
            status = (link_status.get(href) or {})
            if MEDIA.search(href):
                st = status.get('status')
                if st is not None and (st == 0 or st >= 400):
                    broken.append(f'media {href} (HTTP {st})')
                continue
            target = index.resolve(href)
            st = status.get('status')
            if target and target in published:
                tpage = published[target].get('page') or {}
                st = st if st is not None else tpage.get('status')
            if st is not None and (st == 0 or st >= 400):
                broken.append(f'"{link["anchor"][:50]}" → {href} (HTTP {st})')
            elif status.get('redirects'):
                redirected.append(f'{href} → {status.get("final_url")}')
            if target == key:
                self_links.append(href)
                continue
            if target:
                edges[key].add(target)
                if target not in seen_targets:
                    inbound[target] += 1
                    seen_targets.add(target)
                anchor_uses[target][norm(link['anchor'])] += 1
            text = norm(link['anchor'])
            if text in WEAK_ANCHORS or text.startswith(('http://', 'https://')) or not text:
                weak.append(f'"{link["anchor"][:60]}" → {href}')
            elif len(syllables(text)) > 12:
                # A related-post link whose anchor is the target's own title is descriptive, not a defect.
                title_toks = set(syllables(published[target]['title'])) if target in published else set()
                anchor_toks = syllables(text)
                if sum(t in title_toks for t in anchor_toks) / len(anchor_toks) < 0.8:
                    long_.append(f'"{link["anchor"][:80]}…" → {href}')
            if 'nofollow' in (link.get('rel') or '').lower():
                nofollow.append(href)
        if broken:
            issues.append(make('L-BROKEN-INTERNAL', r, evidence='; '.join(broken[:4]), impact=len(broken)))
        if redirected:
            issues.append(make('L-REDIRECTED-INTERNAL', r, evidence='; '.join(redirected[:4]), impact=len(redirected)))
        if weak:
            issues.append(make('L-WEAK-ANCHOR', r, evidence='; '.join(weak[:4]), impact=len(weak)))
        if long_:
            issues.append(make('L-LONG-ANCHOR', r, evidence='; '.join(long_[:3])))
        if nofollow:
            issues.append(make('L-NOFOLLOW-INTERNAL', r, evidence=', '.join(nofollow[:4])))
        if self_links:
            issues.append(make('L-SELF-LINK', r, evidence=', '.join(self_links[:3])))
        bad_ext, unverified = [], []
        for link in r.get('external_links', []):
            st = link_status.get(link['href'])
            if not st:
                continue
            if st.get('status') in (404, 410) and common.host(link['href']) in odd_hosts:
                unverified.append(f"{link['href']} (HTTP {st['status']}; host trả 404 cho hầu hết URL từ runner)")
            elif st.get('status') in (404, 410):
                bad_ext.append(f"{link['href']} (HTTP {st['status']})")
            elif st.get('status') in (0, 401, 403, 429) or (st.get('status') or 0) >= 500:
                unverified.append(f"{link['href']} (HTTP {st.get('status')} {st.get('error', '')})".strip())
        if bad_ext:
            issues.append(make('L-BROKEN-EXTERNAL', r, evidence='; '.join(bad_ext[:4]), impact=len(bad_ext)))
        if unverified:
            issues.append(make('L-EXTERNAL-UNVERIFIED', r, evidence='; '.join(unverified[:4]), impact=len(unverified)))

    home = cfg['site_url'].rstrip('/') + '/'
    depths = click_depths(home, page_links, lambda u: next(
        (published[k]['url'] for k in [index.resolve(u)] if k in published), None)) if page_links else {}
    graph_complete = bool(depths) and len(page_links) > len(published) * 0.9

    def depth_of(r):
        for u in (r['url'], (r.get('page') or {}).get('final_url') or r['url']):
            nu = normalize_url(u)
            if nu in depths:
                return depths[nu]
            if nu.rstrip('/') in depths:
                return depths[nu.rstrip('/')]
        return None

    for key, r in published.items():
        if r['type'] != 'post' or (r.get('page') or {}).get('status') not in (200, None) or key in exclude:
            continue
        d = depth_of(r)
        if graph_complete and d is None:
            issues.append(make('L-UNREACHABLE', r, evidence='không có đường dẫn từ trang chủ qua liên kết đã crawl'))
        elif d is not None and d > th['max_click_depth']:
            issues.append(make('L-DEEP-PAGE', r, evidence=f'độ sâu {d} lần nhấp từ trang chủ', impact=d))
        if inbound[key] == 0:
            issues.append(make('L-ORPHAN', r, priority='P1' if (graph_complete and d is None) else 'P2',
                               evidence=f'0 liên kết ngữ cảnh từ {len(published) - 1} bài/trang khác; độ sâu={d}'))
        elif inbound[key] == 1:
            issues.append(make('L-LOW-INBOUND', r, evidence='1 liên kết ngữ cảnh trỏ tới'))
        if not edges.get(key):
            issues.append(make('L-NO-OUTBOUND', r, evidence='0 liên kết tới bài nội bộ khác trong nội dung'))

    candidates = {k: r for k, r in published.items() if k not in exclude}
    architecture, suggestions = build_architecture(cfg, corpus, candidates, terms, edges, inbound, depth_of)
    post_depths = [d for d in (depth_of(r) for k, r in candidates.items()) if d is not None]
    stats = {
        'published': len(published), 'contextual_edges': sum(len(v) for v in edges.values()),
        'orphans': sum(1 for k, r in candidates.items() if r['type'] == 'post' and inbound[k] == 0),
        'avg_inbound': round(sum(inbound[k] for k in published) / max(1, len(published)), 2),
        'max_depth': max(post_depths) if post_depths else None,
        'suspicious_external_hosts': sorted(odd_hosts), 'excluded_duplicate_copies': len(exclude),
        'depth_histogram': {('unknown' if k is None else str(k)): v for k, v in sorted(
            Counter(depth_of(r) for r in candidates.values()).items(), key=lambda kv: (kv[0] is None, kv[0] or 0))},
        'graph_complete': graph_complete, 'suggestions': len(suggestions),
    }
    return issues, suggestions, architecture, stats


def build_architecture(cfg, corpus, published, terms, edges, inbound, depth_of):
    th = cfg['thresholds']
    cats, chain = category_layers(terms)
    clusters = defaultdict(list)
    for key, r in published.items():
        if r['type'] == 'post' and r.get('categories'):
            clusters[r['categories'][0]].append(key)
    overrides = cfg.get('pillar_overrides') or {}
    architecture = {'homepage': cfg['site_url'].rstrip('/') + '/', 'clusters': []}
    leads = {}
    for cid, members in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
        layers = chain(cid)
        centroid = corpus.centroid(members)
        scored = sorted(((sum(w * centroid.get(t, 0.0) for t, w in corpus.body.vectors.get(k, {}).items())
                          + 0.03 * math.log1p(inbound[k]), k) for k in members), reverse=True)
        lead = scored[0][1] if scored else None
        override = overrides.get(str(cid))
        if override:
            lead = next((k for k in members if published[k]['url'] == override or str(published[k]['id']) == str(override)), lead)
        leads[cid] = lead
        architecture['clusters'].append({
            'category_id': cid, 'path': ' > '.join(c['name'] for c in layers),
            'pillar': {'name': layers[0]['name'], 'url': layers[0].get('link')} if layers else None,
            'hub': {'name': layers[1]['name'], 'url': layers[1].get('link')} if len(layers) > 1 else None,
            'silo': {'name': layers[2]['name'], 'url': layers[2].get('link')} if len(layers) > 2 else None,
            'cluster_archive': cats.get(cid, {}).get('link'),
            'posts': len(members),
            'proposed_cluster_lead': {'post_id': published[lead]['id'], 'url': published[lead]['url'],
                                      'title': published[lead]['title'],
                                      'centroid_similarity': round(scored[0][0], 3),
                                      'source': 'pillar_overrides' if override else 'computed (needs approval)'} if lead else None,
            'contextual_links_inside_cluster': sum(1 for k in members for t in edges.get(k, ()) if t in members),
            'orphans': sum(1 for k in members if inbound[k] == 0),
        })

    suggestions = []
    per_source = Counter()
    per_target = Counter()
    planned = set()
    title_df = title_ngram_counts(r['title'] for r in published.values())
    max_titles = th.get('anchor_max_titles', 3)

    def add(src, dst, relation, similarity, reason):
        if src == dst or dst in edges.get(src, ()) or (src, dst) in planned:
            return False
        if per_source[src] >= th['max_suggestions_per_source'] or per_target[dst] >= th['max_suggestions_per_target']:
            return False
        anchor, context, score = find_anchor(corpus.blocks(src), target_terms(corpus, dst), corpus.idf,
                                             title_tokens=syllables(published[dst]['title']),
                                             is_compound=corpus.is_compound, title_df=title_df,
                                             max_titles=max_titles)
        s, t = published[src], published[dst]
        priority = 'P1' if inbound[dst] == 0 else ('P2' if relation == 'to-cluster-lead' else 'P3')
        suggestions.append({
            'source_post_id': s['id'], 'source_matrix_id': s.get('matrix_id') or '', 'source_url': s['url'],
            'source_title': s['title'], 'target_post_id': t['id'], 'target_matrix_id': t.get('matrix_id') or '',
            'target_url': t['url'], 'target_title': t['title'], 'relation': relation,
            'similarity': round(similarity, 3), 'suggested_anchor': anchor or '',
            'anchor_in_source_text': 'yes' if anchor else 'no — needs a new sentence written by an editor',
            'context': context or '', 'reason': reason, 'priority': priority,
            'target_inbound_now': inbound[dst], 'status': 'PROPOSED', 'approval': '',
        })
        planned.add((src, dst))
        per_source[src] += 1
        per_target[dst] += 1
        return True

    # 1. orphans first: link them from their most similar published neighbour.
    for dst in sorted((k for k in published if inbound[k] == 0 and published[k]['type'] == 'post'),
                      key=lambda k: published[k]['id']):
        cid = (published[dst].get('categories') or [None])[0]
        pool = [k for k in clusters.get(cid, []) if k != dst] or [k for k in published if k != dst]
        ranked = sorted(pool, key=lambda k: corpus.body_cos(k, dst), reverse=True)
        for src in ranked[:6]:
            if add(src, dst, 'orphan-rescue', corpus.body_cos(src, dst),
                   'Bài đích chưa có liên kết ngữ cảnh nào; nguồn là bài cùng cụm có nội dung gần nhất'):
                break
    # 2. supporting → proposed cluster lead.
    for cid, members in clusters.items():
        lead = leads.get(cid)
        if not lead:
            continue
        for src in sorted(members, key=lambda k: corpus.body_cos(k, lead), reverse=True):
            add(src, lead, 'to-cluster-lead', corpus.body_cos(src, lead),
                'Bài hỗ trợ trỏ về bài dẫn dắt cụm (đề xuất, cần duyệt) để gom tín hiệu chủ đề')
    # 3. strongly related posts in the same pillar, plus reciprocal links.
    pillar_of = {}
    for k, r in published.items():
        layers_k = chain((r.get('categories') or [None])[0])
        pillar_of[k] = layers_k[0]['id'] if layers_k else None
    for src in sorted(published, key=lambda k: published[k]['id']):
        if published[src]['type'] != 'post':
            continue
        cid = (published[src].get('categories') or [None])[0]
        layers = chain(cid)
        pillar = layers[0]['id'] if layers else None
        pool = [(k, sim) for k, sim in corpus.neighbors().get(src, [])
                if k in published and published[k]['type'] == 'post' and pillar_of.get(k) == pillar]
        for dst, sim in pool[:5]:
            if sim < th['related_link_cosine']:
                break
            if add(src, dst, 'related', sim, 'Nội dung liên quan cao trong cùng nhóm trụ cột'):
                if sim >= th['related_link_cosine'] + 0.1 and src not in edges.get(dst, ()):
                    add(dst, src, 'reciprocal', sim, 'Liên kết hai chiều giữa hai bài liên quan cao')
    order = {'P1': 0, 'P2': 1, 'P3': 2}
    suggestions.sort(key=lambda s: (order[s['priority']], s['anchor_in_source_text'] != 'yes',
                                    -s['similarity'], s['source_post_id']))
    return architecture, suggestions
