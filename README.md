# CyberSec Ops Toolkit 2.0

## Installatie

Vereisten:

- Python 3.11 of nieuwer
- Chrome/Chromedriver voor `web-auto`
- Administrator/root rechten voor `sniff`

Installeer de dependencies:

```bash
pip install -r requirements.txt
```

## Starten

```bash
python -m ops.cli --help
python main.py --help
```

Algemene vorm:

```bash
python -m ops.cli <subcommand> [arguments]
```

## Projectstructuur

```text
cybersec_ops_toolkit/
├─ main.py
├─ ops/
│  ├─ __init__.py
│  ├─ cli.py
│  ├─ files.py
│  ├─ net.py
│  ├─ sniff.py
│  ├─ scrape.py
│  ├─ web_auto.py
│  ├─ ssh.py
│  ├─ serve.py
│  ├─ report.py
│  └─ utils.py
├─ data/
│  ├─ config.json
│  ├─ iocs.json
│  └─ screenshots/
├─ reports/
├─ tests/
│  ├─ test_files.py
│  ├─ test_net.py
│  ├─ test_scrape.py
│  └─ test_report.py
├─ requirements.txt
└─ README.md
```

## Subcommands

### scan

Scant een map op verdachte extensies en verdachte tekstpatronen. Verdachte bestanden kunnen naar quarantaine worden verplaatst.

```bash
python -m ops.cli scan ./testmap
python -m ops.cli scan ./testmap --filter "*.py"
python -m ops.cli scan ./testmap --quarantine
```

Voorbeeldoutput:

```text
=== File Scanner -> C:\lab\testmap ===
[*] Pattern filter : *.py
[*] Quarantine mode: OFF
[+] Scan complete. 1 suspicious file(s) found.
[+] Report saved -> reports/scan_20260508_150000.json
```

### net-scan

Een eenvoudige TCP portscanner met threads. Hij ondersteunt losse IP-adressen, meerdere IP-adressen en CIDR ranges.

```bash
python -m ops.cli net-scan 127.0.0.1 --ports 22,80,443
python -m ops.cli net-scan 192.168.1.0/30 --timeout 0.5 --no-random
```

Voorbeeldoutput:

```text
=== Network Scanner ===
[*] Targets  : 127.0.0.1
[*] Ports    : [22, 80, 443]
No open ports found.
```

### sniff

Gebruikt Scapy om HTTP-achtige packets te bekijken en eenvoudige credential-patronen te zoeken.
Dit werkt alleen met voldoende rechten en op een netwerkinterface waar verkeer zichtbaar is.

```bash
python -m ops.cli sniff --count 20 --port 80
python -m ops.cli sniff --interface eth0 --count 50
```

### scrape

Haalt een webpagina op, parsed HTML met BeautifulSoup, zoekt links, e-mailadressen en optioneel CSS-selector content.

```bash
python -m ops.cli scrape https://example.com
python -m ops.cli scrape https://example.com --selector "h1"
```

### web-auto

Start Selenium, opent een pagina en maakt een screenshot. Als `image_viewer` aanwezig is, probeert de tool de screenshot ook te tonen.

```bash
python -m ops.cli web-auto https://example.com
python -m ops.cli web-auto https://example.com --selector "body" --no-headless
```

### ssh

Kan via Paramiko verbinden met een SSH-server en commando's uitvoeren. Er is ook een lokale `whois` optie via `subprocess`.

```bash
python -m ops.cli ssh --host 192.168.56.10 --user student --key ~/.ssh/id_rsa --commands "id" "uname -a"
python -m ops.cli ssh --whois example.com
```

Gebruik geen echte wachtwoorden in screenshots of in Git. Voor de demo is key-based login beter.

### serve

Start een lokale HTTP-server die JSON rapporten uit `reports/` toont.

```bash
python -m ops.cli serve
python -m ops.cli serve --port 9000
```

Open daarna:

```text
http://127.0.0.1:8000
```

### report

Leest JSON rapporten, maakt een samenvatting en bouwt een e-mailbericht met JSON attachment.
Met `--send` kan het bericht naar een test-SMTP server gestuurd worden via een raw socket.

```bash
python -m ops.cli report --sender toolkit@localhost --recipient admin@localhost
python -m ops.cli report --smtp-host 127.0.0.1 --smtp-port 1025 --send
```

## Checklist verplichte modules

