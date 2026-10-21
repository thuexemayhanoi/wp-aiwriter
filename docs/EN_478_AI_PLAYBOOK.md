# MASTER RUNBOOK — NGUYỄN HÀ / WP-AIWRITER / 478 EN ARTICLES
**Updated:** 2026-10-20 · **Scope:** English articles ONLY at `https://blog.rentbikehanoi.com/en/`.  
**Applies to:** ChatGPT Work, Claude, Gemini, Codex, GitHub writer, any future AI session.  
**Repository:** `thuexemayhanoi/wp-aiwriter` — branch `main`.

> **One canonical handoff.** Read this file before touching the 478-row English queue. Do not improvise a replacement Excel or accidentally run the Vietnamese writer. GitHub stores the durable work state. A session being disconnected must not lose an article that was already committed.

## 0. Start in 60 seconds — exact reading order

1. `AGENTS.md`, `CLAUDE.md` (global repo rules and this EN handoff).
2. **This document** and `docs/EN_478_TITLE_PLAN.md`.
3. `docs/MENU_TAXONOMY_MAP_VI_EN.md` + `data/navigation-map.json` (current *snapshot*; live WordPress wins).
4. `en/title-plan-478.csv` (478 rows), `en/topics.json` (500 source topics), `en/publication-policy.json`, `en/business.json`.
5. `data/en-publication-state.json` (durable publish ledger), `en/posts/` (authored manuscripts), `docs/EN_WRITER_CHECKPOINT.md` (handoff/history), latest GitHub Actions status.
6. For operational or QA detail, `docs/EN_PIPELINE.md` and `tests/test_en_engine.py`.

**Important:** The optional downloadable Excel and the Google Sheets copy are human-friendly views. The actual GitHub pipeline reads **`en/topics.json` and `en/posts/NNNN.md`**. Editing the spreadsheet/Google Sheet does **not** automatically change GitHub. The CSV in GitHub is the authoritative *title-planning/approval queue*, not the WordPress publishing ledger.

### Fast-track next three without lowering QA

Once the startup reading above is complete, run `python scripts/en_writer_brief.py --limit 3` (or `--format json`). The script checks the 478-row GitHub plan against the EN topic source, manuscript directory, durable publication ledger, editorial policy, and the read-only taxonomy snapshot; it returns the next three available IDs with an exact slug, current canonical title, proposed title, actual category ancestors and search-intent/legal-research prompts. It writes **nothing**, cannot bypass editorial approval, cannot check live WordPress and cannot publish. The AI must still conduct live duplicate/term verification, factual research, original English writing and the full QA ≥85 procedure. If a shell is unavailable, manually read the same files and do not claim the script ran. Rerun after every verified batch; never use a cached packet after other writers have pushed.

## 1. Snapshot vs living state

- Baseline on **20 October 2026**: `en/topics.json` contains **500** planned English IDs; `data/en-publication-state.json` contains **22 VERIFIED/published** English IDs; `en/title-plan-478.csv` contains the other **478 candidate IDs**.
- **Do not repeat 478 as a live remaining-unpublished count after new publications.** The 478-row file is a *fixed campaign cohort*. Current completion = reconcile each row against the EN ledger, authored files **and live WP**. Never reset ledger counts or publish based on a stale spreadsheet cell.
- **Existing EN taxonomy:** 21 WordPress category terms (IDs 46–56 and 60–69), with ancestor hierarchy in the navigation map. `subject_cluster_en` is only a topical group — **not** a category/term ID.
- The owner's **35 EN thematic groups** are a planning checklist. Existing 500 topics currently map into only **18** of them; the other 17 are identified gaps. Do not invent thin English pages, add categories or change historical IDs to force equal coverage. Research separate valid intents and request taxonomy/plan changes through review.
- Source titles and slugs for the 22 published posts are frozen; published ledger `VERIFIED` beats CSV and checkpoint prose.
- **Brand:** Nguyễn Hà, not Nguyễn Tú. Facts and prices ONLY from `en/business.json` and independently checked official/current sources.

## 2. The 478-row CSV schema — no guessing

