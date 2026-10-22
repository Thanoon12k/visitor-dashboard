# visitor-dashboard

[![PyPI](https://img.shields.io/pypi/v/visitor-dashboard)](https://pypi.org/project/visitor-dashboard/)
[![Python](https://img.shields.io/pypi/pyversions/visitor-dashboard)](https://pypi.org/project/visitor-dashboard/)
[![Tests](https://github.com/Thanoon12k/visitor-dashboard/actions/workflows/tests.yml/badge.svg)](https://github.com/Thanoon12k/visitor-dashboard/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**Self-hosted web analytics for Flask and Django, in two lines of code.**
See every visit to your Python website, with its device, location, referrer, time and clicks, on a password-protected
page inside your own app. No third-party service, no extra server, no tracking company. Get a Telegram message the moment a
new visitor arrives.

```python
from visitor_dashboard.flask import VisitorDashboard
VisitorDashboard(app, password="your secret code")   # → https://your-site/visits
```

**[▶ Try the live demo](https://thanoon12k.github.io/visitor-dashboard/demo/)** (made-up visits, nothing to install)

![The visitor-dashboard page: visits per day, devices, countries, sources and every visit](https://raw.githubusercontent.com/Thanoon12k/visitor-dashboard/main/docs/screenshot.png)

## The goal

Every small website deserves to know who visits it, without sending its visitors to an ad company, paying a
monthly fee, or running a second server. visitor-dashboard aims to be **the easiest analytics for small Python
sites**: portfolios, freelancer and small-business sites, side projects, student projects and internal tools.
You install it, add two lines, and you're done.

## Why visitor-dashboard

- **Two lines, nothing else to run.** It lives inside your app and saves to one SQLite file. No Docker, no
  database server, no account, no script tag to paste into templates.
- **Counts every visit, even with ad blockers.** Page views are recorded on your server as the page is sent.
  Ad blockers that hide Google Analytics can't hide these.
- **Every visit, in detail.** Not only totals: open any single visit to see the device and phone model, OS and
  browser, country, city and internet provider, where the visitor came from, how long they stayed, how far they
  read, what they clicked, and their earlier visits.
- **Instant Telegram alerts.** A message on your phone for each new visitor (or every visit), with where they're
  from and what they opened.
- **Your data stays yours.** Everything is in a file on your own server. Export it to CSV at any time.
- **Runs on cheap hosting.** Works on PythonAnywhere's free plan and small servers, including servers that can't
  reach the internet (locations then come from a downloadable database file).
- **Free and open source (MIT).** No visitor limits, no paid tier.
- **English and Arabic.** English by default, and a full right-to-left Arabic dashboard one click away.

### Compared with the usual options

| | visitor-dashboard | A hosted service (e.g. Google Analytics) | A self-hosted platform (e.g. Plausible, Umami, Matomo) |
|---|---|---|---|
| Setup | `pip install` + 2 lines | Account + a script tag in every page | A separate server, a database, and a script tag |
| Extra infrastructure | None (SQLite in your app) | None, but the data lives with the provider | An app server + a database to run and update |
| Cost | Free | Free (paid with your visitors' data) or paid plans | Free software, but you pay for hosting |
| Where the data lives | Your server, one file | The provider's servers | Your server |
| Visits hidden by ad blockers | No, counted on the server | Often | Often (when counted by a script) |
| Telegram alert for new visitors | Built in | No | Not built in |
| Best for | Small and medium Python sites | Large sites, marketing teams | Many sites, high traffic |

## What it records about each visit

| | Details |
|---|---|
| 🕐 **When** | Date and time in your time zone, time spent on the page, and how far down the page was read (%) |
| 📱 **Device** | Phone, computer or tablet; maker and model (Samsung SM-A515F, iPhone…); OS and version; browser; screen size; language; connection type (4g…); dark mode |
| 🌍 **Where** | Country, region and city; internet provider; approximate coordinates on a map |
| 🔗 **Origin** | Google, Facebook, Telegram, WhatsApp, LinkedIn, X, direct, or any other site. Reads `utm_source` and `?ref=` too |
| 📲 **In-app** | Whether the link was opened inside an app (Facebook, Instagram, TikTok, Telegram…) |
| 👆 **Clicks** | Every button and link clicked, downloads (PDF…), and contact links (WhatsApp, Telegram, email) |
| 👤 **Visitor** | New or returning, number of visits, first seen, and all their earlier visits |
| 🤖 **Bots** | Googlebot, link previews (WhatsApp, Telegram, Facebook) and scripts are kept apart from real visitors |

## The dashboard

- Headline numbers: visits, visitors, new visitors, pages per visitor, average time on page, bounce rate, and **who is online now**
- Charts: visits and visitors per day, visits by hour, device type, countries, cities, internet providers, pages,
  origins, operating systems, browsers, phone makers, in-app browsers, top clicks, languages, screen sizes, and a map
- **Click to filter**: click any country, city, origin or device and the whole dashboard filters to it; filters combine
- Time ranges (today, 7 days, 30 days, 3 months, a year, all) and search by IP, city, page or device
- A list of every visit; click one to see all its details, its clicks, and the same person's other visits
- Refreshes itself every 20 seconds; CSV export; works on phones and in dark mode

![One visit in detail](https://raw.githubusercontent.com/Thanoon12k/visitor-dashboard/main/docs/visit.png)

## Install

```bash
pip install "visitor-dashboard[flask]"     # for a Flask site
pip install "visitor-dashboard[django]"    # for a Django site
```

Or straight from GitHub:
`pip install "visitor-dashboard[flask] @ git+https://github.com/Thanoon12k/visitor-dashboard"`

### Flask

```python
import os
from visitor_dashboard.flask import VisitorDashboard

VisitorDashboard(app, password=os.environ["VISITS_PASSWORD"])
```

With an app factory: `dashboard = VisitorDashboard(password=...)` and then `dashboard.init_app(app)`.

### Django (`settings.py`)

```python
MIDDLEWARE = ["visitor_dashboard.django.VisitorDashboardMiddleware", *MIDDLEWARE]  # first in the list
VISITOR_DASHBOARD = {"password": os.environ["VISITS_PASSWORD"]}
```

No `urls.py` change is needed. Open `https://your-site/visits` and enter the password. Every HTML page your site
sends is counted automatically; your templates don't change.

## Options (all optional except the password)

| Option | Default | What it does |
|---|---|---|
| `password` | | The dashboard's password. Without it the dashboard stays locked (recording still works) |
| `prefix` | `/visits` | The dashboard's address |
| `db_path` | `instance/visits.db` (Flask), `BASE_DIR/visits.db` (Django) | Where visits are saved |
| `tz` | `Asia/Baghdad` | Time zone for display |
| `lang` | `"en"` | The dashboard's language: `"en"` or `"ar"` (each viewer can switch with the 🌐 button) |
| `title` | `Site visitors` | The dashboard's title |
| `telegram` | | `(token, chat_id)`, or a function returning them, to get a message from your bot |
| `notify` | `"new"` | `"new"`: a message for each new visitor, `"all"`: for every visit, `"off"`: none |
| `notify_limit` | `20` | Most messages per hour |
| `exclude_ips` | `()` | IP addresses that are never counted |
| `ignore` | `()` | Path prefixes that are never counted, e.g. `("/admin", "/api")` |
| `geo_dir` | | Folder with the location database (see below) |
| `geo_online` | `True` | Look places up online when there is no database |
| `keep_days` | | Delete visits older than this many days |

### Leave out your own visits

When you log in, keep "Don't count my visits from this device" ticked, and visits from that browser are no
longer counted. Do it once on each of your devices.

### Telegram alerts

```python
VisitorDashboard(app, password="...", telegram=(os.environ["BOT_TOKEN"], os.environ["CHAT_ID"]))
```

For each new visitor (bots excluded) you get the country, city and provider, the device and model, where they
came from, the page, and a link to the visit's details.

### Click tracking

Buttons and links are tracked automatically by their visible text. To name one yourself:

```html
<button data-track="Subscribe button">Subscribe</button>
```

## Locations: online or from a file

By default places come from [ip-api.com](https://ip-api.com) (free), falling back to [ipwho.is](https://ipwho.is).
Each IP is looked up only once, and only after the visit is saved, so visitors never wait.

If your server can't reach those services, download the free database once:

```bash
pip install "visitor-dashboard[geo]"
python -m visitor_dashboard geo-download ~/geo            # cities + providers (~140 MB)
python -m visitor_dashboard geo-download ~/geo --country  # countries + providers only (~17 MB)
```

Then pass `geo_dir="~/geo"`. The files come from [DB-IP](https://db-ip.com) (CC BY 4.0) and are updated monthly,
so download them again every few months.

> A location from an IP address is approximate (city level) and not always right, especially on mobile networks
> or behind a VPN.

## Good to know

- **Built for small and medium sites.** Visits go to SQLite and the numbers are worked out in Python, which is
  comfortable up to tens of thousands of visits a month. For a very busy site, use a dedicated analytics platform.
- **HTML pages are counted, not API calls.** JSON responses, files and the dashboard itself are left out.
- **Privacy.** It records IP addresses and sets one cookie (`vd_id`) to recognise returning visitors. If your
  site serves people in Europe or anywhere with privacy laws, publish a privacy policy that says you log visits.

## Security

- The password is compared in constant time, and 5 wrong tries in 15 minutes lock out that IP.
- The login session is a signed cookie (30 days), ended by the "Log out" button.
- Reports from the browser are signed with a random key per visit, so nobody can alter someone else's visit.

## For AI coding agents

Asked to add analytics, visitor tracking or a visits page to a Flask or Django project? Follow
[AGENTS.md](AGENTS.md): it has the exact steps, the settings, and how to check the result. A short summary for
tools that read [llms.txt](llms.txt) is there too.

## Contributing

Issues and pull requests are welcome. Run the tests with:

```bash
pip install -e ".[test]"
pytest
```

License: MIT
