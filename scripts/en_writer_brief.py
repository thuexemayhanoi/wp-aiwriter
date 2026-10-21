#!/usr/bin/env python3
"""Read-only, English-only brief for up to ten unclaimed WP-AIWriter topics.

No API calls, WordPress writes, article generation, title approval or file mutation.
This packet is a *research plan*, not QA PASS or a publishing authorisation.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re

import en_title_plan

ROOT = pathlib.Path(__file__).resolve().parents[1]
NAV = ROOT / "data" / "navigation-map.json"
BUSINESS = ROOT / "en" / "business.json"
POLICY = ROOT / "en" / "publication-policy.json"
EN_URL = "https://blog.rentbikehanoi.com/en/"


def category_chain(term_id, categories):
    """Return root-to-leaf EN term labels from a read-only taxonomy snapshot."""
    by_id = {int(t["term_id"]): t for t in categories if t.get("language") == "en"}
    chain, visited = [], set()
    current = int(term_id)
    while current:
        if current in visited:
            raise ValueError(f"English taxonomy cycle at {current}")
        visited.add(current)
        term = by_id.get(current)
        if not term:
            raise ValueError(f"English term #{current} missing from snapshot; inspect live WP")
        chain.append({"term_id": current, "name": term["name"]})
        current = int(term.get("parent_term_id") or 0)
    return list(reversed(chain))


def build_packet(limit=10):
    if not 1 <= limit <= 10:
        raise ValueError("One editorial batch must contain 1 to 10 topics")
    rows, topics, ledger = en_title_plan.check()
    nav = json.loads(NAV.read_text(encoding="utf-8"))
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    business = json.loads(BUSINESS.read_text(encoding="utf-8"))
    selected = en_title_plan.pending(limit)
    fixed_ids = {int(r["topic_id"]) for r in rows}
    if any(item["topic_id"] not in fixed_ids for item in selected):
        raise ValueError("An item is outside the fixed 478-topic English cohort")
    published = sum(1 for p in ledger.values() if p.get("phase") == "VERIFIED" and p.get("status") == "publish")
    packet = {
        "mode": "READ_ONLY_EN_EDITORIAL_BRIEF",
        "repo": "thuexemayhanoi/wp-aiwriter",
        "target_site": EN_URL,
        "live_wordpress_verified": False,
        "note": "Canonical en/topics.json titles are ready for writing. GitHub EN Publisher performs live WordPress duplicate, route, taxonomy and readback checks before publication.",
        "snapshot_date": nav.get("snapshot_date", "unknown"),
        "campaign": {"original_topic_ids": 500, "original_cohort": 478,
                     "verified_by_local_ledger": published,
                     "remaining_in_original_cohort_by_local_ledger": sum(
                         1 for r in rows if str(r["topic_id"]) not in ledger)},
        "quality_gate": {"minimum_score": policy["min_score"], "minimum_words": policy["min_words"],
                         "maximum_words": 5000, "continuous_publishing": True,
                         "cannot_reduce_QA": True},
        "business": {"name_en": business["name_en"], "source": "en/business.json",
                     "english_home": business["home_en"]},
        "topics": [],
    }
    for item in selected:
        topic_id = item["topic_id"]
        source = topics[topic_id]
        term_id = int(source["category_id"])
        chain = category_chain(term_id, nav["categories"])
        text = " ".join((source["title"], source.get("intent", "")))
        legal_hint = bool(re.search(r"\b(law|licen[cs]e|fine|penalt|alcohol|traffic rule|drink.driv|decree|regulation|insurance)\b", text, re.I))
        legal_hard_gate = term_id in set(policy["legal_categories"])
        packet["topics"].append({
            "topic_id": topic_id,
            "source_title_en": source["title"],
            "proposed_title_en": item["proposed_title_en"],
            "title_approval": item["title_approval"],
            "canonical_title_status": "READY_TO_WRITE",
            "proposal_review_required": False,
            "write_with_title": source["title"],
            "article_path": f"en/posts/{topic_id:04d}.md",
            "slug_locked": source["slug"],
            "expected_url": EN_URL + source["slug"] + "/",
            "category_id": term_id,
            "category_ancestors_from_snapshot": chain,
            "search_intent": source.get("intent") or item["source_title_en"],
            "keywords_from_source": source.get("keywords") or [],
            "editorial_topic_group_not_taxonomy": item["subject_cluster_en"],
            "research_priority": ("OFFICIAL_LEGAL_SOURCES_AND_EFFECTIVE_DATES" if legal_hard_gate or legal_hint
                                   else "FIRST_PARTY_AND_RELIABLE_SOURCES"),
            "legal_qa_hard_gate": legal_hard_gate,
            "blockers_before_write": [
                "Skip claimed or ledgered IDs; refresh the packet before another writing batch",
                "Research topic accuracy and distinct search intent; keep canonical title, slug and category",
                "Do not write if actual WordPress taxonomy conflict has been discovered; publisher verifies live",
            ],
            "fixed_metadata": {"en_id": topic_id, "slug": source["slug"], "category_id": term_id},
        })
    return packet


def markdown(packet):
    q = packet["quality_gate"]
    lines = [
        "# EN writer packet — next " + str(len(packet["topics"])) + " candidates",
        "",
        "**READ ONLY — does not claim a row, research, QA or publish.**",
        "**Canonical en/topics.json title is READY now; Excel proposal review is OPTIONAL.**",
        "**Live WordPress duplicate, taxonomy, URL and readback checks run in the EN Publisher.**",
        "",
        f"- Repository: `{packet['repo']}` · destination: `{packet['target_site']}`",
        f"- Ledger: {packet['campaign']['verified_by_local_ledger']} EN VERIFIED; {packet['campaign']['remaining_in_original_cohort_by_local_ledger']} originally planned EN IDs not represented in the local ledger.",
        f"- Unchanged hard gates: QA >= {q['minimum_score']}; {q['minimum_words']}–{q['maximum_words']} English words; EN publisher drains every QA-passing manuscript without a count cap.",
        "- Fast EN instructions: docs/EN_FAST_WRITER.md; consult full mapping docs only for exceptions.",
        "- Never turn spreadsheet row numbers or `excel-` into WordPress slugs. Never change the VI pipeline.",
        "",
    ]
    if not packet["topics"]:
        lines.append("No EN candidates available without a ledger/manuscript entry; inspect GitHub and WP before continuing.")
    for topic in packet["topics"]:
        labels = " > ".join(f"{x['name']} (#{x['term_id']})" for x in topic["category_ancestors_from_snapshot"])
        lines += [
            f"## EN-{topic['topic_id']:04d}: {topic['source_title_en']}",
            "",
            f"- Canonical title for manuscript NOW: **{topic['write_with_title']}**",
            f"- Optional Excel headline suggestion: {topic['proposed_title_en']} (proposal status: {topic['title_approval']}; IGNORE unless changing canonical title).",
            "- CAN WRITE NOW using canonical title. No editorial approval/synchronization required for unchanged title.",
            f"- Exact GitHub file: `{topic['article_path']}`",
            f"- Locked slug: `{topic['slug_locked']}`",
            f"- Expected permalink: {topic['expected_url']}",
            f"- WordPress taxonomy from snapshot: {labels}",
            f"- Distinct search intent: {topic['search_intent']}",
            f"- Keywords in original source: {', '.join(topic['keywords_from_source']) or '(research required)'}",
            f"- Source research priority: **{topic['research_priority']}**",
            "",
            "**Before writing:** Confirm ID remains unclaimed in GitHub; research factual/legal claims using reliable sources and `en/business.json`. EN Publisher separately checks live WordPress before creating anything.",
            "",
        ]
    lines += [
        "## Publish-only-after-QA procedure",
        "",
        "1. Use the existing `en/topics.json` title/slug/category without approval. Optional headline changes are a separate, explicitly reviewed process.",
        "2. Write 1,600–5,000 original English words with strong headings, FAQ, sources and genuine EN internal links. Do not copy Vietnamese articles.",
        "3. Run `python scripts/en_engine.py --mode qa` on manuscripts before push. GitHub Actions runs title-plan validation, regression tests and the live Publisher automatically after a green push.",
        f"4. QA >= {q['minimum_score']} is necessary but not sufficient: verify no duplicates, lawful routes, accurate dated facts, category and WordPress readiness.",
        "5. Push reviewed files to GitHub; trust `data/en-publication-state.json` VERIFIED + WP readback before marking published. Do not retry uncertain POSTs.",
        "6. Confirm WordPress URLs from the publisher ledger, then obtain the next unclaimed packet. Add a short checkpoint after meaningful completed work, not after every single article.",
        "",
    ]
    return "\n".join(lines)


def compact(packet):
    """Token-efficient canonical writing queue; no optional headline review steps."""
    lines = [
        f"# EN READY: {len(packet['topics'])} candidates | ledger VERIFIED: {packet['campaign']['verified_by_local_ledger']}",
        "Use en/topics.json titles EXACTLY; QA >=76 + hard gates; publish via existing EN Actions.",
        "ID | CANONICAL TITLE | TERM | SLUG | LEGAL RESEARCH",
    ]
    for t in packet["topics"]:
        lines.append(
            f"{t['topic_id']:04d} | {t['write_with_title']} | {t['category_id']} "
            f"| {t['slug_locked']} | {t['research_priority']}"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Produce an English-only, read-only next-batch writer brief")
    parser.add_argument("--limit", type=int, default=10, help="1–10 read-only research candidates per packet; NOT a publishing limit")
    parser.add_argument("--format", choices=["markdown", "json", "compact"], default="compact")
    args = parser.parse_args()
    packet = build_packet(args.limit)
    print(json.dumps(packet, ensure_ascii=False, indent=2) if args.format == "json" else
          markdown(packet) if args.format == "markdown" else compact(packet))


if __name__ == "__main__":
    main()
