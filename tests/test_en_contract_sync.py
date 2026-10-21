"""Static contract tests: EN writer docs and QA publisher must not reintroduce obsolete three-post caps.

These checks never access WordPress or modify any files. The Vietnamese publisher is unaffected.
"""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


class EnglishPublicationContract(unittest.TestCase):
    def test_en_policy_has_no_article_or_batch_count_caps(self):
        policy = json.loads(read("en/publication-policy.json"))
        self.assertNotIn("batch_size", policy)
        self.assertNotIn("max_batches_per_run", policy)
        self.assertEqual(policy["min_score"], 76)
        self.assertGreaterEqual(policy["min_words"], 1600)
        self.assertTrue(policy["require_live_routes"])

    def test_publisher_continuation_and_safety_survive(self):
        engine = read("scripts/en_engine.py")
        workflow = read(".github/workflows/en-publisher.yml")
        self.assertNotIn("policy['batch_size']", engine)
        self.assertNotIn("max_batches_per_run", engine)
        self.assertIn("for index, article in enumerate(eligible)", engine)
        self.assertIn("report['has_more'] = bool(remaining)", engine)
        self.assertIn("POST_INTENT", engine)
        self.assertIn("VERIFIED", engine)
        for guard in (
            "cancel-in-progress: false",
            "EN_PUBLISH_TIME_BUDGET_SECONDS",
            "python scripts/en_engine.py --mode sync --live --persist-state",
            "steps.sync.outputs.has_more == 'true'",
            "gh workflow run en-publisher.yml --ref main -f live=true",
        ):
            self.assertIn(guard, workflow)
        self.assertNotIn("max_batches_per_run", workflow)

    def test_current_agent_and_editorial_docs_agree(self):
        expected = {
            "AGENTS.md": "không giới hạn số bài/lượt",
            "CLAUDE.md": "no article-count cap",
            "README.md": "no `batch_size` or `max_batches_per_run`",
            "docs/EN_478_AI_PLAYBOOK.md": "no article-count or batch-count limit",
            "docs/EN_478_TITLE_PLAN.md": "no EN article/batch-count limit",
            "docs/EN_500_ROLLOUT.md": "article-count/batch-count limits have been removed",
            "docs/EN_CATEGORY_SEED_QUEUE.md": "no count-based article or batch cap",
            "docs/EN_PIPELINE.md": "without a numeric cap",
            "docs/EN_WRITER_CHECKPOINT.md": "CURRENT EN POLICY OVERRIDE",
            "docs/MENU_TAXONOMY_MAP_VI_EN.md": "không giới hạn số bài theo lượt/batch",
        }
        for path, phrase in expected.items():
            with self.subTest(path=path):
                self.assertIn(phrase.casefold(), read(path).casefold())
        self.assertNotIn("publish tối đa 3/lượt", read("AGENTS.md"))
        self.assertNotIn("<=3 new EN posts per run", read("CLAUDE.md"))


if __name__ == "__main__":
    unittest.main()
