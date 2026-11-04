#!/usr/bin/env python3
"""Make Instagram carousel images (1080x1350) and a caption for newsroom stories.

Usage: python3 tools/social_cards.py posts/<id>.json [...]   (default: posts changed in the last commit; --missing: every post without cards)
Output: social/<id>/slide-1..3.png (preview), slide-1..3.jpg (for Instagram) and caption.txt
Needs: pip install playwright (Chromium available).
"""
import html, json, os, re, subprocess, sys, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = (ROOT / "tools" / "fonts").as_uri()
DIRNAMES = {"D1": "Always stoppable", "D2": "Bounded autonomy", "D3": "Physical safety", "D4": "Honest identity",
            "D5": "Private by default", "D6": "Secure and supported", "D7": "No manipulation", "D8": "Fair treatment",
            "D9": "Accountable", "D10": "Safe for its whole life"}
REGIONS = {"United Kingdom", "Singapore", "China", "Canada", "European Union", "Japan", "India", "Australia", "South Korea",
           "United States", "Brazil", "global", "Germany", "France", "UAE", "Nigeria", "Kenya", "South Africa", "Mexico"}
def mark(bg, fg):
    return ('<svg viewBox="0 0 120 120" width="64" height="64">'
            f'<circle cx="60" cy="60" r="58" fill="{bg}"/>'
            f'<g transform="translate(0 -4)" fill="none" stroke="{fg}" stroke-width="10" stroke-linecap="round">'
            '<path d="M37.06 31.23 A40 40 0 1 0 82.94 31.23"/><line x1="60" y1="42" x2="60" y2="70"/>'
            f'<circle cx="60" cy="21" r="8" fill="{fg}" stroke="none"/></g></svg>')
CSS = f"""
@font-face{{font-family:B;font-weight:700;src:url({FONTS}/bricolage-grotesque-700.woff2)}}
@font-face{{font-family:A;font-weight:400;src:url({FONTS}/atkinson-hyperlegible-400.woff2)}}
@font-face{{font-family:A;font-weight:700;src:url({FONTS}/atkinson-hyperlegible-700.woff2)}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1080px;height:1350px;font-family:A,sans-serif}}
.s{{width:1080px;height:1350px;padding:84px 84px 72px;display:flex;flex-direction:column;overflow:hidden}}
.dark{{background:#145C39;color:#F4F8F5}} .light{{background:#F7F9F6;color:#17171A}} .tint{{background:#EAF3EC;color:#17171A}}
.top{{display:flex;align-items:center;gap:18px}}
.bn{{font-family:B;font-weight:700;font-size:40px;line-height:1}} .tg{{font-size:17px;letter-spacing:.18em;font-weight:700;color:#8ED1A8;margin-top:6px}}
.eb{{font-size:26px;font-weight:700;letter-spacing:.14em;text-transform:uppercase}}
.dark .eb{{color:#8ED1A8}} .light .eb,.tint .eb{{color:#1F7A4D}} .light .tg,.tint .tg{{color:#1F7A4D}}
h1{{font-family:B;font-weight:700;font-size:var(--h,84px);line-height:1.05;letter-spacing:-1px}}
.body{{font-size:44px;line-height:1.35}}
.chips{{display:flex;flex-wrap:wrap;gap:14px}}
.chip{{font-size:28px;font-weight:700;padding:12px 22px;border-radius:999px;background:#F4F8F5;color:#145C39}}
.light .chip,.tint .chip{{background:#145C39;color:#F4F8F5}}
.foot{{margin-top:auto;display:flex;justify-content:space-between;font-size:26px;opacity:.8}}
.mid{{margin:auto 0;display:flex;flex-direction:column;gap:36px}}
.cta{{font-family:B;font-weight:700;font-size:64px;line-height:1.1}}
"""

def region(d):
    for t in d.get("tags", []):
        if t in REGIONS:
            return "Global" if t == "global" else t
    return "Global"

def first_section(body):
    """Text of the first h2 section, as up to 3 short points."""
    m = re.search(r"<h2>(.*?)</h2>(.*?)(?=<h2>|$)", body, re.S)
    if not m:
        return None, []
    head = re.sub("<[^>]+>", "", m.group(1)).strip()
    items = re.findall(r"<li>(.*?)</li>", m.group(2), re.S)
    pts = [re.sub("<[^>]+>", "", i).strip() for i in items][:3]
    while pts and sum(len(p) for p in pts) > 430:
        pts = pts[:-1]
    if any(len(p) > 230 for p in pts):
        return head, []
    return head, pts

