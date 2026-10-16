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


def find_anchor(segments_list, key_terms, idf, min_terms=2, max_len=7, title_bigrams=()):
    """Best plain-text phrase (2..max_len syllables) matching target key terms.

    segments_list: [(full_text, [(text, in_link), ...]), ...] for one source article.
    Returns (anchor, context, score) or (None, None, 0).
    """
    best = (None, None, 0.0)
    keyset = set(key_terms)
    # key_terms are ordered by IDF; an anchor must contain one of the target's most distinctive terms.
    distinctive = set(list(key_terms)[:3])
    for _full, segments in segments_list:
        raw, mask = '', []
        for text, linked in segments:
            raw += text
            mask.extend([linked] * len(text))
        toks = [(m.group(0), m.start(), m.end()) for m in TOKEN.finditer(raw)]
        lowered = [norm(t) for t, _, _ in toks]
        for i in range(len(toks)):
            if lowered[i] not in keyset:
                continue
            for j in range(i + 1, min(len(toks), i + max_len)):
                if lowered[j] not in keyset:
                    continue
                k = j
                # Do not cut a compound such as "Hà Nội" that appears in the target title.
                while k + 1 < len(toks) and k - i + 1 < max_len + 1 and \
                        (lowered[k], lowered[k + 1]) in title_bigrams:
                    k += 1
                window = lowered[i:k + 1]
                start, end = toks[i][1], toks[k][2]
                if any(mask[start:end]):
                    continue
                if any(ch in raw[start:end] for ch in '.,!?;:()[]"“”/'):
                    continue
                matched = {t for t in window if t in keyset}
                if len(matched) < min_terms or not (matched & distinctive):
                    continue
                score = sum(idf(t) for t in matched) - 0.15 * len(window)
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


def title_bigrams(corpus, key):
    toks = syllables(corpus.records[key]['title'])
    return set(zip(toks, toks[1:]))


def audit(cfg, corpus, records, site, terms, link_status, page_links):
    th = cfg['thresholds']
    issues = []
    index = LinkIndex(records, link_status)
    edges = defaultdict(set)
    inbound = Counter()
    anchor_uses = defaultdict(Counter)
    published = {key_of(r): r for r in records if r.get('status') == 'publish'}

    for key, r in published.items():
        seen_targets = set()
        broken, redirected, weak, long_, nofollow, self_links = [], [], [], [], [], []
        for link in r.get('internal_links', []):
            href = link['href']
            status = (link_status.get(href) or {})
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
            if st.get('status') in (404, 410):
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
        if r['type'] != 'post' or (r.get('page') or {}).get('status') not in (200, None):
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

    architecture, suggestions = build_architecture(cfg, corpus, published, terms, edges, inbound, depth_of)
    stats = {
        'published': len(published), 'contextual_edges': sum(len(v) for v in edges.values()),
        'orphans': sum(1 for k, r in published.items() if r['type'] == 'post' and inbound[k] == 0),
        'avg_inbound': round(sum(inbound[k] for k in published) / max(1, len(published)), 2),
        'max_depth': max(depths.values()) if depths else None,
        'depth_histogram': {('unknown' if k is None else str(k)): v for k, v in sorted(
            Counter(depth_of(r) for r in published.values()).items(), key=lambda kv: (kv[0] is None, kv[0] or 0))},
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

    def add(src, dst, relation, similarity, reason):
        if src == dst or dst in edges.get(src, ()) or (src, dst) in planned:
            return False
        if per_source[src] >= th['max_suggestions_per_source'] or per_target[dst] >= th['max_suggestions_per_target']:
            return False
        anchor, context, score = find_anchor(corpus.blocks(src), target_terms(corpus, dst), corpus.idf,
                                             title_bigrams=title_bigrams(corpus, dst))
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
