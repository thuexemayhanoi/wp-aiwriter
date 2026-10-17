#!/usr/bin/env python3
"""Internal Link Matrix: who links to whom, where the gaps are, and which links to add (proposals only).

  python scripts/link_matrix.py                       # offline, from posts/*.md + the publication ledger
  python scripts/link_matrix.py --check-links         # also HEAD-check every internal target on the live site
  python scripts/link_matrix.py --write-data          # refresh data/seo/link-matrix.json, link-plan.json and the doc

The tool NEVER edits posts or WordPress. Published URLs, slugs and content are protected; the proposals in
data/seo/link-plan.json are meant for separate QA-reviewed changes.
"""
import argparse
import collections
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seo_common as sc  # noqa: E402

MIN_OUT = 2          # every article should link to at least this many sibling articles
MIN_IN = 2           # ...and be linked from at least this many
MAX_SUGGEST = 3      # proposals per source article
MIN_SCORE = 0.08


def build_graph(ready, ledger, site=sc.SITE):
    nodes = {}
    for art in ready:
        entry = ledger.get(str(art['id']), {})
        parts = [p.strip() for p in art['category'].split('>')]
        nodes[art['id']] = {'id': art['id'], 'title': art['title'], 'category': art['category'],
                            'silo': parts[0], 'group': ' > '.join(parts[:-1]) if len(parts) > 1 else parts[0],
                            'url': entry.get('url', ''), 'words': art['words'],
                            'published': entry.get('phase') == 'VERIFIED' and entry.get('status') == 'publish'}
    url_to_id = {sc.norm_url(n['url']): i for i, n in nodes.items() if n['url']}
    edges = {}
    unmapped = collections.defaultdict(set)
    self_links = collections.defaultdict(int)
    external = collections.Counter()
    for art in ready:
        src = art['id']
        for anchor, url in sc.md_links(art['body']):
            if not sc.is_internal(url, site):
                external[sc.host_of(url)] += 1
                continue
            dst = url_to_id.get(sc.norm_url(url))
            if dst is None:
                unmapped[src].add(url)
            elif dst == src:
                self_links[src] += 1
            else:
                edge = edges.setdefault((src, dst), {'count': 0, 'anchors': []})
                edge['count'] += 1
                if anchor and anchor not in edge['anchors']:
                    edge['anchors'].append(anchor)
    return {'nodes': nodes, 'edges': edges, 'unmapped': {k: sorted(v) for k, v in unmapped.items()},
            'self_links': dict(self_links), 'external': external, 'url_to_id': url_to_id}


def pagerank(nodes, edges, damping=0.85, rounds=40):
    ids = list(nodes)
    rank = {i: 1 / len(ids) for i in ids}
    out = {}
    for (src, dst) in edges:
        out.setdefault(src, []).append(dst)
    for _ in range(rounds):
        fresh = {i: (1 - damping) / len(ids) for i in ids}
        sink = sum(rank[i] for i in ids if i not in out)
        for i in ids:
            fresh[i] += damping * sink / len(ids)
        for src, targets in out.items():
            share = damping * rank[src] / len(targets)
            for dst in targets:
                fresh[dst] += share
        rank = fresh
    return rank


