"""Frozen sources, study protocol and verified bounded downloads."""

import json
import ssl
import urllib.error
import urllib.request
from importlib.resources import files
from pathlib import Path

import truststore

from phishguard.audit.common import AuditError
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.pretrained.source import HTTPSRedirect

SOURCE = json.loads(files(__package__).joinpath("source.json").read_text(encoding="utf-8"))
PROTOCOL = json.loads(files(__package__).joinpath("protocol.json").read_text(encoding="utf-8"))
SOURCE_SHA256 = digest(json_bytes(SOURCE))
PROTOCOL_SHA256 = digest(json_bytes(PROTOCOL))
CACHE = Path("data/raw/refresh-v1")
DATA = Path("data/processed/real-mail-v2")
REFERENCE = Path("data/manifests/real-mail-v2.json")


def verify_file(path, metadata):
    import hashlib

    hasher = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            hasher.update(block)
            size += len(block)
            if size > metadata["bytes"]:
                raise AuditError("refresh_source_integrity_mismatch")
    if size != metadata["bytes"] or hasher.hexdigest() != metadata["sha256"]:
        raise AuditError("refresh_source_integrity_mismatch")


def fetch(cache):
    cache.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(
        HTTPSRedirect(),
        urllib.request.HTTPSHandler(context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)),
    )
    for name, meta in SOURCE["files"].items():
        target = cache / name
        if target.exists():
            verify_file(target, meta)
            continue
        request = urllib.request.Request(meta["url"], headers={"User-Agent": "PhishGuard/0.4.2"})
        # Partial files are never trusted or silently reused after interruption.
        partial = cache / (name + ".partial")
        if partial.exists():
            raise AuditError("refresh_partial_already_exists")
        created = False
        try:
            with opener.open(request, timeout=60) as response, partial.open("xb") as stream:
                created = True
                if not response.url.startswith("https://"):
                    raise AuditError("insecure_source_redirect")
                remaining = meta["bytes"] + 1
                while remaining and (block := response.read(min(1024 * 1024, remaining))):
                    stream.write(block)
                    remaining -= len(block)
            verify_file(partial, meta)
            partial.rename(target)
        except (urllib.error.URLError, TimeoutError):
            raise AuditError("refresh_download_failed") from None
        finally:
            if created and partial.exists():
                partial.unlink()
    return {"status": "verified", "source_sha256": SOURCE_SHA256}
