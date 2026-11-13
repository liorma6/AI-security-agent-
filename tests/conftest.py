import json
from pathlib import Path

import pytest

from phishguard.contracts import EmailExample, EmailInput
from phishguard.datasets.preparation import (
    GROUPING,
    PIPELINE_VERSION,
    SPLITS,
    json_bytes,
    membership,
    partition_stats,
)
from phishguard.datasets.source import SOURCE, digest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_data():
    def load(name):
        return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))

    return load


@pytest.fixture
def corpus():
    partitions = {}
    for split, tag, count in [
        ("train", "alpha", 4),
        ("validation", "bravo", 2),
        ("test", "charlie", 2),
    ]:
        records = []
        for label in ("legitimate", "phishing"):
            for index in range(count):
                rid = f"{split}-{label}-{index}"
                signal = (
                    "agenda collaboration workshop"
                    if label == "legitimate"
                    else "verify password urgent"
                )
                extra = "heldoutonlytoken" if split == "validation" else ""
                marker = "<<infected_payload>>" if label == "phishing" else ""
                body = f"{signal} {tag}{chr(97 + index)} {extra} {marker}"
                records.append(
                    EmailExample(
                        example_id=rid,
                        email=EmailInput(body=body),
                        label=label,
                        source_id=SOURCE["source_id"],
                        source_revision=SOURCE["revision"],
                        license=SOURCE["license"],
                        group_id=f"group-{rid}",
                        split=split,
                    )
                )
        partitions[split] = records
    return partitions


@pytest.fixture
def prepared(tmp_path, corpus):
    directory = tmp_path / "dataset"
    directory.mkdir()
    records = [r for values in corpus.values() for r in values]
    manifest = {
        "format_version": "1.0",
        "pipeline_version": PIPELINE_VERSION,
        "source": SOURCE,
        "target_ratios": SPLITS,
        "grouping": GROUPING,
        "groups": membership(records),
        "partitions": partition_stats(records),
        "files": {},
    }
    for split, values in corpus.items():
        payload = b"".join((r.model_dump_json() + "\n").encode() for r in values)
        name = f"{split}.jsonl"
        (directory / name).write_bytes(payload)
        manifest["files"][name] = {"bytes": len(payload), "sha256": digest(payload)}
    payload = json_bytes(manifest)
    (directory / "manifest.json").write_bytes(payload)
    reference = tmp_path / "frozen.json"
    reference.write_bytes(payload)
    return directory, reference
