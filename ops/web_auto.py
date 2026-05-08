"""
web_auto.py - Webautomatisering.
Automatiseert een browser met Selenium, maakt screenshots en toont ze indien mogelijk.

Gebruikte modules: selenium, image_viewer, pathlib, datetime, base64
Nieuwe module: tqdm voor voortgang tijdens de stappen
"""

import base64
from datetime import datetime

from ops.utils import ReportWriter, SCREENSHOTS_DIR, banner

try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    import image_viewer
    IMAGE_VIEWER_AVAILABLE = True
except ImportError:
    IMAGE_VIEWER_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


class WebAutomationBot:
    """
    Simpele browserbot.
    Opent een URL, wacht op een CSS-selector, scrollt en maakt een screenshot.
    """

    def __init__(self, url: str, headless: bool = True):
        self.url = url
        self.headless = headless
        self.driver = None
        self.steps_log: list[dict] = []
        self.screenshot_paths: list[str] = []

    def _init_driver(self) -> None:
        """Start Chrome/Chromium WebDriver."""
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,900")
        self.driver = webdriver.Chrome(options=options)

    def _log_step(self, action: str, detail: str = "") -> None:
        entry = {
            "action": action,
            "detail": detail,
            "timestamp": datetime.now().isoformat(),
        }
        self.steps_log.append(entry)
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] {action}: {detail}")

    def _take_screenshot(self, label: str = "screenshot") -> str | None:
        """Maak een screenshot en geef het pad terug."""
        filename = f"{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        dest = SCREENSHOTS_DIR / filename
        try:
            self.driver.save_screenshot(str(dest))
            self.screenshot_paths.append(str(dest))
            self._log_step("screenshot", str(dest))

            raw = dest.read_bytes()
            base64.b64encode(raw).decode("ascii")
            return str(dest)
        except Exception as exc:
            self._log_step("screenshot_fout", str(exc))
            return None

    def _display_screenshot(self, path: str) -> None:
        """Toon de screenshot met image_viewer als dat beschikbaar is."""
        if IMAGE_VIEWER_AVAILABLE and path:
            try:
                image_viewer.show(path)
            except Exception:
                print(f"  [image_viewer] Kon {path} niet tonen")
        else:
            print(f"  [i] Screenshot opgeslagen op: {path}")

    def run(self, wait_selector: str = "body") -> list[dict]:
        """Voer de browserworkflow uit."""
        if not SELENIUM_AVAILABLE:
            print("[!] Selenium is niet geinstalleerd. Run: pip install selenium")
            return []

        banner(f"Webautomatisering -> {self.url}")

        steps = [
            "Browser starten",
            "URL openen",
            "Wachten op pagina",
            "Pagina scrollen",
            "Screenshot maken",
            "Browser sluiten",
        ]

        iterator = tqdm(steps, desc="Automatisering", unit="stap") if TQDM_AVAILABLE else steps

        try:
            for step in iterator:
                if step == "Browser starten":
                    self._init_driver()
                    self._log_step("init", "Chrome headless gestart")

                elif step == "URL openen":
                    self.driver.get(self.url)
                    self._log_step("navigate", self.url)

                elif step == "Wachten op pagina":
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                        )
                        self._log_step("wait", f"Selector '{wait_selector}' gevonden")
                    except TimeoutException:
                        self._log_step("wait_timeout", "Selector niet gevonden binnen 10s")

                elif step == "Pagina scrollen":
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
                    self._log_step("scroll", "Gescrolld naar 50% van de pagina")

                elif step == "Screenshot maken":
                    path = self._take_screenshot(label="page")
                    self._display_screenshot(path)

                elif step == "Browser sluiten":
                    self.driver.quit()
                    self._log_step("close", "Browser gesloten")

        except WebDriverException as exc:
            self._log_step("fout", str(exc))
            if self.driver:
                self.driver.quit()

        return self.steps_log

    def save_report(self) -> None:
        writer = ReportWriter("web_auto")
        writer.write({
            "url": self.url,
            "steps": self.steps_log,
            "screenshots": self.screenshot_paths,
        })


def run(args) -> None:
    """CLI-startpunt voor het web-auto-subcommand."""
    bot = WebAutomationBot(url=args.url, headless=not args.no_headless)
    bot.run(wait_selector=args.selector or "body")
    bot.save_report()
