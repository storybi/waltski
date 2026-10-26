"""Sunday's sermon at the top of Morning Devotion on www.waltski.com (Mark, Oct 26, 2026).

The newest Sunday sermon from Washington Heights Church (youtube.com/@washingtonheightschurch, channel
UCVrrcXPrnh-Qv_hV_GdGC9g) plays in an embedded YouTube player right on the page.

  * inject(html, sermon)  adds the player block, its CSS and script to the page (used by build_public.py).
                          Idempotent: a page that already has the block only gets its SERMON value updated.
  * pick(feed_xml)        chooses last Sunday's sermon from the channel's RSS feed (used by update_data.py).

The church posts several videos each Sunday: the 9 AM and 11 AM livestreams ("Title | 9 AM | Series") and a
sermon-only cut ("Title | Series") in 16:9, plus a 4:3 copy. pick() takes the newest Sunday (Mountain time) that
has any service video and prefers its 16:9 sermon-only cut, falling back to the 9 AM, then the 11 AM livestream.
"""
import datetime as dt
import html as _h
import json
import re
import urllib.request
from zoneinfo import ZoneInfo

CHANNEL = "UCVrrcXPrnh-Qv_hV_GdGC9g"
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id=" + CHANNEL
CHANNEL_URL = "https://www.youtube.com/@washingtonheightschurch"
MT = ZoneInfo("America/Denver")
UA = {"User-Agent": "Mozilla/5.0"}

# Last Sunday (Oct 25, 2026) — used until the live-data job writes a newer one.
DEFAULT = {"id": "jTIyPCtUmWI", "title": "Ask Me Again | Hidden in Plain Sight", "date": "2026-10-25"}


def _aspect(vid):
    """Width/height of a video from YouTube's oEmbed, or None."""
    try:
        u = "https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v=" + vid
        d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=15))
        return float(d["width"]) / float(d["height"])
    except Exception:  # noqa: BLE001
        return None


def pick(x):
    entries = []
    for e in re.findall(r"<entry>(.*?)</entry>", x, re.S):
        vid = re.search(r"<yt:videoId>(.*?)</yt:videoId>", e)
        pub = re.search(r"<published>(.*?)</published>", e)
        tit = re.search(r"<title>(.*?)</title>", e, re.S)
        link = re.search(r'<link rel="alternate" href="(.*?)"', e)
        if not (vid and pub and tit) or (link and "/shorts/" in link.group(1)):
            continue
        title = " ".join(_h.unescape(tit.group(1)).split())
        if "kidz" in title.lower() or "|" not in title:
            continue
        when = dt.datetime.fromisoformat(pub.group(1)).astimezone(MT)
        if when.weekday() != 6:  # Sundays only (Mountain time)
            continue
        am = re.search(r"\b(9|11)\s*AM\b", title, re.I)
        entries.append({"id": vid.group(1), "title": title, "when": when, "am": am.group(1) if am else None})
    if not entries:
        return None
    day = max(e["when"].date() for e in entries)
    same = sorted([e for e in entries if e["when"].date() == day], key=lambda e: e["when"])
    cuts = [e for e in same if not e["am"]]
    choice = None
    for e in cuts:
        a = _aspect(e["id"])
        if a and a > 1.6:
            choice = e
            break
    if not choice:
        streams = [e for e in same if e["am"] == "9"] or [e for e in same if e["am"] == "11"] or cuts
        choice = streams[0]
    title = re.sub(r"\s*\|\s*(9|11)\s*AM\s*", " | ", choice["title"], flags=re.I).strip(" |")
    return {"id": choice["id"], "title": title, "date": day.isoformat()}


CSS = """<style id="sermon-css">
/* Sunday's sermon at the top of Morning Devotion (Mark, Oct 26, 2026) */
.sermon{margin:0 0 18px; background:var(--surface); border:1px solid var(--border); border-left:3px solid var(--accent);}
.sermon-head{display:flex; justify-content:space-between; align-items:baseline; gap:12px; padding:10px 14px 8px;}
.sermon-head h3{margin:0; font:700 15px/1.3 var(--font-body);}
.sermon-date{font:500 12px var(--font-body); color:var(--fg-muted); white-space:nowrap;}
.sermon-frame{position:relative; aspect-ratio:16/9; background:#000; overflow:hidden;}
.sermon-frame iframe{position:absolute; inset:0; width:100%; height:100%; border:0;}
.sermon-foot{display:flex; justify-content:space-between; align-items:baseline; gap:12px; padding:8px 14px 10px; font:600 13px/1.4 var(--font-body);}
.sermon-foot a{font-weight:500; white-space:nowrap;}
</style>
"""

BLOCK = """
    <!-- Sunday's sermon (added Oct 26, 2026) — rendered by the "Sunday's sermon" script from SERMON; refreshed by the live-data job. -->
    <div class="sermon" id="sermon">
      <div class="sermon-head"><h3>Sunday&rsquo;s Sermon &middot; Washington Heights Church</h3><span class="sermon-date" id="sermon-date"></span></div>
      <div class="sermon-frame" id="sermon-frame"></div>
      <div class="sermon-foot"><span id="sermon-title"></span><a href="@@CH@@" target="_blank" rel="noopener">WHC on YouTube &rarr;</a></div>
    </div>""".replace("@@CH@@", CHANNEL_URL)

JS = """<script>
/* Sunday's sermon (Mark, Oct 26, 2026): plays in an embedded YouTube player so the page stays put. SERMON is rewritten
   by scripts/update_data.py from the church's RSS feed. */
(function(){
  var SERMON = @@SERMON@@;
  var fr = document.getElementById("sermon-frame"), ti = document.getElementById("sermon-title"), da = document.getElementById("sermon-date");
  if(!fr || !SERMON || !SERMON.id) return;
  function esc(x){ return String(x == null ? "" : x).replace(/[&<>"]/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]; }); }
  if(ti) ti.textContent = SERMON.title || "";
  try{ if(da && SERMON.date) da.textContent = new Date(SERMON.date + "T12:00:00").toLocaleDateString("en-US",{weekday:"short", month:"short", day:"numeric"}); }catch(e){}
  fr.innerHTML = '<iframe src="https://www.youtube.com/embed/' + encodeURIComponent(SERMON.id) + '?rel=0&modestbranding=1&playsinline=1" title="' + esc(SERMON.title) + '" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>';
})();
</script>
"""


def _json(v):
    return json.dumps(v, ensure_ascii=False, separators=(",", ":"))


def inject(page, sermon=None):
    sermon = sermon or DEFAULT
    if 'id="sermon"' in page:
        return re.sub(r"var SERMON = \{.*?\};", lambda m: "var SERMON = " + _json(sermon) + ";", page, count=1)
    m = re.search(r'(<section id="daily-word">\s*<div class="section-head">.*?</div>\s*</div>)', page, re.S)
    if not m:
        raise SystemExit("sermon: could not find the Morning Devotion section head")
    page = page[: m.end()] + BLOCK + page[m.end():]
    page = page.replace("</head>", CSS + "</head>", 1) if "</head>" in page else CSS + page
    js = JS.replace("@@SERMON@@", _json(sermon))
    i = page.rfind("</body>")
    return page[:i] + js + page[i:] if i >= 0 else page + js


def current(page):
    """The SERMON value already in a page, or None."""
    m = re.search(r"var SERMON = (\{.*?\});", page)
    try:
        return json.loads(m.group(1)) if m else None
    except Exception:  # noqa: BLE001
        return None
