"""Offline contract tests for the 404 crawler; no network or site mutations."""
import importlib.util
from pathlib import Path
from unittest import TestCase, main, mock

spec=importlib.util.spec_from_file_location("site404",Path(__file__).resolve().parents[1]/"scripts/sitewide_404_audit.py")
a=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

class ScanContracts(TestCase):
    def test_internal_and_external_url_normalization(self):
        self.assertEqual(a.clean_url("/hello/?x=1#part",a.BASE+"/en/"),a.BASE+"/hello/?x=1")
        self.assertIsNone(a.clean_url("javascript:alert(1)",a.BASE+"/"))
        self.assertFalse(a.internal("https://elsewhere.com/"))
        self.assertTrue(a.internal(a.BASE+"/"));

    def test_find_links_and_media_in_html(self):
        html='<p><a href="/missing/">Click</a><img src="/wp-content/uploads/photo.webp" srcset="/a.webp 1x, /b.webp 2x"><source data-src="/c.webp"></p>'
        links=a.extract(html)
        values=[x[0] for x in links]
        for val in ("/missing/","/wp-content/uploads/photo.webp","/a.webp","/b.webp","/c.webp"):
            self.assertIn(val,values)

    def test_http_404_classification(self):
        self.assertEqual(a.classify({"status":404}),"broken_404")
        self.assertEqual(a.classify({"status":410}),"broken_404")
        self.assertEqual(a.classify({"status":503}),"unverified_transient")
        self.assertEqual(a.classify({"status":200}),"ok")
        self.assertEqual(a.classify({"status":"redirect_loop"}),"broken_redirect")

    def test_unexpected_redirect_cycle(self):
        with mock.patch.object(a,"fetch",side_effect=[
          (301,{"Location":"/b/"},b""),(302,{"Location":"/a/"},b"")]):
            z=a.check_target(a.BASE+"/a/")
        self.assertEqual(z["status"],"redirect_loop")

if __name__=="__main__":
    main()
