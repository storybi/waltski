"""US Ikon Pass resorts (2026/27 full Ikon Pass: unlimited + up-to-7-day destinations) for the Skiinut resort picker.

Each entry: key, name, state, access ("U" unlimited / "7" up to 7 days), lat, lon, time zone, OnTheSnow path,
where (town / area line), live-cams page, trail-map page, header/cam frames, optional radar override.
Frames: ("yt", youtubeId, name) = YouTube live stream (newest frame from i.ytimg.com);
        ("img", url, name) = a still picture the cam host publishes.
Resorts with no public still picture get an aerial view (Esri World Imagery) behind the header instead.
"""

OTS = "https://www.onthesnow.com/%s/%s"

R = [
 # key, name, ST, access, lat, lon, tz, ots path, where, cams page, map page, frames, extra
 ("sb", "Snowbasin", "UT", "7", 41.2160, -111.8569, "America/Denver", "utah/snowbasin", "Huntsville, Utah · Ogden Valley",
  "https://www.snowbasin.com/the-mountain/web-cams/", "https://www.snowbasin.com/the-mountain/mountain-maps/", [], {}),
 ("alta", "Alta", "UT", "7", 40.5884, -111.6386, "America/Denver", "utah/alta-ski-area", "Little Cottonwood Canyon, Utah",
  None, None, [], {}),
 ("snowbird", "Snowbird", "UT", "7", 40.5830, -111.6556, "America/Denver", "utah/snowbird", "Little Cottonwood Canyon, Utah",
  "https://www.snowbird.com/the-mountain/webcams/view-all-webcams/", None,
  [("img", "https://img.hdrelay.com/frames/5780754f-8da1-4223-ab8a-6755d84cbc10/default/last.jpg", "Hidden Peak"),
   ("img", "https://img.hdrelay.com/frames/8611e276-7ee5-42c0-b8cd-d9e1890e1cd4/default/last.jpg", "Mid-mountain"),
   ("img", "https://img.hdrelay.com/frames/db2a69c5-66e9-4c48-a713-919eaf191fc1/default/last.jpg", "Peruvian Gulch"),
   ("img", "https://b15.hdrelay.com/camera/544432bd-3910-4888-aa9f-14b6f51a7eb5/snapshot", "Snowbird Center")], {}),
 ("brighton", "Brighton", "UT", "7", 40.5980, -111.5832, "America/Denver", "utah/brighton-resort", "Big Cottonwood Canyon, Utah",
  None, None, [], {}),
 ("solitude", "Solitude", "UT", "U", 40.6199, -111.5919, "America/Denver", "utah/solitude-mountain-resort", "Big Cottonwood Canyon, Utah",
  "https://www.solitudemountain.com/mountain-and-village/webcams", None,
  [("yt", "Lnznapxh2xM", "Sunshine Bowl"), ("yt", "NSiItCGabfo", "Moonbeam lift line"), ("yt", "Yx3QmuKfwjY", "Link lift line")], {}),
 ("dv", "Deer Valley", "UT", "7", 40.6375, -111.4783, "America/Denver", "utah/deer-valley-resort", "Park City, Utah · Wasatch Back",
  "https://www.deervalley.com/explore-the-mountain/webcams", "https://www.deervalley.com/explore-the-mountain/trail-map", [], {}),
 ("abasin", "Arapahoe Basin", "CO", "U", 39.6425, -105.8719, "America/Denver", "colorado/arapahoe-basin-ski-area", "Summit County, Colorado",
  "https://www.arapahoebasin.com/mountain-cams/", "https://www.arapahoebasin.com/trail-maps/",
  [("img", "https://watch.hdrelay.io/api/public/poster/cam_arapahoe_basin_pali_cam_1790623627806", "Pali"),
   ("img", "https://dirigo-resorts-f4e2bde5azc2cne6.z02.azurefd.net/arapahoe/images/medium/webcams/abasincam5.jpg", "Mountain view"),
   ("img", "https://dirigo-resorts-f4e2bde5azc2cne6.z02.azurefd.net/arapahoe/images/medium/webcams/abasincam1001m.jpg", "Base area")], {}),
 ("aspen", "Aspen Snowmass", "CO", "7", 39.2084, -106.9490, "America/Denver", "colorado/aspen-snowmass", "Aspen & Snowmass Village, Colorado",
  "https://www.aspensnowmass.com/our-mountains/mountain-cams", None, [], {}),
 ("copper", "Copper Mountain", "CO", "U", 39.5022, -106.1511, "America/Denver", "colorado/copper-mountain-resort", "Summit County, Colorado",
  "https://www.coppercolorado.com/the-mountain/webcams/", None,
  [("img", "https://watch.hdrelay.io/api/public/poster/cam_copper_mountain___union_1790871057199", "Union Creek"),
   ("img", "https://watch.hdrelay.io/api/public/poster/cam_copper_mountain___excelerator_1791911614707", "Excelerator"),
   ("img", "https://watch.hdrelay.io/api/public/poster/cam_copper_mountain___center_village_1791904709663", "Center Village"),
   ("img", "https://watch.hdrelay.io/api/public/poster/cam_copper_mountain___super_bee_1791911334637", "Super Bee"),
   ("img", "https://img.hdrelay.com/frames/fb469125-f1f3-459f-aeb4-98cb674e395f/default/last.jpg", "Mountain view")], {}),
 ("eldora", "Eldora", "CO", "U", 39.9372, -105.5827, "America/Denver", "colorado/eldora-mountain-resort", "Nederland, Colorado",
  "https://www.eldora.com/the-mountain/current-conditions/webcams/", "https://www.eldora.com/the-mountain/maps/alpine-trail-map/", [], {}),
 ("steamboat", "Steamboat", "CO", "U", 40.4572, -106.8045, "America/Denver", "colorado/steamboat", "Steamboat Springs, Colorado",
  None, None, [], {}),
 ("winterpark", "Winter Park", "CO", "U", 39.8868, -105.7625, "America/Denver", "colorado/winter-park-resort", "Winter Park, Colorado",
  "https://www.winterparkresort.com/the-mountain/mountain-cams", None,
  [("yt", "HfX4H3MSwXs", "Lunch Rock"), ("yt", "vyWAzJAWv4w", "Base cam"), ("yt", "Dt_WhmxV0yE", "Snoasis"),
   ("img", "https://cams.winterparkresort.com/best-western-cam.jpg", "Village")], {}),
 ("bigsky", "Big Sky", "MT", "7", 45.2857, -111.4012, "America/Denver", "montana/big-sky-resort", "Big Sky, Montana",
  "https://www.bigskyresort.com/webcams", None,
  [("yt", "6iW7bdSavUo", "Lone Peak Tram"), ("yt", "dMr-Jt_K3Cc", "Everett's 8800"), ("yt", "TsG0Utw13bs", "Headwaters snow stake")], {}),
 ("jackson", "Jackson Hole", "WY", "7", 43.5875, -110.8279, "America/Denver", "wyoming/jackson-hole", "Teton Village, Wyoming",
  None, None, [], {}),
 ("taos", "Taos Ski Valley", "NM", "7", 36.5960, -105.4545, "America/Denver", "new-mexico/taos-ski-valley", "Taos Ski Valley, New Mexico",
  "https://www.skitaos.com/webcams", None, [], {}),
 ("sv", "Sun Valley", "ID", "7", 43.6710, -114.3640, "America/Boise", "idaho/sun-valley", "Ketchum, Idaho · Wood River Valley",
  "https://www.sunvalley.com/the-mountain/web-cams/", "https://www.sunvalley.com/the-mountain/trail-maps/", [], {}),
 ("schweitzer", "Schweitzer", "ID", "U", 48.3677, -116.6227, "America/Los_Angeles", "idaho/schweitzer", "Sandpoint, Idaho",
  "https://www.schweitzer.com/mountain-info/webcam", "https://www.schweitzer.com/mountain-info/maps",
  [("yt", "7INfYvwClC0", "Basin Express"), ("yt", "7vfVVc9AhcQ", "Lakeview Triple"), ("yt", "6-8KuVdZJWA", "Colburn Triple"),
   ("yt", "Y3LI7eFJ6wo", "Rowdy Grouse"), ("yt", "B6k3gfxXxLc", "Outback")], {}),
 ("mammoth", "Mammoth Mountain", "CA", "U", 37.6510, -119.0270, "America/Los_Angeles", "california/mammoth-mountain-ski-area", "Mammoth Lakes, California",
  None, "https://www.mammothmountain.com/on-the-mountain/winter-trail-map", [], {}),
 ("june", "June Mountain", "CA", "U", 37.7678, -119.0904, "America/Los_Angeles", "california/june-mountain", "June Lake, California",
  "https://www.junemountain.com/mountain-information/live-cams", "https://www.junemountain.com/mountain-information/trail-map",
  [("yt", "-U--7tKsSQU", "June Patrol"), ("yt", "ZEwoBjYmWhM", "Mountain view"), ("yt", "itJI-3uiYkI", "June Chalet")], {}),
 ("palisades", "Palisades Tahoe", "CA", "U", 39.1966, -120.2345, "America/Los_Angeles", "california/palisades-tahoe", "Olympic Valley, California",
  "https://www.palisadestahoe.com/mountain-information/webcams", "https://www.palisadestahoe.com/mountain-information/trail-maps", [], {}),
 ("sierra", "Sierra-at-Tahoe", "CA", "7", 38.8004, -120.0808, "America/Los_Angeles", "california/sierra-at-tahoe", "Twin Bridges, California",
  "https://sierraattahoe.com/live-cams/", "https://sierraattahoe.com/maps-and-stats/",
  [("img", "https://img.hdrelay.com/frames/f5145304-44dc-475f-a654-8a7bacee1e81/sugar/last.jpg", "Mountain view")], {}),
 ("bigbear", "Big Bear Mountain", "CA", "U", 34.2283, -116.8914, "America/Los_Angeles", "california/snow-summit", "Big Bear Lake, California",
  "https://www.bigbearmountainresort.com/webcams", "https://www.bigbearmountainresort.com/mountain-information/trail-maps", [], {}),
 ("snowvalley", "Snow Valley", "CA", "U", 34.2245, -117.0367, "America/Los_Angeles", "california/snow-valley", "Running Springs, California",
  None, None, [], {}),
 ("crystal", "Crystal Mountain", "WA", "U", 46.9327, -121.4877, "America/Los_Angeles", "washington/crystal-mountain-wa", "Mount Rainier area, Washington",
  None, None, [], {}),
 ("snoqualmie", "Summit at Snoqualmie", "WA", "7", 47.4110, -121.4140, "America/Los_Angeles", "washington/the-summit-at-snoqualmie", "Snoqualmie Pass, Washington",
  "https://www.summitatsnoqualmie.com/webcams", "https://www.summitatsnoqualmie.com/trail-maps",
  [("yt", "w4Sno8NIjmU", "Summit Central top"), ("yt", "c_XLrUYV8tk", "Alpental mid-mountain"), ("yt", "H7HwsNLqVC8", "Silver Fir base"),
   ("yt", "vhO8nNqg9iw", "Summit West base"), ("yt", "bWf5rScCIas", "Alpental top")], {}),
 ("bachelor", "Mt. Bachelor", "OR", "7", 43.9792, -121.6886, "America/Los_Angeles", "oregon/mt-bachelor", "Bend, Oregon",
  "https://www.mtbachelor.com/the-mountain/webcams/", None,
  [("yt", "lyN2JG7zowo", "Mid-mountain"), ("yt", "gAftCYziGW4", "Cloudchaser"), ("yt", "pXHMtXbmo7k", "Sunrise")], {}),
 ("alyeska", "Alyeska", "AK", "7", 60.9703, -149.0987, "America/Anchorage", "alaska/alyeska-resort", "Girdwood, Alaska",
  None, None, [], {"ridge": "AHG", "z": 10}),
 ("killington", "Killington-Pico", "VT", "7", 43.6262, -72.7965, "America/New_York", "vermont/killington-resort", "Killington, Vermont",
  "https://killington.com/webcams", "https://killington.com/winter-trail-map",
  [("img", "https://watch.hdrelay.io/api/public/poster/cam_snowshed_adventure_center_1789055086968", "Snowshed")], {}),
 ("stratton", "Stratton", "VT", "U", 43.1027, -72.9048, "America/New_York", "vermont/stratton-mountain", "Stratton, Vermont",
  None, None, [], {}),
 ("sugarbush", "Sugarbush", "VT", "U", 44.1359, -72.8944, "America/New_York", "vermont/sugarbush", "Warren, Vermont",
  "https://www.sugarbush.com/mountain/webcams", None,
  [("yt", "F5m1Ac9ZvKc", "Heaven's Gate"), ("yt", "dR2pY9L3md8", "Allyn's Lodge"), ("img", "https://assets2.webcam.io/w/z7DpwM/latest.jpg", "Mountain view")], {}),
 ("sugarloaf", "Sugarloaf", "ME", "7", 45.0544, -70.3087, "America/New_York", "maine/sugarloaf", "Carrabassett Valley, Maine",
  None, None, [], {}),
 ("sundayriver", "Sunday River", "ME", "7", 44.4734, -70.8567, "America/New_York", "maine/sunday-river", "Newry, Maine",
  None, None, [], {}),
 ("loon", "Loon Mountain", "NH", "7", 44.0451, -71.6366, "America/New_York", "new-hampshire/loon-mountain", "Lincoln, New Hampshire",
  None, None, [], {}),
 ("windham", "Windham Mountain", "NY", "7", 42.2939, -74.2613, "America/New_York", "new-york/windham-mountain", "Windham, New York",
  None, "https://www.windhammountainclub.com/maps/", [], {}),
 ("bluemtn", "Blue Mountain", "PA", "7", 40.8167, -75.5098, "America/New_York", "pennsylvania/blue-mountain-ski-area", "Palmerton, Pennsylvania",
  "https://www.skibluemt.com/mountain-cams/", "https://www.skibluemt.com/winter-sports/skiing-snowboarding/trail-map/", [], {}),
 ("camelback", "Camelback", "PA", "7", 41.0507, -75.3557, "America/New_York", "pennsylvania/camelback-mountain-resort", "Tannersville, Pennsylvania",
  "https://www.camelbackresort.com/resort-information/live-cameras", "https://www.camelbackresort.com/trail-map", [], {}),
 ("snowshoe", "Snowshoe", "WV", "U", 38.4117, -79.9947, "America/New_York", "west-virginia/snowshoe-mountain-resort", "Snowshoe, West Virginia",
  None, None, [], {}),
 ("boyne", "Boyne Mountain", "MI", "7", 45.1640, -84.9330, "America/Detroit", "michigan/boyne-mountain-resort", "Boyne Falls, Michigan",
  None, "https://www.boynemountain.com/mountain-maps", [], {}),
 ("highlands", "The Highlands", "MI", "7", 45.4683, -84.9139, "America/Detroit", "michigan/boyne-highlands", "Harbor Springs, Michigan",
  None, None, [], {}),
 ("snowriver", "Snowriver", "MI", "7", 46.5002, -89.9758, "America/Menominee", "michigan/snowriver-mountain-resort", "Wakefield, Michigan",
  "https://www.snowriver.com/mountain-info/our-webcams", "https://www.snowriver.com/mountain-info/trail-map-mountain-stats", [], {}),
 ("lutsen", "Lutsen Mountains", "MN", "7", 47.6560, -90.7251, "America/Chicago", "minnesota/lutsen-mountains", "Lutsen, Minnesota",
  "https://www.lutsen.com/mountain-info/our-webcam", "https://www.lutsen.com/mountain-info/trail-map-mountain-stats",
  [("img", "https://backend.roundshot.com/cams/64460a72aa4ef9d439c0737b8d266be5/medium", "Panorama")], {}),
 ("granitepeak", "Granite Peak", "WI", "7", 44.9258, -89.6857, "America/Chicago", "wisconsin/granite-peak-ski-area", "Wausau, Wisconsin",
  "https://www.skigranitepeak.com/mountain-info/live-web-cams", "https://www.skigranitepeak.com/mountain-info/trail-map-mountain-stats", [], {}),
]

