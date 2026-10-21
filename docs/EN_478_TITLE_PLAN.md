# English title-plan queue — fixed 478-topic cohort (baseline 2026-10-20)

> **AI ENTRYPOINT:** [`docs/EN_478_AI_PLAYBOOK.md`](EN_478_AI_PLAYBOOK.md) is the single A–Z instruction and restart guide. It is referenced from `README.md`, `AGENTS.md` and `CLAUDE.md`. Use GitHub CSV for planning/approval, `en/topics.json` for publisher metadata, the EN ledger for VERIFIED, and `docs/EN_WRITER_CHECKPOINT.md` for handoff. Google Sheets/Excel does not automatically sync to this repo.



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

**Fast candidate packet:** `python scripts/en_writer_brief.py --limit 3` generates a *read-only* three-article research brief from this CSV plus the existing EN matrix, ledger and taxonomy. `--format json` is available for AI agents. It does not change any row or reduce QA; always check WordPress live before writing.

## Usage and safety
1. `python scripts/en_title_plan.py --check` validates all 478 records, English titles (60–80 characters), unique IDs/titles, source slug and category, and current ledger phases. No WordPress writes.
2. `python scripts/en_title_plan.py --next 3` shows the next **unpublished and unwritten** EN candidates. Reconcile against live WP and `en/posts` before claiming a row.
3. Research search intent thoroughly, validate facts with sources (especially legal content), check title + semantic overlap against existing EN posts, approved EN pages, 500-topic matrix and live WordPress. Working-title extensions may be generic; **they are candidates, not editorially approved headlines**.
4. Mark only reviewed, genuinely unique headings as `title_approval=APPROVED`; run `python scripts/en_title_plan.py --apply-approved` to synchronise those approved, *unwritten, unledgered* titles into `en/topics.json`. This preserves original ID, slug, category, published legacy posts and 500-topic count. Inspect the diff and commit.
5. Write `en/posts/NNNN.md` using **the exact now-synchronised title, slug and category ID from `en/topics.json`**. English prose only; 1,600–5,000 words for new work; QA >=85, sources, internal links and fact-checks. Never write a proposal title as a post before synchronisation.
6. Existing `EN Writer QA` then `EN Publisher` handles QA → draft → VI/EN registration → publish → live readback. **Owner update 2026-10-21:** no EN article/batch-count limit or next-three approval. All eligible manuscripts pass full QA and WordPress gates; the publisher resumes across runner time windows. `--next 3` remains an **editorial research preview only**. Only the live-verified `VERIFIED` ledger establishes a publication, never a stale CSV status.

**Non-negotiable:** Do not edit any Vietnamese content, menu, categories, canonical, slug or sitemap; no API-based AI writing, no mass automatic publication, no overwrites. Do not change a post with any ledger entry or existing manuscript. Never silently change a category to fit a topic. The 35 group labels in the CSV are topical descriptions, not WordPress taxonomy IDs.

**Note on title lengths:** 60–80 is the owner's temporary title-planning range, not a ranking guarantee. The existing QA engine applies a small title-length penalty above 65 characters. Editors should prefer clarity, distinct intent and natural English and retain QA >=85 rather than keyword stuffing.
