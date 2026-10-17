# SEO systems on GitHub — Audit, Internal Link Matrix, Protection

Ba hệ thống chạy hoàn toàn bằng GitHub Actions + Python chuẩn, **không cần WPVibe, WP Agent hay plugin nào**.
Chúng chỉ **đọc** (REST công khai và trang công khai của blog), không có secret bắt buộc và **không bao giờ ghi vào WordPress**.

| System | Script | Workflow | Question it answers |
|---|---|---|---|
| **SEO Audit** | `scripts/seo_audit.py` | `.github/workflows/seo-audit.yml` | Is every article and the live site technically and editorially healthy? |
| **Internal Link Matrix** | `scripts/link_matrix.py` | `.github/workflows/internal-link-matrix.yml` | Who links to whom, which articles are orphans/dead ends, which links should be added? |
| **SEO Protection** | `scripts/seo_protection.py` | `.github/workflows/seo-protection.yml` | Did anything that already works (URL, slug, title, canonical, indexability, schema, robots, sitemap, published content) change? |

Shared code: `scripts/seo_common.py` (read-only HTTP, HTML/JSON-LD parser, TF-IDF). Tests: `tests/test_seo.py` (hermetic; a fake WordPress site is started on localhost, no internet needed). They run inside the QA and Publisher workflows together with the publisher tests.

## Safety contract

- Read-only. No WordPress credentials are used; only public `GET`/`HEAD` requests. WordPress Trash, drafts and private content are never visible to these tools and are never touched.
- Published URLs, slugs, titles, canonicals and content are protected, not edited. Link and fix proposals are written to files for **separate QA-reviewed changes** (see `AGENTS.md`).
- The protection baseline is **append-only**: existing entries change only through an explicit `--accept ID --reason "…"`, which is also logged in `data/seo/protection-allowlist.json`.
- Reports live in `reports/seo/` (workflow artifacts, 30 days) and in the job summary. Machine-readable snapshots that are worth versioning are committed under `data/seo/`.

## 1. SEO Audit

```bash
python scripts/seo_audit.py --mode source                 # offline: Markdown sources + ledger (≈15 s)
python scripts/seo_audit.py --mode full --check-links     # + live site: REST list, every public page, links, robots, sitemap
python scripts/seo_audit.py --mode live --max-pages 20 --psi 5   # PageSpeed sample needs PAGESPEED_API_KEY (optional secret)
```

Source checks per article: word count (thin < 1,200, long > 3,000), H2 count and duplicates, title length, direct-answer opening, FAQ and sources sections, internal/external links, non-https links, links to pages that are not public, slug length. Site-level: QA errors, duplicate titles, **near-duplicate titles across the whole site (possible cannibalisation)**.

Live checks per public page: HTTP status, redirects, canonical present and equal to the permalink, `noindex` (meta and `X-Robots-Tag`), `<title>`, meta description, H1 count, JSON-LD (Article/BlogPosting, BreadcrumbList, invalid JSON), Open Graph, image alt text, viewport, mixed content, response time, HTML weight, page title still matching the ledger. Site level: ledger vs live (missing, URL/slug/category drift), `robots.txt` (`Disallow: /`, sitemap declared), XML sitemap coverage, home page schema, broken internal links (optional external links), PageSpeed LCP/CLS sample.

Severity: critical (indexability or identity broken), high, medium, low, info. Each page gets a 0–100 score. `--strict` exits 1 on any critical finding. Output: `reports/seo/audit.json`, `audit.md`, `audit-pages.csv`. Scheduled/manual runs keep one open issue titled **SEO Audit — latest report**.

## 2. Internal Link Matrix

```bash
python scripts/link_matrix.py                       # offline matrix + proposals into reports/seo/
python scripts/link_matrix.py --check-links --hubs  # + live HEAD checks and category-hub coverage
python scripts/link_matrix.py --write-data          # refresh data/seo/link-matrix.json, link-plan.json, docs/INTERNAL_LINK_MATRIX.md
```