def analyse(graph):
    nodes, edges = graph['nodes'], graph['edges']
    inbound, outbound = collections.defaultdict(set), collections.defaultdict(set)
    for (src, dst) in edges:
        outbound[src].add(dst)
        inbound[dst].add(src)
    rank = pagerank(nodes, edges) if nodes else {}
    for i, node in nodes.items():
        node['out'], node['in'] = len(outbound[i]), len(inbound[i])
        node['orphan'] = node['in'] == 0
        node['dead_end'] = node['out'] == 0
        node['pagerank'] = round(rank.get(i, 0) * len(nodes), 4)
        node['unmapped_internal'] = len(graph['unmapped'].get(i, []))
    reciprocal = sorted({tuple(sorted((a, b))) for (a, b) in edges if (b, a) in edges})
    clusters = {}
    for node in nodes.values():
        clusters.setdefault(node['category'], []).append(node['id'])
    cluster_rows = []
    for category, ids in sorted(clusters.items()):
        members = set(ids)
        inside = sum(1 for (a, b) in edges if a in members and b in members)
        leaving = sum(1 for (a, b) in edges if a in members and b not in members)
        arriving = sum(1 for (a, b) in edges if a not in members and b in members)
        possible = len(ids) * (len(ids) - 1)
        cluster_rows.append({'category': category, 'posts': len(ids), 'internal_edges': inside,
                             'density': round(inside / possible, 4) if possible else 0,
                             'out_to_other_clusters': leaving, 'in_from_other_clusters': arriving,
                             'orphans': sum(1 for i in ids if nodes[i]['orphan']),
                             'dead_ends': sum(1 for i in ids if nodes[i]['dead_end'])})
    total = len(nodes) or 1
    summary = {'posts': len(nodes), 'edges': len(edges), 'links': sum(e['count'] for e in edges.values()),
               'orphans': sum(n['orphan'] for n in nodes.values()), 'dead_ends': sum(n['dead_end'] for n in nodes.values()),
               'reciprocal_pairs': len(reciprocal),
               'below_min_out': sum(1 for n in nodes.values() if n['out'] < MIN_OUT),
               'below_min_in': sum(1 for n in nodes.values() if n['in'] < MIN_IN),
               'policy_compliance_pct': round(100 * sum(1 for n in nodes.values()
                                                        if n['out'] >= MIN_OUT and n['in'] >= MIN_IN) / total, 1),
               'unmapped_internal_targets': len({u for urls in graph['unmapped'].values() for u in urls}),
               'external_domains': dict(graph['external'].most_common(12))}
    return {'summary': summary, 'clusters': cluster_rows, 'reciprocal': reciprocal}


def documents(ready):
    docs = {}
    for art in ready:
        headings = ' '.join(h for lvl, h in sc.md_headings(art['body']) if lvl == '##')
        lead = ' '.join(sc.plain_text(art['body']).split()[:120])
        docs[art['id']] = f'{art["title"]} {art["title"]} {art["title"]} {headings} {lead}'
    return docs


def propose(graph, ready, per_source=MAX_SUGGEST):
    """Rank link additions: topical similarity first, then orphan/low-inbound targets and missing reciprocals."""
    nodes, edges = graph['nodes'], graph['edges']
    vectors = sc.tfidf_vectors(documents(ready))
    inbound = collections.Counter(dst for (_, dst) in edges)
    plan = []
    for src, node in nodes.items():
        if not node['url']:
            continue
        scored = []
        for dst, other in nodes.items():
            if dst == src or (src, dst) in edges or not other['url']:
                continue
            similarity = sc.cosine(vectors[src], vectors[dst])
            same_cluster = other['category'] == node['category']
            same_group = other['group'] == node['group']
            if not (same_cluster or same_group or similarity >= 0.30):
                continue
            value = similarity + (0.10 if same_cluster else 0.04 if same_group else 0)
            reasons = ['same cluster' if same_cluster else 'same group' if same_group else 'strong topical match']
            if inbound[dst] == 0:
                value += 0.15
                reasons.append('target is an orphan')
            elif inbound[dst] < MIN_IN:
                value += 0.06
                reasons.append(f'target has only {inbound[dst]} inbound link')
            if (dst, src) in edges:
                value += 0.12
                reasons.append('reciprocal of an existing link')
            if node['dead_end']:
                value += 0.04
                reasons.append('source has no outgoing links')
            if similarity >= MIN_SCORE:
                scored.append((value, similarity, dst, reasons))
        for value, similarity, dst, reasons in sorted(scored, key=lambda t: (-t[0], t[2]))[:per_source]:
            other = nodes[dst]
            plan.append({'source_id': src, 'source_url': node['url'], 'target_id': dst, 'target_url': other['url'],
                         'anchor_hint': other['title'], 'score': round(value, 4), 'similarity': round(similarity, 4),
                         'reasons': reasons,
                         'priority': 'high' if (inbound[dst] == 0 or node['dead_end']) else 'normal'})
    plan.sort(key=lambda p: (p['priority'] != 'high', -p['score'], p['source_id'], p['target_id']))
    return plan


def check_live_links(graph, workers=6, cap=1500):
    targets = {}
    for src, urls in graph['unmapped'].items():
        for url in urls:
            targets.setdefault(url, []).append(src)
    for (src, dst) in graph['edges']:
        targets.setdefault(graph['nodes'][dst]['url'], []).append(src)
    urls = sorted(u for u in targets if u)[:cap]
    results = sc.fetch_many(urls, workers=workers, method='HEAD', retries=1, timeout=20)
    broken = []
    for url, reply in results.items():
        if reply.status in (405, 501):
            reply = sc.http_get(url, retries=0, timeout=20)
        if reply.status == 0 or reply.status >= 400:
            broken.append({'url': url, 'status': reply.status, 'error': reply.error, 'linked_from': sorted(set(targets[url]))[:8]})
    return {'checked': len(urls), 'broken': broken}


