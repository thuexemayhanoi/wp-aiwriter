# AUTO SEO ENGINE 06 — Hosting backup verification (2026-10-17)

Target site: https://blog.rentbikehanoi.com/
Repository: thuexemayhanoi/wp-aiwriter
Method: locally inspect owner-supplied gz archives; gzip CRC verification, tar member listing, WordPress `wp-config.php` database mapping. Never upload database or WordPress archives to GitHub; they may contain credentials and private customer data.

## Correct matching pair for blog.rentbikehanoi.com

| Backup component | Owner-supplied archive (2026-10-04 13:10:48) | Verification |
|---|---|---|
| MariaDB | `u875771739_QuSkL.blog-rentbikehanoi-com.20261004131048.sql(1).gz` | gzip CRC PASS, 26 CREATE TABLE statements, WordPress site URL in SQL, DB identifier `u875771739_QuSkL` matches blog's archived `wp-config.php` |
| WordPress filesystem | `u875771739.blog-rentbikehanoi-com.20261004131048.tar(1).gz` | gzip CRC PASS, tar enumerated 8,703 members / 7,597 regular files, WP core / wp-config.php / wp-content present; archived DB identifier matches corresponding SQL |

NOT FOR THIS BLOG: `u875771739_iPCeC.thuexemaynguyentu-com.20261004131048.sql(1).gz` and `u875771739.thuexemaynguyentu-com.20261004131048.tar(1).gz`. These belong to a different production website. Both passed gzip CRC but MUST NOT be restored to the blog.

## Freshness and recovery limits

- Backup date: 2026-10-04, currently **13 days old** on 2026-10-17. The owner reports weekly automated hosting backups, but the most recent hosting restore point is **not accessible/verified** from the provided files.
- Archived blog filesystem lacks the currently live theme `nguyen-ha-glass-2026` (site_info confirms the theme live on 2026-10-17). This backup is thus NOT a recoverable full snapshot of the current live site state.
- Live 2026-10-17 site has **507 published posts and 18 published pages** (see `data/seo/wp-inventory-20261017.json`), including recently added articles after Oct 4. Restoring the old SQL/files onto live would risk content loss and theme regression.
- `gzip -t` proves compressed file integrity, NOT successful WordPress disaster-recovery restoration; restore testing was not performed.
- The supplied `wp-config.php` contains WordPress configuration; do not include raw backup bytes or configuration secrets in repository commits or public links.

## Verified Homepage Guard

Owner enabled WPCode snippet ID **1192**. WordPress WP-CLI (read tier) confirmed `post_status=publish`, `_wpcode_auto_insert=1`. Rendered live Homepage SEO Title, Meta Description, canonical and H1 remain unchanged from baseline `data/seo/homepage-protection-baseline-20261017.json` (checked 2026-10-17).

## Safe next work for the hourly SEO schedule

1. Obtain/verify a **current** Hostinger full database + filesystem backup/restore point covering current WordPress content and theme; verify WordPress DB and filesystem pair match. Owner states weekly automatic backups, but the uploaded Oct 4 pair does not demonstrate a recent restore point.
2. Until that condition is satisfied, allow only READ-ONLY audit, intent review, internal-link and alt proposals and GitHub documentation. Do not write production post/page/SEO metadata.
3. Provisional first high-intent SEO review group from live inventory: WP pages 26 `/long-bien/`, 27 `/ba-dinh/`, 28 `/gia-lam/`. All three have empty *explicit* Yoast custom title and description in authenticated REST inventory. This does **not** mean their rendered snippets are absent: check Yoast fallback in live HTML before proposing final changes. Check body relevance, distinct local intent, helpful internal links and accurate information; don't invent NAP, pricing, rankings or geography.
4. For actual production batch (only after current backup verification): 2–5 pages per hour, pre-write snapshot + rollback, QA >=85 with hard fails PASS, REST and public readback, no homepage SEO/H1/hero edits, then update Matrix/checkpoints and a before/after homepage snapshot.

## Execution status for 2026-10-17

- [x] Matched correct SQL/filesystem pair to WordPress database and hostname.
- [x] Checked gzip CRC and archive content lists, including theme comparison.
- [x] Confirmed WPCode homepage lock is enabled and homepage metadata still consistent.
- [x] Selected an initial read-only SEO review group.
- [ ] Verified most recent weekly host backup suitable for current production.
- [ ] Production SEO updates on the three pages — intentionally NOT done pending current backup.

Do not restore old backup over current production without separately approved disaster-recovery procedure.
