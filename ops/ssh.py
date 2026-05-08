"""
ssh.py - SSH-automatisering.
Verbindt met hosts via Paramiko, voert commando's uit en kan lokale diagnose-tools starten.

Gebruikte modules: paramiko, subprocess, json, datetime
Nieuwe module: cryptography voor SSH host key fingerprints
"""

import base64
import subprocess
from datetime import datetime

from ops.utils import ReportWriter, banner

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

try:
    from cryptography.hazmat.primitives import hashes
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class SSHClient:
    """
    Kleine wrapper rond Paramiko.
    Credentials worden alleen tijdens runtime gebruikt en niet opgeslagen.
    """

    def __init__(self, host: str, port: int, username: str, key_path: str = None, password: str = None):
        self.host = host
        self.port = port
        self.username = username
        self.key_path = key_path
        self.password = password
        self.client = None
        self.results: list[dict] = []

    def connect(self) -> bool:
        """Maak een SSH-verbinding met key of wachtwoord."""
        if not PARAMIKO_AVAILABLE:
            print("[!] Paramiko is niet geinstalleerd. Run: pip install paramiko")
            return False

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.WarningPolicy())

        try:
            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "timeout": 10,
            }
            if self.key_path:
                connect_kwargs["key_filename"] = self.key_path
            elif self.password:
                connect_kwargs["password"] = self.password
            else:
                raise ValueError("Geef --key of --password mee voor SSH-authenticatie.")

            self.client.connect(**connect_kwargs)

            transport = self.client.get_transport()
            if transport and CRYPTO_AVAILABLE:
                host_key = transport.get_remote_server_key()
                raw_key = host_key.asbytes()
                digest_context = hashes.Hash(hashes.SHA256())
                digest_context.update(raw_key)
                digest = digest_context.finalize()
                fp = base64.b64encode(digest).decode("ascii")
                print(f"  [*] Host key fingerprint (SHA256): {fp}")

            print(f"  [+] Verbonden met {self.host}:{self.port} als {self.username}")
            return True

        except (paramiko.AuthenticationException, paramiko.SSHException, OSError) as exc:
            print(f"  [!] Verbinding mislukt: {exc}")
            return False

    def execute(self, command: str) -> dict:
        """Voer een commando uit via SSH en geef stdout/stderr terug."""
        if not self.client:
            return {"error": "Not connected"}

        result = {
            "command": command,
            "executed_at": datetime.now().isoformat(),
            "stdout": "",
            "stderr": "",
            "exit_code": None,
        }

        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=30)
            result["stdout"] = stdout.read().decode(errors="replace").strip()
            result["stderr"] = stderr.read().decode(errors="replace").strip()
            result["exit_code"] = stdout.channel.recv_exit_status()

            print(f"\n  $ {command}")
            if result["stdout"]:
                for line in result["stdout"].splitlines()[:20]:
                    print(f"    {line}")
        except paramiko.SSHException as exc:
            result["error"] = str(exc)

        self.results.append(result)
        return result

    def close(self) -> None:
        if self.client:
            self.client.close()
            print("\n  [*] SSH-verbinding gesloten.")

    def save_report(self) -> None:
        writer = ReportWriter("ssh")
        writer.write({
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "commands": self.results,
        })


class LocalTools:
    """Start lokale diagnose-tools via subprocess."""

    def __init__(self):
        self.results: list[dict] = []

    def run_whois(self, target: str) -> dict:
        """Voer whois uit op een domein of IP."""
        return self._run(["whois", target], label=f"whois {target}")

    def run_nslookup(self, target: str) -> dict:
        """Voer nslookup uit voor DNS-informatie."""
        return self._run(["nslookup", target], label=f"nslookup {target}")

    def _run(self, cmd: list[str], label: str) -> dict:
        result = {
            "command": " ".join(cmd),
            "label": label,
            "executed_at": datetime.now().isoformat(),
            "stdout": "",
            "stderr": "",
            "return_code": None,
        }
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
            )
            result["stdout"] = proc.stdout.strip()
            result["stderr"] = proc.stderr.strip()
            result["return_code"] = proc.returncode

            print(f"\n  [{label}]")
            for line in result["stdout"].splitlines()[:25]:
                print(f"    {line}")
        except FileNotFoundError:
            result["error"] = f"Commando '{cmd[0]}' niet gevonden op dit systeem."
            print(f"  [!] {result['error']}")
        except subprocess.TimeoutExpired:
            result["error"] = "Commando duurde te lang."

        self.results.append(result)
        return result


def run(args) -> None:
    """CLI-startpunt voor het ssh-subcommand."""
    banner("SSH-automatisering")

    if args.whois:
        local = LocalTools()
        local.run_whois(args.whois)
        writer = ReportWriter("ssh_local")
        writer.write({"local_tools": local.results})
        return

    if not args.host:
        print("[!] Geef --host mee voor SSH of --whois <target> voor lokale tools.")
        return

    commands = args.commands if args.commands else ["id", "uname -a", "uptime"]
    client = SSHClient(
        host=args.host,
        port=args.port,
        username=args.user,
        key_path=args.key,
        password=args.password,
    )
    if client.connect():
        for cmd in commands:
            client.execute(cmd)
        client.close()
        client.save_report()