def hub_coverage(ready, ledger, site=sc.SITE):
    """Share of articles that link to their own category archive (the silo hub). Needs the public REST API."""
    cats = {int(c['id']): c for c in sc.wp_list('categories', 'id,name,link,parent,count', site)}
    by_cat = collections.defaultdict(lambda: {'posts': 0, 'linked': 0})
    for art in ready:
        entry = ledger.get(str(art['id']), {})
        cat = cats.get(entry.get('category_id'))
        if not cat:
            continue
        row = by_cat[cat['name']]
        row['posts'] += 1
        hub = sc.norm_url(cat['link'])
        if any(sc.norm_url(u) == hub for _, u in sc.md_links(art['body'])):
            row['linked'] += 1
    return dict(by_cat)


def render_markdown(graph, analysis, plan, live=None):
    s = analysis['summary']
    lines = ['# Internal Link Matrix', '',
             'Generated by `python scripts/link_matrix.py --write-data` (read-only; proposals are for QA-reviewed changes).', '',
             '| Metric | Value |', '|---|---:|',
             f'| Articles analysed | {s["posts"]} |', f'| Distinct internal edges (article → article) | {s["edges"]} |',
             f'| Total internal links | {s["links"]} |', f'| Orphans (no inbound) | {s["orphans"]} |',
             f'| Dead ends (no outbound) | {s["dead_ends"]} |', f'| Reciprocal pairs | {s["reciprocal_pairs"]} |',
             f'| Below {MIN_OUT} outbound | {s["below_min_out"]} |', f'| Below {MIN_IN} inbound | {s["below_min_in"]} |',
             f'| Policy compliance (≥{MIN_OUT} out and ≥{MIN_IN} in) | {s["policy_compliance_pct"]}% |',
             f'| Links to legacy/non-matrix internal URLs | {s["unmapped_internal_targets"]} distinct |', '',
             '## Silo / cluster cohesion', '',
             '| Cluster | Posts | Internal edges | Density | Out | In | Orphans | Dead ends |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for c in analysis['clusters']:
        lines.append(f'| {c["category"]} | {c["posts"]} | {c["internal_edges"]} | {c["density"]} | '
                     f'{c["out_to_other_clusters"]} | {c["in_from_other_clusters"]} | {c["orphans"]} | {c["dead_ends"]} |')
    top = sorted(graph['nodes'].values(), key=lambda n: (-n['in'], n['id']))[:15]
    lines += ['', '## Most linked-to articles', '', '| ID | In | Out | Title |', '|---:|---:|---:|---|']
    lines += [f'| {n["id"]} | {n["in"]} | {n["out"]} | {n["title"][:80]} |' for n in top]
    worst = [n for n in sorted(graph['nodes'].values(), key=lambda n: (n['in'], n['out'], n['id'])) if n['orphan']][:40]
    if worst:
        lines += ['', '## Orphans needing inbound links (first 40)', '', '| ID | Out | Cluster | Title |', '|---:|---:|---|---|']
        lines += [f'| {n["id"]} | {n["out"]} | {n["category"]} | {n["title"][:70]} |' for n in worst]
    lines += ['', '## Highest-priority proposals (first 40 of ' + str(len(plan)) + ')', '',
              '| From | To | Score | Why | Anchor hint |', '|---:|---:|---:|---|---|']
    for p in plan[:40]:
        lines.append(f'| {p["source_id"]} | {p["target_id"]} | {p["score"]} | {"; ".join(p["reasons"])} | {p["anchor_hint"][:60]} |')
    if live:
        lines += ['', '## Live link check', '', f'Checked {live["checked"]} internal targets; broken: {len(live["broken"])}.']
        lines += [f'- {b["url"]} → HTTP {b["status"]} (linked from {b["linked_from"]})' for b in live['broken'][:25]]
    lines += ['', '_Machine-readable data: `data/seo/link-matrix.json`, `data/seo/link-plan.json`._']
    return '\n'.join(lines) + '\n'


def export(graph, analysis, plan, out, live=None, hubs=None):
    out.mkdir(parents=True, exist_ok=True)
    nodes = graph['nodes']
    ids = sorted(nodes)
    with open(out / 'link-matrix.csv', 'w', newline='', encoding='utf-8') as handle:  # dense matrix: row links to column
        writer = csv.writer(handle)
        writer.writerow(['source\\target'] + ids)
        for src in ids:
            writer.writerow([src] + [graph['edges'].get((src, dst), {}).get('count', 0) for dst in ids])
    with open(out / 'link-edges.csv', 'w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['source', 'target', 'count', 'anchors'])
        for (src, dst), edge in sorted(graph['edges'].items()):
            writer.writerow([src, dst, edge['count'], ' | '.join(edge['anchors'])])
    with open(out / 'link-nodes.csv', 'w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['id', 'category', 'in', 'out', 'orphan', 'dead_end', 'pagerank', 'title', 'url'])
        for i in ids:
            n = nodes[i]
            writer.writerow([i, n['category'], n['in'], n['out'], int(n['orphan']), int(n['dead_end']), n['pagerank'],
                             n['title'], n['url']])
    with open(out / 'link-plan.csv', 'w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['priority', 'source', 'target', 'score', 'reasons', 'anchor_hint', 'source_url', 'target_url'])
        for p in plan:
            writer.writerow([p['priority'], p['source_id'], p['target_id'], p['score'], '; '.join(p['reasons']),
                             p['anchor_hint'], p['source_url'], p['target_url']])
    (out / 'link-matrix.md').write_text(render_markdown(graph, analysis, plan, live), encoding='utf-8')
    return hubs


def data_snapshot(graph, analysis):
    nodes = [{k: v for k, v in n.items()} for _, n in sorted(graph['nodes'].items())]
    return {'version': 1, 'policy': {'min_out': MIN_OUT, 'min_in': MIN_IN}, 'summary': analysis['summary'],
            'clusters': analysis['clusters'], 'nodes': nodes,
            'edges': [{'source': s, 'target': d, 'count': e['count'], 'anchors': e['anchors']}
                      for (s, d), e in sorted(graph['edges'].items())],
            'legacy_internal_targets': graph['unmapped']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', default=str(sc.REPORT_DIR))
    parser.add_argument('--site', default=sc.SITE)
    parser.add_argument('--check-links', action='store_true')
    parser.add_argument('--hubs', action='store_true', help='measure links to category archive hubs (public REST)')
    parser.add_argument('--write-data', action='store_true', help='refresh the committed data/seo + docs files')
    parser.add_argument('--per-source', type=int, default=MAX_SUGGEST)
    parser.add_argument('--strict', action='store_true', help='exit 1 on broken internal links')
    args = parser.parse_args(argv)
    topics, ready, errors = sc.load_sources()
    ledger = sc.load_ledger()
    graph = build_graph(ready, ledger, args.site)
    analysis = analyse(graph)
    plan = propose(graph, ready, args.per_source)
    live = check_live_links(graph) if args.check_links else None
    hubs = None
    if args.hubs:
        try:
            hubs = hub_coverage(ready, ledger, args.site)
        except sc.SeoFetchError as exc:
            print(f'hub coverage skipped: {exc}', file=sys.stderr)
    out = sc.pathlib.Path(args.out)
    export(graph, analysis, plan, out, live, hubs)
    snapshot = data_snapshot(graph, analysis)
    if hubs is not None:
        snapshot['hub_link_coverage'] = hubs
    sc.write_json(out / 'link-matrix.json', snapshot)
    if args.write_data:
        sc.write_json(sc.DATA_DIR / 'link-matrix.json', snapshot)
        sc.write_json(sc.DATA_DIR / 'link-plan.json', {'version': 1, 'note': 'Proposals only; apply through QA-reviewed '
                      'changes. Published URLs, slugs and content must not be altered.', 'proposals': plan})
        (sc.ROOT / 'docs' / 'INTERNAL_LINK_MATRIX.md').write_text(render_markdown(graph, analysis, plan, live), encoding='utf-8')
    s = analysis['summary']
    text = render_markdown(graph, analysis, plan, live)
    sc.step_summary(text)
    print(f'Link matrix: {s["posts"]} posts, {s["edges"]} edges, orphans={s["orphans"]}, dead_ends={s["dead_ends"]}, '
          f'compliance={s["policy_compliance_pct"]}%, proposals={len(plan)}')
    return 1 if args.strict and live and live['broken'] else 0


if __name__ == '__main__':
    sys.exit(main())
