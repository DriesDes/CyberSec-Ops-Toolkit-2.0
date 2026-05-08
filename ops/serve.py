"""
serve.py - HTTP-dashboard.
Serveert JSON-rapporten uit reports/ via een lokale HTTP-server.

Gebruikte modules: http, json, os, pathlib, glob
"""

import glob
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from ops.utils import REPORTS_DIR, banner


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<title>CyberSec Ops Toolkit - Dashboard</title>
<style>
  :root {{ --bg:#0d1117; --surface:#161b22; --border:#30363d; --accent:#58a6ff; --text:#e6edf3; --red:#f85149; --green:#3fb950; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:"Courier New",monospace; padding:2rem; }}
  h1 {{ color:var(--accent); margin-bottom:0.5rem; font-size:1.4rem; }}
  .sub {{ color:#8b949e; font-size:0.85rem; margin-bottom:2rem; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:1rem; }}
  .card {{ background:var(--surface); border:1px solid var(--border); border-radius:6px; padding:1rem; }}
  .card h3 {{ color:var(--accent); font-size:0.9rem; margin-bottom:0.5rem; word-break:break-all; }}
  .meta {{ color:#8b949e; font-size:0.75rem; margin-bottom:0.75rem; }}
  pre {{ background:var(--bg); border:1px solid var(--border); border-radius:4px; padding:0.75rem;
         font-size:0.72rem; max-height:240px; overflow:auto; white-space:pre-wrap; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:3px; font-size:0.7rem; font-weight:bold; }}
  .badge-scan {{ background:#21262d; color:var(--red); }}
  .badge-net  {{ background:#21262d; color:var(--green); }}
  .badge-scrape {{ background:#21262d; color:var(--accent); }}
  .badge-other {{ background:#21262d; color:#e3b341; }}
  a {{ color:var(--accent); }}
</style>
</head>
<body>
<h1>CyberSec Ops Toolkit 2.0 - Dashboard</h1>
<p class="sub">Rapporten uit <code>{reports_dir}</code> - {count} rapport(en) gevonden - {ts}</p>
<div class="grid">{cards}</div>
</body>
</html>"""

CARD_HTML = """
<div class="card">
  <h3>{filename}</h3>
  <p class="meta"><span class="badge badge-{tool_class}">{tool}</span> &nbsp; gemaakt op {generated_at}</p>
  <pre>{preview}</pre>
  <p style="margin-top:0.5rem;font-size:0.75rem;"><a href="/reports/{filename}">raw JSON</a></p>
</div>"""


def _build_dashboard() -> str:
    """Bouw de HTML-pagina voor het dashboard."""
    report_files = sorted(
        glob.glob(str(REPORTS_DIR / "*.json")),
        key=os.path.getmtime,
        reverse=True,
    )

    cards_html = ""
    for filepath in report_files:
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            tool = data.get("tool", "unknown")
            generated_at = data.get("generated_at", "")
            preview = json.dumps(data.get("data", {}), indent=2, default=str)[:600]
            badge = "scan" if "scan" in tool else ("net" if "net" in tool else ("scrape" if "scrape" in tool else "other"))
            cards_html += CARD_HTML.format(
                filename=Path(filepath).name,
                tool=tool,
                tool_class=badge,
                generated_at=generated_at[:19],
                preview=preview,
            )
        except (json.JSONDecodeError, OSError):
            pass

    return DASHBOARD_HTML.format(
        reports_dir=REPORTS_DIR,
        count=len(report_files),
        ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        cards=cards_html or "<p style='color:#8b949e'>Nog geen rapporten gevonden.</p>",
    )


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP-handler voor dashboard en raw JSON endpoints."""

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            content = _build_dashboard().encode("utf-8")
            self._respond(200, "text/html; charset=utf-8", content)

        elif self.path.startswith("/reports/"):
            filename = Path(self.path).name
            filepath = REPORTS_DIR / filename
            if filepath.exists() and filepath.suffix == ".json":
                content = filepath.read_bytes()
                self._respond(200, "application/json", content)
            else:
                self._respond(404, "text/plain", b"Niet gevonden")
        else:
            self._respond(404, "text/plain", b"Niet gevonden")

    def _respond(self, code: int, content_type: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class DashboardServer:
    """Wrapper rond HTTPServer."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        self.host = host
        self.port = port
        self.httpd = HTTPServer((host, port), DashboardHandler)

    def serve_forever(self) -> None:
        banner("HTTP-dashboard")
        print(f"[+] Dashboard draait op http://{self.host}:{self.port}")
        print("[*] Druk op Ctrl+C om te stoppen.\n")
        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Server gestopt.")
        finally:
            self.httpd.server_close()


def run(args) -> None:
    """CLI-startpunt voor het serve-subcommand."""
    server = DashboardServer(host=args.host, port=args.port)
    server.serve_forever()
