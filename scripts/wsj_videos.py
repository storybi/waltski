#!/usr/bin/env python3
"""Newest Wall Street Journal YouTube videos for the WSJ Video section at the top of the Other News page (Mark, Oct 28, 2026).

Reads the channel's Videos tab (https://www.youtube.com/@wsj/videos — long-form uploads, no Shorts), newest first.
YouTube's RSS feeds were returning 404 when this was set up, so the page's ytInitialData is used instead.

Used two ways:
  * scripts/update_data.py imports do_wsj() and rewrites `var WSJV` in index.html (hourly job);
  * `python3 scripts/wsj_videos.py` prints the `var WSJV = …;` line, for Claude's daily artifact refresh.

WSJV = {"asof": "Wed 8:05 p.m. MT", "v": [[videoId, title, "11h ago"], ...]}   (newest first, up to 30)
"""
import datetime as dt
import json
import re
import sys
import urllib.request
from zoneinfo import ZoneInfo

MT = ZoneInfo("America/Denver")
URL = "https://www.youtube.com/@wsj/videos"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}


def fetch():
    t = urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=30).read().decode("utf-8", "ignore")
    m = re.search(r"ytInitialData\s*=\s*(\{.*?\});\s*</script>", t, re.S)
    if not m:
        raise ValueError("ytInitialData not found")
    data = json.loads(m.group(1))
    items = []

    def walk(o):
        if isinstance(o, dict):
            if "richItemRenderer" in o:
                items.append(o["richItemRenderer"].get("content", {}))
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(data)
    out, seen = [], set()
    for it in items:
        if "lockupViewModel" in it:
            lv = it["lockupViewModel"]
            vid = lv.get("contentId")
            md = (lv.get("metadata") or {}).get("lockupMetadataViewModel") or {}
            title = (md.get("title") or {}).get("content") or ""
            parts = [((p.get("text") or {}).get("content") or "")
                     for r in ((md.get("metadata") or {}).get("contentMetadataViewModel") or {}).get("metadataRows", [])
                     for p in r.get("metadataParts", [])]
            ago = next((p for p in parts if "ago" in p), "")
        elif "videoRenderer" in it:  # older page layout
            v = it["videoRenderer"]
            vid = v.get("videoId")
            title = "".join(r.get("text", "") for r in (v.get("title") or {}).get("runs", []))
            ago = (v.get("publishedTimeText") or {}).get("simpleText", "")
        else:
            continue
        if vid and re.fullmatch(r"[\w-]{11}", vid) and vid not in seen:
            seen.add(vid)
            out.append([vid, title.strip(), ago.strip()])
    if not out:
        raise ValueError("no videos found")
    asof = dt.datetime.now(MT).strftime("%a %-I:%M %p MT").replace("AM", "a.m.").replace("PM", "p.m.")
    return {"asof": asof, "v": out[:30]}


def do_wsj(s, now_mt=None, set_var=None, get_var=None):
    """Hook for scripts/update_data.py: rewrite WSJV in the page text s (keeps the old list if YouTube fails)."""
    try:
        w = fetch()
    except Exception as e:  # noqa: BLE001
        print("  wsj videos failed:", e)
        return s
    s, ok = set_var(s, "WSJV", json.dumps(w, ensure_ascii=False, separators=(",", ":")))
    print("  wsj videos: %d (newest %s)" % (len(w["v"]), w["v"][0][0]) if ok else "  wsj videos: WSJV not in page")
    return s


if __name__ == "__main__":
    print("var WSJV = %s;" % json.dumps(fetch(), ensure_ascii=False, separators=(",", ":")))
