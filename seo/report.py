"""Phase 6: SEO matrix, CSV reports, technical-audit.json, dashboard and change log."""
from collections import Counter
import csv
import os
import re

from . import common
from .common import iso, read_json, write_json
from .issues import PRIORITY_ORDER, sort_key

MATRIX_COLUMNS = ['Issue Key', 'Post ID', 'Matrix ID', 'URL', 'Category', 'Issue Code', 'Issue', 'Evidence',
                  'Priority', 'Suggested Fix', 'Risk', 'Status', 'Last Checked', 'QA Result']
LINK_COLUMNS = ['priority', 'relation', 'source_post_id', 'source_matrix_id', 'source_url', 'source_title',
                'target_post_id', 'target_matrix_id', 'target_url', 'target_title', 'suggested_anchor',
                'anchor_in_source_text', 'context', 'similarity', 'target_inbound_now', 'reason', 'status', 'approval']
CANNIBAL_COLUMNS = ['post_id_a', 'matrix_id_a', 'url_a', 'title_a', 'category_a', 'post_id_b', 'matrix_id_b',
                    'url_b', 'title_b', 'category_b', 'title_similarity', 'body_similarity', 'shared_title_terms',
                    'same_cluster', 'gsc_shared_queries', 'verification', 'recommendation']
GAP_COLUMNS = ['priority', 'cluster', 'gap_type', 'evidence', 'suggested_action', 'verification']
DEFAULT_STATUS = {'VERIFIED': 'OPEN', 'NEEDS_REVIEW': 'NEEDS_REVIEW', 'INFO': 'INFO', 'BLOCKED': 'BLOCKED'}
QA_TEXT = {'VERIFIED': 'VERIFIED — rule-based check on live data',
           'NEEDS_REVIEW': 'NEEDS HUMAN REVIEW — heuristic signal',
           'INFO': 'INFO — context/suggestion, not a defect',
           'BLOCKED': 'BLOCKED — check could not run (no data/credentials)'}


def write_csv(path_, columns, rows):
    path_.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig so Excel opens Vietnamese text correctly.
    with path_.open('w', newline='', encoding='utf-8-sig') as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, '') for c in columns})


def run_link():
    server, repo, run_id = (os.environ.get(k) for k in ('GITHUB_SERVER_URL', 'GITHUB_REPOSITORY', 'GITHUB_RUN_ID'))
    return f'{server}/{repo}/actions/runs/{run_id}' if server and repo and run_id else 'local run'


def dedupe(issues):
    seen, out = set(), []
    for item in issues:
        if item.key in seen:
            continue
        seen.add(item.key)
        out.append(item)
    return out


