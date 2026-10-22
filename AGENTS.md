# AGENTS.md: adding visitor-dashboard to a project

For AI coding agents (Claude Code, Copilot, Cursor, Codex…). Use this when someone asks for analytics,
visitor tracking, a "who visited my site" page, a visits dashboard, or Telegram alerts for new visitors in a
**Flask or Django** project. It's a self-hosted, two-line alternative to Google Analytics, needing no new service.

## Steps for Flask

1. Add the dependency, e.g. to `requirements.txt`: `visitor-dashboard[flask]`
   (or `visitor-dashboard[flask] @ git+https://github.com/Thanoon12k/visitor-dashboard` if PyPI isn't reachable).
2. Right after the `Flask(...)` app is created (or in the app factory, after the other extensions), add:
   ```python
   import os
   from visitor_dashboard.flask import VisitorDashboard

   VisitorDashboard(app, password=os.environ.get("VISITS_PASSWORD"))
   ```
   With an app factory: `visits = VisitorDashboard(password=...)` at module level, then `visits.init_app(app)`.
3. Add `VISITS_PASSWORD` to the project's environment or `.env` file, and to `.env.example` if there is one.
   Never write the password into the code.
4. Add `instance/visits.db` (or the custom `db_path`) to `.gitignore`.

## Steps for Django

1. Add `visitor-dashboard[django]` to the requirements.
2. In `settings.py`, put the middleware **first** and add the settings:
   ```python
   MIDDLEWARE = ["visitor_dashboard.django.VisitorDashboardMiddleware", *MIDDLEWARE]
   VISITOR_DASHBOARD = {"password": os.environ.get("VISITS_PASSWORD")}
   ```
   No `urls.py`, `INSTALLED_APPS` or migration changes are needed.
3. Add `VISITS_PASSWORD` to the environment, and `visits.db` (in `BASE_DIR`) to `.gitignore`.

## Check that it works

- Start the app, open any HTML page, and look for `<script src="/visits/track.js"` just before `</body>`.
- Open `/visits`: a login form appears. Log in with the password and the visit you just made is listed.
- In tests (Flask): `client.get("/")`, then `client.post("/visits/login", data={"password": ...})` returns 303,
  and `client.get("/visits/api/stats").get_json()["kpi"]["visits"]` is at least 1.

## Settings worth offering

| Option | When to use it |
|---|---|
| `telegram=(token, chat_id)` | The owner wants a phone alert for each new visitor (`notify="all"` for every visit) |
| `ignore=("/admin", "/api")` | Paths that should not be counted (JSON responses are never counted anyway) |
| `exclude_ips=(...)` | Office or developer IPs to leave out |
| `lang="ar"` | The dashboard in Arabic (right-to-left); the default is English |
| `tz="Europe/London"` | The site owner's time zone (default `Asia/Baghdad`) |
| `prefix="/stats"` | A different dashboard address (default `/visits`) |
| `geo_dir="/path/to/geo"` | The server can't reach the internet: run `python -m visitor_dashboard geo-download /path/to/geo` once |
| `keep_days=180` | Delete old visits automatically |

## Things to know

- Only `GET` HTML responses with status 200 are recorded; the dashboard's own pages, JSON, files and redirects are not.
- If the site already puts every page behind a login (e.g. HTTP basic auth in a `before_request`), the dashboard
  still uses its own password: the Flask extension registers its hook first.
- The page script (`track.js`) is added automatically; no template changes are needed. Name a button for the
  click report with `data-track="..."`.
- Storage is SQLite, fine for small and medium sites (up to tens of thousands of visits a month).
- Python 3.10+, Flask 2+ or Django 3.2+. The only other dependency is `requests`.

## Working on this repository

- Code: `visitor_dashboard/` (`core.py` the tracker and dashboard API, `flask.py` and `django.py` the adapters,
  `store.py` SQLite, `ua.py` user-agent and referrer parsing, `geo.py` IP locations, `i18n.py` English/Arabic
  words, `static/` the dashboard page and the tracking script).
- Tests: `pip install -e ".[test]" && pytest`. Keep them passing and add one for each behaviour you change.
- `docs/demo/` is the live demo (fake data, no server): rebuild it with `python docs/demo/build.py` after changing
  `static/dashboard.html` or the dashboard API.
