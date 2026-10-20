"""Guard the read-only VI/EN WordPress navigation map against editorial drift.

Runs entirely offline in existing Python unittest CI. WordPress REST is the
production truth; a mismatch means review/update the snapshot, not mutate live.
"""
import json
import pathlib
import unittest
from collections import Counter


ROOT = pathlib.Path(__file__).resolve().parents[1]
MAP = json.loads((ROOT / "data" / "navigation-map.json").read_text(encoding="utf-8"))
VI_TOPICS = json.loads((ROOT / "data" / "topics.json").read_text(encoding="utf-8"))
EN_TOPICS = json.loads((ROOT / "en" / "topics.json").read_text(encoding="utf-8"))
EN_POLICY = json.loads((ROOT / "en" / "publication-policy.json").read_text(encoding="utf-8"))


class NavigationMapContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cats = {int(row["term_id"]): row for row in MAP["categories"]}
        cls.pages = {int(row["page_id"]): row for row in MAP["pages"]}
        cls.menus = {int(row["menu_id"]): row for row in MAP["menus"]}

    def taxonomy_path(self, term_id):
        current = int(term_id)
        parts = []
        visited = set()
        while current:
            self.assertIn(current, self.cats, "unknown WordPress Term ID")
            self.assertNotIn(current, visited, "category parent cycle")
            visited.add(current)
            row = self.cats[current]
            parts.append(row["name"])
            current = int(row["parent_term_id"])
        return " > ".join(reversed(parts))

    def category_slug_path(self, term_id):
        current = int(term_id)
        parts = []
        visited = set()
        while current:
            self.assertIn(current, self.cats)
            self.assertNotIn(current, visited, "category slug parent cycle")
            visited.add(current)
            row = self.cats[current]
            parts.append(row["slug"])
            current = int(row["parent_term_id"])
        return "/".join(reversed(parts))

    def test_schema_and_snapshot_provenance(self):
        self.assertEqual(MAP["schema_version"], 1)
        self.assertTrue(MAP["read_only"])
        self.assertEqual(MAP["site"], "https://blog.rentbikehanoi.com")
        self.assertEqual(MAP["menu_ids"], {
            "vi_primary": 26, "vi_footer": 29, "en_primary": 57, "en_footer": 58,
        })
        self.assertEqual(len(MAP["categories"]), len(self.cats))
        self.assertEqual(len(MAP["pages"]), len(self.pages))
        self.assertEqual(len(MAP["menus"]), len(self.menus))

    def test_complete_vi_en_taxonomy_and_permalink_parents(self):
        self.assertEqual(Counter(x["language"] for x in self.cats.values()),
                         {"vi": 22, "en": 21})
        self.assertEqual({i for i, c in self.cats.items() if c["language"] == "en"},
                         set(range(46, 57)) | set(range(60, 70)))
        for term_id, row in self.cats.items():
            full = self.category_slug_path(term_id)
            self.assertEqual(row["rest_path"], f"/category/{full}/")
            prefix = "/en" if row["language"] == "en" else ""
            self.assertEqual(row["public_path_expected"], prefix + row["rest_path"])
            if row["parent_term_id"]:
                self.assertEqual(self.cats[row["parent_term_id"]]["language"], row["language"])
            self.assertGreaterEqual(row["posts_direct_snapshot"], 0)

    def test_vi_excel_category_paths_exactly_match_wordpress(self):
        category_paths = {
            self.taxonomy_path(term_id) for term_id, row in self.cats.items()
            if row["language"] == "vi" and term_id != 1
        }
        self.assertEqual(len(VI_TOPICS), 355)
        for row in VI_TOPICS:
            self.assertIsInstance(row, list)
            self.assertGreaterEqual(len(row), 3)
            self.assertIn(row[2], category_paths,
                          f"VI Excel article #{row[0]} targets an unknown taxonomy path")
        self.assertNotIn("Uncategorized", {r[2] for r in VI_TOPICS})

    def test_en_writer_topic_ids_match_map_and_approved_policy(self):
        english_ids = {term_id for term_id, row in self.cats.items()
                       if row["language"] == "en"}
        self.assertEqual(len(EN_TOPICS), 500)
        allowed = {int(i) for i in EN_POLICY["category_ids"]["leaves"]}
        registered = ({int(i) for i in EN_POLICY["category_ids"]["parents"]}
                      | allowed)
        self.assertEqual(registered, english_ids)
        self.assertTrue(allowed <= english_ids)
        self.assertTrue(all(int(t["category_id"]) in allowed for t in EN_TOPICS))
        self.assertEqual(EN_POLICY["min_words"], 1600)
        self.assertGreaterEqual(EN_POLICY["min_score"], 85)

    def test_pages_keep_language_and_parent_type(self):
        self.assertEqual(Counter(x["language"] for x in self.pages.values()),
                         {"vi": 18, "en": 19})
        self.assertEqual(self.pages[1758]["path"], "/en/")
        for id_, page in self.pages.items():
            parent = int(page["parent_page_id"])
            if parent:
                self.assertIn(parent, self.pages)
                self.assertEqual(self.pages[parent]["language"], page["language"])
            if page["language"] == "en":
                self.assertTrue(page["path"].startswith("/en/"), f"page {id_}")
                if id_ != 1758:
                    self.assertEqual(parent, 1758, f"unexpected EN WP page parent {id_}")
            else:
                self.assertFalse(page["path"].startswith("/en/"), f"page {id_}")
        pairs = EN_POLICY["page_pairs"]
        self.assertEqual(len(pairs), 16)
        for pair in pairs:
            self.assertEqual(self.pages[int(pair["vi"])]["language"], "vi")
            self.assertEqual(self.pages[int(pair["en"])]["language"], "en")

    def test_exact_eight_primary_links_and_no_orphan_submenus(self):
        self.assertEqual(set(self.menus), {26, 29, 57, 58})
        for menu_id, menu in self.menus.items():
            items = menu["items"]
            ids = [int(item["menu_item_id"]) for item in items]
            self.assertEqual(len(ids), len(set(ids)), f"duplicate menu item {menu_id}")
            byid = {int(item["menu_item_id"]): item for item in items}
            expected = "en" if menu_id in (57, 58) else "vi"
            self.assertEqual(menu["language"], expected)
            roots = [x for x in items if not x["parent_menu_item_id"]]
            if menu["purpose"] == "primary":
                self.assertEqual(len(roots), 8, f"primary menu {menu_id} must remain eight top items")
            for item in items:
                par = int(item["parent_menu_item_id"])
                seen = {int(item["menu_item_id"])}
                while par:
                    self.assertIn(par, byid, f"menu {menu_id} has an orphan child")
                    self.assertNotIn(par, seen, f"menu {menu_id} contains a cycle")
                    seen.add(par)
                    par = int(byid[par]["parent_menu_item_id"])
                kind = item["object_type"]
                target = int(item["object_id"])
                if kind == "page":
                    self.assertIn(target, self.pages)
                    self.assertEqual(self.pages[target]["language"], expected)
                    self.assertEqual(item["rest_path"], self.pages[target]["path"])
                    self.assertEqual(item["public_path_expected"], item["rest_path"])
                elif kind == "category":
                    self.assertIn(target, self.cats)
                    self.assertEqual(self.cats[target]["language"], expected)
                    cat = self.cats[target]
                    self.assertEqual(item["rest_path"], cat["rest_path"])
                    self.assertEqual(item["public_path_expected"],
                                     cat["public_path_expected"])
                else:
                    self.assertEqual(kind, "custom")
                    self.assertTrue(item["rest_path"].startswith("/"))

    def test_handoff_files_reference_canonical_map(self):
        expected = ("docs/MENU_TAXONOMY_MAP_VI_EN.md", "data/navigation-map.json")
        for name in ("AGENTS.md", "CLAUDE.md"):
            body = (ROOT / name).read_text(encoding="utf-8")
            for path in expected:
                self.assertIn(path, body, f"{name} must instruct writers to read {path}")


if __name__ == "__main__":
    unittest.main()
