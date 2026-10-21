# Claude / ChatGPT / AI writer — read before making any change

> **EN FAST HANDOFF (21 Oct 2026):** [`docs/EN_FAST_WRITER.md`](docs/EN_FAST_WRITER.md) is the current short contract. Run `python scripts/en_writer_brief.py --limit 10 --format compact`; use the **unchanged canonical** `en/topics.json` title/slug/category directly. Excel headline proposals are OPTIONAL; no repeated original-title review, no `--apply-approved` unless deliberately changing a title. QA >=76 and 1,600–5,000 English words; no EN publishing cap. Keep VI untouched and protect VERIFIED ledgers and WordPress URLs.



**Site:** https://blog.rentbikehanoi.com (Nguyễn Hà only). **Do not confuse with Nguyễn Tú, /wp-writer or /global.**

**FAST EN COMMAND:** `python scripts/en_writer_brief.py --limit 10 --format compact` (`--format json` for detailed research context). This queues original canonical titles directly with no proposed-title review; EN Publisher performs final live WordPress checks. The one-page EN fast guide and QA safeguards are mandatory.

## Detailed startup reading — required for VI, taxonomy/structure changes and EN exceptions; ordinary EN uses Fast Writer

1. [`AGENTS.md`](AGENTS.md) — existing writer/publisher contract and production safety.
2. [`docs/MENU_TAXONOMY_MAP_VI_EN.md`](docs/MENU_TAXONOMY_MAP_VI_EN.md) — full, human-readable **VI/EN header/footer menus, all category parent/child trees, every Page ID, and writing rules**.
3. [`data/navigation-map.json`](data/navigation-map.json) — the corresponding **read-only machine-readable WordPress snapshot**. This file is reference data, not a request to change WordPress.
4. The **chosen language's** exact topic matrix and publisher policy:
   - VI: `data/topics.json` + `data/publication-policy.json`
   - EN: `en/topics.json` + `en/publication-policy.json`
5. Current publication ledger (`data/publication-state.json` for VI; `data/en-publication-state.json` for EN), writer checkpoints and GitHub Actions status.

## Before writing

- Identify the precise topic **ID**, search intent, language, destination **Term ID** or VI full `category_path` (including all parent terms) and relevant live hub links.
- **Never mistake menu item IDs for Term IDs or Page IDs.** Don't infer taxonomy from visible menu labels, and don't equate English category archives with English hub *pages*.
- The snapshot was read from WordPress on **2026-10-20**. If live taxonomy, menu, routes or page ownership differs, **BLOCK and report the mismatch**. Update map only after inspecting live WordPress and reviewing an explicit PR. Do **not** modify production to make it match the snapshot.
- EN: author original English prose (not an auto-translation), **1,600–5,000 words** for new/revised content; QA **≥76**, unique intent and slug, valid sources, correct EN `category_id`, publisher **automatically drains every QA-ready article with no count limit**. Previously VERIFIED posts are immutable unless separately approved.
- VI: maintain Excel Matrix's exact original title and `category_path`; do not rewrite original `data/topics.json`.
- Protect existing slugs, canonical, menu URLs, Yoast sitemap, plugin VI/EN routes, parent taxonomy and published content. Never create hundreds of location terms or doorway pages merely to mirror menu labels.
- Publication is **not finished** until WordPress readback + ledger `VERIFIED` confirm correct URL, language, category and content. Never duplicate an uncertain POST or erase the ledger to retry.

## Fast handoff to another AI session

> EN standard manuscript: read docs/EN_FAST_WRITER.md, run --limit 10 --format compact and write current canonical titles. For VI work or taxonomy conflicts, use AGENTS.md and full menu map; never invent category IDs or change existing URLs. Publisher checks WordPress live and records VERIFIED before counting any post.
