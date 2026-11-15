"""Composite snow forecast by Utah region (Mark, Nov 15, 2026).

Blends, for each region's mid-mountain point:
  * Open-Meteo deterministic models: ECMWF IFS, GFS, ICON, GEM (daily snowfall, highs, lows; 10 days)
  * Open-Meteo ensembles: ECMWF ENS (51) + GEFS (31) hourly snowfall -> daily 10th / 50th / 90th percentiles
  * NWS Salt Lake City gridpoint forecast (snowfallAmount, max/min temperature; about 7 days)
  * University of Utah downscaled snow ensemble (82 members, GEFS + ECMWF) for Little Cottonwood (its only text table)
  * NWS Salt Lake City Area Forecast Discussion: the first key message
Global models under-forecast mountain snow, so they are scaled to the NWS gridpoint forecast (ratio of their totals over the
days NWS covers, kept between 1 and 3). Composite daily snow = 45% NWS + 35% U of U + 20% scaled models (Cottonwoods),
65% NWS + 35% scaled models elsewhere, and the scaled models alone after the NWS forecast ends.
Prints `var COMPOSITE = {...};` when run directly; update_data.py imports build().
"""
import datetime as dt
import json
import re
import statistics as st
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

MT = ZoneInfo("America/Denver")
UA = {"User-Agent": "skiinut.com composite forecast (github.com/storybi/waltski)", "Accept": "application/json,application/geo+json,*/*"}

# Region -> representative mid-mountain point. keys = resort-menu values that use this region.
REGIONS = [
    ("ogden", "Ogden Valley", "Snowbasin · Powder Mountain · Nordic Valley", 41.200, -111.870, 2450, ["sb", "powmow"]),
    ("cottonwoods", "Cottonwood Canyons", "Alta · Snowbird · Brighton · Solitude", 40.590, -111.620, 2900, ["alta", "snowbird", "brighton", "solitude"]),
    ("parkcity", "Park City", "Park City · Deer Valley", 40.635, -111.540, 2550, ["dv", "parkcity"]),
    ("provo", "Provo Canyon", "Sundance", 40.385, -111.600, 2300, []),
    ("logan", "Logan & Bear River", "Beaver Mountain · Cherry Peak", 41.970, -111.540, 2300, []),
    ("south", "Southern Utah", "Brian Head · Eagle Point", 37.690, -112.850, 3000, []),
]
MODELS = ["ecmwf_ifs025", "gfs_seamless", "icon_seamless", "gem_seamless"]
DAYS = 10


def _get(url, tries=3, raw=False):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                b = r.read().decode("utf-8")
                return b if raw else json.loads(b)
        except Exception as e:  # noqa: BLE001
            last = e
            import time
            time.sleep(1.5 * (i + 1))
    raise last


def _om_det(lat, lon, elev):
    q = urllib.parse.urlencode({"latitude": lat, "longitude": lon, "elevation": elev, "models": ",".join(MODELS),
                                "daily": "snowfall_sum,temperature_2m_max,temperature_2m_min", "timezone": "America/Denver",
                                "forecast_days": DAYS, "temperature_unit": "fahrenheit", "precipitation_unit": "inch"})
    d = _get("https://api.open-meteo.com/v1/forecast?" + q)["daily"]
    out = {}
    for m in MODELS:
        out[m] = {"snow": d.get("snowfall_sum_" + m), "hi": d.get("temperature_2m_max_" + m), "lo": d.get("temperature_2m_min_" + m)}
    return d["time"], out


def _om_ens(lat, lon, elev, dates):
    """daily snowfall per member -> {date: (p10, p50, p90)}"""
    q = urllib.parse.urlencode({"latitude": lat, "longitude": lon, "elevation": elev, "models": "ecmwf_ifs025,gfs025",
                                "hourly": "snowfall", "timezone": "America/Denver", "forecast_days": DAYS, "precipitation_unit": "inch"})
    h = _get("https://ensemble-api.open-meteo.com/v1/ensemble?" + q)["hourly"]
    t = h["time"]
    mem = [k for k in h if k.startswith("snowfall")]
    res = {}
    for day in dates:
        idx = [i for i, x in enumerate(t) if x.startswith(day)]
        tots = []
        for k in mem:
            v = [h[k][i] for i in idx if h[k][i] is not None]
            if len(v) >= 12:
                tots.append(sum(v))
        if len(tots) >= 10:
            tots.sort()
            q10, q50, q90 = tots[int(len(tots) * .1)], st.median(tots), tots[min(len(tots) - 1, int(len(tots) * .9))]
            res[day] = (q10, q50, q90)
    return res


