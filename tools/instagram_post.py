#!/usr/bin/env python3
"""Post Humasure News carousels to Instagram, one story at a time, only once the story is live on humasure.org.

Environment:
  IG_USER_ID       Instagram professional account ID (linked to the Humasure Facebook Page)
  IG_ACCESS_TOKEN  Page access token with instagram_basic and instagram_content_publish
  GRAPH_BASE       default https://graph.facebook.com/v26.0
  MAX_POSTS        stories to post this run (default 1)
  MAX_AGE_DAYS     ignore stories older than this (default 14)
  DRY_RUN=1        show what would be posted, post nothing
  FB_PAGE_ID       Facebook Page to mirror each post to (default 1504545736066506, the Humasure Ai Page).
                   Needs pages_manage_posts on the same Page token. Set FB_MIRROR=0 to switch mirroring off.

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
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")

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

FB_PAGE = os.environ.get("FB_PAGE_ID", "1504545736066506")

def fb_caption(d, caption):
    """Facebook shows clickable links, so swap 'link in bio' for the story's own address."""
    url = f"https://humasure.org/news/{d['slug']}/"
    return caption.replace("Full story and sources at humasure.org/news (link in bio).", f"Full story and sources: {url}")

def post_facebook(sid, d, urls, caption):
    photos = [graph("POST", f"{FB_PAGE}/photos", url=u, published="false")["id"] for u in urls]
    params = {"message": fb_caption(d, caption)}
    for i, pid in enumerate(photos):
        params[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    return graph("POST", f"{FB_PAGE}/feed", **params)["id"]

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
        if not all(http("HEAD", u)[0] == 200 for u in urls):
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
        print("nothing new for Instagram this run")
    if os.environ.get("FB_MIRROR", "1") == "1" and not dry:
        mirrored = 0
        for sid, rec in sorted(posted.items()):
            if rec.get("fb_post_id") or rec.get("fb_skip") or mirrored >= max_posts + 1:
                continue
            f = ROOT / "posts" / f"{sid}.json"
            if not f.exists():
                continue
            d = json.loads(f.read_text())
            urls = [RAW.format(id=sid, n=n) for n in (1, 2, 3)]
            caption = (ROOT / "social" / sid / "caption.txt").read_text(encoding="utf-8")
            try:
                rec["fb_post_id"] = post_facebook(sid, d, urls, caption)
                rec["fb_posted_at"] = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
                print(f"mirrored {sid} to Facebook as {rec['fb_post_id']}")
                mirrored += 1
            except SystemExit as e:
                print(f"::warning::Facebook mirror failed for {sid}: {e}")
                break
        STATE.write_text(json.dumps(posted, indent=2) + "\n")

if __name__ == "__main__":
    main()
