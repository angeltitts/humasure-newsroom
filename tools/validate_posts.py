#!/usr/bin/env python3
"""Validate newsroom story files. Usage: python3 tools/validate_posts.py [files...]  (default: all posts/*.json)"""
import json, re, sys, glob, os
from html.parser import HTMLParser
ALLOWED={"p","h2","h3","ul","ol","li","strong","em","blockquote","a"}
TYPES={"explainer","guide","news","analysis","update"}
CATS={"News","Explainers","Regulation","Research","Humasure updates"}
DIRS={f"D{i}" for i in range(1,11)}
BANNED=["revolutionary","game-changing","terrifying","rogue ai","killer robot","100% safe","guaranteed","hackers could take over"]
REQ=["id","type","slug","title","excerpt","category","tags","directives","names_companies","incident","sources","body_html"]
class P(HTMLParser):
    def __init__(s): super().__init__(); s.bad=set(); s.text=[]
    def handle_starttag(s,t,a):
        if t not in ALLOWED: s.bad.add(t)
    def handle_data(s,d): s.text.append(d)
def check(path):
    e=[]
    try: d=json.load(open(path))
    except Exception as x: return [f"invalid JSON: {x}"]
    for k in REQ:
        if k not in d: e.append(f"missing {k}")
    if e: return e
    name=os.path.basename(path)[:-5]
    if d["id"]!=name: e.append("id != filename")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-[a-z0-9-]+",d["id"]): e.append("bad id format")
    if not d["id"].endswith(d["slug"]): e.append("slug not end of id")
    if d["type"] not in TYPES: e.append("bad type")
    if d["category"] not in CATS: e.append("bad category")
    if len(d["title"])>=90: e.append("title >= 90 chars")
    if len(d["excerpt"])>=220: e.append("excerpt >= 220 chars")
    if not d["tags"]: e.append("no tags (need country/region)")
    if not d["directives"] or not set(d["directives"])<=DIRS: e.append("bad directives")
    for k in ("names_companies","incident"):
        if not isinstance(d[k],bool): e.append(f"{k} not boolean")
    if not d["sources"] or any(not s.get("url","").startswith("https://") or not s.get("title") for s in d["sources"]): e.append("bad sources")
    p=P(); p.feed(d["body_html"])
    if p.bad: e.append(f"disallowed tags {sorted(p.bad)}")
    w=len(" ".join(p.text).split())
    if not 300<=w<=900: e.append(f"word count {w} outside 300-900")
    low=(d["body_html"]+d["title"]+d["excerpt"]).lower()
    for b in BANNED:
        if b in low: e.append(f"banned phrase: {b}")
    if re.search(r"\bpartner",low): e.append("uses 'partner' (check it is not a manufacturer)")
    if d["incident"] and "humasure.org/questions-to-ask" not in d["body_html"]: e.append("incident story must link /questions-to-ask/")
    if d["type"] in ("news","analysis") and not d["names_companies"] and not d["incident"]:
        e.append("note: news without companies/incident would auto-publish; confirm intended")
    return e
files=sys.argv[1:] or sorted(glob.glob(os.path.join(os.path.dirname(__file__),"..","posts","*.json")))
bad=0
slugs={}
for f in files:
    errs=check(f)
    try: slugs.setdefault(json.load(open(f))["slug"],[]).append(f)
    except Exception: pass
    print(("FAIL " if errs else "ok   ")+os.path.basename(f)); 
    for x in errs: print("   -",x)
    bad+=bool(errs)
for s,fs in slugs.items():
    if len(fs)>1: print("DUPLICATE slug",s); bad+=1
sys.exit(1 if bad else 0)
