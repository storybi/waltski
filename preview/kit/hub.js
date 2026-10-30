/* Resort hub (Mark, Oct 30, 2026): one resort picker for the whole Ski Weather page. Every US resort on the 2026/27 Ikon Pass
   (window.IKON, from the "Ikon resorts" script near the top), plus Kailua for the beach view. The radar menu (#radar-view) holds the
   choice; the big picker in the header (#rs-pick) mirrors it. Picking a resort changes the header photo, radar, cams, outlook,
   resort weather card, trail map and the conditions panel in the header. Remembered on this device. Keep as is. */
(function(){
  var IK = window.IKON || {r:{}, order:[]}, R = IK.r;
  var root = document.documentElement, pick = document.getElementById("radar-view"), hp = document.getElementById("rs-pick");
  var inClaude = !!(window.claude && window.claude.use);
  if(!pick) return;
  if(hp){ hp.innerHTML = pick.innerHTML; hp.value = pick.value; }
  function esc(t){ return String(t == null ? "" : t).replace(/[&<>"]/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]; }); }
  function txt(id){ var e = document.getElementById(id); return e ? e.textContent.replace(/["″]/g, "").trim() : ""; }
  var MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  var ACC = {U: "Ikon unlimited", "7": "Ikon · 7 days"};
  var STAKE = {sb: ["wt-stake-in", "wt-base-sb"], dv: ["wt-stake-dv", "wt-base-dv"], sv: ["wt-stake-sv", "wt-base-sv"]};
  function skiRow(r){ var S = window.SKI_DATA || []; for(var i = 0; i < S.length; i++) if(S[i][2] === r.ots) return S[i]; return null; }
  function stat(lbl, val, unit, cls){ return '<div class="rs-stat' + (cls ? " " + cls : "") + '"><span class="v">' + esc(val) + (unit ? '<small>' + unit + '</small>' : "") + '</span><span class="l">' + lbl + '</span></div>'; }
  function panel(k){
    var box = document.getElementById("rs-panel"); if(!box) return;
    if(k === "hi"){ box.innerHTML = '<div class="rs-where">Windward Oʻahu, Hawaii · beach view</div>'; return; }
    var r = R[k]; if(!r){ box.innerHTML = ""; return; }
    var s = skiRow(r), nw = null, base = null, temp = null, st = "";
    if(s){ base = s[5]; nw = s[6]; temp = s[11];
      if(s[7]) st = "Open" + (s[9] != null && s[10] ? " · " + s[9] + "/" + s[10] + " lifts" : "");
      else if(s[8]){ var d = s[8].split("-"); st = "Opens " + MON[+d[1]-1] + " " + (+d[2]); }
      else st = "Closed"; }
    if(STAKE[k]){ var a = txt(STAKE[k][0]), b = txt(STAKE[k][1]); if(a !== "") nw = a; if(b !== "") base = b; }
    var html = '<div class="rs-where">' + esc(r.where) + '<span class="rs-acc">' + (ACC[r.acc] || "Ikon") + '</span></div>' +
      '<div class="rs-stats">' + stat("New 24h", nw == null ? "—" : nw, nw == null ? "" : "″", +nw > 0 ? "fresh" : "") +
      stat("Base", base == null ? "—" : base, base == null ? "" : "″") +
      stat("Now", temp == null ? "—" : temp, temp == null ? "" : "°F") +
      '<div class="rs-stat rs-status' + (s && s[7] ? " open" : "") + '"><span class="v">' + esc(st || "—") + '</span><span class="l">Status</span></div></div>' +
      '<div class="rs-links"><a href="' + esc(r.cams) + '" target="_blank" rel="noopener">Live cams ↗</a><a href="#sbmap">Trail map</a>' +
      '<a href="https://www.onthesnow.com/' + esc(r.ots) + '/skireport" target="_blank" rel="noopener">Snow report ↗</a></div>';
    box.innerHTML = html;
  }
  /* Cams under the radar for every resort except Snowbasin, Deer Valley and Sun Valley (those keep their own rows). */
  var camTimer = null, mcp = null;
  function camTile(f, i, src){
    return '<figure class="cam"><a class="frame" href="' + esc(f.watch) + '" target="_blank" rel="noopener"><span class="cam-tag' + (f.yt ? " live" : "") + '">' + (f.yt ? "Live" : "Cam") + '</span>' +
      (src ? '<img alt="' + esc(f.name) + '" src="' + esc(src) + '" loading="lazy" onerror="this.style.display=\'none\'">' : "") +
      '<span class="ph">' + (src ? "" : "Tap to open this cam live") + '</span></a><figcaption><span>' + esc(f.name) + '</span></figcaption></figure>';
  }
  function cams(k){
    var wrap = document.getElementById("ik-cams"), grid = document.getElementById("ik-grid"), h = document.getElementById("ik-h"), lk = document.getElementById("ik-link"), stt = document.getElementById("ik-status");
    if(!wrap || !grid) return;
    if(camTimer){ clearInterval(camTimer); camTimer = null; }
    var r = R[k]; if(!r || k === "sb" || k === "dv" || k === "sv"){ grid.innerHTML = ""; return; }
    h.textContent = r.name + " Cams";
    lk.href = r.cams; lk.textContent = r.camsOfficial ? "All cams ↗" : "Cams on OnTheSnow ↗";
    if(!r.frames.length){
      grid.innerHTML = '<a class="ik-empty" href="' + esc(r.cams) + '" target="_blank" rel="noopener"><b>' + esc(r.name) + ' live cams</b><span>' +
        (r.camsOfficial ? "This resort shows its cams in its own player. Open them on " + esc(r.cams.replace(/^https?:\/\/(www\.)?/, "").split("/")[0]) + " ↗" : "Open the cams for " + esc(r.name) + " on OnTheSnow ↗") + '</span></a>';
      stt.textContent = ""; return;
    }
    stt.textContent = inClaude ? "Current pictures, refreshed every 10 minutes" : "Current pictures, refreshed every 5 minutes. Tap one to watch live.";
    function draw(){
      if(inClaude){
        var saved = null; try{ saved = JSON.parse(localStorage.getItem("wsj-" + k + "-set") || "null"); }catch(e){}
        var by = {}; (saved && saved.set || []).forEach(function(x){ by[x.i] = "data:image/jpeg;base64," + x.img; });
        grid.innerHTML = r.frames.map(function(f, i){ return camTile(f, i, by[i] || ""); }).join("");
      } else {
        var t = Date.now();
        grid.innerHTML = r.frames.map(function(f, i){ return camTile(f, i, f.img + (f.img.indexOf("?") < 0 ? "?t=" : "&t=") + t); }).join("");
      }
    }
    draw(); camTimer = setInterval(function(){ if(!document.hidden) draw(); }, inClaude ? 60000 : 5*60000);
  }
  /* Trail map: Snowbasin keeps its own map picture; every other resort gets an open piste map (OpenSnowMap over the terrain) on skiinut.com
     and a link to the resort's official trail map. */
  var lmap = null;
  function mapView(k){
    var sec = document.getElementById("sbmap"); if(!sec) return;
    var r = R[k] || R.sb, ttl = document.getElementById("rmap-title"), sub = document.getElementById("rmap-sub"), lk = document.getElementById("rmap-link"), live = document.getElementById("rmap-live");
    root.classList.toggle("map-sb", k === "sb" || !R[k]);
    if(ttl) ttl.textContent = r.name + " Trail Map";
    if(lk){ lk.href = r.map; lk.textContent = (r.mapOfficial ? "Official " + r.name + " trail map" : r.name + " trail map on OnTheSnow") + " ↗"; }
    if(k === "sb" || !R[k]){ if(sub) sub.innerHTML = "Snowbasin Resort’s 2025–26 winter trail map. Tap the map to open it full size on snowbasin.com."; return; }
    if(sub) sub.textContent = inClaude ? "Ski runs and lifts for " + r.name + " show on skiinut.com. Open the official map below." : "Runs and lifts from OpenSnowMap over the terrain. Drag and zoom; the official map is linked below.";
    if(inClaude || !live) return;
    function make(){
      if(!window.L) return;
      if(!lmap){
        lmap = L.map(live, {zoomControl: true, attributionControl: true, scrollWheelZoom: false});
        L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {maxZoom: 17, attribution: "Imagery © Esri"}).addTo(lmap);
        L.tileLayer("https://tiles.opensnowmap.org/pistes/{z}/{x}/{y}.png", {maxZoom: 18, attribution: "Pistes © OpenSnowMap.org (CC BY-SA), data © OpenStreetMap contributors"}).addTo(lmap);
      }
      lmap.setView([r.lat, r.lon], 14); setTimeout(function(){ lmap.invalidateSize(); }, 200);
    }
    if(window.L) make();
    else { var ld = document.querySelector('script[src*="leaflet"]');
      if(!ld){ var c = document.createElement("link"); c.rel = "stylesheet"; c.href = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"; document.head.appendChild(c);
        ld = document.createElement("script"); ld.src = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"; document.head.appendChild(ld); }
      ld.addEventListener("load", make); var tries = 0, iv = setInterval(function(){ if(window.L || ++tries > 40){ clearInterval(iv); make(); } }, 250); }
  }
  function apply(k){
    if(hp && hp.value !== k) hp.value = k;
    root.classList.toggle("rs-hi", k === "hi");
    var name = k === "hi" ? "Kailua, Oahu" : (R[k] ? R[k].name : "");
    var nm = document.getElementById("rs-name"); if(nm) nm.textContent = name;
    panel(k); cams(k); mapView(k);
    var ticker = document.querySelectorAll("#ski-track a.tk-it"); var ots = R[k] ? R[k].ots : "";
    ticker.forEach(function(a){ a.classList.toggle("tk-sel", !!ots && a.getAttribute("href").indexOf("/" + ots + "/") > 0); });
  }
  if(hp) hp.addEventListener("change", function(){ var k = hp.value; if(pick.value === k) return; pick.value = k; pick.dispatchEvent(new Event("change")); apply(k); });
  pick.addEventListener("change", function(){ apply(pick.value); });
  document.addEventListener("wsj-cam", function(e){ setTimeout(function(){ apply(pick.value); }, 0); });
  if(inClaude) window.claude.use("mcp").then(function(m){ mcp = m; }, function(){});
  apply(pick.value);
  setInterval(function(){ if(!document.hidden) panel(pick.value); }, 60000);
})();