`en/title-plan-478.csv`, columns:
- `topic_id`: stable numeric ID mapping directly to `en/topics.json[id]` and file `en/posts/NNNN.md` (four digits). An internal tracking ID, **never part of the URL**.
- `category_id` / `category_en`: existing EN WordPress *term ID* and readable label, not the parent name, menu or page.
- `subject_cluster_en`: editorial grouping (35 requested group vocabulary).
- `existing_title_en`: historical EN topic title; do not edit as a shortcut.
- `planned_title_en`: **proposed**, 60–80 characters, not editorially final; some expansions may sound generic.
- `title_chars`: character count of the proposal; re-check if reworded.
- `slug_locked`: permanent planned public slug; do not add `excel-`, row numbers, or blindly recreate from a revised title.
- `source_intent`: existing search-intent notes. Empty/generic intent => research is still mandatory.
- `writing_status`: only a human planning cue; **never authoritative for publish status**.
- `title_approval`: `NEEDS_EDITORIAL_REVIEW` (default), `APPROVED` (human/AI editor checked), `SYNCED` (only after GitHub source reflects approved title).
- `qa_score`, `wp_post_id`, `published_url`: informative reporting fields; values are only trusted after live verification.
- `note`: safe guidance and collision warnings.

**Title rule:** English-only; proposed length 60–80 characters for the planning file. Headlines must be grammatical, useful, truthful and distinguishable by search intent. Do not force keyword stuffing to hit 80. Current EN article QA may penalize titles above 65 by a few points; QA >=85 remains mandatory.

## 3. A → Z execution for ONE EN article (repeat in small batches)

**A — Identify language.** Explicitly declare `TARGET=EN`, `SITE=https://blog.rentbikehanoi.com/en/`, `REPO=thuexemayhanoi/wp-aiwriter`. **STOP if the task is actually VI, /wp-writer, /global or thuexemaynguyentu.com.**

**B — Sync repo/main and record HEAD.** Do not overwrite parallel writer commits or writer's current work. If a prior attempt was interrupted, read Git history/checkpoint before continuing.

**C — Load policy, map, backlog, ledger.** Trust live WordPress for current terms, existing posts/URLs and VI-EN Core. If live taxonomy conflicts with snapshots, BLOCK and investigate, **do not modify WordPress to match the snapshot**.

**D — Run read-only checks** (if a shell exists):
```bash
python -m pip install -r requirements.txt
python scripts/en_title_plan.py --check
python scripts/en_title_plan.py --next 3
python scripts/en_engine.py --mode sync
```
The last command is a **dry run**, never a publish command. If the session has no shell, read the corresponding GitHub files, list 3 candidate rows, and say tests have not run — do not claim PASS.

**E — Claim the next safe row.** Pick a CSV ID absent from the publication ledger and `en/posts/NNNN.md`, reconfirm absent on **live WP** by English title, slug and search intent, including drafts and existing /en/ pages. Use **max 3 small candidates per editorial pass**; do not assume a GitHub claim alone is a global mutex.

**F — Research intent & dedupe.** Compare all 500 planned titles, 22+ published EN posts, pages and current WP posts. Different angles must actually answer distinct questions (no doorway pages or same-content location permutations). For regulations, verify official laws/effective dates and source links. Don't fabricate personal experience, booking, travel times, services, models or prices.

**G — Review proposed headline.** The 60–80 character `planned_title_en` is **not automatically approved**. If the original title is better, keep the existing source title and record the editorial decision; if adopting/rewriting the proposal, first update `planned_title_en` and `title_chars` in GitHub CSV and set `title_approval=APPROVED` only after uniqueness/factual check.

**H — Sync approved titles into the source matrix safely.**
```bash
python scripts/en_title_plan.py --check
python scripts/en_title_plan.py --apply-approved
git diff -- en/topics.json en/title-plan-478.csv
```
This command changes **only approved, not-yet-authored, not-yet-ledgered EN titles**. It does not change IDs, category IDs or slugs. Commit the source title update before or with the manuscript; don't write a future proposal title as article metadata until `en/topics.json` matches. If original title is retained, use it verbatim; never add `excel-` to `slug_locked`.

