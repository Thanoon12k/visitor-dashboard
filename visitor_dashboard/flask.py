"""For a Flask site:

    from visitor_dashboard.flask import VisitorDashboard
    VisitorDashboard(app, password="your secret code")   # the dashboard is at /visits

or, with an app factory: dashboard = VisitorDashboard(password=...); dashboard.init_app(app).
Every option of Tracker (core.py) can be passed here too.
"""

from __future__ import annotations

import logging

from flask import Flask, Response, request

from .core import Reply, Req, Tracker

log = logging.getLogger("visitor_dashboard")


class VisitorDashboard:
    def __init__(self, app: Flask | None = None, **options):
        self.options, self.tracker = options, None
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        options = dict(self.options)
        options.setdefault("db_path", f"{app.instance_path}/visits.db")
        options.setdefault("password", app.config.get("VISITOR_DASHBOARD_PASSWORD"))
        self.tracker = Tracker(**options)
        app.extensions["visitor_dashboard"] = self
        # first among the before_request hooks, so the dashboard keeps its own password
        app.before_request_funcs.setdefault(None, []).insert(0, self.before)
        app.after_request(self.after)

    def req(self) -> Req:
        return Req(method=request.method, path=request.path, query=request.args.to_dict(),
                   headers={k.lower(): v for k, v in request.headers.items()}, cookies=dict(request.cookies),
                   remote_addr=request.remote_addr or "", body=request.get_data(cache=True) if request.method == "POST" else b"",
                   scheme=request.scheme, host=request.host,
                   form=request.form.to_dict() if request.mimetype in ("application/x-www-form-urlencoded", "multipart/form-data") else {})

    def before(self):
        reply = self.tracker.handle(self.req())
        if reply is None:
            return None
        return self.response(reply)

    def response(self, reply: Reply) -> Response:
        response = Response(reply.body, status=reply.status, content_type=reply.type, headers=reply.headers)
        self.cookies(response, reply.cookies)
        return response

    def cookies(self, response: Response, cookies: list) -> None:
        for name, value, max_age, path in cookies:
            response.set_cookie(name, value, max_age=max_age or None, path=path, httponly=True, samesite="Lax",
                                secure=request.is_secure or request.headers.get("X-Forwarded-Proto") == "https",
                                **({"expires": 0} if not max_age else {}))

    def after(self, response: Response) -> Response:
        try:
            if response.direct_passthrough or response.is_streamed:
                return response
            req = self.req()
            if not self.tracker.wants(req, response.status_code, response.content_type):
                return response
            page, cookies = self.tracker.track(req, response.get_data())
            response.set_data(page)
            self.cookies(response, cookies)
        except Exception as exc:  # the site always answers, counted or not
            log.warning("visitor_dashboard: track failed: %s", exc)
        return response
