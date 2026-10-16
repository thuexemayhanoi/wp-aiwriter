# Production checkpoint — 2026-10-16, Excel #229–231 published (latest)

- Owner explicitly authorized another 3–5-article batch in `https://github.com/thuexemayhanoi/wp-aiwriter` to `https://blog.rentbikehanoi.com/`. Only active taxonomy: `Cẩm nang > Hãng xe > Hãng xe điện` (#201–235, WP category ID 21). No WordPress Trash interaction.
- Three original full-length, manufacturer-sourced articles added to `main`: `posts/0229.md` (display readings and warnings; title exactly Excel #229), `posts/0230.md` (Smart Key vs mechanical key; Excel #230), `posts/0231.md` (manufacturer smartphone app functions and privacy; Excel #231). All `matrix_id`, titles and taxonomy paths match `data/topics.json`. Source research used VinFast, Selex and Dat Bike official documentation.
- QA workflow [38896797537](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38896797537) completed **SUCCESS**: 67/67 source Markdown QA PASS, **18/18 regression tests PASS**, 0 QA FAIL.
- The live WordPress publisher [38890257103](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38890257103) latest rerun **SUCCESS** and remotely verified all **three new published posts**: Excel **#229 → WP 919**, **#230 → WP 920**, **#231 → WP 921**, all `phase=VERIFIED`, `status=publish`, `category_id=21`. IDs/permalinks stored in `data/publication-state.json`, no duplicate groups or errors.
- **Progress**: **86/355 Excel topics published**, previous category #146–200 completed 55/55; active #201–235 has **31/35** published. Site-wide WordPress published count from GitHub publisher: **238**. Only **4 source articles #232–235** remain in current category. GitHub source files #165–231 count **67**; **269 ID files #232–500** still unwritten.
- **NEXT BATCH: #232, #233, #234, #235**. Read immutable topics for exact titles and taxonomy. Author four distinct, source-supported Vietnamese articles, run QA, publish with authorized workflow in a single batch size 4 only after next owner approval; no duplicate creation or background promises. **STOP when #235 verified**, produce end-of-category report and wait for explicit authorization before changing `data/publication-policy.json` to next category #236+.
- Do not delete or edit old URLs/canonicals or touch WordPress Trash. Leave policy's fail-closed taxonomy mapping unchanged unless specifically authorized.

---

# Production checkpoint — 2026-10-16, Excel #223–225 verified on WordPress

- Owner approved next 3-post batch within Excel `Cẩm nang > Hãng xe > Hãng xe điện` (#201–235, WordPress category **21**). The WordPress Trash is exclusively owner-managed and was not touched.
- Authored and committed to `main` `posts/0223.md` (international-brand technology, Honda/YADEA), `posts/0224.md` (cross-brand buyer comparison rubric distinct from pairwise YADEA/VinFast), `posts/0225.md` (IEC 60529 IP Code, IP67/IPX7, flood-related safety). Exact source ID/title/ancestor categories match `data/topics.json`. Official source pages referenced; no fabricated prices, user testing or product ownership.
- Independent GitHub QA workflow [38886571339](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38886571339) completed **SUCCESS**: 61/61 written articles QA PASS, 18/18 regression tests PASS, 0 QA FAIL.
- Owner-approved live publisher [38867887824](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38867887824) latest rerun **SUCCESS**: three new posts and remote receipts all `VERIFIED`, `status=publish`, `category_id=21`: Excel **#223→WP 913**, **#224→WP 914**, **#225→WP 915**. No duplicate groups or publisher errors; canonical published URLs in `data/publication-state.json`.
- Excel publication progress **80/355**, first category #146–200 **55/55** completed; active Hãng xe điện #201–235 **25/35** correctly published. **10 IDs #226–235** still need article files and WordPress publication; **275 IDs #226–500** not yet authored.
- **NEXT WRITER**: #226 phanh tái sinh, #227 chế độ Eco, #228 chế độ Sport; read exact title and taxonomy from `data/topics.json`, author 3–5 high-quality posts, QA, then publish only with owner approval. Check topical overlap: regeneration vs drive modes have distinct search intents.
- Keep `data/publication-policy.json` active category unchanged until #235 completes and owner receives category report. No autonomous AI source generation happens inside GitHub Actions; never auto-modify old WordPress URLs/slugs/canonicals or empty/restore/delete posts from Trash.

---

# WordPress production checkpoint — 2026-10-16 through Excel #222

- Owner approved exactly the next batch of 3. Source Markdown `posts/0220.md`, `posts/0221.md`, `posts/0222.md` was authored, pushed individually and matches the immutable Excel title/ID/full taxonomy `Cẩm nang > Hãng xe > Hãng xe điện`. Research compared official VinFast, Selex and Dat Bike sources; #220 is charger strategies, #221 is station-network access/reliability, #222 is conditional advantages of Vietnamese brands.
- Independent QA workflow [38884687655](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38884687655) **SUCCESS**: **58/58 authored QA PASS**, **18/18 regression tests PASS**, no QA failure.
- Owner-authorized live publisher [38867887824](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38867887824) latest job **SUCCESS**; **three new WordPress posts created and verified** with exact Excel taxonomy category **21**, status `publish`: #220 → WP **910**, #221 → WP **911**, #222 → WP **912**. `VERIFIED` ledger receipts and public URLs in `data/publication-state.json`. Duplicate groups=0, errors=0.
- Progress: **77/355** Excel titles published, first category #146–200 **55/55** completed, active #201–235 Hãng xe điện **22/35** correctly published. **13 IDs #223–235** still need source and publication; full matrix remaining source **278 IDs #223–500**.
- **NEXT WRITER BATCH:** #223, #224, #225; obtain exact IDs, titles and ancestry from `data/topics.json`. Write small, unique researched posts, run no-write QA, obtain explicit owner approval for 3–5 posts, then publish with verification. Do not advance to next Excel category #236+ without end-of-category report and approval.
- Keep `data/publication-policy.json` active category unchanged. Preserve older post URLs, slugs, canonicals, all old published posts, and WordPress Trash; no deletions or unattended self-writer assumed.

---

# Production checkpoint — 2026-10-16, Excel #217–219 published

- Owner approved writing and publishing the next 3 posts in current active Excel category `Cẩm nang > Hãng xe > Hãng xe điện` (#201–235); WordPress child category ID **21**.
- Created and pushed `posts/0217.md` Feliz–Klara design/ergonomics, `posts/0218.md` YADEA vs VinFast decision criteria and `posts/0219.md` removable/fixed batteries, distinguishing physical removability from battery-swap network eligibility. All three titles, IDs and taxonomy paths match `data/topics.json`; research refers to manufacturer documents.
- Safe QA GitHub Actions [run 38883581257](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38883581257) = **SUCCESS**, **55/55 authored QA PASS, 18/18 regression tests PASS**, 0 QA failures.
- Live publishing GitHub Actions [run 38867887824](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38867887824), latest job = **SUCCESS**. All three WordPress posts **VERIFIED**, `status=publish`, category `[21]`: Excel **#217 → WP 907**, **#218 → WP 908**, **#219 → WP 909**. No duplicate groups, no publishing errors, URLs and IDs recorded in `data/publication-state.json`.
- Excel publication progress **74/355**, first category `#146–200` **55/55** finished; current electric manufacturer category `#201–235` **19/35** correctly published; **16 remaining #220–235**. Authored source posts through #219 (55 files); **281 IDs #220–500** not yet authored.
- **NEXT WRITER BATCH** starts #220, #221, #222: use exact Excel metadata, write source files, QA, then run an authorized 3–5 POST batch. No automatic AI writer is running within GitHub Actions.
- Preserve `data/topics.json` checksum, site/post URL/slug/canonical, category boundary, Git it Write inactive and **WordPress Trash strictly untouched**. When #235 is finished report and stop before changing `data/publication-policy.json`.

---

# Verified production checkpoint — 2026-10-16 through Excel #216

- Authorized current batch: **#214–216**, written and pushed individually to `main` as `posts/0214.md`, `posts/0215.md`, `posts/0216.md`. Original Excel IDs, exact titles and full taxonomy path `Cẩm nang > Hãng xe > Hãng xe điện` preserved, researched against relevant official VinFast manufacturer product pages.
- QA workflow [38881064994](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38881064994) = SUCCESS: **52 authored posts, 52 QA PASS, 0 QA FAIL, 18/18 safety regression tests PASS**.
- Live WordPress publisher [38867887824](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38867887824) latest re-run = **SUCCESS**, all three created, publicly verified and committed to ledger as `VERIFIED`: **#214 → WP 904**, **#215 → WP 905**, **#216 → WP 906**, `status=publish`, category **21**, no duplicates or errors. URLs are recorded in `data/publication-state.json`.
- Excel progress **71/355 published**, first category #146–200 finished 55/55, current #201–235 published **16/35**, **19 missing #217–235**. Current authored total 52 files #165–216, **284 files #217–500 not yet authored**.
- NEXT WRITE: **#217–219**, exact titles/category from `data/topics.json`. Preserve 3–5 per owner-approved batch; QA before publishing. Do not proceed to category #236+ until full current group completes and is reported for review. No WordPress Trash interaction, no duplicate or legacy re-creation.
- GitHub workflows publish existing Markdown files only; do not claim an unsupervised AI writer is running.

---

# Production checkpoint — 2026-10-16 through #213

- Owner approved one new WordPress batch of 3 posts. No scheduled auto-publishing, no change in active category, no interaction with WordPress Trash.
- Newly authored and committed to `main`: `posts/0211.md` (VinFast short intra-city itineraries), `posts/0212.md` (YADEA onboarding for first-time riders), `posts/0213.md` (Dat Bike long-distance trip practicality). All exact titles and parent/child paths from `data/topics.json`.
- Manufacturer sources for each: VinFast product and battery policy, YADEA catalog and warranty, Dat Bike Quantum S technical information and specific 285 km reference conditions. No fictional user reviews, unverified inventory or assumed pricing.
- Latest code/content QA Actions run [38878718455](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38878718455): **SUCCESS**, 49/49 authored Markdown QA PASS, **18/18 regression tests PASS**.
- Latest owner-approved publication batch: [Excel Matrix WP Publisher](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38867887824) latest job **SUCCESS**; all **three new WordPress posts VERIFIED and published in leaf term #21**: Excel #211 → WP 901, #212 → WP 902, #213 → WP 903. Errors=0 and duplicate groups=0.
- Excel progress **68/355** published. Category `Cẩm nang > Hãng xe > Hãng xe điện`, Excel #201–235, now **13/35** correctly published, **22 IDs #214–235** require drafting/publishing. Whole matrix **287 files #214–500** have not been authored; published first category #146–200 remains 55/55.
- **NEXT WRITER** #214 and #215, then #216, using exact Excel titles and category; write in small batches, QA and push promptly. Do not bypass `data/publication-policy.json`, unpause #236+, or claim background AI article generation.
- Preserve existing site URL, post URLs, taxonomy, canonical, sitemap, and all WordPress Trash. No blind retries for uncertain prior WordPress writes.

---

# Writer and WordPress checkpoint — 2026-10-16 through Excel #210

- Owner approved continuation of one 3–5-post batch, staying within the current Excel category `Cẩm nang > Hãng xe > Hãng xe điện` (#201–235), matching WordPress child category ID 21, and leaving Trash untouched.
- Authored and pushed `posts/0208.md` (Pega), `posts/0209.md` (VinFast–YADEA), and `posts/0210.md` (VinFast–Dat Bike). Titles, IDs and full taxonomy paths exactly match `data/topics.json`. Articles use official manufacturer pages and avoid invented field testing, prices and unsupported details.
- Independent GitHub quality workflow [38877775274](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38877775274) returned **SUCCESS**: 46 authored, 46 QA PASS, 0 QA FAIL; **18/18 regression tests PASS**.
- Owner-approved WordPress publisher [38867887824](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38867887824) latest rerun returned **SUCCESS**. New WordPress posts **#208 → 897; #209 → 898; #210 → 899**, all `VERIFIED`, `status=publish`, `category_id=21`, public URLs recorded in `data/publication-state.json`.
- **Excel publication progress: 65/355** (#146–200 completed 55/55, #201–210 published 10/35). **Current category #201–235: 25 subjects #211–235 still need authoring/publishing**. Total **290 source topics #211–500 not authored**.
- **NEXT WRITER**: #211 and #212, then #213 according to exact immutable Excel. Follow `docs/PUBLISHER_OPERATIONS.md`, author 3–5 posts per active writing batch, commit promptly, validate QA and use manually approved GitHub publisher only when ready. Do not assert unattended AI content generation.
- The category gate remains fixed at #201–235. Do not publish #236+ or change `data/publication-policy.json` without reporting completion of #235 for owner review. If full WordPress category ancestry is absent, publish to draft and report; never guess Uncategorized. Never delete, restore, or modify Trash.

---

# Current production checkpoint — 2026-10-16 through Excel #207

- Owner explicitly authorized publishing 3–5 articles per batch directly to the unique matching WordPress parent/child taxonomy from `data/topics.json`. User will manage WordPress Trash themselves; **do not touch or purge the Trash**.
- Target: `https://blog.rentbikehanoi.com/`; repository `thuexemayhanoi/wp-aiwriter` on `main`.
- Category #146–200 `Cẩm nang > Hãng xe > Hãng xe máy`: completed 55/55 on WordPress; original posts #165–167 were corrected to matching child category 20 using authenticated WordPress REST, preserving URLs.
- Current publication scope in `scripts/engine.py`: `APPROVED_CATEGORY = 'Cẩm nang > Hãng xe > Hãng xe điện'`, `APPROVED_LAST_ID = 235`. WordPress category 21, parent term 19, grandparent term 15, was verified to match this exact ancestry.
- **Excel #201–207: seven published and fully VERIFIED** by GitHub Actions, WP IDs #890–896 inclusive, categories [21], `status=publish`; zero publishing errors, zero duplicate groups in the latest run.
- GitHub contains **43 source posts #165–207**, all QA PASS. Newly authored in this session: #204 VinFast Klara, #205 Yadea, #206 Dat Bike and #207 Selex Motors; each uses exact Excel title/category, source references and unique substantive editorial content.
- **No source files yet for #208–500 (293 topics).** Within current category #201–235, 28 source articles #208–235 remain unwritten, and the publisher does not generate text. An active writer must author them in batches, QA and push; then the live REST publisher can publish 3–5 per approved batch.
- GitHub Actions `Excel Matrix WP Publisher`: `workflow_dispatch` only; no cron or push publishing, no chained runs. Connector-triggered latest completed job for run 38867887824 returned SUCCESS: **43 authored, 43 QA PASS, 0 QA FAIL; 3 newly created and verified #205–207; 62 of 355 Excel titles published.** The preceding batch published #201–204 with matching category 21. Git it Write remains disabled.
- A transient GitHub-hosted WordPress network failure caused a single blocked run with zero WordPress writes; immediate retry succeeded. Authentication is verified working. Never invent publication when an attempt fails.
- Keep exact Excel `data/topics.json` bytes/checksum; do not change existing slugs, URLs, canonical, themes or older posts. If a category full ancestry is missing or ambiguous, create **draft** with reported reason rather than guessing or publishing in Uncategorized. Skip duplicates; do not delete older content automatically.
- NEXT CONTENT: #208 (`Pega có những dòng xe điện đô thị nào dễ gặp?`) and #209 onward: read exact next titles from `data/topics.json`; create one `posts/NNNN.md` per ID, pass `python scripts/engine.py --mode qa` and all safety tests. Do not cross #235 without reporting category completion.

---

## WordPress taxonomy correction verified — 2026-10-16

- Authenticated WordPress REST updated **only** post categories for #165 (WP 814), #166 (WP 815), #167 (WP 823) from parent term **19** to Excel-required leaf term **20** (`Cẩm nang > Hãng xe > Hãng xe máy`).
- Fresh REST readback verified all three are **published**, categories **[20]**, with their previous titles/slugs/permalinks preserved. No posts, slugs or content were deleted or regenerated.
- The publisher already resolves the *complete* Excel category ancestry for new articles; when the unique full path exists, it publishes directly to the matching WordPress child category. When not found/ambiguous, it uses **draft** instead of guessing.
- Category 1 (#146–200) is fully published and these three legacy taxonomy exceptions are now fixed. Owner's per-category review gate remains locked at #200 until a new category is approved.

# Publication milestone — 2026-10-16, Excel category 1 reviewed for owner

- WordPress target: https://blog.rentbikehanoi.com/ ; repository: `thuexemayhanoi/wp-aiwriter`.
- Category boundary is hard-coded in `scripts/engine.py`: `APPROVED_CATEGORY = Cẩm nang > Hãng xe > Hãng xe máy`, `APPROVED_LAST_ID = 200`. Do **not** remove/advance gate without owner review after each category.
- **First category #146–200: 55/55 Excel titles published and discoverable**, latest GitHub Actions job status SUCCESS. Publishing is manually triggered (no cron/push). #184–200 were verified in the latest continuation.
- All 39 existing source Markdown files #165–203 pass publisher QA; #201–203 are **not published**, because they belong to the next category. #204–500 (**297 subjects**) are not yet authored. GitHub Actions publishes files but **does not generate AI articles**; authors must write and QA the missing 297 files in later writer sessions.
- Legacy category mismatches to report to the owner for manual reclassification: WordPress posts **814 (#165)**, **815 (#166)** and **823 (#167)** are in parent category 19 `Cẩm nang > Hãng xe`, whereas Excel requires leaf category 20 `Cẩm nang > Hãng xe > Hãng xe máy`. Change category only, do not change slug/canonical.
- Original WP post 816 for #167 and URL `/0167-2/` are missing from WordPress. Currently existing unique live content is WP **823**, URL `/0167-3/`. Owner should review SEO redirect from missing original permalink to the retained version, without blindly changing URLs.
- Missing WP post #169 ID 834 was independently confirmed deleted and then safely restored with new WP **880** using the same article title, body, category 20 and original `/excel-169-.../` permalink. The one-time recovery exception and tests have been removed after successful verification. #173 WP **838** verified after normalizing WordPress ellipsis rendering.
- Proven duplicate copies of #165–167 were moved to WordPress Trash, not permanently deleted. Several copies later appeared again in Published; six more exact-body copies 821,824,827,825,826,829 were returned to Trash. No external cause has been confirmed. Before further bulk work, recheck live inventory for concurrent modifications and keep Git it Write disabled.
- **NEXT STEP**: notify owner that category #146–200 has finished and ask them to review taxonomy of 814,815,823. Only after approval should the category gate advance to `#201–235 Cẩm nang > Hãng xe > Hãng xe điện`. Write missing files starting #204, maintain original `data/topics.json` checksum and QA.
- Keep all existing URLs, titles, canonical, sitemap, categories, plugin state and old posts unchanged except explicitly reviewed corrections. Do not automatically move to new category while owner is reviewing.

---

# Writer continuation checkpoint — updated 2026-10-16 (through #203)

## Latest verified writer progress

- Repository: `thuexemayhanoi/wp-aiwriter`; target WordPress: `https://blog.rentbikehanoi.com/`.
- Latest authored Excel ID: **203**. Numbered files: **39**, exactly **#165–203**; the original Excel topic matrix `data/topics.json` remains unchanged.
- New in the latest assistant session: **four articles #200–203**, pushed to **main in two separate two-article commits** without forced updates:
  - **#200–201**: `b4ca16cb016858467175c60d9817f398fd7337df`
  - **#202–203**: `776ffc400d99fa5a7eeddbd80ad42cc64fdc6c17`
- Verified GitHub Actions run [38857643948](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38857643948): **39 authored, 39 QA PASS, 0 QA FAIL; 12/12 publisher safety tests PASS**. Action overall status is failure only at **WordPress authentication**.
- Publication remains **BLOCKED_AUTH**: `WP_USERNAME` and `WP_APPLICATION_PASSWORD` Actions Secrets are absent; **zero WordPress writes** in this session. Do not interpret pushed Markdown as published WordPress content. No secret was written to source files.
- **297 Excel rows #204–500 remain unwritten**. Next writer batch: **#204–205**, exact titles and full category paths must be read from `data/topics.json`.
- User authorized ongoing small writes: **2–5 articles per GitHub push**, with validation and expected-HEAD protection to avoid overwriting concurrent writers. Current publisher implementation independently caps live publishing attempts at two new posts per run.
- Earlier WordPress snapshot identified existing public #165–167 in Uncategorized; do not recreate them. The next potentially new publish pair is still #168–169, subject to authenticated duplicate and ledger checks after credentials are configured.
- Use this latest section as authoritative for counts and next IDs; the prior checkpoint is preserved below as historical context. No unattended AI-writing process is implied between active sessions.

---

## Archived checkpoint — verified through #199

## Current main and scope

- Repository: `thuexemayhanoi/wp-aiwriter`; WordPress target: `https://blog.rentbikehanoi.com/` only.
- Session started from verified main HEAD `e6461a390de45ea2baea59d48554974624d25c51`.
- Latest completed content ID: **199**.
- Latest content commit: **c0a09a6c24b23f310b11f629f4428f4a9d7016cd**.
- Numbered authored files: **35**, exactly #165–199, with exact `matrix_id`, title and category_path from Excel and `ready: true`.
- Created this session: **20 articles #180–199**, in **10 consecutive two-article pushes to main**. #197 received an additional editorial clarification in the last pair's commit.
- Earlier completed files #165–179 were preserved. No publisher, workflow, tests, requirements or topic source code was changed in this session.
- `data/topics.json` remains the original 355 rows #146–500. SHA-256: `01192fc9ae78d7ddced2b9c7afa85b0794081269c11b028fdcf56e18aba4ca60`.
- **301 rows #200–500 remain unauthored.** The target of #500 is not complete.
- No Cloud Browser, login prompts, WPVibe/WP Agent writes, external text generator, model API key or open-source AI was used. The active assistant authored the prose.
- Terminal read/fetch, installation, tests and QA worked. HTTPS terminal push had no credential provider; content was committed and main advanced using the authenticated GitHub connector, with expected-head checks and no forced updates. Local worktree was synchronized to the resulting remote commits.
- Writer execution stops at the current active-session output/context limit. Actions does not author text, and no background writer is claimed after the session ends.

## Verification results

- Final local mechanical QA: **35 PASS, 0 FAIL**.
- Final local publisher regression suite: **12 PASS**.
- GitHub Actions run [38856323063](https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38856323063), for content commit `c0a09a6`, independently passed **12 tests** and **35-article QA**; live sync failed at missing credentials.
- New article lengths use the engine's Unicode word-token counter: **1,284–1,587**. This is not a claim about linguistic segmentation of Vietnamese words.
- **31 internal-link occurrences** in #180–199 were checked against published WordPress REST inventory. All **17 unique public permalinks returned HTTP 200** in the final GET checks; 0 failures.
- Exact metadata, required sections, placeholders, repeated paragraphs, near-duplicate text checks and source checksum passed the existing engine.
- Mechanical near-duplicate PASS does not prove distinct search intent. Adjacent Excel rows were compared editorially; closely related titles and reserved scopes are recorded below.

## Publication status — BLOCKED_AUTH

**BLOCKED_AUTH** remains the exact checkpoint status. Latest live Actions log:

`BLOCKED: missing WP_USERNAME / WP_APPLICATION_PASSWORD GitHub Secrets; zero WordPress writes`

- Required encrypted Actions Secrets: `WP_USERNAME` and `WP_APPLICATION_PASSWORD`.
- Do not request passwords in chat or put them in source, logs or checkpoint files.
- Missing authentication must not stop content writing and pushing.
- No workflow rebuild or authentication workaround was attempted.
- New WordPress publish writes by this session: **0**.
- New WordPress draft writes by this session: **0**.
- Authenticated inventory, total drafts, actual create/readback and production remote-ledger writes remain **UNVERIFIED**.
- `data/publication-state.json` is currently absent on main. No POST_INTENT or VERIFY_PENDING checkpoint was cleared or changed.

## Public WordPress inventory and taxonomy discrepancy

Public REST snapshot at **2026-10-16 05:30:09 UTC / 12:30:09 Asia/Ho_Chi_Minh**:

- Published posts across the entire site: **168**. This is not the number completed from the Excel plan.
- Exact-title public matches to Excel: **22**, #146–167.
- #146–164: **19** public exact-title matches assigned category **20**, resolving to `Cẩm nang > Hãng xe > Hãng xe máy`.
- #165–167: **3 public existing posts with incorrect Excel taxonomy**. They are in category **1 — Uncategorized**, not the expected leaf 20.

| Matrix ID | Existing WP ID | Existing permalink | Public categories |
| --- | --- | --- | --- |
| 165 | 814 | https://blog.rentbikehanoi.com/0165-2/ | [1] |
| 166 | 815 | https://blog.rentbikehanoi.com/0166-2/ | [1] |
| 167 | 816 | https://blog.rentbikehanoi.com/0167-2/ | [1] |

These pre-existing public posts were discovered through read-only inventory; they are **not** verified publications produced by this workflow. No content-hash equivalence to the repository files is claimed. Preserve their IDs, URLs, slugs and current content. Do not repost them to work around the category issue. Taxonomy reconciliation remains outstanding and cannot be performed without authenticated access under the current create-only publisher contract.

#168–199 have no exact-title public matches in that snapshot. Public title matching cannot reveal private drafts; authenticated duplicate checks are still required before any new POST.

## Writer queue versus publisher queue

### Next writer pair

After re-reading latest main and complete files, choose the two smallest incomplete IDs:

1. **200** — Chọn hãng xe theo tiêu chí dễ sử dụng, dễ sửa hay kiểu dáng: nên ưu tiên gì?
   - Exact category_path: `Cẩm nang > Hãng xe > Hãng xe máy`.
2. **201** — VinFast có những dòng xe máy điện nào phù hợp đi lại trong đô thị?
   - Exact category_path: `Cẩm nang > Hãng xe > Hãng xe điện`.

Research fresh official VinFast sources for #201; do not infer the current product range, charging rules, prices, battery plan or vehicle classification from old articles.

### Publisher resume

The publisher still scans authored files from #165, independently of the writer. When authentication is configured, run the existing workflow with `live=true`, `batch_size=2` and reconcile live authenticated inventory first.

Given the public snapshot, #165–167 already exist and must be skipped. **The next potential NEW publication pair is #168–169**, provided authenticated inventory does not reveal existing drafts or unresolved ledger entries. Do not hard-code the old #165–166 creation expectation. Do not mark the existing three miscategorized posts as category-compliant successes.

Full unambiguous category ancestry permits PUBLISH; missing or conflicting ancestry requires DRAFT with a reason. Maximum two new attempts per run. A failure in one article must not block unrelated eligible articles. Never clear uncertain write intents for a blind retry.

## New content pushes

| IDs | Main content commit | QA word tokens |
| --- | --- | --- |
| 180–181 | 4685aa02fb1514a54e7add1b120bcb20a7dfc53c | 1,484 / 1,443 |
| 182–183 | c6894c0b6fa55b601bd62b7344babecfb52a27e5 | 1,347 / 1,502 |
| 184–185 | c39c6044ae187adf921cc864606183f4a25eb0a9 | 1,347 / 1,439 |
| 186–187 | 77760881201efe8de7da7b3ebb03953183b86a8a | 1,428 / 1,424 |
| 188–189 | 59bb994672f0c2150eac9dae2905c0ed4774468a | 1,384 / 1,395 |
| 190–191 | 3251daf8a655fd784290d1d3e4e9e60e285681ac | 1,377 / 1,386 |
| 192–193 | c2ff5d496bb9671f2f7b045112c0a2b8a3c409a5 | 1,353 / 1,396 |
| 194–195 | 8a1a375d49f108b4b927dc75cb7740e58704b19a | 1,284 / 1,321 |
| 196–197 | 2d2c55ba2255a606ac1d1dd117fb0cafa5c2f155 | 1,314 / 1,378 at first push |
| 198–199, plus #197 clarification | c0a09a6c24b23f310b11f629f4428f4a9d7016cd | 1,310 / 1,336; #197 final 1,587 |

Earlier session history: #172–173 `df0816e6e5ddb540d2cb60763ea744fd740bfe36`; #174–175 `7fea068abbe1796a37b8b4b7c727a0ad712f98f5`; #176–177 `444d542a66a471482347bcceb72bb3a8fb98fba3`; #178–179 `0cceecf8c8d8f1817fa8b37d606d9f1f2fdd68e6`. Publisher repair remains `603256fde112073198b8755ecc96ad8b138ef88a`.

## Editorial and source continuity

- #180 compares a whole working day with Grande/Lead; reserve #336 for the narrower luggage decision. #181 explains concrete model configurations; future #337 needs a distinct applied decision scope, not a copy of the comparison table.
- #182 covers design proportions, while the existing NVX article and future #343 focus on riding position. #183 compares Liberty/SH Mode brand styling and practical layout without asserting a universal winner.
- #184 is Wave/Sirius ergonomics and controls; reserve #287 for the novice learning decision. #185 is a first walk-around of Blade versus Sirius, not a history or sales ranking.
- #186 compares the components contributing to comfort, explicitly scoped to Future 125 FI and Jupiter Finn. Future #289 must not repeat the same model comparison; focus on applied fit selection if sufficient distinct value exists.
- #187–188 discuss layout patterns within each scooter brand; #189 explains comparison categories for semi-automatic motorcycles. They are not replacements for #168–169 model-count articles or the earlier brand riding-feel article.
- #190–191 use fresh SYM/Kymco official product sources. Legal points were checked against the Ministry of Public Security response published on Chinhphu.vn on 22/01/2026. Do not equate a 50cc sticker with legal classification or automatic rider eligibility.
- #192 separates Piaggio Group, Piaggio brand and Vespa brand. #193 is a selected Honda storage overview, not a claim to rank the entire range. #194 scopes manufacturer weight labels carefully; handling suitability is not determined by mass alone.
- #195–198 are practical identification procedures linked to the existing model-overview pages #154/#155/#150/#149. There is inherent topical overlap in the unchanged Excel titles. Keep these procedures focused on evidence, exact configurations and uncertainty; do not duplicate historical overviews. #197 was sharpened with a six-configuration lookup table after checking the existing Sirius article. Search-intent overlap remains an editorial monitoring concern despite mechanical PASS.
- #199 distinguishes product recognition, brand origin, manufacturing origin and current versus historic catalogues. No Hanoi prevalence survey or unsupported most-popular ranking is invented.
- New sources were read from Honda, Yamaha, SYM, Kymco, Piaggio Group, Piaggio, Vespa, Suzuki and the government policy portal. Each article links its own sources and scopes dated specifications. Conflicting or incomplete manufacturer fields were not silently filled with guesses.
- Internal links point only to URLs observed in public published REST inventory; no future article URL or draft link was invented. Existing #165–167 links use their observed actual permalinks, preserving URLs despite their taxonomy discrepancy.
- No rental prices, deposit waivers, availability promises, fabricated reviews, firsthand riding tests or fake statistics were added.

## Resume commands and safeguards

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/engine.py --mode qa
```

Always re-read main, AGENTS.md, the source topics, authored files, current Actions receipts and publication ledger before choosing the next pair. Keep the original Excel bytes and metadata unchanged. Commit and push each passing pair promptly; do not wait for repeated batch approval. No background writing is implied by the scheduled publisher.
