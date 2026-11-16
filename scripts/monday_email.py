"""SKIINUT Monday outlook email (Mark, Nov 16, 2026).

Every Monday at about 5:30 a.m. Mountain Time (see .github/workflows/monday-email.yml) this sends each subscriber a SKIINUT-branded
email with the week's outlook for the home resort they picked when they subscribed on skiinut.com.

  * Utah resorts in a composite region (Snowbasin, Powder Mountain, Alta, Snowbird, Brighton, Solitude, Deer Valley, Park City) get the
    composite snow forecast for their region (NWS Salt Lake City + University of Utah ensemble + global models; scripts/composite.py).
  * Every other resort gets its 7-day forecast (Open-Meteo; the same data as the site's resort weather card, var RWX).

Subscribers live in a Brevo contact list. The subscribe form on skiinut.com (a Brevo form) stores the home resort's key (e.g. "sb") in
the contact attribute RESORT. Each Monday this script copies the subscribers of each resort into a list "SKIINUT <key>" (folder
"SKIINUT resorts", made automatically), then creates and sends one Brevo email campaign per resort to that list. Brevo handles
unsubscribes ({{ unsubscribe }} link in the footer).

Environment (GitHub secrets):
  BREVO_API_KEY   starts with xkeysib-  (Brevo > SMTP & API > API keys)
  BREVO_LIST_ID   the number of the signup list (Contacts > Lists)
  BREVO_FROM      the sender address, verified in Brevo (Senders, domains & dedicated IPs)
Without them it does a dry run: it writes one preview HTML file per resort into ./email-preview/ and sends nothing.

Usage:  python3 scripts/monday_email.py index.html [--only sb,alta] [--test you@example.com]
  --test   sends the emails (default: Snowbasin) only to that address, as Brevo transactional emails; nobody else gets anything.
"""
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

MT = ZoneInfo("America/Denver")
SITE = "https://www.skiinut.com/"
ORANGE = "#E2733A"
NAVY = "#0d1b2a"
SNOW = "#2f80ed"

# WMO weather codes -> short words (Open-Meteo)
WMO = {0: "Clear", 1: "Mostly sunny", 2: "Partly cloudy", 3: "Cloudy", 45: "Fog", 48: "Fog", 51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
       56: "Freezing drizzle", 57: "Freezing drizzle", 61: "Rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain",
       71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains", 80: "Showers", 81: "Showers", 82: "Heavy showers",
       85: "Snow showers", 86: "Heavy snow showers", 95: "Thunderstorms", 96: "Thunderstorms", 99: "Thunderstorms"}
SNOWY = {71, 73, 75, 77, 85, 86}


def page_var(src, name):
    m = re.search(r"var %s = (\{.*?\});\n" % name, src, re.S)
    return json.loads(m.group(1)) if m else None


def fresh_composite(here):
    """Run composite.py for this morning's numbers; fall back to the page's copy."""
    try:
        out = subprocess.run([sys.executable, os.path.join(here, "composite.py")], capture_output=True, text=True, timeout=240).stdout
        m = re.search(r"var COMPOSITE = (\{.*\});", out, re.S)
        if m:
            return json.loads(m.group(1))
    except Exception as e:
        print("composite.py failed, using the page's copy:", e)
    return None


def wd(iso):
    return dt.date.fromisoformat(iso).strftime("%a")


def md(iso):
    d = dt.date.fromisoformat(iso)
    return "%d/%d" % (d.month, d.day)


def inch(v):
    if v is None:
        return "—"
    return "0\"" if v < 0.05 else ("%.1f\"" % v if v < 1 else "%d\"" % round(v))


# ---------- email pieces ----------

