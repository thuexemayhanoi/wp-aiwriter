"""CLI: python -m seo <command> [options]

Commands
  discover            verify REST root, site identity and Yoast namespace (read-only)
  sync [--full]       refresh data/posts-index.jsonl from public REST (incremental by default)
  crawl [--full]      crawl public HTML, archives, robots.txt, sitemaps, probes, internal links, images
  external-links      check outbound link status (cached, read-only GET/HEAD)
  psi                 PageSpeed Insights lab/field data for a few key URLs (optional)
  gsc                 Google Search Console (only with GSC secrets)
  audit               run all audit modules on the latest data and write reports/
  run                 sync → crawl → (external-links) → (psi) → gsc → audit
  fixes {validate,apply,rollback}   approved WordPress fixes (apply/rollback need confirmation)
"""
import argparse
import json
import os
import sys

from . import aeo, common, content, crawl, fixes, gsc, inventory, linking, report, technical
from .common import read_json, write_json
from .corpus import Corpus
from .net import Fetcher


def fetcher(cfg):
    return Fetcher(cfg)


def gather_stack(records, site):
    themes, plugins, yoast = set(), set(), set()
    pages = [r.get('page') or {} for r in records] + list((site.get('archives') or {}).values())
    for page in pages:
        themes.update(page.get('theme') or [])
        plugins.update(page.get('plugins') or [])
        if page.get('yoast_version'):
            yoast.add(page['yoast_version'])
    generator = next((p.get('generator') for p in pages if p.get('generator')), None)
    return {'themes': sorted(themes), 'plugins': sorted(plugins), 'yoast_version': ', '.join(sorted(yoast)) or None,
            'generator': generator}


def do_audit(cfg, mode, notes=None):
    records = inventory.load_index()
    if not records:
        raise SystemExit('No inventory: run `python -m seo sync` first')
    cache = inventory.load_content_cache()
    missing = [r for r in records if f"{r['type']}:{r['id']}" not in cache]
    if missing:
        raise SystemExit(f'Content cache missing {len(missing)} records: run `python -m seo sync` first')
    terms = inventory.load_terms()
    site = read_json(crawl.site_cache_path(), {}) or {}
    link_status = read_json(crawl.link_status_path(), {}) or {}
    page_links = (read_json(crawl.pages_cache_path(), {}) or {}).get('links', {})
    state = read_json(inventory.state_path(), {}) or {}
    psi = read_json(common.path('data/seo/psi.json'), None)
    gsc_summary = read_json(common.path('data/seo/gsc-summary.json'), None) or {'status': 'BLOCKED', 'reason': 'not run'}
    corpus = Corpus(records, cache)
    duplicates = corpus.duplicate_copies(preferred=inventory.ledger_by_wp_id())
    issues = []
    tech_issues, tech_extra = technical.audit(cfg, records, site, terms, state, link_status, psi, duplicates)
    issues += tech_issues
    link_issues, suggestions, architecture, link_stats = linking.audit(cfg, corpus, records, site, terms, link_status,
                                                                       page_links, exclude=duplicates)
    issues += link_issues
    content_issues, cannibal_rows, gap_rows, content_stats = content.audit(cfg, corpus, records, terms, gsc_summary,
                                                                           duplicates)
    issues += content_issues
    aeo_issues, aeo_summary = aeo.audit(cfg, corpus, records, site, state.get('discovery'), duplicates)
    issues += aeo_issues
    if gsc_summary.get('status') != 'OK':
        from .issues import make
        issues.append(make('G-GSC-NOT-CONFIGURED', url=cfg['site_url'].rstrip('/') + '/', key_extra='gsc',
                           evidence=gsc_summary.get('reason', '')))
    context = {
        'mode': mode, 'discovery': state.get('discovery'), 'counts': state.get('counts'),
        'sync_stats': state.get('sync_stats'), 'crawl': site.get('crawl'), 'probes': site.get('probes'),
        'external': state.get('external_links'), 'stack': gather_stack(records, site),
        'terms_summary': {'categories': len(terms.get('categories', [])), 'tags': len(terms.get('tags', [])),
                          'media': terms.get('media_count'), 'media_images_missing_alt': terms.get('media_missing_alt')},
        'linking': link_stats, 'architecture': architecture, 'content': content_stats, 'aeo': aeo_summary,
        'psi': tech_extra.get('psi'), 'gsc': gsc_summary, 'notes': (notes or []) + [
            f'Cảnh báo REST: {w}' for w in state.get('rest_warnings') or []],
        'site_checked': ((site.get('probes') or {}).get('checked_at')),
    }
    tech = report.build(cfg, issues, suggestions, cannibal_rows, gap_rows, context)
    print(json.dumps({'issues': tech['issue_counts']['by_priority'], 'suggestions': len(suggestions),
                      'cannibalization': len(cannibal_rows), 'gaps': len(gap_rows)}, ensure_ascii=False))
    return tech


