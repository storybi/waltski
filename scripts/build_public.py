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
  * the header shows the live Needles cam picture (refreshed every minute) with a Watch Live link (photos remain the fallback)

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
body = re.sub(r'<a href="#shopping">[^<]*</a>', "", body)

# 4. Hide the Ask Claude bar (its code shares a script with the weather renderer, so only the bar is hidden).
public_css = """<style>
/* Public site: no Ask Claude bar */
#askbar{display:none!important;}
</style>
"""

# 4b. Free Google search bar at the top of the sticky dock (Mark, Oct 26, 2026) — the public site has no Ask Claude bar, so this
#     takes its place: "Search" opens Google results, "AI Mode" opens Google's free AI answers (udm=50), both in a new tab.
GBAR_HTML = """
  <form class="gbar" id="gbar" action="https://www.google.com/search" method="get" target="_blank" rel="noopener" role="search">
    <svg class="gbar-g" viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2.2"/><path d="M15.5 15.5L21 21" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>
    <input type="search" name="q" placeholder="Search Google…" aria-label="Search Google" autocomplete="off" required>
    <button type="submit">Search</button>
    <button type="submit" class="gbar-ai" name="udm" value="50" title="Google AI Mode">AI Mode</button>
  </form>"""
GBAR_CSS = """<style>
/* Public site: free Google search bar at the top of the sticky dock */
.gbar{display:flex; align-items:center; gap:6px; margin:0; padding:5px 6px 5px 10px; background-color:var(--bg); border:1px solid var(--border); border-bottom:0;}
@media (prefers-color-scheme: light){ :root:not([data-theme="dark"]) .gbar{background-image:var(--paper);} }
:root[data-theme="light"] .gbar{background-image:var(--paper);}
.gbar-g{width:16px; height:16px; flex:none; color:var(--fg-faint);}
.gbar input{flex:1; min-width:0; border:0; outline:0; background:transparent; color:var(--fg); font:15px var(--font-body); padding:6px 2px;}
.gbar input::placeholder{color:var(--fg-faint);}
.gbar button{font:600 12.5px var(--font-body); border:1px solid var(--border); background:var(--surface); color:var(--fg); padding:6px 10px; cursor:pointer; white-space:nowrap;}
.gbar button:hover{border-color:var(--fg-muted);}
.gbar .gbar-ai{background:var(--accent); border-color:var(--accent); color:#fff;}
@media (max-width:420px){ .gbar button{padding:6px 7px; font-size:12px;} }
</style>
"""
DOCK = '<div class="wt-dock" id="wt-dock">'
must(body.count(DOCK) == 1, "wt-dock")
body = body.replace(DOCK, DOCK + GBAR_HTML, 1)
public_css += GBAR_CSS

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
/* Public site: live Oregon Ducks score straight from ESPN's public college scoreboard, every 30 seconds while the Ducks strip shows a live game. */
(function(){
  var el = document.getElementById("ore-game");
  if(!el || !window.wsjOreUpdate) return;
  var timer = null;
  function poll(){
    if(document.hidden) return;
    fetch("https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?groups=80&limit=300", {cache:"no-store"}).then(function(r){ return r.json(); }).then(function(j){
      (j.events || []).forEach(function(e){
        var c = e.competitions && e.competitions[0]; if(!c) return;
        var t = {}; (c.competitors || []).forEach(function(x){ t[x.homeAway] = x; });
        if(!t.home || !t.away || (t.home.team.abbreviation !== "ORE" && t.away.team.abbreviation !== "ORE")) return;
        window.wsjOreUpdate({start: e.date, state: c.status.type.state, detail: c.status.type.shortDetail || "",
          away: t.away.team.abbreviation, awayScore: t.away.score == null ? "" : String(t.away.score),
          home: t.home.team.abbreviation, homeScore: t.home.score == null ? "" : String(t.home.score), espn: e.id ? String(e.id) : "",
          poss: (function(){ var si = c.situation || {}, id = String(si.possession || ""); return id === String(t.home.team.id) ? t.home.team.abbreviation : id === String(t.away.team.id) ? t.away.team.abbreviation : ""; })(),
          spot: (c.situation && c.situation.possessionText) || "", dd: (c.situation && c.situation.shortDownDistanceText) || "",
          lpTeam: (function(){ var lp = (c.situation && c.situation.lastPlay) || {}, id = String((lp.team && lp.team.id) || ""); return id === String(t.home.team.id) ? t.home.team.abbreviation : id === String(t.away.team.id) ? t.away.team.abbreviation : ""; })(),
          lpYds: c.situation && c.situation.lastPlay && c.situation.lastPlay.statYardage != null ? String(c.situation.lastPlay.statYardage) : "",
          lpType: (c.situation && c.situation.lastPlay && c.situation.lastPlay.type && c.situation.lastPlay.type.text) || "",
          lpText: (c.situation && c.situation.lastPlay && c.situation.lastPlay.text) || "",
          awayRec: (t.away.records && t.away.records[0] && t.away.records[0].summary) || "", homeRec: (t.home.records && t.home.records[0] && t.home.records[0].summary) || "",
          col: (function(){ var o = {}; [t.away, t.home].forEach(function(x){ var tm = x.team; o[tm.abbreviation] = [tm.name || tm.shortDisplayName || tm.abbreviation, "#" + (tm.color || "444444"), "#" + (tm.alternateColor || "999999")]; }); return o; })()});
      });
      if(!el.querySelector(".sg-st.live") && timer){ clearInterval(timer); timer = null; }
    }).catch(function(){});
  }
  if(el.querySelector(".sg-st.live")){ poll(); timer = setInterval(poll, 30000); document.addEventListener("visibilitychange", function(){ if(!document.hidden && timer) poll(); }); }
})();
</script>
"""
must(body.count("</style>") >= 1, "</style>")

# 6. Header live cams (Oct 26, 2026): the header rotates through Snowbasin's live cam pictures (Needles + Mt. Ogden, John Paul Lodge,
#    Base of Wildcat) every 20 seconds; a "Watch Live" link in the dateline (where Next Photo was) opens Snowbasin's webcam page, where the
#    real-time Needles video plays in their own player (that stream needs a per-viewer token, so it can't be embedded here).
#    If the snapshot can't load, the rotating cam photos stay as they are.
NEEDLES_SNAP = "https://b15.hdrelay.com/camera/1b6ed87c-f919-4e59-b9cc-7480e3ca31c3/snapshot"
NEEDLES_LIVE = "https://www.snowbasin.com/the-mountain/web-cams/"
video_css = """<style>
/* Public site: live Needles cam picture behind the header (falls back to the rotating cam photos) */
#wt-banner img.wt-live{position:absolute; inset:0; width:100%; height:100%; object-fit:cover; object-position:center 45%; opacity:0; transition:opacity 1.2s ease; z-index:0; pointer-events:none;}
#wt-banner img.wt-live.on{opacity:1;}
html.has-video #wt-banner .bl{opacity:0!important;}
html.has-video .wt-banner-cap{display:none;}
html.has-video .wt-vid-cap{display:block;}
.wt-vid-cap{display:none; z-index:2; position:absolute; right:10px; bottom:6px; font:500 10px var(--font-body); letter-spacing:.06em; color:rgba(255,255,255,.85); text-shadow:0 1px 2px rgba(0,0,0,.8);}
html.has-video #wt-next, html.has-video .wt-next-sep{display:none;}
html:not(.has-video) .wt-play, html:not(.has-video) .wt-play-sep{display:none;}
a.wt-play{text-decoration:none;}
a.wt-play:hover, a.wt-play:focus-visible{text-decoration:underline;}
</style>
"""
video_js = r"""<script>
/* Public site: the header rotates through Snowbasin's LIVE cam pictures every 20 seconds (Mark, Oct 26, 2026) — the Needles cam
   (HD Relay snapshot) plus the Mt. Ogden, John Paul Lodge and Base of Wildcat cams, each freshly loaded when its turn comes, with a
   crossfade. The dateline's "Watch Live" link (where Next Photo was) opens Snowbasin's webcam page, where the real-time video plays in
   Snowbasin's own player. If no live picture loads, the rotating cam photos stay. */
