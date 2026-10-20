"""Regression contract for the 500-topic English expansion.

No WordPress or AI services required. Topic planning is not manuscript publication.
"""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import en_engine


class En500TopicPlan(unittest.TestCase):
    def test_exact_500_sequential_ids_and_unique_slugs(self):
        rows = json.loads((ROOT / "en" / "topics.json").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 500)
        self.assertEqual([row["id"] for row in rows], list(range(1, 501)))
        self.assertEqual(len({row["slug"] for row in rows}), 500)
        self.assertEqual(len(en_engine.load_topics()), 500)

    def test_all_candidates_are_in_registered_leaf_categories(self):
        policy = en_engine.load_policy()
        rows = json.loads((ROOT / "en" / "topics.json").read_text(encoding="utf-8"))
        allowed = set(policy["category_ids"]["leaves"])
        for row in rows:
            self.assertIn(row["category_id"], allowed)
            self.assertTrue(row["title"].strip())
            self.assertTrue(row["slug"].strip())
        for term_id in allowed:
            self.assertGreaterEqual(sum(x["category_id"] == term_id for x in rows), 50)

    def test_expansion_is_research_backlog_not_marked_published(self):
        rows = json.loads((ROOT / "en" / "topics.json").read_text(encoding="utf-8"))
        self.assertEqual(len(rows[:48]), 48)
        for row in rows[48:]:
            self.assertEqual(row["research_status"], "candidate")
            self.assertEqual(row["keywords"], [])
        # Published is a WordPress/ledger fact, never inferred from topic count.
        self.assertFalse(any("published" in row for row in rows[48:]))


if __name__ == "__main__":
    unittest.main()
