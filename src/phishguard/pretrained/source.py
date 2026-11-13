"""Pinned public downloads; verify every file before local-only inference."""

import hashlib
import http.client
import json
import os
import tempfile
import urllib.error
import urllib.request
from importlib.resources import files
from pathlib import Path

from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest

SOURCE = json.loads(files(__package__).joinpath("source.json").read_text(encoding="utf-8"))
PROTOCOL = json.loads(files(__package__).joinpath("protocol.json").read_text(encoding="utf-8"))
SOURCE_SHA256 = digest(json_bytes(SOURCE))
PROTOCOL_SHA256 = digest(json_bytes(PROTOCOL))
DEFAULT_MODEL = Path("models/pretrained") / ("dima806-" + SOURCE["revision"][:8])


class PretrainedError(ValueError):
    """Stable public error codes without email text or transport details."""


def verify_file(path: Path, expected: dict) -> None:
    size = 0
    hashed = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > expected["bytes"]:
                raise PretrainedError("model_integrity_mismatch")
            hashed.update(chunk)
    if size != expected["bytes"] or hashed.hexdigest() != expected["sha256"]:
        raise PretrainedError("model_integrity_mismatch")


def verify_source(directory: Path) -> dict:
    try:
        for name, expected in SOURCE["files"].items():
            verify_file(directory / name, expected)
    except FileNotFoundError:
        raise PretrainedError("model_not_downloaded") from None
    return {"status": "verified", "model_id": SOURCE["model_id"], "revision": SOURCE["revision"]}


class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith("https://"):
            raise PretrainedError("insecure_model_redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_source(directory: Path = DEFAULT_MODEL) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(HTTPSRedirect())
    for name, expected in SOURCE["files"].items():
        target = directory / name
        if target.exists():
            verify_file(target, expected)
            continue
        url = f"{SOURCE['homepage']}/resolve/{SOURCE['revision']}/{name}"
        temporary = None
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "PhishGuard-pretrained/1.0"}
            )
            with opener.open(request, timeout=60) as response:
                if not response.url.startswith("https://"):
                    raise PretrainedError("insecure_model_redirect")
                with tempfile.NamedTemporaryFile(
                    dir=directory, prefix=".download-", delete=False
                ) as stream:
                    temporary = Path(stream.name)
                    size = 0
                    while chunk := response.read(1024 * 1024):
                        size += len(chunk)
                        if size > expected["bytes"]:
                            raise PretrainedError("model_integrity_mismatch")
                        stream.write(chunk)
            verify_file(temporary, expected)
            # Atomic publication without replacing a concurrently created target.
            os.link(temporary, target)
        except (urllib.error.URLError, TimeoutError, http.client.HTTPException):
            raise PretrainedError("model_download_failed") from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return verify_source(directory)
