"""Unit tests voor de webscraper met dummy HTML en gemockte requests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from ops.scrape import WebScraper


DUMMY_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Test Security Page</title>
  <meta name="description" content="A page for testing the scraper.">
</head>
<body>
  <h1 class="headline">Welcome to the test page</h1>
  <p>Contact us at: admin@example.com or support@test.org</p>
  <a href="https://example.com">Example</a>
  <a href="https://test.org/about">About</a>
  <a href="/relative-link">Relative</a>
</body>
</html>"""


def make_mock_response(html: str, status: int = 200):
    """Maak een MagicMock die lijkt op een requests.Response."""
    mock_response = MagicMock()
    mock_response.status_code = status
    mock_response.text = html
    mock_response.raise_for_status = MagicMock()
    if status >= 400:
        mock_response.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return mock_response


class TestWebScraper:
    """Tests voor WebScraper met gemockte HTTP-responses."""

    @patch("ops.scrape.requests.get")
    def test_extracts_title(self, mock_get):
        mock_get.return_value = make_mock_response(DUMMY_HTML)
        scraper = WebScraper(url="http://test.local")
        result = scraper.scrape()
        assert result["title"] == "Test Security Page"

    @patch("ops.scrape.requests.get")
    def test_detects_emails(self, mock_get):
        mock_get.return_value = make_mock_response(DUMMY_HTML)
        scraper = WebScraper(url="http://test.local")
        result = scraper.scrape()
        emails = result["emails_found"]
        assert "admin@example.com" in emails
        assert "support@test.org" in emails

    @patch("ops.scrape.requests.get")
    def test_collects_absolute_links(self, mock_get):
        mock_get.return_value = make_mock_response(DUMMY_HTML)
        scraper = WebScraper(url="http://test.local")
        result = scraper.scrape()
        assert "https://example.com" in result["links"]
        assert "https://test.org/about" in result["links"]

    @patch("ops.scrape.requests.get")
    def test_relative_links_excluded(self, mock_get):
        """Relatieve links mogen niet in de linklijst staan."""
        mock_get.return_value = make_mock_response(DUMMY_HTML)
        scraper = WebScraper(url="http://test.local")
        result = scraper.scrape()
        assert "/relative-link" not in result["links"]

    @patch("ops.scrape.requests.get")
    def test_css_selector_extraction(self, mock_get):
        mock_get.return_value = make_mock_response(DUMMY_HTML)
        scraper = WebScraper(url="http://test.local", selector="h1.headline")
        result = scraper.scrape()
        assert result["selector_results"] == ["Welcome to the test page"]

    @patch("ops.scrape.requests.get")
    def test_failed_request_returns_empty(self, mock_get):
        """Een mislukte request moet een lege dict teruggeven."""
        import requests
        mock_get.side_effect = requests.RequestException("Connection refused")
        scraper = WebScraper(url="http://unreachable.local")
        result = scraper.scrape()
        assert result == {}

    @patch("ops.scrape.requests.get")
    def test_no_emails_returns_empty_list(self, mock_get):
        """Een pagina zonder e-mails geeft een lege lijst terug."""
        html = "<html><head><title>No email</title></head><body><p>Nothing here</p></body></html>"
        mock_get.return_value = make_mock_response(html)
        scraper = WebScraper(url="http://test.local")
        result = scraper.scrape()
        assert result["emails_found"] == []
