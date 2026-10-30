#!/usr/bin/env python3
"""Rocky Mountain and US Ikon Pass resort conditions for the Ski Weather ticker on www.skiinut.com (Mark, Oct 28, 2026).

For each resort in RESORTS (Utah first, then Colorado, Wyoming, Idaho, Montana, New Mexico and the Canadian Rockies):
  * base depth, 24-hour new snow, open/closed, opening date and lifts open: OnTheSnow's public region pages
    (onthesnow.com/<region>/skireport; their Next.js page payload carries one record per resort, depths in cm);
  * current temperature and weather: Open-Meteo's free forecast API, one call for every resort's coordinates.

Used two ways:
  * scripts/update_data.py imports do_ski() and rewrites `var SKI_ASOF` / `var SKI` in index.html (hourly job);
  * `python3 scripts/ski_conditions.py` prints three JavaScript lines (SKI_ASOF, SKI, OUTLOOK), for Claude's daily artifact refresh.
OUTLOOK is today's hour-by-hour rain/snow outlook (Open-Meteo) for each radar location, used by the 24-hour outlook chart.

SKI rows: [name, state, onthesnow path, lat, lon, base_in|null, new24_in|null, open(1/0), opening "YYYY-MM-DD"|"",
           lifts_open|null, lifts_total|null, temp_F|null, WMO weather code|null]
"""
import datetime as dt
import json
import re
import sys
import urllib.request
from zoneinfo import ZoneInfo

MT = ZoneInfo("America/Denver")
HTML_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
           "Accept": "text/html"}

# name, state, onthesnow path, lat, lon  — keep Utah first (Mark's request)
RESORTS = [
    ["Snowbasin", "UT", "utah/snowbasin", 41.2156, -111.8619],
    ["Powder Mountain", "UT", "utah/powder-mountain", 41.3985, -111.763],
    ["Nordic Valley", "UT", "utah/wolf-creek", 41.3105, -111.8649],
    ["Beaver Mountain", "UT", "utah/beaver-mountain", 41.9682, -111.5413],
    ["Snowbird", "UT", "utah/snowbird", 40.5836, -111.6566],
    ["Alta", "UT", "utah/alta-ski-area", 40.5885, -111.6386],
    ["Brighton", "UT", "utah/brighton-resort", 40.5977, -111.5848],
    ["Solitude", "UT", "utah/solitude-mountain-resort", 40.6191, -111.5935],
    ["Park City", "UT", "utah/park-city-mountain-resort", 40.6539, -111.5094],
    ["Deer Valley", "UT", "utah/deer-valley-resort", 40.6381, -111.4796],
    ["Sundance", "UT", "utah/sundance", 40.388, -111.5774],
    ["Brian Head", "UT", "utah/brian-head-resort", 37.7013, -112.8464],
    ["Eagle Point", "UT", "utah/eagle-point", 38.3203, -112.3838],
    ["Vail", "CO", "colorado/vail", 39.643, -106.3785],
    ["Beaver Creek", "CO", "colorado/beaver-creek", 39.604, -106.5173],
    ["Breckenridge", "CO", "colorado/breckenridge", 39.4812, -106.0477],
    ["Keystone", "CO", "colorado/keystone", 39.6047, -105.9539],
    ["Arapahoe Basin", "CO", "colorado/arapahoe-basin-ski-area", 39.6417, -105.8791],
    ["Copper Mountain", "CO", "colorado/copper-mountain-resort", 39.4998, -106.1571],
    ["Loveland", "CO", "colorado/loveland", 39.6801, -105.8979],
    ["Winter Park", "CO", "colorado/winter-park-resort", 39.8879, -105.7626],
    ["Steamboat", "CO", "colorado/steamboat", 40.4655, -106.7868],
    ["Aspen Snowmass", "CO", "colorado/aspen-snowmass", 39.1909, -106.8211],
    ["Telluride", "CO", "colorado/telluride", 37.9375, -107.8123],
    ["Crested Butte", "CO", "colorado/crested-butte-mountain-resort", 38.8957, -106.9662],
    ["Wolf Creek", "CO", "colorado/wolf-creek-ski-area", 37.4671, -106.7774],
    ["Purgatory", "CO", "colorado/durango-mountain-resort", 37.6292, -107.8155],
    ["Monarch", "CO", "colorado/monarch-mountain", 38.5121, -106.3322],
    ["Eldora", "CO", "colorado/eldora-mountain-resort", 39.9372, -105.5807],
    ["Jackson Hole", "WY", "wyoming/jackson-hole", 43.5882, -110.8272],
    ["Grand Targhee", "WY", "wyoming/grand-targhee-resort", 43.7877, -110.9584],
    ["Sun Valley", "ID", "idaho/sun-valley", 43.6707, -114.3681],
    ["Big Sky", "MT", "montana/big-sky-resort", 45.2848, -111.4014],
    ["Bridger Bowl", "MT", "montana/bridger-bowl", 45.8174, -110.8966],
    ["Whitefish", "MT", "montana/whitefish-mountain-resort", 48.4806, -114.3501],
    ["Red Lodge", "MT", "montana/red-lodge-mountain", 45.1911, -109.3364],
    ["Taos", "NM", "new-mexico/taos-ski-valley", 36.596, -105.4544],
    ["Ski Santa Fe", "NM", "new-mexico/ski-santa-fe", 35.7966, -105.8013],
    ["Lake Louise", "AB", "alberta/lake-louise", 51.4434, -116.1668],
    ["Banff Sunshine", "AB", "alberta/banff-sunshine", 51.0786, -115.7765],
    ["Mt. Norquay", "AB", "alberta/ski-banff-norquay", 51.2116, -115.603],
    ["Marmot Basin", "AB", "alberta/marmot-basin", 52.8014, -118.083],
    ["Fernie", "BC", "british-columbia/fernie-alpine", 49.463, -115.0864],
]


