> **21 October 2026 FAST WRITER OVERRIDE:** Canonical EN titles already in `en/topics.json` are write-ready; optional Excel title suggestions need no review or synchronization. Use [EN_FAST_WRITER.md](EN_FAST_WRITER.md) and `python scripts/en_writer_brief.py --limit 10 --format compact`. Old 3-topic/manual title review instructions in historical checkpoints are not active. QA ≥76 and all hard publication gates remain.

## EN FAST WRITER PASS — 2026-10-22 · IDs 444–500 · all 500 manuscripts on `main`; 493 VERIFIED, 494–500 in publisher queue

- Scope: EN only → `https://blog.rentbikehanoi.com/en/`. Titles, slugs and category IDs taken unchanged from `en/topics.json`; no VI, URL, canonical, workflow, plugin or ledger edits. Source commits on `main`: `6680f29` (464–473), `ff44d71` (474–485), `463f641` (486–493), `4b64106` (494–500), after the earlier batches 444–463.
- **Ledger at time of writing (`data/en-publication-state.json`):** 493 `VERIFIED`. WordPress IDs 464→3392 … 473→3410, 474→3414 … 485→3436, 486→3438 … 493→3452 (two IDs per post, ascending). **494–500 were pushed and are waiting for the publisher — re-read the ledger before trusting this line.**
- QA: every manuscript in this range scores 100 locally (`python scripts/en_engine.py --mode qa`, `qa_errors: []`), 1,718–2,391 words.
- **Facts checked for this range (reuse, do not re-derive):** Law 36/2024/QH15 Articles 9, 11, 12, 14, 15, 18, 20–22, 24, 30, 33, 59, 77, 80–83 from the English translation on `english.luatvietnam.vn`; railway-crossing fine for motorbikes VND 4–6 million under **Decree 81/2026/ND-CP Art 13** (effective 15 May 2026, railway sector, not Decree 168); pavement riding VND 4–6 million + 2 points and phone use VND 800,000–1,000,000 + 4 points under Decree 168/2024 Art 7 (a phone fixed in a holder and only looked at is outside the ban per Vietnamese legal commentary); number-plate covering VND 4–6 million + 6 points (Art 14); motorbike U-turn where banned VND 400,000–600,000 (Art 7(2)(k)); engine running at a pump has no stand-alone traffic fine, a lawyer links it to Decree 106/2025/ND-CP Art 11 (VND 20–25 million). Medicine, heat, fatigue, helmet, flood and passenger articles rely on NHS/CDC/WHO/NWS/Snell-derived guidance and say so.
- Shop facts used only as published (`en/business.json`, `/terms/`, `/prices/`): one basic helmet per rider, no raincoat in short rentals, no separate lock, late fee VND 30,000/h for 1–5 h. Child helmets, passenger cover, recovery fees, flood-damage handling and spare bulbs are **not published**, so the articles tell the reader to ask the shop.
- **Items for the owner (not fixed here, VERIFIED posts are immutable):** (1) published #421 (WP 2695) shows a truncated external source URL for Law 36/2024 Art 18 in its `## Sources`; (2) IDs 100–104 were already VERIFIED (WP 2138–2146) when a second local set of manuscripts for the same IDs existed; those duplicates were deliberately not pushed; (3) Firecrawl credits ran out during this pass, so research used Nimble search/extract and the Law's English text instead.
- After the last ID is `VERIFIED`: reconcile ledger vs live URLs (404s, category, slug, canonical, sitemap, internal links) read-only; never retry an uncertain POST or edit the ledger by hand.

---

## EN FAST WRITER PASS — 2026-10-21 · IDs 38, 41, 43, 45, 48, 50, 54, 56–84 · 30 VERIFIED, 80–84 in publisher queue

