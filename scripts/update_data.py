#!/usr/bin/env python3
"""Refresh the mechanical data on www.waltski.com without Claude.

Usage:  python3 scripts/update_data.py index.html

Run by the GitHub Actions workflow .github/workflows/update-data.yml every 15 minutes during
market hours and hourly otherwise. It rewrites only these data blocks inside index.html, all from
free public sources:

  * Stock ticker  (TICK_ASOF, TICK, SPARK_ASOF, SPARK)      Yahoo Finance public chart API
  * Markets cards (MKT_ASOF, MKT)                            Yahoo Finance (^GSPC ^DJI ^IXIC ^RUT)
  * SpaceX chart  (SX_ASOF, SX_SERIES)                       Yahoo Finance (SPCX)
  * Weather       (WX, which also drives the mini weather bar) National Weather Service API
  * Seahawks game strip (SEA_GAME)                           ESPN public scoreboard
  * Oregon Ducks game strip (ORE_GAME)                        ESPN public college scoreboard
  * Weather With Travis latest video (TRAVIS)                 YouTube channel RSS feed
  * Sunday's sermon, Washington Heights Church (SERMON)      YouTube channel RSS feed (scripts/sermon.py)
  * Snowbasin cam snapshots (SNAP, SNAP_AT)                  the cam hosts themselves

Everything written by Claude (stories, briefs, devotions, snow outlook, badges, deals) is left alone.
Each block is independent: if a source fails or a block isn't found, that block keeps its old value
and the rest still update. The script never fails the workflow because of one bad source.
"""
import base64
import datetime as dt
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

MT = ZoneInfo("America/Denver")
ET = ZoneInfo("America/New_York")
UA = {"User-Agent": "Mozilla/5.0 (waltski.com data refresh; github.com/storybi/waltski)", "Accept": "application/json,*/*"}
LOG = []


def log(*a):
    msg = " ".join(str(x) for x in a)
    LOG.append(msg)
    print(msg, flush=True)