# US Ikon Pass resorts (2026/27 full Ikon Pass), keyed like the page's resort picker (Mark, Oct 30, 2026):
# key, name, state, lat, lon, onthesnow path, where
IKON = [
    ["sb", "Snowbasin", "UT", 41.216, -111.8569, "utah/snowbasin", "Huntsville, Utah · Ogden Valley"],
    ["alta", "Alta", "UT", 40.5884, -111.6386, "utah/alta-ski-area", "Little Cottonwood Canyon, Utah"],
    ["snowbird", "Snowbird", "UT", 40.583, -111.6556, "utah/snowbird", "Little Cottonwood Canyon, Utah"],
    ["brighton", "Brighton", "UT", 40.598, -111.5832, "utah/brighton-resort", "Big Cottonwood Canyon, Utah"],
    ["solitude", "Solitude", "UT", 40.6199, -111.5919, "utah/solitude-mountain-resort", "Big Cottonwood Canyon, Utah"],
    ["dv", "Deer Valley", "UT", 40.6375, -111.4783, "utah/deer-valley-resort", "Park City, Utah · Wasatch Back"],
    ["abasin", "Arapahoe Basin", "CO", 39.6425, -105.8719, "colorado/arapahoe-basin-ski-area", "Summit County, Colorado"],
    ["aspen", "Aspen Snowmass", "CO", 39.2084, -106.949, "colorado/aspen-snowmass", "Aspen & Snowmass Village, Colorado"],
    ["copper", "Copper Mountain", "CO", 39.5022, -106.1511, "colorado/copper-mountain-resort", "Summit County, Colorado"],
    ["eldora", "Eldora", "CO", 39.9372, -105.5827, "colorado/eldora-mountain-resort", "Nederland, Colorado"],
    ["steamboat", "Steamboat", "CO", 40.4572, -106.8045, "colorado/steamboat", "Steamboat Springs, Colorado"],
    ["winterpark", "Winter Park", "CO", 39.8868, -105.7625, "colorado/winter-park-resort", "Winter Park, Colorado"],
    ["bigsky", "Big Sky", "MT", 45.2857, -111.4012, "montana/big-sky-resort", "Big Sky, Montana"],
    ["jackson", "Jackson Hole", "WY", 43.5875, -110.8279, "wyoming/jackson-hole", "Teton Village, Wyoming"],
    ["taos", "Taos Ski Valley", "NM", 36.596, -105.4545, "new-mexico/taos-ski-valley", "Taos Ski Valley, New Mexico"],
    ["sv", "Sun Valley", "ID", 43.671, -114.364, "idaho/sun-valley", "Ketchum, Idaho · Wood River Valley"],
    ["schweitzer", "Schweitzer", "ID", 48.3677, -116.6227, "idaho/schweitzer", "Sandpoint, Idaho"],
    ["mammoth", "Mammoth Mountain", "CA", 37.651, -119.027, "california/mammoth-mountain-ski-area", "Mammoth Lakes, California"],
    ["june", "June Mountain", "CA", 37.7678, -119.0904, "california/june-mountain", "June Lake, California"],
    ["palisades", "Palisades Tahoe", "CA", 39.1966, -120.2345, "california/palisades-tahoe", "Olympic Valley, California"],
    ["sierra", "Sierra-at-Tahoe", "CA", 38.8004, -120.0808, "california/sierra-at-tahoe", "Twin Bridges, California"],
    ["bigbear", "Big Bear Mountain", "CA", 34.2283, -116.8914, "california/snow-summit", "Big Bear Lake, California"],
    ["snowvalley", "Snow Valley", "CA", 34.2245, -117.0367, "california/snow-valley", "Running Springs, California"],
    ["crystal", "Crystal Mountain", "WA", 46.9327, -121.4877, "washington/crystal-mountain-wa", "Mount Rainier area, Washington"],
    ["snoqualmie", "Summit at Snoqualmie", "WA", 47.411, -121.414, "washington/the-summit-at-snoqualmie", "Snoqualmie Pass, Washington"],
    ["bachelor", "Mt. Bachelor", "OR", 43.9792, -121.6886, "oregon/mt-bachelor", "Bend, Oregon"],
    ["alyeska", "Alyeska", "AK", 60.9703, -149.0987, "alaska/alyeska-resort", "Girdwood, Alaska"],
    ["killington", "Killington-Pico", "VT", 43.6262, -72.7965, "vermont/killington-resort", "Killington, Vermont"],
    ["stratton", "Stratton", "VT", 43.1027, -72.9048, "vermont/stratton-mountain", "Stratton, Vermont"],
    ["sugarbush", "Sugarbush", "VT", 44.1359, -72.8944, "vermont/sugarbush", "Warren, Vermont"],
    ["sugarloaf", "Sugarloaf", "ME", 45.0544, -70.3087, "maine/sugarloaf", "Carrabassett Valley, Maine"],
    ["sundayriver", "Sunday River", "ME", 44.4734, -70.8567, "maine/sunday-river", "Newry, Maine"],
    ["loon", "Loon Mountain", "NH", 44.0451, -71.6366, "new-hampshire/loon-mountain", "Lincoln, New Hampshire"],
    ["windham", "Windham Mountain", "NY", 42.2939, -74.2613, "new-york/windham-mountain", "Windham, New York"],
    ["bluemtn", "Blue Mountain", "PA", 40.8167, -75.5098, "pennsylvania/blue-mountain-ski-area", "Palmerton, Pennsylvania"],
    ["camelback", "Camelback", "PA", 41.0507, -75.3557, "pennsylvania/camelback-mountain-resort", "Tannersville, Pennsylvania"],
    ["snowshoe", "Snowshoe", "WV", 38.4117, -79.9947, "west-virginia/snowshoe-mountain-resort", "Snowshoe, West Virginia"],
    ["boyne", "Boyne Mountain", "MI", 45.164, -84.933, "michigan/boyne-mountain-resort", "Boyne Falls, Michigan"],
    ["highlands", "The Highlands", "MI", 45.4683, -84.9139, "michigan/boyne-highlands", "Harbor Springs, Michigan"],
    ["snowriver", "Snowriver", "MI", 46.5002, -89.9758, "michigan/snowriver-mountain-resort", "Wakefield, Michigan"],
    ["lutsen", "Lutsen Mountains", "MN", 47.656, -90.7251, "minnesota/lutsen-mountains", "Lutsen, Minnesota"],
    ["granitepeak", "Granite Peak", "WI", 44.9258, -89.6857, "wisconsin/granite-peak-ski-area", "Wausau, Wisconsin"],
]