def build(cfg, issues, suggestions, cannibal_rows, gap_rows, context):
    generated = iso()
    overrides = read_json(common.path('data/seo/issue-overrides.json'), {}) or {}
    overrides = overrides.get('issues', overrides)
    issues = sorted(dedupe(issues), key=sort_key)
    rows = []
    for item in issues:
        status = DEFAULT_STATUS[item.verification]
        override = overrides.get(item.key) if isinstance(overrides, dict) else None
        if isinstance(override, dict) and override.get('status'):
            status = override['status'] + (f" — {override['note']}" if override.get('note') else '')
        rows.append({'Issue Key': item.key, 'Post ID': item.post_id, 'Matrix ID': item.matrix_id, 'URL': item.url,
                     'Category': item.category, 'Issue Code': item.code, 'Issue': item.issue,
                     'Evidence': item.evidence, 'Priority': item.priority, 'Suggested Fix': item.fix,
                     'Risk': item.risk, 'Status': status, 'Last Checked': item.checked or context.get('site_checked') or generated,
                     'QA Result': QA_TEXT[item.verification]})
    reports = common.path('reports')
    write_csv(reports / 'seo-matrix.csv', MATRIX_COLUMNS, rows)
    write_csv(reports / 'internal-link-matrix.csv', LINK_COLUMNS, suggestions)
    write_csv(reports / 'cannibalization.csv', CANNIBAL_COLUMNS, cannibal_rows)
    gap_rows = sorted(gap_rows, key=lambda r: (PRIORITY_ORDER.get(r.get('priority'), 9), r.get('cluster') or ''))
    write_csv(reports / 'content-gaps.csv', GAP_COLUMNS, gap_rows)

    by_priority = Counter(i.priority for i in issues)
    by_verification = Counter((i.priority, i.verification) for i in issues)
    by_code = Counter((i.code, i.priority, i.verification) for i in issues)
    snapshot_path = common.path('data/seo/issues-snapshot.json')
    previous = read_json(snapshot_path, None)
    current = {i.key: i.priority for i in issues}
    delta = None
    if previous is not None:
        prev_keys = set(previous.get('issues', {}))
        delta = {'new': sorted(set(current) - prev_keys), 'resolved': sorted(prev_keys - set(current))}
    write_json(snapshot_path, {'generated_at': generated, 'issues': current})

    technical = {
        'generated_at': generated, 'run': run_link(), 'site': cfg['site_url'],
        'mode': context.get('mode'), 'read_only': True,
        'discovery': context.get('discovery'), 'counts': context.get('counts'),
        'sync_stats': context.get('sync_stats'), 'crawl': context.get('crawl'),
        'external_links': context.get('external'),
        'probes': summarize_probes(context.get('probes') or {}),
        'stack': context.get('stack'), 'terms': context.get('terms_summary'),
        'issue_counts': {'by_priority': dict(sorted(by_priority.items())),
                         'by_priority_and_verification': {f'{p}/{v}': n for (p, v), n in sorted(by_verification.items())},
                         'by_code': [{'code': c, 'priority': p, 'verification': v, 'count': n}
                                     for (c, p, v), n in sorted(by_code.items(), key=lambda kv: (PRIORITY_ORDER[kv[0][1]], -kv[1]))]},
        'linking': context.get('linking'), 'architecture': context.get('architecture'),
        'content': context.get('content'), 'aeo_geo': context.get('aeo'),
        'pagespeed': context.get('psi'), 'gsc': {k: v for k, v in (context.get('gsc') or {}).items()
                                                  if k not in ('shared_query_pairs',)},
        'delta_vs_previous': {'new': len(delta['new']), 'resolved': len(delta['resolved'])} if delta else None,
    }
    write_json(reports / 'technical-audit.json', technical)
    dashboard = render_dashboard(cfg, technical, issues, suggestions, cannibal_rows, gap_rows, delta, context)
    (reports / 'seo-dashboard.md').write_text(dashboard, encoding='utf-8')
    append_change_log(generated, technical, delta, context)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as out:
            out.write(dashboard)
    return technical


def summarize_probes(probes):
    robots = probes.get('robots') or {}
    sm = probes.get('sitemaps') or {}
    return {
        'robots_status': robots.get('status'), 'robots_sitemaps': robots.get('sitemaps'),
        'robots_disallow_all': robots.get('disallow_all_for_star'),
        'robots_txt': robots.get('body', '')[:2000],
        'sitemap_files': [{k: f.get(k) for k in ('url', 'status', 'kind', 'count', 'error')} for f in sm.get('files', [])],
        'sitemap_url_count': len(sm.get('urls') or {}),
        'core_wp_sitemap': probes.get('core_wp_sitemap'), 'http_to_https': probes.get('http_to_https'),
        'not_found_probe': probes.get('not_found_probe'), 'no_trailing_slash_probe': probes.get('no_trailing_slash_probe'),
        'llms_txt': probes.get('llms_txt'),
    }


def _table(headers, rows):
    out = '| ' + ' | '.join(headers) + ' |\n|' + '|'.join('---' for _ in headers) + '|\n'
    for row in rows:
        out += '| ' + ' | '.join(str(c).replace('|', '\\|').replace('\n', ' ') for c in row) + ' |\n'
    return out