STATE_NAMES = {"UT": "Utah", "CO": "Colorado", "MT": "Montana", "WY": "Wyoming", "NM": "New Mexico", "ID": "Idaho", "CA": "California",
               "WA": "Washington", "OR": "Oregon", "AK": "Alaska", "VT": "Vermont", "ME": "Maine", "NH": "New Hampshire", "NY": "New York",
               "PA": "Pennsylvania", "WV": "West Virginia", "MI": "Michigan", "MN": "Minnesota", "WI": "Wisconsin"}
GROUPS = [("Utah", ["UT"]), ("Colorado & Rockies", ["CO", "MT", "WY", "NM", "ID"]), ("West Coast & Alaska", ["CA", "WA", "OR", "AK"]),
          ("Northeast", ["VT", "ME", "NH", "NY", "PA", "WV"]), ("Midwest", ["MI", "MN", "WI"])]


def aerial(lat, lon):
    dx, dy = 0.045, 0.018
    return ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?bbox=%.4f,%.4f,%.4f,%.4f"
            "&bboxSR=4326&imageSR=3857&size=1600,640&format=jpg&f=image") % (lon - dx, lat - dy, lon + dx, lat + dy)


def registry():
    out = {}
    for key, name, st, acc, lat, lon, tz, ots, where, cams, mp, frames, extra in R:
        fr = []
        for kind, ref, nm in frames:
            if kind == "yt":
                fr.append({"name": nm, "img": "https://i.ytimg.com/vi/%s/maxresdefault_live.jpg" % ref, "watch": "https://www.youtube.com/live/" + ref, "yt": ref})
            else:
                fr.append({"name": nm, "img": ref, "watch": cams or OTS % (ots, "webcams")})
        e = {"name": name, "st": st, "acc": acc, "lat": lat, "lon": lon, "tz": tz, "ots": ots, "where": where,
             "cams": cams or OTS % (ots, "webcams"), "camsOfficial": bool(cams),
             "map": mp or OTS % (ots, "trailmap"), "mapOfficial": bool(mp), "frames": fr, "aerial": aerial(lat, lon)}
        e.update(extra)
        out[key] = e
    return out


def select_html(selected="sb"):
    reg = registry()
    parts = []
    for label, sts in GROUPS:
        keys = [k for k, *_ in R if reg[k]["st"] in sts]
        opts = "".join('<option value="%s"%s>%s</option>' % (k, " selected" if k == selected else "", reg[k]["name"] + ("" if reg[k]["st"] == "UT" or label == "Utah" else ", " + reg[k]["st"])) for k in keys)
        parts.append('<optgroup label="%s">%s</optgroup>' % (label, opts))
    parts.append('<optgroup label="Beach"><option value="hi">Kailua, Oahu</option></optgroup>')
    return "".join(parts)


if __name__ == "__main__":
    import json
    print(len(R), "resorts")
    print(json.dumps(registry())[:400])
