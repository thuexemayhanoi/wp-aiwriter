"""The optional 478 Excel headline proposals never block canonical EN manuscripts."""
import csv
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import en_title_plan


class OptionalEnglishProposals(unittest.TestCase):
    def test_read_only_queue_is_canonical_ready_without_title_sync(self):
        rows, topics, ledger = en_title_plan.check()
        self.assertEqual(len(rows), 478)
        queue = en_title_plan.pending(10)
        self.assertTrue(queue)
        self.assertLessEqual(len(queue), 10)
        for row in queue:
            self.assertTrue(row["canonical_ready"])
            self.assertTrue(row["proposal_optional"])
            self.assertEqual(row["canonical_title"], topics[row["topic_id"]]["title"])
            self.assertNotIn(str(row["topic_id"]), ledger)
            self.assertFalse((en_title_plan.POSTS / f'{row["topic_id"]:04d}.md').exists())

    def test_imperfect_unapproved_proposals_cannot_block_source_titles(self):
        with tempfile.TemporaryDirectory() as tmp:
            replacement = pathlib.Path(tmp) / "title-plan.csv"
            with en_title_plan.PLAN.open(encoding="utf-8-sig", newline="") as src:
                original = list(csv.DictReader(src))
            original[0]["planned_title_en"] = "Short suggestion!"
            original[0]["title_approval"] = "NEEDS_EDITORIAL_REVIEW"
            with replacement.open("w", encoding="utf-8", newline="") as out:
                writer = csv.DictWriter(out, fieldnames=original[0].keys())
                writer.writeheader()
                writer.writerows(original)
            with patch.object(en_title_plan, "PLAN", replacement):
                rows, topics, _ = en_title_plan.check()
                self.assertEqual(len(rows), 478)
                self.assertEqual(topics[int(rows[0]["topic_id"])]["title"],
                                 json.loads(en_title_plan.TOPICS.read_text(encoding="utf-8"))[int(rows[0]["topic_id"]) - 1]["title"])

    def test_explicit_title_approval_still_rejects_malformed_proposal(self):
        with tempfile.TemporaryDirectory() as tmp:
            replacement = pathlib.Path(tmp) / "title-plan.csv"
            with en_title_plan.PLAN.open(encoding="utf-8-sig", newline="") as src:
                original = list(csv.DictReader(src))
            candidate = next(r for r in original if
                             str(r["topic_id"]) not in json.loads(en_title_plan.LEDGER.read_text(encoding="utf-8"))["posts"]
                             and not (en_title_plan.POSTS / f'{int(r["topic_id"]):04d}.md').exists())
            candidate["planned_title_en"] = "Too short"
            candidate["title_approval"] = "APPROVED"
            with replacement.open("w", encoding="utf-8", newline="") as out:
                writer = csv.DictWriter(out, fieldnames=original[0].keys())
                writer.writeheader()
                writer.writerows(original)
            with patch.object(en_title_plan, "PLAN", replacement):
                with self.assertRaisesRegex(ValueError, "needs 60"):
                    en_title_plan.apply_approved()


if __name__ == "__main__":
    unittest.main()