def render_dashboard(cfg, tech, issues, suggestions, cannibal_rows, gap_rows, delta, context):
    counts = tech.get('counts') or {}
    crawl = tech.get('crawl') or {}
    linking = tech.get('linking') or {}
    content = tech.get('content') or {}
    probes = tech.get('probes') or {}
    stack = tech.get('stack') or {}
    md = [f"# SEO Dashboard — {cfg['site_url']}\n",
          f"Cập nhật: **{tech['generated_at']}** · Lần chạy: {tech['run']} · Chế độ: `{tech.get('mode')}` · "
          f"**Chỉ đọc**: engine không ghi vào WordPress.\n",
          '## Tổng quan inventory\n',
          _table(['Bài viết', 'Trang', 'Chuyên mục', 'Thẻ', 'Media', 'URL trong sitemap'],
                 [[counts.get('posts', '?'), counts.get('pages', '?'), counts.get('categories', '?'),
                   counts.get('tags', '?'), counts.get('media', '?'), probes.get('sitemap_url_count', '?')]]),
          f"\nCrawl: {crawl.get('posts_pages_crawled', 0)} bài/trang tải mới, {crawl.get('posts_pages_reused', 0)} dùng lại, "
          f"{crawl.get('archives_crawled', 0)} trang chuyên mục/lưu trữ, {crawl.get('internal_targets_checked', 0)} link nội bộ khác, "
          f"{crawl.get('requests', '?')} request.\n",
          '\n## Vấn đề theo mức ưu tiên\n']
    pv = Counter((i.priority, i.verification) for i in issues)
    md.append(_table(['Ưu tiên', 'Đã xác minh', 'Cần người duyệt', 'Thông tin', 'Bị chặn', 'Tổng'],
                     [[p, pv[(p, 'VERIFIED')], pv[(p, 'NEEDS_REVIEW')], pv[(p, 'INFO')], pv[(p, 'BLOCKED')],
                       sum(n for (pp, _), n in pv.items() if pp == p)] for p in ('P0', 'P1', 'P2', 'P3')]))
    if delta:
        md.append(f"\nSo với lần trước: **{len(delta['new'])} mới**, **{len(delta['resolved'])} đã hết**.\n")
    md.append('\n## Mã lỗi phổ biến\n')
    md.append(_table(['Mã', 'Ưu tiên', 'Xác minh', 'Số lượng'],
                     [[c['code'], c['priority'], c['verification'], c['count']]
                      for c in tech['issue_counts']['by_code'][:25]]))
    md.append(owner_decisions(issues, tech, context))
    top = [i for i in issues if i.priority in ('P0', 'P1')][:20]
    md.append('\n## 20 mục P0/P1 đầu tiên\n')
    md.append(_table(['Ưu tiên', 'Mã', 'URL', 'Bằng chứng', 'Xác minh'],
                     [[i.priority, i.code, i.url, i.evidence[:110], i.verification] for i in top]) if top else 'Không có mục P0/P1.\n')
    md.append('\n## Liên kết nội bộ\n')
    sug = Counter(s['priority'] for s in suggestions)
    md.append(_table(['Liên kết ngữ cảnh', 'Bài mồ côi', 'Inbound TB', 'Độ sâu tối đa', 'Đề xuất P1/P2/P3', 'Có anchor sẵn'],
                     [[linking.get('contextual_edges', '?'), linking.get('orphans', '?'), linking.get('avg_inbound', '?'),
                       linking.get('max_depth', '?'), f"{sug['P1']}/{sug['P2']}/{sug['P3']}",
                       sum(1 for s in suggestions if s['anchor_in_source_text'] == 'yes')]]))
    hist = linking.get('depth_histogram') or {}
    if hist:
        md.append('\nPhân bố độ sâu nhấp chuột: ' + ', '.join(f'{k}: {v}' for k, v in hist.items()) + '\n')
    md.append('\n## Nội dung\n')
    md.append(f"- Cặp gần trùng lặp: {content.get('near_duplicate_pairs', 0)}; cặp nghi cannibalization: "
              f"{content.get('cannibalization_pairs', 0)} (cần GSC để xác minh); content gap: {len(gap_rows)} dòng.\n")
    nap = content.get('nap') or {}
    if nap.get('phones'):
        md.append('- Số điện thoại tìm thấy trong nội dung: ' + ', '.join(
            f"{p} ({n} trang)" for p, n in sorted((nap.get('phone_pages') or {}).items(), key=lambda kv: -kv[1])[:6]) + '\n')
    domains = content.get('top_external_domains') or {}
    if domains:
        md.append('- Domain ngoài được liên kết nhiều nhất: ' + ', '.join(f'{d} ({n})' for d, n in list(domains.items())[:8]) + '\n')
    if linking.get('suspicious_external_hosts'):
        md.append('- Host trả 404 cho hầu hết URL từ runner (xếp vào "không kiểm tra được", không coi là link hỏng): '
                  + ', '.join(linking['suspicious_external_hosts']) + '\n')
    md.append('\n## Kỹ thuật\n')
    md.append(f"- robots.txt: HTTP {probes.get('robots_status')}; sitemap khai báo: {probes.get('robots_sitemaps')}\n"
              f"- Sitemap: {len(probes.get('sitemap_files') or [])} file, {probes.get('sitemap_url_count', 0)} URL; "
              f"wp-sitemap.xml lõi: HTTP {(probes.get('core_wp_sitemap') or {}).get('status')} "
              f"({len((probes.get('core_wp_sitemap') or {}).get('redirects') or [])} chuyển hướng → "
              f"{(probes.get('core_wp_sitemap') or {}).get('final_url')})\n"
              f"- HTTP→HTTPS: {(probes.get('http_to_https') or {}).get('final_url')}; probe 404: HTTP "
              f"{(probes.get('not_found_probe') or {}).get('status')}\n"
              f"- Yoast: {stack.get('yoast_version') or 'không thấy phiên bản'}; theme: {stack.get('themes')}; "
              f"plugin nhận diện từ HTML: {len(stack.get('plugins') or [])}\n")
    psi = tech.get('pagespeed') or []
    measured = [p for p in psi if p.get('lab')]
    md.append('\n## Core Web Vitals / PageSpeed\n')
    if measured:
        md.append(_table(['URL', 'Điểm lab', 'LCP lab (s)', 'CLS lab', 'CrUX field'],
                         [[p['url'], p['lab'].get('performance_score'),
                           round((p['lab'].get('largest-contentful-paint') or 0) / 1000, 2),
                           round(p['lab'].get('cumulative-layout-shift') or 0, 3),
                           (p.get('field') or {}).get('overall_category') or 'không có'] for p in measured]))
        md.append('\nLab data là mô phỏng Lighthouse; chỉ CrUX field data phản ánh người dùng thật.\n')
    else:
        statuses = sorted({str(p.get('status')) for p in psi})
        hint = ' API trả HTTP 429 (hết hạn mức không khóa): thêm secret `PSI_API_KEY`.' if '429' in statuses else ''
        md.append(f"Chưa đo trong lần chạy này (BLOCKED/không chạy; HTTP {', '.join(statuses) or '—'}).{hint} "
                  'Không suy đoán số liệu.\n')
    gsc = tech.get('gsc') or {}
    md.append('\n## Google Search Console\n')
    md.append(f"Trạng thái: **{gsc.get('status', 'BLOCKED')}** — {gsc.get('reason', '')}\n")
    if gsc.get('status') == 'OK':
        md.append(f"Khoảng {gsc.get('start')} → {gsc.get('end')}: {gsc.get('pages_with_impressions')} URL có hiển thị; "
                  f"{gsc.get('published_without_impressions')} URL đã xuất bản chưa có hiển thị.\n")
    md.append('\n## Cách dùng báo cáo\n'
              '- `reports/seo-matrix.csv`: toàn bộ vấn đề, sắp P0→P3; cột QA Result phân biệt lỗi đã xác minh và cảnh báo cần người duyệt.\n'
              '- `reports/internal-link-matrix.csv`: đề xuất liên kết nguồn→đích với anchor có sẵn trong bài; chỉ áp dụng sau khi duyệt.\n'
              '- `reports/cannibalization.csv`, `reports/content-gaps.csv`: tín hiệu cần người quyết định.\n'
              '- Ghi trạng thái xử lý vào `data/seo/issue-overrides.json`; chỉ mục trong `data/seo/approved-fixes.json` mới được áp dụng lên WordPress.\n')
    text = ''.join(md)
    # GitHub-flavoured Markdown: keep a blank line after every heading.
    text = re.sub(r'([^\n])\n(#{1,6} )', r'\1\n\n\2', text)
    return re.sub(r'^(#{1,6} [^\n]*)\n(?!\n)', r'\1\n\n', text, flags=re.M)


