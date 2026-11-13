"""Fixed protocol, bounded JSON and reproducibility metadata."""

import json
import os
import platform
import subprocess
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest

PROTOCOL = json.loads(files(__package__).joinpath("protocol.json").read_text(encoding="utf-8"))
PROTOCOL_SHA256 = digest(json_bytes(PROTOCOL))
MODEL_ID = "tfidf-logistic-regression"
MAX_MODEL_BYTES = 32 * 1024 * 1024


class BaselineError(ValueError):
    """Public errors contain fixed codes only."""


def read_bytes(path: Path, limit: int = MAX_MODEL_BYTES) -> bytes:
    with path.open("rb") as stream:
        payload = stream.read(limit + 1)
    if len(payload) > limit:
        raise BaselineError("artifact_too_large")
    return payload


def parse_json(payload: bytes) -> dict:
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise BaselineError("invalid_artifact_json")
            result[key] = value
        return result

    def invalid_constant(value):
        raise BaselineError("invalid_artifact_json")

    try:
        result = json.loads(
            payload, object_pairs_hook=unique_pairs, parse_constant=invalid_constant
        )
    except (UnicodeError, ValueError, RecursionError):
        raise BaselineError("invalid_artifact_json") from None
    if not isinstance(result, dict):
        raise BaselineError("invalid_artifact_json")
    return result


def environment() -> dict:
    return {
        "python": platform.python_version(),
        "os": platform.system(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "requested_numeric_threads": PROTOCOL["threads"],
        "packages": {
            name: version(name)
            for name in ("phishguard", "scikit-learn", "numpy", "scipy", "threadpoolctl")
        },
    }


def code_revision() -> dict:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5, check=True
        ).stdout.strip()
        dirty = (
            subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            ).stdout
            != ""
        )
        return {"commit": head, "working_tree_dirty": dirty}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "working_tree_dirty": None}
