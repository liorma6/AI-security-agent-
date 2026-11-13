"""Prepare a real-mail training study while protecting all earlier held-out groups."""

import csv
from collections import Counter, defaultdict
from pathlib import Path

from pydantic import ValidationError

from phishguard.audit.common import SOURCE as AUDIT_SOURCE
from phishguard.audit.common import AuditError
from phishguard.audit.data import cohort_stats, load_audit
from phishguard.audit.mime import english, messages
from phishguard.audit.similarity import relations
from phishguard.baseline.common import BaselineError, parse_json, read_bytes
from phishguard.baseline.data import FrozenDataset
from phishguard.baseline.preprocessing import preprocess
from phishguard.contracts import EmailExample, EmailInput
from phishguard.datasets.grouping import canonical, group_identifier
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import checked_bytes, digest
from phishguard.refresh.common import PROTOCOL, PROTOCOL_SHA256, SOURCE, SOURCE_SHA256, verify_file
from phishguard.refresh.text import clean_text, extract
from phishguard.validation import validate_json


def record(rid, email, label, source, revision, group="unassigned", license="CC-BY-4.0"):
    return EmailExample(
        example_id=rid,
        email=email,
        label=label,
        source_id=source,
        source_revision=revision,
        license=license,
        group_id=group,
    )


def sample(rows, limit):
    return sorted(rows, key=lambda r: digest(f"refresh-sample:{r.example_id}".encode()))[:limit]


def csv_rows(path):
    previous = csv.field_size_limit(1024 * 1024)
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            yield from csv.DictReader(stream)
    finally:
        csv.field_size_limit(previous)


def meajor(cache):
    name = "meajor_cleaned_preprocessed.csv"
    verify_file(cache / name, SOURCE["files"][name])
    selected = defaultdict(list)
    counts = Counter()
    for index, row in enumerate(csv_rows(cache / name)):
        counts["raw_rows"] += 1
        source = row.get("source")
        if source not in PROTOCOL["meajor_sources"] or row.get("label") != PROTOCOL["meajor_label"]:
            counts["non_ham_or_unknown_source"] += 1
            continue
        if set((row.get("language") or "").split(";")) != {"en"}:
            counts["publisher_not_english"] += 1
            continue
        try:
            email, _ = clean_text(EmailInput(subject=row["subject"], body=row["body"]))
            preprocess(email.text)
        except (ValidationError, BaselineError, AuditError):
            counts["invalid_text"] += 1
            continue
        selected[source].append(
            record(
                f"meajor-{source}-{index:06d}",
                email,
                "legitimate",
                f"meajor-{source}",
                SOURCE["files"][name]["sha256"],
            )
        )
    retained = []
    for _source, rows in sorted(selected.items()):
        chosen = sample(rows, PROTOCOL["meajor_max_per_source"])
        counts["outside_fixed_sample"] += len(rows) - len(chosen)
        for row in chosen:
            if english(row.email):
                retained.append(row)
            else:
                counts["language_filter"] += 1
    counts["selected"] = len(retained)
    return retained, dict(counts)


def nazario(cache):
    name = "nazario-2007.mbox"
    verify_file(cache / name, SOURCE["files"][name])
    rows, counts = [], Counter()
    for index, raw in messages(cache / name, "mbox"):
        counts["raw_rows"] += 1
        try:
            email, flags = extract(raw)
            if not english(email):
                raise AuditError("language_filter")
        except AuditError as error:
            counts[str(error)] += 1
            continue
        counts.update(k for k, v in flags.items() if v)
        rows.append(
            record(
                f"nazario-2007-{index:06d}",
                email,
                "phishing",
                "nazario-2007",
                SOURCE["files"][name]["sha256"],
            )
        )
    chosen = sample(rows, PROTOCOL["nazario_max"])
    counts["outside_fixed_sample"] = len(rows) - len(chosen)
    counts["selected"] = len(chosen)
    return chosen, dict(counts)