# Ikon resorts not already in the Rockies list join the ticker (Mark, Oct 30, 2026), after the Rockies.
_have = {r[2] for r in RESORTS}
RESORTS += [[r[1], r[2], r[5], r[3], r[4]] for r in IKON if r[5] not in _have]


def _get(url, headers, timeout=30):
    last = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


def _flight(url):
    """Decode a Next.js App Router page payload into {id: value} plus a resolver for "$id" references."""
    t = _get(url, HTML_UA).decode("utf-8", "ignore")
    buf = "".join(json.loads('"' + m.group(1) + '"')
                  for m in re.finditer(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', t, re.S))
    rows = {}
    for line in re.split(r"\n(?=[0-9a-f]+:)", buf):
        mm = re.match(r"([0-9a-f]+):(.*)", line, re.S)
        if mm:
            try:
                rows[mm.group(1)] = json.loads(mm.group(2))
            except Exception:  # noqa: BLE001
                pass

    def res(v, depth=0):
        if depth > 8:
            return v
        if isinstance(v, str) and re.fullmatch(r"\$[0-9a-f]+", v):
            return res(rows.get(v[1:], v), depth + 1)
        if isinstance(v, dict):
            return {k: res(x, depth + 1) for k, x in v.items()}
        if isinstance(v, list):
            return [res(x, depth + 1) for x in v]
        return v
    return rows, res


def _inches(cm):
    return None if cm is None else int(round(float(cm) / 2.54))


def fetch(prev=None):
    """Return (asof_text, rows). prev = the page's current rows, used to keep old values when a source fails."""
    old = {r[2]: r for r in (prev or [])}
    snow = {}
    for region in sorted({r[2].split("/")[0] for r in RESORTS}):
        try:
            rows, res = _flight("https://www.onthesnow.com/%s/skireport" % region)
        except Exception as e:  # noqa: BLE001
            print("  ski: %s failed: %s" % (region, e))
            continue
        for v in rows.values():
            if isinstance(v, dict) and "slug" in v and "snow" in v and "status" in v and "title_short" in v:
                snow[region + "/" + v["slug"]] = res(v)
    wx = {}
    try:
        q = "https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&current=temperature_2m,weather_code&temperature_unit=fahrenheit&timezone=UTC" % (
            ",".join(str(r[3]) for r in RESORTS), ",".join(str(r[4]) for r in RESORTS))
        data = json.loads(_get(q, {"User-Agent": HTML_UA["User-Agent"], "Accept": "application/json"}).decode("utf-8"))
        data = data if isinstance(data, list) else [data]
        for r, d in zip(RESORTS, data):
            c = d.get("current") or {}
            if c.get("temperature_2m") is not None:
                wx[r[2]] = (int(round(c["temperature_2m"])), c.get("weather_code"))
    except Exception as e:  # noqa: BLE001
        print("  ski: open-meteo failed:", e)
    out = []
    for name, st, path, lat, lon in RESORTS:
        o = old.get(path)
        s = snow.get(path)
        if s:
            sd = s.get("snow") or {}
            depth = next((sd[k] for k in ("base", "middle", "summit") if sd.get(k) is not None), None)
            stt = s.get("status") or {}
            lifts = s.get("lifts") or {}
            row = [name, st, path, lat, lon, _inches(depth), _inches(sd.get("last24")),
                   1 if stt.get("openFlag") == 1 else 0, stt.get("openingDate") or "",
                   lifts.get("open"), lifts.get("total")]
        elif o:
            row = list(o[:11])
        else:
            row = [name, st, path, lat, lon, None, None, 0, "", None, None]
        t = wx.get(path)
        row += [t[0], t[1]] if t else ([o[11], o[12]] if o and len(o) > 12 else [None, None])
        out.append(row)
    asof = dt.datetime.now(MT).strftime("%a %-I:%M %p MT").replace("AM", "a.m.").replace("PM", "p.m.")
    return asof, out, len(snow), len(wx)


def js(asof, rows):
    body = ",\n    ".join(json.dumps(r, separators=(",", ":")) for r in rows)
    return 'var SKI_ASOF = %s;' % json.dumps(asof), "var SKI = [\n    %s\n  ];" % body



# --------------------------------------------------------------------------------------------- 24-hour outlook
# Today's hour-by-hour rain and snow outlook for each radar location (Mark, Oct 28, 2026), shown under the resort cams.
# Keys match the resort picker (every US Ikon resort, plus hi). Each location uses its own local day, 12 a.m. to 11 p.m.
OUTLOOK_PLACES = [(r[0], r[1], r[3], r[4]) for r in IKON] + [("hi", "Kailua", 21.4022, -157.7394)]


def fetch_outlook():
    """{key: {"name", "date", "h": [[chance %, rain in, snow in, temp F] x 48]}, "asof": "..."}  (today 12 a.m. through tomorrow 11 p.m.; rain includes showers)"""
    q = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&hourly=precipitation_probability,rain,showers,snowfall,temperature_2m"
         "&temperature_unit=fahrenheit&precipitation_unit=inch&timezone=auto&forecast_days=2") % (
        ",".join(str(p[2]) for p in OUTLOOK_PLACES), ",".join(str(p[3]) for p in OUTLOOK_PLACES))
    data = json.loads(_get(q, {"User-Agent": HTML_UA["User-Agent"], "Accept": "application/json"}).decode("utf-8"))
    data = data if isinstance(data, list) else [data]
    out = {}
    for (key, name, lat, lon), d in zip(OUTLOOK_PLACES, data):
        h = d.get("hourly") or {}
        t = h.get("time") or []
        if len(t) < 24:
            continue
        rows = []
        m = min(48, len(t))
        for i in range(m):
            pr = (h.get("precipitation_probability") or [None] * m)[i]
            rn = ((h.get("rain") or [0] * m)[i] or 0) + ((h.get("showers") or [0] * m)[i] or 0)
            sn = (h.get("snowfall") or [0] * m)[i] or 0
            tp = (h.get("temperature_2m") or [None] * m)[i]
            rows.append([pr if pr is not None else 0, round(rn, 3), round(sn, 2), None if tp is None else int(round(tp))])
        out[key] = {"name": name, "date": t[0][:10], "h": rows}
    out["asof"] = dt.datetime.now(MT).strftime("%a %-I:%M %p MT").replace("AM", "a.m.").replace("PM", "p.m.")
    return out


RWX_WHERE = dict([(r[0], r[6]) for r in IKON] + [("hi", "Windward O\u02bbahu, Hawaii")])
RWX_NAME = dict([(r[0], r[1]) for r in IKON] + [("hi", "Kailua, O\u02bbahu")])


def fetch_resort_wx():
    """Weather card for the resort picked in the radar menu (Mark, Oct 29, 2026):
    {key: {"name", "where", "now" (F), "code" (WMO), "days": [[date, code, hi, lo, chance %] x 7]}, "asof": "..."}"""
    q = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&current=temperature_2m,weather_code,is_day"
         "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
         "&temperature_unit=fahrenheit&timezone=auto&forecast_days=7") % (
        ",".join(str(p[2]) for p in OUTLOOK_PLACES), ",".join(str(p[3]) for p in OUTLOOK_PLACES))
    data = json.loads(_get(q, {"User-Agent": HTML_UA["User-Agent"], "Accept": "application/json"}).decode("utf-8"))
    data = data if isinstance(data, list) else [data]
    out = {}
    for (key, name, lat, lon), d in zip(OUTLOOK_PLACES, data):
        c, dl = d.get("current") or {}, d.get("daily") or {}
        t = dl.get("time") or []
        if not t:
            continue
        rd = lambda v: None if v is None else int(round(v))
        days = [[t[i], (dl.get("weather_code") or [None] * len(t))[i], rd((dl.get("temperature_2m_max") or [None] * len(t))[i]),
                 rd((dl.get("temperature_2m_min") or [None] * len(t))[i]), (dl.get("precipitation_probability_max") or [None] * len(t))[i]]
                for i in range(min(7, len(t)))]
        out[key] = {"name": RWX_NAME[key], "where": RWX_WHERE[key], "now": rd(c.get("temperature_2m")), "code": c.get("weather_code"),
                    "day": c.get("is_day", 1), "days": days}
    out["asof"] = dt.datetime.now(MT).strftime("%a %-I:%M %p MT").replace("AM", "a.m.").replace("PM", "p.m.")
    return out


