#!/usr/bin/env python3
"""Read-only / opt-in English title-plan bridge. Never touches WordPress or Vietnamese data."""
from __future__ import annotations
import argparse
import csv
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAN = ROOT / "en" / "title-plan-478.csv"
TOPICS = ROOT / "en" / "topics.json"
LEDGER = ROOT / "data" / "en-publication-state.json"
POSTS = ROOT / "en" / "posts"

def load():
    with PLAN.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    topics = {int(x["id"]): x for x in json.loads(TOPICS.read_text(encoding="utf-8"))}
    ledger = json.loads(LEDGER.read_text(encoding="utf-8")).get("posts", {})
    return rows, topics, ledger

def check():
    rows, topics, ledger = load()
    if len(rows) != 478 or len({x["topic_id"] for x in rows}) != 478:
        raise ValueError("Plan must contain 478 unique stable English topic IDs")
    # The 478 spreadsheet proposals are advisory. Canonical en/topics.json titles are
    # already eligible; validating optional headline lengths must never stall writing.
    for row in rows:
        i = int(row["topic_id"])
        topic = topics.get(i)
        if topic is None:
            raise ValueError(f"Unknown topic ID {i}")
        if row["existing_title_en"] != topic["title"] and (
            row["title_approval"] not in ("APPROVED", "SYNCED")
            or row["planned_title_en"] != topic["title"]
        ):
            raise ValueError(f"Existing English source title drift at {i}; investigate before writing")
        if str(topic["category_id"]) != row["category_id"] or topic["slug"] != row["slug_locked"]:
            raise ValueError(f"Source category/slug drift at {i}; stop")
        # An imperfect or duplicated OPTIONAL proposal does not block canonical
        # manuscript creation. apply_approved() validates proposals that are used.
        if str(i) in ledger:
            # A previously queued post may have published since the plan was generated.
            # Do not rewrite, remove or re-publish it.
            if ledger[str(i)].get("phase") not in ("VERIFIED", "DRAFT_CREATED", "REGISTERED", "VERIFY_PENDING", "POST_INTENT", "REGISTER_FAILED"):
                raise ValueError(f"Unrecognised publication phase at {i}")
    return rows, topics, ledger

def pending(limit=10):
    if not 1 <= limit <= 10:
        raise ValueError("English writer preview limit must be 1 to 10")
    rows, topics, ledger = check()
    result = []
    for row in rows:
        i = int(row["topic_id"])
        if str(i) in ledger or (POSTS / f"{i:04}.md").exists():
            continue
        result.append({"topic_id": i, "category_id": int(row["category_id"]),
                       "category_en": row["category_en"], "subject_cluster_en": row["subject_cluster_en"],
                       "source_title_en": row["existing_title_en"],
                       "proposed_title_en": row["planned_title_en"], "locked_slug": row["slug_locked"],
                       "title_approval": row["title_approval"],
                       "canonical_title": topics[i]["title"],
                       "canonical_ready": True,
                       "proposal_optional": True,
                       "status": "READY_TO_WRITE_CANONICAL"})
        if len(result) >= limit:
            break
    return result

def apply_approved():
    """Opt-in. Change only un-authored, un-published EN topic titles explicitly marked APPROVED."""
    rows, topics, ledger = check()
    data = json.loads(TOPICS.read_text(encoding="utf-8"))
    index = {int(x["id"]): x for x in data}
    changed = []
    for row in rows:
        if row["title_approval"] != "APPROVED":
            continue
        i = int(row["topic_id"])
        if str(i) in ledger or (POSTS / f"{i:04}.md").exists():
            raise ValueError(f"Refuse change to authored / ledger topic ID {i}")
        candidate = row["planned_title_en"].strip()
        if not 60 <= len(candidate) <= 80:
            raise ValueError(f"Approved title at {i} needs 60–80 characters")
        if index[i]["title"] == candidate:
            continue  # An earlier approved batch was already synced; keep it unchanged.
        if index[i]["title"] != row["existing_title_en"]:
            raise ValueError(f"Source title drift at {i}")
        index[i]["title"] = row["planned_title_en"]
        changed.append(i)
    if changed:
        TOPICS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--next", type=int, metavar="N")
    parser.add_argument("--apply-approved", action="store_true")
    args = parser.parse_args()
    rows, _, ledger = check()
    if args.apply_approved:
        print(json.dumps({"synchronised_en_titles": apply_approved()}))
    elif args.next is not None:
        print(json.dumps({"english_only": True, "queue": pending(args.next)}, ensure_ascii=False, indent=2))
    else:
        count = sum(1 for r in rows if str(r["topic_id"]) in ledger)
        print(json.dumps({"english_only": True, "plan_rows": len(rows), "covered_by_ledger": count,
                          "unsynced_title_candidates": sum(r["planned_title_en"] != r["existing_title_en"] for r in rows),
                          "ready_for_writing": "YES_WITH_CANONICAL_EN_TOPICS_TITLE; proposals optional",
                          "proposal_review_is_not_a_blocker": True,
                          "source": str(PLAN.relative_to(ROOT))}))

if __name__ == "__main__":
    main()