- Scope: EN only → `https://blog.rentbikehanoi.com/en/`. Titles, slugs and category IDs taken unchanged from `en/topics.json`; no VI, URL, canonical or ledger changes. Source commits on `main`: `7ede457`, `402d104` (+ `473bcb1` fix), `74a8aaf`, `a79e863`, `2fc5d3f`, `add5b8f`, `3a27896`.
- **VERIFIED by the EN Publisher (ledger + WordPress ID):** 41→1958, 43→1960, 45→1962, 48→1964, 38→1966, 50→1968, 54→1970, 56→1972, 57→1974, 59→1976, 60→1978, 61→1980, 62→1982, 63→1984, 64→1986, 65→1988, 66→1990, 67→1992, 68→1994, 69→1996, 70→1998, 74→2000, 75→2002, 76→2004, 77→2006, 78→2008, 71→2010, 72→2012, 73→2014, 79→2016. Ledger total at last read: **83 VERIFIED**.
- **Pushed, publication pending at time of writing:** 80, 81, 82, 83, 84 (QA 98–100 locally; re-check the ledger before trusting this line).
- QA: every manuscript 1,618–2,586 words, local `en_engine.py --mode qa` 0 errors, scores 91–100 before the final description trims (all 100 or 95–98 after).
- **Legal fact-check corrections made BEFORE publication (important for future writers):** the first drafts of #41/#43/#45 quoted secondary summaries. Checked against the official text of Decree 168/2024/ND-CP on `xaydungchinhsach.chinhphu.vn`, the fixed VND 200,000–300,000 "did not carry" fines in Article 18 clause 2 apply to motorbikes in **commercial transport**; for private/rental riders the decree fines **not having** valid insurance (200,000–300,000), no/expired registration (Article 14 clause 2, 2,000,000–3,000,000), and licence offences (Article 18: 2,000,000–4,000,000 up to 125 cc, 6,000,000–8,000,000 above). Wrong-lane/keep-right = Article 7 clause 3 point d (600,000–800,000); banned road = clause 6 point b (2,000,000–3,000,000, 2 points); wrong way/pavement = clause 7 point a (4,000,000–6,000,000, 2 points); expressway = clause 7 point b (6 points); red light = clause 7 point c (4 points). Decree 238/2026/ND-CP (15 Aug 2026) does not change Articles 7 or 18 amounts (it rewords Art. 14 clause 3 point b and Art. 18 clause 4). Law 36/2024/QH15 Articles 13, 33, 56, 57 were read verbatim. Do not repeat the secondary-source figures.
- Source notes: Honda Vietnam Wave RSX FI owner's manual (`cdn.honda.com.vn/motorbike-manual/September2025/EzA6x0gXYsjvv9AhkVm2.pdf`), Honda safe-riding training document (`cdn.honda.com.vn/training-material-document-customer/August2026/U4p8gKhBPAbzAL0kuQgS.pdf`), Honda Global Plus One chain/tyre pages, Yamaha Motor Vietnam Exciter/Sirius pages, V-Green swap conditions, Hanoi fire-prevention charging advice (reported 5 Sep 2026). PDF scrapes cost ~100+ Firecrawl credits for the manual; plain HTML pages ~5. Direct `curl`/WebFetch to Vietnamese sites is blocked in this container; Firecrawl works.
- **Topic-cluster caution:** IDs 60–89 are a dense cluster of near-neighbour semi-automatic-bike topics. Each article was given a distinct question and heading set and passed the engine's same-intent gate, but later IDs in the cluster have little new factual material beyond the Honda manual/training document. Keep the same discipline: one real question per article, no padding, no invented figures.
- Next candidates (re-run `python scripts/en_writer_brief.py --limit 10 --format compact`): **85, 86, 87, 88, 89**, then 90+. Never republish a VERIFIED ID; always `git fetch` + rebase before push because the Publisher commits checkpoints to `main`.

---

## EN WRITE/PUBLISH SMOKE TEST — 2026-10-21 · IDs 46, 47 · 2/2 VERIFIED

> Owner-authorised English-only real publication test after the QA score cutoff changed to 76/100. All hard gates remain required, and this is a verified GitHub + WordPress result, not merely a manuscript commit.

