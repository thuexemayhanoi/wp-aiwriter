# SEO Batch 005 — updated two safety guides (17/10/2026)

**Site:** https://blog.rentbikehanoi.com/  
**Repo:** thuexemayhanoi/wp-aiwriter  
**Scope:** 2 previously published posts, in-place reversible edits, without slugs/canonicals/homepage changes.

## Production changes already made

1. WordPress **#245**, [Cách kiểm tra lốp xe máy thuê để tránh sự cố giữa đường](https://blog.rentbikehanoi.com/cach-kiem-tra-lop-xe-may-thue-de-tranh-su-co-giua-duong/):
   - Corrected advice to continue riding for kilometres with tubeless tyres losing air. Prioritises gradual safe stopping, not riding on a flattened/unstable tyre and contact with the rental provider/qualified repairer.
   - Corrected advice in the “cán đinh” FAQ which suggested that a nail lodged in the tyre makes continuing to a tyre shop automatically safe.
   - Added Gutenberg heading and related links to brake, lighting/turn-indicators, and vehicle-condition photo guides.
   - Confirmed `post_status=publish`, modified at **12:08:23 local** and valid public rendered title/meta/canonical/index-follow; the new body was **not** subsequently re-fetched in the public `<main>` owing to quota.
2. WordPress **#256**, [Kiểm tra đèn pha, đèn hậu và xi nhan khi nhận xe](https://blog.rentbikehanoi.com/cach-kiem-tra-den-pha-den-hau-va-xi-nhan-khi-nhan-xe/):
   - Replaced inappropriate “tạm được cho quãng ngắn” recommendation about non-functioning rear-brake stop lamp switch. Now advises reporting fault and fixing or changing vehicle before setting off.
   - Added Gutenberg heading and contextual links to brake, tyre and horn/mirror checks.
   - Confirmed `post_status=publish`, modified at **12:08:25 local**, and public `<main>` HTML actually contains the new safety advice and links. SEO head post-edit remains unchecked due quota.

**Rollback:** Complete original post bodies, titles, URLs and excerpts saved BEFORE production writes as `data/seo/batch-005-preedit-20261017.json`. WordPress revisions can restore the previous contents after reviewing newer changes.

## Link Matrix

- 3 new contextual internal links on #245 and 3 on #256.
- 6/6 destinations exist in authenticated published WordPress snapshot `data/seo/wp-inventory-20261017.json`. This is not a full independent HTTP/404 validation.
- No image, alt text, permalink, category or canonical edits.

## Source-backed editorial safety reasoning

- Michelin Việt Nam: https://www.michelin.vn/motorbike/loi-khuyen/lai-xe/xe-may-thung-lop-co-nen-di-tiep
- Michelin motorcycle riding advice: https://www.michelinman.com/motorcycle/tips-and-advice/motorcycle-riding-tips-and-advice/safe-riding-with-our-motorcycle-tires
- Triumph official owner handbook warns that inoperative brake lamps are dangerous and require correction: https://api.triumphtechnicalinformation.com/handbooks/documents/660bd43371e369e75f5bfb45/pdf

## QA gate and constraints

- **Do not mark these two posts as >=85/100 QA PASS yet.** Rate limit interrupted public content readback for #245, SEO-head recheck for #256, and final homepage after-write comparison. Both require more systematic factual review.
- WPVibe connection for the site reports *daily fair-use cap reached* on the `nguyentuantu1102@gmail.com` free account. Do not bypass or spam it; continue once limits naturally free up. The WordPress database read successfully showed both pages still published.
- Before edits, WPCode homepage SEO guard #1192 was active, WordPress homepage title, description, canonical and `index, follow` were valid and matched the owner-approved baseline. No homepage content was changed. Post-edit recheck is pending due limits.
- The backup provided from Hostinger 04/10/2026 is old, not current recovery snapshot; per-post GitHub original is a reversible rollback safeguard, not a replacement for disaster recovery.
- Baseline inventory 525 content URLs; **11 unique edited**, **9 scoped QA pass from earlier batches**, **2 pending QA**, **514 not yet edited**. Live post count can increase; recount regularly.

## Next hourly cycle

Complete QA verification for #245 / #256 *without repeating edits*, improve weak auto excerpt only if needed after inspecting Yoast rendered head and remaining factual statements; then optimize 2–5 new Matrix URLs (such as #253 or #262) with full pre-edit snapshot, QA >=85/100, live readback and protected homepage regression check. Do not invent rankings or indexing status.

Machine-readable checkpoint: `data/seo/seo-master-matrix-progress-20261017-batch005.json`.
