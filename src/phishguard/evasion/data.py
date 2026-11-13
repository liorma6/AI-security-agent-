"""Generate/freeze a candidate bank without scoring or reading reserved mail."""

from collections import Counter

from phishguard.baseline.common import parse_json, read_bytes
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.evasion.common import (
    PROTOCOL,
    PROTOCOL_SHA256,
    EvasionError,
    identity,
    lines_bytes,
)
from phishguard.evasion.perturbations import generate, rank
from phishguard.finetune.common import STUDY_SHA256, partition, study


def preview(directory, reference, output):
    if output.exists():
        raise EvasionError("output_already_exists")
    frozen = study(directory, reference)
    rows = partition(frozen, "train")
    samples, public = [], []
    for operation in PROTOCOL["operations"]:
        for label in ("legitimate", "phishing"):
            candidates = sorted(
                (r for r in rows if r.label == label),
                key=lambda r: rank("preflight", operation, label, r.example_id),
            )
            chosen = 0
            for row in candidates:
                variants = [v for v in generate(row, "train") if v["operation"] == operation]
                if not variants:
                    continue
                variant = max(variants, key=lambda v: v["changed_words"])
                samples.append({"original": row.model_dump(), "variant": variant})
                public.append({k: v for k, v in variant.items() if k not in {"edits", "email"}})
                chosen += 1
                if chosen == 2:
                    break
    payload = lines_bytes(samples)
    report = {
        **identity(),
        "phase": "training-only-preflight-no-model-scoring",
        "dataset_sha256": frozen.sha256,
        "samples": public,
        "sample_count": len(samples),
        "samples_sha256": digest(payload),
        "benchmark_or_reserve_files_opened": False,
        "model_queries": 0,
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "samples.jsonl").write_bytes(payload)
    (output / "report.json").write_bytes(json_bytes(report))
    return report


def collect(directory, reference):
    frozen = study(directory, reference)
    cohorts, variants, parents, counts = {}, [], [], {}
    for cohort in ("test", "challenge"):
        rows = partition(frozen, cohort)
        cohorts[cohort] = rows
        available, operations, size_counts = 0, Counter(), Counter()
        for row in rows:
            generated = generate(row, cohort)
            available += bool(generated)
            operations.update(v["operation"] for v in generated)
            size_counts[len(generated)] += 1
            parents.append(
                {
                    "parent_id": row.example_id,
                    "group_id": row.group_id,
                    "split": row.split,
                    "cohort": cohort,
                    "variant_ids": [v["variant_id"] for v in generated],
                }
            )
            variants.extend(generated)
        counts[cohort] = {
            "originals": len(rows),
            "groups": len({r.group_id for r in rows}),
            "originals_with_candidates": available,
            "originals_without_candidates": len(rows) - available,
            "variants_by_operation": dict(operations),
            "candidate_count_distribution": {str(k): v for k, v in sorted(size_counts.items())},
        }
    ids = [v["variant_id"] for v in variants]
    if len(ids) != len(set(ids)):
        raise EvasionError("duplicate_variant_identity")
    payload = lines_bytes(variants)
    manifest = {
        "version": "evasion-bank-v1",
        "protocol": PROTOCOL,
        "protocol_sha256": PROTOCOL_SHA256,
        "dataset_sha256": frozen.sha256,
        "stage5_study_sha256": STUDY_SHA256,
        "cohorts": counts,
        "parents": parents,
        "variants": len(variants),
        "files": {"variants.jsonl": {"bytes": len(payload), "sha256": digest(payload)}},
        "training_validation_or_reserve_files_opened": False,
    }
    return cohorts, variants, payload, manifest


def prepare(directory, reference, output):
    if output.exists():
        raise EvasionError("output_already_exists")
    _, _, payload, manifest = collect(directory, reference)
    output.mkdir(parents=True, exist_ok=False)
    (output / "variants.jsonl").write_bytes(payload)
    (output / "manifest.json").write_bytes(json_bytes(manifest))
    return manifest


def verify(directory, reference, bank, bank_reference):
    declared = read_bytes(bank / "manifest.json")
    if declared != read_bytes(bank_reference):
        raise EvasionError("evasion_bank_reference_mismatch")
    cohorts, variants, payload, manifest = collect(directory, reference)
    if parse_json(declared) != manifest:
        raise EvasionError("evasion_bank_manifest_mismatch")
    if read_bytes(bank / "variants.jsonl", 128 * 1024 * 1024) != payload:
        raise EvasionError("evasion_bank_content_mismatch")
    return cohorts, variants, manifest