def _iso_dur(s):
    m = re.match(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?)?", s)
    return int(m.group(1) or 0) * 24 + int(m.group(2) or 0)


def _nws(lat, lon, dates):
    """NWS gridpoint: {date: {'snow': in, 'hi': F, 'lo': F}}"""
    p = _get("https://api.weather.gov/points/%.4f,%.4f" % (lat, lon))
    g = _get(p["properties"]["forecastGridData"])["properties"]
    res = {d: {"snow": 0.0, "hi": None, "lo": None, "_sn": False} for d in dates}
    for v in g.get("snowfallAmount", {}).get("values", []):
        start, dur = v["validTime"].split("/")
        t0 = dt.datetime.fromisoformat(start).astimezone(MT)
        hours = max(1, _iso_dur(dur))
        amt = (v["value"] or 0) / 25.4
        for k in range(hours):   # spread the amount evenly over its hours, so it lands on the right local days
            day = (t0 + dt.timedelta(hours=k)).strftime("%Y-%m-%d")
            if day in res:
                res[day]["snow"] += amt / hours
                res[day]["_sn"] = True
    for key, fld in (("maxTemperature", "hi"), ("minTemperature", "lo")):
        for v in g.get(key, {}).get("values", []):
            start = v["validTime"].split("/")[0]
            t0 = dt.datetime.fromisoformat(start).astimezone(MT)
            day = (t0 + dt.timedelta(hours=6)).strftime("%Y-%m-%d")
            if day in res and v["value"] is not None:
                res[day][fld] = v["value"] * 9 / 5 + 32
    return {d: x for d, x in res.items() if x["_sn"] or x["hi"] is not None}


def _afd_key():
    try:
        lst = _get("https://api.weather.gov/products/types/AFD/locations/SLC")
        url = lst["@graph"][0]["@id"]
        txt = _get(url)["productText"]
    except Exception:  # noqa: BLE001
        return "", ""
    issued = ""
    m = re.search(r"\n(\d{3,4} [AP]M [A-Z]{3} \w{3} \w{3} \d+ \d{4})\n", txt)
    if m:
        issued = m.group(1)
    blk = re.search(r"\.KEY MESSAGES\.\.\.(.*?)(?:\n&&|\n\.[A-Z])", txt, re.S)
    if not blk:
        blk = re.search(r"\.SYNOPSIS\.\.\.(.*?)(?:\n&&|\n\.[A-Z])", txt, re.S)
    if not blk:
        return "", issued
    t = re.sub(r"\s+", " ", blk.group(1)).strip()
    parts = [x.strip(" -*") for x in re.split(r"\s[-*]\s", " " + t) if x.strip(" -*")]
    first = parts[0] if parts else t
    first = first[0].upper() + first[1:].lower() if first.isupper() else first
    if len(first) > 280:   # whole sentences only
        cut = first[:280].rfind(". ")
        first = first[:cut + 1] if cut > 60 else first[:277].rsplit(" ", 1)[0] + "…"
    return first, issued


def _r(x, n=1):
    return None if x is None else round(x, n)


