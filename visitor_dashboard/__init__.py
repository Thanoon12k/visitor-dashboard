"""visitor-dashboard: a protected page on your own Python site that shows every visit, with charts.

Flask:   from visitor_dashboard.flask import VisitorDashboard; VisitorDashboard(app, password="...")
Django:  settings.MIDDLEWARE += "visitor_dashboard.django.VisitorDashboardMiddleware" (first), VISITOR_DASHBOARD = {"password": "..."}
"""

from .core import Tracker

__version__ = "0.2.0"
__all__ = ["Tracker", "VisitorDashboard"]


def __getattr__(name):
    if name == "VisitorDashboard":  # Flask is imported only when asked for
        from .flask import VisitorDashboard
        return VisitorDashboard
    raise AttributeError(name)
