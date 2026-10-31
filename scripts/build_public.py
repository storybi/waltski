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

# 4. Hide the Ask Claude bar (its code shares a script with the weather renderer, so only the bar is hidden).
public_css = """<style>
/* Public site: no Ask Claude bar */
#askbar{display:none!important;}
</style>
"""

# 4b. Suggest-a-resort bar at the top of the sticky dock (Mark, Oct 29, 2026) — replaces the free Google search bar (Oct 26, 2026).
#     Visitors type a resort they'd like added and press Send; it reaches Mark's phone as a push notification (see 6b below).
#     It keeps the "gbar" class and id, so the existing bar styling and the 9 p.m.–7 a.m. black-out still apply.
GBAR_HTML = """
  <form class="gbar sug" id="gbar" autocomplete="off" aria-label="Suggest a resort">
    <svg class="gbar-g" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 20l6.5-11 4 6.5 2.5-4L21 20z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>
    <input type="text" id="sug-resort" maxlength="80" required placeholder="Suggest a resort here!" aria-label="Suggest a resort">
    <input type="text" id="sug-web" tabindex="-1" autocomplete="off" aria-hidden="true" class="sug-hp">
    <button type="submit" class="gbar-ai" id="sug-send">Send</button>
    <span class="sug-msg" id="sug-msg" role="status" aria-live="polite"></span>
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
<title>Skiinut</title>
<meta name="description" content="Skiinut — markets, economy, top stories, Wasatch snow and weather, refreshed twice a day.">
<meta property="og:title" content="Skiinut">
<meta property="og:description" content="Markets, economy, top stories, Wasatch snow and weather — refreshed twice a day.">
<meta name="theme-color" content="#000000">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%23E2733A'/%3E%3Ctext x='20' y='28' font-family='Montserrat,Arial,sans-serif' font-weight='800' font-size='20' fill='%23fff' text-anchor='middle'%3EIN%3C/text%3E%3C/svg%3E">
"""

# Keep the page's own <style>/<link> tags where they are (browsers accept them in the body); close head first.
# Greeting by the reader's clock: since Oct 31, 2026 the page itself sets the greeting and date from the reader's clock every minute
# (the "Waltmark Times dateline" script), so the public page needs no extra greeting script. Kept as an empty string.
greet_js = ""
# 6b. Suggest a resort (Mark, Oct 29, 2026): the bar at the top of the dock (4b) where visitors type a resort they'd like
#     added. Each suggestion is pushed instantly to Mark's phone through ntfy (free push notifications, no account): he subscribes to
#     the topic below in the ntfy app. Public site only. Keep the topic name unchanged, or his phone stops getting suggestions.
SUGGEST_TOPIC = "skiinut-resorts-6eb2b87be4"
SUGGEST_CSS = """<style>
/* Suggest-a-resort bar (Mark, Oct 29, 2026): status message shows under the field; honeypot hidden */
.gbar.sug{position:relative; flex-wrap:wrap;}
.sug-hp{position:absolute!important; left:-9999px!important; width:1px!important; height:1px!important; opacity:0!important;}
.sug-msg{flex-basis:100%; font:600 12px/1.3 var(--font-body); color:var(--fg-muted); padding:2px 0 1px 22px;}
.sug-msg:empty{display:none;}
.sug-msg.ok{color:#2f9e4c;} .sug-msg.err{color:#c8102e;}
.gbar button:disabled{opacity:.5; cursor:default;}
html.clock-night .sug-msg{color:#777;}
</style>
"""
SUGGEST_JS = """<script>
/* Suggest a resort — sends the suggestion to Mark's phone as an ntfy push notification. Light spam guards: hidden honeypot field,
   length limits, and at most 3 suggestions per browser per hour. */
(function(){
  var TOPIC = "%s", f = document.getElementById("gbar"); if(!f) return;
  var r = document.getElementById("sug-resort"), hp = document.getElementById("sug-web"),
      b = document.getElementById("sug-send"), msg = document.getElementById("sug-msg"), KEY = "skiinut-sug-times";
  function say(t, c){ msg.textContent = t; msg.className = "sug-msg" + (c ? " " + c : ""); }
  function recent(){ try{ var a = JSON.parse(localStorage.getItem(KEY) || "[]"); return a.filter(function(x){ return Date.now() - x < 3600000; }); }catch(e){ return []; } }
  f.addEventListener("submit", function(e){
    e.preventDefault();
    var name = r.value.replace(/\\s+/g, " ").trim();
    if(hp.value){ say("Thanks! Your suggestion was sent.", "ok"); f.reset(); return; }
    if(name.length < 2){ say("Please type a resort name.", "err"); r.focus(); return; }
    var t = recent(); if(t.length >= 3){ say("Thanks — you\\u2019ve sent a few already. Please try again later.", "err"); return; }
    b.disabled = true; say("Sending\\u2026");
    fetch("https://ntfy.sh/" + TOPIC, {method: "POST", body: "Resort: " + name,
      headers: {"Title": "Skiinut: resort suggestion", "Tags": "ski", "Priority": "default"}})
      .then(function(res){ if(!res.ok) throw new Error(res.status);
        t.push(Date.now()); try{ localStorage.setItem(KEY, JSON.stringify(t)); }catch(_){}
        say("Thanks! \\u201c" + name + "\\u201d was sent to Skiinut.", "ok"); f.reset(); setTimeout(function(){ if(msg.className.indexOf("ok") > 0) say(""); }, 8000); })
      .catch(function(){ say("Sorry, that didn\\u2019t go through. Please try again in a minute.", "err"); })
      .then(function(){ b.disabled = false; });
  });
})();
</script>
""" % SUGGEST_TOPIC
public_css += SUGGEST_CSS

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
