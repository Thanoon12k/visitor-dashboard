"""The live demo (docs/demo/build.py) still fits the dashboard page and the parser."""

import importlib.util
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent / "docs" / "demo" / "build.py"


def load():
    spec = importlib.util.spec_from_file_location("demo_build", BUILD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_demo_page_is_the_dashboard_without_a_server():
    html = load().page()
    assert "{{" not in html and '<script src="api.js"></script>' in html and "Live demo with made-up visits" in html


def test_the_demo_data_is_sane():
    data = load().build()
    rows = [dict(zip(data["columns"], r)) for r in data["rows"]]
    assert len(rows) > 1000 and all(r["ts"] <= 0 for r in rows)  # times are before "now"
    assert [r["id"] for r in rows] == sorted((r["id"] for r in rows), reverse=True)  # newest first
    assert {"direct", "internal", "Google"} <= {r["source"] for r in rows}
    assert any(r["bot"] for r in rows) and data["events"]
