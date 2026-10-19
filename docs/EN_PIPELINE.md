# English pipeline (EN) — research, write, QA, publish, verify

**Target:** the English side of https://blog.rentbikehanoi.com/ (`/en/`), served by the Nguyen Ha Editorial theme and
VI-EN Core 0.5.1 (repository `thuexemayhanoi/wordpress-theme`). **Business:** Nguyen Ha Motorbike Rental only; never the
Nguyen Tu data (`en/business.json` lists the forbidden fragments). The Vietnamese pipeline (`posts/`, `data/topics.json`,
`scripts/engine.py`, its workflows and ledger) is untouched and keeps working as before.

## Files

| File | Role |
|---|---|
| `en/topics.json` | The topic matrix: `id`, `title`, `slug`, `category_id` (an English leaf category 49–56), `intent`, `hub`, `keywords`. The single source of IDs, titles, slugs and categories; one search intent per row; no duplicates. |
| `en/business.json` | Nguyen Ha facts for the QA: phone, address, hours, allowed VND amounts (the price table), forbidden fragments of the other business, English page URLs. |
| `en/publication-policy.json` | `enabled` (false = preview only), `mode` (`pilot` publishes only `pilot_ids`; `batch` publishes every QA-ready article), `batch_size`, `max_batches_per_run`, `require_live_routes`, `legal_categories`, `min_score`. |
| `en/posts/NNNN.md` | One article per topic ID, front matter `en_id`, `title`, `slug`, `category_id`, `description`, `ready`. Original English prose with `## ` sections, a `## FAQ` and a `## Sources` section. |
| `scripts/en_engine.py` | `--mode qa` (gates and score) and `--mode sync` (publisher; `--live --persist-state` on GitHub Actions). |
| `scripts/en_ops.py` | Operates VI-EN Core through its REST API: status, enable/disable/undo, register categories, link page pairs, publish pages, public verify, and `rollout` (one idempotent go-live pass: status → routes on if not live → missing categories → missing page pairs, both slugs checked first → public verify; `NOT_INSTALLED` while the site runs a plugin older than 0.5.1). |
| `.github/workflows/en-autopilot.yml` | Every two hours: one `rollout --live --confirm` pass. Quiet while 0.5.1 is not installed; once a pass is `VERIFIED` it sets `enabled: true` in the policy, pushes, and starts the EN Publisher live for the pilot. Failures go to the issue "EN autopilot alert" (one comment per failed pass, pause after three until the issue is closed). |
| `tests/test_en_ops.py` | Rollout safety against a fake VI-EN Core: order of writes, idempotence, slug checks, the English site name (plugin 0.5.2+), stop at the first failure, no writes without `--live`. |
| `en/pages/*.md` | The seven English pages (WordPress 1758 `/en/`, 1759 about, 1760 prices, 1761 contact, 1762 rental-guide, 1763 faq, 1764 motorbikes): front matter `page_id`, `slug`, `parent`, `title`, `description` (the excerpt and, with plugin 0.5.2, the meta description), `ready`; Markdown body written from the Vietnamese pages and `en/business.json`. |
| `scripts/en_pages.py` | `--mode qa` (registry match, title/description lengths, word minimum per page, English only, business facts and allowed amounts, `/en/`-only links, 15+ FAQ questions, copied paragraphs between pages) and `--mode sync [--live]` (update-only publisher: reads each live page, refuses anything that is not the expected English page, skips unchanged content by marker, keeps the previous title/excerpt/content in the report, updates title + excerpt + content, reads back, checks the public page). Never creates, deletes or moves a page, never touches a Vietnamese page. |
| `.github/workflows/en-pages.yml` | Push to `main` touching `en/pages/**` → tests + QA → live update of the changed pages; manual runs preview unless `live`. Report artifact `en-pages-<run>` holds the previous content of every updated page (WordPress keeps a revision too). |
| `tests/test_en_pages.py` | The page gates and the update-only publisher against a fake WordPress. |
| `scripts/wp_probe.py` | Read-only probe of the live site (plugins, theme, pages, categories, menus, public answers, page text). |
| `data/en-publication-state.json` | Write-ahead ledger of English publications (POST_INTENT → DRAFT_CREATED → REGISTERED → VERIFY_PENDING → VERIFIED, or REGISTER_FAILED). Never cleared by hand to force a retry. |
| `tests/test_en_engine.py` | QA gates, duplicate detection and publisher safety (no network). |

## Pipeline

Topic Research → Intent & Keyword Mapping (`en/topics.json`) → Source Research → Outline → English Writer (`en/posts/NNNN.md`)
→ SEO QA + Fact QA + Duplicate QA (`en_engine.py --mode qa`) → Category Validation (VI-EN Core status) → Publisher →
Live Verification → Progress (ledger, reports, checkpoint).

### QA gates (hard; any failure keeps the article in GitHub)

- `en_id` = file name = a row of `en/topics.json`; title, slug and category match that row exactly; `ready: true`.
- 1,000–5,000 English words; at least three `## ` sections; no H1 in the body; no placeholders; no scripts.
- English only: Vietnamese letters under 2 % of letters and fewer than five Vietnamese stopwords (place names are fine).
- Business facts: no fragment of the other business (phone 0942…, 112 Nguyen Van Cu, Nguyen Tu); any phone number must be
  the Nguyen Ha number; any VND amount must be in `allowed_amounts_vnd` (the price table) unless it is a fine or penalty;
  no USD prices.
