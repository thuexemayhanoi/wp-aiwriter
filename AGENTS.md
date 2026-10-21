# BẮT BUỘC: ĐỌC BẢN ĐỒ MENU & TAXONOMY TRƯỚC MỌI BÀI VI/EN

> **LUỒNG EN — BẮT BUỘC CHO MỌI AI (478 TIÊU ĐỀ, 20/10/2026):** Đọc [`docs/EN_478_AI_PLAYBOOK.md`](docs/EN_478_AI_PLAYBOOK.md) trước khi chọn/claim/viết bài EN. Đọc cả `en/title-plan-478.csv` → `en/topics.json` → `en/publication-policy.json` → `data/en-publication-state.json` → `docs/EN_WRITER_CHECKPOINT.md` → kiểm tra WordPress live. CSV/Excel là kế hoạch tiêu đề 60–80 ký tự, **không phải lệnh xuất bản và không tự đồng bộ từ Google Sheet**; `en/topics.json` mới là nguồn metadata cho `en/posts/NNNN.md`. 22 bài EN đã VERIFIED lúc chốt mốc phải bảo vệ; 478 là danh sách cố định, phải trừ từng ID hiện đã xuất bản khi làm tiếp. Chỉ viết EN gốc 1.600–5.000 từ, QA ≥85, xuất bản EN liên tục không giới hạn số bài theo batch (giữ thời hạn runner và checkpoint), không thêm `excel-`/ID vào slug, không sửa bất kỳ nội dung hay pipeline VI. Mất mạng: đọc ledger, bài viết, commit/checkpoint, làm tiếp từ ID an toàn; không POST trùng. **Không được bỏ qua bản đồ menu/taxonomy bắt buộc bên dưới.**



