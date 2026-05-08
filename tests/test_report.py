"""Unit tests voor rapporten samenvoegen en e-mailmeldingen."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from ops.report import EmailAlert, ReportMerger


def write_dummy_report(directory: Path, tool: str, data: dict) -> Path:
    """Schrijf een klein dummyrapport naar een map."""
    path = directory / f"{tool}_test.json"
    content = {
        "tool": tool,
        "generated_at": "2026-05-07T10:00:00",
        "data": data,
    }
    path.write_text(json.dumps(content), encoding="utf-8")
    return path


class TestReportMerger:
    """Tests voor ReportMerger."""

    def test_merges_multiple_reports(self, tmp_path, monkeypatch):
        """Meerdere JSON-rapporten moeten allemaal opgenomen worden."""
        write_dummy_report(tmp_path, "scan", {"findings": [], "total": 0})
        write_dummy_report(tmp_path, "scrape", {"url": "http://test.local", "links_found": 5})

        monkeypatch.setattr("ops.report.REPORTS_DIR", tmp_path)

        merger = ReportMerger()
        result = merger.merge()

        assert result["report_count"] == 2
        tools = [r["tool"] for r in result["reports"]]
        assert "scan" in tools
        assert "scrape" in tools

    def test_empty_reports_dir(self, tmp_path, monkeypatch):
        """Geen JSON-bestanden betekent report_count 0."""
        monkeypatch.setattr("ops.report.REPORTS_DIR", tmp_path)
        merger = ReportMerger()
        result = merger.merge()
        assert result["report_count"] == 0
        assert result["reports"] == []

    def test_summary_extracts_scalars(self, tmp_path, monkeypatch):
        """_summarize neemt scalars over en telt lijsten."""
        write_dummy_report(tmp_path, "net_scan", {"total_hosts": 3, "open_ports": [80, 443]})
        monkeypatch.setattr("ops.report.REPORTS_DIR", tmp_path)

        merger = ReportMerger()
        result = merger.merge()
        summary = result["reports"][0]["summary"]
        assert summary.get("total_hosts") == 3
        assert summary.get("open_ports_count") == 2


class TestEmailAlert:
    """Tests voor EmailAlert."""

    @pytest.fixture
    def sample_merged(self):
        return {
            "merged_at": "2026-05-07T10:00:00",
            "report_count": 2,
            "reports": [
                {"tool": "scan", "file": "scan_test.json", "generated_at": "2026-05-07T09:00:00", "summary": {"total": 1}},
                {"tool": "scrape", "file": "scrape_test.json", "generated_at": "2026-05-07T09:30:00", "summary": {"links_found": 10}},
            ],
        }

    def test_email_headers(self, sample_merged):
        """E-mail moet From, To en Subject bevatten."""
        alert = EmailAlert(sender="toolkit@test.local", recipient="admin@test.local")
        msg = alert.build_message(sample_merged)
        assert msg["From"] == "toolkit@test.local"
        assert msg["To"] == "admin@test.local"
        assert "CyberSec Ops" in msg["Subject"]

    def test_email_has_text_body(self, sample_merged):
        """De e-mail moet een plain-text body bevatten."""
        alert = EmailAlert(sender="a@a.com", recipient="b@b.com")
        msg = alert.build_message(sample_merged)
        text_parts = [p for p in msg.walk() if p.get_content_type() == "text/plain"]
        assert len(text_parts) == 1
        body = text_parts[0].get_payload(decode=True).decode("utf-8")
        assert "scan" in body
        assert "scrape" in body

    def test_email_has_json_attachment(self, sample_merged):
        """De e-mail moet een JSON-attachment hebben."""
        alert = EmailAlert(sender="a@a.com", recipient="b@b.com")
        msg = alert.build_message(sample_merged)
        attachments = [
            p for p in msg.walk()
            if p.get_content_disposition() == "attachment"
        ]
        assert len(attachments) == 1
        assert attachments[0].get_filename().endswith(".json")

    def test_smtp_connection_failure_handled(self, sample_merged):
        """Een SMTP-verbindingsfout mag geen exception laten ontsnappen."""
        alert = EmailAlert(
            sender="a@a.com",
            recipient="b@b.com",
            smtp_host="127.0.0.1",
            smtp_port=9,
        )
        msg = alert.build_message(sample_merged)
        alert.send_raw_smtp(msg)