**I — Author manuscript at `en/posts/NNNN.md`.** Use exact canonical title/slug/category from `en/topics.json`, **not** the current spreadsheet display. Required front matter:
```yaml
---
en_id: 10
title: Exact current title from en/topics.json for topic 10
slug: exact-locked-slug-from-en-topics-json
category_id: 53
description: An original accurate English meta description appropriate to the article.
ready: true
---
```
The above is a **shape/example**, not an instruction to force ID 10/category 53 or those placeholders into production. After front matter, produce original English prose with helpful H2 sections, authentic examples, FAQ, dated references and internal /en/ links. Don't insert Markdown H1 inside body. QA requires **1,600–5,000 English words** on new/revised posts.

**J — QA thoroughly.** No duplicated title or URL, no overlapping intent, correct category and term parents, no leaked Vietnamese material, no Nguyễn Tú data, legal citations verified, EN-only internal links to genuine 200 pages, natural meta description, strong original answers. Score **>=85** plus all hard gates:
```bash
python -m unittest discover -s tests -v
python scripts/en_title_plan.py --check
python scripts/en_engine.py --mode qa
python scripts/en_engine.py --mode sync     # dry-run preview
```
**FAIL => repair in GitHub, do not publish**; do not weaken hard guards, omit source verification or mark ready without passing. If tools unavailable, do not assert test pass.

**K — Commit early, publish through EXISTING workflow.** Push a small QA-ready EN manuscript/approved title to `main` only after review. A successful push-triggered `EN Writer QA (No WordPress Writes)` can trigger `EN Publisher` (subject to policy). GitHub Actions runs QA/publisher, **not** the AI writer: it will not spontaneously research or generate 478 article bodies. No external AI API keys are needed.

**L — Continuous QA-gated publication (owner approved 2026-10-21).** The English publisher has no article-count or batch-count limit. Every ready original EN manuscript must pass QA ≥85, all hard gates, WordPress duplicate preflight and immutable ledger protection. GitHub runner time is a technical boundary: save progress and automatically dispatch the next serialized publisher run when the deadline approaches. No manual approval per 3 posts is required. Keep `min_words=1600`; do not touch VI.

**M — Verify LIVE.** The EN Publisher creates a WordPress draft, checks actual post slug (rejects if WordPress adds `excel-`), registers with VI-EN Core, publishes, checks WordPress post ID, English category ID, title, public URL `/en/{slug}/`, HTTP 200, English language marker, self canonical and normal-URL redirect; then writes `VERIFIED` to `data/en-publication-state.json`. **Only this combination counts as published.** Check Yoast sitemap where applicable.

