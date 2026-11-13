"""Prepare immutable, grouped splits from the reviewed E-PhishLLM revision."""

import json
from collections import Counter, defaultdict
from pathlib import Path

from pydantic import ValidationError

from phishguard.contracts import EmailExample, EmailInput
from phishguard.datasets.grouping import canonical, group_identifier, related_components
from phishguard.datasets.source import SOURCE, DatasetError, checked_bytes, digest

PIPELINE_VERSION = "ephishllm-v1"
SPLITS = {"train": 0.70, "validation": 0.15, "test": 0.15}
LABELS = ("legitimate", "phishing")
GROUPING = {
    "exact": "NFKC, casefold, whitespace collapse; subject plus body",
    "subject": "same normalized subject, at least 15 characters and 3 words",
    "body": "mask placeholders, URLs, email addresses and digits; at least 10 words",
    "near_body": "word-trigram set Jaccard >= 0.90, exact prefix-index search",
    "closure": "transitive components including declared parent links",
}


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode()


def ingest(rows: list) -> tuple[list[EmailExample], dict]:
    """Keep publisher-English text verbatim; record exclusions by row index only."""
    if not isinstance(rows, list):
        raise DatasetError("invalid_source_shape")
    records = []
    exclusions = []
    languages = Counter()
    for index, row in enumerate(rows):
        reason = None
        if (
            not isinstance(row, dict)
            or set(row) != {"Subject", "Body", "Language", "type"}
            or type(row["type"]) is not int
            or row["type"] not in (0, 1)
            or not isinstance(row["Language"], str)
        ):
            reason = "invalid_row_schema"
        else:
            languages[row["Language"]] += 1
            if row["Language"] != SOURCE["language_filter"]:
                reason = "other_language"
            else:
                try:
                    email = EmailInput(subject=row["Subject"], body=row["Body"])
                    record = EmailExample(
                        example_id=f"ephishllm-{SOURCE['revision'][:8]}-{index:06d}",
                        email=email,
                        label=SOURCE["label_mapping"][str(row["type"])],
                        source_id=SOURCE["source_id"],
                        source_revision=SOURCE["revision"],
                        license=SOURCE["license"],
                        group_id="unassigned",
                    )
                    records.append(record)
                except ValidationError:
                    reason = "invalid_email"
        if reason:
            exclusions.append({"source_row": index, "reason": reason})
    return records, {
        "source_rows": len(rows),
        "language_counts": dict(sorted(languages.items())),
        "accepted_before_deduplication": len(records),
        "ingestion_exclusion_counts": dict(Counter(e["reason"] for e in exclusions)),
        "ingestion_exclusions": exclusions,
    }


def deduplicate(records: list[EmailExample]) -> tuple[list[EmailExample], list[dict]]:
    exact = defaultdict(list)
    for record in records:
        exact[canonical(record.email.text)].append(record)
    retained, excluded = [], []
    for members in exact.values():
        members.sort(key=lambda r: r.example_id)
        if len({r.label for r in members}) > 1:
            excluded.extend(
                {"example_id": r.example_id, "reason": "conflicting_exact_labels"} for r in members
            )
        else:
            retained.append(members[0])
            excluded.extend(
                {
                    "example_id": r.example_id,
                    "reason": "exact_duplicate",
                    "retained_id": members[0].example_id,
                }
                for r in members[1:]
            )
    return sorted(retained, key=lambda r: r.example_id), sorted(
        excluded, key=lambda item: item["example_id"]
    )


def assign_splits(records: list[EmailExample], seed: int = 42) -> list[EmailExample]:
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise DatasetError("invalid_seed")
    components = related_components(records)
    by_id = {r.example_id: r for r in records}
    totals = Counter(r.label for r in records)
    if any(totals[label] < 3 for label in LABELS) or len(components) < 3:
        raise DatasetError("insufficient_independent_groups")
    groups = [(group_identifier(members), members) for members in components]
    groups.sort(key=lambda g: (-len(g[1]), digest(f"{seed}:{g[0]}".encode())))
    counts = {split: Counter() for split in SPLITS}
    assigned = []
    for gid, members in groups:
        group_counts = Counter(by_id[rid].label for rid in members)

        def cost(split, group_counts=group_counts):
            # Change in class-wise squared deviation, weighted by target size.
            return sum(
                (
                    (counts[split][label] + group_counts[label] - totals[label] * ratio) ** 2
                    - (counts[split][label] - totals[label] * ratio) ** 2
                )
                / max(1, totals[label] * ratio)
                for label in LABELS
                for ratio in [SPLITS[split]]
            )

        chosen = min(SPLITS, key=lambda split: (cost(split), split))
        counts[chosen].update(group_counts)
        assigned.extend(
            by_id[rid].model_copy(update={"group_id": gid, "split": chosen}) for rid in members
        )
    if any(counts[s][label] == 0 for s in SPLITS for label in LABELS):
        raise DatasetError("insufficient_class_coverage")
    return sorted(assigned, key=lambda r: r.example_id)


def membership(records: list[EmailExample]) -> list[dict]:
    grouped = defaultdict(list)
    for record in records:
        grouped[record.group_id].append(record)
    result = []
    for gid, values in sorted(grouped.items()):
        splits = {r.split for r in values}
        if len(splits) != 1:
            raise DatasetError("group_crosses_splits")
        result.append(
            {
                "group_id": gid,
                "split": values[0].split,
                "members": sorted(r.example_id for r in values),
            }
        )
    return result


def partition_stats(records: list[EmailExample]) -> dict:
    return {
        split: {
            "rows": sum(r.split == split for r in records),
            "groups": len({r.group_id for r in records if r.split == split}),
            "labels": {
                label: sum(r.split == split and r.label == label for r in records)
                for label in LABELS
            },
        }
        for split in SPLITS
    }


def prepare_source(source: Path, output: Path, seed: int = 42) -> dict:
    if output.exists():
        raise DatasetError("output_already_exists")
    data = checked_bytes(source, SOURCE["files"]["ephishLLM.json"])
    records, report = ingest(json.loads(data))
    records, exclusions = deduplicate(records)
    records = assign_splits(records, seed)
    report["deduplication_exclusions"] = exclusions
    report["deduplication_exclusion_counts"] = dict(Counter(e["reason"] for e in exclusions))
    report["retained_rows"] = len(records)
    report["largest_group"] = max(len(g["members"]) for g in membership(records))
    report["placeholder_rows_by_label"] = {
        label: sum(r.label == label and "<<" in r.email.text for r in records) for label in LABELS
    }
    manifest = {
        "format_version": "1.0",
        "pipeline_version": PIPELINE_VERSION,
        "source": SOURCE,
        "seed": seed,
        "target_ratios": SPLITS,
        "grouping": GROUPING,
        "report": report,
        "partitions": partition_stats(records),
        "groups": membership(records),
        "files": {},
    }
    # An incomplete directory has no final manifest and cannot pass verification.
    output.mkdir(parents=True, exist_ok=False)
    for split in SPLITS:
        payload = b"".join(
            (r.model_dump_json() + "\n").encode("utf-8") for r in records if r.split == split
        )
        name = f"{split}.jsonl"
        (output / name).write_bytes(payload)
        manifest["files"][name] = {"sha256": digest(payload), "bytes": len(payload)}
    (output / "manifest.json").write_bytes(json_bytes(manifest))
    return manifest