def challenge(cache):
    names = ("Phishing_validation_emails_v3.csv", "phishing_v3_metadata.csv")
    for name in names:
        verify_file(cache / name, SOURCE["files"][name])
    with (cache / names[0]).open(encoding="utf-8-sig", newline="") as first:
        rows = list(csv.DictReader(first))
    with (cache / names[1]).open(encoding="utf-8-sig", newline="") as second:
        metadata = list(csv.DictReader(second))
    if len(rows) != len(metadata) or len(rows) != 2000:
        raise AuditError("challenge_metadata_mismatch")
    result, origins = [], {}
    labels = {"Safe Email": "legitimate", "Phishing Email": "phishing"}
    for index, (row, meta) in enumerate(zip(rows, metadata, strict=True), 1):
        if (
            meta["record_id"] != str(index)
            or meta["email_type"] != row["Email Type"]
            or meta["source_category"] not in {"original_v1", "generated_v3"}
            or (meta["source_category"] == "original_v1") != (meta["template_id"] == "ORIGINAL")
        ):
            raise AuditError("challenge_metadata_mismatch")
        rid = f"zenodo-v3-{index:04d}"
        group = rid if meta["template_id"] == "ORIGINAL" else meta["template_id"]
        email = EmailInput(body=row["Email Text"])
        preprocess(email.text)
        result.append(
            record(
                rid,
                email,
                labels[row["Email Type"]],
                "zenodo-v3-" + meta["source_category"],
                SOURCE["files"][names[0]]["sha256"],
                "zenodo-template-" + group,
            )
        )
        origins[rid] = meta["source_category"]
    return result, origins


def old_audit(directory, reference, raw_cache):
    rows, manifest, sha = load_audit(directory, reference)
    if sha != PROTOCOL["external_manifest_sha256"]:
        raise AuditError("previous_audit_mismatch")
    by_id, repaired, changes = {r.example_id: r for r in rows}, {}, []
    for name, meta in AUDIT_SOURCE["files"].items():
        if meta["kind"] == "terms":
            continue
        checked_bytes(raw_cache / name, meta)
        for index, raw in messages(raw_cache / name, meta["kind"]):
            rid = f"external-{name.split('.')[0]}-{index:06d}"
            if rid not in by_id:
                continue  # Do not parse raw reserve messages for extraction changes.
            email, flags = extract(raw)
            repaired[rid] = by_id[rid].model_copy(update={"email": email, "split": "unassigned"})
            if email != by_id[rid].email:
                changes.append(
                    {
                        "example_id": rid,
                        "label": by_id[rid].label,
                        "flags": [k for k, v in flags.items() if v],
                        "old_chars": len(by_id[rid].email.text),
                        "new_chars": len(email.text),
                    }
                )
    if set(repaired) != set(by_id):
        raise AuditError("audit_reextraction_incomplete")
    # Sole permitted use: automatic duplicate protection, never fit/review/predict.
    payload = checked_bytes(directory / "reserve.jsonl", manifest["files"]["reserve.jsonl"])
    reserve = [validate_json("example", line) for line in payload.splitlines()]
    expected = {rid for g in manifest["groups"] if g["cohort"] == "reserve" for rid in g["members"]}
    if {r.example_id for r in reserve} != expected or len(reserve) != len(expected):
        raise AuditError("reserve_membership_mismatch")
    return list(repaired.values()), reserve, changes, manifest["files"]["reserve.jsonl"]


def components(records):
    """Add known source families to the broader text-similarity components."""
    groups, _ = relations(records)
    parent = {r.example_id: r.example_id for r in records}

    def root(rid):
        while parent[rid] != rid:
            parent[rid] = parent[parent[rid]]
            rid = parent[rid]
        return rid

    def union(a, b):
        a, b = root(a), root(b)
        parent[max(a, b)] = min(a, b)

    for group in groups:
        for rid in group[1:]:
            union(group[0], rid)
    known = {}
    for row in records:
        if row.group_id != "unassigned":
            if row.group_id in known:
                union(row.example_id, known[row.group_id])
            else:
                known[row.group_id] = row.example_id
    result = defaultdict(list)
    for rid in sorted(parent):
        result[root(rid)].append(rid)
    return sorted(result.values())