def shell(title, pre, body):
    """Table-based, inline-styled wrapper that holds up in Gmail, Outlook and Apple Mail."""
    return """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(t)s</title></head>
<body style="margin:0;padding:0;background:#eef2f6;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">%(pre)s</div>
<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="background:#eef2f6;"><tr><td align="center" style="padding:18px 10px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%%;max-width:600px;background:#ffffff;border-radius:14px;overflow:hidden;font-family:Helvetica,Arial,sans-serif;color:#1b2430;">
<tr><td style="background:%(navy)s;padding:22px 26px 18px;">
  <div style="font:italic 900 34px/1 Helvetica,Arial,sans-serif;letter-spacing:.5px;color:#ffffff;">SKI<span style="color:%(or)s;">IN</span>UT</div>
  <div style="font:600 12px/1.4 Helvetica,Arial,sans-serif;letter-spacing:2px;text-transform:uppercase;color:#9fb3c8;margin-top:6px;">Monday snow outlook</div>
</td></tr>
%(body)s
<tr><td style="padding:18px 26px 26px;font:12px/1.6 Helvetica,Arial,sans-serif;color:#6b7785;border-top:1px solid #e6ebf0;">
  You're getting this because you subscribed to the SKIINUT Monday outlook on skiinut.com for your home resort.<br>
  To change your home resort, subscribe again on <a href="https://www.skiinut.com/" style="color:#6b7785;">skiinut.com</a> with the new one.<br>
  <a href="{{ unsubscribe }}" style="color:#6b7785;">Unsubscribe</a>
</td></tr>
</table></td></tr></table></body></html>""" % {"t": html.escape(title), "pre": html.escape(pre), "body": body, "navy": NAVY, "or": ORANGE}


def headline(name, sub, big, small):
    return """<tr><td style="padding:22px 26px 6px;">
  <div style="font:700 24px/1.2 Helvetica,Arial,sans-serif;color:#0d1b2a;">%s</div>
  <div style="font:13px/1.4 Helvetica,Arial,sans-serif;color:#6b7785;margin-top:3px;">%s</div>
</td></tr>
<tr><td style="padding:10px 26px 4px;">
  <table role="presentation" cellpadding="0" cellspacing="0"><tr>%s</tr></table>
  <div style="font:15px/1.55 Helvetica,Arial,sans-serif;color:#1b2430;margin-top:14px;">%s</div>
</td></tr>""" % (html.escape(name), html.escape(sub), big, small)


def chip(value, label, color=SNOW):
    return ("""<td style="padding:0 10px 0 0;"><div style="background:#f2f6fb;border-radius:10px;padding:10px 14px;text-align:center;min-width:110px;">
  <div style="font:800 28px/1 Helvetica,Arial,sans-serif;color:%s;">%s</div>
  <div style="font:600 11px/1.3 Helvetica,Arial,sans-serif;letter-spacing:1px;text-transform:uppercase;color:#6b7785;margin-top:5px;">%s</div>
</div></td>""" % (color, html.escape(value), html.escape(label)))