def main(argv=None):
    parser = argparse.ArgumentParser(prog='python -m seo', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('discover')
    p = sub.add_parser('sync'); p.add_argument('--full', action='store_true')
    p = sub.add_parser('crawl'); p.add_argument('--full', action='store_true'); p.add_argument('--max-pages', type=int)
    p = sub.add_parser('external-links'); p.add_argument('--force', action='store_true')
    sub.add_parser('psi')
    sub.add_parser('gsc')
    p = sub.add_parser('audit'); p.add_argument('--mode', default='audit')
    p = sub.add_parser('run')
    p.add_argument('--full', action='store_true', help='full REST sync and full HTML crawl')
    p.add_argument('--no-crawl', action='store_true', help='skip HTML crawl (inventory/content audits only)')
    p.add_argument('--external', action='store_true', help='also check outbound links')
    p.add_argument('--psi', action='store_true', help='also query PageSpeed Insights')
    p.add_argument('--mode', default='run')
    p = sub.add_parser('fixes')
    p.add_argument('action', choices=['validate', 'apply', 'rollback'])
    p.add_argument('--max-fixes', type=int, default=1)
    p.add_argument('--fix-id')
    args = parser.parse_args(argv)
    cfg = common.load_config()

    if args.command == 'discover':
        print(json.dumps(inventory.discover(fetcher(cfg), cfg), ensure_ascii=False, indent=2))
        return 0
    if args.command == 'sync':
        _, rep = inventory.sync(cfg, fetcher(cfg), full=args.full)
        print(json.dumps(rep['stats'], ensure_ascii=False))
        return 0
    if args.command == 'crawl':
        data = crawl.crawl(cfg, fetcher(cfg), inventory.load_index(), full=args.full, max_pages=args.max_pages)
        print(json.dumps(data['crawl'], ensure_ascii=False))
        return 0
    if args.command == 'external-links':
        print(json.dumps(_external(cfg, force=args.force), ensure_ascii=False))
        return 0
    if args.command == 'psi':
        print(json.dumps(_psi(cfg), ensure_ascii=False)[:2000])
        return 0
    if args.command == 'gsc':
        print(json.dumps({k: v for k, v in gsc.run(cfg, inventory.load_index()).items()
                          if k != 'shared_query_pairs'}, ensure_ascii=False))
        return 0
    if args.command == 'audit':
        do_audit(cfg, args.mode)
        return 0
    if args.command == 'run':
        notes = []
        f = fetcher(cfg)
        records, rep = inventory.sync(cfg, f, full=args.full)
        notes.append(f"REST đồng bộ {'đầy đủ' if args.full else 'tăng dần'}: " + json.dumps(
            {k: {x: v[x] for x in ('listed', 'fetched', 'new', 'updated')} for k, v in rep['stats'].items()}, ensure_ascii=False))
        if not args.no_crawl:
            data = crawl.crawl(cfg, f, records, full=args.full)
            notes.append(f"Crawl: {data['crawl']['posts_pages_crawled']} trang tải mới, {data['crawl']['archives_crawled']} trang lưu trữ")
        if args.external:
            notes.append('Liên kết ngoài: ' + json.dumps(_external(cfg), ensure_ascii=False))
        if args.psi:
            measured = _psi(cfg)
            notes.append(f"PageSpeed: {sum(1 for m in measured if m.get('lab'))}/{len(measured)} URL có dữ liệu")
        g = gsc.run(cfg, inventory.load_index())
        notes.append(f"GSC: {g['status']}")
        do_audit(cfg, args.mode, notes)
        return 0
    if args.command == 'fixes':
        user, password = fixes.credentials()
        wp = fixes.WordPress(cfg, user, password)
        confirm = os.environ.get('SEO_APPLY_CONFIRM') == 'yes'
        if args.action == 'validate':
            result = fixes.validate(cfg, wp)
        elif args.action == 'apply':
            if not (user and password):
                raise SystemExit('BLOCKED: WordPress credentials not configured; zero writes')
            result = fixes.apply(cfg, wp, max_fixes=args.max_fixes, confirm=confirm)
        else:
            if not args.fix_id:
                raise SystemExit('--fix-id is required for rollback')
            result = [fixes.rollback(cfg, wp, args.fix_id, confirm=confirm)]
        write_json(common.path('reports/fix-plan.json'), {'action': args.action, 'at': common.iso(), 'results': result})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if all(r.get('status', 'VALID') == 'VALID' or r.get('applied') or r.get('phase') for r in result) else 1
    return 2


def _external(cfg, force=False):
    result = crawl.check_external(cfg, fetcher(cfg), inventory.load_index(), force=force)
    state = read_json(inventory.state_path(), {}) or {}
    state['external_links'] = {**result, 'checked_at': common.iso()}
    write_json(inventory.state_path(), state)
    return result


def _psi(cfg):
    records = inventory.load_index()
    site = cfg['site_url'].rstrip('/') + '/'
    posts = sorted((r for r in records if r['type'] == 'post'), key=lambda r: -r.get('word_count', 0))
    terms = inventory.load_terms()
    cats = sorted((c for c in terms.get('categories', []) if c.get('count')), key=lambda c: -c['count'])
    urls = [site] + [p['url'] for p in posts[:2]] + [c['link'] for c in cats[:1]]
    measured = crawl.pagespeed(cfg, fetcher(cfg), urls, api_key=os.environ.get('PSI_API_KEY'))
    write_json(common.path('data/seo/psi.json'), measured)
    return measured


if __name__ == '__main__':
    sys.exit(main())