DECISION_CODES = ('T-DUPLICATE-COPY', 'C-NAP-INCONSISTENT', 'A-ENTITY-INCONSISTENT', 'A-AUTHOR-GENERIC',
                  'C-FINE-AMOUNT', 'T-ARCHIVE-NOINDEX', 'T-META-DESC-NOT-YOAST')


def owner_decisions(issues, tech, context):
    """Items the engine must not resolve by itself: listed for the owner, never auto-fixed."""
    by_code = {}
    for item in issues:
        if item.code in DECISION_CODES:
            by_code.setdefault(item.code, []).append(item)
    if not by_code:
        return ''
    md = ['\n## Cần chủ sở hữu quyết định (engine không tự sửa)\n']
    copies = by_code.get('T-DUPLICATE-COPY', [])
    if copies:
        md.append(f'- **{len(copies)} bản sao trùng lặp đang xuất bản** (giữ bản gốc, bản thừa xử lý thủ công/301):\n')
        md.extend(f'  - WP {i.post_id} {i.url} — {i.evidence[:160]}\n' for i in copies[:12])
    for code, label in (('C-NAP-INCONSISTENT', 'NAP/liên hệ'), ('A-ENTITY-INCONSISTENT', 'Tên thương hiệu trong schema'),
                        ('A-AUTHOR-GENERIC', 'Tác giả'), ('T-META-DESC-NOT-YOAST', 'Nguồn meta description')):
        for item in by_code.get(code, []):
            md.append(f'- **{label}**: {item.evidence[:300]}\n')
    fines = by_code.get('C-FINE-AMOUNT', [])
    if fines:
        md.append(f'- **{len(fines)} bài nêu mức phạt cụ thể**: đối chiếu văn bản hiện hành trước khi giữ/sửa '
                  '(xem `C-FINE-AMOUNT` trong seo-matrix.csv).\n')
    noindex = by_code.get('T-ARCHIVE-NOINDEX', [])
    if noindex:
        md.append(f'- **{len(noindex)} trang lưu trữ noindex**: xác nhận có chủ đích: ' + ', '.join(i.url for i in noindex[:6]) + '\n')
    return ''.join(md)


