import json
import subprocess
import sys
from pathlib import Path

from phishguard.validation import MAX_JSON_BYTES

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*arguments, data=None):
    return subprocess.run(
        [sys.executable, "-m", "phishguard", *arguments],
        input=data,
        capture_output=True,
        cwd=ROOT,
        timeout=15,
    )


def test_cli_accepts_file_without_echoing_message():
    result = run_cli("validate", "email", "--file", "tests/fixtures/email.json")
    assert result.returncode == 0
    assert not result.stderr
    assert json.loads(result.stdout) == {
        "status": "valid",
        "contract": "email",
        "schema_version": "1.0",
    }
    assert b"Workshop" not in result.stdout


def test_cli_stdin_preserves_privacy_for_invalid_input():
    marker = "PRIVATE-STDIN-MARKER"
    data = json.dumps({"body": marker, marker: True}).encode()
    result = run_cli("validate", "email", "--file", "-", data=data)
    assert result.returncode == 1
    assert not result.stdout
    assert json.loads(result.stderr)["status"] == "invalid"
    assert marker.encode() not in result.stderr
    assert b"Traceback" not in result.stderr


def test_cli_json_errors_do_not_echo_payload():
    result = run_cli("validate", "email", "--file", "-", data=b"{PRIVATE-JSON-MARKER")
    assert result.returncode == 1
    assert json.loads(result.stderr)["issues"][0]["code"] == "invalid_json"
    assert b"PRIVATE-JSON-MARKER" not in result.stderr


def test_cli_unreadable_file_has_explicit_error(tmp_path):
    result = run_cli("validate", "email", "--file", str(tmp_path / "PRIVATE-PATH"))
    assert result.returncode == 2
    assert json.loads(result.stderr) == {"status": "error", "code": "input_unreadable"}
    assert b"PRIVATE-PATH" not in result.stderr


def test_cli_rejects_oversized_file(tmp_path):
    path = tmp_path / "oversized.json"
    path.write_bytes(b" " * (MAX_JSON_BYTES + 1))
    result = run_cli("validate", "email", "--file", str(path))
    assert result.returncode == 1
    assert json.loads(result.stderr)["issues"][0]["code"] == "input_too_large"


def test_cli_schema_and_version():
    schema = run_cli("schema", "prediction")
    assert schema.returncode == 0
    assert json.loads(schema.stdout)["discriminator"]["propertyName"] == "status"
    version = run_cli("--version")
    assert version.returncode == 0
    assert version.stdout.strip() == b"PhishGuard 0.4.1"
