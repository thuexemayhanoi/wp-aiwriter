# English title-plan queue — fixed 478-topic cohort (baseline 2026-10-20)

> **CURRENT EN FAST ENTRYPOINT (21 Oct 2026):** [`EN_FAST_WRITER.md`](EN_FAST_WRITER.md). The existing title in `en/topics.json` is already writable. `title_approval=NEEDS_EDITORIAL_REVIEW` concerns the optional 60–80-character replacement suggestion only and **never blocks authoring with the current canonical title**. The old numbered proposal-approval steps below are optional only if you choose to rename a title.



**Site:** https://blog.rentbikehanoi.com/en/  
**Repo:** `thuexemayhanoi/wp-aiwriter`  
**Data:** `en/title-plan-478.csv` (478 rows; working English titles 60–80 characters).

## Verified baseline
- `en/topics.json`: 500 existing English-only stable topic IDs.
- `data/en-publication-state.json`: 22 English posts VERIFIED and published as of the baseline; those IDs do not appear in the 478-row plan. WP Agent independently confirmed their published WordPress URLs.
- 21 registered EN WordPress category IDs (46–56 and 60–69; only existing terms are referenced). Vietnamese category IDs and content are not part of this plan.
- 418 existing unpublished titles were shorter than 60 characters and have **proposed** longer titles in a separate column. Original titles, permanent slugs and term IDs remain unchanged in `en/topics.json` until safe explicit approval.
- Topics currently cover 18 of the owner's 35 requested thematic groups; the 17 unrepresented clusters are **gaps**, not grounds for inventing duplicate pages or changing the 500-ID source without research.

## English URL protection (no spreadsheet prefixes)
- Public EN articles must use the exact `slug` from `en/topics.json`, e.g. `/en/hanoi-motorbike-rental-guide/`, **not** `/en/excel-123-hanoi-motorbike-rental-guide/`.
- `topic_id`, the filename `NNNN.md`, Excel row numbers and Google Sheet labels exist only in internal tracking. Do not derive a public slug from the Excel filename, topic ID or proposed title.
- `scripts/en_engine.py` rejects Excel-, matrix-, spreadsheet- or numbered sheet-prefixed EN slugs while loading the topic matrix and before WordPress publishing; it also checks WordPress's **actual draft slug** before registration or publication. Unexpected rewrite leaves the post as a draft in the ledger, to be reconciled manually. It must never be blindly retried.
- All 500 pre-existing EN source slugs were checked and have no `excel-` prefix. The original 22 published EN posts retain their URLs and canonicals. Existing Vietnamese `/excel-ID-...` legacy URLs are deliberately **not** changed by this English-only task; correcting those later requires a separate URL/redirect/SEO migration plan.

**Fast candidate packet:** `python scripts/en_writer_brief.py --limit 10 --format compact` generates 1–10 read-only canonical, unclaimed EN topics using this CSV, EN matrix, ledger and taxonomy snapshot. It does not change data or reduce QA. WordPress Publisher performs the live checks before publication; manually investigate only known conflicts.

## Current writing path (canonical titles)

1. Run `python scripts/en_writer_brief.py --limit 10 --format compact`. It checks fixed IDs, current topic ID/title/slug/category, English ledger and manuscript existence. No need to validate or approve Excel headline suggestions one by one.
2. Use **unchanged** `en/topics.json` title/slug/category_id in `en/posts/NNNN.md`. Write original, distinct English content 1,600–5,000 words, research official legal facts and include useful links. QA ≥76, all hard gates mandatory.
3. Run `python scripts/en_engine.py --mode qa` and push EN manuscripts after review. GitHub Actions reruns all tests + QA and automatically publishes every eligible file to WordPress after live duplicate and route validation; confirm `VERIFIED` ledger. No EN article/batch-count limit.
4. **Optional title-change branch only:** if an existing canonical headline genuinely needs revision, change the **suggestion** and mark `title_approval=APPROVED` after review, then execute `python scripts/en_title_plan.py --apply-approved` only for unpublished/unwritten IDs. Inspect the diff; preserve slug/category/ID. The proposal cannot override a published URL.

`python scripts/en_title_plan.py --check` continues to protect 478 unique topic IDs, source category/slug and publication phases. Imperfect or duplicate optional headline suggestions do not prevent canonical-title writing. `--next 10` is a quick JSON preview.

**Non-negotiable:** Do not edit any Vietnamese content, menu, categories, canonical, slug or sitemap; no paid AI API writing, no publication without individual QA/Gates and live verification, no overwrites. Do not change a post with any ledger entry or existing manuscript. Never silently change a category to fit a topic. The 35 group labels in the CSV are topical descriptions, not WordPress taxonomy IDs.

**Note on title lengths:** 60–80 is the owner's temporary title-planning range, not a ranking guarantee. The existing QA engine applies a small title-length penalty above 65 characters. Editors should prefer clarity, distinct intent and natural English and retain QA >=76 rather than keyword stuffing.