def allocate(groups, by_id, ratios):
    totals = Counter((by_id[rid].source_id, by_id[rid].label) for ids in groups for rid in ids)
    counts = {split: Counter() for split in ratios}
    assigned = []
    groups = sorted(
        groups,
        key=lambda ids: (-len(ids), digest(f"{PROTOCOL['seed']}:{group_identifier(ids)}".encode())),
    )
    for ids in groups:
        increments = Counter((by_id[rid].source_id, by_id[rid].label) for rid in ids)

        def cost(split, increments=increments):
            return sum(
                (
                    (counts[split][key] + n - totals[key] * ratios[split]) ** 2
                    - (counts[split][key] - totals[key] * ratios[split]) ** 2
                )
                / max(1, totals[key] * ratios[split])
                for key, n in increments.items()
            )

        chosen = min(ratios, key=lambda split: (cost(split), split))
        counts[chosen].update(increments)
        assigned.append({"group_id": group_identifier(ids), "split": chosen, "members": ids})
    return assigned


def prepare(cache, internal_dir, internal_ref, audit_dir, audit_ref, raw_cache, output):
    if output.exists():
        raise AuditError("output_already_exists")
    internal = FrozenDataset(internal_dir, internal_ref)
    if internal.sha256 != PROTOCOL["internal_manifest_sha256"]:
        raise AuditError("internal_dataset_mismatch")
    protected = [r for s in ("train", "validation", "test") for r in internal.load(s)]
    audit, reserve, repairs, reserve_file = old_audit(audit_dir, audit_ref, raw_cache)
    protected.extend(reserve)
    ham, ham_report = meajor(cache)
    phish, phish_report = nazario(cache)
    holdout, origins = challenge(cache)
    all_candidates = audit + ham + phish + holdout
    all_rows = all_candidates + protected
    by_id = {r.example_id: r for r in all_rows}
    protected_ids = {r.example_id for r in protected}
    audit_ids = {r.example_id for r in audit}
    challenge_ids = {r.example_id for r in holdout}
    exclusions, duplicates = [], defaultdict(list)
    for row in all_candidates:
        duplicates[canonical(preprocess(row.email.text))].append(row.example_id)
    removed = set()
    for ids in duplicates.values():
        ids.sort(key=lambda rid: (rid not in audit_ids, rid))
        conflict = len({by_id[rid].label for rid in ids}) > 1
        for rid in ids if conflict else ids[1:]:
            removed.add(rid)
            exclusions.append(
                {
                    "example_id": rid,
                    "reason": "conflicting_exact_labels" if conflict else "duplicate_input",
                }
            )
    development, new_groups, challenge_groups = [], [], []
    for ids in components(all_rows):
        candidates = set(ids) - protected_ids - removed
        if not candidates:
            continue
        if set(ids) & protected_ids:
            exclusions.extend(
                {"example_id": rid, "reason": "related_to_protected_corpus"}
                for rid in sorted(candidates)
            )
            continue
        external_challenge = candidates & challenge_ids
        normal = candidates - challenge_ids
        if external_challenge and normal:
            exclusions.extend(
                {"example_id": rid, "reason": "challenge_related_to_development"}
                for rid in sorted(external_challenge)
            )
        elif external_challenge:
            challenge_groups.append(sorted(external_challenge))
        if normal:
            (development if set(ids) & audit_ids else new_groups).append(sorted(normal))
    membership = allocate(development, by_id, PROTOCOL["old_audit_splits"])
    membership += allocate(new_groups, by_id, PROTOCOL["splits"])
    membership += [
        {"group_id": group_identifier(ids), "split": "challenge", "members": ids}
        for ids in challenge_groups
    ]
    partitions = {s: [] for s in ("train", "validation", "test", "challenge")}
    for group in membership:
        split = group["split"]
        partitions[split].extend(
            by_id[rid].model_copy(
                update={
                    "split": "test" if split == "challenge" else split,
                    "group_id": group["group_id"],
                }
            )
            for rid in group["members"]
        )
    for split, rows in partitions.items():
        rows.sort(key=lambda r: r.example_id)
        if {r.label for r in rows} != {"legitimate", "phishing"}:
            raise AuditError("insufficient_refresh_class_coverage")
        if split == "test" and any(r.example_id in audit_ids for r in rows):
            raise AuditError("inspected_audit_in_test")
    manifest = {
        "version": "real-mail-v2",
        "source": SOURCE,
        "source_sha256": SOURCE_SHA256,
        "protocol": PROTOCOL,
        "protocol_sha256": PROTOCOL_SHA256,
        "groups": sorted(membership, key=lambda g: g["group_id"]),
        "partitions": {s: cohort_stats(rows) for s, rows in partitions.items()},
        "ingestion": {"meajor": ham_report, "nazario": phish_report},
        "extraction_repairs": repairs,
        "exclusions": sorted(exclusions, key=lambda e: e["example_id"]),
        "exclusion_counts": dict(Counter(e["reason"] for e in exclusions)),
        "protected_internal_rows": len(protected) - len(reserve),
        "reserve_rows": len(reserve),
        "reserve_file": reserve_file,
        "reserve_rows_scored": 0,
        "challenge_origins": {
            rid: origins[rid]
            for g in membership
            if g["split"] == "challenge"
            for rid in g["members"]
        },
        "files": {},
    }
    output.mkdir(parents=True, exist_ok=False)
    for split, rows in partitions.items():
        payload = b"".join((r.model_dump_json() + "\n").encode() for r in rows)
        name = split + ".jsonl"
        (output / name).write_bytes(payload)
        manifest["files"][name] = {"bytes": len(payload), "sha256": digest(payload)}
    (output / "manifest.json").write_bytes(json_bytes(manifest))
    return manifest


