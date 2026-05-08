"""Command-line interface voor CyberSec Ops Toolkit 2.0."""

import argparse
import sys

from ops import files, net, report, scrape, serve, sniff, ssh, web_auto

TOOLKIT_VERSION = "2.0.0"

ASCII_BANNER = """
CyberSec Ops Toolkit 2.0
Scripting and Code Analysis | versie {version}
"""


def build_parser() -> argparse.ArgumentParser:
    """Maak de hoofdparser en alle subcommands."""
    parser = argparse.ArgumentParser(
        prog="ops",
        description="CyberSec Ops Toolkit 2.0 - securitytools voor een legale labomgeving.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Gebruik dit alleen op eigen systemen of in toegelaten testomgevingen.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {TOOLKIT_VERSION}")

    subparsers = parser.add_subparsers(dest="subcommand", title="subcommands", metavar="<subcommand>")
    subparsers.required = True

    p_scan = subparsers.add_parser("scan", help="Scan een map op verdachte bestanden en patronen.")
    p_scan.add_argument("path", help="Map die gescand moet worden.")
    p_scan.add_argument("--quarantine", action="store_true", help="Verplaats verdachte bestanden naar quarantaine.")
    p_scan.add_argument("--filter", default="*", metavar="GLOB", help="Bestandsfilter, bijvoorbeeld *.py.")
    p_scan.set_defaults(func=files.run)

    p_net = subparsers.add_parser("net-scan", help="Parallelle TCP-poortscanner met CIDR-ondersteuning.")
    p_net.add_argument("target", help="IP, CIDR-range of IP-adressen gescheiden door komma's.")
    p_net.add_argument("--ports", metavar="PORTS", help="Poorten gescheiden door komma's.")
    p_net.add_argument("--timeout", type=float, default=1.0, help="Socket-timeout in seconden.")
    p_net.add_argument("--no-random", action="store_true", help="Schakel willekeurige scanvolgorde uit.")
    p_net.set_defaults(func=net.run)

    p_sniff = subparsers.add_parser("sniff", help="Vang HTTP-packets op en zoek naar credentials.")
    p_sniff.add_argument("--interface", "-i", help="Netwerkinterface waarop geluisterd wordt.")
    p_sniff.add_argument("--count", "-c", type=int, default=50, help="Aantal packets om te capteren.")
    p_sniff.add_argument("--port", "-p", type=int, default=80, help="TCP-poortfilter.")
    p_sniff.set_defaults(func=sniff.run)

    p_scrape = subparsers.add_parser("scrape", help="Download en analyseer een webpagina.")
    p_scrape.add_argument("url", help="URL die gescrapet moet worden.")
    p_scrape.add_argument("--selector", "-s", metavar="CSS", help="CSS-selector om content uit te halen.")
    p_scrape.set_defaults(func=scrape.run)

    p_auto = subparsers.add_parser("web-auto", help="Selenium browserautomatisering met screenshots.")
    p_auto.add_argument("url", help="URL die geopend moet worden.")
    p_auto.add_argument("--selector", "-s", metavar="CSS", help="CSS-selector waarop gewacht wordt.")
    p_auto.add_argument("--no-headless", action="store_true", help="Toon het browservenster.")
    p_auto.set_defaults(func=web_auto.run)

    p_ssh = subparsers.add_parser("ssh", help="SSH-automatisering en lokale diagnose-tools.")
    p_ssh.add_argument("--host", help="Remote host om mee te verbinden.")
    p_ssh.add_argument("--port", type=int, default=22, help="SSH-poort.")
    p_ssh.add_argument("--user", default="root", help="SSH-gebruikersnaam.")
    p_ssh.add_argument("--key", metavar="PATH", help="Pad naar private key.")
    p_ssh.add_argument("--password", metavar="PASS", help="SSH-wachtwoord voor labgebruik.")
    p_ssh.add_argument("--commands", nargs="+", metavar="CMD", help="Commando's om remote uit te voeren.")
    p_ssh.add_argument("--whois", metavar="TARGET", help="Voer lokale whois uit zonder SSH.")
    p_ssh.set_defaults(func=ssh.run)

    p_serve = subparsers.add_parser("serve", help="Toon JSON-rapporten via een lokaal HTTP-dashboard.")
    p_serve.add_argument("--host", default="127.0.0.1", help="Luisteradres.")
    p_serve.add_argument("--port", type=int, default=8000, help="Luisterpoort.")
    p_serve.set_defaults(func=serve.run)

    p_report = subparsers.add_parser("report", help="Voeg rapporten samen en maak een e-mailmelding.")
    p_report.add_argument("--sender", default="toolkit@localhost", help="E-mailadres van afzender.")
    p_report.add_argument("--recipient", default="admin@localhost", help="E-mailadres van ontvanger.")
    p_report.add_argument("--smtp-host", default=None, help="SMTP-serverhost.")
    p_report.add_argument("--smtp-port", type=int, default=25, help="SMTP-serverpoort.")
    p_report.add_argument("--send", action="store_true", help="Verstuur de e-mail via raw SMTP socket.")
    p_report.set_defaults(func=report.run)

    return parser


def main() -> None:
    """Lees argumenten en voer het gekozen subcommand uit."""
    print(ASCII_BANNER.format(version=TOOLKIT_VERSION))
    parser = build_parser()
    args = parser.parse_args()

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n[!] Onderbroken door gebruiker.")
        sys.exit(0)
    except Exception as exc:
        print(f"\n[!] Onverwachte fout: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
