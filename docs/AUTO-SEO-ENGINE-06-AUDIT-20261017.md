# AUTO SEO ENGINE 06 — VERIFIED COLD-START AUDIT (17/10/2026)

Site: https://blog.rentbikehanoi.com/

Scope: Live authenticated WordPress REST inventory and WordPress database aggregate SELECT, no GSC/GA4/rankings supplied. **No fabricated traffic or ranking data.**
 
## Production state and homepage lock
- WordPress 7.1.3, theme Nguyễn Hà Glass 2026, Yoast SEO 28.7.
- Homepage uses posts index, not a static page (show_on_front=posts; page_on_front=0).
- Original homepage SEO values saved in `data/seo/homepage-protection-baseline-20261017.json`.
- WPCode PHP Homepage Guard ID 1192 was created **DISABLED**. This is a staged write-layer guard, NOT yet an active protection; owner must review and enable it.
- Protected template content: `front-page.php` lines 26–27 for hero H1/lead. WPCode option filters cannot block a future theme file deployment by themselves.
- P0 is a HARD BLOCK on broad production content changes until the owner enables #1192 and a fresh homepage before/after comparison passes.
- WordPress post data has **not** been mass-modified in this run. Host-level database/files backup before mass updates remains unverified.

## Inventory — verified against WordPress
| Field | Count | Meaning |
|---|---:|---|
| Published posts | 507 | Unique WordPress posts |
| Published pages | 18 | Static pages; none is configured as front page |
| Published content URLs | 525 | Posts and pages, excludes category archive URLs |
| Categories | 22 | Include parent and child categories |
| Image attachments | 58 | Media Library image records |
| Images without Media Library alt | 57 | Requires visual/context verification |
| Posts without featured image | 480 | Not automatically a ranking issue |
| Post/page records with empty custom Yoast SEO title | 482 | Yoast fallback titles may still render |
| Post/page records with empty custom Yoast meta description | 478 | Yoast/snippet fallback may still render |
| Published posts with `href=` in body (SQL) | 383 | Presence only; destinations not fully validated |
| Published posts with no `href=` in body (SQL) | 124 | Candidate link analysis |

## WordPress categories (published post membership, multi-assignment counted more than once)

| Cluster | Posts |
|---|---:|
| Cẩm nang > Kinh nghiệm | 112 |
| Dịch vụ > Xe máy > Xe ga | 55 |
| Cẩm nang > Hãng xe > Hãng xe máy | 55 |
| Dịch vụ > Xe máy > Xe số | 45 |
| Dịch vụ > Xe điện | 35 |
| Cẩm nang > Hãng xe > Hãng xe điện | 35 |
| Cẩm nang > Giao thông | 35 |
| Dịch vụ > Xe máy > Xe 50cc | 25 |
| Cẩm nang > Ứng dụng > App xe máy | 25 |
| Cẩm nang > Ứng dụng > App xe điện | 20 |
| Khu vực > Long Biên | 16 |
| Khu vực > Hoàn Kiếm | 15 |
| Khu vực > Gia Lâm | 13 |
| Khu vực > Ba Đình | 10 |
| Khu vực > Hoàn Kiếm > Phố Cổ | 8 |
| Cẩm nang > Hãng xe | 6 |
| Cẩm nang | 4 |
| Uncategorized | 1 |
| Dịch vụ > Xe máy | 1 |

