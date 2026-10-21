# Nguyen Ha English content architecture — 20 October 2026

This rollout is **already live on** `https://blog.rentbikehanoi.com/en/`; this document records the independent English information architecture before the campaign reaches 500 articles.

## Production status (verified 2026-10-20)

- 19 published English pages: 7 original EN pages (IDs 1758–1764) and 12 new service/area/legal/guide pages (IDs 1827–1838).
- 16 VI/EN page pairs using VI/EN Core, with real corresponding purposes. Pair identifiers and expected slugs are in `en/publication-policy.json`.
- 21 registered EN categories: original IDs 46–56 (11) and new IDs 60–69 (10). The WordPress default `Uncategorized` is not an English content category.
- English main navigation deliberately has 8 links, parallel to VI: Home, About, Prices, Services, Areas, Guides, FAQ, Contact. All subpages and categories are linked from appropriate parents, not all exposed as top-level links.
- **9 English posts published and verified** when the architecture was audited. The 500 entries of `en/topics.json` represent editorial intents, **not** 500 published articles. Existing live posts and authored manuscripts 1–9 keep their original categories, titles and slugs.

## English term IDs, parent IDs and editorial purpose

| ID | English category | Parent ID | Use |
|---|---|---|---|
| 46 | Motorbike Rental in Hanoi | 0 | Main rental hub |
| 47 | Hanoi Travel & Routes | 0 | Route hub |
| 48 | Riding Advice & Safety | 0 | Safety hub |
| 49–52 | Manual / Automatic / 50cc / Electric bikes | 46 | Vehicle comparisons |
| 53–54 | Neighbourhoods / Suggested Routes | 47 | Locality and travel |
| 55–56 | Rental Tips / Road Rules | 48 | Rental operations and safety |
| 60 | Hoan Kiem Area | 53 | Central Hanoi |
| 61 | Old Quarter Riding | 60 | Historic core and parking |
| 62 | Long Bien Area | 53 | Shop-area travel |
| 63 | Ba Dinh Area | 53 | Landmark access |
| 64 | Gia Lam Area | 53 | Eastern Hanoi |
| 65 | Honda & Yamaha Comparisons | 46 | Genuine model comparisons |
| 66 | Motorbike Handover & Maintenance | 46 | Vehicle checks |
| 67 | Navigation Apps & Maps | 47 | Maps and offline planning |
| 68 | Hanoi Traffic & Parking | 48 | Legal parking and city traffic |
| 69 | Weekly & Monthly Rentals | 46 | Longer rental agreements |

All new categories are already registered with `NH_VIEN_Rest /categories`. **Do not publish empty category hubs just to reach numeric parity**: English term archives without eligible published English articles can return 404 until populated. Keep the menu linked to the informative hub *pages* while the 500 articles are being developed. Preserve the original Vietnamese taxonomy unchanged.

## Existing English page slots

| English WordPress ID | EN slug | VI page ID |
|---|---|---|
| 1758 | /en/ | VI homepage |
| 1759 | about | 14 |
| 1760 | prices | 19 |
| 1761 | contact | 25 |
| 1762 | rental-guide | independent |
| 1763 | faq | 24 |
| 1764 | motorbikes | independent |
| 1827 | services | 15 |
| 1828 | 50cc-bikes | 17 |
| 1829 | electric-scooters | 18 |
| 1830 | guides | 23 |
| 1831 | areas | 20 |
| 1832 | hoan-kiem | 21 |
| 1833 | old-quarter | 22 |
| 1834 | long-bien | 26 |
| 1835 | ba-dinh | 27 |
| 1836 | gia-lam | 28 |
| 1837 | privacy | 3 |
| 1838 | terms | 29 |

The new pages have independent English HTML content and Yoast metadata already published on WordPress. In `scripts/en_pages.py`, the page IDs are now registered as **update-only** targets, but new `en/pages/{slug}.md` source files have **not** been imported yet. Without a source file, that script skips the page. It never creates or modifies these 12 newly published pages on its own. Do not invent markdown to "fill" this gap or overwrite live editor-authored content without backed-up QA. Import from live WordPress with an approved, reversible workflow first.

## English editorial pipeline

- `en/topics.json` maintains 500 unique topics with stable IDs 1–500, unique slugs, and **only registered English category IDs**. Later topics are candidates until a separately researched English manuscript exists.
- `en/publication-policy.json` controls English-only taxonomy, page pairs, batch size, verification and QA threshold. QA must be ≥76, and legal claims need official dated references. First 9 manuscripts retain their original category IDs.
- English posts are **original articles with their own search intent**, not translated Vietnamese articles. No automatic VI/EN article hreflang pairs unless a genuine authored content counterpart is explicitly registered.
- `EN Writer QA` → `EN Publisher`: draft → register with VI/EN Core → publish → readback/SEO check; ledger ensures idempotency. Only QA-passing work may publish.
- **Never** rewrite existing Vietnamese posts/slugs/canonicals or the existing Yoast sitemap. Never redirect broken English archives to the homepage. Unpopulated categories wait until original articles pass QA.
- English menu stays at 8 primary links; use nested navigation and category hubs as content grows, and test mobile / tablet / desktop after any menu change. Purge LiteSpeed Cache as appropriate.

## What remains

Research and write the remaining 491 topics, then publish in bounded verified batches; monitor page QA, category hub growth, page link health and desktop menu wrapping. Page creation and taxonomy registration **do not equal** article publication.