- Source commit: `ef484c356ba921577d67d50eff5e10dbfe3c8210` on `main`; files `en/posts/0046.md` and `en/posts/0047.md`. Titles, slugs and category IDs were taken unchanged from `en/topics.json`; no Excel prefix and no VI changes.
- EN Writer QA run `39583332710`: success, 48 authored, 48 PASS, 0 FAIL. Topic 46: **2,007 words, QA 96/100** (4-point title-length deduction); topic 47: **2,185 words, QA 96/100** (4-point title-length deduction).
- EN Publisher run `39583428444`: success, **2 newly created and VERIFIED**, 46 previously existing, 0 duplicates, 0 errors, empty remaining eligible queue.
- **EN-0046:** `Semi-Automatic Bikes Explained: How to Ride a Honda Wave Without a Clutch` — term **49**, WP post **1944**, `VERIFIED/publish`, https://blog.rentbikehanoi.com/en/how-to-ride-a-semi-automatic-honda-wave/
- **EN-0047:** `Hanoi Street Food by Scooter: A Loop That Avoids the Worst Traffic` — term **53**, WP post **1946**, `VERIFIED/publish`, https://blog.rentbikehanoi.com/en/hanoi-street-food-loop-by-scooter/
- Ledger now: **48 VERIFIED / 500 planned**, with **452 not yet authored and verified**. Publication succeeded without manual per-article approval; the main remaining throughput constraint is researching/writing new English manuscripts and safely resolving pending title proposals, not an EN Publisher batch cap.
- Independent monitoring caveat: a prior `SEO Protection` run `39582145731` reported **17 blocking findings** in its own live drift check (its repository guard was clean). This did **not** stop these two EN publications. Investigate separately; do not automatically weaken that guard.
- Before choosing the next EN IDs, re-read `data/en-publication-state.json`, live WordPress, `en/topics.json`, the 478-row title plan, and the latest GitHub Actions logs. Never republish a `VERIFIED` entry.

---

# EN WRITER RELEASE CHECKPOINT — 2026-10-21 · IDs 16, 19, 20 · 3/3 VERIFIED

> **CURRENT EN QA SCORE OVERRIDE (21 Oct 2026):** Owner approved a soft QA threshold of **76/100**: scores **76–100 PASS**, scores **0–75 FAIL**. Hard safety gates (1,600–5,000 words for new/revised manuscripts, legal sources, factual accuracy checks, duplication, categories, slug and WordPress verification) are unchanged. Earlier checkpoint values of QA ≥85 are historical only; `en/publication-policy.json` is authoritative.

> **CURRENT EN POLICY OVERRIDE (21 Oct 2026):** `batch_size` and `max_batches_per_run` were removed from `en/publication-policy.json`, `scripts/en_engine.py` and `.github/workflows/en-publisher.yml`. Every manuscript that passes all English QA/Gates enters the serialized, uncapped publishing queue, with safe checkpoint/continuation near runner time limits. The older three-post approval notes below document history **only**. For live progress consult `data/en-publication-state.json` + live WordPress, not historical numbers.


> Verified release receipt. On resume, read the current ledger and WordPress before trusting these counts; never retry a published or unresolved post.

