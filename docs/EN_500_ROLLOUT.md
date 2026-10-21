# EN 500 — Editorial rollout and QA contract (20 Oct 2026)

> **CURRENT POLICY UPDATE (21 Oct 2026):** The disabled-policy and 9-post figures below are **historical launch snapshots**, not current state. The pilot is finished. The owner authorised `enabled=true, mode=batch` without `batch_size` or `max_batches_per_run`. The EN Publisher continuously processes eligible manuscripts (resuming on GitHub runner time cutoff), without approval per group of 3. QA >=85, 1,600–5,000 words for new/revised posts, WordPress gates and immutable EN ledger remain mandatory.


**WordPress:** https://blog.rentbikehanoi.com/  
**Repository:** `thuexemayhanoi/wp-aiwriter`  
**Theme/SEO routing:** `thuexemayhanoi/wordpress-theme`, VI/EN Core 0.5.2, Yoast SEO.

## Roles: do not create a second authoring/publishing stack

- `en/topics.json`: exactly 500 **English editorial topic candidates**, IDs 1–500. IDs 1–48 and their metadata are retained, with 452 additional planned subjects (49–500).
- `en/posts/NNNN.md`: original, research-backed English prose **only after a writer produces it**. GitHub Actions does not write article copy, cannot run Claude or ChatGPT by itself and needs no AI API key.
- `.github/workflows/en-writer-qa.yml`: tests, full manuscript QA, duplicate guards, dry-run queue.
- `.github/workflows/en-publisher.yml`: existing create-only publisher, QA-success gated. Draft → register language with VI/EN Core → publish → verify `/en/{slug}/`, canonical, category and language marker.
- `.github/workflows/en-autopilot.yml`: one-time VI/EN rollout and pilot activation after authenticated live checks. It must **not** blindly switch the policy to batch mode.
- `/wordpress-theme`: presentation, menus, taxonomy URLs and Yoast integration. Do **not** write 500 articles in the theme.

## Current baseline — do not confuse planning with publishing

At the time of this plan:
- 500 topics queued; 9 English manuscripts (#1–9) already exist in GitHub and previously passed deterministic QA (96–100).
- Zero English article URLs were present in the live Yoast post sitemap when inspected on 20 Oct 2026.
- VI/EN Core 0.5.2 was confirmed active on WordPress with 11 registered English categories and zero public English posts.
- The existing EN publication policy is deliberately `enabled=false`, `mode=pilot`, `pilot_ids=[1,2,3]`.
- Prior EN autopilot runs returned `NOT_INSTALLED` before VI/EN Core was installed; a green workflow outcome did **not** mean publishing occurred.
- WordPress credentials used by the existing VI GitHub publisher must be validated again in the EN rollout. Never display, email, hardcode or commit them.

## Publishing sequence

1. **Preflight**: Back up WordPress; inspect the live VI/EN REST status, homepage `/` and `/en/`, category registrations, reserved URL collisions, published English pages and true page pairs; ensure GitHub publisher has valid existing WordPress credentials. Do not replace Vietnamese URLs, metadata or taxonomy.
2. **Pilot**: After all rollout checks pass, let the existing autopilot turn on the policy and publish only IDs 1–3. For legal topics (notably #1), verify law citations against current official sources **before publishing**, regardless of mechanical QA. Independently verify all three public pages, self-canonicals, `lang=en-US`, no `noindex`, correct EN category and the Yoast sitemap.
3. **Continuous publishing after successful pilot (current)**: `mode=batch` is enabled and article-count/batch-count limits have been removed. After push QA success, the serialized EN Publisher handles all eligible manuscripts, enforces every existing gate, checkpoints before WordPress writes and safely dispatches continuation near the GitHub runner deadline. The old 3 → 10 → 20 staging recommendation was superseded by owner approval on 2026-10-21.
4. **Writers**: Research and write small original English batches under `en/posts/NNNN.md`, with exact topic ID/title/slug/category, `ready: true`, appropriate independent English title and meta description, current sources for legal/safety claims, no unsupported numbers and non-duplicated search intent. Prefer source-backed original explanations and internal links to already-live `/en/` pages. A candidate in `en/topics.json` is **not** QA-approved content and should be researched and pruned/merged if it collides with another intent before drafting.
5. **Create-only release**: Successful EN Writer QA triggers the current EN Publisher. No blind retry after an unknown POST; preserve `POST_INTENT`, `VERIFY_PENDING` and any existing WordPress post ID. Stop on authentication, sitemap, canonical, collision or taxonomy errors and repair the exact cause. Count only WordPress-verified `publish` articles toward 500.
6. **Completion**: Stop English publication at 500 verified unique EN posts (not 500 planned topics). Report `planned`, `authored`, `QA PASS`, `VERIFIED`, `duplicates`, `blocked`, `remaining`. Continue protecting existing Vietnamese articles, all original slugs and the Yoast `sitemap_index.xml`.

## SEO invariants

- VI `/...` and EN `/en/...` each have self-canonical; only genuinely paired articles get reciprocal hreflang.
- Never set canonical of an English original to an unrelated Vietnamese page or fabricate a pair.
- Yoast owns the sitemap and SEO meta. English posts enter it **when published**, not when a topic row is planned.
- Empty English category archives may return 404 and are intentionally hidden from navigation until published English articles exist; keep the underlying 11 category records and hierarchy.
- Do not invent district storefronts, publish doorway location pages, alter the existing VI category hierarchy, noindex, or downgrade editorial QA to increase throughput.
- Avoid bulk Yoast/sitewide title, robots, URL, slug or structured data changes.
