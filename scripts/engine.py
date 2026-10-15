#!/usr/bin/env python3
"""Excel SEO queue -> strictly categorized WordPress posts. No AI model dependency."""
import argparse, html, json, os, pathlib, re, sys, unicodedata, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "data/topics.json"
WP_URL = "https://blog.rentbikehanoi.com"

def matrix():
    rows = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    ids = [r[0] for r in rows]
    if len(rows) != 355 or ids != list(range(146,501)):
        raise ValueError("Unexpected Excel Matrix; expected IDs 146..500 without gaps")
    return {i: {"id":i,"title":title,"category":category} for i,title,category in rows}

def read_post(path, topics):
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"\A---\n(.*?)\n---\n(.*)\Z",raw,re.S)
    if not m: raise ValueError(f"{path}: missing front matter")
    metadata = {}
    for line in m.group(1).splitlines():
        if not line.strip(): continue
        key, sep, val = line.partition(":")
        if not sep: raise ValueError(f"{path}: malformed front matter")
        metadata[key.strip()] = val.strip().strip('"').strip("'")
    try: i = int(metadata["matrix_id"])
    except (KeyError, ValueError): raise ValueError(f"{path}: invalid matrix_id")
    if i < 165 or i not in topics: raise ValueError(f"{path}: ID outside remaining 165..500")
    if metadata.get("title") != topics[i]["title"] or metadata.get("category_path") != topics[i]["category"]:
        raise ValueError(f"{path}: title/category mismatch with Excel row {i}")
    if metadata.get("ready","false").lower() != "true":
        return {"id":i,"ready":False,"status":"WAIT_WRITER"}
    body = m.group(2).strip()
    words = len(re.findall(r"\w+",body,flags=re.UNICODE))
    h2 = len(re.findall(r"^## .+",body,re.M))
    if words < 350 or h2 < 3 or re.search(r"TODO|TBD|Lorem ipsum",body,re.I):
        raise ValueError(f"{path}: QA FAIL (words={words}, h2={h2})")
    return {"id":i,"ready":True,"status":"QA_PASS","words":words,
            "title":topics[i]["title"],"category":topics[i]["category"],"body":body}

def slugify(text):
    text = unicodedata.normalize("NFKD",text.lower().replace("đ","d"))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"-+","-",re.sub(r"[^a-z0-9]+","-",text)).strip("-")[:75]

def markdown_to_html(text):
    output=[]
    for paragraph in re.split(r"\n\s*\n",text):
        block=paragraph.strip()
        if not block: continue
        heading=re.match(r"^(#{1,3}) (.+)$",block)
        if heading:
            level=len(heading.group(1))
            output.append(f"<h{level}>{html.escape(heading.group(2))}</h{level}>")
        elif block.startswith("- "):
            output.append("<ul>"+"".join("<li>"+html.escape(x[2:].strip())+"</li>" for x in block.splitlines() if x.startswith("- "))+"</ul>")
        else:
            output.append("<p>"+html.escape(" ".join(block.splitlines()))+"</p>")
    return "\n".join(output)

def wp(path, user, password, method="GET", payload=None):
    url=WP_URL+"/wp-json"+path
    data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode("utf-8")
    headers={"Accept":"application/json","User-Agent":"wp-aiwriter/1.0"}
    if data is not None: headers["Content-Type"]="application/json; charset=utf-8"
    import base64
    headers["Authorization"]="Basic "+base64.b64encode(f"{user}:{password}".encode()).decode()
    req=urllib.request.Request(url,method=method,data=data,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=40) as response: return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"WordPress HTTP {exc.code} at {path}: "+exc.read(600).decode(errors="replace")) from exc

def categories(user,password):
    cats=wp("/wp/v2/categories?per_page=100&hide_empty=false&_fields=id,name,parent",user,password)
    by_id={c["id"]:c for c in cats}
    paths={}
    for cat in cats:
        parts=[];cur=cat;seen=set()
        while cur and cur["id"] not in seen:
            seen.add(cur["id"])
            parts.append(html.unescape(cur["name"]).strip())
            cur=by_id.get(cur.get("parent",0))
        paths[" > ".join(reversed(parts))]=cat["id"]
    return paths

def exists(title,user,password):
    query=urllib.parse.urlencode({"search":title,"status":"any","context":"edit","per_page":100,"_fields":"id,title,status"})
    result=wp("/wp/v2/posts?"+query,user,password)
    for p in result:
        t=html.unescape(p.get("title",{}).get("raw",p.get("title",{}).get("rendered",""))).strip()
        if t.casefold()==title.strip().casefold(): return p
    return None

def run(args):
    topics=matrix()
    print("Matrix verified: 355 rows, IDs 146–500. Remaining: IDs 165–500 (336).")
    items=[];seen=set()
    for path in sorted((ROOT/"posts").glob("[0-9][0-9][0-9][0-9].md")):
        article=read_post(path,topics)
        if article["id"] in seen: raise ValueError(f"Repeated ID {article['id']}")
        seen.add(article["id"]);items.append(article)
    print("Authored files:",len(items),"QA PASS:",sum(x["ready"] for x in items))
    if args.mode=="qa": return 0
    ready=sorted([x for x in items if x["ready"]],key=lambda x:x["id"])
    if not args.live:
        print("DRY RUN:",[(x["id"],x["category"]) for x in ready[:args.limit]])
        return 0
    user=os.getenv("WP_USERNAME");password=os.getenv("WP_APPLICATION_PASSWORD")
    if not user or not password:
        print("Missing WP_USERNAME / WP_APPLICATION_PASSWORD secrets; no WordPress writes.")
        return 2
    paths=categories(user,password)
    print("WordPress hierarchies available:",len(paths))
    created=0;skipped=0
    for article in ready:
        if created>=args.limit: break
        old=exists(article["title"],user,password)
        if old:
            skipped+=1
            print(f"SKIP #{article['id']}: existing WP ID {old['id']} ({old['status']})")
            continue
        category_id=paths.get(article["category"])
        status="publish" if category_id is not None else "draft"
        payload={"title":article["title"],
                 "slug":f"excel-{article['id']}-{slugify(article['title'])}",
                 "status":status,
                 "content":markdown_to_html(article["body"])}
        if category_id is not None: payload["categories"]=[category_id]
        result=wp("/wp/v2/posts",user,password,method="POST",payload=payload)
        if result.get("status")!=status: raise RuntimeError("WordPress status mismatch")
        print(f"CREATED #{article['id']} WP:{result['id']} status={status} category_id={category_id} URL={result.get('link')}")
        created+=1
    print(f"COMPLETE created={created} preexisting_skipped={skipped}")
    output_path=os.getenv("GITHUB_OUTPUT")
    if output_path:
        with open(output_path,"a",encoding="utf-8") as out:
            out.write(f"created={created}\n")
    return 0

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=["qa","sync"],default="qa")
    parser.add_argument("--limit",type=int,default=2)
    parser.add_argument("--live",action="store_true")
    args=parser.parse_args()
    if not (1<=args.limit<=10):parser.error("limit must be 1..10")
    try:sys.exit(run(args))
    except (RuntimeError,ValueError) as e:
        print("FAIL:",e,file=sys.stderr)
        sys.exit(1)
