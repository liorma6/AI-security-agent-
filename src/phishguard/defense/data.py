"""Frozen development augmentation and separate benchmark candidates; never resplit."""

from collections import Counter

from phishguard.baseline.common import parse_json, read_bytes
from phishguard.baseline.model import check_training_boundary, text_hash
from phishguard.contracts import EmailInput
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.defense.common import PROTOCOL, PROTOCOL_SHA256, DefenseError
from phishguard.evasion.common import PROTOCOL as EVASION
from phishguard.evasion.common import lines_bytes
from phishguard.evasion.perturbations import generate, rank
from phishguard.finetune.common import partition, study


def public_variant(variant):
    return {k: v for k, v in variant.items() if k not in {"email", "edits"}}


def copies(rows, split):
    if split not in PROTOCOL["augmentation_seeds"] or any(r.split != split for r in rows):
        raise DefenseError("augmentation_development_only")
    seed = PROTOCOL["augmentation_seeds"][split]
    result = []
    for row in rows:
        bank = generate(row, split, seed=seed)
        chosen = (
            min(bank, key=lambda v: rank("choice", v["variant_id"], seed=seed))
            if bank
            else {
                "variant_id": None,
                "parent_id": row.example_id,
                "group_id": row.group_id,
                "cohort": split,
                "split": split,
                "label": row.label,
                "source_id": row.source_id,
                "operation": "clean_fallback",
                "seed": seed,
                "changed_words": 0,
                "email": row.email.model_dump(),
                "edits": [],
            }
        )
        result.append(chosen)
    return result


def review_sample(variants):
    chosen = []
    for operation in EVASION["operations"]:
        for label in ("legitimate", "phishing"):
            pool = [
                v
                for v in variants
                if v["split"] == "train" and v["operation"] == operation and v["label"] == label
            ]
            chosen.extend(sorted(pool, key=lambda v: rank("review", v["variant_id"]))[:2])
    return chosen


def collect_augmentation(directory, reference):
    frozen = study(directory, reference)
    rows = {s: partition(frozen, s) for s in ("train", "validation")}
    check_training_boundary(rows["train"], rows["validation"])
    variants = {s: copies(values, s) for s, values in rows.items()}
    # Validate original AND augmented boundaries before any gradient update.
    views = {
        s: values
        + [
            r.model_copy(update={"email": EmailInput.model_validate(v["email"])})
            for r, v in zip(values, variants[s], strict=True)
        ]
        for s, values in rows.items()
    }
    train_hashes = {text_hash(r.email) for r in views["train"]}
    if train_hashes & {text_hash(r.email) for r in views["validation"]}:
        raise DefenseError("augmentation_validation_overlap")
    for values in views.values():
        labels = {}
        for row in values:
            fingerprint = text_hash(row.email)
            if fingerprint in labels and labels[fingerprint] != row.label:
                raise DefenseError("augmentation_conflicting_labels")
            labels[fingerprint] = row.label
    all_variants = variants["train"] + variants["validation"]
    payload = lines_bytes(all_variants)
    samples = review_sample(all_variants)
    manifest = {
        "version": "defense-augmentation-v1",
        "protocol_sha256": PROTOCOL_SHA256,
        "dataset_sha256": frozen.sha256,
        "files": {"copies.jsonl": {"bytes": len(payload), "sha256": digest(payload)}},
        "partitions": {
            s: {
                "originals": len(rows[s]),
                "copies": len(values),
                "operations": dict(Counter(v["operation"] for v in values)),
                "labels": dict(Counter(v["label"] for v in values)),
            }
            for s, values in variants.items()
        },
        "copies": [public_variant(v) for v in all_variants],
        "review_variant_ids": [v["variant_id"] for v in samples],
        "test_challenge_or_reserve_files_opened": False,
        "model_queries": 0,
    }
    return rows, variants, views, payload, manifest


def prepare(directory, reference, output):
    if output.exists():
        raise DefenseError("output_already_exists")
    rows, variants, _, payload, manifest = collect_augmentation(directory, reference)
    originals = {r.example_id: r for r in rows["train"]}
    samples = [
        {"original": originals[v["parent_id"]].model_dump(), "variant": v}
        for v in review_sample(variants["train"])
    ]
    output.mkdir(parents=True, exist_ok=False)
    (output / "copies.jsonl").write_bytes(payload)
    (output / "manifest.json").write_bytes(json_bytes(manifest))
    (output / "review-samples.jsonl").write_bytes(lines_bytes(samples))
    return manifest


def verify_augmentation(directory, reference, augmentation, frozen_reference, review_reference):
    rows, variants, views, payload, manifest = collect_augmentation(directory, reference)
    declared = read_bytes(frozen_reference)
    if (
        read_bytes(augmentation / "manifest.json") != declared
        or parse_json(declared) != manifest
        or read_bytes(augmentation / "copies.jsonl", 128 * 1024 * 1024) != payload
    ):
        raise DefenseError("augmentation_reference_or_content_mismatch")
    review = parse_json(read_bytes(review_reference))
    decisions = review.get("decisions", [])
    if (
        review.get("augmentation_manifest_sha256") != digest(declared)
        or [r.get("variant_id") for r in decisions] != manifest["review_variant_ids"]
        or not decisions
        or any(r.get("decision") != "supported" for r in decisions)
    ):
        raise DefenseError("augmentation_review_incomplete_or_unsupported")
    return rows, variants, views, manifest


def collect_fresh(directory, reference):
    frozen = study(directory, reference)
    cohorts, variants = {}, []
    parents = []
    for cohort in ("test", "challenge"):
        rows = partition(frozen, cohort)
        cohorts[cohort] = rows
        for row in rows:
            bank = generate(row, cohort, seed=PROTOCOL["fresh_search_seed"])
            variants.extend(bank)
            parents.append(
                {
                    "parent_id": row.example_id,
                    "group_id": row.group_id,
                    "cohort": cohort,
                    "split": row.split,
                    "variant_ids": [v["variant_id"] for v in bank],
                }
            )
    payload = lines_bytes(variants)
    manifest = {
        "version": "defense-fresh-bank-v1",
        "protocol_sha256": PROTOCOL_SHA256,
        "dataset_sha256": frozen.sha256,
        "seed": PROTOCOL["fresh_search_seed"],
        "parents": parents,
        "variants": len(variants),
        "files": {"variants.jsonl": {"bytes": len(payload), "sha256": digest(payload)}},
        "training_validation_or_reserve_files_opened": False,
    }
    return cohorts, variants, payload, manifest


def prepare_fresh(directory, reference, output):
    if output.exists():
        raise DefenseError("output_already_exists")
    _, _, payload, manifest = collect_fresh(directory, reference)
    output.mkdir(parents=True, exist_ok=False)
    (output / "variants.jsonl").write_bytes(payload)
    (output / "manifest.json").write_bytes(json_bytes(manifest))
    return manifest


def verify_fresh(directory, reference, bank, bank_reference):
    cohorts, variants, payload, manifest = collect_fresh(directory, reference)
    declared = read_bytes(bank_reference)
    if (
        read_bytes(bank / "manifest.json") != declared
        or parse_json(declared) != manifest
        or read_bytes(bank / "variants.jsonl", 128 * 1024 * 1024) != payload
    ):
        raise DefenseError("fresh_bank_reference_or_content_mismatch")
    return cohorts, variants, manifest