> **Mọi phiên ChatGPT, Claude, Gemini, GitHub Writer và agent mới phải đọc đủ `docs/MENU_TAXONOMY_MAP_VI_EN.md` + `data/navigation-map.json` TRƯỚC KHI nghiên cứu, viết, sửa hoặc publish.** Đây là bản đồ live WordPress xác minh ngày 20/10/2026 (43 Term, 37 Page; menu VI primary #26/footer #29; EN primary #57/footer #58). Phân biệt **Term ID / Page ID / Menu Item ID**; không dùng nhãn menu để đoán danh mục đăng bài.
>
> **Luồng VI:** đối chiếu từng hàng bất biến trong `data/topics.json`, dùng `category_path` cha/con đầy đủ, không đổi URL/slug/canonical. **Luồng EN:** đối chiếu `en/topics.json` và `en/publication-policy.json`, dùng đúng `category_id`, bài mới/sửa 1.600–5.000 từ, QA ≥85, EN Publisher tự xuất bản tất cả bài đủ QA/Gate, không giới hạn số bài/lượt và không cần duyệt từng đợt; `en_writer_brief.py --limit 3` chỉ là gói nghiên cứu. Đọc ledger tương ứng và kiểm tra WordPress trước khi báo VERIFIED. Không dùng dữ liệu kinh doanh Nguyễn Tú cho Nguyễn Hà, không tự tạo category mới, không đăng khi taxonomy live khác bản đồ chụp.
>
> **Hệ quy chiếu:** website `https://blog.rentbikehanoi.com`; hệ VI/EN native trên `/en/`. Snapshot JSON chỉ dùng tham chiếu; **WordPress live là nguồn chuẩn**, cần cập nhật snapshot qua PR sau khi chủ website phê duyệt thay đổi cấu trúc. **Không tự sửa WordPress để làm giống bản đồ.**

---

> **TĂNG TỐC EN, KHÔNG HẠ QA:** Chạy `python scripts/en_writer_brief.py --limit 3` để in sẵn hồ sơ 3 ID còn chưa có bài/ledger; đối chiếu WordPress live trước khi viết. Đây chỉ là bản đọc dữ liệu, KHÔNG claim, KHÔNG duyệt title, KHÔNG chạy QA, KHÔNG đăng. `--format json` cho AI đọc tự động. Bắt buộc QA ≥85, 1.600–5.000 từ, đúng URL/slug/category và nguồn luật chính thức như trước.

# WP AIWriter: editorial & publication contract

**Target WordPress**: https://blog.rentbikehanoi.com
**Source**: the owner's 355-row Excel file, represented losslessly in `data/topics.json` (exact IDs 146–500, exact title and taxonomy).

## Work order
- #146–164 already exist on WordPress; never rewrite or republish these.
- Work strictly on #165–500; writer sessions create **one file per article** as `posts/NNNN.md`.
- Front matter keys: `matrix_id`, `title`, `category_path`, `ready: true`. Title and full category path MUST EXACTLY match the Excel row.
- Write factually careful, original Vietnamese content responding to that topic's search intent. No fabricated data, pricing, specifications, traffic law, reviews or first-hand experience. Use official sources for time-dependent legal facts.
- Run `python scripts/engine.py --mode qa` before pushing. Fix errors, then commit and push promptly.

## QA-gated, immediate WordPress auto-publisher

- **Writer:** ChatGPT Work, Claude, Gemini or a person actively authors exact Excel `posts/NNNN.md` and pushes to `main`; GitHub Actions never generates prose. No AI API keys or external reviewers needed.
- **Publish trigger:** a green **push-triggered** `WP AIWriter QA (No WordPress Writes)` run automatically triggers the secret-bearing `Excel Matrix WP Publisher` by `workflow_run`. The Publisher re-runs tests and entire Markdown QA on latest main under an exclusive concurrency lock. **No clock delay, hourly timer or manual Run button** is required.
- **Batch drain:** WordPress REST publishing runs in repeated iterations of up to **5 QA-ready articles**, without sleep, until none remain in the **owner-approved active Excel category**. The finite safety cap and GitHub job runtime are failure protections, not a waiting period.
- **Strict safety:** exact Excel title and category ancestry, skip existing titles/URLs including drafts, no touching WordPress Trash, no overwrites; missing/ambiguous WordPress category → draft, verify readback after every POST; unknown POST outcomes are never retried blindly. A new category still requires owner approval.
- **Manual diagnosis:** `workflow_dispatch` remains available with `live=false` default preview; `live=true` is a deliberate manual run.

## Article metadata example
```
---
matrix_id: 165
title: SYM có những mẫu xe nào đáng chú ý cho nhu cầu đi lại cơ bản?
category_path: Cẩm nang > Hãng xe > Hãng xe máy
ready: true
---

## Direct answer
...
## Practical analysis
...
## Final notes
...
```

Each article needs at least 350 words and 3 level-2 sections. This is only a mechanical minimum; writers must provide actual substance. For SEO, improve contents with supporting images, authoritative references, links and structured data later through separate QA-reviewed changes.
## Continuation and stronger QA
- User's current target is 1,000–1,800 useful Vietnamese words per new article when the subject supports it. The publisher enforces at least 1,000 words for #172 onward; the earlier seven authored files are preserved.
- Always select the next smallest IDs without complete authored files. Push each validated writing pair immediately, and successful push QA now authorizes automatic publishing in the selected category. Do not mark an article published merely because it was pushed.
- Install `requirements.txt` before QA. Use `python -m unittest discover -s tests -v` after modifying publisher code.
- Do not edit `data/topics.json`: its original bytes are checksum protected.
- Inspect `data/publication-state.json` and Actions receipts on resume. Never clear a POST_INTENT/VERIFY_PENDING record to make the publisher retry. Reconcile any uncertain WordPress write first.
- Exact-title/slug checks are mechanical. The active writer must additionally compare search intent against the full Excel list and live WordPress inventory before writing. Do not invent fresh topics or a replacement Matrix.
- Record session checkpoint in `docs/WRITER_CHECKPOINT.md`, including the content commit, QA, verified publication counts and the next two IDs. Secrets must never appear there.

## Automatic publication safeguards

- Every push QA PASS triggers automatic Publisher; QA FAIL means **no WordPress writes**. Keep category switching owner-approved.
- Each loop iteration attempts at most five newly authored posts; serialized lock, no cooldown, no cron, finite safety cap, remote receipts and WordPress verification.
- Category mismatch → WordPress draft; existing titles or duplicate groups → skip/report; no update/delete/restore; keep Git it Write disabled.
- The owner-authorized change only removes per-batch manual activation and time waiting; it does not grant permission to alter prior URLs, titles, taxonomy or canonicals.

## SEO systems (read-only, GitHub only)
- `docs/SEO_SYSTEMS.md` documents **SEO Audit**, **Internal Link Matrix** and **SEO Protection** (`scripts/seo_audit.py`, `scripts/link_matrix.py`, `scripts/seo_protection.py`). They never write to WordPress and need no WPVibe/WP Agent.
- Never edit, rename or delete the Markdown of an already published post: `python scripts/seo_protection.py --mode repo` flags `published_source_edited`. Link proposals in `data/seo/link-plan.json` are applied only through separate, QA-reviewed changes that keep published URLs, slugs and canonicals intact.
- Intentional changes to a published page are approved with `seo_protection.py --mode baseline --accept ID --reason "..."` (recorded in `data/seo/protection-allowlist.json`).

## Production runbook and current category

Full operational instructions: `docs/PUBLISHER_OPERATIONS.md`.

- **Single point of control:** `data/publication-policy.json` → `active_category` (must match Excel parent/child path exactly). Engine derives start/end/next category from original `data/topics.json`.
- **Currently approved:** `Cẩm nang > Ứng dụng > App xe máy` (#236–260; WordPress term 17); #236–243 are verified published. Check `docs/WRITER_CHECKPOINT.md` for next ID and `data/publication-state.json` for WP IDs.
- **Completed previous group:** #146–200, 55/55 published, WordPress taxonomy corrected for legacy WP 814, 815, 823 to child category 20. Do not republish.
- **Completion alert:** Actions summary + deduplicated GitHub Issue when all rows of the active category are published in the exact WordPress taxonomy; keep the next group blocked until approved.
- **QA automation:** `WP AIWriter QA (No WordPress Writes)` automatically tests code, all authored posts and the active-category queue on changes. It never publishes.
- **WordPress publishing:** after green push QA, `Excel Matrix WP Publisher` starts automatically, serializes up-to-5 batches and drains the ready queue without cooldown. Full taxonomy match → publish; missing/ambiguous → draft + report.
- **Never touch WordPress Trash.** Owner handles it. No auto-delete, restore, or forced overwrites. Duplicates are skipped and reported. Keep the old Git it Write sync inactive; do not run multiple publishers.
- **Old ledger repairs:** Excel #169 currently WP 880; #173 WP 838, both VERIFIED. Preserve their URLs; do not recreate from scratch.
- Source writer is separate. GitHub Actions does not generate missing article prose by itself. Writers should follow `docs/PUBLISHER_OPERATIONS.md` and update `docs/WRITER_CHECKPOINT.md` after small pushes.
