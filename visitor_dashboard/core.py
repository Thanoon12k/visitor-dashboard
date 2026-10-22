"""The tracker itself, the same for Flask and Django (flask.py and django.py only translate requests).

Every HTML page the site sends is recorded (time, visitor, page, origin, device, IP) and gets a small script
(static/track.js) added before </body>. The script reports what only the browser knows (screen, model, time
spent, how far the page was read, clicks) to <prefix>/hit, signed with the visit's own random key.
<prefix> (default /visits) is the dashboard, behind its own password; your own visits are left out once you
have logged in on that browser.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import html
import io
import json
import logging
import re
import secrets
import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode

import requests

from . import ua as ua_parser
from .geo import Geo, flag
from .store import Store

log = logging.getLogger("visitor_dashboard")
HERE = Path(__file__).resolve().parent
VISITOR, OWNER, SESSION = "vd_id", "vd_me", "vd_s"
YEAR = 365 * 86400
DEVICE = {"mobile": "موبايل", "desktop": "كمبيوتر", "tablet": "تابلت", "bot": "بوت"}
DEVICE_ICON = {"mobile": "📱", "desktop": "💻", "tablet": "📲", "bot": "🤖"}
RANGES = {"today": 0, "1": 1, "7": 7, "30": 30, "90": 90, "365": 365, "all": None}
FILTERS = ("country_code", "city", "device", "os", "browser", "brand", "source", "path", "app", "isp", "lang", "screen", "visitor")
# what the page's script may report, and how long each may be
REPORTED = {"screen": 20, "viewport": 20, "tz": 50, "lang": 40, "conn": 10, "title": 200, "model": 60, "os_ver": 20}


@dataclass
class Req:
    """A request, as much of it as the tracker needs."""
    method: str
    path: str
    query: dict
    headers: dict  # lower-case names
    cookies: dict
    remote_addr: str = ""
    body: bytes = b""
    scheme: str = "http"
    host: str = ""
    form: dict = field(default_factory=dict)


@dataclass
class Reply:
    status: int = 200
    body: bytes | str = b""
    type: str = "text/html; charset=utf-8"
    headers: dict = field(default_factory=dict)
    cookies: list = field(default_factory=list)  # (name, value, max_age, path)


class Tracker:
    def __init__(self, password: str | None, db_path: str | Path = "visits.db", prefix: str = "/visits",
                 tz: str = "Asia/Baghdad", telegram: tuple | Callable | None = None, notify: str = "new",
                 notify_limit: int = 20, exclude_ips: tuple = (), ignore: tuple = (), geo_dir: str | Path | None = None,
                 geo_online: bool = True, lang: str = "ar", keep_days: int | None = None, title: str = "زوّار الموقع"):
        self.password = (password or "").strip()
        self.secret = hashlib.sha256(f"visitor-dashboard:{self.password}".encode()).digest()
        self.prefix = "/" + prefix.strip("/")
        self.store = Store(db_path)
        self.geo = Geo(geo_dir, online=geo_online, lang=lang)
        self.tz = zone(tz)
        self.telegram, self.notify, self.notify_limit = telegram, notify, notify_limit
        self.exclude_ips, self.ignore = set(exclude_ips), tuple(ignore)
        self.keep_days, self.title = keep_days, title
        self.sent: list[float] = []      # notification times, for the hourly limit
        self.failures: dict[str, list] = defaultdict(list)  # failed logins per IP
        self.resolving = threading.Lock()
        self.last_resolve = self.last_prune = 0.0

    # ---- who ----
    def ip(self, req: Req) -> str:
        for name in ("cf-connecting-ip", "x-real-ip", "x-forwarded-for"):
            value = req.headers.get(name, "")
            if value:
                return value.split(",")[0].strip()[:45]
        return req.remote_addr or ""

    def sign(self, text: str) -> str:
        return hmac.new(self.secret, text.encode(), hashlib.sha256).hexdigest()[:32]

    def is_owner(self, req: Req) -> bool:
        return bool(self.password) and hmac.compare_digest(req.cookies.get(OWNER, ""), self.sign("owner"))

    def logged_in(self, req: Req) -> bool:
        expires, _, sig = req.cookies.get(SESSION, "").partition(".")
        return (bool(self.password) and expires.isdigit() and int(expires) > time.time()
                and hmac.compare_digest(sig, self.sign(f"session{expires}")))

    # ---- recording ----
    def wants(self, req: Req, status: int, content_type: str) -> bool:
        return (req.method == "GET" and status == 200 and "text/html" in (content_type or "")
                and not req.path.startswith(self.prefix) and not req.path.startswith(self.ignore)
                and "prefetch" not in req.headers.get("sec-purpose", req.headers.get("purpose", ""))
                and not self.is_owner(req) and self.ip(req) not in self.exclude_ips)

    def track(self, req: Req, page: bytes) -> tuple[bytes, list]:
        """Record this page view and add the script. -> (page, cookies to set)"""
        now, ip = time.time(), self.ip(req)
        agent = req.headers.get("user-agent", "")[:500]
        info = ua_parser.parse(agent)
        cookies = []
        visitor = re.sub(r"[^a-zA-Z0-9]", "", req.cookies.get(VISITOR, ""))[:32]
        if not visitor:
            # no cookie yet (a first visit, or cookies blocked): the same address and browser count as one visitor
            visitor = "h" + hashlib.sha256(f"{ip}|{agent}".encode()).hexdigest()[:20]
        if not info["bot"]:
            cookies.append((VISITOR, visitor, 2 * YEAR, "/"))
        before = self.store.latest(visitor)
        session = before["session"] if before and now - (before["last"] or before["ts"]) < 1800 else secrets.token_hex(6)
        place = self.store.place(ip) or self.geo.quick(ip)
        referrer = req.headers.get("referer", "")[:500]
        host = req.headers.get("host", req.host)
        visit = {**info, "ts": now, "last": now, "visitor": visitor, "session": session, "new_visitor": int(before is None),
                 "key": secrets.token_hex(8), "ip": ip, "host": host[:100], "path": req.path[:300],
                 "query": urlencode({k: v for k, v in req.query.items() if k.startswith("utm_") or k in ("ref", "fbclid")})[:300],
                 "referrer": referrer, "ua": agent, "bot": int(info["bot"]),
                 "source": ua_parser.source(referrer, host, req.query.get("utm_source") or req.query.get("ref", "")),
                 "lang": req.headers.get("accept-language", "").split(",")[0][:20]}
        if place:
            visit.update({k: place.get(k) for k in ("country_code", "country", "region", "city", "isp", "lat", "lon")}, geo=1)
        visit_id = self.store.add(visit)
        script = (f'<script src="{self.prefix}/track.js" data-v="{visit_id}" data-k="{visit["key"]}" '
                  f'data-u="{self.prefix}/hit" defer></script>').encode()
        lower = page.lower()
        at = lower.rfind(b"</body>")
        page = page[:at] + script + page[at:] if at >= 0 else page + script
        if not info["bot"] and (self.notify == "all" or (self.notify == "new" and before is None)):
            base = f"{req.headers.get('x-forwarded-proto', req.scheme)}://{host}"
            threading.Thread(target=self.tell, args=(visit_id, base), daemon=True).start()
        if self.keep_days and now - self.last_prune > 86400:
            self.last_prune = now
            self.store.prune(self.keep_days)
        return page, cookies

    def hit(self, req: Req) -> Reply:
        """The page's script: {v, k, screen, viewport, dpr, tz, lang, conn, dark, touch, model, os_ver, ipad, d, s, e}."""
        try:
            data = json.loads(req.body[:20000] or b"{}")
            visit_id, key = int(data.get("v")), str(data.get("k", ""))
        except (ValueError, TypeError):
            return Reply(400, b"")
        fields = {k: str(data[k])[:n] for k, n in REPORTED.items() if data.get(k) not in (None, "")}
        for name, kind in (("dpr", float), ("dark", int), ("touch", int)):
            try:
                if data.get(name) is not None:
                    fields[name] = kind(data[name])
            except (TypeError, ValueError):
                pass
        if "d" in data:
            fields["duration"] = min(max(float(data["d"] or 0), 0), 86400)
        if "s" in data:
            fields["scroll"] = min(max(int(data["s"] or 0), 0), 100)
        if data.get("ipad"):
            fields.update(device="tablet", os="iPadOS", brand="Apple", model="iPad")
        if fields.get("os_ver") and not data.get("ipad"):
            visit = self.store.visit(visit_id) or {}
            if visit.get("os") == "Windows":  # the browser knows 11 from 10 (the User-Agent says 10 for both)
                fields["os_ver"] = "11" if fields["os_ver"].split(".")[0].isdigit() and int(fields["os_ver"].split(".")[0]) >= 13 else "10"
            elif visit.get("os") not in ("Android", "macOS"):
                fields.pop("os_ver")
        if fields.get("model"):
            fields["brand"] = next((b for b, p in ua_parser.BRANDS if re.search(p, fields["model"])), "")
        events = [(min(float(e.get("t") or time.time()), time.time()), str(e.get("k", "click"))[:12],
                   str(e.get("l", ""))[:120], str(e.get("h", ""))[:300])
                  for e in (data.get("e") or [])[:50] if isinstance(e, dict)]
        ok = self.store.update(visit_id, key, fields, events)
        return Reply(204 if ok else 403, b"", "text/plain")

    # ---- places ----
    def resolve(self, wait: bool = False) -> None:
        """Place the visits saved without one (online lookups, at most every 20 seconds unless asked to wait)."""
        if not wait and time.time() - self.last_resolve < 20:
            return
        if not self.resolving.acquire(blocking=wait):
            return
        try:
            self.last_resolve = time.time()
            ips = self.store.pending(100)
            if ips:
                self.store.set_places(self.geo.lookup(ips), tried=ips)
        except Exception as exc:  # a lookup service down never breaks the dashboard
            log.warning("visitor_dashboard: place lookup failed: %s", exc)
        finally:
            self.resolving.release()

    # ---- Telegram ----
    def bot(self) -> tuple[str, str] | None:
        value = self.telegram() if callable(self.telegram) else self.telegram
        if isinstance(value, dict):
            value = (value.get("token"), value.get("chat"))
        return (str(value[0]), str(value[1])) if value and value[0] and value[1] else None

    def tell(self, visit_id: int, base: str) -> None:
        try:
            bot = self.bot()
            now = time.time()
            self.sent = [t for t in self.sent if now - t < 3600]
            if not bot or len(self.sent) >= self.notify_limit:
                return
            self.sent.append(now)
            self.resolve(wait=True)
            v = self.store.visit(visit_id)
            if not v:
                return
            place = " · ".join(x for x in (v["country"], v["region"] if v["region"] != v["city"] else "", v["city"]) if x)
            device = " · ".join(x for x in (DEVICE.get(v["device"], v["device"]), f"{v['os']} {v['os_ver']}".strip(),
                                            f"{v['brand']} {v['model']}".strip(), v["browser"], v["app"] and f"داخل {v['app']}") if x)
            text = (f"👀 <b>{'زائر جديد' if v['new_visitor'] else 'زيارة'}</b> على {html.escape(v['host'] or '')}\n"
                    f"{flag(v['country_code'])} {html.escape(place or 'مكان غير معروف')}"
                    f"{' · ' + html.escape(v['isp']) if v['isp'] else ''}\n"
                    f"{DEVICE_ICON.get(v['device'], '')} {html.escape(device)}\n"
                    f"🔗 جاي من: {html.escape(v['source'] or '')}\n📄 {html.escape(v['path'] or '/')}\n"
                    f"🕐 {self.local(v['ts']):%Y-%m-%d %H:%M}\n"
                    f'<a href="{base}{self.prefix}#v={visit_id}">كل التفاصيل</a>')
            requests.post(f"https://api.telegram.org/bot{bot[0]}/sendMessage", timeout=10,
                          json={"chat_id": bot[1], "text": text, "parse_mode": "HTML", "disable_web_page_preview": True})
        except Exception as exc:  # a notification never matters more than the site
            log.warning("visitor_dashboard: telegram failed: %s", exc)

    # ---- the dashboard ----
    def local(self, ts: float) -> datetime:
        return datetime.fromtimestamp(ts, self.tz)

    def handle(self, req: Req) -> Reply | None:
        """Answer the dashboard's own addresses (under prefix); None for every other page."""
        if req.path != self.prefix and not req.path.startswith(self.prefix + "/"):
            return None
        sub = req.path[len(self.prefix):].strip("/")
        if sub == "track.js":
            return Reply(200, (HERE / "static" / "track.js").read_bytes(), "application/javascript; charset=utf-8",
                         {"Cache-Control": "public, max-age=86400"})
        if sub == "hit" and req.method == "POST":
            return self.hit(req)
        if not self.password:
            return Reply(503, page("لوحة الزوار", "<p>اللوحة مقفولة: ما انحط رمز سري (password) بإعدادات الموقع.</p>"))
        if sub == "login" and req.method == "POST":
            return self.login(req)
        if sub == "logout":
            return Reply(303, b"", headers={"Location": self.prefix}, cookies=[(SESSION, "", 0, self.prefix)])
        if not self.logged_in(req):
            if sub.startswith("api/") or sub == "export.csv":
                return Reply(401, b'{"error":"login"}', "application/json")
            return Reply(200, self.login_page(), headers={"Cache-Control": "no-store"})
        headers = {"Cache-Control": "no-store"}
        if sub == "":
            body = (HERE / "static" / "dashboard.html").read_text(encoding="utf-8")
            body = body.replace("{{PREFIX}}", self.prefix).replace("{{TITLE}}", html.escape(self.title))
            return Reply(200, body, headers={**headers, "X-Frame-Options": "DENY"})
        self.resolve()
        if sub == "api/stats":
            return json_reply(self.stats(req.query))
        if sub == "api/visits":
            return json_reply(self.visits(req.query))
        if sub.startswith("api/visit/") and sub[10:].isdigit():
            found = self.detail(int(sub[10:]))
            return json_reply(found) if found else Reply(404, b"{}", "application/json")
        if sub == "export.csv":
            return Reply(200, self.export(req.query), "text/csv; charset=utf-8",
                         {**headers, "Content-Disposition": f'attachment; filename="visits-{datetime.now(self.tz):%Y%m%d}.csv"'})
        return Reply(404, page("مو موجود", "<p>هالصفحة مو موجودة.</p>"))

    def login(self, req: Req) -> Reply:
        ip, now = self.ip(req), time.time()
        self.failures[ip] = [t for t in self.failures[ip] if now - t < 900]
        if len(self.failures[ip]) >= 5:
            return Reply(429, self.login_page("محاولات كثيرة. جرّب بعد ربع ساعة."))
        given = str(req.form.get("password", ""))
        if not hmac.compare_digest(given.encode(), self.password.encode()):
            self.failures[ip].append(now)
            return Reply(401, self.login_page("الرمز غلط."))
        self.failures.pop(ip, None)
        expires = str(int(now + 30 * 86400))
        cookies = [(SESSION, f"{expires}.{self.sign('session' + expires)}", 30 * 86400, self.prefix)]
        if req.form.get("me"):
            cookies.append((OWNER, self.sign("owner"), 5 * YEAR, "/"))
        return Reply(303, b"", headers={"Location": self.prefix}, cookies=cookies)

    def login_page(self, error: str = "") -> str:
        return page(self.title, f"""
<form method="post" action="{self.prefix}/login" class="card">
  <h1>🔒 {html.escape(self.title)}</h1>
  <label for="pw">الرمز السري</label>
  <input id="pw" name="password" type="password" autocomplete="current-password" required autofocus>
  <label class="check"><input type="checkbox" name="me" value="1" checked> لا تحسب زياراتي من هذا الجهاز</label>
  {f'<p class="error" role="alert">{html.escape(error)}</p>' if error else ''}
  <button type="submit">دخول</button>
</form>""")

    # ---- the numbers ----
    def chosen(self, query: dict) -> tuple[list[dict], float, float]:
        """The visits the filters pick. -> (rows, since, days)"""
        span = query.get("range", "7")
        days = RANGES.get(span, 7)
        today = datetime.now(self.tz).replace(hour=0, minute=0, second=0, microsecond=0)
        since = 0.0 if days is None else (today - timedelta(days=max(days - 1, 0))).timestamp()
        rows = self.store.rows(since)
        if query.get("bots") != "1":
            rows = [r for r in rows if not r["bot"]]
        for name in FILTERS:
            if query.get(name):
                rows = [r for r in rows if str(r.get(name) or "") == query[name]]
        if query.get("new") == "1":
            rows = [r for r in rows if r["new_visitor"]]
        needle = (query.get("q") or "").strip().lower()
        if needle:
            rows = [r for r in rows if any(needle in str(r.get(k) or "").lower()
                                           for k in ("ip", "city", "country", "isp", "path", "ua", "source", "model", "referrer"))]
        if not rows and days is None:
            since = time.time()
        elif days is None:
            since = min(r["ts"] for r in rows)
        return rows, since, days or 0

    def stats(self, query: dict) -> dict:
        rows, since, _ = self.chosen(query)
        now = time.time()
        visitors = {r["visitor"] for r in rows}
        sessions = Counter(r["session"] for r in rows)
        durations = [r["duration"] for r in rows if r["duration"]]
        first = datetime.fromtimestamp(since, self.tz).date()
        last = datetime.now(self.tz).date()
        per_day = {first + timedelta(days=i): [0, set()] for i in range((last - first).days + 1)}
        hours = [0] * 24
        for r in rows:
            moment = self.local(r["ts"])
            day = per_day.setdefault(moment.date(), [0, set()])
            day[0] += 1
            day[1].add(r["visitor"])
            hours[moment.hour] += 1

        def top(key, n=10, label=None):
            counts = Counter(str(r.get(key) or "") for r in rows)
            counts.pop("", None)
            return [{"value": k, "label": label(k) if label else k, "n": c} for k, c in counts.most_common(n)]

        names = {r["country_code"]: r["country"] for r in rows if r["country_code"]}
        online = [r for r in self.store.rows(now - 300) if not r["bot"] and now - (r["last"] or r["ts"]) < 300]
        return {
            "kpi": {"visits": len(rows), "visitors": len(visitors),
                    "new": len({r["visitor"] for r in rows if r["new_visitor"]}),
                    "avg_duration": round(sum(durations) / len(durations)) if durations else 0,
                    "bounce": round(100 * sum(1 for n in sessions.values() if n == 1) / len(sessions)) if sessions else 0,
                    "per_visitor": round(len(rows) / len(visitors), 1) if visitors else 0,
                    "online": len({r["visitor"] for r in online})},
            "days": [{"day": f"{d:%Y-%m-%d}", "visits": v[0], "visitors": len(v[1])} for d, v in sorted(per_day.items())],
            "hours": hours,
            "devices": top("device", label=lambda k: DEVICE.get(k, k)),
            "os": top("os"), "browsers": top("browser"), "brands": top("brand"), "apps": top("app"),
            "countries": top("country_code", label=lambda k: f"{flag(k)} {names.get(k, k)}"),
            "cities": top("city"), "isps": top("isp"), "pages": top("path"), "sources": top("source"),
            "languages": top("lang"), "screens": top("screen"),
            "clicks": [{"label": e["label"] or e["kind"], "kind": e["kind"], "n": e["n"]} for e in self.store.top_events(since)],
            "points": [{"lat": r["lat"], "lon": r["lon"], "city": r["city"], "n": n}
                       for (r, n) in _places(rows)][:300],
            "now": f"{datetime.now(self.tz):%Y-%m-%d %H:%M:%S}",
        }

    def row(self, r: dict) -> dict:
        moment = self.local(r["ts"])
        return {"id": r["id"], "time": f"{moment:%Y-%m-%d %H:%M}", "ago": ago(time.time() - r["ts"]),
                "flag": flag(r["country_code"]), "country": r["country"], "country_code": r["country_code"],
                "city": r["city"], "region": r["region"], "isp": r["isp"], "ip": r["ip"],
                "device": r["device"], "device_label": DEVICE.get(r["device"], r["device"]),
                "icon": DEVICE_ICON.get(r["device"], ""), "os": f"{r['os'] or ''} {r['os_ver'] or ''}".strip(),
                "browser": f"{r['browser'] or ''} {r['browser_ver'] or ''}".strip(),
                "model": f"{r['brand'] or ''} {r['model'] or ''}".strip(), "app": r["app"], "source": r["source"],
                "path": r["path"], "title": r["title"], "duration": round(r["duration"] or 0), "scroll": r["scroll"],
                "clicks": r["clicks"], "new": bool(r["new_visitor"]), "bot": bool(r["bot"]), "visitor": r["visitor"],
                "online": time.time() - (r["last"] or r["ts"]) < 300}

    def visits(self, query: dict) -> dict:
        rows, _, _ = self.chosen(query)
        try:
            offset = max(int(query.get("offset", 0)), 0)
        except ValueError:
            offset = 0
        return {"total": len(rows), "visits": [self.row(r) for r in rows[offset:offset + 50]]}

    def detail(self, visit_id: int) -> dict | None:
        r = self.store.visit(visit_id)
        if not r:
            return None
        count, first = self.store.count(r["visitor"])
        out = {**self.row(r), "referrer": r["referrer"], "query": r["query"], "ua": r["ua"], "lang": r["lang"],
               "screen": r["screen"], "viewport": r["viewport"], "dpr": r["dpr"], "tz": r["tz"], "conn": r["conn"],
               "dark": r["dark"], "touch": r["touch"], "lat": r["lat"], "lon": r["lon"], "host": r["host"],
               "session": r["session"], "visitor_visits": count,
               "first_seen": f"{self.local(first):%Y-%m-%d %H:%M}" if first else "",
               "events": [{"time": f"{self.local(e['ts']):%H:%M:%S}", "kind": e["kind"], "label": e["label"],
                           "target": e["target"]} for e in self.store.events(visit_id)],
               "history": [{"id": h["id"], "time": f"{self.local(h['ts']):%Y-%m-%d %H:%M}", "path": h["path"],
                            "source": h["source"], "duration": round(h["duration"] or 0)} for h in self.store.history(r["visitor"])]}
        return out

    def export(self, query: dict) -> str:
        rows, _, _ = self.chosen(query)
        out = io.StringIO()
        out.write("﻿")  # so Excel reads the Arabic
        columns = ["id", "time"] + [c for c in rows[0] if c not in ("id", "ts", "key")] if rows else ["id", "time"]
        writer = csv.writer(out)
        writer.writerow(columns)
        for r in rows:
            writer.writerow([r["id"], f"{self.local(r['ts']):%Y-%m-%d %H:%M:%S}"] + [r[c] for c in columns[2:]])
        return out.getvalue()


