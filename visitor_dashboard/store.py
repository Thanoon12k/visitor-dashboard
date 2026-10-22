"""The visits, kept in one SQLite file: nothing to install or run beside the site.

visits: one row per page opened (time, visitor, device, place, origin...), filled in later by the page's own
        script (screen, time spent, how far down it was read).
events: the clicks inside a visit (buttons, links, downloads).
places: each IP's place, looked up once.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

VISIT = ("ts", "last", "visitor", "session", "new_visitor", "key", "ip", "host", "path", "query", "title", "referrer",
         "source", "ua", "device", "os", "os_ver", "browser", "browser_ver", "brand", "model", "app", "bot", "lang",
         "country_code", "country", "region", "city", "isp", "lat", "lon", "geo", "screen", "viewport", "dpr", "tz",
         "conn", "dark", "touch", "duration", "scroll", "clicks")
SCHEMA = """
create table if not exists visits (
  id integer primary key autoincrement, ts real not null, last real, visitor text, session text,
  new_visitor integer default 0, key text, ip text, host text, path text, query text, title text, referrer text,
  source text, ua text, device text, os text, os_ver text, browser text, browser_ver text, brand text, model text,
  app text, bot integer default 0, lang text, country_code text default '', country text default '',
  region text default '', city text default '', isp text default '', lat real, lon real, geo integer default 0,
  screen text, viewport text, dpr real, tz text, conn text, dark integer, touch integer,
  duration real default 0, scroll integer default 0, clicks integer default 0);
create index if not exists visits_ts on visits(ts);
create index if not exists visits_visitor on visits(visitor, ts);
create index if not exists visits_geo on visits(geo, ip);
create table if not exists events (
  id integer primary key autoincrement, visit_id integer not null, ts real not null, kind text, label text, target text);
create index if not exists events_visit on events(visit_id);
create table if not exists places (ip text primary key, place text not null, ts real not null);
"""


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        with self.db() as db:
            db.executescript(SCHEMA)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def add(self, visit: dict) -> int:
        keys = [k for k in VISIT if k in visit]
        with self.lock, self.db() as db:
            cursor = db.execute(f"insert into visits ({','.join(keys)}) values ({','.join('?' * len(keys))})",
                                [visit[k] for k in keys])
            return cursor.lastrowid

    def latest(self, visitor: str) -> dict | None:
        with self.db() as db:
            row = db.execute("select id, ts, last, session from visits where visitor=? order by ts desc limit 1",
                             (visitor,)).fetchone()
        return dict(row) if row else None

    def update(self, visit_id: int, key: str, fields: dict, events: list[tuple]) -> bool:
        """What the page's script reports, accepted only with the visit's own key."""
        with self.lock, self.db() as db:
            row = db.execute("select key, clicks from visits where id=?", (visit_id,)).fetchone()
            if not row or not key or row["key"] != key:
                return False
            events = events[:max(0, 300 - (row["clicks"] or 0))]
            fields = {**fields, "last": time.time(), "clicks": (row["clicks"] or 0) + len(events)}
            db.execute(f"update visits set {','.join(f'{k}=?' for k in fields)} where id=?", [*fields.values(), visit_id])
            db.executemany("insert into events (visit_id, ts, kind, label, target) values (?,?,?,?,?)",
                           [(visit_id, *e) for e in events])
        return True

    # ---- places ----
    def place(self, ip: str) -> dict | None:
        with self.db() as db:
            row = db.execute("select place from places where ip=?", (ip,)).fetchone()
        return json.loads(row["place"]) if row else None

    def pending(self, limit: int = 100) -> list[str]:
        with self.db() as db:
            return [r["ip"] for r in db.execute(
                "select distinct ip from visits where geo=0 and ip is not null order by ts desc limit ?", (limit,))]

    def set_places(self, places: dict[str, dict], tried: list[str] = ()) -> None:
        """Save each IP's place, and fill it into its visits; addresses tried and not found stop being retried."""
        with self.lock, self.db() as db:
            for ip, place in places.items():
                db.execute("insert or replace into places (ip, place, ts) values (?,?,?)",
                           (ip, json.dumps(place, ensure_ascii=False), time.time()))
                db.execute("update visits set country_code=?, country=?, region=?, city=?, isp=?, lat=?, lon=?, geo=1 "
                           "where ip=? and geo=0", (place.get("country_code") or "", place.get("country") or "",
                                                    place.get("region") or "", place.get("city") or "",
                                                    place.get("isp") or "", place.get("lat"), place.get("lon"), ip))
            missing = [ip for ip in tried if ip not in places]
            db.executemany("update visits set geo=2 where ip=? and geo=0", [(ip,) for ip in missing])

    # ---- reading ----
    def rows(self, since: float = 0, until: float | None = None) -> list[dict]:
        with self.db() as db:
            return [dict(r) for r in db.execute(
                "select * from visits where ts>=? and ts<? order by ts desc", (since, until or time.time() + 60))]

    def visit(self, visit_id: int) -> dict | None:
        with self.db() as db:
            row = db.execute("select * from visits where id=?", (visit_id,)).fetchone()
        return dict(row) if row else None

    def events(self, visit_id: int) -> list[dict]:
        with self.db() as db:
            return [dict(r) for r in db.execute("select ts, kind, label, target from events where visit_id=? order by ts",
                                                (visit_id,))]

    def history(self, visitor: str, limit: int = 50) -> list[dict]:
        with self.db() as db:
            return [dict(r) for r in db.execute(
                "select id, ts, path, title, source, duration, clicks from visits where visitor=? order by ts desc limit ?",
                (visitor, limit))]

    def count(self, visitor: str) -> tuple[int, float]:
        with self.db() as db:
            row = db.execute("select count(*) n, min(ts) first from visits where visitor=?", (visitor,)).fetchone()
        return row["n"], row["first"]

    def top_events(self, since: float) -> list[dict]:
        with self.db() as db:
            return [dict(r) for r in db.execute(
                "select e.kind, e.label, count(*) n from events e join visits v on v.id=e.visit_id "
                "where e.ts>=? and v.bot=0 group by e.kind, e.label order by n desc limit 15", (since,))]

    def prune(self, keep_days: int) -> int:
        cutoff = time.time() - keep_days * 86400
        with self.lock, self.db() as db:
            db.execute("delete from events where visit_id in (select id from visits where ts<?)", (cutoff,))
            return db.execute("delete from visits where ts<?", (cutoff,)).rowcount
