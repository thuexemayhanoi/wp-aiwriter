# EN writer checkpoint — 2026-10-20 (session 01KGiU6TaMPFJi6KEAjSmXge)

## State

- English pipeline created: `en/topics.json` (48 topics), `en/business.json`, `en/publication-policy.json`
  (**enabled=false, pilot, IDs 1–3**, page pairs 14→1759 `gioi-thieu`→`about`, 19→1760 `bang-gia`→`prices`,
  25→1761 `lien-he`→`contact`), `scripts/en_engine.py`, `scripts/en_ops.py` (with `rollout`), `scripts/wp_probe.py`,
  `tests/test_en_engine.py`, `tests/test_en_ops.py`, workflows `en-writer-qa.yml`, `en-publisher.yml`,
  `en-rollout.yml`, `en-autopilot.yml`, `wp-probe.yml`, runbook `docs/EN_PIPELINE.md`. The Vietnamese pipeline is
  untouched (83 tests pass in total).
- Pilot articles authored and QA PASS: `en/posts/0001.md` (licence rules, category 55), `0002.md` (Vision vs Air
  Blade, 50), `0003.md` (Hanoi to Ninh Binh, 54). **Not published**: the policy is off until the site is ready.
- Live site (probe 2026-10-19 21:28 UTC, run 39327672733): theme `wordpress-theme` 2.0.1 active (installed by Deployer
  for Git from the repository; the plugin is **not** deployed that way), VI-EN Core **0.5.0** active, Yoast 28.7,
  LiteSpeed Cache 7.9.1; pages 1758–1764 published; categories 46–56 exist and are empty; menus `primary-en` #57 and
  `footer-en` #58 exist; `nh-vien/v1/status` 404 (0.5.1 not installed); `/en/…` answers 200 in the Vietnamese chrome
  (`lang="vi"`, Yoast title suffix "- Thuê xe máy Nguyễn Hà", no hreflang, no `X-NH-VIEN-Lang`); `/en/category/…` 404.
- VI-EN Core 0.5.1 merged into `wordpress-theme` `main` (PR #11, b5bb0d4): admin switch with preflight, smoke test,
  rollback, undo, REST API `nh-vien/v1`, publish guard, cache purge on switch. Theme QA run 138 green; artifact
  `release-b5bb0d47c40ae12b308c6a89a114c2faab50edad` (expires 2026-11-18) holds `nguyen-ha-vi-en-0.5.1.zip`
  (sha256 `0eb94af802e27b2251ffe52787c1119a50b374a5d6cab1c392481ad5233db18e`, 56,928 bytes; `tools/package.sh` at
  b5bb0d4 rebuilds it).
- `SEO Protection (read-only guard)` is red and issue #15 "SEO Protection alert" is open since 2026-10-18, before this
  session: Vietnamese pages 17, 20–23, 25–28 were edited (200–1245 % word-count change) and ~140 Vietnamese posts
  changed by a few percent. Nothing in this session wrote to WordPress. Approving those edits is the owner's call
  (`SEO Protection` → mode `baseline`, `accept` with the IDs, a reason); leave it unless the edits are known.

## Next steps, in order

1. **Manual (owner):** upload `nguyen-ha-vi-en-0.5.1.zip` in Plugins → Add New → Upload Plugin → "Replace current with
   uploaded". Nothing changes on the site at that point (the switch stays off until the rollout turns it on).
2. **Automatic:** within two hours `EN autopilot` runs `rollout --live --confirm`: routes on, categories 46–56, the
   three page pairs, public verify of the seven English pages. A `VERIFIED` pass sets `enabled: true` in the policy,
   pushes, and starts `EN Publisher` live for IDs 1–3 (draft → register → publish → verify; ledger
   `data/en-publication-state.json` committed). A failed pass opens or comments on the issue "EN autopilot alert"
   (pause after three; close the issue to resume). To go faster: run `EN autopilot` by hand with `live`.
3. After the pilot: probe `/en/<slug>/` of the three posts, `/en/category/…`, the menus, `/sitemap_index.xml`,
   hreflang on the three paired pages; then `mode: batch`, `batch_size: 3`, then 10, then 20 (by commit), and write
   the next articles from `en/topics.json` (IDs 4, 5, 6 first: helmet rules, deposit, transmission types), each with
   official sources and an effective date.
4. Plugin 0.5.2 candidates (wordpress-theme): an English site name for `<title>`/`og:site_name` on `/en/` pages (Yoast
   appends the Vietnamese site name today); English Yoast meta descriptions are not writable through REST, so the
   excerpt/`nh_summary` carry the summary. The English pages are short (458–542 words on /en/ and /en/about/) against
   the brief's targets; enrich them with verified facts only.

## Resume commands

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/en_engine.py --mode qa
python scripts/en_engine.py --mode sync      # preview, no writes
python scripts/en_ops.py rollout             # dry run (needs WP_USERNAME / WP_APPLICATION_PASSWORD; on Actions only)
```
