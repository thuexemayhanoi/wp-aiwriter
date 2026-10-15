# GitHub → WordPress AI Writer

Target: **https://blog.rentbikehanoi.com/**

This repository preserves the user's Excel SEO topic list **exactly** in [data/topics.json](data/topics.json) (355 articles, #146–500). WordPress already has #146–164. The remaining work is #165–500 (336 articles).

## Components
- `data/topics.json`: verified, original titles and hierarchical categories (not a new SEO Matrix).
- `AGENTS.md`: guide for **active** external AI writers (ChatGPT Work / Claude / Gemini) to author one Markdown file per title.
- `posts/0165.md`, `posts/0166.md`: first two articles ready to transfer.
- `scripts/engine.py`: QA, category ancestry match, duplicate guard, Markdown conversion and first-party WordPress REST publisher.
- `.github/workflows/wordpress-publisher.yml`: runs on push, manual dispatch and hourly; publishes at most **2 new posts per run**.

## One-time connection to WordPress (needed before actual auto-publication)
1. On WordPress, log in as an account authorized to publish and open **Users → Profile → Application Passwords**. Create a dedicated Application Password for `wp-aiwriter-github`.
2. In this GitHub repository open **[Actions secrets](https://github.com/thuexemayhanoi/wp-aiwriter/settings/secrets/actions)** and create **`WP_USERNAME`** (WordPress login) and **`WP_APPLICATION_PASSWORD`** (the generated Application Password). Never paste these into chat, Markdown or public files.
3. Open **[Excel Matrix WP Publisher](https://github.com/thuexemayhanoi/wp-aiwriter/actions/workflows/wordpress-publisher.yml)** and run `live=true`, `batch_size=2` (or simply push a new validated article). If credentials have not been configured, the workflow **dry-runs and does not post**.

## Publication policy
- Exact Excel title + full hierarchy exists on WordPress + QA PASS → publish and assign correct leaf category.
- Missing/mismatched category path → WordPress draft, **never force a guessed category**.
- An existing WordPress article with the same title → skip; no overwrites or mass-SEO URL changes.
- With no ready article, GitHub Actions does not generate prose. GitHub Actions is a publisher and deterministic QA runner; content generation requires an **active external AI writer session**, not a background LLM that has not been connected.

Run QA manually: `python scripts/engine.py --mode qa`.