- Scope: EN only → `https://blog.rentbikehanoi.com/en/`. Repo HEAD before: `26af875`; source commit `9d730ddc57ccdac4804bdee502c9c05e03244b2f`; QA run `39540805667`; publisher run `39540863786` (success).
- **EN-0016** `en/posts/0016.md` · `Fuel in Hanoi: Petrol Stations, Prices and Filling Up a Rental Scooter` · term **55** Rental Tips & Paperwork (parent **48**) · **QA 96/100** (-4 title length), 1,925 words · WordPress **1907**, **VERIFIED/publish**: https://blog.rentbikehanoi.com/en/fuel-in-hanoi-petrol-stations-rental-scooter/
- **EN-0019** `en/posts/0019.md` · `Honda Lead and Vision for Two Riders: Carrying a Passenger and Luggage` · term **65** Honda & Yamaha Comparisons (parent **46**) · **QA 96/100** (-4 title length), 2,021 words · WordPress **1909**, **VERIFIED/publish**: https://blog.rentbikehanoi.com/en/scooter-for-two-riders-and-luggage-hanoi/ — intent kept distinct from EN-0002 (solo Vision vs Air Blade).
- **EN-0020** `en/posts/0020.md` · `Riding in Hanoi Rain: Season, Gear and the Streets That Flood` · term **56** Road Rules & Rider Safety (parent **48**) · **QA 100/100**, 1,979 words · WordPress **1911**, **VERIFIED/publish**: https://blog.rentbikehanoi.com/en/riding-in-hanoi-rain/
- Title decision: original `en/topics.json` titles used verbatim (CSV proposals for 16/19/20 identical to the originals → `SYNCED`).
- Facts/legal basis: Circular 50/2025/TT-BCT (E10 nationwide from 1 Jun 2026, E5 RON 92 to end-2030), Resolution 55/NQ-CP (19 Mar 2026), Decree 70/2025/ND-CP e-invoices; Law 36/2024/QH15 Art. 20 (lights in rain) and Art. 33 (one passenger, bulky items); Decree 168/2024/ND-CP Art. 7 (lights VND 200,000–400,000, umbrella VND 800,000–1,000,000, extra passenger VND 400,000–600,000); Hanoi 2026 flood plan (up to 220 points). No pump prices quoted (weekly-changing; QA amount gate). Fuel rules only from `en/business.json`.
- Local checks before push: `unittest` 130 OK; `en_title_plan.py --check` OK; `en_engine.py --mode qa` 0 errors; sync dry-run 0 errors. Live duplicate preflight done by the publisher (container cannot reach the blog).
- Durable state: `data/en-publication-state.json` = **31 VERIFIED English posts**.
- Next candidates (re-check before claiming): **23, 24, 25** (Tam Dao, Ba Vi, Ha Giang). Policy unchanged: 3 per run.

---

# EN WRITER RELEASE CHECKPOINT — 2026-10-20 (2nd batch) · IDs 13, 14, 15 · 3/3 VERIFIED

> Verified release receipt. On resume, read the current ledger and WordPress before trusting these counts; never retry a published or unresolved post.

- Scope: EN only → `https://blog.rentbikehanoi.com/en/`. Repo HEAD before: `b8b6142`; source commit `e013fe6552bb3b1d1e2a469c9c3525f0c910d29e`; QA run `39483774590`; publisher run `39483890295` (success).
- **EN-0013** `en/posts/0013.md` · `Traffic Fines in Vietnam That Catch Foreign Riders Out` · term **56** Road Rules & Rider Safety (parent **48**) · **QA 100/100**, 2,162 words · WordPress **1901**, **VERIFIED/publish**: https://blog.rentbikehanoi.com/en/traffic-fines-vietnam-foreign-riders/
- **EN-0014** `en/posts/0014.md` · `Drink-Driving Rules for Motorbike Riders in Vietnam` · term **56** (parent **48**) · **QA 100/100**, 1,820 words · WordPress **1903**, **VERIFIED/publish**: https://blog.rentbikehanoi.com/en/drink-driving-rules-motorbike-vietnam/
- **EN-0015** `en/posts/0015.md` · `What to Check Before You Ride Off: A 10-Minute Rental Scooter Inspection` · term **55** Rental Tips & Paperwork (parent **48**) · **QA 96/100** (-4 title length), 1,855 words · WordPress **1905**, **VERIFIED/publish**: https://blog.rentbikehanoi.com/en/rental-scooter-inspection-checklist/ — intent kept distinct from EN-0049 (semi-automatic mechanics).
- Title decision: original `en/topics.json` titles used verbatim; the padded 60–80-char proposals for 13/14 were NOT adopted (CSV note added, must not be applied to these VERIFIED posts); 15 proposal = original → `SYNCED`. CSV rows 13–15 now `VERIFIED` with QA, WP IDs and URLs.
- Legal basis cited: Decree 168/2024/ND-CP (Art. 7, 14, 18), Law 36/2024/QH15, Law 44/2019/QH14 and **Decree 238/2026/ND-CP (amends 168, in force 15 Aug 2026)**; no change found to the motorbike amounts quoted. Official sources: chinhphu.vn, congbao.chinhphu.vn, bocongan.gov.vn, provincial .gov.vn, thuvienphapluat.vn.
- Local checks before push: `unittest` 130 OK; `en_title_plan.py --check` OK; `en_engine.py --mode qa` 0 errors; sync dry-run 0 errors. Live duplicate preflight done by the publisher (container cannot reach the blog).
- **Proposed revision, NOT applied (needs owner approval; VERIFIED posts are immutable):** EN-0013 — (a) drop the uniform-colour description of traffic police; (b) replace "rental shops hand over the registration and insurance documents…" with "ask the shop which documents travel with the bike"; (c) remove "may be settled against the deposit" for camera fines (EN-0005 does not list fines as a deposit deduction); (d) note that a small on-the-spot fine can be collected only against an official receipt. EN-0014 — reword "the passenger is not fined" to "the rider is the one fined". Applying any of these requires a manual, approved WordPress update plus ledger hash reconciliation; the publisher will not update existing posts.
- Durable state: `data/en-publication-state.json` = **28 VERIFIED English posts**.
- Next candidates (re-check before claiming): **16, 19, 20**. Policy unchanged: 3 per run.

