# SEO Engine — runbook

**Site:** https://blog.rentbikehanoi.com (single host; the engine refuses a config with more than one host).
**Code:** `seo/` (Python standard library only; `google-auth` only for the optional GSC monitor).
**Rule:** every audit is read-only. The engine sends GET/HEAD requests without credentials. The only
code path that can change WordPress is `approved-seo-fixes.yml`, for owner-approved entries only.

## Cycle

Audit → Matrix → Prioritize → Propose fix → Test → Approval → Apply → Verify → Report.

1. **Discover / sync** (`python -m seo sync`): verifies that `/wp-json/` reports the configured home URL,
   records namespaces (Yoast REST present or not), then paginates posts, pages, categories, tags and media.
   Incremental by default: only items whose `modified_gmt` changed are re-fetched. Output:
   `data/posts-index.jsonl` (one normalised record per post/page; no full bodies) and
   `data/seo/terms.json`. Full bodies live in `data/seo/cache/` (GitHub Actions cache, not committed).
2. **Crawl** (`python -m seo crawl`): public HTML of every post/page (only changed or older than 7 days
   unless `--full`), home and category/tag archives with pagination, robots.txt, all sitemaps, HTTP→HTTPS,
   a random-URL 404 probe, a no-trailing-slash probe, llms.txt, every internal link target and image weight.
3. **External links** (`python -m seo external-links`): outbound link status, cached 14 days. 403/429/timeouts
   are reported as NEEDS_REVIEW because many sites block bots.
4. **PageSpeed** (`python -m seo psi`, optional): Lighthouse lab data and CrUX field data for 4 key URLs.
   Lab data is a simulation; only field data reflects real users. Missing data is reported as BLOCKED.
   Without the `PSI_API_KEY` secret the shared anonymous quota usually answers HTTP 429.
5. **GSC** (`python -m seo gsc`, optional): needs secrets `GSC_SERVICE_ACCOUNT_JSON` and `GSC_PROPERTY`
   (for example `sc-domain:rentbikehanoi.com` or `https://blog.rentbikehanoi.com/`), and the service account
   added as a user of the property. Read-only scope. Without them nothing is inferred.
6. **Audit + report** (`python -m seo audit`): technical, internal linking, content/cannibalization and
   AEO/GEO modules, then the matrix and reports.

`python -m seo run [--full] [--no-crawl] [--external] [--psi]` chains the steps.

## Outputs

| File | Content |
| --- | --- |
| `data/posts-index.jsonl` | Inventory with a compact crawl summary (status, canonical, robots, title, description, H1, schema types; fields no audit reads are dropped) |
| `reports/seo-matrix.csv` | Every issue, sorted P0→P3, with evidence, fix, risk, status and QA result |
| `reports/internal-link-matrix.csv` | Source → target → anchor that already exists in the source text → reason |
| `reports/cannibalization.csv` | Pairs with similar titles and bodies; NEEDS_REVIEW until GSC confirms |
| `reports/content-gaps.csv` | Structural gaps and hypotheses (empty categories, thin clusters, trust pages, query gaps) |
| `reports/technical-audit.json` | Discovery, stack, probes, counts, architecture, link stats, PSI, GSC status |
| `reports/seo-dashboard.md` | Human summary (also written to the Actions job summary) |
| `reports/change-log.md` | One entry per run: sync counts, issue counts, new/resolved issues |
| `data/seo/issues-snapshot.json` | Issue keys from the last run, used for the delta |
| `data/seo/link-status.json` | Cached internal/external link status |
| `data/seo/site-checks.json` | robots/sitemap/probe results and archive crawl summaries |

CSV files are UTF-8 with BOM so Excel shows Vietnamese correctly.

## Reading the matrix

- **Priority**: P0 blocks indexing or loses content; P1 strong ranking/crawl impact; P2 quality; P3 polish.
- **QA Result**: `VERIFIED` = deterministic rule on live data. `NEEDS HUMAN REVIEW` = heuristic signal
  (similarity, intent, legal/price mentions). `INFO` = context. `BLOCKED` = check could not run.
