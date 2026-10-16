# GitHub → WordPress AI Writer

Target: **https://blog.rentbikehanoi.com/**

This repository preserves the user's Excel SEO topic list **exactly** in [data/topics.json](data/topics.json) (355 articles, #146–500). WordPress already has #146–164. The remaining work is #165–500 (336 articles).

## Components
- `data/topics.json`: verified, original titles and hierarchical categories (not a new SEO Matrix).
- `AGENTS.md`: guide for **active** external AI writers (ChatGPT Work / Claude / Gemini) to author one Markdown file per title.
- `posts/NNNN.md`: authored articles with exact Excel identity; see `docs/WRITER_CHECKPOINT.md` for verified current progress.
- `scripts/engine.py`: QA, category ancestry match, duplicate guard, Markdown conversion and first-party WordPress REST publisher.
- `.github/workflows/wordpress-publisher.yml`: runs on push, manual dispatch and hourly; publishes at most **2 new posts per run**.

## One-time connection to WordPress (needed before actual auto-publication)
1. On WordPress, log in as an account authorized to publish and open **Users → Profile → Application Passwords**. Create a dedicated Application Password for `wp-aiwriter-github`.
2. In this GitHub repository open **[Actions secrets](https://github.com/thuexemayhanoi/wp-aiwriter/settings/secrets/actions)** and create **`WP_USERNAME`** (WordPress login) and **`WP_APPLICATION_PASSWORD`** (the generated Application Password). Never paste these into chat, Markdown or public files.
3. Open **[Excel Matrix WP Publisher](https://github.com/thuexemayhanoi/wp-aiwriter/actions/workflows/wordpress-publisher.yml)** and run `live=true`, `batch_size=2` (or simply push a new validated article). If credentials have not been configured, a live run **fails visibly as BLOCKED and does not post**. A deliberate manual `live=false` run remains a dry run.

## Publication policy
- Exact Excel title + full hierarchy exists on WordPress + QA PASS → publish and assign correct leaf category.
- Missing/mismatched category path → WordPress draft, **never force a guessed category**.
- An existing WordPress article with the same title → skip; no overwrites or mass-SEO URL changes.
- With no ready article, GitHub Actions does not generate prose. GitHub Actions is a publisher and deterministic QA runner; content generation requires an **active external AI writer session**, not a background LLM that has not been connected.

Run QA manually: `python scripts/engine.py --mode qa`.

## Verified publisher behavior (2026-10-16)

- Missing authentication is a visible **BLOCKED / failed live run**, never a green dry run. Manual `live=false` remains available.
- The complete category tree and post inventory are paginated. An exact, unique full category ancestry permits publication; missing/ambiguous ancestry creates a draft and records the reason.
- New content from #172 onward must pass a 1,000-word mechanical floor, exact metadata, structure, placeholder, repeated-paragraph and near-duplicate-content checks. These checks supplement the active writer's factual and search-intent checks; they do not prove content quality automatically.
- Markdown tables, emphasis and HTTPS links are rendered by the small Python-Markdown package. Actions does not author articles.
- At most two new article attempts occur per run. A failed article does not prevent another valid article being processed. Remaining ready articles trigger another serialized run even if one attempted article failed.
- `data/publication-state.json` is a durable write-ahead publication ledger, not a replacement Matrix. The original `data/topics.json` is protected by its original SHA-256 checksum.
- Before a POST, the ledger is committed to latest main. After a POST, the WordPress ID is checkpointed. Readback checks the authenticated post, public REST content and public permalink. A successful HTTP response alone is insufficient.
- A timed-out POST is **not blindly retried**. Later runs reconcile the exact title/slug and embedded matrix marker. An unresolved intent without a matching post remains blocked until investigated. Existing posts and drafts are always preserved; this publisher has no update/delete path.
- Run receipts appear in the Actions summary and downloadable `publication-receipt-*` artifact, including failures. Count `VERIFIED` publish receipts separately from authored GitHub files.
- Only the publisher uses WordPress Application Password secrets. No AI provider credentials or WPVibe/WP Agent calls are used.

Validation: `python -m pip install -r requirements.txt`, `python -m unittest discover -s tests -v`, then `python scripts/engine.py --mode qa`.
