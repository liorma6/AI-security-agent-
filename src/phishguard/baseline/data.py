"""Read requested frozen partitions only; training never opens test.jsonl."""

from collections import Counter
from pathlib import Path

from phishguard.baseline.common import BaselineError, parse_json, read_bytes
from phishguard.contracts import EmailExample
from phishguard.datasets.preparation import GROUPING, PIPELINE_VERSION, SPLITS
from phishguard.datasets.source import SOURCE, digest
from phishguard.validation import ContractError, validate_json


class FrozenDataset:
    def __init__(self, directory: Path, reference: Path):
        self.directory = directory
        payload = read_bytes(directory / "manifest.json")
        if payload != read_bytes(reference):
            raise BaselineError("frozen_manifest_mismatch")
        self.sha256 = digest(payload)
        self.manifest = parse_json(payload)
        try:
            if (
                self.manifest["format_version"] != "1.0"
                or self.manifest["pipeline_version"] != PIPELINE_VERSION
                or self.manifest["source"] != SOURCE
                or self.manifest["grouping"] != GROUPING
                or self.manifest["target_ratios"] != SPLITS
            ):
                raise BaselineError("dataset_manifest_invalid")
            self.members = {}
            for group in self.manifest["groups"]:
                for rid in group["members"]:
                    if rid in self.members or group["split"] not in SPLITS:
                        raise BaselineError("dataset_manifest_invalid")
                    self.members[rid] = (group["group_id"], group["split"])
        except (KeyError, TypeError):
            raise BaselineError("dataset_manifest_invalid") from None

    def load(self, split: str) -> list[EmailExample]:
        if split not in SPLITS:
            raise BaselineError("invalid_partition")
        name = f"{split}.jsonl"
        payload = read_bytes(self.directory / name)
        try:
            if self.manifest["files"][name] != {"sha256": digest(payload), "bytes": len(payload)}:
                raise BaselineError("partition_integrity_mismatch")
            records = [validate_json("example", line) for line in payload.splitlines()]
            seen = set()
            for record in records:
                if (
                    record.split != split
                    or record.example_id in seen
                    or self.members.get(record.example_id) != (record.group_id, split)
                    or record.source_id != SOURCE["source_id"]
                    or record.source_revision != SOURCE["revision"]
                    or record.license != SOURCE["license"]
                ):
                    raise BaselineError("record_membership_mismatch")
                seen.add(record.example_id)
            if seen != {rid for rid, (_, s) in self.members.items() if s == split}:
                raise BaselineError("record_membership_mismatch")
            labels = Counter(r.label for r in records)
            expected = self.manifest["partitions"][split]
            if (
                len(records) != expected["rows"]
                or labels != expected["labels"]
                or len({r.group_id for r in records}) != expected["groups"]
            ):
                raise BaselineError("partition_counts_mismatch")
        except (KeyError, TypeError, ContractError):
            raise BaselineError("invalid_dataset_artifact") from None
        return records
