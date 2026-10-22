#!/usr/bin/env python3
"""Read-only public-site crawl for 404s in Nguyễn Hà's WP posts, pages, menus, media and XML sitemaps.
Produces per-link source attribution. No WP credentials, writes or content updates.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import socket
import time
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlsplit, urlunsplit, urldefrag
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
import http.client

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports"/"seo"/"sitewide-404"
BASE="https://blog.rentbikehanoi.com"
DOMAIN="blog.rentbikehanoi.com"
UA="NguyenHaSite404Audit/1.0 (+read-only; wordpress owner approved)"
SKIP_PREFIX=("mailto:","tel:","sms:","data:","javascript:","blob:","whatsapp:","skype:")
RETRIES=(0,1,3)
MAX_BYTES=1800000

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

OPENER=build_opener(NoRedirect())

def fetch(url, method="GET", max_bytes=MAX_BYTES):
    """A single hop; don't silently turn old 404 links into home page successes."""
    last=None
    for n, delay in enumerate(RETRIES):
        if delay: time.sleep(delay)
        try:
            req=Request(url,method=method,headers={
                "User-Agent":UA,"Accept":"text/html,application/json,application/xml,text/xml,*/*",
                "Accept-Encoding":"identity"})
            with OPENER.open(req,timeout=24) as response:
                return response.status,dict(response.headers),response.read(max_bytes) if method=="GET" else b""
        except HTTPError as e:
            code=e.code
            if code in (429,500,502,503,504) and n<len(RETRIES)-1:
                last=(code,dict(e.headers),b"");continue
            return code,dict(e.headers),b""
        except (OSError,URLError,TimeoutError,socket.timeout,http.client.HTTPException) as e:
            last=("network",{},type(e).__name__+": "+str(e)[:120])
            if n==len(RETRIES)-1: break
    return last or ("network",{},b"")

def internal(url):
    p=urlsplit(url)
    return p.scheme in ("https","http") and p.netloc.lower() in (DOMAIN, "www."+DOMAIN)

def clean_url(ref,source):
    ref=(ref or "").strip()
    if not ref or ref.startswith(("#","?")) or ref.lower().startswith(SKIP_PREFIX):
        return None
    if any(c in ref for c in ("{","}","<",">"," ")):
        return None
    try:
        absolute,fragment=urldefrag(urljoin(source,ref))
        p=urlsplit(absolute)
        if p.scheme not in ("http","https") or not p.netloc: return None
        if internal(absolute):
            path=p.path or "/"
            return urlunsplit(("https",DOMAIN,path,p.query,""))
        return absolute
    except ValueError: return None

class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ("a","area"): fields=("href",)
        elif tag in ("img","source","video","audio","iframe","embed","track"): fields=("src","data-src","data-lazy-src","poster")
        elif tag=="form": fields=("action",)
        elif tag=="link": fields=("href",)
        elif tag=="script": fields=("src",)
        else: fields=()
        for field in fields:
            val=a.get(field)
            if val: self.links.append((val,tag+"."+field))
        if tag in ("img","source"):
            for field in ("srcset","data-srcset"):
                for item in (a.get(field) or "").split(","):
                    value=item.strip().split(" ")[0]
                    if value: self.links.append((value,tag+"."+field))

def extract(html):
    parser=Links()
    parser.feed(html)
    return parser.links

def read_json(url):
    code,headers,body=fetch(url)
    if code!=200: raise RuntimeError("REST "+url+" status "+str(code))
    try: return json.loads(body),headers
    except (ValueError,UnicodeError) as e: raise RuntimeError("REST invalid JSON "+url+" "+str(e))

def wp_collection(name,per_page=20,max_pages=100):
    rows=[]
    base=BASE+"/wp-json/wp/v2/"+name
    fields="id,link,slug,status,content"
    # Explicit status=publish; never scan drafts or leave invisible content in report.
    for page in range(1,max_pages+1):
        data,headers=read_json(base+f"?status=publish&per_page={per_page}&page={page}&_fields={fields}")
        if not isinstance(data,list): raise RuntimeError("REST not a list "+name)
        rows.extend(data)
        total_pages=int(headers.get("X-WP-TotalPages",str(page)))
        if page>=total_pages:return rows
    raise RuntimeError("REST page cap reached "+name)