def day_rows(rows, max_snow):
    """rows: [(day, date, snow_or_None, lo_hi_range_or_None, hi, lo, words)]"""
    out = []
    for dname, dlabel, snow, rng, hi, lo, words in rows:
        w = 0 if not snow or max_snow <= 0 else max(4, int(round(150 * snow / max_snow)))
        bar = ('<div style="height:12px;width:%dpx;background:%s;border-radius:6px;"></div>' % (w, SNOW)) if w else \
              '<div style="height:12px;width:4px;background:#d9e2ec;border-radius:6px;"></div>'
        snowtxt = inch(snow) if snow is not None else ""
        if rng and snow is not None and snow >= 0.5:
            snowtxt += ' <span style="color:#8a96a3;font-weight:400;">(%s–%s)</span>' % (inch(rng[0]).rstrip('"'), inch(rng[1]))
        out.append("""<tr>
  <td style="padding:7px 0;border-bottom:1px solid #eef2f6;font:700 14px Helvetica,Arial,sans-serif;color:#0d1b2a;width:62px;">%s<br><span style="font-weight:400;font-size:12px;color:#8a96a3;">%s</span></td>
  <td style="padding:7px 8px;border-bottom:1px solid #eef2f6;width:160px;">%s</td>
  <td style="padding:7px 0;border-bottom:1px solid #eef2f6;font:700 14px Helvetica,Arial,sans-serif;color:%s;width:96px;">%s</td>
  <td style="padding:7px 0;border-bottom:1px solid #eef2f6;font:14px Helvetica,Arial,sans-serif;color:#1b2430;text-align:right;white-space:nowrap;"><b style="color:%s;">%s</b> / %s<br><span style="font-size:12px;color:#8a96a3;">%s</span></td>
</tr>""" % (dname, dlabel, bar, SNOW, snowtxt, ORANGE, "%d°" % hi if hi is not None else "—",
            "%d°" % lo if lo is not None else "—", html.escape(words or "")))
    return """<tr><td style="padding:14px 26px 4px;">
  <table role="presentation" width="100%%" cellpadding="0" cellspacing="0">
  <tr><td colspan="2" style="font:600 11px Helvetica,Arial,sans-serif;letter-spacing:1px;text-transform:uppercase;color:#8a96a3;padding-bottom:4px;">Day &middot; new snow</td>
      <td></td><td style="font:600 11px Helvetica,Arial,sans-serif;letter-spacing:1px;text-transform:uppercase;color:#8a96a3;text-align:right;padding-bottom:4px;">High / low</td></tr>
  %s</table></td></tr>""" % "".join(out)


def cta(key):
    return """<tr><td style="padding:18px 26px 8px;" align="left">
  <a href="%s" style="display:inline-block;background:%s;color:#ffffff;font:700 15px Helvetica,Arial,sans-serif;text-decoration:none;padding:12px 22px;border-radius:999px;">Live cams, radar &amp; snow stake on SKIINUT &rarr;</a>
</td></tr>""" % (SITE + "?resort=" + key, ORANGE)


def note(text, src):
    t = ""
    if text:
        t += '<div style="font:14px/1.55 Helvetica,Arial,sans-serif;color:#1b2430;"><b>National Weather Service:</b> %s</div>' % html.escape(text)
    if src:
        t += '<div style="font:12px/1.5 Helvetica,Arial,sans-serif;color:#8a96a3;margin-top:8px;">Sources: %s.</div>' % html.escape(src)
    return '<tr><td style="padding:10px 26px 4px;">%s</td></tr>' % t if t else ""


# ---------- per-resort emails ----------

def utah_email(key, name, comp):
    reg = comp["regions"][comp["keys"][key]]
    dates = comp["dates"]
    d = reg["d"]
    tot5, tot10 = (reg.get("tot") or [None, None])[:2]
    rows = []
    for i, day in enumerate(d[:7]):
        best, lo, hi_s, thi, tlo = (day + [None] * 5)[:5]
        rows.append((wd(dates[i]), md(dates[i]), best, (lo, hi_s), thi, tlo,
                     "Snow" if (best or 0) >= 1 else ("Flurries" if (best or 0) >= 0.2 else "")))
    mx = max([r[2] or 0 for r in rows] + [1])
    big = chip(inch(tot5), "Next 5 days") + chip(inch(tot10), "Next 10 days")
    ft = (" · %s ft" % format(reg["ft"], ",")) if reg.get("ft") else ""
    body = headline(name, "%s composite forecast%s" % (reg["name"], ft), big, html.escape(reg.get("sum") or "")) + \
        day_rows(rows, mx) + note(comp.get("nws"), ", ".join(comp.get("src") or [])) + cta(key)
    subj = "SKIINUT · %s: %s of snow this week" % (name, inch(tot5)) if (tot5 or 0) >= 1 else "SKIINUT · %s: your Monday outlook" % name
    pre = (reg.get("sum") or "")[:140]
    return subj, shell(subj, pre, body)


