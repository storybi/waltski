#!/usr/bin/env python3
"""Apply the Ikon resort picker + Skiinut 2.0 redesign to a News artifact page.

usage: python3 apply.py <in.html> <out.html> [ski_out.js]
in.html = the artifact page (from <title> on). ski_out.js (optional) = output of the extended scripts/ski_conditions.py
(SKI_ASOF, SKI, OUTLOOK, RWX lines) to drop into the page.
"""
import json, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resorts import registry, select_html, R

src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding="utf-8").read()
HERE = os.path.dirname(os.path.abspath(__file__))


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit("expected %d match(es), found %d: %r" % (count, n, old[:120]))
    s = s.replace(old, new)


reg = registry()
order = [r[0] for r in R]

# 1. Resort registry, before every script that uses it (right after the theme script at the top).
REG_JS = ("<script>\n/* Ikon resorts (Mark, Oct 30, 2026): every US resort on the 2026/27 Ikon Pass (unlimited and up-to-7-day), keyed like the resort picker.\n"
          "   name, state, access (U unlimited / 7 days), lat/lon, time zone, OnTheSnow path, where, live-cams page, trail-map page, cam frames, aerial view.\n"
          "   Used by the radar, header photo, cams, outlook, resort weather card, trail map and the header conditions panel. Keep as is. */\n"
          "window.IKON = {order: %s, r: %s};\n</script>\n") % (json.dumps(order), json.dumps(reg, ensure_ascii=False, separators=(",", ":")))
anchor = "<meta name=\"claude:viewport-fit-sides\""
rep(anchor, REG_JS + anchor)

# 2. Resort menu: every Ikon resort, grouped by region.
m = re.search(r'<select class="radar-pick" id="radar-view" aria-label="Radar location">.*?</select>', s, re.S)
s = s[:m.start()] + '<select class="radar-pick" id="radar-view" aria-label="Resort">' + select_html() + '</select>' + s[m.end():]

# 3. Radar: a view for every resort, and resort markers.
rep('hi: {c: [21.408, -157.772], z: 11, fc: [21.4022, -157.7394], fcName: "Kailua", alt: "Kaneohe and Kailua, Oahu", ridge: "HMO"}};',
    'hi: {c: [21.408, -157.772], z: 11, fc: [21.4022, -157.7394], fcName: "Kailua", alt: "Kaneohe and Kailua, Oahu", ridge: "HMO"}};\n'
    '  /* Every Ikon resort in the picker (Mark, Oct 30, 2026); Alyeska uses the Kenai NWS radar (AHG), since the mosaic stops at the lower 48. */\n'
    '  (window.IKON && window.IKON.order || []).forEach(function(k){ var r = window.IKON.r[k]; if(!VIEWS[k]) VIEWS[k] = {c: [r.lat, r.lon], z: r.z || 10, fc: [r.lat, r.lon], fcName: r.name, alt: r.name, ridge: r.ridge};\n'
    '    if(!PLACES.some(function(p){ return p[0] === r.name; })) PLACES.push([r.name, r.lat, r.lon]); });')

# 4. Header photo: every resort's cam pictures (or an aerial view), and URLs that already carry a query string.
rep('      hd("22429e23-e586-4934-b19b-beb1e20a54a7", "Sun Valley Club"), hd("32f27fbc-fa53-4194-8aeb-596e921468ef", "Ice Rink")]}\n  };',
    '      hd("22429e23-e586-4934-b19b-beb1e20a54a7", "Sun Valley Club"), hd("32f27fbc-fa53-4194-8aeb-596e921468ef", "Ice Rink")]}\n  };\n'
    '  /* Ikon resorts (Mark, Oct 30, 2026): each resort\'s own cam pictures; resorts with no public still picture show an aerial view (Esri). */\n'
    '  (window.IKON && window.IKON.order || []).forEach(function(k){ if(CAMS[k] || k === "sb") return; var r = window.IKON.r[k];\n'
    '    var fr = r.frames.length ? r.frames : [{name: "Satellite view", cap: r.name + " \\u00b7 " + r.where + " \\u00b7 satellite view \\u00a9 Esri", img: r.aerial, watch: r.cams}];\n'
    '    CAMS[k] = {resort: r.name, title: "Watch " + r.name + "\'s cams live", frames: fr}; });')
rep("    try: r=urllib.request.urlopen(urllib.request.Request(u+'?t='+str(int(datetime.datetime.now().timestamp())),headers={'User-Agent':'Mozilla/5.0'}),timeout=20).read()\\n",
    "    try: r=urllib.request.urlopen(urllib.request.Request(u+('&' if '?' in u else '?')+'t='+str(int(datetime.datetime.now().timestamp())),headers={'User-Agent':'Mozilla/5.0'}),timeout=20).read()\\n")
