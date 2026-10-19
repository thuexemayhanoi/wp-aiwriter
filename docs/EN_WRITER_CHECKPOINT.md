# EN writer checkpoint — 2026-10-20 (session 01KGiU6TaMPFJi6KEAjSmXge)

## State

- English pipeline created: `en/topics.json` (48 topics), `en/business.json`, `en/publication-policy.json`
  (**enabled=false, pilot, IDs 1–3**), `scripts/en_engine.py`, `scripts/en_ops.py`, `scripts/wp_probe.py`,
  `tests/test_en_engine.py`, workflows `en-writer-qa.yml`, `en-publisher.yml`, `en-rollout.yml`, `wp-probe.yml`,
  runbook `docs/EN_PIPELINE.md`. The Vietnamese pipeline is untouched (65 tests pass in total).
- Pilot articles authored and QA PASS: `en/posts/0001.md` (licence rules, category 55), `0002.md` (Vision vs Air
  Blade, 50), `0003.md` (Hanoi to Ninh Binh, 54). **Not published**: the policy is off until the site is ready.
- Live site (probe 2026-10-19 21:03 UTC): theme `wordpress-theme` 2.0.1 active (installed by Deployer for Git from the
  repository), VI-EN Core **0.5.0** active, Yoast 28.7, LiteSpeed Cache 7.9.1; pages 1758–1764 published; categories
  46–56 exist and are empty; menus `primary-en` #57 and `footer-en` #58 exist (no location); `nh-vien/v1/status` 404
  (0.5.1 not installed); `/en/…` answers 200 but in the Vietnamese chrome (`lang="vi"`, no `X-NH-VIEN-Lang`) because the
  routes are not switched on; `/en/category/…` 404.
- VI-EN Core 0.5.1 merged into `wordpress-theme` `main` (PR #11, b5bb0d4): admin switch with preflight, smoke test,
  rollback, undo, REST API `nh-vien/v1`, publish guard, cache purge on switch.

## Next steps, in order

1. **Manual (owner):** download `nguyen-ha-vi-en-0.5.1.zip` from the `release-<sha>` artifact of the green Theme QA run on
   `main` (or build it with `tools/package.sh`) and upload it in Plugins → Add New → Upload Plugin → "Replace current with
   uploaded". Nothing changes on the site at that point.
2. Run `EN rollout` (wp-aiwriter → Actions) with `status`, then `enable` (live + confirm), then `register-categories`
   `46,47,48,49,50,51,52,53,54,55,56`, then `link-pages` `14:1759,19:1760,25:1761`, then `verify`. Read every summary.
3. Set `"enabled": true` in `en/publication-policy.json` and push: EN Writer QA runs, EN Publisher publishes IDs 1–3
   (draft → register → publish → verify) and commits `data/en-publication-state.json`. Check `/en/<slug>/`, the
   categories, `/en/category/…`, the menus and `/sitemap_index.xml`.
4. If all three verify: `mode: batch`, `batch_size: 3`, then 10, then 20; write the next articles from `en/topics.json`
   (IDs 4, 5, 6 first: helmet rules, deposit, transmission types), each with official sources and an effective date.
5. Plugin 0.5.2 candidates (wordpress-theme): an English site name for `<title>`/`og:site_name` on `/en/` pages (Yoast
   appends the Vietnamese site name today); English Yoast meta descriptions are not writable through REST, so the
   excerpt/`nh_summary` carry the summary.

## Resume commands

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/en_engine.py --mode qa
python scripts/en_engine.py --mode sync      # preview, no writes
```