The graph is built from the Markdown links in `posts/*.md`, mapped to published URLs through `data/publication-state.json`. Metrics: in/out degree, orphans, dead ends, reciprocal pairs, PageRank, per-cluster (Excel category) density and cross-cluster flow, policy compliance (target: ≥ 2 outgoing and ≥ 2 incoming links per article), links to legacy URLs outside the ledger.

Proposals (`data/seo/link-plan.json`, `reports/seo/link-plan.csv`) rank candidate additions by TF-IDF similarity of title + H2 + opening text, boosted for same cluster, orphan targets, low-inbound targets, reciprocal completion and dead-end sources; `anchor_hint` is the target's exact Excel title. Outputs: `link-matrix.csv` (dense matrix), `link-edges.csv`, `link-nodes.csv`, `link-plan.csv`, `link-matrix.json`, `link-matrix.md`. The current analysis is in [`INTERNAL_LINK_MATRIX.md`](INTERNAL_LINK_MATRIX.md).

Manual workflow run with `commit=true` commits the refreshed snapshot with `[skip ci]`.

## 3. SEO Protection

```bash
python scripts/seo_protection.py --mode repo        # offline guard (also runs on every posts/** push)
python scripts/seo_protection.py --mode baseline    # live: add pages that are not baselined yet (append-only)
python scripts/seo_protection.py --mode check       # live: compare the site with data/seo/protection-baseline.json
python scripts/seo_protection.py --mode baseline --accept 950 --reason "approved title change"
```

- **Repo guard (offline):** every ledger entry is `VERIFIED` and `publish`; `posts/NNNN.md` still exists, still passes QA and still hashes to the content that was published (editing a published post source is flagged `published_source_edited`); title and slug match; no duplicate WP ID, URL or slug; one WordPress category per Excel category; baseline URLs agree with the ledger.
- **Live check:** removed or non-200 pages, URL/slug change, redirect, canonical change, new `noindex`, title and category change, lost JSON-LD types, content edits (word-count delta; rendered-text changes without a modified date are `info` because widgets can change), `robots.txt` change or `Disallow: /`, sitemap shrinking by more than 20%, home canonical/availability. New public pages are reported as `unbaselined`.
- **Exit codes:** 0 clean, 1 drift/violation (critical or high), 2 no baseline yet, 3 live site unreadable. Daily check opens or updates one issue titled **SEO Protection alert** and closes it when a later check is clean.
- The baseline is added automatically after every successful Publisher run (new pages only) and can be created/extended manually: *Actions → SEO Protection → Run workflow → mode = baseline*. To approve an intentional change use `accept` + `reason`; the approval is recorded in the allowlist.

## First-time setup

1. Nothing to configure: no secrets are required. Optional: add `PAGESPEED_API_KEY` as an Actions secret to enable the PageSpeed sample (`psi_sample` input).
   If a WAF/CDN blocks the default bot name (`wp-aiwriter-seo-bot/1.0`), the tools say so (`audit_bot_blocked`, exit 3) instead of reporting mass failures; set the repository variable `SEO_USER_AGENT` or allow the GitHub runner.
2. Run **SEO Protection** once with `mode = baseline` (or let the next successful Publisher run create it). Until then the daily check reports a warning instead of failing.
3. Run **SEO Audit** (mode `full`) and **Internal Link Matrix** (`check_links`, `hubs`, optionally `commit`) from the Actions tab for the first live results. Schedules: audit Mondays 02:17 UTC, matrix Mondays 02:37 UTC, protection daily 01:47 UTC.

## What these systems deliberately do not do

They do not edit WordPress or the Markdown of published posts, do not call Search Console/Analytics (no credentials), do not measure browser-level Core Web Vitals except through the optional PageSpeed sample, and do not judge factual accuracy. Findings are inputs for human-reviewed, QA-gated changes.
