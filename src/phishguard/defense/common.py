"""Fixed defense identity; errors contain codes rather than research text."""

import json
from importlib.resources import files
from pathlib import Path

from phishguard.baseline.common import code_revision, environment
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.evasion.common import PROTOCOL_SHA256 as EVASION_SHA256
from phishguard.finetune.common import STUDY_SHA256

PROTOCOL = json.loads(files(__package__).joinpath("protocol.json").read_text(encoding="utf-8"))
PROTOCOL_SHA256 = digest(json_bytes(PROTOCOL))
MODEL_ID = "phishguard-bert-tiny-defense-v1"
MODEL = Path("models/defended-v1")
AUGMENTATION = Path("artifacts/defense-augmentation-v1")
AUGMENTATION_REFERENCE = Path("data/manifests/defense-augmentation-v1.json")
REVIEW_REFERENCE = Path("docs/reports/defense-preflight-review.json")
SELECTION_REFERENCE = Path("data/manifests/defended-v1-selection.json")
FRESH_BANK = Path("artifacts/defense-fresh-bank-v1")
FRESH_REFERENCE = Path("data/manifests/defense-fresh-bank-v1.json")


class DefenseError(ValueError):
    """Fixed public code."""


def identity():
    return {
        "report_version": "1.0",
        "protocol": PROTOCOL,
        "protocol_sha256": PROTOCOL_SHA256,
        "stage6_protocol_sha256": EVASION_SHA256,
        "stage5_study_sha256": STUDY_SHA256,
        "code": code_revision(),
        "environment": environment(),
        "reserve_rows_scored": 0,
    }
