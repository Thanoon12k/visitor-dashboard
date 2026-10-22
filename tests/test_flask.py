import json
import re
import time

import pytest
from flask import Flask

from visitor_dashboard.flask import VisitorDashboard

PHONE = ("Mozilla/5.0 (Linux; Android 13; SM-A515F Build/TP1A.220624.014) AppleWebKit/537.36 (KHTML, like Gecko) "
         "Chrome/126.0.0.0 Mobile Safari/537.36 [FBAN/EMA;FBLC/ar_AR;FBAV/400.0.0.0;]")


@pytest.fixture
def setup(tmp_path):
    app = Flask(__name__)

    @app.get("/")
    def home():
        return "<html><body><h1>hello</h1></body></html>"

    @app.get("/api/data")
    def data():
        return {"ok": True}

    dashboard = VisitorDashboard(app, password="sesame", db_path=tmp_path / "v.db", geo_online=False, notify="off")
    return app, app.test_client(), dashboard.tracker


def login(client, me=True):
    form = {"password": "sesame", **({"me": "1"} if me else {})}
    return client.post("/visits/login", data=form)


def test_a_page_is_recorded_and_gets_the_script(setup):
    app, client, tracker = setup
    page = client.get("/?utm_source=telegram", headers={"User-Agent": PHONE, "X-Forwarded-For": "37.236.1.1, 10.0.0.1",
                                                        "Referer": "https://t.me/somechannel"})
    body = page.get_data(as_text=True)
    assert re.search(r'<script src="/visits/track.js" data-v="\d+" data-k="[0-9a-f]{16}"', body)
    assert body.index("track.js") < body.index("</body>")
    assert "vd_id" in page.headers.get("Set-Cookie", "")
    row = tracker.store.rows()[0]
    assert (row["ip"], row["path"], row["source"], row["device"]) == ("37.236.1.1", "/", "telegram", "mobile")
    assert (row["os"], row["os_ver"], row["brand"], row["model"], row["app"]) == ("Android", "13", "Samsung", "SM-A515F", "Facebook")
    assert row["new_visitor"] == 1 and row["geo"] == 0  # placed later (online lookups are off here)


def test_json_and_dashboard_pages_are_not_counted(setup):
    _, client, tracker = setup
    client.get("/api/data")
    client.get("/visits")
    client.get("/visits/track.js")
    assert tracker.store.rows() == []


def test_the_same_browser_is_one_visitor_and_one_session(setup):
    _, client, tracker = setup
    client.get("/", headers={"User-Agent": PHONE})
    client.get("/", headers={"User-Agent": PHONE})
    rows = tracker.store.rows()
    assert len(rows) == 2 and rows[0]["visitor"] == rows[1]["visitor"] and rows[0]["session"] == rows[1]["session"]
    assert [r["new_visitor"] for r in rows] == [0, 1]


def test_the_script_reports_with_its_own_key_only(setup):
    _, client, tracker = setup
    body = client.get("/", headers={"User-Agent": PHONE}).get_data(as_text=True)
    visit, key = re.search(r'data-v="(\d+)" data-k="(\w+)"', body).groups()
    wrong = client.post("/visits/hit", data=json.dumps({"v": visit, "k": "0" * 16, "d": 99}))
    assert wrong.status_code == 403
    report = {"v": visit, "k": key, "d": 42, "s": 80, "screen": "412×915", "tz": "Asia/Baghdad", "dark": 1,
              "e": [{"t": time.time(), "k": "download", "l": "السيرة الذاتية", "h": "/cv.pdf"}]}
    assert client.post("/visits/hit", data=json.dumps(report)).status_code == 204
    assert client.post("/visits/hit", data=json.dumps({"v": visit, "k": key, "model": "SM-S918B", "os_ver": "14.0.0"})).status_code == 204
    row = tracker.store.visit(int(visit))
    assert (row["duration"], row["scroll"], row["screen"], row["clicks"], row["model"], row["brand"]) == (42, 80, "412×915", 1, "SM-S918B", "Samsung")
    assert tracker.store.events(int(visit))[0]["label"] == "السيرة الذاتية"


