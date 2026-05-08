"""
net.py - Netwerkscanner.
Parallelle TCP-poortscanner met CIDR-ondersteuning, randomisatie en timeouts.

Gebruikte modules: socket, threading, random, time, itertools
"""

import itertools
import random
import socket
import threading
import time
from ipaddress import ip_network

from ops.utils import ReportWriter, banner


DEFAULT_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 8080, 8443]
MAX_THREADS = 100


class PortScanner:
    """
    TCP-poortscanner met threads.
    Ondersteunt losse IP's, komma-gescheiden IP's en CIDR-notatie.
    """

    def __init__(self, targets: str, ports: list[int], timeout: float = 1.0, randomize: bool = True):
        self.targets = self._parse_targets(targets)
        self.ports = ports
        self.timeout = timeout
        self.randomize = randomize
        self.results: dict[str, list[int]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _parse_targets(targets_str: str) -> list[str]:
        """Accepteer een CIDR-range, een los IP-adres of een lijst met komma's."""
        hosts = []
        for part in targets_str.split(","):
            part = part.strip()
            try:
                network = ip_network(part, strict=False)
                hosts.extend(str(h) for h in network.hosts())
            except ValueError:
                hosts.append(part)
        return hosts

    def _probe_port(self, host: str, port: int) -> None:
        """Probeer een TCP-connectie naar host:port."""
        try:
            with socket.create_connection((host, port), timeout=self.timeout):
                with self._lock:
                    self.results.setdefault(host, []).append(port)
                print(f"  [OPEN]  {host}:{port}")
        except (socket.timeout, ConnectionRefusedError, OSError):
            pass

    def scan(self) -> dict[str, list[int]]:
        """Start een threaded scan over alle host/poort-combinaties."""
        banner("Netwerkscanner")
        print(f"[*] Doelen       : {', '.join(self.targets[:5])}{'...' if len(self.targets) > 5 else ''}")
        print(f"[*] Poorten      : {self.ports}")
        print(f"[*] Timeout      : {self.timeout}s  |  Randomisatie: {self.randomize}")
        print()

        combinations = list(itertools.product(self.targets, self.ports))

        if self.randomize:
            random.shuffle(combinations)

        threads = []
        semaphore = threading.Semaphore(MAX_THREADS)

        def worker(host: str, port: int) -> None:
            with semaphore:
                time.sleep(random.uniform(0.01, 0.05))
                self._probe_port(host, port)

        for host, port in combinations:
            t = threading.Thread(target=worker, args=(host, port), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self._print_summary()
        return self.results

    def _print_summary(self) -> None:
        print("\n--- Samenvatting ---")
        if not self.results:
            print("  Geen open poorten gevonden.")
            return
        for host, open_ports in sorted(self.results.items()):
            print(f"  {host} -> {sorted(open_ports)}")

    def save_report(self) -> None:
        writer = ReportWriter("net_scan")
        writer.write(self.results)


def run(args) -> None:
    """CLI-startpunt voor het net-scan-subcommand."""
    ports = DEFAULT_PORTS
    if args.ports:
        ports = [int(p) for p in args.ports.split(",")]

    scanner = PortScanner(
        targets=args.target,
        ports=ports,
        timeout=args.timeout,
        randomize=not args.no_random,
    )
    scanner.scan()
    scanner.save_report()