def wp_categories():
    try:
        data,headers=read_json(BASE+"/wp-json/wp/v2/categories?per_page=100&hide_empty=false&_fields=id,link,slug,count")
        return data if isinstance(data,list) else []
    except Exception as e:
        print("CATEGORY_REST_WARNING "+str(e)[:240],flush=True)
        return []

def sitemap_locs():
    """Fetch sitemaps without hitting WordPress admin, with recursive child map limit."""
    seed=BASE+"/sitemap_index.xml"
    queue=[seed];seen=set();urls=[];warnings=[]
    while queue and len(seen)<50:
        url=queue.pop(0)
        if url in seen:continue
        seen.add(url)
        code,_,body=fetch(url)
        if code!=200:
            warnings.append({"sitemap":url,"status":code});continue
        try:root=ET.fromstring(body)
        except ET.ParseError:
            warnings.append({"sitemap":url,"error":"invalid XML"});continue
        children=[e.text.strip() for e in root.iter() if e.tag.endswith("loc") and e.text]
        if root.tag.endswith("sitemapindex"):
            queue.extend(child for child in children if clean_url(child,url) and internal(child) and child not in seen)
        else:
            urls.extend(children)
    if queue:warnings.append({"error":"sitemap child limit reached"})
    return urls,warnings,len(seen)

def check_target(target):
    """Resolve max 5 hops; recheck apparent 404/410 using GET to reduce HEAD false positives."""
    chain=[]
    url=target
    for hop in range(6):
        code,headers,_=fetch(url,method="HEAD")
        if code in (405,501,400,"network",403) or (isinstance(code,int) and code in (404,410)):
            getcode,gh,_=fetch(url,method="GET",max_bytes=2048)
            if getcode!= "network" or code=="network":
                code,headers=getcode,gh
        chain.append({"status":code,"url":url})
        if code in (301,302,303,307,308):
            loc=headers.get("Location") or headers.get("location")
            if not loc:
                return {"status":"bad_redirect","final_url":url,"chain":chain}
            nxt=clean_url(loc,url)
            if not nxt or not internal(nxt):
                return {"status":"external_redirect","final_url":nxt or loc,"chain":chain}
            if any(h["url"]==nxt for h in chain):
                return {"status":"redirect_loop","final_url":nxt,"chain":chain}
            url=nxt
            continue
        return {"status":code,"final_url":url,"chain":chain}
    return {"status":"too_many_redirects","final_url":url,"chain":chain}

def classify(row):
    status=row["status"]
    if status in (404,410):return "broken_404"
    if status in ("redirect_loop","bad_redirect","too_many_redirects"):return "broken_redirect"
    if status=="network" or status in (429,500,502,503,504):return "unverified_transient"
    if status in (401,403,405,451,"external_redirect"):return "blocked_or_external"
    if isinstance(status,int) and 200<=status<300:return "ok"
    return "other"

