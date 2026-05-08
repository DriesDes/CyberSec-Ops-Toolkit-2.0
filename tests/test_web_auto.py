"""Kleine tests voor fallbackgedrag van Selenium-automatisering."""

from ops import web_auto


def test_web_auto_without_selenium_returns_empty(monkeypatch):
    monkeypatch.setattr(web_auto, "SELENIUM_AVAILABLE", False)
    bot = web_auto.WebAutomationBot("https://example.com")

    assert bot.run() == []
