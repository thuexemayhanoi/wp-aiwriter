# EN writer checkpoint — 2026-10-20 (session 01KGiU6TaMPFJi6KEAjSmXge)

## State

- **Live and verified (2026-10-19 22:04 UTC, run 39332264092):** the seven English pages 1758–1764 carry the content
  of `en/pages/*.md` (home 599 words, about 1,060, prices 859, contact 399, rental-guide 1,049, faq 1,125 with 21
  questions, motorbikes 845), each updated through `scripts/en_pages.py` with the previous content kept in the report
  artifact `en-pages-39332264092` and as a WordPress revision. Public answers HTTP 200 with the new titles.
- English pipeline: `en/topics.json` (48 topics), `en/business.json` (facts incl. fuel, delivery both ways, included
  items, models; allowed amounts incl. 20,000 and 100,000), `en/publication-policy.json` (**enabled=false, pilot,
  IDs 1–3**, page pairs 14→1759 `gioi-thieu`→`about`, 19→1760 `bang-gia`→`prices`, 25→1761 `lien-he`→`contact`,
  24→1763 `hoi-dap`→`faq`; the Vietnamese pages 29 `dieu-khoan` and 3 `bao-mat` have no English equivalent yet),
  `scripts/en_engine.py`, `scripts/en_ops.py` (`rollout` incl. the English site name for plugin 0.5.2+),
  `scripts/en_pages.py`, `scripts/wp_probe.py` (`--slugs`), tests `test_en_engine.py`, `test_en_ops.py`,
  `test_en_pages.py` (108 tests in total with the Vietnamese ones), workflows `en-writer-qa.yml`, `en-publisher.yml`,
  `en-rollout.yml`, `en-autopilot.yml`, `en-pages.yml`, `wp-probe.yml`, runbook `docs/EN_PIPELINE.md`.
- Articles authored and QA PASS (scores 96–100): `en/posts/0001.md` (licence rules, 55), `0002.md` (Vision vs Air
  Blade, 50), `0003.md` (Hanoi to Ninh Binh, 54), `0004.md` (helmet rules, 56), `0005.md` (rental deposit, 55),
  `0006.md` (manual / semi-automatic / automatic, 49), `0007.md` (50cc scooters, 51), `0008.md` (electric scooters,
  52), `0009.md` (Old Quarter riding, 53). Legal facts cite Law 36/2024/QH15, Decree 168/2024/ND-CP, Circular
  38/2024/TT-BGTVT and QCVN 2:2021/BKHCN with effective dates; VinFast figures from launch press coverage. **None
  published**: the policy is off (pilot IDs 1–3 first; 4–9 wait for `mode: batch`). Next IDs: 10, 11, 12.
- Live site (probe 2026-10-19 21:43 UTC): theme `wordpress-theme` 2.0.1 active (Deployer for Git deploys the theme
  only), VI-EN Core **0.5.0** active, Yoast 28.7, LiteSpeed Cache 7.9.1; categories 46–56 exist and are empty; menus
  `primary-en` #57 and `footer-en` #58 have their items; `nh-vien/v1/status` 404; `/en/…` answers 200 in the
  Vietnamese chrome (`lang="vi"`, Yoast title suffix "- Thuê xe máy Nguyễn Hà", empty meta description, no hreflang);
  `/en/category/…` 404. Vietnamese pages in the page sitemap: 19 (incl. `/hoi-dap/` FAQ, `/dieu-khoan/` terms,
  `/bao-mat/` privacy, `/dich-vu/`, `/xe-50cc/`, `/xe-dien/`, district pages).
- VI-EN Core in `wordpress-theme` `main`: **0.5.2** (PR #12 merged, 8105785) on top of 0.5.1 (PR #11, b5bb0d4). 0.5.2
  adds the English site name (Tools field + `POST nh-vien/v1/settings`) used inside `/en/` pages for the `<title>`
  suffix, `og:site_name` and the structured data, and the excerpt as meta/OG/Twitter description when Yoast has none.
  `tools/package.sh` at 8105785 builds `nguyen-ha-vi-en-0.5.2.zip` (sha256
  `2c61344127b6c8dd90a59335e6f9288f1faa177c2b81891c1ee3311a1c051493`); the `release-8105785…` artifact of the Theme QA
  run on `main` holds the same package once that run is green.
- `SEO Protection (read-only guard)` is red and issue #15 is open since 2026-10-18, before this work: Vietnamese pages
  17, 20–23, 25–28 edited (200–1245 % word-count change) and ~140 Vietnamese posts changed by a few percent. Nothing
  here wrote to a Vietnamese page or post. Approving those edits is the owner's call (`SEO Protection` → `baseline`,
  `accept` with the IDs, a reason).

## Next steps, in order

1. **Manual (owner):** upload `nguyen-ha-vi-en-0.5.2.zip` in Plugins → Add New → Upload Plugin → "Replace current with
   uploaded". Nothing changes on the site at that point.
2. **Automatic:** within two hours `EN autopilot` runs `rollout --live --confirm`: routes on, categories 46–56, the
   three page pairs, the English site name "Nguyen Ha Motorbike Rental", public verify of the seven English pages. A
   `VERIFIED` pass sets `enabled: true` in the policy, pushes, and starts `EN Publisher` live for IDs 1–3 (draft →
   register → publish → verify; ledger `data/en-publication-state.json` committed). A failed pass opens or comments on
   the issue "EN autopilot alert" (pause after three; close the issue to resume).
3. After the pilot: probe `/en/<slug>/` of the three posts, `/en/category/…`, the menus, `/sitemap_index.xml`,
   hreflang on the four paired pages, `og:site_name` and the meta descriptions; then `mode: batch`, `batch_size: 3`,
   then 10, then 20 (by commit). Consider English terms and privacy pages (the Vietnamese `/dieu-khoan/` #29 and
   `/bao-mat/` #3 exist; `en_pages.py` is update-only, so a create path with the same checks would be needed).
4. Keep writing `en/posts/NNNN.md` from `en/topics.json` (IDs 4 onwards), each with official sources and an effective
   date for legal facts; they stay unpublished until batch mode.

## Resume commands

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/en_engine.py --mode qa
python scripts/en_pages.py --mode qa
python scripts/en_engine.py --mode sync      # preview, no writes
python scripts/en_ops.py rollout             # dry run (needs WP_USERNAME / WP_APPLICATION_PASSWORD; on Actions only)
```