def _places(rows: list[dict]):
    seen = Counter((r["lat"], r["lon"]) for r in rows if r["lat"] is not None and r["lon"] is not None)
    first = {}
    for r in rows:
        first.setdefault((r["lat"], r["lon"]), r)
    return [(first[k], n) for k, n in seen.most_common()]


def zone(name: str):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:  # no time zone data on the server: Baghdad is UTC+3 all year
        return timezone(timedelta(hours=3))


def ago(seconds: float) -> str:
    if seconds < 60:
        return "هسه"
    if seconds < 3600:
        return f"قبل {int(seconds // 60)} دقيقة"
    if seconds < 86400:
        return f"قبل {int(seconds // 3600)} ساعة"
    return f"قبل {int(seconds // 86400)} يوم"


def json_reply(value) -> Reply:
    return Reply(200, json.dumps(value, ensure_ascii=False), "application/json; charset=utf-8", {"Cache-Control": "no-store"})


def page(title: str, body: str) -> str:
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>{html.escape(title)}</title><style>
:root{{--bg:#f6f6f4;--card:#fff;--ink:#0b0b0b;--muted:#52514e;--line:#e4e3df;--accent:#2a78d6;--bad:#c62828}}
@media (prefers-color-scheme:dark){{:root{{--bg:#121211;--card:#1a1a19;--ink:#f0efec;--muted:#c3c2b7;--line:#2c2c2a;--accent:#3987e5;--bad:#ef6c6c}}}}
body{{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,"Segoe UI",Tahoma,sans-serif;padding:16px;box-sizing:border-box}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:24px;width:100%;max-width:340px;display:grid;gap:10px}}
h1{{font-size:20px;margin:0 0 6px}} input[type=password]{{font:inherit;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--bg);color:var(--ink)}}
.check{{display:flex;gap:8px;align-items:center;color:var(--muted);font-size:13px}}
button{{font:inherit;font-weight:600;padding:10px;border:0;border-radius:10px;background:var(--accent);color:#fff;cursor:pointer}}
.error{{color:var(--bad);margin:0}}
</style></head><body>{body}</body></html>"""