(function(){
  var SNAP = "@@SNAP@@", LIVE = "@@LIVE@@", ROTATE = 20000;
  var NAMES = {ogden: "Mt. Ogden", jp: "John Paul Lodge", wildcat: "Base of Wildcat"};
  var b = document.getElementById("wt-banner"), root = document.documentElement;
  if(!b) return;
  var nb = document.getElementById("wt-next");
  if(nb && nb.previousElementSibling && nb.previousElementSibling.classList.contains("wt-sep2")) nb.previousElementSibling.classList.add("wt-next-sep");
  var cap = document.createElement("span"); cap.className = "wt-vid-cap"; cap.textContent = "Snowbasin · Needles live cam"; b.appendChild(cap);
  var sep = document.createElement("span"); sep.className = "wt-sep2 wt-play-sep"; sep.setAttribute("aria-hidden", "true"); sep.textContent = "|";
  var link = document.createElement("a"); link.className = "wt-next wt-play"; link.textContent = "Watch Live";
  link.href = LIVE; link.target = "_blank"; link.rel = "noopener"; link.title = "Watch Snowbasin's cams live on Snowbasin's webcam page";
  if(nb && nb.parentNode){ nb.parentNode.insertBefore(link, nb.nextSibling); nb.parentNode.insertBefore(sep, link); }
  var L = [document.createElement("img"), document.createElement("img")], front = 0, busy = false, idx = -1, fails = 0;
  L.forEach(function(i){ i.className = "wt-live"; i.alt = ""; i.setAttribute("aria-hidden", "true"); i.decoding = "async"; b.insertBefore(i, b.firstChild); });
  function when(){ try{ return new Date().toLocaleTimeString("en-US",{timeZone:"America/Denver",hour:"numeric",minute:"2-digit"}).replace("AM","a.m.").replace("PM","p.m.") + " MT"; }catch(e){ return ""; } }
  function list(){
    var l = [{src: SNAP, name: "Needles"}];
    ["ogden", "jp", "wildcat"].forEach(function(k){ var a = document.querySelector("#cam-" + k + " .frame"); if(a && a.href && /^https?:/.test(a.href)) l.push({src: a.href, name: NAMES[k]}); });
    return l;
  }
  function load(){
    if(busy) return;
    var l = list(); idx = (idx + 1) % l.length; var f = l[idx];
    busy = true;
    var next = 1 - front, img = L[next], probe = new Image();
    probe.onload = function(){
      busy = false;
      if(probe.naturalWidth < 40){ if(++fails < l.length) load(); return; }
      fails = 0;
      img.src = probe.src;
      img.classList.add("on"); L[front].classList.remove("on"); front = next;
      root.classList.add("has-banner", "has-video");
      cap.textContent = "Snowbasin · " + f.name + " live cam · " + when();
    };
    probe.onerror = function(){ busy = false; if(++fails < l.length) load(); };
    probe.src = f.src + (f.src.indexOf("?") < 0 ? "?" : "&") + "t=" + Date.now();
  }
  load();
  setInterval(function(){ if(!document.hidden) load(); }, ROTATE);
})();
</script>
""".replace("@@SNAP@@", NEEDLES_SNAP).replace("@@LIVE@@", NEEDLES_LIVE)

head = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Waltski News</title>
<meta name="description" content="Waltski News — markets, economy, top stories, Wasatch snow and weather, refreshed twice a day.">
<meta property="og:title" content="Waltski News">
<meta property="og:description" content="Markets, economy, top stories, Wasatch snow and weather — refreshed twice a day.">
<meta name="theme-color" content="#000000">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 40'%3E%3Cpath d='M2 38 L22 10 L32 22 L42 6 L62 38 Z' fill='%23E2733A'/%3E%3C/svg%3E">
"""

