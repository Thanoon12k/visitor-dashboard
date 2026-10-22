"""Builds the live demo (docs/demo/): the real dashboard page, made-up visits, and api.js answering the dashboard's
API in the browser, so the demo needs no server (GitHub Pages serves it).

    python docs/demo/build.py

Rebuild after changing visitor_dashboard/static/dashboard.html or the dashboard API (core.py). The visits are
generated here with the library's own parser (ua.py) and saved with times relative to now, so the demo never
looks old; api.js mirrors core.py's numbers (Tracker.chosen, stats, row, detail).
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from visitor_dashboard import i18n, ua  # noqa: E402

DAYS = 120
HOST = "janedoe.dev"
# (country code, country, region, city, provider, lat, lon, language, time zone, weight)
PLACES = [
    ("US", "United States", "New York", "New York", "Verizon", 40.71, -74.0, "en-US", "America/New_York", 14),
    ("US", "United States", "California", "San Francisco", "Comcast", 37.77, -122.42, "en-US", "America/Los_Angeles", 10),
    ("GB", "United Kingdom", "England", "London", "BT", 51.51, -0.13, "en-GB", "Europe/London", 9),
    ("DE", "Germany", "Berlin", "Berlin", "Deutsche Telekom", 52.52, 13.4, "de-DE", "Europe/Berlin", 8),
    ("IN", "India", "Karnataka", "Bengaluru", "Reliance Jio", 12.97, 77.59, "en-IN", "Asia/Kolkata", 9),
    ("IN", "India", "Maharashtra", "Mumbai", "Bharti Airtel", 19.08, 72.88, "en-IN", "Asia/Kolkata", 5),
    ("IQ", "Iraq", "Baghdad", "Baghdad", "EarthLink", 33.31, 44.36, "ar-IQ", "Asia/Baghdad", 7),
    ("IQ", "Iraq", "Nineveh", "Mosul", "Asiacell", 36.34, 43.13, "ar-IQ", "Asia/Baghdad", 4),
    ("IQ", "Iraq", "Erbil", "Erbil", "Korek Telecom", 36.19, 44.01, "ar-IQ", "Asia/Baghdad", 3),
    ("EG", "Egypt", "Cairo", "Cairo", "TE Data", 30.04, 31.24, "ar-EG", "Africa/Cairo", 4),
    ("SA", "Saudi Arabia", "Riyadh", "Riyadh", "STC", 24.71, 46.68, "ar-SA", "Asia/Riyadh", 3),
    ("AE", "United Arab Emirates", "Dubai", "Dubai", "Etisalat", 25.2, 55.27, "en-AE", "Asia/Dubai", 3),
    ("BR", "Brazil", "São Paulo", "São Paulo", "Vivo", -23.55, -46.63, "pt-BR", "America/Sao_Paulo", 4),
    ("FR", "France", "Île-de-France", "Paris", "Orange", 48.86, 2.35, "fr-FR", "Europe/Paris", 4),
    ("CA", "Canada", "Ontario", "Toronto", "Rogers", 43.65, -79.38, "en-CA", "America/Toronto", 4),
    ("NL", "Netherlands", "North Holland", "Amsterdam", "KPN", 52.37, 4.9, "nl-NL", "Europe/Amsterdam", 3),
    ("TR", "Turkey", "Istanbul", "Istanbul", "Turk Telekom", 41.01, 28.98, "tr-TR", "Europe/Istanbul", 3),
    ("JP", "Japan", "Tokyo", "Tokyo", "NTT", 35.68, 139.69, "ja-JP", "Asia/Tokyo", 2),
]
# (user agent, screen, weight)
AGENTS = [
    ("Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36", "412×915", 10),
    ("Mozilla/5.0 (Linux; Android 13; SM-A546E Build/TP1A) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/25.0 Chrome/121.0.0.0 Mobile Safari/537.36", "412×915", 5),
    ("Mozilla/5.0 (Linux; Android 12; Redmi Note 11 Build/SKQ1) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/125.0.0.0 Mobile Safari/537.36 [FBAN/EMA;FBLC/en_US;FBAV/460.0.0.0;]", "393×873", 5),
    ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36", "412×915", 4),
    ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1", "390×844", 14),
    ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 330.0.0.0", "390×844", 4),
    ("Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1", "820×1180", 3),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36", "1920×1080", 18),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0", "1536×864", 6),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15", "1440×900", 8),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36", "1728×1117", 6),
    ("Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0", "1920×1080", 5),
]
BOTS = ["Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
        "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)", "TelegramBot (like TwitterBot)"]
# (referrer, utm_source, weight)
ORIGINS = [("", "", 24), ("https://www.google.com/", "", 22), ("https://www.linkedin.com/", "", 11),
           ("https://github.com/janedoe", "", 10), ("https://l.facebook.com/", "", 7), ("https://t.me/pythondevs", "", 6),
           ("https://t.co/x1y2", "", 5), ("", "whatsapp", 4), ("https://www.reddit.com/r/flask/", "", 4),
           ("https://dev.to/janedoe", "", 3), ("https://www.bing.com/", "", 2), ("", "newsletter", 2)]
PAGES = {"/": "Jane Doe · Python developer", "/projects": "Projects", "/projects/shop-app": "Shop app (Flask)",
         "/blog": "Blog", "/blog/flask-tips": "10 Flask tips", "/blog/django-deploy": "Deploying Django cheaply",
         "/about": "About", "/contact": "Contact"}
NEXT = {"/": ["/projects", "/about", "/blog", "/contact"], "/projects": ["/projects/shop-app", "/contact"],
        "/projects/shop-app": ["/contact", "/projects"], "/blog": ["/blog/flask-tips", "/blog/django-deploy"],
        "/blog/flask-tips": ["/blog/django-deploy", "/"], "/blog/django-deploy": ["/contact", "/"],
        "/about": ["/contact", "/projects"], "/contact": ["/"]}
# (page, kind, label, target, chance)
CLICKS = [("/", "link", "View projects", "/projects", .3), ("/", "download", "Download CV", "/cv.pdf", .12),
          ("/", "outbound", "GitHub", "https://github.com/janedoe", .1), ("/", "contact", "Hire me", "mailto:jane@janedoe.dev", .06),
          ("/contact", "contact", "WhatsApp", "https://wa.me/15550100", .25), ("/contact", "click", "Send message", "", .3),
          ("/projects/shop-app", "outbound", "Live demo", "https://shop.janedoe.dev", .3),
          ("/blog/flask-tips", "click", "Copy code", "", .35), ("/blog/django-deploy", "click", "Copy code", "", .3),
          ("/blog/flask-tips", "outbound", "Share on LinkedIn", "https://www.linkedin.com/sharing", .06)]


def pick(rng, items, weight=-1):
    return rng.choices(items, weights=[i[weight] for i in items])[0]


def build(seed: int = 7) -> dict:
    rng = random.Random(seed)
    agents = []
    for agent, screen, _ in AGENTS:
        parsed = ua.parse(agent)
        agents.append({**parsed, "ua": agent, "screen": screen})
    for agent in BOTS:
        agents.append({**ua.parse(agent), "ua": agent, "screen": ""})
    bot_start = len(AGENTS)
    visitors, rows, events = [], [], []
    for day in range(DAYS, -1, -1):
        growth = 0.35 + 0.65 * (DAYS - day) / DAYS
        count = int(rng.gauss(26 * growth, 4)) + (6 if (DAYS - day) % 7 in (1, 2, 3) else 0)
        for _ in range(max(count, 3)):
            if visitors and rng.random() < 0.3:
                visitor = rng.choice(visitors)
                new = False
            else:
                place = pick(rng, PLACES)
                index = rng.choices(range(len(AGENTS)), weights=[a[2] for a in AGENTS])[0]
                visitor = {"id": f"v{len(visitors):05d}", "place": PLACES.index(place), "agent": index,
                           "ip": f"{rng.choice(['203.0.113', '198.51.100', '192.0.2'])}.{rng.randint(1, 254)}",
                           "dark": int(rng.random() < .4), "conn": rng.choice(["4g", "4g", "4g", "3g", ""])}
                visitors.append(visitor)
                new = True
            hour = rng.choices(range(24), weights=[1, 1, 1, 1, 1, 2, 3, 5, 7, 8, 9, 9, 8, 8, 9, 9, 8, 8, 9, 10, 10, 8, 5, 3])[0]
            # seconds before now: the hour sets the time of day; today's visits are all at least 10 minutes old
            start = max(day * 86400 + (23 - hour) * 3600 + rng.randint(0, 3599), 600)
            origin = pick(rng, ORIGINS)
            path = rng.choices(list(PAGES), weights=[30, 8, 5, 5, 9, 7, 4, 3])[0]
            session = f"s{len(rows):06d}"
            for step in range(rng.choices([1, 2, 3, 4], weights=[45, 30, 15, 10])[0]):
                duration = round(min(rng.expovariate(1 / 70), 900))
                rows.append({"visitor": visitor, "new": new and step == 0, "ago": start, "session": session, "path": path,
                             "referrer": origin[0] if step == 0 else f"https://{HOST}/", "utm": origin[1] if step == 0 else "",
                             "duration": duration, "scroll": rng.randint(15, 100) if duration > 5 else rng.randint(0, 30)})
                for page, kind, label, target, chance in CLICKS:
                    if page == path and rng.random() < chance:
                        events.append([len(rows) - 1, rng.randint(2, max(3, duration)), kind, label, target])
                start = max(start - duration - rng.randint(2, 20), 360)
                path = rng.choice(NEXT[path])
        for _ in range(rng.randint(0, 3)):  # crawlers and link previews
            rows.append({"visitor": {"id": f"b{rng.randint(0, 99)}", "place": 0, "agent": bot_start + rng.randrange(len(BOTS)),
                                     "ip": f"192.0.2.{rng.randint(1, 254)}", "dark": 0, "conn": ""},
                         "new": False, "ago": day * 86400 + rng.randint(600, 86399), "session": "bot", "path": rng.choice(list(PAGES)),
                         "referrer": "", "utm": "", "duration": 0, "scroll": 0, "bot": True})
    # a few people on the site right now
    for minutes in (0.5, 1.5, 3):
        visitor = rng.choice(visitors)
        rows.append({"visitor": visitor, "new": False, "ago": int(minutes * 60), "session": f"now{minutes}", "path": "/",
                     "referrer": "https://www.google.com/", "utm": "", "duration": int(minutes * 60) - 5, "scroll": 60})
    order = sorted(range(len(rows)), key=lambda i: rows[i]["ago"])  # newest first
    position = {old: new for new, old in enumerate(order)}
    out = []
    for i in order:
        r = rows[i]
        v = r["visitor"]
        place, agent = PLACES[v["place"]], agents[v["agent"]]
        bot = bool(r.get("bot"))
        out.append([
            len(order) - position[i], -r["ago"], v["id"], r["session"], int(r["new"]), v["ip"], r["path"],
            f"utm_source={r['utm']}" if r["utm"] else "", PAGES[r["path"]], r["referrer"],
            ua.source(r["referrer"], HOST, r["utm"]), v["agent"], int(bot),
            -1 if bot else v["place"], r["duration"], r["scroll"], v["dark"], v["conn"],
        ])
    columns = ["id", "ts", "visitor", "session", "new_visitor", "ip", "path", "query", "title", "referrer", "source",
               "agent", "bot", "place", "duration", "scroll", "dark", "conn"]
    places = [{"country_code": p[0], "country": p[1], "region": p[2], "city": p[3], "isp": p[4], "lat": p[5], "lon": p[6],
               "lang": p[7], "tz": p[8]} for p in PLACES]
    return {"host": HOST, "columns": columns, "rows": out, "places": places, "agents": agents,
            "events": [[len(order) - position[i], offset, kind, label, target] for i, offset, kind, label, target in events],
            "words": i18n.TEXT, "ar_countries": i18n.AR_COUNTRIES, "ar_cities": i18n.AR_CITIES}


def page() -> str:
    """The real dashboard page, with the demo's data and api.js in place of a server."""
    html = (ROOT / "visitor_dashboard" / "static" / "dashboard.html").read_text(encoding="utf-8")
    swaps = [
        ('<html lang="{{LANG}}" dir="{{DIR}}">', '<html lang="en" dir="ltr">'),
        ('<meta name="robots" content="noindex">\n', ""),  # the real dashboard hides from search engines; the demo shouldn't
        ("<title>{{TITLE}}</title>", "<title>visitor-dashboard · live demo</title>\n"
         '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22%3E%3Ctext y=%22.9em%22 font-size=%2290%22%3E📊%3C/text%3E%3C/svg%3E">\n'
         '<meta name="description" content="Live demo of visitor-dashboard: self-hosted web analytics for Flask and Django, '
         'with made-up visits.">\n<script>try { if (localStorage.getItem("vd-demo-lang") === "ar") '
         '{ document.documentElement.lang = "ar"; document.documentElement.dir = "rtl"; } } catch (e) {}</script>'),
        ("<h1>📊 {{TITLE}}</h1>", "<h1>📊 visitor-dashboard</h1>"),
        ('<a class="btn" href="{{PREFIX}}/logout" data-t="logout"></a>',
         '<a class="btn" href="https://github.com/Thanoon12k/visitor-dashboard">GitHub</a>'),
        ("<main>\n", '<main>\n  <p class="demo-note">🧪 Live demo with made-up visits. Add it to your Flask or Django site: '
         '<code>pip install "visitor-dashboard[flask]"</code> · '
         '<a href="https://github.com/Thanoon12k/visitor-dashboard">How it works</a></p>\n'),
        (".lang-switch {", ".demo-note { margin: 0; padding: 10px 14px; border-radius: 10px; background: var(--chip); "
         "color: var(--ink-2); font-size: 13px; }\n.demo-note code { font-size: 12px; }\n.lang-switch {"),
        ('const P = "{{PREFIX}}", LANG = "{{LANG}}";', 'const P = "/visits", LANG = document.documentElement.lang;'),
        ('  document.cookie = `vd_lang=${LANG === "ar" ? "en" : "ar"}; path=${P}; max-age=${5 * 365 * 86400}; samesite=lax`;',
         '  try { localStorage.setItem("vd-demo-lang", LANG === "ar" ? "en" : "ar"); } catch (e) {}'),
        ("\n<script>\nconst P", '\n<script src="data.js"></script>\n<script src="api.js"></script>\n<script>\nconst P'),
    ]
    for old, new in swaps:
        if html.count(old) != 1:
            raise SystemExit(f"dashboard.html changed: can't find {old!r}; update docs/demo/build.py")
        html = html.replace(old, new)
    return html


if __name__ == "__main__":
    data = build()
    (HERE / "data.js").write_text("window.DEMO = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n",
                                  encoding="utf-8")
    (HERE / "index.html").write_text(page(), encoding="utf-8")
    print(f"{len(data['rows'])} visits, {len(data['events'])} clicks -> {HERE}")