## Search-intent collisions: candidate review, not proven keyword cannibalization
- Exact normalized duplicate Post/Page titles: **3 groups**.
- Lexical Jaccard similarity >= 0.77 after stripping generic stopwords: **16 candidate pairs**; this is a screening heuristic, not SERP overlap.
1. 1: [1066](https://blog.rentbikehanoi.com/excel-375-thue-xe-ga-theo-tuan-nen-chon-theo-tieu-chi-nao/) ↔ [1015](https://blog.rentbikehanoi.com/excel-324-thue-xe-so-theo-tuan-nen-chon-theo-tieu-chi-nao/)
2. 1: [1062](https://blog.rentbikehanoi.com/excel-371-xe-ga-co-phu-hop-voi-nguoi-thue-lan-dau-tai-ha-noi-khong/) ↔ [1010](https://blog.rentbikehanoi.com/excel-319-xe-so-co-phu-hop-voi-nguoi-thue-lan-dau-tai-ha-noi-khong/)
3. 1: [1060](https://blog.rentbikehanoi.com/excel-369-di-xe-ga-vao-mua-dong-ha-noi-can-luu-y-gi/) ↔ [1011](https://blog.rentbikehanoi.com/excel-320-di-xe-so-vao-mua-dong-ha-noi-can-luu-y-gi/)
4. 1: [1059](https://blog.rentbikehanoi.com/excel-368-thue-xe-ga-dai-ngay-can-kiem-tra-nhung-bo-phan-nao-thuong-xuyen/) ↔ [997](https://blog.rentbikehanoi.com/excel-306-thue-xe-so-dai-ngay-can-kiem-tra-nhung-bo-phan-nao-thuong-xuyen/)
5. 1: [1041](https://blog.rentbikehanoi.com/excel-350-cach-dung-phanh-truoc-va-phanh-sau-tren-xe-ga-an-toan-hon/) ↔ [989](https://blog.rentbikehanoi.com/excel-298-cach-dung-phanh-truoc-va-phanh-sau-tren-xe-so-an-toan-hon/)
6. 1: [1040](https://blog.rentbikehanoi.com/excel-349-xe-ga-co-de-dieu-khien-khi-troi-mua-khong/) ↔ [986](https://blog.rentbikehanoi.com/excel-295-xe-so-co-de-dieu-khien-khi-troi-mua-khong/)
7. 1: [1035](https://blog.rentbikehanoi.com/excel-344-xe-ga-110cc-co-du-dung-cho-nhu-cau-di-lai-trong-ha-noi-khong/) ↔ [981](https://blog.rentbikehanoi.com/excel-290-xe-so-110cc-co-du-dung-cho-nhu-cau-di-lai-trong-ha-noi-khong/)
8. 1: [1017](https://blog.rentbikehanoi.com/excel-326-xe-ga-co-phu-hop-de-di-lam-hang-ngay-trong-noi-do-ha-noi-khong/) ↔ [972](https://blog.rentbikehanoi.com/excel-281-xe-so-co-phu-hop-de-di-lam-hang-ngay-trong-noi-do-ha-noi-khong/)
9. 0.889: [1186](https://blog.rentbikehanoi.com/excel-495-di-xe-may-quanh-ngoc-lam-va-bo-de-nhung-tuyen-thuan-tien-cho-nguoi-moi/) ↔ [1144](https://blog.rentbikehanoi.com/excel-453-di-xe-may-quanh-ngoc-lam-nhung-tuyen-duong-thuan-tien-cho-nguoi-moi/)
10. 0.857: [1072](https://blog.rentbikehanoi.com/excel-381-xe-may-dien-co-phu-hop-de-di-lam-hang-ngay-o-ha-noi-khong/) ↔ [1017](https://blog.rentbikehanoi.com/excel-326-xe-ga-co-phu-hop-de-di-lam-hang-ngay-trong-noi-do-ha-noi-khong/)
11. 0.857: [1072](https://blog.rentbikehanoi.com/excel-381-xe-may-dien-co-phu-hop-de-di-lam-hang-ngay-o-ha-noi-khong/) ↔ [972](https://blog.rentbikehanoi.com/excel-281-xe-so-co-phu-hop-de-di-lam-hang-ngay-trong-noi-do-ha-noi-khong/)
12. 0.857: [1061](https://blog.rentbikehanoi.com/excel-370-di-xe-ga-duoi-mua-lon-can-chu-y-gi-o-lop-va-phanh/) ↔ [1012](https://blog.rentbikehanoi.com/excel-321-di-xe-so-duoi-mua-lon-can-chu-y-gi-o-bo-phan-phanh-va-lop/)

## Internal-link baseline limitations
- Current committed `docs/INTERNAL_LINK_MATRIX.md` analyzed 336 articles and reported 769 distinct edges and 253 body-link orphans **at that snapshot only**.
- Current site has 507 posts. That old graph is incomplete for the current production inventory and must not be advertised as a fresh full-site orphan count.
- Recompute body-link graph for all published posts, pages, menu/sidebar/footer, category archives separately; distinguish zero incoming *contextual body links* from true orphan pages.
- Supporting → cluster hub/pillar → relevant commercial page; avoid obligatory homepage links and unrelated anchors.

## Priority order, ZERO-DATA mode
1. P0: Activate owner-approved WordPress guard; compare home title, description, H1, hero lead against protected snapshot; verify theme-file review gate.
2. Back up production DB + wp-content through hosting or existing backup facility, snapshot affected post fields before each batch. No destructive changes.
3. Rendered Yoast meta coverage and intent checks across all 525 post/page URLs; safely propose titles/meta only for genuinely weak pages.
4. Visually classify 57 missing alt items; decorative images can have blank alt. Audit per-use context before edits.
5. Refresh body + navigation link graph and validate targets with HEAD/GET. Repair actual orphans and dead ends in category-cohesive batches.
6. QA >=85/100 plus hard-fail truthfulness, canonical/indexability, duplicate intent, broken links, and homepage guard. Re-verify each saved field.
7. Publish only with validated rollback, checkpoint, and evidence of WordPress REST readback.

**Existing systems to reuse:** `scripts/seo_audit.py`, `scripts/link_matrix.py`, `scripts/seo_protection.py`. Do not create overlapping autonomous publisher/optimizer.

## Machine-readable evidence
- `data/seo/wp-inventory-20261017.json`: 507 published posts, 18 published pages, 22 categories, 58 image attachments, stored URLs and editable Yoast meta baseline.
- `data/seo/homepage-protection-baseline-20261017.json`: immutable homepage SEO values.
- `data/seo/wpcode-homepage-seo-guard.php.txt`: owner-activatable PHP guard.
- `data/seo/link-matrix.json`: **historical partial graph**, not complete production verification.

## Publishing receipts from this run
WordPress Post/Page edits: 0; updated image alts: 0; contextual internal links inserted: 0; published article count changes: 0. WPCode snippet #1192 saved disabled. Repository snapshot and audit files were committed; no claims of SEO rank increases.
