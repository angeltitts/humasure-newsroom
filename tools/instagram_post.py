#!/usr/bin/env python3
"""Post Humasure News carousels to Instagram, one story at a time, only once the story is live on humasure.org.

Environment:
  IG_USER_ID       Instagram professional account ID (linked to the Humasure Facebook Page)
  IG_ACCESS_TOKEN  Page access token with instagram_basic and instagram_content_publish
  GRAPH_BASE       default https://graph.facebook.com/v26.0
  MAX_POSTS        stories to post this run (default 1)
  MAX_AGE_DAYS     ignore stories older than this (default 14)
  DRY_RUN=1        show what would be posted, post nothing

Rules (do not relax without Jonathan's written OK):
  - A story is posted only if https://humasure.org/news/<slug>/ is publicly live. Stories waiting for
    approval in WordPress are not public, so the website's approval gate carries over to Instagram.
  - Each story is posted at most once (social/posted.json records it).
"""
import datetime as dt, json, os, pathlib, sys, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / "social" / "posted.json"
RAW = "https://raw.githubusercontent.com/angeltitts/humasure-newsroom/main/social/{id}/slide-{n}.jpg"
BASE = os.environ.get("GRAPH_BASE", "https://graph.facebook.com/v26.0")
UA = {"User-Agent": "HumasureNewsroom/1.0"}

def http(method, url, data=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def graph(method, path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    if method == "GET":
        code, txt = http("GET", f"{BASE}/{path}?{urllib.parse.urlencode(params)}")
    else:
        code, txt = http("POST", f"{BASE}/{path}", params)
    d = json.loads(txt or "{}")
    if code >= 400 or "error" in d:
        msg = d.get("error", {}).get("message", txt)
        raise SystemExit(f"Instagram API error on {path}: {msg}")  # never print the token
    return d

def is_live(slug):
    code, _ = http("GET", f"https://humasure.org/news/{slug}/")
    return code == 200

def wait_ready(container):
    for _ in range(30):
        st = graph("GET", container, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise SystemExit(f"container {container} status {st}")
        time.sleep(5)
    raise SystemExit(f"container {container} not ready in time")

def main():
    dry = os.environ.get("DRY_RUN") == "1"
    if not dry and not (os.environ.get("IG_USER_ID") and os.environ.get("IG_ACCESS_TOKEN")):
        print("Instagram secrets not set yet; nothing posted."); return
    posted = json.loads(STATE.read_text()) if STATE.exists() else {}
    max_posts = int(os.environ.get("MAX_POSTS", "1"))
    cutoff = (dt.date.today() - dt.timedelta(days=int(os.environ.get("MAX_AGE_DAYS", "14")))).isoformat()
    done = 0
    for f in sorted((ROOT / "posts").glob("*.json")):
        if done >= max_posts:
            break
        d = json.loads(f.read_text())
        sid = d["id"]
        if sid in posted or sid[:10] < cutoff:
            continue
        cards = [ROOT / "social" / sid / f"slide-{n}.jpg" for n in (1, 2, 3)]
        if not all(c.exists() for c in cards):
            print(f"skip {sid}: cards not generated yet"); continue
        if not is_live(d["slug"]):
            print(f"wait {sid}: not live on humasure.org yet (awaiting approval or sync)"); continue
        urls = [RAW.format(id=sid, n=n) for n in (1, 2, 3)]
        if not all(http("GET", u)[0] == 200 for u in urls):
            print(f"skip {sid}: card images not public yet"); continue
        caption = (ROOT / "social" / sid / "caption.txt").read_text(encoding="utf-8")
        if dry:
            print(f"DRY RUN would post {sid}\n  {urls}\n  caption: {caption[:80]}..."); done += 1; continue
        ig = os.environ["IG_USER_ID"]
        children = [graph("POST", f"{ig}/media", image_url=u, is_carousel_item="true")["id"] for u in urls]
        for c in children:
            wait_ready(c)
        parent = graph("POST", f"{ig}/media", media_type="CAROUSEL", children=",".join(children), caption=caption)["id"]
        wait_ready(parent)
        media = graph("POST", f"{ig}/media_publish", creation_id=parent)["id"]
        posted[sid] = {"media_id": media, "posted_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"}
        STATE.write_text(json.dumps(posted, indent=2) + "\n")
        print(f"posted {sid} as media {media}")
        done += 1
    if done == 0:
        print("nothing to post this run")

if __name__ == "__main__":
    main()
