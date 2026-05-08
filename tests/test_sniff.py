"""Kleine tests voor fallbackgedrag van de packet sniffer."""

from ops import sniff


def test_sniffer_without_scapy_returns_empty_stats(monkeypatch):
    monkeypatch.setattr(sniff, "SCAPY_AVAILABLE", False)
    sniffer = sniff.PacketSniffer(count=1)
    stats = sniffer.start()

    assert stats["total_packets"] == 0
    assert stats["http_packets"] == 0
    assert stats["credential_hits"] == []
