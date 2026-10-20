# English category seeding: three original articles per owner approval

Last live audit: 20 October 2026. WordPress VI/EN Core reported **21 English content categories and 9 published English articles**, all in the existing original EN groups. The 10 newly registered subcategories (IDs 60–69) had no directly assigned English articles. Parent category IDs 46, 47 and 48 had zero direct assignments, although their category hierarchies already contained published child articles.

**Rules (new authoring standard effective 20 October 2026):** No placeholder articles, no Vietnamese translations, no invented branches, delivery options, parking rates or licence terms. Write one original **1,600–5,000-word** article fitting each category's own search intent (already-published, unchanged ledger-verified legacy posts keep their previous approved length); run current Research/Writer QA >=85, duplication and slug gates, VI/EN Core registration and post-publication Yoast/HTTP checks. Do not auto-generate 21 thin near-duplicate pages. Preserve all 9 existing post IDs and the existing Vietnamese content.

## Seed queue and approvals

| Owner approval batch | WordPress EN category ID | Category | Existing 500-topic ID | Draft or research target |
|---|---:|---|---:|---|
| **01 (approved, author now)** | **69** | Weekly & Monthly Rentals | **31** | Genuine published-price and contract comparison |
| **01 (approved, author now)** | **66** | Motorbike Handover & Maintenance | **49** | Practical semi-automatic handover inspection |
| **01 (approved, author now)** | **60** | Hoan Kiem Area | **285** | Verified parking and walking-zone planning |
| 02 (needs owner's next approval) | 61 | Old Quarter Riding | 286 | Train Street access, distinct from existing Old Quarter riding article #9 |
| 02 (needs owner's next approval) | 62 | Long Bien Area | 302 | Responsible visit to Long Bien market |
| 02 (needs owner's next approval) | 63 | Ba Dinh Area | 22 | Visitor-specific access and parking guidance |
| 03 (needs approval) | 64 | Gia Lam Area | 40 | Gia Lam and Bat Trang route, confirm accessible roads |
| 03 (needs approval) | 65 | Honda & Yamaha Comparisons | 18 | Wave versus Sirius, verify specs against model years |
| 03 (needs approval) | 67 | Navigation Apps & Maps | 371 | Avoiding motorway routing on motorcycle navigation |
| 04 (needs approval) | 68 | Hanoi Traffic & Parking | 17 | Guarded parking and official road rules |

## Parent-hub direct posts need separate planning

- Root terms 46 (Motorbike Rental in Hanoi), 47 (Hanoi Travel & Routes) and 48 (Riding Advice & Safety) currently have zero **direct** articles; WordPress category archive queries may nevertheless include child posts. Their three future direct articles require distinct non-overlapping topics and explicit publisher QA support for assigning root categories. Do not silently modify an existing article's category or republish it.
- Count the 10 direct child seeds and these 3 parent seeds separately when the owner's requirement means at least one **direct assignment** in every category.
- After each owner-approved batch, verify WordPress `wp/v2/categories` for term counts, `nh-vien/v1/status` for English post IDs, Yoast canonical/sitemap, and the real EN category archive. If a category has no public articles its archive may not resolve yet; don't redirect it to the homepage.
- The publisher limit for this seed stage is **3 new posts per successful run** (`batch_size=3, max_batches_per_run=1`). Pause for the owner's next explicit approval before adding more new ready manuscripts. A planned topic ID is not a published post.

