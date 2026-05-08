"""
report.py - Rapportage en e-mailmeldingen.
Voegt JSON-rapporten samen en maakt een e-mailbericht.

Gebruikte modules: email, base64, json, socket, glob
"""

import base64
import glob
import json
import socket
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from ops.utils import REPORTS_DIR, ReportWriter, banner


class ReportMerger:
    """Laadt alle JSON-rapporten uit reports/ en maakt een korte samenvatting."""

    def __init__(self):
        self.merged: dict = {
            "merged_at": datetime.now().isoformat(),
            "report_count": 0,
            "reports": [],
        }

    def merge(self) -> dict:
        """Lees alle JSON-rapporten en combineer ze."""
        report_files = glob.glob(str(REPORTS_DIR / "*.json"))
        report_files = [f for f in report_files if "merged_report" not in f]

        banner("Rapporten samenvoegen")
        print(f"[*] {len(report_files)} rapport(en) gevonden in {REPORTS_DIR}")

        for filepath in sorted(report_files):
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                self.merged["reports"].append({
                    "file": Path(filepath).name,
                    "tool": data.get("tool", "unknown"),
                    "generated_at": data.get("generated_at", ""),
                    "summary": self._summarize(data),
                })
            except (json.JSONDecodeError, OSError) as exc:
                print(f"  [!] Kon {filepath} niet lezen: {exc}")

        self.merged["report_count"] = len(self.merged["reports"])
        print(f"[+] {self.merged['report_count']} rapport(en) samengevoegd.")
        return self.merged

    @staticmethod
    def _summarize(data: dict) -> dict:
        """Haal een korte samenvatting uit de data-sectie van een rapport."""
        inner = data.get("data", {})
        summary = {}
        for key, val in inner.items():
            if isinstance(val, (str, int, float, bool)):
                summary[key] = val
            elif isinstance(val, list):
                summary[f"{key}_count"] = len(val)
        return summary

    def save(self) -> Path:
        writer = ReportWriter("merged_report")
        return writer.write(self.merged)


class EmailAlert:
    """
    Bouwt een MIME-email uit het samengevoegde rapport.
    Kan optioneel via een raw SMTP-socket verzenden.
    """

    def __init__(self, sender: str, recipient: str, smtp_host: str = None, smtp_port: int = 25):
        self.sender = sender
        self.recipient = recipient
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

    def build_message(self, merged_report: dict) -> MIMEMultipart:
        """Maak een MIME-email met tekst en JSON-attachment."""
        msg = MIMEMultipart("mixed")
        msg["From"] = self.sender
        msg["To"] = self.recipient
        msg["Subject"] = f"[CyberSec Ops] Rapport - {merged_report['merged_at'][:10]}"

        body_lines = [
            "CyberSec Ops Toolkit 2.0 - automatisch rapport",
            "=" * 48,
            f"Gemaakt op : {merged_report['merged_at']}",
            f"Rapporten  : {merged_report['report_count']}",
            "",
        ]
        for rep in merged_report["reports"]:
            body_lines.append(f"- [{rep['tool']}] {rep['file']} (gemaakt op {rep['generated_at'][:19]})")
            for k, v in rep["summary"].items():
                body_lines.append(f"    {k}: {v}")
            body_lines.append("")

        body_lines += [
            "-" * 48,
            "Dit rapport werd automatisch gemaakt door CyberSec Ops Toolkit 2.0.",
            "Gebruik alleen op eigen systemen of legale testomgevingen.",
        ]

        msg.attach(MIMEText("\n".join(body_lines), "plain", "utf-8"))

        json_bytes = json.dumps(merged_report, indent=2, default=str).encode("utf-8")
        base64.encodebytes(json_bytes)

        attachment = MIMEApplication(json_bytes, _subtype="json")
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=f"report_{merged_report['merged_at'][:10]}.json",
        )
        msg.attach(attachment)

        return msg

    def send_raw_smtp(self, msg: MIMEMultipart) -> None:
        """Verstuur de e-mail via een eenvoudige raw SMTP-socket."""
        if not self.smtp_host:
            print("[!] Geen SMTP-host ingesteld. Verzenden wordt overgeslagen.")
            return

        raw = msg.as_bytes()
        print(f"\n[*] Verbinden met SMTP {self.smtp_host}:{self.smtp_port} via raw socket...")

        try:
            with socket.create_connection((self.smtp_host, self.smtp_port), timeout=5) as sock:
                banner_line = sock.recv(1024).decode(errors="replace").strip()
                print(f"  Server: {banner_line}")

                def smtp_cmd(cmd: str) -> str:
                    sock.sendall((cmd + "\r\n").encode())
                    return sock.recv(4096).decode(errors="replace").strip()

                print(f"  > {smtp_cmd('EHLO toolkit')}")
                print(f"  > {smtp_cmd(f'MAIL FROM:<{self.sender}>')}")
                print(f"  > {smtp_cmd(f'RCPT TO:<{self.recipient}>')}")
                print(f"  > {smtp_cmd('DATA')}")
                sock.sendall(raw + b"\r\n.\r\n")
                resp = sock.recv(1024).decode(errors="replace").strip()
                print(f"  > {resp}")
                smtp_cmd("QUIT")
                print("[+] E-mail verstuurd via raw SMTP socket.")
        except (socket.timeout, ConnectionRefusedError, OSError) as exc:
            print(f"[!] SMTP-verbinding mislukt: {exc}")

    def print_preview(self, msg: MIMEMultipart) -> None:
        """Print de e-mailheaders en body in dry-run modus."""
        print("\n--- E-mailvoorbeeld ---")
        print(f"  Van       : {msg['From']}")
        print(f"  Naar      : {msg['To']}")
        print(f"  Onderwerp : {msg['Subject']}")
        print()
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                print(part.get_payload(decode=True).decode("utf-8", errors="replace"))
                break


def run(args) -> None:
    """CLI-startpunt voor het report-subcommand."""
    merger = ReportMerger()
    merged = merger.merge()
    merger.save()

    alert = EmailAlert(
        sender=args.sender,
        recipient=args.recipient,
        smtp_host=args.smtp_host,
        smtp_port=args.smtp_port,
    )
    msg = alert.build_message(merged)

    if args.send:
        alert.send_raw_smtp(msg)
    else:
        alert.print_preview(msg)
        print("\n[i] Voeg --send toe om via raw SMTP socket te verzenden.")
