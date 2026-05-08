"""
sniff.py - Packet sniffer.
Vangt HTTP-achtige packets op, zoekt plaintext credentials met regex en bewaart statistieken.

Gebruikte modules: scapy, re, json, datetime
"""

import re
from datetime import datetime

from ops.utils import ReportWriter, banner

try:
    from scapy.all import IP, TCP, Raw, sniff as scapy_sniff
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False


CREDENTIAL_PATTERNS = [
    re.compile(rb"(?i)(user(?:name)?|login)\s*[:=]\s*(\S+)"),
    re.compile(rb"(?i)(pass(?:word)?|passwd|pwd)\s*[:=]\s*(\S+)"),
    re.compile(rb"(?i)Authorization:\s*Basic\s+([A-Za-z0-9+/=]+)"),
]

HTTP_METHODS = (b"GET ", b"POST ", b"PUT ", b"DELETE ", b"HEAD ", b"OPTIONS ")


class PacketSniffer:
    """Vangt TCP-packets op en controleert HTTP-data op simpele credentialpatronen."""

    def __init__(self, interface: str = None, count: int = 50, port_filter: int = 80):
        self.interface = interface
        self.count = count
        self.port_filter = port_filter
        self.stats = {
            "total_packets": 0,
            "http_packets": 0,
            "credential_hits": [],
            "started_at": datetime.now().isoformat(),
            "stopped_at": None,
        }

    def _process_packet(self, pkt) -> None:
        """Callback die door Scapy wordt aangeroepen per packet."""
        self.stats["total_packets"] += 1

        if not (pkt.haslayer(TCP) and pkt.haslayer(Raw)):
            return

        payload: bytes = bytes(pkt[Raw].load)

        if not any(payload.startswith(method) for method in HTTP_METHODS):
            return

        self.stats["http_packets"] += 1
        src_ip = pkt[IP].src if pkt.haslayer(IP) else "onbekend"
        dst_ip = pkt[IP].dst if pkt.haslayer(IP) else "onbekend"

        print(f"  [HTTP]  {src_ip} -> {dst_ip}  ({len(payload)} bytes)")

        for pattern in CREDENTIAL_PATTERNS:
            match = pattern.search(payload)
            if match:
                hit = {
                    "timestamp": datetime.now().isoformat(),
                    "src": src_ip,
                    "dst": dst_ip,
                    "pattern": pattern.pattern.decode(errors="replace"),
                    "matched": match.group(0).decode(errors="replace")[:120],
                }
                self.stats["credential_hits"].append(hit)
                print(f"  [!] CREDENTIALPATROON GEVONDEN: {hit['matched'][:60]}")

    def start(self) -> dict:
        """Start packet capture en geef de statistieken terug."""
        if not SCAPY_AVAILABLE:
            print("[!] Scapy is niet geinstalleerd of niet bereikbaar. Run: pip install scapy")
            return self.stats

        banner("Packet sniffer")
        iface_label = self.interface or "standaardinterface"
        print(f"[*] Interface : {iface_label}")
        print(f"[*] Poort     : {self.port_filter}")
        print(f"[*] Aantal    : {self.count}")
        print("[*] Capture gestart... (Ctrl+C om te stoppen)\n")

        bpf_filter = f"tcp port {self.port_filter}"
        kwargs = {"filter": bpf_filter, "count": self.count, "prn": self._process_packet, "store": False}
        if self.interface:
            kwargs["iface"] = self.interface

        try:
            scapy_sniff(**kwargs)
        except PermissionError:
            print("[!] Geen rechten. Start als administrator/root voor packet capture.")
        except KeyboardInterrupt:
            print("\n[!] Capture gestopt door gebruiker.")

        self.stats["stopped_at"] = datetime.now().isoformat()
        self._print_summary()
        return self.stats

    def _print_summary(self) -> None:
        print("\n--- Capture samenvatting ---")
        print(f"  Totaal packets   : {self.stats['total_packets']}")
        print(f"  HTTP packets     : {self.stats['http_packets']}")
        print(f"  Credential hits  : {len(self.stats['credential_hits'])}")

    def save_report(self) -> None:
        writer = ReportWriter("sniff")
        writer.write(self.stats)


def run(args) -> None:
    """CLI-startpunt voor het sniff-subcommand."""
    sniffer = PacketSniffer(
        interface=args.interface,
        count=args.count,
        port_filter=args.port,
    )
    sniffer.start()
    sniffer.save_report()