# Keep the page's own <style>/<link> tags where they are (browsers accept them in the body); close head first.
# Greeting by the reader's clock (Mark, Oct 26, 2026): from 10:00 a.m. MT the morning edition's "Rise and shine" becomes
# "Happy mid-morning", and from 5:00 p.m. MT any earlier greeting becomes "Good evening", whether or not a refresh has run.
# Checked on load and every minute.
greet_js = """<script>
(function(){
  function fix(){
    var g = document.getElementById("wt-greet"); if(!g) return;
    var t = g.textContent;
    var hm = new Date().toLocaleTimeString("en-US",{timeZone:"America/Denver",hour:"2-digit",minute:"2-digit",hour12:false}).split(":");
    var m = (+hm[0] % 24) * 60 + (+hm[1]);
    if(m >= 17 * 60) g.textContent = t.replace(/^(Rise and shine|Happy mid-morning|Good afternoon)/, "Good evening");
    else if(m >= 10 * 60) g.textContent = t.replace(/^Rise and shine/, "Happy mid-morning");
  }
  fix(); setInterval(fix, 60000);
})();
</script>
"""
page = head + public_css + video_css + "</head>\n<body>\n" + body.strip() + "\n" + live_js + video_js + greet_js + "</body>\n</html>\n"

open(out, "w", encoding="utf-8").write(page)
print("build_public: wrote", out, len(page), "bytes")
