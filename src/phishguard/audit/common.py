"""Pinned audit identity, bounded publisher downloads and explicit errors."""

import json
import ssl
import urllib.error
import urllib.request
from importlib.resources import files
from pathlib import Path

import truststore

from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import checked_bytes, digest
from phishguard.pretrained.source import HTTPSRedirect

SOURCE = json.loads(files(__package__).joinpath("source.json").read_text(encoding="utf-8"))
PROTOCOL = json.loads(files(__package__).joinpath("protocol.json").read_text(encoding="utf-8"))
SOURCE_SHA256 = digest(json_bytes(SOURCE))
PROTOCOL_SHA256 = digest(json_bytes(PROTOCOL))
DEFAULT_CACHE = Path("data/raw/external-mail-v1")
DEFAULT_DATASET = Path("data/processed/external-mail-v1")
DEFAULT_REFERENCE = Path("data/manifests/external-mail-v1.json")


class AuditError(ValueError):
    """Fixed codes only; never include email text in public errors."""


def fetch(cache: Path) -> dict:
    cache.mkdir(parents=True, exist_ok=True)
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    opener = urllib.request.build_opener(
        HTTPSRedirect(), urllib.request.HTTPSHandler(context=context)
    )
    for name, metadata in SOURCE["files"].items():
        target = cache / name
        if target.exists():
            checked_bytes(target, metadata)
            continue
        request = urllib.request.Request(
            metadata["url"], headers={"User-Agent": "PhishGuard-audit/1"}
        )
        try:
            with opener.open(request, timeout=60) as response:
                if not response.url.startswith("https://"):
                    raise AuditError("insecure_source_redirect")
                payload = response.read(metadata["bytes"] + 1)
        except (urllib.error.URLError, TimeoutError):
            raise AuditError("external_download_failed") from None
        if len(payload) != metadata["bytes"] or digest(payload) != metadata["sha256"]:
            raise AuditError("external_source_integrity_mismatch")
        with target.open("xb") as stream:
            stream.write(payload)
    return {"status": "verified", "source_sha256": SOURCE_SHA256}
