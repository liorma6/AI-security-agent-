"""Independently check frozen output integrity, membership and leakage rules."""

import json
from pathlib import Path

from phishguard.contracts import EmailExample
from phishguard.datasets.grouping import canonical, related_components
from phishguard.datasets.preparation import (
    GROUPING,
    LABELS,
    PIPELINE_VERSION,
    SPLITS,
    membership,
    partition_stats,
)
from phishguard.datasets.source import SOURCE, DatasetError, digest
from phishguard.validation import ContractError, validate_json

MAX_ARTIFACT_BYTES = 64 * 1024 * 1024


def bounded_read(path: Path) -> bytes:
    with path.open("rb") as stream:
        payload = stream.read(MAX_ARTIFACT_BYTES + 1)
    if len(payload) > MAX_ARTIFACT_BYTES:
        raise DatasetError("artifact_too_large")
    return payload


def validate_separation(records: list[EmailExample]) -> None:
    if any(r.split not in SPLITS for r in records):
        raise DatasetError("unassigned_split")
    membership(records)
    by_id = {r.example_id: r for r in records}
    if len(by_id) != len(records):
        raise DatasetError("duplicate_example_id")
    exact = set()
    for record in records:
        key = canonical(record.email.text)
        if key in exact:
            raise DatasetError("duplicate_text")
        exact.add(key)
    for component in related_components(records):
        if len({by_id[rid].group_id for rid in component}) != 1:
            raise DatasetError("related_examples_in_different_groups")
    stats = partition_stats(records)
    if any(stats[s]["labels"][label] == 0 for s in SPLITS for label in LABELS):
        raise DatasetError("insufficient_class_coverage")


def verify_dataset(directory: Path, reference: Path | None = None) -> dict:
    payload = bounded_read(directory / "manifest.json")
    if reference is not None and payload != bounded_read(reference):
        raise DatasetError("frozen_manifest_mismatch")
    try:
        manifest = json.loads(payload)
        if (
            manifest["format_version"] != "1.0"
            or manifest["pipeline_version"] != PIPELINE_VERSION
            or manifest["source"] != SOURCE
            or manifest["grouping"] != GROUPING
            or manifest["target_ratios"] != SPLITS
            or type(manifest["seed"]) is not int
            or not 0 <= manifest["seed"] <= 2**32 - 1
            or set(manifest["files"]) != {f"{s}.jsonl" for s in SPLITS}
        ):
            raise DatasetError("manifest_contract_mismatch")
        records = []
        for split in SPLITS:
            name = f"{split}.jsonl"
            data = bounded_read(directory / name)
            if manifest["files"][name] != {"sha256": digest(data), "bytes": len(data)}:
                raise DatasetError("partition_integrity_mismatch")
            for line in data.splitlines():
                record = validate_json("example", line)
                if (
                    record.split != split
                    or record.source_id != SOURCE["source_id"]
                    or record.source_revision != SOURCE["revision"]
                    or record.license != SOURCE["license"]
                ):
                    raise DatasetError("record_provenance_or_split_mismatch")
                records.append(record)
        validate_separation(records)
        if manifest["groups"] != membership(records):
            raise DatasetError("membership_mismatch")
        if manifest["partitions"] != partition_stats(records):
            raise DatasetError("partition_counts_mismatch")
        if manifest["report"]["retained_rows"] != len(records):
            raise DatasetError("retained_count_mismatch")
    except (KeyError, TypeError, json.JSONDecodeError, UnicodeError, ContractError):
        raise DatasetError("invalid_dataset_artifact") from None
    return {
        "status": "verified",
        "reference_checked": reference is not None,
        "rows": len(records),
        "groups": len(manifest["groups"]),
        "partitions": manifest["partitions"],
        "manifest_sha256": digest(payload),
    }
