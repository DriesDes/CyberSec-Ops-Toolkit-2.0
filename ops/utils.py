"""Gedeelde hulpfuncties voor CyberSec Ops Toolkit 2.0."""

import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_DIR = PROJECT_ROOT / "data"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class ToolkitError(Exception):
    """Basisfout voor toolkit-specifieke problemen."""


class ReportWriter:
    """Schrijft gestructureerde JSON-rapporten naar de reports-map."""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.timestamp = datetime.now().isoformat()

    def write(self, data: dict) -> Path:
        filename = f"{self.tool_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_path = REPORTS_DIR / filename
        report = {
            "tool": self.tool_name,
            "generated_at": self.timestamp,
            "data": data,
        }

        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, default=str)

        print(f"[+] Rapport opgeslagen -> {output_path}")
        return output_path


def load_config() -> dict:
    config_path = DATA_DIR / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_iocs() -> dict:
    ioc_path = DATA_DIR / "iocs.json"
    if not ioc_path.exists():
        return {"patterns": [], "extensions": []}
    with open(ioc_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def banner(text: str) -> None:
    print(f"\n=== {text} ===")