class FrozenStudy:
    def __init__(self, directory: Path, reference: Path):
        self.directory = directory
        payload = read_bytes(directory / "manifest.json")
        if payload != read_bytes(reference):
            raise AuditError("refresh_manifest_mismatch")
        self.sha256, self.manifest = digest(payload), parse_json(payload)
        if (
            self.manifest.get("protocol") != PROTOCOL
            or self.manifest.get("source") != SOURCE
            or self.manifest.get("protocol_sha256") != PROTOCOL_SHA256
            or self.manifest.get("source_sha256") != SOURCE_SHA256
        ):
            raise AuditError("refresh_protocol_mismatch")
        self.members, groups = {}, set()
        for group in self.manifest["groups"]:
            if group["group_id"] in groups or group["split"] not in {
                "train",
                "validation",
                "test",
                "challenge",
            }:
                raise AuditError("refresh_membership_mismatch")
            groups.add(group["group_id"])
            for rid in group["members"]:
                if rid in self.members:
                    raise AuditError("refresh_membership_mismatch")
                self.members[rid] = (group["group_id"], group["split"])

    def load(self, split):
        if split not in {"train", "validation", "test", "challenge"}:
            raise AuditError("invalid_partition")
        name = split + ".jsonl"
        payload = checked_bytes(self.directory / name, self.manifest["files"][name])
        rows = [validate_json("example", line) for line in payload.splitlines()]
        expected = {rid for rid, (_, s) in self.members.items() if s == split}
        if len(rows) != len(expected) or {r.example_id for r in rows} != expected:
            raise AuditError("refresh_membership_mismatch")
        for row in rows:
            if self.members[row.example_id] != (row.group_id, split) or row.split != (
                "test" if split == "challenge" else split
            ):
                raise AuditError("refresh_membership_mismatch")
        if cohort_stats(rows) != self.manifest["partitions"][split]:
            raise AuditError("refresh_counts_mismatch")
        return rows