def test_the_dashboard_needs_the_password(setup):
    _, client, _ = setup
    assert "Password" in client.get("/visits").get_data(as_text=True)
    assert client.get("/visits/api/stats").status_code == 401
    assert client.post("/visits/login", data={"password": "wrong"}).status_code == 401
    assert login(client).status_code == 303
    assert "c-days" in client.get("/visits").get_data(as_text=True)
    assert client.get("/visits/api/stats").status_code == 200


def test_too_many_wrong_passwords_lock_the_door(setup):
    _, client, _ = setup
    for _ in range(5):
        client.post("/visits/login", data={"password": "wrong"})
    assert client.post("/visits/login", data={"password": "sesame"}).status_code == 429


def test_your_own_visits_are_left_out_after_logging_in(setup):
    _, client, tracker = setup
    login(client, me=True)
    client.get("/")
    assert tracker.store.rows() == []


def test_stats_visits_detail_and_csv(setup):
    _, client, tracker = setup
    other = setup[0].test_client()
    other.get("/", headers={"User-Agent": PHONE, "X-Real-IP": "37.236.1.1"})
    setup[0].test_client().get("/", headers={"User-Agent": "Googlebot/2.1 (+http://www.google.com/bot.html)"})
    tracker.store.set_places({"37.236.1.1": {"country_code": "IQ", "country": "Iraq", "city": "Baghdad", "isp": "Earthlink",
                                             "lat": 33.3, "lon": 44.4}})
    login(client, me=False)
    stats = client.get("/visits/api/stats?range=7").get_json()
    assert stats["kpi"]["visits"] == 1 and stats["kpi"]["visitors"] == 1  # the bot is hidden by default
    assert stats["countries"][0]["label"] == "🇮🇶 Iraq" and stats["devices"][0]["label"] == "Mobile"
    assert sum(stats["hours"]) == 1 and stats["points"][0]["city"] == "Baghdad"
    arabic = client.get("/visits/api/stats?ui=ar").get_json()
    assert arabic["countries"][0]["label"] == "🇮🇶 العراق" and arabic["cities"][0] == {"value": "Baghdad", "label": "بغداد", "n": 1}
    assert client.get("/visits/api/stats?bots=1").get_json()["kpi"]["visits"] == 2
    assert client.get("/visits/api/stats?country_code=JO").get_json()["kpi"]["visits"] == 0
    visits = client.get("/visits/api/visits?q=earthlink").get_json()
    assert visits["total"] == 1 and visits["visits"][0]["flag"] == "🇮🇶"
    detail = client.get(f"/visits/api/visit/{visits['visits'][0]['id']}").get_json()
    assert detail["ua"] == PHONE and detail["visitor_visits"] == 1
    csv = client.get("/visits/export.csv").get_data(as_text=True)
    assert csv.startswith("﻿id,time") and "Baghdad" in csv


def test_telegram_hears_of_new_visitors(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr("visitor_dashboard.core.requests.post", lambda url, **kw: sent.append((url, kw["json"])))
    monkeypatch.setattr("visitor_dashboard.core.threading.Thread",
                        lambda target, args, daemon: type("T", (), {"start": lambda self: target(*args)})())
    app = Flask(__name__)
    app.get("/")(lambda: "<body>hi</body>")
    VisitorDashboard(app, password="x", db_path=tmp_path / "v.db", geo_online=False, telegram=("TOKEN", "42"))
    client = app.test_client()
    client.get("/", headers={"User-Agent": PHONE, "Referer": "https://www.google.com/"})
    client.get("/", headers={"User-Agent": PHONE})  # the same visitor again: no second message
    assert len(sent) == 1 and "botTOKEN/sendMessage" in sent[0][0]
    assert sent[0][1]["chat_id"] == "42" and "New visitor" in sent[0][1]["text"] and "Google" in sent[0][1]["text"]


def test_the_dashboard_speaks_english_unless_asked(setup):
    _, client, _ = setup
    login(client)
    page = client.get("/visits").get_data(as_text=True)
    assert '<html lang="en" dir="ltr">' in page and "Site visitors" in page
    client.set_cookie("vd_lang", "ar", path="/visits")
    page = client.get("/visits").get_data(as_text=True)
    assert '<html lang="ar" dir="rtl">' in page and "زوّار الموقع" in page