| Module | Where used? |
|---|---|
| `argparse` | `ops/cli.py` voor subcommands en argumenten |
| `base64` | `ops/files.py` voor file previews, `ops/report.py` voor email attachment, `ops/web_auto.py` voor screenshot encoding, `ops/ssh.py` voor fingerprint output |
| `bs4` | `ops/scrape.py` voor HTML parsing met BeautifulSoup |
| `datetime` | rapportnamen, timestamps en logs in meerdere modules |
| `email` | `ops/report.py` voor MIME e-mails |
| `fnmatch` | `ops/files.py` voor bestandsfilters |
| `glob` | `ops/files.py`, `ops/report.py`, `ops/serve.py` voor bestanden zoeken |
| `http` | `ops/serve.py` met `HTTPServer` en `BaseHTTPRequestHandler` |
| `image_viewer` | `ops/web_auto.py` om screenshots te tonen als de module beschikbaar is |
| `itertools` | `ops/net.py` voor host/poort combinaties |
| `json` | rapporten lezen en schrijven in meerdere modules |
| `os` | `ops/files.py` en `ops/serve.py` voor bestandsgrootte en mtime |
| `paramiko` | `ops/ssh.py` voor SSH |
| `pathlib` | paden in bijna alle file/report functies |
| `random` | `ops/net.py` voor scanvolgorde en jitter |
| `re` | `ops/files.py`, `ops/sniff.py`, `ops/scrape.py` voor regex |
| `requests` | `ops/scrape.py` voor HTTP requests |
| `scapy` | `ops/sniff.py` voor packet capture |
| `selenium` | `ops/web_auto.py` voor browser automation |
| `send2trash` | `ops/files.py` als fallback bij quarantaine |
| `shutil` | `ops/files.py` voor bestanden verplaatsen |
| `socket` | `ops/net.py` voor TCP connecties en `ops/report.py` voor SMTP socket |
| `subprocess` | `ops/ssh.py` voor lokale tools zoals `whois` |
| `sys` | `ops/cli.py` voor exit codes |
| `threading` | `ops/net.py` voor parallel scannen |
| `time` | `ops/net.py` voor kleine random delays |

## Drie nieuwe modules

### rich

`rich` maakt terminaloutput mooier. Ik gebruik het in `ops/scrape.py` om scrape-resultaten als tabel te tonen. Als de module niet aanwezig is, gebruikt de code gewone `print()`.

Ik koos deze module omdat output van CLI-tools snel onoverzichtelijk wordt.

### tqdm

`tqdm` toont een progress bar. Ik gebruik het in `ops/web_auto.py` voor de stappen van de Selenium workflow.

Ik koos deze module omdat browser automation soms traag is en je anders niet ziet in welke stap het programma zit.

### cryptography

`cryptography` bevat veilige crypto-primitieven. Ik gebruik `hashes.Hash(hashes.SHA256())` in `ops/ssh.py` om de fingerprint van een SSH host key te berekenen.

Ik koos deze module omdat host key fingerprints horen bij veilig SSH-gebruik.

## Tests

De tests zijn zelfgemaakt en gebruiken vooral dummy data of monkeypatching.

```bash
pytest tests/ -v
```

Aanwezige tests:

- `test_files.py`: verdachte extensies, regex hits, base64 preview en lege mappen
- `test_net.py`: CIDR parsing, losse targets en scan-resultaatstructuur
- `test_scrape.py`: dummy HTML, e-maildetectie, links en CSS selectors
- `test_report.py`: rapporten mergen, MIME e-mail en SMTP-foutafhandeling
- `test_serve.py`: dashboard HTML met dummy JSON rapporten
- `test_ssh.py`: lokale subprocess helper en SSH zonder verbinding
- `test_web_auto.py`: fallback als Selenium niet beschikbaar is
- `test_sniff.py`: fallback als Scapy niet beschikbaar is

Niet alles is volledig als echte integratietest getest. Packet sniffing, Selenium met echte browser en echte SSH-verbindingen hangen af van lokale rechten, browserdrivers of labmachines. Die onderdelen zijn vooral handmatig te testen in een veilige omgeving.

## Ethische disclaimer

Gebruik deze toolkit alleen op je eigen toestellen, eigen netwerk of een expliciet toegelaten testomgeving.
Netwerken scannen, packets sniffen of inloggen op systemen zonder toestemming is illegaal.

Dit project is gemaakt voor onderwijsdoeleinden.