rep('var u = f.img + "?t=" + Date.now(), probe = new Image();', 'var u = f.img + (f.img.indexOf("?") < 0 ? "?t=" : "&t=") + Date.now(), probe = new Image();')
rep('root.classList.toggle("cam-hi", mode === "hi");', 'root.classList.toggle("cam-hi", mode === "hi"); root.classList.toggle("cam-ik", !!c && ["dv","sv","hi"].indexOf(mode) < 0);')

# 5. Outlook + resort weather card: every resort.
rep('var TZ = {sb:"America/Denver", dv:"America/Denver", sv:"America/Boise", hi:"Pacific/Honolulu"};',
    'var TZ = {sb:"America/Denver", dv:"America/Denver", sv:"America/Boise", hi:"Pacific/Honolulu"};\n'
    '  (window.IKON && window.IKON.order || []).forEach(function(k){ var r = window.IKON.r[k]; if(!PLACES[k]) PLACES[k] = [r.lat, r.lon, r.name]; if(!TZ[k]) TZ[k] = r.tz; });')
rep('var PLACES = {sb:[41.2160,-111.8569], dv:[40.6375,-111.4783], sv:[43.6710,-114.3640], hi:[21.4022,-157.7394]};',
    'var PLACES = {sb:[41.2160,-111.8569], dv:[40.6375,-111.4783], sv:[43.6710,-114.3640], hi:[21.4022,-157.7394]};\n'
    '  (window.IKON && window.IKON.order || []).forEach(function(k){ var r = window.IKON.r[k]; if(!PLACES[k]) PLACES[k] = [r.lat, r.lon]; });')

# 6. Resort ticker: share its rows with the header panel; state names for the new regions.
rep('var STATE = {UT:"Utah", CO:"Colorado", WY:"Wyoming", ID:"Idaho", MT:"Montana", NM:"New Mexico", AB:"Alberta", BC:"British Columbia"};',
    'var STATE = {UT:"Utah", CO:"Colorado", WY:"Wyoming", ID:"Idaho", MT:"Montana", NM:"New Mexico", AB:"Alberta", BC:"British Columbia",\n'
    '    CA:"California", WA:"Washington", OR:"Oregon", AK:"Alaska", VT:"Vermont", ME:"Maine", NH:"New Hampshire", NY:"New York", PA:"Pennsylvania",\n'
    '    WV:"West Virginia", MI:"Michigan", MN:"Minnesota", WI:"Wisconsin"};')
rep('  render();\n  /* Live temperatures on skiinut.com', '  render(); window.SKI_DATA = SKI;\n  /* Live temperatures on skiinut.com')
rep('      if(n) render();\n', '      if(n){ render(); document.dispatchEvent(new Event("ski-data")); }\n')

# 7. Header: the resort panel under the greeting.
rep('</span></span></p>\n  </header>',
    '</span></span></p>\n'
    '    <!-- Resort panel (Mark, Oct 30, 2026): pick any US Ikon resort; the header photo, radar, cams, outlook, weather card and trail map follow. Rendered by the "Resort hub" script. -->\n'
    '    <div class="rs-hero" id="rs-hero">\n'
    '      <div class="rs-top"><label class="rs-label" for="rs-pick">Resort</label><div class="rs-pickwrap"><select class="rs-pick" id="rs-pick" aria-label="Choose a resort"></select></div></div>\n'
    '      <div class="rs-panel" id="rs-panel" aria-live="polite"></div>\n'
    '    </div>\n'
    '  </header>')

# 8. Cams for the other resorts, under the Sun Valley row.
m = re.search(r'(    <div class="wx-cams sv-cams" id="sv-cams">.*?\n    </div>\n)', s, re.S)
s = s[:m.end()] + ('    <!-- Ikon resort cams (Mark, Oct 30, 2026): the picked resort\'s cam pictures (every resort except Snowbasin, Deer Valley and Sun Valley,\n'
                   '         which keep their own rows). Rendered by the "Resort hub" script. -->\n'
                   '    <div class="wx-cams ik-cams" id="ik-cams">\n'
                   '      <div class="cams-head"><h4 id="ik-h">Resort Cams</h4><span class="cams-status" id="ik-status"></span><a class="cams-refresh dv-link" id="ik-link" href="#" target="_blank" rel="noopener">All cams</a></div>\n'
                   '      <div class="cams" id="ik-grid"></div>\n'
                   '    </div>\n') + s[m.end():]