- Links: internal links only below `/en/`; https only; images need alt text.
- Legal topics (categories 55 and 56, or six or more legal words): a `## Sources` section with at least one official
  domain (gov.vn, thuvienphapluat.vn, vbpl.vn, chinhphu.vn, csgt.vn, luatvietnam.vn, honda.com.vn, …) and an effective date
  ("effective 1 January 2025", "as of October 2026").
- Duplicates: 7-word shingle overlap over 70 % with another article, or title+outline cosine over 0.60 (same search intent).

### Score (soft; minimum 85/100)

Description 110–175 characters (−10 missing, −5 length), 1,200–3,500 words, four or more sections, a FAQ (−8), sources
(−8 unless legal), two or more internal `/en/` links (−8), an external reference (−5), title 35–65 characters (−4), slug
≤ 60 (−2), an intro of 60+ words (−5), no paragraph over 180 words (−3 each).

### Publisher (GitHub Actions `EN Publisher (VI-EN Core)`)

1. Runs after a successful push-triggered `EN Writer QA` on `main`, manually, or started live by the `EN autopilot` once
   its rollout pass verified; writes only with `--live` **and** `enabled: true` in the policy; one action per run,
   `max_batches_per_run` batches of `batch_size`.
2. Gate: `GET /wp-json/nh-vien/v1/status` must say `live: true` and list every needed English category (46–56) as
   registered; otherwise BLOCKED with zero writes.
3. For each eligible article (no duplicate title/slug/marker in WordPress, no unresolved ledger phase): POST_INTENT →
   create as **draft** (`categories: [leaf]`, excerpt = description, `meta.nh_summary`, `meta.nh_content_updated`, marker
   comment `wp-aiwriter-en:en_id=…;sha256=…`) → `POST /nh-vien/v1/posts {id}` (register as English) → publish →
   verify: readback (status, slug, title, categories, marker), VI-EN status lists the post as public, public
   `/en/{slug}/` answers 200 with `X-NH-VIEN-Lang: en`, `lang="en-US"`, self canonical and the title, and `/{slug}/`
   redirects to `/en/{slug}/` → VERIFIED. A failed registration leaves the draft and records REGISTER_FAILED; a failed
   verification records the phase and never retries blindly.
4. Receipts: `reports/en/latest.json`, `reports/en/summary.md` (job summary), the ledger committed to `main`.

### Rollout order

1. Install VI-EN Core 0.5.1 on the site (Plugins → Add New → Upload Plugin → Replace current with uploaded; the zip comes
   from the `release-<sha>` artifact of a green Theme QA run on `main`, or from `tools/package.sh` at that commit). The
   one manual step.
2. Automatic from here: the `EN autopilot` workflow notices 0.5.1 or later (`nh-vien/v1/status` answers) within two hours
   and runs one `rollout` pass: routes on (the plugin's preflight, smoke test and rollback apply), categories 46–56
   registered, page pairs 14→1759, 19→1760, 25→1761 linked after a slug check, the English site name set from
   `en/business.json` (`name_en`, plugin 0.5.2+), English pages verified publicly. The same pass can be started by
   hand: `EN rollout` → action `rollout`, live, confirm (dry run without `live`), or `EN autopilot` → `live`.
3. Automatic too: a `VERIFIED` pass sets `enabled: true` in `en/publication-policy.json` (pilot mode, IDs 1–3), pushes it
   and starts `EN Publisher` live: the three pilot articles are created as drafts, registered as English, published
   and verified. Then check the live URLs, `/en/category/…`, the menus and `/sitemap_index.xml` with the probe.
4. Switch `mode` to `batch` with `batch_size` 3 → 10 → 20 as each batch verifies (a human decision, by commit); write
   more `en/posts/NNNN.md` from `en/topics.json`; add topics to the matrix as research finds new intents (never
   duplicate an intent).

## The English pages

The seven pages are content, not posts: they live in `en/pages/*.md` and reach WordPress through `scripts/en_pages.py`,
independently of the routes switch (they are published already and answer at their `/en/…` addresses). Facts come
from the Vietnamese pages `/gioi-thieu/`, `/bang-gia/`, `/lien-he/` (read with the probe, `--text`) and from
`en/business.json`; a change of price or policy is made in `en/business.json` and in the page files together, then
pushed. The publisher updates only the pages whose marker (`wp-aiwriter-en-page:id=…;sha256=…`) changed. To look a
Vietnamese page up by slug (for a future page pair), run the probe with `slugs`.

## Writing rules

- Research first: official sources for law, fines, licences (Law 36/2024/QH15, Decree 168/2024/ND-CP, Circular
  29/2015/TT-BGTVT and their amendments), manufacturer pages for vehicles, the Nguyen Ha pages for prices and terms.
- Natural English for international visitors; no machine translation of Vietnamese posts; no fabricated reviews,
  experiences, statistics or prices; VND only; cite effective dates for legal facts.
- Internal links: hub → category → cluster, only to `/en/` pages and verified English posts; never to Vietnamese URLs.
- Keep `en/topics.json` as the source of truth; a new topic is added there before its article is written.
- After a session: update `docs/EN_WRITER_CHECKPOINT.md` with the commit, QA result, published IDs and the next IDs.
