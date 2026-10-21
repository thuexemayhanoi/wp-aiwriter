"""Regression tests for the zero-write English next-three research packet."""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import en_writer_brief


class EnWriterBrief(unittest.TestCase):
    def test_only_unclaimed_english_ids_and_exact_source_metadata(self):
        original_topics = (ROOT / "en" / "topics.json").read_bytes()
        original_ledger = (ROOT / "data" / "en-publication-state.json").read_bytes()
        original_csv = (ROOT / "en" / "title-plan-478.csv").read_bytes()
        packet = en_writer_brief.build_packet(3)
        ledger = json.loads(original_ledger)["posts"]
        source = {int(x["id"]): x for x in json.loads(original_topics)}
        self.assertEqual(packet["mode"], "READ_ONLY_EN_EDITORIAL_BRIEF")
        self.assertFalse(packet["live_wordpress_verified"])
        self.assertLessEqual(len(packet["topics"]), 3)
        self.assertGreaterEqual(len(packet["topics"]), 1)
        self.assertEqual(len({p["topic_id"] for p in packet["topics"]}), len(packet["topics"]))
        for item in packet["topics"]:
            i = item["topic_id"]
            self.assertNotIn(str(i), ledger)
            self.assertFalse((ROOT / item["article_path"]).exists())
            self.assertEqual(item["write_with_title"], source[i]["title"])
            self.assertEqual(item["slug_locked"], source[i]["slug"])
            self.assertEqual(item["category_id"], source[i]["category_id"])
            self.assertEqual(item["category_ancestors_from_snapshot"][-1]["term_id"], item["category_id"])
            self.assertEqual(item["expected_url"], "https://blog.rentbikehanoi.com/en/" + item["slug_locked"] + "/")
            self.assertFalse(item["slug_locked"].startswith("excel-"))
        self.assertEqual((ROOT / "en" / "topics.json").read_bytes(), original_topics)
        self.assertEqual((ROOT / "data" / "en-publication-state.json").read_bytes(), original_ledger)
        self.assertEqual((ROOT / "en" / "title-plan-478.csv").read_bytes(), original_csv)

    def test_no_qa_bypass_with_unlimited_publishing(self):
        packet = en_writer_brief.build_packet(1)
        policy = json.loads((ROOT / "en" / "publication-policy.json").read_text(encoding="utf-8"))
        self.assertEqual(packet["quality_gate"]["minimum_score"], policy["min_score"])
        self.assertEqual(packet["quality_gate"]["minimum_words"], policy["min_words"])
        self.assertTrue(packet["quality_gate"]["cannot_reduce_QA"])
        self.assertTrue(packet["quality_gate"]["continuous_publishing"])
        self.assertNotIn("batch_size", packet["quality_gate"])
        self.assertNotIn("max_batches_per_run", policy)
        with self.assertRaisesRegex(ValueError, "1 to 3"):
            en_writer_brief.build_packet(4)
        with self.assertRaises(ValueError):
            en_writer_brief.build_packet(0)

    def test_legal_source_warning_and_markdown(self):
        packet = en_writer_brief.build_packet(3)
        rendered = en_writer_brief.markdown(packet)
        self.assertIn("LIVE WordPress", rendered)
        self.assertIn("QA >= 76", rendered)
        self.assertIn("data/en-publication-state.json", rendered)
        self.assertNotIn("ready: true", rendered)
        for topic in packet["topics"]:
            self.assertIn(topic["source_title_en"], rendered)
            if topic["legal_qa_hard_gate"]:
                self.assertEqual(topic["research_priority"], "OFFICIAL_LEGAL_SOURCES_AND_EFFECTIVE_DATES")


if __name__ == "__main__":
    unittest.main()
