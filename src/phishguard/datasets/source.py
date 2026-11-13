"""Fetch only the two reviewed publisher files, with pinned byte-level integrity."""

import hashlib
import json
import urllib.error
import urllib.request
from importlib.resources import files
from pathlib import Path

SOURCE = json.loads(files(__package__).joinpath("source.json").read_text(encoding="utf-8"))
DEFAULT_CACHE = Path("data/raw/ephishllm") / SOURCE["revision"]


class DatasetError(ValueError):
    """A fixed error code, never message content or untrusted exception text."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_bytes(path: Path, metadata: dict) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(metadata["bytes"] + 1)
    if len(data) != metadata["bytes"] or digest(data) != metadata["sha256"]:
        raise DatasetError("source_integrity_mismatch")
    return data


def fetch_source(cache: Path = DEFAULT_CACHE) -> dict:
    """Reuse verified cache files; never overwrite existing or corrupt files."""
    cache.mkdir(parents=True, exist_ok=True)
    for name, metadata in SOURCE["files"].items():
        target = cache / name
        if target.exists():
            checked_bytes(target, metadata)
            continue
        url = f"{SOURCE['homepage']}/resolve/{SOURCE['revision']}/{name}"
        request = urllib.request.Request(url, headers={"User-Agent": "PhishGuard-data/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                if not response.url.startswith("https://"):
                    raise DatasetError("insecure_source_redirect")
                data = response.read(metadata["bytes"] + 1)
        except (urllib.error.URLError, TimeoutError):
            raise DatasetError("source_download_failed") from None
        if len(data) != metadata["bytes"] or digest(data) != metadata["sha256"]:
            raise DatasetError("source_integrity_mismatch")
        with target.open("xb") as stream:
            stream.write(data)
    return {"status": "verified", "source_id": SOURCE["source_id"], "revision": SOURCE["revision"]}