---

# EN WRITER RELEASE CHECKPOINT — 20 October 2026 · 3/3 successful

> This is a verified release receipt. If another session resumes, **read the current GitHub ledger and WordPress before using these historic counts**. No automatic retry of published or unresolved posts.

- Scope: `thuexemayhanoi/wp-aiwriter` → `https://blog.rentbikehanoi.com/en/`; original English articles only; existing English term **54** (`Suggested Motorbike Routes`), category hierarchy already registered.
- **EN-0010** `en/posts/0010.md`, title `Long Bien and the Red River: An Easy First Ride Out of Central Hanoi`. Original slug `long-bien-red-river-first-ride`, **QA 96/100**, WordPress **1895**, **VERIFIED/publish**: https://blog.rentbikehanoi.com/en/long-bien-red-river-first-ride/ . Source commit `b1c348e2004233aec3ccf2d1583f26c198588dcf`; QA run `39429629285`; publisher `39429723079`.
- **EN-0011** `en/posts/0011.md`, title `Hanoi to Ha Long Bay by Motorbike: Is It Worth It and How to Do It Safely`. Original slug `hanoi-to-ha-long-bay-by-motorbike`, **QA 96/100**, WordPress **1897**, **VERIFIED/publish**: https://blog.rentbikehanoi.com/en/hanoi-to-ha-long-bay-by-motorbike/ . Source commit `cc73334c2555ad03c6e99ae57b42e28f4af7535b`; QA run `39429982373`; publisher `39430074267`.
- **EN-0012** `en/posts/0012.md`, title `Hanoi to Mai Chau by Motorbike: A Two-Day Ride Through the Hills`. Original slug `hanoi-to-mai-chau-by-motorbike`, **QA 100/100**, WordPress **1899**, **VERIFIED/publish**: https://blog.rentbikehanoi.com/en/hanoi-to-mai-chau-by-motorbike/ . Source commit `6bbeb39535c9fb735b6fb2d46a45859632dc75ad`; QA run `39430342232`; publisher `39430455962`.
- All three: Python test suite and English QA completed successfully on GitHub Actions; zero English QA failures reported, live publisher verified English language, permalink, canonical, categories, readback and registered VI-EN posts. WP Agent independently found the three new articles published with these exact WordPress IDs.
- Durable state: `data/en-publication-state.json` = **25 VERIFIED English posts (22 original + 3 new)** at end of this release. `en/title-plan-478.csv` keeps **478 fixed cohort rows**; IDs 10–12 changed to `VERIFIED/SYNCED` with QA, WP IDs and URLs (commit `463adcac22dcc3553cebed4745f503f190b7146f`). The previously created Google Sheet `EN 478 Titles` was likewise updated at `J2:N4`.
- Safety: no existing VI or EN WordPress URLs, slugs, canonical tags, posts or term IDs modified; no `excel-` prefix introduced. Source titles were unchanged, so no replacement title was applied. No extra posts created beyond these three.
- Next proposed research IDs **13, 14, 15** (fresh WordPress + `en/posts/` + ledger + taxonomy check required before claiming). IDs 13 and 14 concern legal fines and alcohol rules; they need official 2026 legal research, effective dates, and EN QA gate ≥85. Don't start any new batch without current owner authorisation. Policy remains at **3 per run**.
- How to resume: [EN A–Z runbook](EN_478_AI_PLAYBOOK.md) → ledger → GitHub manuscripts → WordPress live → next candidates; NEVER reset a ledger phase.