def get(url, binary=False, tries=3, headers=None):
    h = dict(UA)
    if headers:
        h.update(headers)
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=25) as r:
                b = r.read()
                return b if binary else json.loads(b.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


def tstr(d):
    """'10:15 a.m.' style time."""
    return d.strftime("%-I:%M %p").replace("AM", "a.m.").replace("PM", "p.m.")


def scale(vals):
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return [50 for _ in vals]
    return [round((v - lo) / (hi - lo) * 99) for v in vals]


def r1(x):
    return round(x + 0.0, 1)


# ----------------------------------------------------------------------------------------------- Yahoo
def ychart(sym, rng="3mo", interval="1d"):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=%s&includePrePost=false" % (
        urllib.parse.quote(sym), rng, interval)
    try:
        j = get(url)
    except Exception:  # noqa: BLE001
        j = get(url.replace("query1.", "query2."))
    res = j["chart"]["result"][0]
    meta = res.get("meta", {})
    ts = res.get("timestamp") or []
    closes = (res.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    tz = ZoneInfo(meta.get("exchangeTimezoneName") or "America/New_York")
    bars = [(dt.datetime.fromtimestamp(t, tz), c) for t, c in zip(ts, closes) if c is not None]
    return meta, bars


def quote(meta, bars):
    """(price, previous close, market-time) from a daily chart."""
    price = meta.get("regularMarketPrice")
    rmt = meta.get("regularMarketTime")
    tz = ZoneInfo(meta.get("exchangeTimezoneName") or "America/New_York")
    when = dt.datetime.fromtimestamp(rmt, tz) if rmt else (bars[-1][0] if bars else None)
    if price is None and bars:
        price = bars[-1][1]
    prev = None
    if bars:
        if when and bars[-1][0].date() == when.date() and len(bars) > 1:
            prev = bars[-2][1]
        else:
            prev = bars[-1][1]
    return price, prev, when


# ---------------------------------------------------------------------------------- block replacement
def replace_block(s, start_pat, new_text, end_pat=None):
    """Replace from the match of start_pat through the end of the statement it begins."""
    m = re.search(start_pat, s)
    if not m:
        return s, False
    i = m.start()
    if end_pat:
        e = re.compile(end_pat).search(s, m.end())
        if not e:
            return s, False
        j = e.end()
    else:
        j = s.index(";", m.end()) + 1
    return s[:i] + new_text + s[j:], True


def bracket_end(s, i):
    """Index just past the bracketed value ([...] or {...}) that starts at s[i], ignoring brackets inside strings."""
    open_c = s[i]
    close_c = {"[": "]", "{": "}"}[open_c]
    depth, k, q = 0, i, None
    while k < len(s):
        c = s[k]
        if q:
            if c == "\\":
                k += 2
                continue
            if c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
            if depth == 0:
                return k + 1
        k += 1
    raise ValueError("unbalanced")


def set_var(s, name, value_text):
    """var NAME = <value>;  ->  var NAME = value_text;"""
    m = re.search(r"var %s = " % re.escape(name), s)
    if not m:
        log("  !", name, "not found")
        return s, False
    i = m.end()
    if s[i] in "[{":
        j = bracket_end(s, i)
    elif s[i] == '"':
        j = s.index('"', i + 1) + 1
    else:
        j = s.index(";", i)
    return s[:i] + value_text + s[j:], True


def get_var(s, name):
    m = re.search(r"var %s = " % re.escape(name), s)
    if not m:
        return None
    i = m.end()
    j = bracket_end(s, i) if s[i] in "[{" else s.index(";", i)
    return s[i:j]


# ------------------------------------------------------------------------------------------- ticker
TICK_ORDER = ["S&amp;P 500", "DOW", "NASDAQ", "TSLA", "TM", "MSFT", "SPCX", "SPY", "DIA", "QQQ", "IWM", "AAPL", "NVDA",
              "AMZN", "GOOGL", "META", "JPM", "PPG", "SHW", "AXTA", "BA", "GLD", "USO", "BTC", "ETH"]
YSYM = {"S&amp;P 500": "^GSPC", "DOW": "^DJI", "NASDAQ": "^IXIC", "BTC": "BTC-USD", "ETH": "ETH-USD"}


def market_label(now_mt, when):
    """'Mon 10:15 a.m. MT' while the US market is open, else 'Close Fri'."""
    if when is None:
        return None
    w_et = when.astimezone(ET)
    n_et = now_mt.astimezone(ET)
    open_now = (n_et.weekday() < 5 and dt.time(9, 30) <= n_et.time() <= dt.time(16, 5)
                and (n_et - w_et) < dt.timedelta(minutes=40))
    if open_now:
        w = when.astimezone(MT)
        return "%s %s MT" % (w.strftime("%a"), tstr(w))
    return "Close %s" % w_et.strftime("%a")


def do_ticker(s, now_mt):
    old = get_var(s, "TICK") or ""
    old_rows = {m.group(1): m.group(0) for m in re.finditer(r'\["([^"]+)",[-\d.]+,[-\d.]+\]', old)}
    rows, spark, label_when, got = [], {}, None, 0
    for lab in TICK_ORDER:
        sym = YSYM.get(lab, lab)
        try:
            meta, bars = ychart(sym, "3mo", "1d")
            price, prev, when = quote(meta, bars)
            if price is None or prev is None:
                raise ValueError("no price")
            rows.append('["%s",%.2f,%.2f]' % (lab, price, prev))
            closes = [c for _, c in bars]
            if len(closes) >= 10:
                spark[lab.replace("&amp;", "&")] = [r1((closes[-1] / closes[0] - 1) * 100), scale(closes)]
            if lab == "S&amp;P 500":
                label_when = when
            got += 1
        except Exception as e:  # noqa: BLE001
            log("  ticker", sym, "failed:", e)
            if lab in old_rows:
                rows.append(old_rows[lab])
    if got < 5:
        log("  ticker: too few quotes, left as is")
        return s
    lines, line = [], []
    for r in rows:
        line.append(r)
        if len(line) == 4:
            lines.append(",".join(line))
            line = []
    if line:
        lines.append(",".join(line))
    s, _ = set_var(s, "TICK", "[\n    " + ",\n    ".join(lines) + "\n  ]")
    lab = market_label(now_mt, label_when)
    if lab:
        s, _ = set_var(s, "TICK_ASOF", json.dumps(lab, ensure_ascii=False))
    if len(spark) >= 5:
        old_sp = get_var(s, "SPARK") or "{}"
        merged = []
        for lab2 in TICK_ORDER:
            k = lab2.replace("&amp;", "&")
            if k in spark:
                merged.append('    "%s":%s' % (k, json.dumps(spark[k], separators=(",", ":"))))
            else:
                m = re.search(r'"%s":\[[^\]]*\[[^\]]*\]\]' % re.escape(k), old_sp)
                if m:
                    merged.append("    " + m.group(0))
        s, _ = set_var(s, "SPARK", "{\n" + ",\n".join(merged) + "\n  }")
        s, _ = set_var(s, "SPARK_ASOF", json.dumps("90 days to %s" % now_mt.strftime("%b %-d, %Y")))
    log("  ticker: %d quotes, %d sparklines" % (got, len(spark)))
    return s


# ------------------------------------------------------------------------------------------- markets
MKT_DEF = [("S&P 500", "^GSPC"), ("Dow Jones Industrial", "^DJI"), ("Nasdaq Composite", "^IXIC"), ("Russell 2000", "^RUT")]


def months_back(d, n):
    y, m = d.year, d.month - n
    while m <= 0:
        m += 12
        y -= 1
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return dt.date(y, m, day)


def close_on_or_before(bars, day):
    c = None
    for d, v in bars:
        if d.date() <= day:
            c = v
        else:
            break
    return c


def do_markets(s, now_mt):
    old = get_var(s, "MKT") or ""
    out, label_when, got = [], None, 0
    for name, sym in MKT_DEF:
        try:
            meta, bars = ychart(sym, "2y", "1d")
            price, prev, when = quote(meta, bars)
            ref = when.date() if when else bars[-1][0].date()
            chg = []
            for n in (1, 3, 6, 12):
                c0 = close_on_or_before(bars, months_back(ref, n))
                chg.append(r1((price / c0 - 1) * 100) if c0 else 0.0)
            yr = [(d, v) for d, v in bars if d.date() > months_back(ref, 12)]
            weekly, seen = [], {}
            for d, v in yr:
                seen[d.isocalendar()[:2]] = v
            weekly = list(seen.values())
            if weekly and abs(weekly[-1] - price) > 1e-9:
                weekly.append(price)
            out.append('    {name:"%s", level:"%s", day:%s, chg:[%s], bg:[%s]}' % (
                name, "{:,.2f}".format(price), r1((price / prev - 1) * 100) if prev else 0.0,
                ", ".join(str(x) for x in chg), ",".join(str(x) for x in scale(weekly))))
            if sym == "^GSPC":
                label_when = when
            got += 1
        except Exception as e:  # noqa: BLE001
            log("  markets", sym, "failed:", e)
            m = re.search(r'\{name:"%s".*?\]\}' % re.escape(name), old)
            if m:
                out.append("    " + m.group(0))
    if not got:
        log("  markets: no data, left as is")
        return s
    s, _ = set_var(s, "MKT", "[\n" + ",\n".join(out) + "\n  ]")
    if label_when:
        lab = market_label(now_mt, label_when)
        if lab and lab.startswith("Close"):
            lab = "Close " + label_when.astimezone(ET).strftime("%a, %b %-d, %Y")
        s, _ = set_var(s, "MKT_ASOF", json.dumps(lab))
    log("  markets: %d indexes" % got)
    return s


# ------------------------------------------------------------------------------------------- SpaceX
def do_spacex(s, now_mt):
    try:
        meta, bars = ychart("SPCX", "1y", "1d")
        price, prev, when = quote(meta, bars)
        series = [[d.strftime("%Y-%m-%d"), round(v, 2)] for d, v in bars if d.strftime("%Y-%m-%d") >= "2026-06-12"]
        if len(series) < 5:
            raise ValueError("short series")
        if when and series[-1][0] != when.strftime("%Y-%m-%d"):
            series.append([when.strftime("%Y-%m-%d"), round(price, 2)])
        else:
            series[-1][1] = round(price, 2)
        s, _ = set_var(s, "SX_SERIES", json.dumps(series, separators=(",", ":")))
        lab = market_label(now_mt, when)
        if lab and lab.startswith("Close"):
            lab = "Close " + when.astimezone(ET).strftime("%a, %b %-d, %Y")
        s, _ = set_var(s, "SX_ASOF", json.dumps(lab))
        log("  spacex: %d closes" % len(series))
    except Exception as e:  # noqa: BLE001
        log("  spacex failed:", e)
    return s


# ------------------------------------------------------------------------------------------- weather
WX_DEF = [
    dict(city="Morgan, Utah", home=True, abbr="Mor", where="Morgan County · Wasatch Back", lat=41.0361, lon=-111.6769),
    dict(city="Eugene, Oregon", abbr="Eug", where="Willamette Valley", lat=44.0521, lon=-123.0868),
    dict(city="Redmond, Washington", abbr="Red", where="King County · Eastside", lat=47.674, lon=-122.121),
    dict(city="Honolulu, Hawaii", abbr="Hon", where="Oʻahu · Honolulu metro", lat=21.3069, lon=-157.8583),
    dict(city="Lakeland, Florida", abbr="Lak", where="Polk County · Central Florida", lat=28.0395, lon=-81.9498),
]
NWS = {"User-Agent": "waltski.com weather (github.com/storybi/waltski)", "Accept": "application/geo+json"}


def icon_for(text):
    t = (text or "").lower()
    if "snow" in t or "flurr" in t or "sleet" in t or "wintry" in t or "blizzard" in t:
        return "snow"
    if "thunder" in t or "t-storm" in t:
        return "storm"
    if "rain" in t or "shower" in t or "drizzle" in t:
        return "rain"
    if "fog" in t or "haze" in t or "smoke" in t:
        return "fog"
    if "mostly cloudy" in t or t.strip() in ("cloudy", "overcast") or t.startswith("cloudy"):
        return "cloud"
    if "partly" in t or "mostly sunny" in t or "mostly clear" in t or "cloud" in t:
        return "partly"
    return "sun"


def pop(p):
    v = (p.get("probabilityOfPrecipitation") or {}).get("value")
    return v or 0


def do_weather(s, now_mt):
    old = get_var(s, "WX") or ""
    cards, got = [], 0
    for c in WX_DEF:
        try:
            pt = get("https://api.weather.gov/points/%.4f,%.4f" % (c["lat"], c["lon"]), headers=NWS)["properties"]
            tz = ZoneInfo(pt.get("timeZone") or "America/Denver")
            per = get(pt["forecast"], headers=NWS)["properties"]["periods"]
            hourly = get(pt["forecastHourly"], headers=NWS)["properties"]["periods"]
            # group daily periods by local date
            byday, order = {}, []
            for p in per:
                d = dt.datetime.fromisoformat(p["startTime"]).astimezone(tz)
                key = d.date()
                if key not in byday:
                    byday[key] = {}
                    order.append(key)
                byday[key]["day" if p["isDaytime"] else "night"] = p
            days = []
            for key in order[:7]:
                e = byday[key]
                dp, np_ = e.get("day"), e.get("night")
                ic = icon_for((dp or np_)["shortForecast"])
                hi = dp["temperature"] if dp else None
                lo = np_["temperature"] if np_ else None
                pp = max(pop(dp) if dp else 0, pop(np_) if np_ else 0)
                days.append([key.strftime("%a"), ic, hi, lo, ("%d%%" % pp) if pp >= 20 else ""])
            now_h = hourly[0]
            today = dt.datetime.now(tz).date()
            mid = None
            for h in hourly:
                hd = dt.datetime.fromisoformat(h["startTime"]).astimezone(tz)
                if hd.date() == today and hd.hour == 12:
                    mid = h["temperature"]
                    break
            if mid is None:
                mid = days[0][2] if days and days[0][2] is not None else now_h["temperature"]
            parts = []
            for p in per[:3]:
                sf = p["shortForecast"]
                parts.append("%s: %s, %s %d°%s." % (p["name"], sf.lower(),
                                                     "high" if p["isDaytime"] else "low", p["temperature"],
                                                     (", %d%% chance of precipitation" % pop(p)) if pop(p) >= 30 else ""))
            card = {"city": c["city"]}
            if c.get("home"):
                card["home"] = True
            # Current conditions (Oct 26, 2026): the latest station observation, not the hourly forecast; the mini weather bar shows these.
            now_t, now_c = now_h["temperature"], now_h["shortForecast"]
            try:
                stn = get(pt["observationStations"], headers=NWS)["features"][0]["id"]
                ob = get(stn + "/observations/latest", headers=NWS)["properties"]
                if ob.get("temperature", {}).get("value") is not None:
                    now_t = round(ob["temperature"]["value"] * 9 / 5 + 32)
                    now_c = ob.get("textDescription") or now_c
            except Exception as e:  # noqa: BLE001
                log("  weather obs", c["city"], "failed:", e)
            card.update({"lat": c["lat"], "lon": c["lon"], "abbr": c["abbr"], "mid": mid, "where": c["where"], "now": "%d°" % now_t,
                         "cond": now_c[:1].upper() + now_c[1:].lower(), "note": " ".join(parts), "days": days})
            cards.append("    " + json.dumps(card, ensure_ascii=False, separators=(",", ":")))
            got += 1
        except Exception as e:  # noqa: BLE001
            log("  weather", c["city"], "failed:", e)
            m = re.search(r'\{"?city"?:\s*"%s".*?\]\]\}' % re.escape(c["city"]), old, re.S)
            if m:
                cards.append("    " + m.group(0))
    if not got:
        log("  weather: no data, left as is")
        return s
    s, _ = set_var(s, "WX", "[\n" + ",\n".join(cards) + "\n  ]")
    log("  weather: %d cities" % got)
    return s


# ------------------------------------------------------------------------------------------- Seahawks
NFL_SB = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
NCAAF_SB = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?groups=80&limit=300"


def do_travis(s, now_mt):
    """Weather With Travis: newest upload from the channel's RSS feed (added Oct 26, 2026)."""
    if "TRAVIS" not in s:
        return s
    try:
        x = urllib.request.urlopen(urllib.request.Request(
            "https://www.youtube.com/feeds/videos.xml?channel_id=UCTDfJ5sk6bLV_4VOfWV1BuQ",
            headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read().decode("utf8", "ignore")
        m = re.search(r"<entry>.*?<yt:videoId>(.*?)</yt:videoId>.*?<title>(.*?)</title>.*?<published>(.*?)</published>", x, re.S)
    except Exception as e:  # noqa: BLE001
        log("  travis failed:", e)
        return s
    if not m:
        return s
    import html as _h
    v = {"id": m.group(1), "title": _h.unescape(m.group(2)), "published": m.group(3)[:19] + "Z"}
    s, _ = set_var(s, "TRAVIS", json.dumps(v, ensure_ascii=False, separators=(",", ":")))
    log("  travis:", v["id"], v["title"])
    return s


def do_sermon(s, now_mt):
    """Sunday's sermon at the top of Morning Devotion (added Oct 26, 2026); never steps back to an older Sunday."""
    if "var SERMON = " not in s:
        return s
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import sermon
    try:
        x = urllib.request.urlopen(urllib.request.Request(sermon.FEED, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read().decode("utf8", "ignore")
        v = sermon.pick(x)
    except Exception as e:  # noqa: BLE001
        log("  sermon failed:", e)
        return s
    cur = sermon.current(s) or {}
    if not v or v.get("date", "") < cur.get("date", ""):
        return s
    s, _ = set_var(s, "SERMON", json.dumps(v, ensure_ascii=False, separators=(",", ":")))
    log("  sermon:", v["id"], v["date"], v["title"])
    return s


def do_seahawks(s, now_mt):
    return do_game(s, now_mt, "SEA_GAME", "SEA", NFL_SB, "seahawks", False)


def do_ducks(s, now_mt):
    """Oregon Ducks strip (added Oct 25, 2026): same as the Seahawks, from ESPN's college scoreboard, with team colors."""
    if "ORE_GAME" not in s:
        return s
    return do_game(s, now_mt, "ORE_GAME", "ORE", NCAAF_SB, "ducks", True)


def do_game(s, now_mt, var, abbr, url, name, colors):
    raw = get_var(s, var)
    try:
        g = json.loads(raw) if raw else {}
    except Exception:  # noqa: BLE001
        g = {}
    try:
        j = get(url)
    except Exception as e:  # noqa: BLE001
        log("  %s failed:" % name, e)
        return s
    for e in j.get("events", []):
        c = e["competitions"][0]
        t = {x["homeAway"]: x for x in c["competitors"]}
        if abbr not in (t["home"]["team"]["abbreviation"], t["away"]["team"]["abbreviation"]):
            continue
        state = c["status"]["type"]["state"]
        start = e["date"]
        if len(start) == 17:
            start = start[:-1] + ":00Z"
        if state == "pre":
            log("  %s: next game not started, strip left as is" % name)
            return s
        if g.get("start") and start < g["start"] and g.get("status") == "closed":
            return s
        ids = {x["team"]["id"]: x["team"]["abbreviation"] for x in c["competitors"]}
        si = c.get("situation") or {}
        lp = si.get("lastPlay") or {}
        same = g.get("away") == t["away"]["team"]["abbreviation"] and g.get("home") == t["home"]["team"]["abbreviation"] and g.get("start", "")[:13] == start[:13]
        rec = {}
        for side in ("away", "home"):
            r = (t[side].get("records") or [{}])[0].get("summary")
            if r:
                rec[t[side]["team"]["abbreviation"]] = r
        detail = c["status"]["type"].get("shortDetail", "")
        if (lp.get("type") or {}).get("text", "").lower().startswith("end of half"):
            detail = "Halftime"
        play_text = re.sub(r"^\s*(\([^)]*\)\s*)+", "", " ".join(str(lp.get("text", "")).split()))
        snap = lp and not re.search(r"timeout|kick|punt|field goal|extra point|two-minute|end of|end period|coin|official",
                                    (lp.get("type") or {}).get("text", ""), re.I)
        new = {
            "id": g.get("id", "") if same else "",
            "espn": str(e.get("id", "")),
            "start": start,
            "away": t["away"]["team"]["abbreviation"],
            "home": t["home"]["team"]["abbreviation"],
            "title": g.get("title", "") if same else "",
            "tv": g.get("tv", "") if same else "",
            "status": "inprogress" if state == "in" else "closed",
            "detail": detail,
            "score": {t["away"]["team"]["abbreviation"]: int(t["away"].get("score") or 0),
                      t["home"]["team"]["abbreviation"]: int(t["home"].get("score") or 0)},
            "poss": ids.get(str(si.get("possession", "")), "") if state == "in" else "",
            "spot": si.get("possessionText", "") if state == "in" else "",
            "dd": si.get("shortDownDistanceText", "") if state == "in" else "",
            "lp": ({"team": ids.get(str((lp.get("team") or {}).get("id", "")), ""), "yds": lp.get("statYardage") or 0,
                    "type": (lp.get("type") or {}).get("text", "")} if (snap and state == "in") else None),
            "play": play_text if state == "in" else "",
            "headline": g.get("headline", "") if same else "",
            "rec": rec or None,
            "asof": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if colors:
            new["col"] = {x["team"]["abbreviation"]: [x["team"].get("name") or x["team"].get("shortDisplayName") or x["team"]["abbreviation"],
                                                      "#" + (x["team"].get("color") or "444444"), "#" + (x["team"].get("alternateColor") or "999999")]
                          for x in c["competitors"]}
        s, _ = set_var(s, var, json.dumps(new, ensure_ascii=False, separators=(",", ":")))
        log("  %s:" % name, new["away"], new["score"][new["away"]], "at", new["home"], new["score"][new["home"]], new["detail"])
        return s
    log("  %s: no game this week" % name)
    return s


# ------------------------------------------------------------------------------------------- cams
def do_cams(s, now_mt):
    try:
        from PIL import Image
    except Exception:  # noqa: BLE001
        log("  cams: Pillow not installed, skipped")
        return s
    cams = re.findall(r'\{k:"(\w+)",\s*name:"[^"]*",\s*elev:"[^"]*",\s*src:"([^"]+)"\}', s)
    got = 0
    for k, url in cams:
        try:
            b = get(url, binary=True, headers={"Accept": "image/*"})
            im = Image.open(io.BytesIO(b)).convert("RGB")
            im.thumbnail((480, 480))
            o = io.BytesIO()
            im.save(o, "JPEG", quality=60, optimize=True)
            new = base64.b64encode(o.getvalue()).decode()
            s, n = re.subn(r'(\n\s*%s:")[A-Za-z0-9+/=]+(")' % k, lambda m: m.group(1) + new + m.group(2), s, count=1)
            got += n
        except Exception as e:  # noqa: BLE001
            log("  cam", k, "failed:", e)
    if got:
        s, _ = set_var(s, "SNAP_AT", json.dumps(dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
    log("  cams: %d snapshots" % got)
    return s


def do_ski_resorts(s, now_mt):
    """Resort conditions ticker on the Ski Weather page (Mark, Oct 28, 2026): see scripts/ski_conditions.py."""
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ski_conditions
    return ski_conditions.do_ski(s, now_mt, set_var=set_var, get_var=get_var)


def do_wsj_videos(s, now_mt):
    """WSJ Video section at the top of the Other News page (Mark, Oct 28, 2026): see scripts/wsj_videos.py."""
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import wsj_videos
    return wsj_videos.do_wsj(s, now_mt, set_var=set_var, get_var=get_var)


def main():
    path = sys.argv[1]
    s = open(path, encoding="utf-8").read()
    before = s
    now_mt = dt.datetime.now(MT)
    log("waltski data refresh", now_mt.strftime("%Y-%m-%d %H:%M MT"))
    for fn in (do_ticker, do_markets, do_spacex, do_weather, do_seahawks, do_ducks, do_travis, do_sermon, do_cams, do_ski_resorts, do_wsj_videos):
        try:
            s = fn(s, now_mt)
        except Exception as e:  # noqa: BLE001
            log("  %s crashed: %s" % (fn.__name__, e))
    if s != before:
        open(path, "w", encoding="utf-8").write(s)
        log("index.html updated")
    else:
        log("no changes")


if __name__ == "__main__":
    main()
