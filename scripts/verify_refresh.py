"""Independently recount the two fixed runs; never fit, predict or parse reserve text."""

import hashlib
import json
from collections import Counter
from pathlib import Path


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def recount(rows, name, threshold):
    counts = Counter()
    for row in rows:
        positive = row["label"] == "phishing"
        predicted = row[name + "_score"] >= threshold
        counts[
            {(True, True): "tp", (False, True): "fp", (False, False): "tn", (True, False): "fn"}[
                (positive, predicted)
            ]
        ] += 1
    c = {key: counts[key] for key in ("tp", "fp", "tn", "fn")}
    tp, fp, tn, fn = (c[key] for key in ("tp", "fp", "tn", "fn"))
    recall = tp / (tp + fn) if tp + fn else None
    fpr = fp / (fp + tn) if fp + tn else None
    return {
        "confusion": c,
        "accuracy": (tp + tn) / len(rows),
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": recall,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "false_positive_rate": fpr,
        "balanced_accuracy": (recall + 1 - fpr) / 2
        if recall is not None and fpr is not None
        else None,
    }


def assert_metrics(measured, expected):
    for key, value in measured.items():
        if isinstance(value, float):
            assert abs(value - expected[key]) < 1e-12, key
        else:
            assert value == expected[key], key


def main():
    manifest_bytes = Path("data/manifests/real-mail-v2.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    for name in (
        "manifest.json",
        "train.jsonl",
        "validation.jsonl",
        "test.jsonl",
        "challenge.jsonl",
    ):
        payload = (Path("data/processed/real-mail-v2") / name).read_bytes()
        assert payload == (Path("data/processed/real-mail-v2-reproduction") / name).read_bytes(), (
            name
        )
        if name == "manifest.json":
            assert payload == manifest_bytes
        else:
            assert digest(payload) == manifest["files"][name]["sha256"]
    model = Path("models/baseline-v2/model.json").read_bytes()
    assert model == Path("models/baseline-v2-reproduction/model.json").read_bytes()
    selection = read("data/manifests/baseline-v2-selection.json")
    assert digest(model) == selection["model_revision"]
    assert digest(manifest_bytes) == selection["dataset_sha256"]
    old_model = Path("models/baseline-v1/model.json").read_bytes()
    assert digest(old_model) == manifest["protocol"]["old_model_revision"]
    reserve = Path("data/processed/external-mail-v1/reserve.jsonl").read_bytes()
    assert digest(reserve) == manifest["reserve_file"]["sha256"]
    assert len(reserve) == manifest["reserve_file"]["bytes"]
    original = read("data/manifests/ephishllm-v1.json")
    for name, meta in original["files"].items():
        payload = (Path("data/processed/ephishllm-v1") / name).read_bytes()
        assert digest(payload) == meta["sha256"], name
    first = Path("artifacts/real-mail-v2-evaluation")
    second = Path("artifacts/real-mail-v2-reproduction")
    report, repeated = read(first / "report.json"), read(second / "report.json")
    payload = (first / "predictions.jsonl").read_bytes()
    assert payload == (second / "predictions.jsonl").read_bytes()
    assert digest(payload) == report["predictions_sha256"] == repeated["predictions_sha256"]
    predictions = [json.loads(line) for line in payload.splitlines()]
    recounted = {}
    for split, cohort in report["cohorts"].items():
        rows = [r for r in predictions if r["cohort"] == split]
        expected_ids = {
            rid for g in manifest["groups"] if g["split"] == split for rid in g["members"]
        }
        assert len(rows) == len(expected_ids) and {r["example_id"] for r in rows} == expected_ids
        paired = Counter()
        for row in rows:
            truth = row["label"] == "phishing"
            a = (row["v1_score"] >= report["old_threshold"]) == truth
            b = (row["v2_score"] >= selection["threshold"]) == truth
            paired[
                {
                    (True, True): "both_correct",
                    (False, False): "both_wrong",
                    (True, False): "v1_only_correct",
                    (False, True): "v2_only_correct",
                }[(a, b)]
            ] += 1
        assert paired == cohort["paired_correctness"]
        recounted[split] = {}
        for short, name in (("v1", "baseline_v1"), ("v2", "baseline_v2")):
            result = cohort["results"][name]
            for key in ("metrics", "per_source", "group_bootstrap", "threshold"):
                assert result[key] == repeated["cohorts"][split]["results"][name][key]
            counts = recount(rows, short, result["threshold"])
            assert_metrics(counts, result["metrics"])
            for source, expected in result["per_source"].items():
                assert_metrics(
                    recount(
                        [r for r in rows if r["source_id"] == source], short, result["threshold"]
                    ),
                    expected,
                )
            recounted[split][name] = counts
    review = read("docs/reports/refresh-review-boundary.json")
    inspected = set(review["reviewed_ids"])
    for split, recorded in review["final_partitions"].items():
        ids = {rid for g in manifest["groups"] if g["split"] == split for rid in g["members"]}
        assert sorted(ids & inspected) == recorded
    sensitivity = [
        r for r in predictions if r["cohort"] == "test" and r["example_id"] not in inspected
    ]
    assert len(sensitivity) == review["sensitivity_rows"] == 424
    for short, name, threshold in (
        ("v1", "baseline_v1", report["old_threshold"]),
        ("v2", "baseline_v2", selection["threshold"]),
    ):
        assert_metrics(recount(sensitivity, short, threshold), review["posthoc_sensitivity"][name])
    verification = {
        "status": "passed",
        "independent_confusion_and_metrics": recounted,
        "data_and_manifest_byte_identical": True,
        "model_byte_identical": True,
        "predictions_byte_identical": True,
        "paired_and_subgroup_counts_match": True,
        "bootstrap_intervals_identical": True,
        "original_internal_files_unchanged": True,
        "v1_model_sha256": digest(old_model),
        "v2_model_sha256": digest(model),
        "dataset_manifest_sha256": digest(manifest_bytes),
        "reserve_sha256": digest(reserve),
        "reserve_rows_scored": 0,
        "reserve_text_parsed_by_this_verifier": False,
        "reviewed_rows_in_frozen_historical_test": len(review["final_partitions"]["test"]),
        "review_boundary_sensitivity_recounted": True,
    }
    Path("docs/reports/refresh-verification.json").write_text(
        json.dumps(verification, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"status": "verified", "predictions": len(predictions), "reserve_rows_scored": 0}
        )
    )


if __name__ == "__main__":
    main()
