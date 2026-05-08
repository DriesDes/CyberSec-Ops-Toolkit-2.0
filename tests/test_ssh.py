"""Kleine tests voor SSH-hulpfuncties zonder echte server."""

from types import SimpleNamespace

from ops.ssh import LocalTools, SSHClient


def test_local_whois_uses_subprocess(monkeypatch):
    def fake_run(cmd, capture_output, text, timeout):
        return SimpleNamespace(stdout="Domain Name: EXAMPLE.COM", stderr="", returncode=0)

    monkeypatch.setattr("ops.ssh.subprocess.run", fake_run)
    tools = LocalTools()
    result = tools.run_whois("example.com")

    assert result["return_code"] == 0
    assert "EXAMPLE.COM" in result["stdout"]


def test_execute_without_connection_returns_error():
    client = SSHClient(host="127.0.0.1", port=22, username="student")
    result = client.execute("id")

    assert result["error"] == "Not connected"
