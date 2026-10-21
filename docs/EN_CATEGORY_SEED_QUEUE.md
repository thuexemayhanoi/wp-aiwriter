# English category seeding — historical 2026-10-20 plan and current policy

> **CURRENT EN RULE (owner-approved 2026-10-21):** The table is a historical category-seeding proposal, **not** an active per-batch approval queue. No three-post publishing limit and no next-batch approval remain. English articles still require QA >=85, minimum 1,600 words for new/revised work, distinct intent, genuine sources, live registered taxonomy, duplicate preflight, WordPress verification and durable ledger checkpoints. This authorisation does **not** permit changing taxonomy, previous published articles, or URLs.


Last live audit: 20 October 2026. WordPress VI/EN Core reported **21 English content categories and 9 published English articles**, all in the existing original EN groups. The 10 newly registered subcategories (IDs 60–69) had no directly assigned English articles. Parent category IDs 46, 47 and 48 had zero direct assignments, although their category hierarchies already contained published child articles.

**Rules (new authoring standard effective 20 October 2026):** No placeholder articles, no Vietnamese translations, no invented branches, delivery options, parking rates or licence terms. Write one original **1,600–5,000-word** article fitting each category's own search intent (already-published, unchanged ledger-verified legacy posts keep their previous approved length); run current Research/Writer QA >=85, duplication and slug gates, VI/EN Core registration and post-publication Yoast/HTTP checks. Do not auto-generate 21 thin near-duplicate pages. Preserve all 9 existing post IDs and the existing Vietnamese content.

## Historical seed candidates (not approval gates)

| Historical wave (20 Oct 2026) | WordPress EN category ID | Category | Existing 500-topic ID | Original research target |
|---|---:|---|---:|---|
| 01 (historical) | **69** | Weekly & Monthly Rentals | **31** | Genuine published-price and contract comparison |
| 01 (historical) | **66** | Motorbike Handover & Maintenance | **49** | Practical semi-automatic handover inspection |
| 01 (historical) | **60** | Hoan Kiem Area | **285** | Verified parking and walking-zone planning |
| 02 (historical) | 61 | Old Quarter Riding | 286 | Train Street access, distinct from existing Old Quarter riding article #9 |
| 02 (historical) | 62 | Long Bien Area | 302 | Responsible visit to Long Bien market |
| 02 (historical) | 63 | Ba Dinh Area | 22 | Visitor-specific access and parking guidance |
| 03 (historical) | 64 | Gia Lam Area | 40 | Gia Lam and Bat Trang route, confirm accessible roads |
| 03 (historical) | 65 | Honda & Yamaha Comparisons | 18 | Wave versus Sirius, verify specs against model years |
| 03 (historical) | 67 | Navigation Apps & Maps | 371 | Avoiding motorway routing on motorcycle navigation |
| 04 (historical) | 68 | Hanoi Traffic & Parking | 17 | Guarded parking and official road rules |

## Parent-hub direct posts need separate planning

- Root terms 46 (Motorbike Rental in Hanoi), 47 (Hanoi Travel & Routes) and 48 (Riding Advice & Safety) currently have zero **direct** articles; WordPress category archive queries may nevertheless include child posts. Their three future direct articles require distinct non-overlapping topics and explicit publisher QA support for assigning root categories. Do not silently modify an existing article's category or republish it.
- Count the 10 direct child seeds and these 3 parent seeds separately when the owner's requirement means at least one **direct assignment** in every category.
- After each successful publication wave, verify WordPress `wp/v2/categories` for term counts, `nh-vien/v1/status` for English post IDs, Yoast canonical/sitemap, and the real EN category archive. If a category has no public articles its archive may not resolve yet; don't redirect it to the homepage.
- The EN publisher has **no count-based article or batch cap**, and does not wait for a three-post approval. A planned topic ID is not a published post. Small *editorial research packets* may still be used for focus, but never limit how many QA-passing manuscripts can publish.

