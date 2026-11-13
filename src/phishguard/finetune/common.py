"""Pinned inputs, bounded source downloads and a fixed review-aware study."""

import json
import os
import ssl
import tempfile
import urllib.request
from importlib.resources import files
from pathlib import Path

import truststore

from phishguard.baseline.common import parse_json, read_bytes
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.pretrained.source import HTTPSRedirect, verify_file
from phishguard.refresh.data import FrozenStudy


class FineTuneError(ValueError):
    """Fixed public codes; no message text or arbitrary exception details."""


def resource(name):
    return json.loads(files(__package__).joinpath(name).read_text(encoding="utf-8"))


SOURCE, PROTOCOL, STUDY = (resource(n) for n in ("source.json", "protocol.json", "study.json"))
SOURCE_SHA256, PROTOCOL_SHA256, STUDY_SHA256 = (
    digest(json_bytes(x)) for x in (SOURCE, PROTOCOL, STUDY)
)
SOURCE_DIRECTORY = Path("models/finetune-source/google-" + SOURCE["revision"][:8])
MODEL_DIRECTORY = Path("models/finetuned-v1")
SELECTION_REFERENCE = Path("data/manifests/finetuned-v1-selection.json")
MODEL_ID = "phishguard-bert-tiny-v1"


def verify_source(directory):
    for name, meta in SOURCE["files"].items():
        verify_file(directory / name, meta)
    if parse_json(read_bytes(directory / "config.json")) != SOURCE["configuration"]:
        raise FineTuneError("source_configuration_mismatch")
    return {"status": "verified", "model_id": SOURCE["model_id"], "revision": SOURCE["revision"]}


def fetch(directory):
    directory.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(
        HTTPSRedirect(),
        urllib.request.HTTPSHandler(context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)),
    )
    for name, meta in SOURCE["files"].items():
        target = directory / name
        if target.exists():
            verify_file(target, meta)
            continue
        temporary = None
        try:
            request = urllib.request.Request(
                f"{SOURCE['homepage']}/resolve/{SOURCE['revision']}/{name}",
                headers={"User-Agent": "PhishGuard/0.5.0"},
            )
            with opener.open(request, timeout=60) as response:
                if not response.url.startswith("https://"):
                    raise FineTuneError("insecure_source_redirect")
                with tempfile.NamedTemporaryFile(
                    dir=directory, prefix=".download-", delete=False
                ) as stream:
                    temporary = Path(stream.name)
                    remaining = meta["bytes"] + 1
                    while remaining and (chunk := response.read(min(1024 * 1024, remaining))):
                        stream.write(chunk)
                        remaining -= len(chunk)
            verify_file(temporary, meta)
            os.link(temporary, target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return verify_source(directory)


def study(directory, reference):
    frozen = FrozenStudy(directory, reference)
    if frozen.sha256 != STUDY["dataset_sha256"]:
        raise FineTuneError("finetuning_dataset_mismatch")
    actual = [
        g
        for g in frozen.manifest["groups"]
        if g["split"] in {"test", "challenge"} and set(g["members"]) & set(STUDY["reviewed_ids"])
    ]
    if actual != STUDY["excluded_benchmark_groups"]:
        raise FineTuneError("review_registry_mismatch")
    return frozen


def partition(frozen, name):
    rows = frozen.load(name)
    if name in {"test", "challenge"}:
        excluded = {g["group_id"] for g in STUDY["excluded_benchmark_groups"]}
        rows = [r for r in rows if r.group_id not in excluded]
        if any(r.example_id in STUDY["reviewed_ids"] for r in rows):
            raise FineTuneError("reviewed_example_in_benchmark")
    if len(rows) != STUDY["expected_rows"][name]:
        raise FineTuneError("finetuning_partition_count_mismatch")
    return rows