def main():
    args=argparse.ArgumentParser()
    args.add_argument("--workers",type=int,default=5,choices=range(1,9))
    opts=args.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    posts=wp_collection("posts")
    pages=wp_collection("pages")
    if len(posts)<900 or len(pages)<30:
        raise RuntimeError(f"Unexpected short WP inventory posts={len(posts)}, pages={len(pages)}")
    print(f"INVENTORY posts={len(posts)} pages={len(pages)}",flush=True)
    sources=defaultdict(list)
    counters=Counter()
    def add(target,source,kind):
        url=clean_url(target,source)
        if url is None:
            counters["skipped_non_http_or_fragment"]+=1;return
        if not internal(url):
            counters["external_outbound_not_checked"]+=1;return
        counters["internal_references"]+=1
        if len(sources[url])<12:sources[url].append({"from":source,"kind":kind})

    for row in posts+pages:
        origin=row.get("link","")
        if not origin:raise RuntimeError("Missing permalink for WP id "+str(row.get("id")))
        typ="post" if row in posts else "page"
        add(origin,origin,typ+".permalink")
        body=row.get("content",{}).get("rendered","")
        if not isinstance(body,str): raise RuntimeError("Missing REST rendered body "+str(row.get("id")))
        for link,kind in extract(body):
            add(link,origin,typ+".body."+kind)
        counters[typ+"_body_scanned"]+=1
    for cat in wp_categories():
        if cat.get("link"):add(cat["link"],BASE+"/", "taxonomy.category")

    # Render page-builder output and site-wide templates, including menu/footer links.
    frontend=[BASE+"/",BASE+"/en/"]
    frontend += [p["link"] for p in pages]
    if posts:
        frontend += [posts[0]["link"],posts[-1]["link"]]
    frontend=list(dict.fromkeys(frontend))
    preview_failures=[]
    for i,url in enumerate(frontend):
        code,_,body=fetch(url,max_bytes=1200000)
        if code!=200:
            preview_failures.append({"source":url,"status":code})
            continue
        for link,kind in extract(body.decode("utf-8",errors="replace")):
            add(link,url,"frontend."+kind)
    print(f"FRONTEND full_html={len(frontend)} failed={len(preview_failures)}",flush=True)

    sitemap_urls,sitemap_warnings,sitemap_count=sitemap_locs()
    for url in sitemap_urls:add(url,BASE+"/sitemap_index.xml","sitemap.loc")
    add(BASE+"/sitemap_index.xml",BASE+"/","sitemap.index")
    targets=sorted(sources.keys())
    print(f"LINK_TARGETS unique_internal={len(targets)} references={counters['internal_references']} sitemap_urls={len(sitemap_urls)}",flush=True)
    rows=[]
    with ThreadPoolExecutor(max_workers=opts.workers) as pool:
        jobs={pool.submit(check_target,url):url for url in targets}
        for i,future in enumerate(as_completed(jobs),1):
            url=jobs[future]
            try: result=future.result()
            except Exception as e: result={"status":"network","final_url":url,"chain":[],"error":repr(e)[:200]}
            result.update({"url":url,"sources":sources[url],"classification":classify(result)})
            rows.append(result)
            if i%250==0: print(f"LINK_PROGRESS {i}/{len(targets)}",flush=True)
    rows.sort(key=lambda x:x["url"])
    counts=Counter(x["classification"] for x in rows)
    problem=[x for x in rows if x["classification"] in ("broken_404","broken_redirect")]
    uncertain=[x for x in rows if x["classification"]=="unverified_transient"]
    summary={
        "site":BASE,"read_only":True,
        "published_posts":len(posts),"published_pages":len(pages),
        "body_scanned":counters["post_body_scanned"]+counters["page_body_scanned"],
        "frontend_templates_and_pages_checked":len(frontend),
        "frontend_render_failures":preview_failures,
        "sitemaps_checked":sitemap_count,"sitemap_urls":len(sitemap_urls),
        "sitemap_warnings":sitemap_warnings,
        "internal_references":counters["internal_references"],
        "external_references_skipped":counters["external_outbound_not_checked"],
        "unique_internal_targets":len(targets),
        "classification_counts":dict(counts),
        "broken_count":len(problem),
        "uncertain_count":len(uncertain),
        "broken_preview":problem[:35],
        "uncertain_preview":uncertain[:15],
        "complete":not uncertain and not sitemap_warnings and not preview_failures,
    }
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT/"all-internal-links.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (OUT/"broken-links.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.writer(f);w.writerow(["classification","status","bad_url","final_url","source_page","link_kind","redirect_chain"])
        for x in problem+uncertain:
            for src in x["sources"]:
                w.writerow([x["classification"],x["status"],x["url"],x["final_url"],src["from"],src["kind"],
                            " -> ".join(str(c["status"]) for c in x["chain"])])
    print("SITE404_SUMMARY "+json.dumps({k:v for k,v in summary.items()
        if k not in ("broken_preview","uncertain_preview","frontend_render_failures","sitemap_warnings")},
        ensure_ascii=False),flush=True)
    for row in problem[:30]:
        print("SITE404_BROKEN "+json.dumps({"url":row["url"],"status":row["status"],
            "sources":row["sources"][:3],"chain":row["chain"]},ensure_ascii=False)[:800],flush=True)
    for row in uncertain[:8]:
        print("SITE404_UNCERTAIN "+json.dumps({"url":row["url"],"status":row["status"]},ensure_ascii=False)[:350],flush=True)
    return 2 if problem else (3 if not summary["complete"] else 0)

if __name__=="__main__":
    raise SystemExit(main())
