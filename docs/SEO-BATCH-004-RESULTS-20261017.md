# SEO Batch 004 — executed and live verified (17/10/2026)

Target site: https://blog.rentbikehanoi.com/
Repository: thuexemayhanoi/wp-aiwriter

## Work executed

- **#22 Phố Cổ** `/pho-co/`: fixed dangling Vietnamese contrast sentence left in prior Batch 003: “Trong khi ...” -> “Nếu cần thông tin cho phạm vi rộng hơn, hãy tham khảo ...”. Confirmed rendered WordPress content reflects correction. Original before-edit copy saved by Batch 003.
- **#21 Hoàn Kiếm** `/hoan-kiem/`: replaced jargon-like thin introduction with actionable information about actual location in Bồ Đề, Long Biên vs renting for use in Hoàn Kiếm; added pickup/delivery distinction, vehicle choice, paperwork, links and FAQs. Before-edit full page snapshot: `data/seo/batch-004-preedit-20261017.json`.
- **#219** `/cach-kiem-tra-phanh-xe-truoc-khi-bat-dau-hanh-trinh-o-ha-noi/`: introduced contextual related reading to three published safety posts (tyres, lights/indicators, photograph vehicle condition), preserving Gutenberg block semantics. Its first-paragraph fallback description was weak. WP-CLI refused writing protected Yoast meta key without forcing; **did not bypass** protection. Instead updated ordinary WordPress `post_excerpt` via `post update`, which Yoast reads as the live, improved 141-character `meta description` (confirmed in rendered HTML). Also replaced one unsupported *universal 3 mm brake pad threshold* with **manufacturer-specific wear indicators**, aligned to Honda documentation: https://global.honda/en/motorcycle-aftersales/plusone/202301.html and https://webom.hondamotopub.com/webom/HMEE/MLC250/html/GMT016002.html .
- Full original #219 post content and original empty excerpt captured in GitHub BEFORE WordPress writes: `data/seo/batch-004-preedit-20261017.json`. WordPress revisions allow rollback.

## Technical QA evidence

- WordPress #21, #22, #219 all remain `publish`, `post_modified` advanced, and their respective live public `main` includes edits. Page #21's Yoast rendered title/description/self-canonical and `index, follow` unchanged. Post #219's new rendered description is verified; canonical unchanged.
- #21: seven internal links, all resolve to paths in published WordPress inventory; #22 seven; #219 three related-safety links to currently published post slugs. Target existence verified using authenticated inventory, not an independent HTTP 200 crawl for each.
- Homepage Guard WPCode #1192 `publish`, `auto_insert=1` confirmed before edits. Homepage title/description/canonical/robots matched baseline before edits, and H1 matched baseline again afterward. One later homepage HEAD fetch returned a CDN browser-challenge HTML (`Checking your browser` with a `noindex` tag). This tag belongs to **the challenge response**, not necessarily the underlying WordPress homepage. Do not misreport that Google now sees homepage `noindex`. Recheck when host anti-bot challenge clears.
- No URL, slug, canonical, theme, home SEO, homepage hero, menu, image or existing terms changed.

## Internal editorial / on-page QA score (limited scope)

| ID | URL | Manual scoped QA | Result |
|---|---|---:|---|
| 22 | `/pho-co/` | **88/100** | pass after correction |
| 21 | `/hoan-kiem/` | **89/100** | pass |
| 219 | `/cach-kiem-tra-phanh-xe-truoc-khi-bat-dau-hanh-trinh-o-ha-noi/` | **86/100** | pass scoped; full historical technical claims deserve follow-up specialist fact check |

The scoring rubric is internal: 25 intent/usefulness, 20 facts/safety, 20 rendered technical metadata, 15 contextual internal links, 10 writing/structure, 10 rollback/public verification. These are **not** scores from Yoast, Google, GSC or PageSpeed. The original article #219 is lengthy and the content/safety check is not a complete manufacturer-by-manufacturer audit. Remaining cross-site image ALT, broken external links, CWV, full incoming-link graph and every FAQ factual/legal nuance still require independent verification.

## Progress / next run

Prior unique modified URLs: 7 (IDs 20,22,23,25,26,27,28). New modified URLs: 2 (IDs 21,219). Modified so far = **9**. Scoped editorial/on-page QA passes = **9**. First-pass untouched baseline URLs = **516** of 525. The number of published posts/pages may change as publisher workflows run; refresh count periodically.

Continue the existing scheduled 2–5-page hourly batches without repeating completed IDs. Next candidates: additional published posts with no contextual outbound links, e.g. ID 245 `/cach-kiem-tra-lop-xe-may-thue-de-tranh-su-co-giua-duong/`, ID 253, ID 256 or related intent clusters. Review real content, claims and rendered Yoast before writing; snapshot everything first. Respect WPVibe plan quota and any 429.

## Backup note
The owner reports weekly Hostinger backups. The uploaded Oct 4 SQL/tar pair is a valid old historical archive but **not** a current production snapshot. Per-page GitHub originals and WordPress revisions protect these reversible small edits, but do not substitute a current disaster recovery backup.

See `data/seo/seo-master-matrix-progress-20261017-batch004.json`.
