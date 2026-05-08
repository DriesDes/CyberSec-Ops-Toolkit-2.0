"""
files.py - Bestandsscanner.
Zoekt verdachte bestanden en patronen, zet ze eventueel in quarantaine en logt naar JSON.

Gebruikte modules: glob, fnmatch, pathlib, os, shutil, send2trash, re, base64, json, datetime
"""

import base64
import fnmatch
import glob
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from ops.utils import REPORTS_DIR, ReportWriter, banner, load_iocs


DEFAULT_PATTERNS = [
    r"eval\s*\(",           # eval() komt vaak voor in obfuscated scripts
    r"base64_decode",       # PHP/shell base64 decode
    r"exec\s*\(",           # mogelijk misbruik van exec()
    r"os\.system\s*\(",     # risico op shell injection
    r"rm\s+-rf",            # destructief shellcommando
    r"wget\s+http",         # downloaden vanuit scripts
    r"chmod\s+777",         # te brede bestandsrechten
    r"\/etc\/passwd",       # verwijzing naar gevoelig systeemfile
]

SUSPICIOUS_EXTENSIONS = {".exe", ".bat", ".vbs", ".ps1", ".sh", ".php", ".hta"}


class FileScanner:
    """
    Scant een map recursief op verdachte bestanden en inhoudspatronen.
    Ondersteunt optionele quarantaine.
    """

    def __init__(self, target_dir: str, quarantine: bool = False, pattern_filter: str = "*"):
        self.target_dir = Path(target_dir).resolve()
        self.quarantine = quarantine
        self.pattern_filter = pattern_filter
        self.iocs = load_iocs()
        self.patterns = DEFAULT_PATTERNS + self.iocs.get("patterns", [])
        self.suspicious_extensions = SUSPICIOUS_EXTENSIONS | set(
            self.iocs.get("extensions", [])
        )
        self.findings: list[dict] = []

    def _scan_content(self, file_path: Path) -> list[str]:
        """Lees een bestand en geef alle verdachte regex-matches terug."""
        matches = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for pattern in self.patterns:
                if re.search(pattern, content):
                    matches.append(pattern)
        except (PermissionError, OSError):
            pass
        return matches

    def _encode_preview(self, file_path: Path, max_bytes: int = 256) -> str:
        """Geef een base64-preview van de eerste bytes van een bestand."""
        try:
            raw = file_path.read_bytes()[:max_bytes]
            return base64.b64encode(raw).decode("ascii")
        except (PermissionError, OSError):
            return ""

    def _quarantine_file(self, file_path: Path) -> str:
        """Verplaats een verdacht bestand naar reports/quarantine of naar de prullenbak."""
        quarantine_dir = REPORTS_DIR / "quarantine"
        quarantine_dir.mkdir(exist_ok=True)
        dest = quarantine_dir / file_path.name

        try:
            shutil.move(str(file_path), str(dest))
            return str(dest)
        except Exception:
            try:
                import send2trash
                send2trash.send2trash(str(file_path))
                return "NAAR_PRULLENBAK"
            except Exception as exc:
                return f"QUARANTAINE_MISLUKT: {exc}"

    def scan(self) -> list[dict]:
        """Doorloop de doelmap en controleer alle kandidaatbestanden."""
        if not self.target_dir.exists():
            raise FileNotFoundError(f"Doelmap bestaat niet: {self.target_dir}")

        banner(f"Bestandsscanner -> {self.target_dir}")
        print(f"[*] Bestandsfilter   : {self.pattern_filter}")
        print(f"[*] Quarantaine      : {'AAN' if self.quarantine else 'UIT'}")
        print()

        all_files = glob.glob(str(self.target_dir / "**" / "*"), recursive=True)
        candidates = [
            Path(f) for f in all_files
            if Path(f).is_file() and fnmatch.fnmatch(Path(f).name, self.pattern_filter)
        ]

        for file_path in candidates:
            is_suspicious_ext = file_path.suffix.lower() in self.suspicious_extensions
            content_hits = self._scan_content(file_path)
            is_suspicious = is_suspicious_ext or bool(content_hits)

            finding = {
                "path": str(file_path),
                "size_bytes": os.path.getsize(file_path),
                "extension": file_path.suffix,
                "suspicious_extension": is_suspicious_ext,
                "pattern_matches": content_hits,
                "scanned_at": datetime.now().isoformat(),
                "quarantined": None,
                "preview_b64": "",
            }

            if is_suspicious:
                finding["preview_b64"] = self._encode_preview(file_path)
                print(f"[!] VERDACHT  {file_path}")
                for hit in content_hits:
                    print(f"    -> patroon gevonden: {hit}")

                if self.quarantine:
                    dest = self._quarantine_file(file_path)
                    finding["quarantined"] = dest
                    print(f"    -> in quarantaine: {dest}")
            else:
                print(f"  [OK] {file_path}")

            if is_suspicious:
                self.findings.append(finding)

        print(f"\n[+] Scan klaar. {len(self.findings)} verdacht(e) bestand(en) gevonden.")
        return self.findings

    def save_report(self) -> None:
        """Sla bevindingen op in een JSON-rapport."""
        writer = ReportWriter("scan")
        writer.write({"findings": self.findings, "total": len(self.findings)})


def run(args) -> None:
    """CLI-startpunt voor het scan-subcommand."""
    scanner = FileScanner(
        target_dir=args.path,
        quarantine=args.quarantine,
        pattern_filter=args.filter,
    )
    scanner.scan()
    scanner.save_report()
