# WP AIWriter — GitHub → WordPress QA-gated autopublish

> **AI START HERE — 478 EN topics (20/10/2026):** For new English writing at `/en/`, read [`docs/EN_478_AI_PLAYBOOK.md`](docs/EN_478_AI_PLAYBOOK.md) first. The approved-title planning CSV is [`en/title-plan-478.csv`](en/title-plan-478.csv); `en/topics.json` supplies the actual English article IDs/titles/slugs/category IDs, and `data/en-publication-state.json` prevents republishing the 22 baseline VERIFIED articles. Run `python scripts/en_title_plan.py --check` and `--next 3` before starting. **English only; no `excel-` URL prefix; QA >=85; 1,600–5,000 English words; continuous QA-gated EN publishing without an article-count cap; automatic continuation on runner time cutoff.** On a lost connection, resume from the GitHub ledger, manuscripts and [EN checkpoint](docs/EN_WRITER_CHECKPOINT.md), not from chat memory. The Vietnamese instructions below remain unchanged.



**WordPress:** https://blog.rentbikehanoi.com/  
**Repo:** https://github.com/thuexemayhanoi/wp-aiwriter  
**Immutable Excel topics:** `data/topics.json`, IDs #146–500 (355 titles/categories).

**EN quick-start:** `python scripts/en_writer_brief.py --limit 3` prints the next three safe *research candidates* with exact source title, locked slug, EN taxonomy parents, search intent, source priority and unchanged QA rules. It is read-only, needs no AI/API keys and does not verify live WordPress or publish. Check `docs/EN_478_AI_PLAYBOOK.md` before writing.

**EN publishing policy (21 October 2026):** The `--limit 3` selector produces **research suggestions only**, not a publishing cap. Every EN manuscript passing QA >=85, word minimum, factual/duplicate/taxonomy guards and live WordPress checks is eligible for continuous automatic publication; no three-post approval cycle. `en/publication-policy.json` has no `batch_size` or `max_batches_per_run`. The serialized EN publisher preserves `POST_INTENT`/`VERIFIED` receipts and resumes between GitHub runner windows. The Vietnamese/Excel publisher below remains a **separate workflow**.


## Zero wait after QA PASS

1. An active Claude / ChatGPT Work / Gemini writer or person writes `posts/NNNN.md` using the exact Excel `matrix_id`, `title`, `category_path`, `ready: true`, and original, verified Vietnamese prose.
2. Push to `main` automatically runs **WP AIWriter QA (No WordPress Writes)** — strict source QA, duplicate checks and Python regression tests; QA has no WordPress credentials.
3. **Only successful push QA on main** automatically starts **Excel Matrix WP Publisher** (GitHub `workflow_run`). The publisher repeats tests and QA on the latest main, then immediately performs authenticated WordPress REST publishing under a single concurrency lock.
4. Each iteration attempts **up to 5 posts**, writes a remote `POST_INTENT` checkpoint *before* create, verifies private/public REST + permalink, then records `VERIFIED`; repeats **without any waiting, schedule or manual button** until all ready sources in the approved category have been handled.
5. Missing/ambiguous full WordPress category ancestry → draft, never guess. Existing posts/drafts, duplicates and uncertain previous creates → skip/block, **never overwrite**. Never delete/restore WordPress Trash, change existing URLs, slugs, SEO, or canonicals. The next Excel category still requires explicit owner approval (`data/publication-policy.json`).

**No AI API key and no time-based trigger.** GitHub Actions **cannot write new articles by itself**: an active writer must still create and push them. QA is deterministic and cannot independently verify every factual claim.

## SEO systems (GitHub only, read-only)

Three systems run on GitHub Actions without WPVibe, WP Agent or any plugin: **SEO Audit**, **Internal Link Matrix** and **SEO Protection**. They only read the public site, never write to WordPress, and propose changes for separate QA-reviewed work. See `docs/SEO_SYSTEMS.md` (workflows `seo-audit.yml`, `internal-link-matrix.yml`, `seo-protection.yml`).

## Files and operating instructions

- `AGENTS.md`: current editorial and safety contract
- `docs/PUBLISHER_OPERATIONS.md`: production runbook
- `docs/WRITER_CHECKPOINT.md`: last known article, WP IDs and next queue
- `docs/SEO_SYSTEMS.md`, `docs/INTERNAL_LINK_MATRIX.md`: SEO audit, link matrix and protection runbook / current analysis
- `scripts/seo_*.py`, `scripts/link_matrix.py`, `data/seo/`: the three SEO tools and their committed snapshots
- `posts/NNNN.md`: published/ready source
- `scripts/engine.py`: QA and create-only WordPress REST publisher
- `.github/workflows/publisher-quality.yml`: push-triggered QA with no secrets
- `.github/workflows/wordpress-publisher.yml`: **QA-success auto-trigger**, optional manual preview via `workflow_dispatch` (`live=false` by default)
- `data/publication-state.json`: irreversible write-ahead ledger and verification receipts

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/engine.py --mode qa
python scripts/engine.py --mode sync --limit 5  # safe preview only
```

GitHub Actions Secrets: `WP_USERNAME` (or `WP_USER`) and `WP_APPLICATION_PASSWORD`. Missing credentials fail visibly instead of falsely reporting success. Never paste secrets into chat, commits or repo. Keep parallel WordPress-sync plugins inactive.

**Baseline before this workflow change:** 98/355 Excel posts published, 250 total WordPress posts, category `App xe máy` 8/25 (#236–243); confirm live state for future counts.

## SEO Engine (read-only audits of the live site)

`seo/` audits the published WordPress site without writing to it: REST inventory, HTML crawl, robots/sitemaps,
technical SEO, internal-link graph and suggestions, duplication/cannibalization, AEO/GEO checks, optional
PageSpeed and Search Console. Reports are committed under `reports/` and `data/seo/`. Only
`approved-seo-fixes.yml` can change WordPress, and only for owner-approved fixes. Runbook: `docs/SEO_ENGINE.md`.

```bash
python -m unittest tests.test_seo_engine -v      # offline
python -m seo run --full --external --psi        # needs network access to the site
```

