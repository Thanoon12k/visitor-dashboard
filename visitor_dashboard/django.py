"""For a Django site, two lines in settings.py (no urls.py change):

    MIDDLEWARE = ["visitor_dashboard.django.VisitorDashboardMiddleware", *MIDDLEWARE]   # first, so it sees every page
    VISITOR_DASHBOARD = {"password": "your secret code"}                               # the dashboard is at /visits

Every option of Tracker (core.py) can go in VISITOR_DASHBOARD; db_path defaults to visits.db beside manage.py.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpResponse

from .core import Reply, Req, Tracker

log = logging.getLogger("visitor_dashboard")
FORMS = ("application/x-www-form-urlencoded", "multipart/form-data")
_tracker: Tracker | None = None


def tracker() -> Tracker:
    global _tracker
    if _tracker is None:
        options = dict(getattr(settings, "VISITOR_DASHBOARD", {}))
        options.setdefault("db_path", f"{getattr(settings, 'BASE_DIR', '.')}/visits.db")
        _tracker = Tracker(**options)
    return _tracker


def make_req(request) -> Req:
    return Req(method=request.method, path=request.path, query=request.GET.dict(),
               headers={k.lower(): v for k, v in request.headers.items()}, cookies=dict(request.COOKIES),
               remote_addr=request.META.get("REMOTE_ADDR", ""),
               body=request.body if request.method == "POST" else b"", scheme=request.scheme,
               host=request.get_host() if request.META.get("HTTP_HOST") else "",
               form=request.POST.dict() if request.content_type in FORMS else {})


def set_cookies(request, response, cookies: list) -> None:
    for name, value, max_age, path in cookies:
        if max_age:
            response.set_cookie(name, value, max_age=max_age, path=path, httponly=True, samesite="Lax",
                                secure=request.is_secure())
        else:
            response.delete_cookie(name, path=path, samesite="Lax")


class VisitorDashboardMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.tracker = tracker()

    def __call__(self, request):
        if request.path.startswith(self.tracker.prefix):
            reply = self.tracker.handle(make_req(request))
            if reply is not None:
                return self.respond(request, reply)
        response = self.get_response(request)
        try:
            if getattr(response, "streaming", False):
                return response
            req = make_req(request)
            if self.tracker.wants(req, response.status_code, response.get("Content-Type", "")):
                page, cookies = self.tracker.track(req, response.content)
                response.content = page
                if response.has_header("Content-Length"):
                    response["Content-Length"] = str(len(page))
                set_cookies(request, response, cookies)
        except Exception as exc:  # the site always answers, counted or not
            log.warning("visitor_dashboard: track failed: %s", exc)
        return response

    def respond(self, request, reply: Reply) -> HttpResponse:
        response = HttpResponse(reply.body, status=reply.status, content_type=reply.type)
        for name, value in reply.headers.items():
            response[name] = value
        set_cookies(request, response, reply.cookies)
        return response
