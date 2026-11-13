"""Prepare external cohorts before scores; keep every detected relative in one cohort."""

from collections import Counter, defaultdict
from pathlib import Path

from phishguard.audit.common import PROTOCOL, PROTOCOL_SHA256, SOURCE, SOURCE_SHA256, AuditError
from phishguard.audit.mime import english, extract, messages
from phishguard.audit.similarity import relations
from phishguard.baseline.common import parse_json, read_bytes
from phishguard.baseline.data import FrozenDataset
from phishguard.baseline.preprocessing import preprocess
from phishguard.contracts import EmailExample
from phishguard.datasets.grouping import canonical, group_identifier
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import checked_bytes, digest
from phishguard.validation import validate_json


def cohort_stats(records):
    return {
        "rows": len(records),
        "groups": len({r.group_id for r in records}),
        "labels": dict(sorted(Counter(r.label for r in records).items())),
        "sources": dict(sorted(Counter(r.source_id for r in records).items())),
    }


def partition(records, components):
    by_id = {r.example_id: r for r in records}
    totals = Counter(r.label for r in records)
    ratios = {
        "audit": PROTOCOL["external_split"]["audit"],
        "reserve": PROTOCOL["external_split"]["reserve"],
    }
    counts = {cohort: Counter() for cohort in ratios}
    groups = [(group_identifier(ids), ids) for ids in components]
    seed = PROTOCOL["external_split"]["seed"]
    groups.sort(key=lambda g: (-len(g[1]), digest(f"{seed}:{g[0]}".encode())))
    assigned, membership = {cohort: [] for cohort in ratios}, []
    for gid, ids in groups:
        labels = Counter(by_id[rid].label for rid in ids)

        def cost(cohort, labels=labels):
            return sum(
                (
                    (counts[cohort][label] + n - totals[label] * ratios[cohort]) ** 2
                    - (counts[cohort][label] - totals[label] * ratios[cohort]) ** 2
                )
                / max(1, totals[label] * ratios[cohort])
                for label, n in labels.items()
            )

        cohort = min(ratios, key=lambda key: (cost(key), key))
        counts[cohort].update(labels)
        assigned[cohort].extend(
            by_id[rid].model_copy(
                update={"group_id": gid, "split": "test" if cohort == "audit" else "unassigned"}
            )
            for rid in ids
        )
        membership.append({"group_id": gid, "cohort": cohort, "members": sorted(ids)})
    if any(set(counts[cohort]) != {"phishing", "legitimate"} for cohort in ratios):
        raise AuditError("insufficient_external_class_groups")
    return {
        key: sorted(values, key=lambda r: r.example_id) for key, values in assigned.items()
    }, membership


