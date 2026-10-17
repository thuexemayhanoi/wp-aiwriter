# SEO Batch 003 — live edits and checkpoint (17 October 2026)

Site: https://blog.rentbikehanoi.com/ | GitHub: `thuexemayhanoi/wp-aiwriter`

## Work completed

- WordPress **#20** [Khu vực](https://blog.rentbikehanoi.com/khu-vuc/): replaced internal SEO jargon in the lead with visitor-facing explanation; added distinct Phố Cổ and Gia Lâm pages, explained *one real pickup location vs. location-specific guides*, added price, vehicle-choice and contact navigation and relevant FAQs. Original HTML grid and its three existing links left intact.
- WordPress **#22** [Phố Cổ](https://blog.rentbikehanoi.com/pho-co/): expanded from a thin ~178-word local introduction with advice for pickup, parking, selecting vehicle, renting near accommodation, documents, actual shop location and non-duplicated local FAQs. Did **not** promise a branch in the Old Quarter or street access at specific times.
- Saved complete pre-edit post content for both pages in `data/seo/batch-003-preedit-20261017.json` **before writing**. WordPress revisions additionally available.
- Both pages: WP-CLI confirms `post_status=publish`, `post_modified` advanced and live `<main>` contains the new sections.
- All **8 unique local links on #20** and **6 on #22** reference published content URLs in the October 17 authenticated WordPress inventory. This is URL-inventory validation, **not** independent HTTP response/status checking for every target.
- Homepage WPCode guard #1192 present as `publish`, auto-insert enabled. Homepage Yoast Title, Meta Description, canonical, robots `index,follow` and rendered H1 match baseline **after** the two-page batch.

## QA / pending issue

WordPress #20: **88/100 provisional manual content + on-page QA — scoped PASS**. WordPress #22: **82/100 preliminary score — QA NOT PASSED**, because the new introductory paragraph has an awkward trailing sentence. It currently says `Trong khi <a href="https://blog.rentbikehanoi.com/hoan-kiem/">trang thuê xe máy Hoàn Kiếm</a> bao quát khu vực rộng hơn.` following a full stop. Replace that exact text with `Nếu cần thông tin cho phạm vi rộng hơn, hãy tham khảo <a href="https://blog.rentbikehanoi.com/hoan-kiem/">hướng dẫn thuê xe máy Hoàn Kiếm</a>.`, then re-read public HTML and complete QA. The attempt failed with **HTTP 429 rate limit**; **no further WordPress writes** were attempted afterward. Do not assert #22 passed the >=85 gate yet.

The QA scores are editorial/on-page manual reviews, *not* Google, Yoast, PageSpeed or comprehensive SEO scores. Full image ALT, technical performance, incoming backlinks, all live link status and GSC are outside this limited check.

## Progress

- Previous unique scoped QA-pass IDs: `23,25,26,27,28`.
- This batch edited `20,22`; page `20` passes scoped gate; page `22` remains open for copyediting.
- Edited total: **7 unique** of 525 baseline URLs.
- Scoped QA-pass total: **6**.
- Awaiting QA: **1** (#22).
- Baseline unedited first-pass URLs: **518** (publisher may change current total).
- Do not repeat changes already made; complete #22 proofreading then select 2–5 fresh pages on the next scheduled round, capturing original contents first.

## Constraints

Retain existing homepage, WordPress URL slugs, Yoast tags and live index settings, original factual business NAP, and any published pages. Use owner-confirmed weekly Hostinger backups plus page-local before-edit revisions/snapshots. October 4 backup was identified as historic rather than a fresh full production restore. Respect WPVibe 429 cooldown and do not spam retries. Do not blend Nguyễn Hà with Nguyễn Tú.

See the machine-readable data checkpoint at `data/seo/seo-master-matrix-progress-20261017-batch003.json`.
