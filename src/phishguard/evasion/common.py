"""Fixed protocol and text-free experiment identities."""

import json
from importlib.resources import files
from pathlib import Path

from phishguard.baseline.common import code_revision, environment
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.finetune.common import STUDY_SHA256

PROTOCOL = json.loads(files(__package__).joinpath("protocol.json").read_text(encoding="utf-8"))
PROTOCOL_SHA256 = digest(json_bytes(PROTOCOL))
BANK = Path("artifacts/evasion-variants-v1")
BANK_REFERENCE = Path("data/manifests/evasion-variants-v1.json")


class EvasionError(ValueError):
    """Fixed public codes; no raw input in errors."""


def identity():
    return {
        "report_version": "1.0",
        "protocol": PROTOCOL,
        "protocol_sha256": PROTOCOL_SHA256,
        "stage5_study_sha256": STUDY_SHA256,
        "code": code_revision(),
        "environment": environment(),
        "weights_updated": False,
        "thresholds_updated": False,
        "reserve_rows_scored": 0,
    }


def lines_bytes(rows):
    return b"".join((json.dumps(r, sort_keys=True) + "\n").encode() for r in rows)
