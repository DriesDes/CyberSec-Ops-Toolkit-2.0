"""Kleine tests voor de HTTP-dashboardbouwer."""

import json
from pathlib import Path

from ops import serve


def test_dashboard_lists_json_reports(tmp_path, monkeypatch):
    report_path = tmp_path / "scan_test.json"
    report_path.write_text(
        json.dumps({
            "tool": "scan",
            "generated_at": "2026-05-08T12:00:00",
            "data": {"total": 1},
        }),
        encoding="utf-8",
    )

    monkeypatch.setattr(serve, "REPORTS_DIR", tmp_path)
    html = serve._build_dashboard()

    assert "scan_test.json" in html
    assert "scan" in html


def test_dashboard_handles_empty_reports_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(serve, "REPORTS_DIR", tmp_path)
    html = serve._build_dashboard()

    assert "Nog geen rapporten gevonden" in html
