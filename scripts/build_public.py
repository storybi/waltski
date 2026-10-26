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

# 6. Header time-lapse (Mark's design, Oct 25, 2026): the header shows the LAST frame of Snowbasin's hourly time-lapse (the
#    newest picture), fetched fresh on every page load; a "Play Timelapse" link in the dateline (where Next Photo was) plays the
#    whole video once, then returns to the last frame. If the video can't load, the rotating cam photos stay as they are.
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
html:not(.has-video) .wt-play, html:not(.has-video) .wt-play-sep{display:none;}
</style>
"""
video_js = r"""<script>
/* Public site: the header shows the LAST frame of Snowbasin's hourly time-lapse (the newest picture) instead of rotating photos.
   Every page load fetches a fresh copy (cache-busted) and parks on its final frame; the dateline's "Play Timelapse" link plays the
   whole time-lapse once at PLAY_RATE, then returns to the last frame. If the video can't load, the rotating cam photos stay. */
(function(){
  var SRC = "@@SRC@@";
  var PLAY_RATE = 0.25;            /* speed of the one-time play (1 = normal) */
  var b = document.getElementById("wt-banner"), root = document.documentElement;
  if(!b) return;
  var nb = document.getElementById("wt-next");
  if(nb && nb.previousElementSibling && nb.previousElementSibling.classList.contains("wt-sep2")) nb.previousElementSibling.classList.add("wt-next-sep");
  var cap = document.createElement("span"); cap.className = "wt-vid-cap"; cap.textContent = "Snowbasin · latest time-lapse frame"; b.appendChild(cap);
  /* "Play Timelapse" link where Next Photo was */
  var sep = document.createElement("span"); sep.className = "wt-sep2 wt-play-sep"; sep.setAttribute("aria-hidden", "true"); sep.textContent = "|";
  var btn = document.createElement("button"); btn.type = "button"; btn.className = "wt-next wt-play"; btn.textContent = "Play Timelapse";
  btn.title = "Play today's Snowbasin time-lapse once";
  if(nb && nb.parentNode){ nb.parentNode.insertBefore(btn, nb.nextSibling); nb.parentNode.insertBefore(sep, btn); }
  var v = document.createElement("video");
  v.muted = true; v.defaultMuted = true; v.loop = false; v.playsInline = true; v.preload = "auto";
  v.setAttribute("muted", ""); v.setAttribute("playsinline", ""); v.setAttribute("aria-hidden", "true"); v.setAttribute("disablepictureinpicture", "");
  b.insertBefore(v, b.firstChild);
  var playing = false, ready = false;
  function when(d){ try{ return d.toLocaleTimeString("en-US",{timeZone:"America/Denver",hour:"numeric",minute:"2-digit"}).replace("AM","a.m.").replace("PM","p.m.") + " MT"; }catch(e){ return ""; } }
  function toLast(){
    if(!v.duration || isNaN(v.duration)) return;
    try{ v.pause(); v.currentTime = Math.max(0, v.duration - 0.04); }catch(e){}
  }
  function stopPlay(){
    playing = false; btn.textContent = "Play Timelapse"; toLast();
  }
  v.addEventListener("loadedmetadata", function(){
    if(playing) return;
    /* iPhones only paint a frame after playback has started, so start muted and jump straight to the end. */
    var p = null; try{ p = v.play(); }catch(e){}
    if(p && p.then) p.then(toLast, toLast); else toLast();
  });
  v.addEventListener("seeked", function(){
    if(playing) return;
    ready = true; root.classList.add("has-banner", "has-video");
  });
  v.addEventListener("ended", stopPlay);
  v.addEventListener("error", function(){ if(!ready) root.classList.remove("has-video"); });
  btn.addEventListener("click", function(){
    if(!ready) return;
    if(playing){ stopPlay(); return; }
    playing = true; btn.textContent = "Stop";
    try{ v.currentTime = 0; v.playbackRate = PLAY_RATE; }catch(e){}
    var p = v.play(); if(p && p.catch) p.catch(function(){ stopPlay(); });
  });
  function load(){
    if(playing) return;
    var url = SRC + "?t=" + Date.now();   /* fresh copy on every page load, so the last frame is the newest picture */
    ready = false;
    v.src = url; v.load();
    try{
      fetch(url, {method: "HEAD", cache: "no-store"}).then(function(r){
        var lm = r.headers.get("Last-Modified");
        if(lm) cap.textContent = "Snowbasin · latest time-lapse frame · updated " + when(new Date(lm));
      }).catch(function(){});
    }catch(e){}
  }
  load();
  setInterval(function(){ if(!document.hidden && !playing) load(); }, 60*60000);   /* the source updates hourly */
})();
</script>
""".replace("@@SRC@@", VIDEO_SRC)

head = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Walt Ski News</title>
<meta name="description" content="Walt Ski News — markets, economy, top stories, Wasatch snow and weather, refreshed four times a day.">
<meta property="og:title" content="Walt Ski News">
<meta property="og:description" content="Markets, economy, top stories, Wasatch snow and weather — refreshed four times a day.">
<meta name="theme-color" content="#000000">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 40'%3E%3Cpath d='M2 38 L22 10 L32 22 L42 6 L62 38 Z' fill='%23E2733A'/%3E%3C/svg%3E">
"""

# Keep the page's own <style>/<link> tags where they are (browsers accept them in the body); close head first.
page = head + public_css + video_css + "</head>\n<body>\n" + body.strip() + "\n" + live_js + video_js + "</body>\n</html>\n"

open(out, "w", encoding="utf-8").write(page)
print("build_public: wrote", out, len(page), "bytes")
