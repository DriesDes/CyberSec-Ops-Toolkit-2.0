"""
scrape.py - Webscraper.
Haalt een webpagina op, parsed HTML, zoekt e-mailadressen en schrijft een JSON-rapport.

Gebruikte modules: requests, bs4, re, json, datetime
Nieuwe module: rich voor mooiere terminaloutput
"""

import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from ops.utils import ReportWriter, banner

try:
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False


EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s\-().]{7,}\d)")

DEFAULT_TIMEOUT = 10


class WebScraper:
    """
    Haalt een URL op en zoekt basisinformatie:
    titel, meta description, links, e-mailadressen en optionele CSS-selector resultaten.
    """

    def __init__(self, url: str, selector: str = None, follow_links: bool = False):
        self.url = url
        self.selector = selector
        self.follow_links = follow_links
        self.result: dict = {}

    def _fetch(self, url: str) -> BeautifulSoup | None:
        """Haal een URL op en geef een BeautifulSoup-object terug."""
        try:
            headers = {"User-Agent": "CyberSecOpsToolkit/2.0 (educational)"}
            response = requests.get(url, timeout=DEFAULT_TIMEOUT, headers=headers)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException as exc:
            print(f"[!] Request mislukt voor {url}: {exc}")
            return None

    def scrape(self) -> dict:
        """Voer de scrape uit en geef de resultaten terug."""
        banner(f"Webscraper -> {self.url}")

        soup = self._fetch(self.url)
        if soup is None:
            return {}

        title = soup.title.string.strip() if soup.title else "N/A"
        meta_desc_tag = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
        meta_desc = meta_desc_tag.get("content", "N/A") if meta_desc_tag else "N/A"

        links = [
            a.get("href") for a in soup.find_all("a", href=True)
            if a.get("href", "").startswith("http")
        ]

        page_text = soup.get_text()
        emails = list(set(EMAIL_PATTERN.findall(page_text)))

        selector_hits = []
        if self.selector:
            for element in soup.select(self.selector):
                selector_hits.append(element.get_text(strip=True))

        self.result = {
            "url": self.url,
            "scraped_at": datetime.now().isoformat(),
            "title": title,
            "meta_description": meta_desc,
            "links_found": len(links),
            "links": links[:50],
            "emails_found": emails,
            "selector": self.selector,
            "selector_results": selector_hits,
        }

        self._display_results()
        return self.result

    def _display_results(self) -> None:
        """Toon resultaten met Rich als dat beschikbaar is."""
        r = self.result
        if RICH_AVAILABLE:
            table = Table(title=f"Scrape-resultaten - {r['url']}", show_lines=True)
            table.add_column("Veld", style="cyan", no_wrap=True)
            table.add_column("Waarde", style="white")

            table.add_row("Titel", r["title"])
            table.add_row("Meta description", r["meta_description"][:80])
            table.add_row("Links gevonden", str(r["links_found"]))
            table.add_row("E-mails gevonden", ", ".join(r["emails_found"]) or "geen")
            if r["selector"]:
                table.add_row("Selector hits", str(len(r["selector_results"])))
            console.print(table)
        else:
            print(f"  Titel       : {r['title']}")
            print(f"  Beschrijving: {r['meta_description'][:80]}")
            print(f"  Links       : {r['links_found']}")
            print(f"  E-mails     : {', '.join(r['emails_found']) or 'geen'}")

    def save_report(self) -> None:
        writer = ReportWriter("scrape")
        writer.write(self.result)


def run(args) -> None:
    """CLI-startpunt voor het scrape-subcommand."""
    scraper = WebScraper(
        url=args.url,
        selector=args.selector,
    )
    scraper.scrape()
    scraper.save_report()
