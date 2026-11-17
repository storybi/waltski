#!/usr/bin/env python3
"""Build the public www.skiinut.com page from Mark's private claude.ai "News" artifact.

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
  * Sunday's sermon from Washington Heights Church plays at the top of Morning Devotion (scripts/sermon.py)
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

# 3b. My Holdings (Mark, Nov 4, 2026): keep the chart but delete the private share counts.
#     Without HOLD_SH the page shows % change (default) and Share price only, no dollar totals.
body = re.sub(r'\nvar HOLD_SH = \{[^}]*\};', "\n", body, count=1)
if re.search(r'var HOLD_SH\s*=', body) or '"AAPL":38' in body:
    sys.exit("could not remove My Holdings share counts")

# 3c. Faster fonts (Mark, Nov 4, 2026): the Skiinut 2.0 design uses only Inter, Barlow Condensed, Montserrat (nameplate) and
#     Newsreader italic (greeting). The head (above) loads exactly those, early. Drop the page's old 8-family link and the late
#     @import in the design-system <style> so the browser doesn't fetch unused fonts or wait for Inter.
body = re.sub(r'<link rel="preconnect" href="https://fonts\.(?:googleapis|gstatic)\.com"(?: crossorigin)?>\s*', "", body)
body = re.sub(r'<link href="https://fonts\.googleapis\.com/css2\?family=Archivo\+Narrow[^"]*" rel="stylesheet">\s*', "", body, count=1)
body = re.sub(r'@import url\("https://fonts\.googleapis\.com/css2\?family=Inter[^"]*"\);', "", body, count=1)

# 4. Hide the Ask Claude bar (its code shares a script with the weather renderer, so only the bar is hidden).
public_css = """<style>
/* Public site: no Ask Claude bar */
#askbar{display:none!important;}
</style>
"""

# 4b. Subscribe bar (Mark, Nov 16, 2026; replaces the Suggest-a-resort bar of Oct 29, 2026): an email box, a home-resort menu and a
#     Subscribe button. Signups go to Mark's Brevo contact list (email + RESORT attribute = the resort key, e.g. "sb"); every Monday at
#     5:30 a.m. MT scripts/monday_email.py emails each subscriber the SKIINUT outlook for their resort. It keeps the "gbar" class and id
#     (bar styling, 9 p.m.-7 a.m. black-out) and the "sug" class (the dock script moves it to the bottom of the docked group).
GBAR_HTML = """
  <form class="gbar sug sub" id="gbar" autocomplete="on" aria-label="Subscribe to the SKIINUT Monday snow outlook" novalidate>
    <button type="submit" class="gbar-ai" id="sub-send">Subscribe</button>
    <input type="email" id="sub-email" name="EMAIL" maxlength="120" required placeholder="Your email" aria-label="Your email" autocomplete="email">
    <select id="sub-resort" name="RESORT" required aria-label="Your home resort"><option value="">Home resort</option></select>
    <input type="text" id="sub-hp" tabindex="-1" autocomplete="off" aria-hidden="true" class="sug-hp">
    <span class="sug-msg" id="sub-msg" role="status" aria-live="polite"></span>
  </form>"""
GBAR_CSS = """<style>
/* Public site: free Google search bar at the top of the sticky dock */
.gbar{display:flex; align-items:center; gap:6px; margin:0; padding:5px 6px 5px 10px; background-color:var(--bg); border:1px solid var(--border); border-bottom:0;}
@media (prefers-color-scheme: light){ :root:not([data-theme="dark"]) .gbar{background-image:var(--paper);} }
:root[data-theme="light"] .gbar{background-image:var(--paper);}
.gbar-g{width:16px; height:16px; flex:none; color:var(--fg-faint);}
.gbar input{flex:1; min-width:0; border:1px solid #b9b3a6; outline:0; background:#fff; color:#111; font:15px var(--font-body); padding:6px 8px; border-radius:3px;}
.gbar input:focus{border-color:#E2733A; box-shadow:0 0 0 2px rgba(226,115,58,.25);}
.gbar input::placeholder{color:#8a8578;}
.gbar button{font:600 12.5px var(--font-body); border:1px solid var(--border); background:var(--surface); color:var(--fg); padding:6px 10px; cursor:pointer; white-space:nowrap;}
.gbar button:hover{border-color:var(--fg-muted);}
.gbar .gbar-ai{background:var(--accent); border-color:var(--accent); color:#fff;}
@media (max-width:420px){ .gbar button{padding:6px 7px; font-size:12px;} }
/* Night (Mark, Oct 29, 2026): from 9 p.m. to 7 a.m. by the reader's clock (html.clock-night, set by the header clock), the Google bar is blacked out */
html.clock-night .gbar{background:#000!important; border-color:#000;}
html.clock-night .gbar-g{color:#444;}
html.clock-night .gbar input{background:#0d0d0d; border-color:#222; color:#bbb;}
html.clock-night .gbar input::placeholder{color:#555;}
html.clock-night .gbar button, html.clock-night .gbar .gbar-ai{background:#111; border-color:#222; color:#777;}
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
    /* Every scenic Snowbasin cam (Mark, Nov 11, 2026): the other HDRelay cams from snowbasin.com's webcam page (snow stake left out). */
    [["62101a0b8db58d080b9eac83", "Middle Bowl Base"], ["6192dd615233cdcad76d7dba", "Earl's Plaza"], ["65652b36eb0e282336694064", "Strawberry Patio"], ["621944828db58d080b9eac8b", "Base Area"]].forEach(function(c){ l.push({src: "https://img.hdrelay.com/camera/" + c[0] + "/snapshot", name: c[1]}); });
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
      /* Smooth crossfade (Mark, Oct 29, 2026): the new picture fades in over the old one, then the old one is cleared. */
      var old = L[front];
      img.onload = function(){
        img.onload = null;
        img.style.transition = "none"; img.classList.remove("on"); img.style.zIndex = 2; old.style.zIndex = 1; void img.offsetWidth; img.style.transition = "";
        img.classList.add("on");
        setTimeout(function(){ if(L[front] !== old){ old.style.transition = "none"; old.classList.remove("on"); void old.offsetWidth; old.style.transition = ""; } }, 2700);
      };
      img.src = probe.src; front = next;
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
<title>Skiinut — live snow, radar & forecasts for every Ikon resort</title>
<meta name="description" content="Live snow totals, Doppler radar, 48-hour rain & snow outlooks, resort cams and conditions for Utah and every US Ikon Pass resort.">
<link rel="canonical" href="https://www.skiinut.com/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Skiinut">
<meta property="og:url" content="https://www.skiinut.com/">
<meta property="og:title" content="Skiinut — live snow, radar & forecasts">
<meta property="og:description" content="Live snow totals, radar, outlooks, cams and conditions for Utah and every US Ikon Pass resort.">
<meta property="og:image" content="https://www.skiinut.com/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Skiinut logo over snowy mountains">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://www.skiinut.com/og.png">
<meta name="theme-color" content="#f6f9fc" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0b1628" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-title" content="Skiinut">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Barlow+Condensed:wght@500;600;700;800&family=Montserrat:ital,wght@0,800;1,700;1,800&family=Newsreader:ital,wght@1,400&display=swap">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Cdefs%3E%3CclipPath id='c'%3E%3Crect width='100' height='100' rx='22'/%3E%3C/clipPath%3E%3C/defs%3E%3Cg clip-path='url(%23c)'%3E%3Crect width='100' height='100' fill='%231b2638'/%3E%3Ccircle cx='71' cy='34' r='15' fill='%23E2733A'/%3E%3Cpath d='M4 92 L42 34 L56 52 L66 42 L104 92 Z' fill='%231b2638' stroke='%231b2638' stroke-width='5' stroke-linejoin='round'/%3E%3Cpath d='M4 92 L42 34 L56 52 L66 42 L104 92 Z' fill='%23fff'/%3E%3Cpath d='M13 92 L35 62 L44 70 L52 58 L62 74 L68 64 L96 92 Z' fill='%231b2638'/%3E%3C/g%3E%3C/svg%3E">
"""

# Keep the page's own <style>/<link> tags where they are (browsers accept them in the body); close head first.
# Greeting by the reader's clock: since Oct 31, 2026 the page itself sets the greeting and date from the reader's clock every minute
# (the "Waltmark Times dateline" script), so the public page needs no extra greeting script. Kept as an empty string.
greet_js = ""
# 6b. Subscribe (Mark, Nov 16, 2026; Brevo since 11:40 a.m., replacing Mailchimp). BREVO_FORM_URL is the Brevo signup form's address:
#     Brevo > Contacts > Forms > the SKIINUT form > Share > Embed > the <form ... action="https://....sibforms.com/serve/...">. The form
#     must have the EMAIL field and a RESORT field (text contact attribute RESORT). Until it is filled in, the form says signups open soon.
#     Brevo sends its own confirmation email if double opt-in is on for the form.
BREVO_FORM_URL = "https://ab21955b.sibforms.com/serve/MUIFAOWk10_Wyime34jL6x6Tb9gyGbV-UoI-PpvkxPUyYsMTqIg8j-HM3_NjVST5VX6g0txrJz7KiDFc6GtndKvQUT9aDa2ioug08ggo576Bho0zcnfNfV17V2BsEeRpI4gwA8soESSmIRhBHknYAG7LJmnsetOT8t5OeDsXMWEfYowZvk5LIvD_3VWDONqIv13l0EfPzDGVjFe2pg=="
SUGGEST_CSS = """<style>
/* Subscribe bar (Mark, Nov 16, 2026): email + home resort + Subscribe; status line under it; honeypot hidden */
.gbar.sug{position:relative; flex-wrap:wrap;}
.gbar.sub input[type=email]{flex:1 1 100px; min-width:90px;}
.gbar.sub select{flex:0 1 auto; max-width:44%; min-width:0; border:1px solid #b9b3a6; background:#fff; color:#111; font:15px var(--font-body); padding:6px 6px; border-radius:3px;}
.gbar.sub select:focus{outline:0; border-color:#E2733A; box-shadow:0 0 0 2px rgba(226,115,58,.25);}
.gbar.sub .gbar-ai{background:#E2733A; border-color:#E2733A;}
.gbar.sub #sub-send{order:-1; background:#E2733A!important; border-color:#E2733A!important; color:#fff!important;}
.gbar.sub #sub-send:hover{background:#c85f2a!important; border-color:#c85f2a!important;}
.sug-hp{position:absolute!important; left:-9999px!important; width:1px!important; height:1px!important; opacity:0!important;}
.sug-msg{flex-basis:100%; font:600 12px/1.3 var(--font-body); color:var(--fg-muted); padding:2px 0 1px 2px;}
.sug-msg:empty{display:none;}
.sug-msg.ok{color:#2f9e4c;} .sug-msg.err{color:#c8102e;}
.gbar button:disabled{opacity:.5; cursor:default;}
html.clock-night .sug-msg{color:#777;}
html.clock-night .gbar.sub select{background:#0d0d0d; border-color:#222; color:#bbb;}
@media (max-width:480px){ .gbar.sub select{max-width:34%; font-size:14px;} .gbar.sub input[type=email]{font-size:14px;} }
</style>
"""
SUGGEST_JS = """<script>
/* SKIINUT Monday outlook subscribe (Mark, Nov 16, 2026). Sends the email and home resort to the Brevo signup form (no page reload).
   The resort menu lists every resort in the site's location menu (window.IKON), Utah first. Also: skiinut.com/?resort=<key> (the
   link in the Monday email) opens that resort. */
(function(){
  var BV = "%s", f = document.getElementById("gbar");
  var IK = window.IKON || {}, order = (IK.order || []).filter(function(k){ return k !== "hi" && IK.r && IK.r[k]; });
  function nm(k){ var r = IK.r[k]; return r.name + (r.state ? ", " + r.state : ""); }
  /* open the resort named in ?resort= */
  try{ var want = new URLSearchParams(location.search).get("resort"), pick = document.getElementById("rs-pick");
    if(want && pick && pick.querySelector('option[value="' + want.replace(/[^a-z0-9_-]/gi, "") + '"]')){
      setTimeout(function(){ pick.value = want; pick.dispatchEvent(new Event("change", {bubbles: true})); try{ localStorage.setItem("sk-loc-chosen", "1"); }catch(_){} }, 400); } }catch(e){}
  if(!f) return;
  /* Keep the bar under the site buttons, at the bottom of the docked group (Mark, Nov 16, 2026, 5:20 p.m.): the older "Resort feed"
     script moves #gbar down into #ski-feed (above Weather With Travis), where Mark couldn't find it. */
  try{ var dock = document.getElementById("wt-dock");
    if(dock && f.parentNode !== dock){ dock.appendChild(f); f.classList.add("sug-bot"); window.dispatchEvent(new Event("resize")); } }catch(e){}
  var em = document.getElementById("sub-email"), sel = document.getElementById("sub-resort"), hp = document.getElementById("sub-hp"),
      b = document.getElementById("sub-send"), msg = document.getElementById("sub-msg");
  order.forEach(function(k){ var o = document.createElement("option"); o.value = k; o.textContent = nm(k); sel.appendChild(o); });
  sel.selectedIndex = 0;   /* always starts on "Home resort" (Mark, Nov 17, 2026, 5:49 a.m.; it used to preselect the resort being viewed) */
  function say(t, c){ msg.textContent = t; msg.className = "sug-msg" + (c ? " " + c : ""); }
  f.addEventListener("submit", function(e){
    e.preventDefault();
    var mail = em.value.trim(), res = sel.value;
    if(hp.value){ say("Thanks! Check your inbox to confirm.", "ok"); f.reset(); return; }
    if(!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]{2,}$/.test(mail)){ say("Enter a valid email address.", "err"); em.focus(); return; }
    if(!res){ say("Pick your home resort.", "err"); sel.focus(); return; }
    if(!BV){ say("SKIINUT email alerts open soon \\u2014 check back shortly.", "err"); return; }
    b.disabled = true; say("Subscribing\\u2026");
    function body(){ var d = new FormData(); d.append("EMAIL", mail); d.append("RESORT", res); d.append("email_address_check", ""); d.append("locale", "en"); return d; }
    function ok(){ b.disabled = false; say("You\\u2019re in \\u2014 check your inbox to confirm your SKIINUT Monday outlook for " + nm(res) + ".", "ok"); f.reset(); }
    function bad(t){ b.disabled = false; say(t || "Sorry, that didn\\u2019t go through. Please try again in a minute.", "err"); }
    fetch(BV, {method: "POST", body: body(), headers: {"Accept": "application/json"}})
      .then(function(r){ return r.json().catch(function(){ return {success: r.ok}; }); })
      .then(function(j){ if(j && j.success !== false) ok(); else bad(j && j.message ? String(j.message).replace(/<[^>]*>/g, "") : ""); })
      .catch(function(){ /* the form host may not allow reading the answer; send it anyway */
        fetch(BV, {method: "POST", body: body(), mode: "no-cors"}).then(ok, function(){ bad(); }); });
  });
})();
</script>
""" % BREVO_FORM_URL
public_css += SUGGEST_CSS

# Never add a second copy (Mark, Nov 15, 2026): the artifact can already carry the newest public-site scripts (snow stake, CAM_SKIP,
# banner arrows). A second, older copy ran a second banner rotator without them, so some Snowbasin cams never showed.
if "/* Public site: load the Snowbasin cams" in body:
    live_js = ""
if "/* SKIINUT Monday outlook subscribe" in body:
    SUGGEST_JS = ""
page = head + public_css + video_css + "</head>\n<body>\n" + body.strip() + "\n" + live_js + video_js + greet_js + SUGGEST_JS + "</body>\n</html>\n"

# 7. Sunday's sermon (Mark, Oct 26, 2026): Washington Heights Church's latest Sunday sermon plays in an embedded YouTube player at the
#    top of Morning Devotion (scripts/sermon.py). Keeps the sermon already on the live page so a rebuild never steps back to an older one;
#    the live-data job (update_data.py) moves it forward when a new Sunday's sermon is posted.
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sermon as _sermon
_prev = None
if os.path.exists(out):
    _prev = _sermon.current(open(out, encoding="utf-8").read())
if not _prev or _prev.get("date", "") < _sermon.DEFAULT["date"]:
    _prev = _sermon.DEFAULT
page = _sermon.inject(page, _prev)

open(out, "w", encoding="utf-8").write(page)
print("build_public: wrote", out, len(page), "bytes")