---

# CURRENT EN 478 AI HANDOFF — 20 October 2026

> **READ FIRST:** [Full A–Z guide](EN_478_AI_PLAYBOOK.md) · [478 planning rows](../en/title-plan-478.csv) · [EN pipeline](EN_PIPELINE.md). This section **supersedes stale historical counts below**. The prior dated report remains for archaeology only; do NOT restart its 2026-10-19 pilot or reinstall old plugins from the obsolete next steps.

## Current verified GitHub baseline (snapshot, not a live counter)

- Repository: `thuexemayhanoi/wp-aiwriter` — English-only post pipeline to `https://blog.rentbikehanoi.com/en/`.
- `en/topics.json` = **500** English ID/title/slug/category mappings; `en/title-plan-478.csv` = exactly **478** not-in-original-ledger candidate IDs, 60–80-character *proposed* titles.
- `data/en-publication-state.json` held **22** `VERIFIED`, `publish` English posts on 2026-10-20; the 22 live EN posts were separately checked using WP Agent. **Never overwrite or republish them.** Subsequent completions MUST be derived from the updated ledger, not this snapshot.
- `en/publication-policy.json` at this checkpoint: `enabled=true`, `mode=batch`, `batch_size=3`, `max_batches_per_run=1`, `min_score=85`, `min_words=1600`. Current policy file always wins over prose.
- 21 EN WordPress category IDs are represented in existing taxonomy. Only **18 of 35 owner thematic groups** have candidates in the old 500-ID matrix; remaining clusters are future research gaps, not automatically publishable topics.
- Original 22 English post URLs and all Vietnamese data must remain unchanged. Public future EN slugs are exact `en/topics.json` slugs **without** Excel/internal numeric prefix.
- **Next safe work:** `python scripts/en_title_plan.py --check` → `python scripts/en_title_plan.py --next 3`; reconcile selected IDs with live WP (including drafts) and `en/posts/`, review proposed titles, sync only approved unpublished/unwritten titles to `en/topics.json`, author original English content, QA and push.
- **Checkpoint status for this documentation pass:** only instructions/documents updated; **no new EN article authored and no WordPress publication claimed here**. Running the automated tests/GitHub Actions must be independently confirmed, never inferred from a commit.

## Append this SMALL checkpoint per writer batch (put the newest ABOVE this template)

```text
UTC date/time:
Repo HEAD before / after:
TARGET=EN ; only blog.rentbikehanoi.com/en/
Selected topic IDs (<=3) + term ID + parent ancestry:
Live WP collision/title/slug/intent check: PASS/BLOCK/NOT CHECKED
Title decision: original/approved proposal; CSV and en/topics.json synchronized?:
EN manuscript paths + research links:
QA command + actual result/score: PASS/FAIL/NOT RUN
Commit SHA + GitHub Actions receipt:
WordPress English post ID, verified URL and exact ledger phase:
Pending risk/error (include POST_INTENT or VERIFY_PENDING; do not clear):
Next safe candidates (re-evaluate from GitHub ledger when resuming):
```

**Recover after a disconnect:** git fetch/check `main` → current EN ledger phases → existing `en/posts/NNNN.md` → this checkpoint → WP live → next 3. Never blindly retry an uncertain WordPress POST, reset ledger phases or trust spreadsheet `writing_status` over WordPress readback. GitHub Actions handles QA/publishing, **not** standalone AI authoring.

---

## ARCHIVED HISTORICAL REPORT — prior session only (obsolete deployment instructions follow)

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