def outlook_js(o):
    return "var OUTLOOK = %s;" % json.dumps(o, separators=(",", ":"))

def do_ski(s, now_mt=None, set_var=None, get_var=None):
    """Hook for scripts/update_data.py: rewrite SKI_ASOF, SKI, OUTLOOK and RWX in the page text s."""
    prev = None
    try:
        raw = get_var(s, "SKI") if get_var else None
        prev = json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001
        prev = None
    asof, rows, n_snow, n_wx = fetch(prev)
    print("  ski: %d resorts with snow data, %d with live weather" % (n_snow, n_wx))
    if not n_snow and not n_wx:
        rows = None
    if rows:
        a, b = js(asof, rows)
        s, _ = set_var(s, "SKI_ASOF", json.dumps(asof))
        s, _ = set_var(s, "SKI", b[len("var SKI = "):-1])
    try:
        o = fetch_outlook()
        if len(o) > 1:
            s, _ = set_var(s, "OUTLOOK", json.dumps(o, separators=(",", ":")))
            print("  outlook: %d places" % (len(o) - 1))
    except Exception as e:  # noqa: BLE001
        print("  outlook failed:", e)
    try:
        w = fetch_resort_wx()
        if len(w) > 1:
            s, _ = set_var(s, "RWX", json.dumps(w, ensure_ascii=False, separators=(",", ":")))
            print("  resort weather: %d places" % (len(w) - 1))
    except Exception as e:  # noqa: BLE001
        print("  resort weather failed:", e)
    return s


if __name__ == "__main__":
    asof, rows, n_snow, n_wx = fetch()
    a, b = js(asof, rows)
    print(a)
    print(b)
    try:
        print(outlook_js(fetch_outlook()))
    except Exception as e:  # noqa: BLE001
        print("// outlook failed: %s" % e, file=sys.stderr)
    try:
        print("var RWX = %s;" % json.dumps(fetch_resort_wx(), ensure_ascii=False, separators=(",", ":")))
    except Exception as e:  # noqa: BLE001
        print("// resort weather failed: %s" % e, file=sys.stderr)
    print("// %d resorts with snow data, %d with live weather" % (n_snow, n_wx), file=sys.stderr)