def rwx_email(key, name, r):
    days = r.get("days") or []
    rows = []
    snowy = []
    for dd in days[:7]:
        iso, code, hi, lo, pp = (dd + [None] * 5)[:5]
        words = WMO.get(code, "")
        if pp is not None:
            words += (" · %d%%" % pp) if words else "%d%%" % pp
        rows.append((wd(iso), md(iso), None, None, hi, lo, words))
        if code in SNOWY:
            snowy.append(wd(iso))
    his = [x[4] for x in rows if x[4] is not None]
    if snowy:
        summ = "Snow in the forecast %s. " % ("on " + ", ".join(snowy[:-1]) + (" and " if len(snowy) > 1 else "") + snowy[-1])
    else:
        summ = "No snow in the 7-day forecast. "
    if his:
        summ += "Highs %d° to %d°." % (min(his), max(his))
    big = chip(str(len(snowy)), "Snow days", SNOW) + (chip("%d°" % max(his), "Warmest high", ORANGE) if his else "")
    body = headline(name, (r.get("where") or "") + " · 7-day forecast", big, html.escape(summ)) + \
        day_rows(rows, 0).replace("Day &middot; new snow", "Day") + note(None, "Open-Meteo forecast models") + cta(key)
    subj = "SKIINUT · %s: snow %s this week" % (name, "on " + snowy[0]) if snowy else "SKIINUT · %s: your Monday outlook" % name
    return subj, shell(subj, summ, body)


def build_all(src, here, only=None):
    comp = fresh_composite(here) or page_var(src, "COMPOSITE") or {}
    rwx = page_var(src, "RWX") or {}
    keys = only or [k for k in rwx if k != "hi"]
    out = {}
    for k in keys:
        r = rwx.get(k)
        name = (r or {}).get("name") or k
        if comp.get("keys", {}).get(k) and comp.get("regions"):
            out[k] = utah_email(k, name, comp)
        elif r:
            out[k] = rwx_email(k, name, r)
    return out


# ---------- Brevo ----------

API = "https://api.brevo.com/v3"