def prepare(cache: Path, internal: Path, reference: Path, output: Path) -> dict:
    if output.exists():
        raise AuditError("output_already_exists")
    dataset = FrozenDataset(internal, reference)
    if dataset.sha256 != PROTOCOL["internal_manifest_sha256"]:
        raise AuditError("internal_dataset_mismatch")
    original = [r for split in ("train", "validation", "test") for r in dataset.load(split)]
    records, exclusions, counters = [], [], {}
    for name, metadata in SOURCE["files"].items():
        checked_bytes(cache / name, metadata)
        if metadata["kind"] == "terms":
            continue
        counts = Counter()
        for index, raw in messages(cache / name, metadata["kind"]):
            rid = f"external-{name.split('.')[0]}-{index:06d}"
            counts["raw_messages"] += 1
            try:
                email, diagnostics = extract(raw)
                if not english(email):
                    raise AuditError("not_confident_english")
            except AuditError as error:
                exclusions.append({"example_id": rid, "reason": str(error)})
                counts[str(error)] += 1
                continue
            counts.update(key for key, value in diagnostics.items() if value)
            counts["accepted_before_duplicates"] += 1
            records.append(
                EmailExample(
                    example_id=rid,
                    email=email,
                    label=metadata["label"],
                    source_id=metadata["source_id"],
                    source_revision=metadata["sha256"],
                    license=metadata["license"],
                    group_id="unassigned",
                )
            )
        counters[name] = dict(counts)
    duplicates = defaultdict(list)
    for record in records:
        duplicates[canonical(preprocess(record.email.text))].append(record)
    retained = []
    for values in duplicates.values():
        values.sort(key=lambda r: r.example_id)
        if len({r.label for r in values}) > 1:
            exclusions.extend(
                {"example_id": r.example_id, "reason": "conflicting_exact_labels"} for r in values
            )
        else:
            retained.append(values[0])
            exclusions.extend(
                {
                    "example_id": r.example_id,
                    "reason": "duplicate_model_input",
                    "retained_id": values[0].example_id,
                }
                for r in values[1:]
            )
    components, edges = relations(original + retained, PROTOCOL["relatedness"]["near_body_jaccard"])
    internal_ids = {r.example_id for r in original}
    excluded_ids, external_groups = set(), []
    for ids in components:
        external = set(ids) - internal_ids
        if set(ids) & internal_ids:
            excluded_ids.update(external)
        elif external:
            external_groups.append(sorted(external))
    exclusions.extend(
        {"example_id": rid, "reason": "related_to_internal_corpus"} for rid in sorted(excluded_ids)
    )
    retained = [r for r in retained if r.example_id not in excluded_ids]
    cohorts, membership = partition(retained, external_groups)
    label_review = {
        label: sorted(
            (r.example_id for r in cohorts["audit"] if r.label == label),
            key=lambda rid: digest(f"stage4a-label-review:{rid}".encode()),
        )[: PROTOCOL["audit_label_review"]["per_label"]]
        for label in ("legitimate", "phishing")
    }
    manifest = {
        "format_version": "1.0",
        "source_sha256": SOURCE_SHA256,
        "protocol_sha256": PROTOCOL_SHA256,
        "internal_manifest_sha256": dataset.sha256,
        "source": SOURCE,
        "protocol": PROTOCOL,
        "ingestion": counters,
        "exclusions": sorted(exclusions, key=lambda e: e["example_id"]),
        "exclusion_counts": dict(Counter(e["reason"] for e in exclusions)),
        "partitions": {key: cohort_stats(values) for key, values in cohorts.items()},
        "groups": sorted(membership, key=lambda g: g["group_id"]),
        "cross_source_relation_edges": sum(
            (a in internal_ids) != (b in internal_ids) for a, b, _, _ in edges
        ),
        "label_review_ids": label_review,
        "reserve_scored": False,
        "files": {},
    }
    output.mkdir(parents=True, exist_ok=False)
    for name, values in cohorts.items():
        payload = b"".join((row.model_dump_json() + "\n").encode() for row in values)
        (output / f"{name}.jsonl").write_bytes(payload)
        manifest["files"][f"{name}.jsonl"] = {"bytes": len(payload), "sha256": digest(payload)}
    (output / "manifest.json").write_bytes(json_bytes(manifest))
    return manifest


def load_audit(directory: Path, reference: Path):
    payload = read_bytes(directory / "manifest.json")
    if payload != read_bytes(reference):
        raise AuditError("external_manifest_mismatch")
    manifest = parse_json(payload)
    if (
        manifest.get("source_sha256") != SOURCE_SHA256
        or manifest.get("protocol_sha256") != PROTOCOL_SHA256
        or manifest.get("internal_manifest_sha256") != PROTOCOL["internal_manifest_sha256"]
        or manifest.get("source") != SOURCE
        or manifest.get("protocol") != PROTOCOL
    ):
        raise AuditError("external_protocol_mismatch")
    try:
        members, used_groups = {}, set()
        for group in manifest["groups"]:
            if group["cohort"] not in {"audit", "reserve"} or group["group_id"] in used_groups:
                raise AuditError("invalid_external_membership")
            used_groups.add(group["group_id"])
            for rid in group["members"]:
                if rid in members:
                    raise AuditError("invalid_external_membership")
                members[rid] = (group["group_id"], group["cohort"])
        # Intentionally never read reserve.jsonl during evaluation.
        data = checked_bytes(directory / "audit.jsonl", manifest["files"]["audit.jsonl"])
        rows = [validate_json("example", line) for line in data.splitlines()]
        expected = {rid for rid, (_, cohort) in members.items() if cohort == "audit"}
        if len(rows) != len(expected) or {r.example_id for r in rows} != expected:
            raise AuditError("invalid_external_membership")
        sources = {
            meta["source_id"]: meta for meta in SOURCE["files"].values() if "source_id" in meta
        }
        for row in rows:
            metadata = sources[row.source_id]
            if (
                row.split != "test"
                or members[row.example_id] != (row.group_id, "audit")
                or row.source_revision != metadata["sha256"]
                or row.license != metadata["license"]
                or row.label != metadata["label"]
            ):
                raise AuditError("invalid_external_membership")
        if cohort_stats(rows) != manifest["partitions"]["audit"]:
            raise AuditError("invalid_external_counts")
    except (KeyError, TypeError):
        raise AuditError("invalid_external_manifest") from None
    return rows, manifest, digest(payload)
