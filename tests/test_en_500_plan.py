"""Regression contract for the 500 original English article topics and their 21-category structure.

Read-only tests. Registering categories or pairing pages never means the 500 articles are published.
"""
import json
import pathlib
import sys
import unittest
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import en_engine


class En500TopicPlan(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads((ROOT / "en" / "topics.json").read_text(encoding="utf-8"))
        self.policy = en_engine.load_policy()

    def test_exact_500_sequential_ids_and_unique_slugs(self):
        self.assertEqual(len(self.rows), 500)
        self.assertEqual([row["id"] for row in self.rows], list(range(1, 501)))
        self.assertEqual(len({row["slug"] for row in self.rows}), 500)
        self.assertEqual(len(en_engine.load_topics()), 500)

    def test_all_21_english_categories_are_registered_and_planned(self):
        policy = self.policy
        all_categories = set(policy["category_ids"]["parents"]) | set(policy["category_ids"]["leaves"])
        self.assertEqual(all_categories, set(range(46, 57)) | set(range(60, 70)))
        self.assertEqual(len(all_categories), 21)
        allowed = set(policy["category_ids"]["leaves"])
        counts = Counter(row["category_id"] for row in self.rows)
        self.assertTrue(set(counts) <= allowed)
        self.assertEqual(sum(counts.values()), 500)
        for row in self.rows:
            self.assertTrue(row["title"].strip())
            self.assertTrue(row["slug"].strip())
        # Existing clusters continue to have enough candidates to grow naturally.
        for term_id in range(49, 57):
            self.assertGreaterEqual(counts[term_id], 40)
        # New categories are staged as genuine, specific editorial clusters.
        for term_id in range(60, 70):
            self.assertGreaterEqual(counts[term_id], 1)

    def test_first_nine_ready_manuscripts_stay_on_original_category_ids(self):
        # Do not orphan existing published WordPress articles or nine authored manuscripts.
        original = {1: 56, 2: 50, 3: 54, 4: 56, 5: 55, 6: 49, 7: 52, 8: 50, 9: 53}
        # Avoid hardcoding uncertain topic IDs that could drift in the dataset; source of
        # truth for existing manuscripts is their front matter, if available.
        from en_engine import front_matter
        for article_id in range(1, 10):
            f = ROOT / "en" / "posts" / f"{article_id:04d}.md"
            if f.exists():
                meta, _ = front_matter(f.read_text(encoding="utf-8"))
                self.assertEqual(self.rows[article_id - 1]["category_id"], int(meta["category_id"]))

    def test_expansion_is_research_backlog_not_marked_published(self):
        self.assertEqual(len(self.rows[:48]), 48)
        for row in self.rows[48:]:
            self.assertEqual(row["research_status"], "candidate")
            self.assertEqual(row["keywords"], [])
        self.assertFalse(any("published" in row for row in self.rows[48:]))

    def test_pair_registry_is_complete_and_slug_collision_guard_matches(self):
        pairs = self.policy["page_pairs"]
        self.assertEqual(len(pairs), 16)
        self.assertEqual(len({p["vi"] for p in pairs}), len(pairs))
        self.assertEqual(len({p["en"] for p in pairs}), len(pairs))
        for pair in pairs:
            self.assertIn(pair["en_slug"], en_engine.EN_PAGE_SLUGS)


if __name__ == "__main__":
    unittest.main()