def _uofu_cln():
    """University of Utah downscaled ensemble, Little Cottonwood (CLN): {date: (p10, p50, p90)} daily snowfall, in."""
    html = _get("https://weather.utah.edu/text/ensgefsdslccforecast.html", raw=True)
    body = re.sub(r"<style.*?</style>", "", html, flags=re.S)
    heads = [re.sub(r"<[^>]+>", " ", h).strip() for h in re.findall(r"<h\d[^>]*>(.*?)</h\d>", body, re.S)]
    tables = re.findall(r"<table.*?</table>", body, re.S)
    k = [i for i, h in enumerate(heads) if "6-h Snowfall" in h]
    tb = tables[k[0] if k else 3]
    cols = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<th[^>]*col_heading[^>]*>(.*?)</th>", tb, re.S)]
    rows = {}
    for tr in re.findall(r"<tr>(.*?)</tr>", tb, re.S):
        name = re.findall(r"<th[^>]*row_heading[^>]*>(.*?)</th>", tr, re.S)
        if name:
            rows[name[0].strip()] = [float(re.sub(r"<[^>]+>", "", x).strip() or 0) for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
    daily = {}
    for ci, col in enumerate(cols):
        tt = dt.datetime.strptime(col, "%I %p %a %d %b %Y")
        d = (tt - dt.timedelta(hours=3)).strftime("%Y-%m-%d")   # the 6 h ending at tt -> the day of its middle
        x = daily.setdefault(d, [0.0, 0.0, 0.0])
        for j, row in enumerate(("P10", "P50", "P90")):
            x[j] += rows[row][ci]
    return {d: tuple(v) for d, v in daily.items()}


def _region(lat, lon, elev, uofu=None):
    dates, det = _om_det(lat, lon, elev)
    try:
        ens = _om_ens(lat, lon, elev, dates)
    except Exception:  # noqa: BLE001
        ens = {}
    try:
        nws = _nws(lat, lon, dates)
    except Exception:  # noqa: BLE001
        nws = {}
    uofu = uofu or {}
    n_days = [d for d in dates if d in nws and nws[d]["_sn"]]
    mavg = []
    for i, d in enumerate(dates):
        ms = [det[m]["snow"][i] for m in MODELS if det[m]["snow"] and det[m]["snow"][i] is not None]
        if d in ens:
            ms.append(ens[d][1])
        mavg.append(st.mean(ms) if ms else 0.0)
    # orographic scale: global models -> NWS gridpoint totals over the days NWS covers
    mt = sum(mavg[i] for i, d in enumerate(dates) if d in n_days)
    nt = sum(nws[d]["snow"] for d in n_days)
    k = max(1.0, min(3.0, nt / mt)) if mt > 1 and nt > 0 else (1.0 if not n_days else 1.5)
    rows, srcs = [], {"nws": [], "uofu": [], "models": []}
    for i, d in enumerate(dates):
        sm = mavg[i] * k
        n = nws.get(d) if d in n_days else None
        u = uofu.get(d)
        if n and u:
            comp = .45 * n["snow"] + .35 * u[1] + .20 * sm
        elif n:
            comp = .65 * n["snow"] + .35 * sm
        elif u:
            comp = .6 * u[1] + .4 * sm
        else:
            comp = sm
        pool = [comp, sm] + [det[m]["snow"][i] * k for m in MODELS if det[m]["snow"] and det[m]["snow"][i] is not None]
        if n:
            pool.append(n["snow"])
        if u:
            pool.append(u[1])
        srcs["nws"].append(n["snow"] if n else None)
        srcs["uofu"].append(u[1] if u else None)
        srcs["models"].append(sm)
        his = [det[m]["hi"][i] for m in MODELS if det[m]["hi"] and det[m]["hi"][i] is not None] + ([nws[d]["hi"]] if d in nws and nws[d]["hi"] is not None else [])
        los = [det[m]["lo"][i] for m in MODELS if det[m]["lo"] and det[m]["lo"][i] is not None] + ([nws[d]["lo"]] if d in nws and nws[d]["lo"] is not None else [])
        rows.append([_r(comp), _r(min(pool)), _r(max(pool)), _r(st.mean(his), 0) if his else None, _r(st.mean(los), 0) if los else None])
    return dates, rows, bool(n_days), bool(ens), round(k, 2), srcs


DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _dname(d, today):
    x = dt.date.fromisoformat(d)
    if x == today:
        return "today"
    if x == today + dt.timedelta(days=1):
        return "tomorrow"
    if (x - today).days >= 6:
        return "%s %d" % (DOW[x.weekday()], x.day)
    return DOW[x.weekday()]


def _amt(a, b):
    a, b = int(round(a)), int(round(b))
    if b <= 1:
        return "a trace to 1\""
    if a == b:
        return "%d\"" % a
    return "%d–%d\"" % (a, b)


def _summary(dates, rows, today, srcs=None):
    snow = [r[0] or 0 for r in rows]
    parts = []
    # leading dry spell
    k = 0
    while k < len(snow) and snow[k] < .5:
        k += 1
    if k >= len(snow):
        parts.append("Dry for the next %d days, no meaningful snow in the forecast." % len(snow))
    elif k >= 2:
        parts.append("Dry through %s." % _dname(dates[k - 1], today))
    # storm periods (days with >= 0.5" composite, gaps of one light day joined)
    periods, i = [], 0
    while i < len(snow):
        if snow[i] >= .5:
            j = i
            while j + 1 < len(snow) and (snow[j + 1] >= .5 or (j + 2 < len(snow) and snow[j + 1] >= .2 and snow[j + 2] >= .5)):
                j += 1
            periods.append((i, j))
            i = j + 1
        else:
            i += 1
    periods = [p for p in periods if sum(snow[p[0]:p[1] + 1]) >= 1.5][:3]   # skip specks
    for (a, b) in periods:
        tot = sum(snow[a:b + 1])
        tots = [tot]
        for key in ("nws", "uofu", "models"):
            v = (srcs or {}).get(key) or []
            seg = v[a:b + 1]
            if seg and all(x is not None for x in seg):
                tots.append(sum(seg))
        lo, hi = min(tots), max(tots)
        if hi - lo < max(1, .3 * tot):   # sources agree closely: show a modest +/- range around the blend
            lo, hi = tot * .8, tot * 1.25
        when = _dname(dates[a], today) if a == b else "%s–%s" % (_dname(dates[a], today), _dname(dates[b], today))
        when = when[0].upper() + when[1:]
        his = [rows[x][3] for x in range(a, b + 1) if rows[x][3] is not None]
        feel = ""
        if his and his[0] >= 38:
            feel = ", starting wet and heavy (rain possible at lower elevations)"
        elif his and st.mean(his) <= 28:
            feel = ", cold and light"
        conf = " (low confidence)" if a >= 6 or (hi - lo) > max(8, 1.2 * tot) else ""
        parts.append("%s: %s, best guess %d\"%s%s." % (when, _amt(lo, hi), round(tot), feel, conf))
    t5 = sum(snow[1:6])   # the next 5 days: tomorrow through day 5
    t10 = sum(snow)
    wd = lambda d: DOW[dt.date.fromisoformat(d).weekday()]
    parts.append("Totals: about %d\" %s–%s, %d\" through %s." % (round(t5), wd(dates[1]), wd(dates[5]), round(t10), _dname(dates[-1], today)))
    his = [r[3] for r in rows if r[3] is not None]
    if his:
        cold_i = min(range(len(rows)), key=lambda x: rows[x][3] if rows[x][3] is not None else 999)
        warm_i = max(range(len(rows)), key=lambda x: rows[x][3] if rows[x][3] is not None else -999)
        parts.append("Highs %d° (%s) to %d° (%s)." % (rows[cold_i][3], _dname(dates[cold_i], today), rows[warm_i][3], _dname(dates[warm_i], today)))
    return " ".join(parts), [round(t5, 1), round(t10, 1)]


def build():
    now = dt.datetime.now(MT)
    today = now.date()
    out = {"asof": now.strftime("%a %-I:%M %p MT").replace("AM", "a.m.").replace("PM", "p.m."), "regions": {}, "keys": {}}
    allrows = []
    dates = None
    flags = {"nws": False, "ens": False, "uofu": False}
    try:
        cln = _uofu_cln()
    except Exception as e:  # noqa: BLE001
        print("composite: U of U table failed: %s" % e)
        cln = {}
    for (rid, name, resorts, lat, lon, elev, keys) in REGIONS:
        try:
            d, rows, has_n, has_e, k, srcs = _region(lat, lon, elev, cln if rid == "cottonwoods" else None)
        except Exception as e:  # noqa: BLE001
            print("composite: %s failed: %s" % (rid, e))
            continue
        dates = dates or d
        flags["nws"] |= has_n
        flags["ens"] |= has_e
        flags["uofu"] |= bool(cln) and rid == "cottonwoods"
        summ, tots = _summary(d, rows, today, srcs)
        out["regions"][rid] = {"name": name, "resorts": resorts, "ft": int(round(elev * 3.281, -2)), "d": rows, "sum": summ, "tot": tots, "k": k}
        for k in keys:
            out["keys"][k] = rid
        allrows.append(rows)
    if not dates:
        return None
    # general Utah: average of the regions
    ut = []
    for i in range(len(dates)):
        col = [r[i] for r in allrows]
        def avg(j):
            v = [c[j] for c in col if c[j] is not None]
            return _r(st.mean(v), 0 if j >= 3 else 1) if v else None
        ut.append([avg(0), avg(1), avg(2), avg(3), avg(4)])
    summ, tots = _summary(dates, ut, today)
    out["regions"]["utah"] = {"name": "Utah (general)", "resorts": "average of the six Utah ski regions", "ft": None, "d": ut, "sum": summ, "tot": tots}
    out["dates"] = dates
    km, issued = _afd_key()
    out["nws"] = km
    out["nws_at"] = issued
    out["src"] = ["NWS Salt Lake City" if flags["nws"] else None, "University of Utah snow ensemble" if flags["uofu"] else None,
                  "ECMWF", "GFS", "ICON", "GEM", "ECMWF & GEFS ensembles" if flags["ens"] else None]
    out["src"] = [x for x in out["src"] if x]
    return out


if __name__ == "__main__":
    c = build()
    print("var COMPOSITE = %s;" % json.dumps(c, separators=(",", ":"), ensure_ascii=False))
