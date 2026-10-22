#!/usr/bin/env python3
"""Read-only audit: every approved VI legacy URL must 301 to its live canonical.

No WordPress credentials, site writes, slug edits, or publisher operations.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, unquote
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "data/seo/vi-excel-slug-migrations.json"
REPORT = ROOT / "reports/seo/vi-redirect-audit.json"
SITE = "https://blog.rentbikehanoi.com"
AGENT = "Mozilla/5.0 (compatible; NguyenHaRedirectAudit/1.0)"
HEAD_BYTES = 110000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


HTTP = build_opener(NoRedirect())


def normalize(url):
    url = unquote(url).strip()
    p = urlsplit(url)
    if p.scheme != "https" or p.netloc.lower() != "blog.rentbikehanoi.com":
        return ""
    if p.query or p.fragment or not p.path.startswith("/"):
        return ""
    return SITE + p.path.rstrip("/") + "/"


class HeadMeta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonical = []
        self.robots = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonical.append(attrs.get("href", ""))
        if tag == "meta" and attrs.get("name", "").lower() == "robots":
            self.robots.append(attrs.get("content", ""))


def get_status(url, read_html=False):
    req = Request(url, headers={"User-Agent": AGENT,
                                "Accept": "text/html,application/xhtml+xml",
                                "Accept-Encoding": "identity",
                                "Cache-Control": "no-cache"}, method="GET")
    try:
        with HTTP.open(req, timeout=22) as response:
            body = response.read(HEAD_BYTES) if read_html else b""
            return response.status, response.headers, body
    except HTTPError as error:
        return error.code, error.headers, b""


def check_one(topic_id, row):
    old_url, new_url = row["old_url"], row["new_url"]
    result = {"topic_id": int(topic_id), "wp_id": row["wp_id"],
              "old_url": old_url, "new_url": new_url, "ok": False}
    try:
        code, headers, _ = get_status(old_url)
        result["old_status"] = code
        result["location"] = headers.get("Location", "")
        resolved = urljoin(old_url, result["location"])
        if code != 301:
            result["error"] = f"expected 301 for old URL, got {code}"
            return result
        if normalize(resolved) != normalize(new_url):
            result["error"] = f"wrong redirect destination: {resolved[:180]}"
            return result
        new_code, new_headers, body = get_status(new_url, read_html=True)
        result["new_status"] = new_code
        if new_code != 200:
            result["error"] = f"expected 200 at new URL, got {new_code}"
            return result
        html = body.decode("utf-8", errors="replace")
        parser = HeadMeta()
        parser.feed(html)
        result["canonical"] = parser.canonical
        if len(parser.canonical) != 1 or normalize(parser.canonical[0]) != normalize(new_url):
            result["error"] = "missing, duplicate or wrong canonical"
            return result
        if ("noindex" in ",".join(parser.robots).lower() or
                "noindex" in new_headers.get("X-Robots-Tag", "").lower()):
            result["error"] = "new URL became noindex"
            return result
        result["ok"] = True
    except (TimeoutError, OSError, URLError, ValueError) as error:
        result["error"] = f"{type(error).__name__}: {str(error)[:150]}"
    return result


def verify_manifest(doc):
    rows = doc.get("posts", {})
    if len(rows) != 333:
        raise ValueError(f"Expected 333 approved migrations, got {len(rows)}")
    seen_old, seen_new, seen_id = set(), set(), set()
    for key, row in rows.items():
        if int(key) < 168 or int(key) > 500:
            raise ValueError(f"Unexpected historical topic ID {key}")
        if row["old_slug"] != f"excel-{key}-" + row["new_slug"]:
            raise ValueError(f"Inconsistent old→new slug at {key}")
        if (row["old_url"] != SITE + "/" + row["old_slug"] + "/" or
                row["new_url"] != SITE + "/" + row["new_slug"] + "/"):
            raise ValueError(f"Unexpected origin/path for {key}")
        if row["old_url"] in seen_old or row["new_url"] in seen_new or row["wp_id"] in seen_id:
            raise ValueError(f"Duplicate migration at {key}")
        seen_old.add(row["old_url"])
        seen_new.add(row["new_url"])
        seen_id.add(row["wp_id"])
    return rows


def audit(workers=5):
    rows = verify_manifest(json.loads(MAP.read_text(encoding="utf-8")))
    keys = sorted(rows, key=int)
    # Detect a site-wide WAF/block promptly before making hundreds of requests.
    probes = [keys[0], keys[len(keys)//2], keys[-1]]
    results = [check_one(key, rows[key]) for key in probes]
    if all(not x["ok"] for x in results):
        result = {"total": len(rows), "checked": len(results),
                  "passed": 0, "failed": len(results),
                  "incomplete": True, "reason": "all three distant probes failed; do not flood WordPress",
                  "results": results}
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
        print("REDIRECT_AUDIT_PROBE_FAIL " + json.dumps(result, ensure_ascii=False)[:2400], flush=True)
        return 1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {pool.submit(check_one, key, rows[key]): key for key in keys if key not in probes}
        for future in as_completed(pending):
            results.append(future.result())
    results.sort(key=lambda x: x["topic_id"])
    problems = [x for x in results if not x["ok"]]
    summary = {"total":len(rows), "checked":len(results),
               "passed":len(rows)-len(problems), "failed":len(problems),
               "incomplete":len(results)!=len(rows),
               "old_statuses":dict(Counter(str(x.get("old_status","error")) for x in results)),
               "new_statuses":dict(Counter(str(x.get("new_status","unchecked")) for x in results)),
               "failures_preview":problems[:25], "results":results}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n")
    print("REDIRECT_AUDIT_SUMMARY " + json.dumps(
        {k:v for k,v in summary.items() if k!="results"}, ensure_ascii=False)[:7000], flush=True)
    return int(bool(problems or summary["incomplete"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers",type=int,default=5,choices=range(1,9))
    args = parser.parse_args()
    raise SystemExit(audit(workers=args.workers))