class Brevo:
    def __init__(self, key):
        self.key = key

    def call(self, method, path, body=None):
        req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None)
        req.add_header("api-key", self.key)
        req.add_header("accept", "application/json")
        req.add_header("content-type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                t = r.read().decode()
                return json.loads(t) if t.strip() else {}
        except urllib.error.HTTPError as e:
            raise RuntimeError("%s %s -> %s %s" % (method, path, e.code, e.read().decode()[:400]))

    def list_emails(self, list_id):
        """All contacts on a list: {email: attributes}, skipping blocklisted/unsubscribed ones."""
        out, off = {}, 0
        while True:
            r = self.call("GET", "/contacts/lists/%s/contacts?limit=500&offset=%d" % (list_id, off))
            cs = r.get("contacts", [])
            for c in cs:
                if c.get("emailBlacklisted") or int(list_id) in (c.get("listUnsubscribed") or []):
                    continue
                out[c["email"].lower()] = c.get("attributes") or {}
            off += 500
            if not cs or off >= r.get("count", 0):
                return out


def subscribers(bv, list_id):
    """{resort key: [emails]} from the signup list's RESORT attribute."""
    found = {}
    for em, at in bv.list_emails(list_id).items():
        k = str(at.get("RESORT") or "").strip()
        if k:
            found.setdefault(k, []).append(em)
    return found


def resort_list(bv, key, cache={}):
    """The per-resort list "SKIINUT <key>" in the folder "SKIINUT resorts" (made the first time)."""
    if "folder" not in cache:
        fs = bv.call("GET", "/contacts/folders?limit=50").get("folders") or []
        f = next((x for x in fs if x.get("name") == "SKIINUT resorts"), None)
        cache["folder"] = f["id"] if f else bv.call("POST", "/contacts/folders", {"name": "SKIINUT resorts"})["id"]
        ls = bv.call("GET", "/contacts/folders/%s/lists?limit=50" % cache["folder"]).get("lists") or []
        cache["lists"] = {x["name"]: x["id"] for x in ls}
    name = "SKIINUT " + key
    if name not in cache["lists"]:
        cache["lists"][name] = bv.call("POST", "/contacts/lists", {"name": name, "folderId": cache["folder"]})["id"]
    return cache["lists"][name]


def sync_list(bv, lid, emails):
    """Make the resort list hold exactly these emails (people who switch resorts move lists)."""
    have = set(bv.list_emails(lid))
    want = set(emails)
    add, rm = sorted(want - have), sorted(have - want)
    for i in range(0, len(add), 150):
        bv.call("POST", "/contacts/lists/%s/contacts/add" % lid, {"emails": add[i:i + 150]})
    for i in range(0, len(rm), 150):
        bv.call("POST", "/contacts/lists/%s/contacts/remove" % lid, {"emails": rm[i:i + 150]})


def send_campaign(bv, lid, frm, key, subj, body):
    camp = bv.call("POST", "/emailCampaigns", {
        "name": "SKIINUT Monday %s %s" % (dt.datetime.now(MT).strftime("%Y-%m-%d"), key),
        "subject": subj, "sender": {"name": "SKIINUT", "email": frm}, "replyTo": frm,
        "htmlContent": body, "recipients": {"listIds": [lid]}})
    bv.call("POST", "/emailCampaigns/%s/sendNow" % camp["id"])
    print("  sent")


def send_test(bv, frm, to, subj, body):
    body = body.replace("{{ unsubscribe }}", SITE).replace("{{ update_profile }}", SITE)
    bv.call("POST", "/smtp/email", {"sender": {"name": "SKIINUT", "email": frm}, "to": [{"email": to}],
                                    "subject": "[TEST] " + subj, "htmlContent": body})
    print("  test sent to", to)


def main():
    args = sys.argv[1:]
    page = args[0] if args and not args[0].startswith("--") else "index.html"
    only = None
    test = None
    if "--only" in args:
        only = args[args.index("--only") + 1].split(",")
    if "--test" in args:
        test = args[args.index("--test") + 1]
    here = os.path.dirname(os.path.abspath(__file__))
    src = open(page, encoding="utf-8").read()
    key = os.environ.get("BREVO_API_KEY", "").strip()
    list_id = os.environ.get("BREVO_LIST_ID", "").strip()
    frm = os.environ.get("BREVO_FROM", "").strip()

    if not (key and list_id and frm):
        emails = build_all(src, here, only)
        os.makedirs("email-preview", exist_ok=True)
        for k, (subj, body) in emails.items():
            open(os.path.join("email-preview", k + ".html"), "w", encoding="utf-8").write(body)
        print("Dry run (no BREVO_API_KEY / BREVO_LIST_ID / BREVO_FROM): wrote %d previews to email-preview/" % len(emails))
        return
    if not key.startswith("xkeysib-"):
        sys.exit("BREVO_API_KEY should start with xkeysib- (Brevo > SMTP & API > API keys). Check the GitHub secret.")

    bv = Brevo(key)
    if test:
        emails = build_all(src, here, only or ["sb"])
        for k, (subj, body) in emails.items():
            print("%s: %s" % (k, subj))
            send_test(bv, frm, test, subj, body)
        return
    subs = subscribers(bv, list_id)
    print("Subscribers by home resort:", {k: len(v) for k, v in subs.items()})
    want = [k for k in (only or sorted(subs)) if subs.get(k)]
    if not want:
        print("No subscribers yet; nothing to send.")
        return
    emails = build_all(src, here, want)
    for k in want:
        if k not in emails:
            print("No forecast for", k, "- skipped")
            continue
        subj, body = emails[k]
        print("%s (%d): %s" % (k, len(subs[k]), subj))
        lid = resort_list(bv, k)
        sync_list(bv, lid, subs[k])
        send_campaign(bv, lid, frm, k, subj, body)


if __name__ == "__main__":
    main()