- **Risk**: risk of applying the suggested fix. HIGH covers canonical, noindex, redirects, URL or
  consolidation changes: never apply these without explicit owner approval.
- **Status**: default OPEN / NEEDS_REVIEW / INFO / BLOCKED. Record decisions per `Issue Key` in
  `data/seo/issue-overrides.json` (ACCEPTED, WONTFIX, IN_PROGRESS, FIXED_PENDING_VERIFY).

Rules that keep the matrix free of noise and false positives:

- **Published copies** (same Excel `matrix_id`, or byte-identical content) are reported once, as
  `T-DUPLICATE-COPY` on each copy; the lowest WordPress ID is treated as the original for reporting only.
  Copies are left out of every other per-page check, link suggestion, orphan/depth count and similarity
  pair. The engine never deletes, unpublishes or redirects them: the owner decides.
- **noindex URLs** get only `T-NOINDEX` / `T-ARCHIVE-NOINDEX`; Yoast omits canonical and description there by design.
- **External links**: a failed HEAD is always confirmed with GET. A host answering 404 to at least 90% of
  5+ checked URLs (bot blocking, e.g. help centres) is reported as `L-EXTERNAL-UNVERIFIED`, not broken.
- **Site-wide patterns** (`T-META-DESC-NOT-YOAST`, `A-AUTHOR-GENERIC`, `T-SCHEMA-BREADCRUMB-MISSING`, NAP,
  brand names) are one row with a count and examples instead of hundreds of identical rows.
- The dashboard section **"Cần chủ sở hữu quyết định"** lists what only the owner can decide.

## Workflows

| Workflow | Trigger | What it refreshes |
| --- | --- | --- |
| `seo-matrix-report.yml` | weekly (Mon 03:47 VN), manual, PRs touching the engine | full sync + full crawl + external links + PSI + GSC + all reports |
| `wordpress-content-sync.yml` | daily (08:23 VN), manual | incremental REST sync + content-level audits |
| `technical-seo-audit.yml` | manual | crawl (+PSI) |
| `internal-link-audit.yml` | manual | crawl + external links |
| `content-quality-audit.yml` | manual | REST sync, content audits |
| `aeo-geo-audit.yml` | manual | crawl, AEO/GEO checks |
| `gsc-monitor.yml` | weekly (Mon 07:41 VN), manual | Search Console data (BLOCKED without secrets) |
| `approved-seo-fixes.yml` | manual only | validate (default) / apply / rollback approved fixes |

All of them call `seo-engine.yml`, share the concurrency group `seo-engine-<branch>` and commit only
`data/posts-index.jsonl`, `data/seo/` and the SEO report files. These paths do not trigger the article QA
or the WordPress publisher. No WordPress secret is passed to any audit workflow.

## Applying an approved fix

1. Pick a row in `reports/internal-link-matrix.csv` with `anchor_in_source_text = yes`.
2. Add it to `data/seo/approved-fixes.json` with `expected_modified_gmt` (from `data/posts-index.jsonl`),
   `approved_by`, `approved_at`, `status: approved`.
3. Run **Approved SEO Fixes** with `action=validate`. It checks the post is published, unchanged since
   approval, does not already link the target, and the anchor occurs exactly once outside links/headings.
4. Run again with `action=apply`, `confirm=APPLY`, `max_fixes=1`. The workflow backs up the raw content to
   `data/seo/backups/`, writes `APPLY_INTENT`, updates only `content`, re-reads the raw and public post,
   records `VERIFIED` and mirrors the link into `posts/NNNN.md` when the anchor is unambiguous.
5. To undo: `action=rollback`, `fix_id=…`, `confirm=APPLY`. Rollback refuses if the post was edited after the fix.

Yoast title/description/focus keyphrase are not written through REST: Yoast does not expose a supported
write endpoint, and no alternative mechanism has been verified or approved.

## Limits stated plainly

- Similarity, cannibalization, content gaps, "direct answer" and FAQ checks are heuristics.
- Core Web Vitals come only from PageSpeed/CrUX when available; response time from GitHub runners is not CWV.
- Without GSC there are no clicks, impressions or query data, and no ranking claims are made.
- The engine never promises rankings or AI-search inclusion.
