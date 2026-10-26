#!/usr/bin/env python3
"""Build the public www.waltski.com page from Mark's private claude.ai "News" artifact.

Usage:  python3 scripts/build_public.py <artifact index.html> <output index.html>

The input is the page saved by the Artifact tool (action read, path "index.html").
The output is a standalone page for GitHub Pages. Changes from the private page:
  * the claude.ai publish skeleton is replaced with a normal <head>
  * the Ask Claude bar is hidden (it only works inside claude.ai)
  * the "Update now" button, its status line and its script are removed
  * the Shopping · Deal Watch section and its nav link are removed
  * the Snowbasin cams and the photo banner load the live cam images directly every 5 minutes,
    falling back to the snapshot baked into the page if a cam doesn't load
  * the Seahawks game strip polls ESPN's public scoreboard directly while a game is live
  * the header plays the Snowbasin time-lapse video instead of rotating photos (photos remain the fallback)

Between Claude's twice-daily refreshes, .github/workflows/update-data.yml runs scripts/update_data.py
(no Claude) to refresh the ticker, Markets cards, SpaceX chart, weather, game strip and cam snapshots.
"""
import re
import sys

src, out = sys.argv[1], sys.argv[2]
s = open(src, encoding="utf-8").read()


def must(cond, what):
    if not cond:
        sys.exit("build_public: could not find " + what)


# 1. Strip the publish skeleton: keep everything from <title> to the end, minus the closing tags.
i = s.find("<title>")
must(i >= 0, "<title>")
body = s[i:]
body = re.sub(r"\s*</body>\s*</html>\s*$", "\n", body)
body = re.sub(r"<title>.*?</title>", "", body, count=1, flags=re.S)
body = body.replace('<meta name="claude:viewport-fit-sides" content="cover">', "")

# 2. Remove the Update now button, its status line and its script.
body = re.sub(r'<button[^>]*id="wt-refresh"[^>]*>.*?</button>', "", body, count=1, flags=re.S)
body = re.sub(r'<div class="wt-refresh-msg"[^>]*>\s*</div>', "", body, count=1)
scripts = list(re.finditer(r"<script>(.*?)</script>", body, flags=re.S))
for m in reversed(scripts):
    if 'getElementById("wt-refresh")' in m.group(1):
        body = body[: m.start()] + body[m.end():]

# 3. Remove Shopping (section + nav link).
body = re.sub(r'\s*<!-- =+ SHOPPING[^>]*-->\s*<section id="shopping">.*?</section>', "\n", body, count=1, flags=re.S)
body = re.sub(r'<section id="shopping">.*?</section>', "", body, count=1, flags=re.S)
body = body.replace('<a href="#shopping">Shopping</a>', "")

# 4. Hide the Ask Claude bar (its code shares a script with the weather renderer, so only the bar is hidden).
public_css = """<style>
/* Public site: no Ask Claude bar */
#askbar{display:none!important;}
</style>
"""