**N — Report and checkpoint.** Add a compact new entry to the **TOP of** `docs/EN_WRITER_CHECKPOINT.md` (don't delete previous history): UTC date, Git HEAD, topic IDs, changed files, chosen category IDs and ancestors, proposed-vs-canonical title decision, QA score/evidence, WP ID/URL if live-verified, ledger phase, pending errors, next 3 IDs. Commit checkpoint. CSV planning status can be updated *later*, never used instead of the ledger.

**O — Resume after lost quota, phone signal or new AI session.** Start back at step 0; fetch latest `main`; check the EN ledger first, then `en/posts/`, then checkpoint, then fresh WP. **Do not restart from #10 by memory**, reset `POST_INTENT`/`VERIFY_PENDING`, duplicate a post, or force a manuscript rewrite. If WordPress write outcome is unknown, BLOCK and reconcile via WP ID/slug before any retry.

## 4. Quick commands and source priority

```bash
# All safe read-only previews:
python scripts/en_title_plan.py --check
python scripts/en_title_plan.py --next 3
python scripts/en_engine.py --mode qa
python scripts/en_engine.py --mode sync

# Editable title syncing, opt-in only after actual review:
python scripts/en_title_plan.py --apply-approved
git diff -- en/topics.json

# Global tests:
python -m unittest discover -s tests -v
```

**Priority when conflicts appear:**
- Current WordPress facts/post ownership/category/URL (readback) > stale taxonomy snapshot.
- Durable EN ledger phases and post IDs > checkpoint prose > spreadsheet `writing_status` or `published_url`.
- Source of *future article metadata* = `en/topics.json` and `en/publication-policy.json`; CSV is a reviewed title proposal layer; article file must match source exactly.
- Before creating any WordPress post: duplicate/title/slug/intent preflight > hurry to publish.

## 5. Errors, owners and safe repairs

| Condition | Action |
|---|---|
| `--check` fails | Fix only the offending EN CSV/source row after inspection; do not reset whole matrix. |
| Plan title not approved | Research and review; keep existing title or approve + sync into `en/topics.json` before drafting. |
| Slug contains `excel-` / `matrix-XX-` | BLOCK publication, correct future planned EN source only after duplicate check; **never rewrite an existing published permalink silently**. |
| EN category missing or parent mismatch | BLOCK; verify WordPress term ID/ancestry; don't create random terms. |
| Candidate duplicates a live or drafted EN post | SKIP and record; never POST again. |
| QA <85 / <1,600 words | Repair draft in GitHub and rerun; don't weaken policy. |
| WordPress draft rewrites slug | Keep draft, preserve ledger, reconcile safely; do not publish automatically. |
| Ledger `POST_INTENT`, `DRAFT_CREATED`, `REGISTERED`, `VERIFY_PENDING` or `REGISTER_FAILED` | Investigate WordPress and Actions receipts before any retry; never erase checkpoint phases. |
| Network dropped, quota exhausted | Commit what is validated, leave unfinished work unready, write checkpoint, stop; next session resumes from persistent state. |
| 17 missing topical groups | Separate research and editorial approval; not solved by randomly assigning old topics to unrelated taxonomy. |
| Need to fix old Vietnamese `/excel-N-...` | **Separate SEO migration** (backup, URL mapping, targeted 301, canonical/internal-link/GSC verification); out of scope for EN. |

## 6. AI handoff — copy into a new chat if needed

> Tiếp tục repo `thuexemayhanoi/wp-aiwriter`, LUỒNG TIẾNG ANH DUY NHẤT. Đọc `AGENTS.md`, `CLAUDE.md`, `docs/EN_478_AI_PLAYBOOK.md`, `docs/MENU_TAXONOMY_MAP_VI_EN.md`, `data/navigation-map.json`, `en/title-plan-478.csv`, `en/topics.json`, `en/publication-policy.json`, `data/en-publication-state.json` và `docs/EN_WRITER_CHECKPOINT.md`. Đối chiếu WP live và `en/posts/`, bỏ các bài đã VERIFIED, lấy tối đa 3 ID tiếp theo. Duyệt tiêu đề 60–80 ký tự theo intent; nếu dùng tiêu đề mới, phê duyệt và đồng bộ an toàn vào `en/topics.json`, giữ nguyên ID/slug/category. Nghiên cứu bài EN gốc 1.600–5.000 từ, QA ≥85, chống trùng; commit/push rồi theo dõi EN Publisher, chỉ ghi VERIFIED sau khi xác minh WP live. Không sửa VI, bài cũ, URL, canonical hoặc menu; không tạo slug `excel-`. Nếu rớt mạng/quota, ghi checkpoint và phiên sau tiếp tục từ ledger, không đăng lại. Báo cáo ngắn bằng tiếng Việt theo ID/QA/Post ID/URL/trạng thái.

## 7. Compact reporting after each pass

```text
EN ONLY | HEAD: <sha> | IDs selected: <n,n,n>
Taxonomy check: PASS/BLOCK | Title review: PASS/PENDING
EN manuscripts: <paths> | QA: <actual score or NOT RUN>
Git push: <commit SHA or NOT PUSHED>
WordPress: <VERIFIED + actual WP IDs/URLs | PENDING | BLOCKED>
EN ledger: <actual phase per ID> | Next IDs: <n,n,n>
Issue and next action: <specific evidence>
```

This playbook is a **process document**; owner approval removes EN article-count and batch-count limits but never authorises bypassing QA, safety gates, live verification or existing URL protection.
