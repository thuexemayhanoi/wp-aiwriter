"""Pure regressions for the read-only 333 URL audit; no network."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vi_redirect_audit", ROOT/"scripts/vi_redirect_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditTests(unittest.TestCase):
    def test_approved_manifest_is_exactly_333(self):
        doc = json.loads(audit.MAP.read_text(encoding="utf-8"))
        self.assertEqual(len(audit.verify_manifest(doc)), 333)

    def test_url_normalization_does_not_accept_other_origin_or_query(self):
        self.assertEqual(audit.normalize(audit.SITE+"/a"),audit.SITE+"/a/")
        self.assertEqual(audit.normalize("https://attacker.test/a"),"")
        self.assertEqual(audit.normalize(audit.SITE+"/a?redirect=1"),"")

    def test_301_to_self_canonical(self):
        row={"old_url":audit.SITE+"/excel-168-clean/","new_url":audit.SITE+"/clean/","wp_id":101}
        class Headers(dict):
            pass
        expected=[
            (301, Headers({"Location":"/clean/"}), b""),
            (200, Headers({}), b'<html><head><link rel="canonical" href="https://blog.rentbikehanoi.com/clean/"></head></html>')
        ]
        with patch.object(audit,"get_status",side_effect=expected):
            self.assertTrue(audit.check_one("168",row)["ok"])

    def test_wrong_location_fails(self):
        row={"old_url":audit.SITE+"/excel-168-clean/","new_url":audit.SITE+"/clean/","wp_id":101}
        with patch.object(audit,"get_status",return_value=(302,{"Location":"/clean/"},b"")):
            self.assertFalse(audit.check_one("168",row)["ok"])

    def test_noindex_fails(self):
        row={"old_url":audit.SITE+"/excel-168-clean/","new_url":audit.SITE+"/clean/","wp_id":101}
        expected=[(301,{"Location":"/clean/"},b""),
                  (200,{},b'<link rel="canonical" href="https://blog.rentbikehanoi.com/clean/"><meta name="robots" content="noindex,follow">')]
        with patch.object(audit,"get_status",side_effect=expected):
            result=audit.check_one("168",row)
            self.assertFalse(result["ok"])
            self.assertIn("noindex", result["error"])


if __name__=="__main__":
    unittest.main()
