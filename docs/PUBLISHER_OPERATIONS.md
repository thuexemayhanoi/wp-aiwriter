# WP AIWriter — Excel-to-WordPress runbook

**Repo:** `thuexemayhanoi/wp-aiwriter`  
**WordPress destination:** `https://blog.rentbikehanoi.com/`  
**Canonical Excel matrix:** `data/topics.json` (IDs #146–500, exact byte checksum enforced).

## One place to control category publication

Modify only `data/publication-policy.json` → `active_category` to the **exact category path** that appears in `data/topics.json`. The engine calculates the start ID, end ID, total IDs and next category from the original Excel; no one needs to hand-enter numeric bounds. The publisher will not cross the configured category boundary.

Current category: `Cẩm nang > Ứng dụng > App xe máy` (#236–260; WP category 17, #236–243 VERIFIED as of the workflow change).

**End-of-category behavior:** Mark complete only after **every Excel row in the current category** has exactly one published WordPress post in the uniquely resolved, correctly nested WordPress category. The Actions job summary shows counts, missing author files, drafts, incorrect categories and duplicate published titles. Completion also creates one deduplicated GitHub Issue (subject to repository issue permissions). The next category remains blocked until its `active_category` is explicitly changed after review.

## Distinct writing and publishing roles

1. **AI writer during an active session** reads `data/topics.json` and `docs/WRITER_CHECKPOINT.md`, claims the smallest uncreated ID in the active category and writes `posts/NNNN.md`. Required YAML fields: `matrix_id`, exact `title`, exact `category_path`, `ready: true`. Use unique, well-researched Vietnamese editorial content; cite official sources for current specifications/legal details. Aim for 1,000–1,800+ useful words when enough meaningful information exists. Push validated files in small increments. No unsupported factual claims, fabricated prices, reviews or experience.
2. **QA** is a separate GitHub workflow: `WP AIWriter QA (No WordPress Writes)`. A push of `posts/**`, publisher code, tests or policy runs Python compilation, regression tests, strict Excel source/content QA and a dry-run source queue preview. It cannot publish.
3. **Publisher** is `Excel Matrix WP Publisher`. A **successful push-triggered QA on main** launches it automatically via `workflow_run`; it re-tests latest main, consumes ready sources in repeated batches of up to 5 **without delay** and verifies WordPress writes. Manual `workflow_dispatch` remains available for preview (`live=false` default) and manual diagnostics. Secrets stay inside Publisher; a concurrency lock prevents overlapping writers.
4. **Verify / checkpoint** after an actual create: checkpoint `POST_INTENT` to remote main before POST, create once, read back WordPress REST/private/public and public permalink, then record `VERIFIED` with WP ID and URL. Never blindly retry a POST after a timeout or missing prior post.
5. **Category review**: completion notice in Actions and GitHub Issues, then change just the policy's category when authorized and proceed with the next Excel group. A missing/ambiguous full WordPress parent/child category maps to **draft**, never Uncategorized by guesswork. Never change old URLs or category terms without explicit review.

## Duplicate and trash protection

- Search all existing editable WordPress posts before any create using Excel title, slug and matrix marker. Skip exact matches, including existing drafts; report conflicting matches, never mass-edit or overwrite existing posts.
- WordPress Trash belongs to the owner: do **not** empty it, auto-restore it, or delete any post. `Git it Write` must stay disabled while the GitHub REST publisher is in use.
- If a category is wrong on a legacy post, report its ID, current term and expected leaf; do not create a second article just to correct taxonomy.
- Existing URL, slug, canonical, sitemap, theme and unrelated WordPress content are protected.

## What is and is not automated

GitHub Actions handles **push QA PASS → automatic Publisher activation → category mapping → no-delay up-to-five-post batch draining → REST verification/checkpoints/progress reporting** for authored files. It **cannot write 300 missing articles by itself** without an active AI writer or a separately configured content generator. No AI API key, paid model endpoint, background model execution or cloud browser is implied.

This repo must never be described as having completed all 355 Excel topics simply because its workflow is in place.

## Useful commands (on a computer)

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/engine.py --mode qa
python scripts/engine.py --mode sync --limit 5   # no WP writes (dry run)
```

Do not run `--live` from a local machine without explicit owner approval and the secured credentials; prefer GitHub Actions to preserve concurrency and the remote publication ledger.

## Publisher status fields

`reports/latest.json` and the Actions job summary include: the active Excel category and its exact ID range; correctly published count; ready/unwritten files; missing WordPress posts; drafts; category mismatches; duplicate titles; category completion flag; and next Excel category. GitHub uploads `reports/` as run artifacts. The separate QA workflow uploads non-publishing source readiness receipts.

## Business factual policy (only when relevant)

The owner-supplied NAP and rental price/policy facts apply to *Cho Thuê Xe Máy Nguyễn Tú* content when that business is actually the relevant entity. Do not add a second business address or pricing to unrelated informational motorcycle/electric-bike articles. Do not silently change WordPress identity, structured data or canonical to another domain based solely on business notes.

## Auto-publish safety after owner approval (2026-10-16)

- Zero scheduled sleeps: every successful **push** QA on `main` triggers the publisher, which rechecks all code and source QA inside the publication lock before using secrets.
- No extra owner approval is needed for each push. **Changing `active_category` still requires explicit owner approval.**
- The publisher drains all authored ready posts in the active category in iterations of at most five; finite job runtime and loop caps only guard against runaway jobs, not inter-batch waiting.
- Failed QA, broken credentials, category ambiguity, duplicate titles, unknown POST outcomes and ledger drift fail closed. No editing old URLs, deleting/restoring Trash or parallel publisher.
- GitHub Actions does not autonomously generate missing prose: an active writer must commit `posts/NNNN.md` to `main`.
