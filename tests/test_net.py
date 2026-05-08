"""Unit tests voor de netwerkscanner."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ops.net import PortScanner


class TestPortScanner:
    """Tests voor de PortScanner-klasse."""

    def test_cidr_expansion(self):
        """Een /30 CIDR-blok heeft twee bruikbare hostadressen."""
        scanner = PortScanner(targets="192.168.1.0/30", ports=[80], timeout=0.1)
        assert len(scanner.targets) == 2

    def test_single_ip_target(self):
        """Een los IP-adres geeft exact een target."""
        scanner = PortScanner(targets="10.0.0.1", ports=[80], timeout=0.1)
        assert scanner.targets == ["10.0.0.1"]

    def test_comma_separated_targets(self):
        """Komma-gescheiden IP's worden apart verwerkt."""
        scanner = PortScanner(targets="10.0.0.1,10.0.0.2,10.0.0.3", ports=[80], timeout=0.1)
        assert len(scanner.targets) == 3

    def test_results_type(self):
        """Resultaten zijn een dict van host naar lijst met poorten."""
        scanner = PortScanner(targets="127.0.0.1", ports=[9], timeout=0.2)
        results = scanner.scan()
        assert isinstance(results, dict)
        for host, ports in results.items():
            assert isinstance(host, str)
            assert isinstance(ports, list)
            assert all(isinstance(p, int) for p in ports)

    def test_closed_port_not_in_results(self):
        """Poort 1 op localhost hoort normaal niet als open terug te komen."""
        scanner = PortScanner(targets="127.0.0.1", ports=[1], timeout=0.3, randomize=False)
        results = scanner.scan()
        open_ports = results.get("127.0.0.1", [])
        assert 1 not in open_ports

    def test_randomize_flag_does_not_break_scan(self):
        """Randomisatie mag de datastructuur niet veranderen."""
        scanner = PortScanner(targets="127.0.0.1", ports=[80, 443], timeout=0.2, randomize=True)
        results = scanner.scan()
        assert isinstance(results, dict)
