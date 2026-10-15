# WP AIWriter: editorial & publication contract

**Target WordPress**: https://blog.rentbikehanoi.com
**Source**: the owner's 355-row Excel file, represented losslessly in `data/topics.json` (exact IDs 146–500, exact title and taxonomy).

## Work order
- #146–164 already exist on WordPress; never rewrite or republish these.
- Work strictly on #165–500; writer sessions create **one file per article** as `posts/NNNN.md`.
- Front matter keys: `matrix_id`, `title`, `category_path`, `ready: true`. Title and full category path MUST EXACTLY match the Excel row.
- Write factually careful, original Vietnamese content responding to that topic's search intent. No fabricated data, pricing, specifications, traffic law, reviews or first-hand experience. Use official sources for time-dependent legal facts.
- Run `python scripts/engine.py --mode qa` before pushing. Fix errors, then commit and push promptly.

## Automatic publisher
- GitHub Actions is the **publisher**, **not the AI text generator**. The writer must be an active ChatGPT Work/Claude/Gemini session with GitHub repository write access; without an active writer no new articles are authored. No AI API/key, external reviewer or open-source AI is required for the publishing mechanism.
- Validated articles are published through native WordPress REST in batches of 2. The full category ancestry must match live WordPress; if not, save WordPress **draft** and do not guess.
- Existing titles are skipped (including existing drafts); do not modify existing published URLs, slugs, taxonomy, canonical, themes, plugins, or older articles.
- One-time authentication through encrypted GitHub Actions secrets `WP_USERNAME` and `WP_APPLICATION_PASSWORD`; never print them or store credentials in Git.
- Existing WPVibe connections must remain in place. This repo cannot bypass GitHub Actions secret setup.

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