# 5. Live cams straight from the cam hosts, refreshed every 5 minutes.
live_js = r"""<script>
/* Public site: load the Snowbasin cams and the photo banner straight from the cam hosts. */
(function(){
  var REFRESH = 5*60000, BANNER = ["ogden","jp","wildcat"];
  function now(){ try{ return new Date().toLocaleTimeString("en-US",{timeZone:"America/Denver",hour:"numeric",minute:"2-digit"}).replace("AM","a.m.").replace("PM","p.m.")+" MT"; }catch(e){ return ""; } }
  function load(){
    var figs = document.querySelectorAll("#cams figure.cam"), live = [], pending = figs.length;
    if(!pending) return;
    figs.forEach(function(fig){
      var k = fig.id.replace("cam-",""), a = fig.querySelector(".frame"), img = a && a.querySelector("img"), tag = a && a.querySelector(".cam-tag");
      if(!img || !a.href) { done(); return; }
      var url = a.href + (a.href.indexOf("?") < 0 ? "?" : "&") + "t=" + Date.now(), test = new Image();
      test.onload = function(){
        if(test.naturalWidth > 40){ img.src = url; if(tag){ tag.className = "cam-tag live"; tag.textContent = "Live"; } if(BANNER.indexOf(k) >= 0) live.push({k:k, src:url}); }
        done();
      };
      test.onerror = done;
      test.src = url;
    });
    function done(){
      if(--pending > 0) return;
      var st = document.getElementById("cams-status");
      if(live.length || document.querySelector("#cams .cam-tag.live")){ if(st){ st.textContent = "Live · " + now() + " · tap a frame to open it"; st.classList.remove("err"); } }
      if(live.length && window.wsjSetBanners){
        live.sort(function(x,y){ return BANNER.indexOf(x.k) - BANNER.indexOf(y.k); });
        try{ window.wsjSetBanners(live, new Date().toISOString()); localStorage.removeItem("wsj-banner-set"); }catch(e){}
      }
    }
  }
  var btn = document.getElementById("cams-refresh");
  if(btn){ btn.hidden = false; btn.addEventListener("click", load); }
  load();
  setInterval(function(){ if(!document.hidden) load(); }, REFRESH);
})();
/* Public site: live Seahawks score straight from ESPN's public scoreboard, every 30 seconds while the game strip shows a live game. */
(function(){
  var el = document.getElementById("sea-game");
  if(!el || !window.wsjSeaUpdate) return;
  var timer = null;
  function poll(){
    if(document.hidden) return;
    fetch("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard", {cache:"no-store"}).then(function(r){ return r.json(); }).then(function(j){
      (j.events || []).forEach(function(e){
        var c = e.competitions && e.competitions[0]; if(!c) return;
        var t = {}; (c.competitors || []).forEach(function(x){ t[x.homeAway] = x; });
        if(!t.home || !t.away || (t.home.team.abbreviation !== "SEA" && t.away.team.abbreviation !== "SEA")) return;
        window.wsjSeaUpdate({start: e.date, state: c.status.type.state, detail: c.status.type.shortDetail || "",
          away: t.away.team.abbreviation, awayScore: t.away.score == null ? "" : String(t.away.score),
          home: t.home.team.abbreviation, homeScore: t.home.score == null ? "" : String(t.home.score), espn: e.id ? String(e.id) : "",
          poss: (function(){ var si = c.situation || {}, id = String(si.possession || ""); return id === String(t.home.team.id) ? t.home.team.abbreviation : id === String(t.away.team.id) ? t.away.team.abbreviation : ""; })(),
          spot: (c.situation && c.situation.possessionText) || "", dd: (c.situation && c.situation.shortDownDistanceText) || "",
          lpTeam: (function(){ var lp = (c.situation && c.situation.lastPlay) || {}, id = String((lp.team && lp.team.id) || ""); return id === String(t.home.team.id) ? t.home.team.abbreviation : id === String(t.away.team.id) ? t.away.team.abbreviation : ""; })(),
          lpYds: c.situation && c.situation.lastPlay && c.situation.lastPlay.statYardage != null ? String(c.situation.lastPlay.statYardage) : "",
          lpType: (c.situation && c.situation.lastPlay && c.situation.lastPlay.type && c.situation.lastPlay.type.text) || "",
          lpText: (c.situation && c.situation.lastPlay && c.situation.lastPlay.text) || "",
          awayRec: (t.away.records && t.away.records[0] && t.away.records[0].summary) || "", homeRec: (t.home.records && t.home.records[0] && t.home.records[0].summary) || ""});
      });
      if(!el.querySelector(".sg-st.live") && timer){ clearInterval(timer); timer = null; }
    }).catch(function(){});
  }
  if(el.querySelector(".sg-st.live")){ poll(); timer = setInterval(poll, 30000); document.addEventListener("visibilitychange", function(){ if(!document.hidden && timer) poll(); }); }
})();
</script>
"""
must(body.count("</style>") >= 1, "</style>")