# 9. Trail map for the picked resort.
rep('<div class="section-head"><h2>Snowbasin Trail Map</h2><div class="line"></div></div>\n    <div class="section-sub">Snowbasin Resort&rsquo;s 2025&ndash;26 winter trail map. Tap the map to open it full size on snowbasin.com.</div>',
    '<div class="section-head"><h2 id="rmap-title">Snowbasin Trail Map</h2><div class="line"></div></div>\n    <div class="section-sub" id="rmap-sub">Snowbasin Resort&rsquo;s 2025&ndash;26 winter trail map. Tap the map to open it full size on snowbasin.com.</div>\n'
    '    <div class="rmap-live" id="rmap-live" role="img" aria-label="Ski runs and lifts map"></div>')
rep('<div class="sbmap-src">Map &copy; Snowbasin Resort &middot; <a href="https://www.snowbasin.com/the-mountain/mountain-maps/" target="_blank" rel="noopener">snowbasin.com</a></div>\n  </section>',
    '<div class="sbmap-src">Map &copy; Snowbasin Resort &middot; <a href="https://www.snowbasin.com/the-mountain/mountain-maps/" target="_blank" rel="noopener">snowbasin.com</a></div>\n'
    '    <a class="rmap-link" id="rmap-link" href="https://www.snowbasin.com/the-mountain/mountain-maps/" target="_blank" rel="noopener">Official Snowbasin trail map ↗</a>\n  </section>')
rep('<a href="#sbmap">SB Map</a>', '<a href="#sbmap">Trail Map</a>')

# 10. Weather Elsewhere rolls up by default.
rep('<section id="weather-more">\n    <div class="section-head"><h2>Weather Elsewhere</h2><div class="line"></div></div>',
    '<section id="weather-more">\n    <div class="section-head"><h2>Weather Elsewhere</h2><div class="line"></div><button type="button" class="wm-toggle" id="wm-toggle" aria-expanded="false" aria-controls="wx">Show forecasts</button></div>\n'
    '    <div class="wm-peek" id="wm-peek"></div>')

# 11. New data from the extended ski_conditions.py.
if len(sys.argv) > 3:
    d = open(sys.argv[3], encoding="utf-8").read()
    for name in ("SKI_ASOF", "SKI", "OUTLOOK", "RWX"):
        mm = re.search(r"^var %s = .*?;$" % name, d, re.S | re.M) if name != "SKI" else re.search(r"^var SKI = \[.*?\];$", d, re.S | re.M)
        new = mm.group(0)
        pat = {"SKI_ASOF": r'var SKI_ASOF = "[^"]*";', "SKI": r"var SKI = \[.*?\n  \];", "OUTLOOK": r"var OUTLOOK = \{.*?\};\n", "RWX": r"var RWX = \{.*?\};\n"}[name]
        hits = list(re.finditer(pat, s, re.S))
        if len(hits) != 1:
            raise SystemExit("data block %s: %d matches" % (name, len(hits)))
        h = hits[0]
        tail = "\n" if h.group(0).endswith("\n") else ""
        s = s[:h.start()] + new + tail + s[h.end():]

# 12. Resort hub + Weather Elsewhere toggle + design system, at the very end.
hub = open(os.path.join(HERE, "hub.js"), encoding="utf-8").read()
WM = r'''/* Weather Elsewhere rolls up by default (Mark, Oct 30, 2026): a row of city chips shows; the button opens the full forecasts. Keep as is. */
(function(){
  var sec = document.getElementById("weather-more"), b = document.getElementById("wm-toggle"), pk = document.getElementById("wm-peek");
  if(!sec || !b) return;
  function peek(){ if(!pk) return; var out = [];
    sec.querySelectorAll(".wx-card").forEach(function(c){ var h = c.querySelector("h3"), t = c.querySelector(".wx-now .t"); if(h) out.push("<span>" + h.textContent.split(",")[0] + (t ? " · " + t.textContent : "") + "</span>"); });
    pk.innerHTML = out.join(""); }
  function set(o){ sec.classList.toggle("open", o); b.setAttribute("aria-expanded", o ? "true" : "false"); b.textContent = o ? "Hide forecasts" : "Show forecasts"; }
  b.addEventListener("click", function(e){ e.stopPropagation(); set(!sec.classList.contains("open")); });
  sec.querySelector(".section-head").addEventListener("click", function(){ set(!sec.classList.contains("open")); });
  set(false); peek(); setTimeout(peek, 1500);
})();
'''
css = open(os.path.join(HERE, "design.css"), encoding="utf-8").read()
end = "<script>\n" + hub + "</script>\n<script>\n" + WM + "</script>\n<style>\n" + css + "</style>\n"
s = s.rstrip() + "\n" + end
open(dst, "w", encoding="utf-8").write(s)
print("wrote", dst, len(s))
