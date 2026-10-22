import re

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True, SECRET_KEY="test", ROOT_URLCONF=__name__, ALLOWED_HOSTS=["*"],
        MIDDLEWARE=["visitor_dashboard.django.VisitorDashboardMiddleware", "django.middleware.common.CommonMiddleware",
                    "django.middleware.csrf.CsrfViewMiddleware"],
        VISITOR_DASHBOARD={"password": "sesame", "db_path": ":memory:-unused", "geo_online": False, "notify": "off"},
    )
    django.setup()

from django.http import HttpResponse, JsonResponse  # noqa: E402
from django.test import Client  # noqa: E402
from django.urls import path  # noqa: E402

urlpatterns = [path("", lambda r: HttpResponse("<html><body>salam</body></html>")),
               path("api", lambda r: JsonResponse({"ok": 1}))]


def test_django(tmp_path):
    import visitor_dashboard.django as integration

    settings.VISITOR_DASHBOARD["db_path"] = str(tmp_path / "v.db")
    integration._tracker = None
    client = Client()
    body = client.get("/", HTTP_USER_AGENT="Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) Safari/604.1").content.decode()
    assert re.search(r'data-v="\d+"', body)
    client.get("/api")
    tracker = integration.tracker()
    assert len(tracker.store.rows()) == 1
    assert client.get("/visits/api/stats").status_code == 401
    assert client.post("/visits/login", {"password": "sesame"}).status_code == 303  # no CSRF token needed
    assert client.get("/visits/api/stats").json()["kpi"]["visits"] == 1
    assert "c-days" in client.get("/visits").content.decode()