def slides(d):
    e = html.escape
    reg, dirs = region(d), d.get("directives", [])[:3]
    chips = "".join(f'<span class="chip">{x} {e(DIRNAMES.get(x, ""))}</span>' for x in dirs)
    hsize = 84 if len(d["title"]) <= 60 else 72
    def top(dark):
        m = mark("#F4F8F5", "#145C39") if dark else mark("#145C39", "#F4F8F5")
        return f'<div class="top">{m}<div><div class="bn">Humasure</div><div class="tg">HUMAN IN CHARGE</div></div></div>'
    s1 = (f'<div class="s dark">{top(True)}<div class="mid"><p class="eb">Humasure News · {e(reg)}</p>'
          f'<h1 style="--h:{hsize}px">{e(d["title"])}</h1><div class="chips">{chips}</div></div>'
          f'<div class="foot"><span>Swipe →</span><span>humasure.org/news</span></div></div>')
    head, pts = first_section(d["body_html"])
    if pts:
        li = "".join(f'<li style="margin-bottom:22px">{e(p)}</li>' for p in pts)
        inner = f'<p class="eb">{e(head)}</p><ul class="body" style="padding-left:40px;font-size:38px">{li}</ul>'
    else:
        inner = f'<p class="eb">What happened</p><p class="body">{e(d["excerpt"])}</p>'
    s2 = f'<div class="s light">{top(False)}<div class="mid">{inner}</div><div class="foot"><span>{e(reg)}</span><span>2 / 3</span></div></div>'
    dirlines = "".join(f'<p class="body" style="font-size:38px"><b>{x}</b> {e(DIRNAMES.get(x, ""))}</p>' for x in dirs)
    s3 = (f'<div class="s tint">{top(False)}<div class="mid"><p class="eb">Why it matters</p>'
          f'<p class="body">People stay in charge only when AI and robots meet clear, tested rules.</p>{dirlines}'
          f'<p class="cta">Full story and sources: link in bio</p></div>'
          f'<div class="foot"><span>humasure.org/news</span><span>3 / 3</span></div></div>')
    return [s1, s2, s3]

def caption(d):
    reg = region(d)
    dirs = ", ".join(f"{x} {DIRNAMES.get(x, '')}" for x in d.get("directives", [])[:3])
    tags = ["#HumanInCharge", "#AISafety", "#RobotSafety"]
    extra = {"Regulation": "#AIRegulation", "Research": "#AIResearch"}.get(d.get("category"))
    if extra: tags.append(extra)
    if reg != "Global": tags.append("#" + re.sub(r"[^A-Za-z]", "", reg))
    srcs = "; ".join(s["title"].split(":")[0] for s in d.get("sources", [])[:3])
    return (f"{d['title']}\n\n{d['excerpt']}\n\nWhy it matters: {dirs}.\n\n"
            f"Full story and sources at humasure.org/news (link in bio).\nSources: {srcs}.\n\n" + " ".join(tags))

def main(files):
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for f in files:
            d = json.load(open(f))
            out = ROOT / "social" / d["id"]
            out.mkdir(parents=True, exist_ok=True)
            for i, s in enumerate(slides(d), 1):
                tmp = ROOT / "tools" / ".card.html"
                tmp.write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{s}</body></html>", encoding="utf-8")
                pg.goto(tmp.as_uri())
                pg.evaluate("document.fonts.ready")
                pg.wait_for_timeout(200)
                over = pg.evaluate("(() => {const s=document.querySelector('.s');return s.scrollHeight-s.clientHeight})()")
                if over > 0:
                    print(f"WARNING {d['id']} slide {i} overflows by {over}px")
                pg.screenshot(path=str(out / f"slide-{i}.png"))
                # Instagram's API accepts JPEG only
                pg.screenshot(path=str(out / f"slide-{i}.jpg"), type="jpeg", quality=92)
            (out / "caption.txt").write_text(caption(d), encoding="utf-8")
            print("made", out.relative_to(ROOT))
        (ROOT / "tools" / ".card.html").unlink(missing_ok=True)
        b.close()

if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--missing"]:
        args = [str(p) for p in sorted((ROOT / "posts").glob("*.json"))
                if not (ROOT / "social" / p.stem / "slide-3.jpg").exists()]
        if not args:
            print("all cards present"); sys.exit(0)
    elif not args:
        diff = subprocess.run(["git", "diff", "--name-only", "HEAD~1", "HEAD", "--", "posts/"], capture_output=True, text=True, cwd=ROOT).stdout.split()
        args = [str(ROOT / p) for p in diff if p.endswith(".json")]
    main(args)