# 6. Header time-lapse video (Mark's pick, Oct 25, 2026): plays the Snowbasin time-lapse behind the header in place of the
#    rotating photos. The file is rebuilt about hourly at the source, so the page reloads it every hour. If the video can't
#    play (blocked, Low Power Mode, reduced motion or data saver), the rotating cam photos stay as they are.
VIDEO_SRC = "https://storage.googleapis.com/prism-cam-00054/running/00054_timelapse_1080.mp4"
video_css = """<style>
/* Public site: Snowbasin time-lapse video behind the header (falls back to the rotating cam photos) */
#wt-banner video{position:absolute; inset:0; width:100%; height:100%; object-fit:cover; object-position:center 38%; opacity:0; transition:opacity 1.2s ease; z-index:0; pointer-events:none;}
html.has-video #wt-banner video{opacity:1;}
html.has-video #wt-banner .bl{opacity:0!important;}
html.has-video .wt-banner-cap{display:none;}
html.has-video .wt-vid-cap{display:block;}
.wt-vid-cap{display:none; z-index:2; position:absolute; right:10px; bottom:6px; font:500 10px var(--font-body); letter-spacing:.06em; color:rgba(255,255,255,.85); text-shadow:0 1px 2px rgba(0,0,0,.8);}
html.has-video #wt-next, html.has-video .wt-next-sep{display:none;}
</style>
"""
video_js = """<script>
/* Public site: play the Snowbasin time-lapse behind the header instead of rotating photos; reload it hourly; it plays at quarter speed. */
(function(){
  var SRC = "%s";
  var b = document.getElementById("wt-banner"), root = document.documentElement;
  if(!b) return;
  try{
    if(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if(navigator.connection && navigator.connection.saveData) return;
  }catch(e){}
  var nb = document.getElementById("wt-next");
  if(nb && nb.previousElementSibling && nb.previousElementSibling.classList.contains("wt-sep2")) nb.previousElementSibling.classList.add("wt-next-sep");
  var cap = document.createElement("span"); cap.className = "wt-vid-cap"; cap.textContent = "Snowbasin \\u00b7 time-lapse"; b.appendChild(cap);
  var v = document.createElement("video");
  v.muted = true; v.defaultMuted = true; v.autoplay = true; v.loop = true; v.playsInline = true; v.preload = "auto";
  v.setAttribute("muted", ""); v.setAttribute("playsinline", ""); v.setAttribute("aria-hidden", "true"); v.setAttribute("disablepictureinpicture", "");
  /* Play the time-lapse at quarter speed (Mark asked for it slower, twice). Reapplied whenever the video (re)loads. */
  var RATE = 0.25;
  function slow(){ try{ v.defaultPlaybackRate = RATE; v.playbackRate = RATE; }catch(e){} }
  v.addEventListener("loadedmetadata", slow);
  v.addEventListener("playing", function(){ slow(); root.classList.add("has-banner", "has-video"); });
  v.addEventListener("error", function(){ root.classList.remove("has-video"); });
  v.src = SRC; slow();
  b.insertBefore(v, b.firstChild);
  function go(){ var p = v.play(); if(p && p.catch) p.catch(function(){}); }
  go();
  document.addEventListener("visibilitychange", function(){ if(!document.hidden && v.paused) go(); });
  setInterval(function(){ if(document.hidden) return; v.src = SRC + "?t=" + Date.now(); go(); }, 60*60000);
})();
</script>
""" % VIDEO_SRC

head = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>The Walt Ski Journal</title>
<meta name="description" content="The Walt Ski Journal — markets, economy, top stories, Wasatch snow and weather, refreshed four times a day.">
<meta property="og:title" content="The Walt Ski Journal">
<meta property="og:description" content="Markets, economy, top stories, Wasatch snow and weather — refreshed four times a day.">
<meta name="theme-color" content="#000000">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 40'%3E%3Cpath d='M2 38 L22 10 L32 22 L42 6 L62 38 Z' fill='%23E2733A'/%3E%3C/svg%3E">
"""

# Keep the page's own <style>/<link> tags where they are (browsers accept them in the body); close head first.
page = head + public_css + video_css + "</head>\n<body>\n" + body.strip() + "\n" + live_js + video_js + "</body>\n</html>\n"

open(out, "w", encoding="utf-8").write(page)
print("build_public: wrote", out, len(page), "bytes")