ENTRY_MARK = '<!-- seo-engine-entry -->'


def append_change_log(generated, tech, delta, context):
    path_ = common.path('reports/change-log.md')
    old = path_.read_text(encoding='utf-8') if path_.exists() else ''
    header = ('# SEO Engine change log\n\nMỗi lần chạy thêm một mục ở đầu (giữ 60 mục gần nhất). '
              'Engine chỉ đọc WordPress; thay đổi nội dung chỉ qua approved-seo-fixes.\n\n')
    stats = tech.get('sync_stats') or {}
    lines = [f"## {generated} — {tech.get('mode')}",
             f"- Lần chạy: {tech['run']}",
             '- Đồng bộ: ' + ('; '.join(f"{k}: {v.get('listed')} có, {v.get('new')} mới, {v.get('updated')} sửa, "
                                         f"{len(v.get('removed') or [])} mất" for k, v in stats.items()) or 'không chạy'),
             '- Vấn đề: ' + ', '.join(f'{p}={n}' for p, n in (tech['issue_counts']['by_priority'] or {}).items())]
    if delta:
        lines.append(f"- So với lần trước: {len(delta['new'])} mới, {len(delta['resolved'])} đã hết")
        if delta['resolved'][:10]:
            lines.append('  - Hết: ' + ', '.join(delta['resolved'][:10]))
    for note in context.get('notes', []):
        lines.append(f'- {note}')
    previous = [e.strip('\n') for e in old.split(ENTRY_MARK)[1:]] if ENTRY_MARK in old else []
    entries = ['\n'.join(lines)] + previous[:59]
    path_.write_text(header + ''.join(f'{ENTRY_MARK}\n{e}\n\n' for e in entries), encoding='utf-8')
