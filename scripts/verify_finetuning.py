"""Independently verify fixed-run artifacts, preserved inputs and benchmark counts."""

import json
from collections import Counter
from pathlib import Path

from verify_refresh import assert_metrics, digest, read, recount


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()


def verify_files(directory, files):
    for name, meta in files.items():
        payload = (directory / name).read_bytes()
        assert len(payload) == meta["bytes"] and digest(payload) == meta["sha256"], name


def main():
    policy = read("src/phishguard/finetune/study.json")
    protocol = read("src/phishguard/finetune/protocol.json")
    source = read("src/phishguard/finetune/source.json")
    frozen_payload = Path("data/manifests/real-mail-v2.json").read_bytes()
    assert digest(frozen_payload) == policy["dataset_sha256"]
    frozen = json.loads(frozen_payload)
    verify_files(Path("data/processed/real-mail-v2"), frozen["files"])
    verify_files(
        Path("data/processed/ephishllm-v1"), read("data/manifests/ephishllm-v1.json")["files"]
    )
    verify_files(
        Path("data/processed/external-mail-v1"),
        read("data/manifests/external-mail-v1.json")["files"],
    )
    assert (
        digest(Path("models/baseline-v2/model.json").read_bytes()) == policy["baseline_v2_revision"]
    )
    assert (
        digest(Path("models/baseline-v1/model.json").read_bytes())
        == frozen["protocol"]["old_model_revision"]
    )
    verify_files(Path("models/finetune-source/google-" + source["revision"][:8]), source["files"])
    former = read("src/phishguard/pretrained/source.json")
    verify_files(Path("models/pretrained/dima806-" + former["revision"][:8]), former["files"])
    review = read("docs/reports/refresh-review-boundary.json")
    assert digest(canonical(review)) == policy["review_trace_sha256"]
    chosen = read("data/manifests/finetuned-v1-selection.json")
    first_model, second_model = (
        Path("models/finetuned-v1"),
        Path("models/finetuned-reproduction-v1"),
    )
    manifest = read(first_model / "manifest.json")
    assert digest((first_model / "manifest.json").read_bytes()) == chosen["manifest_sha256"]
    assert (
        digest(canonical({k: v for k, v in manifest.items() if k != "model_revision"}))
        == chosen["model_revision"]
    )
    for name in (
        "model.safetensors",
        "config.json",
        "vocab.txt",
        "manifest.json",
        "selection.json",
    ):
        assert (first_model / name).read_bytes() == (second_model / name).read_bytes(), name
    verify_files(first_model, manifest["files"])
    train_report, train_repeat = (
        read(first_model / "training-report.json"),
        read(second_model / "training-report.json"),
    )
    for key in (
        "epochs",
        "selection",
        "training_metrics",
        "validation_metrics",
        "tokens",
        "encoder_before_sha256",
        "encoder_after_sha256",
        "fit_ids_sha256",
        "validation_ids_sha256",
    ):
        assert train_report[key] == train_repeat[key], key
    assert train_report["encoder_before_sha256"] != train_report["encoder_after_sha256"]
    assert (
        train_report["selected_epoch"]
        == min(train_report["epochs"], key=lambda e: e["validation_mean_loss"])["epoch"]
    )
    assert len(train_report["epochs"]) == protocol["epochs"]
    assert (
        train_report["test_rows_used"]
        == train_report["challenge_rows_used"]
        == train_report["reserve_rows_scored"]
        == 0
    )
    assert train_report["reload_max_absolute_score_error"] <= 1e-7
    first, second = (
        Path("artifacts/finetuned-evaluation-v1"),
        Path("artifacts/finetuned-reproduction-v1"),
    )
    report, repeated = read(first / "report.json"), read(second / "report.json")
    payload = (first / "predictions.jsonl").read_bytes()
    assert payload == (second / "predictions.jsonl").read_bytes()
    assert digest(payload) == report["predictions_sha256"] == repeated["predictions_sha256"]
    predictions = [json.loads(line) for line in payload.splitlines()]
    forbidden = {rid for g in policy["excluded_benchmark_groups"] for rid in g["members"]}
    earlier = {
        r["example_id"]: r
        for r in (
            json.loads(line)
            for line in Path("artifacts/real-mail-v2-evaluation/predictions.jsonl")
            .read_bytes()
            .splitlines()
        )
    }
    counts = {}
    for split, cohort in report["cohorts"].items():
        rows = [r for r in predictions if r["cohort"] == split]
        expected = {
            rid for g in frozen["groups"] if g["split"] == split for rid in g["members"]
        } - forbidden
        assert len(rows) == len(expected) == policy["expected_rows"][split]
        assert {r["example_id"] for r in rows} == expected
        assert not expected & set(policy["reviewed_ids"])
        paired = Counter()
        for row in rows:
            assert row["baseline_score"] == earlier[row["example_id"]]["v2_score"]
            truth = row["label"] == "phishing"
            a = (row["baseline_score"] >= policy["baseline_v2_threshold"]) == truth
            b = (row["finetuned_score"] >= chosen["threshold"]) == truth
            paired[
                {
                    (True, True): "both_correct",
                    (False, False): "both_wrong",
                    (True, False): "baseline_only_correct",
                    (False, True): "finetuned_only_correct",
                }[(a, b)]
            ] += 1
        assert paired == cohort["paired_correctness"]
        for key in ("results", "paired_correctness", "finetuned_at_default_threshold", "tokens"):
            assert cohort[key] == repeated["cohorts"][split][key]
        counts[split] = {}
        for short, name, threshold in (
            ("baseline", "baseline_v2", policy["baseline_v2_threshold"]),
            ("finetuned", "finetuned", chosen["threshold"]),
        ):
            result = cohort["results"][name]
            measured = recount(rows, short, threshold)
            assert_metrics(measured, result["metrics"])
            counts[split][name] = measured
            for source_id, subgroup in result["per_source"].items():
                assert_metrics(
                    recount([r for r in rows if r["source_id"] == source_id], short, threshold),
                    subgroup,
                )
        assert_metrics(recount(rows, "finetuned", 0.5), cohort["finetuned_at_default_threshold"])
    output = {
        "status": "passed",
        "independent_counts": counts,
        "model_revision": chosen["model_revision"],
        "weights_and_artifacts_byte_identical": True,
        "predictions_byte_identical": True,
        "training_history_and_validation_identical": True,
        "selected_encoder_updated": True,
        "class_subgroup_paired_and_default_threshold_metrics_match": True,
        "bootstrap_intervals_identical": True,
        "baseline_scores_match_stage4b": True,
        "old_baselines_pretrained_source_and_datasets_unchanged": True,
        "reviewed_families_excluded": sorted(forbidden),
        "reserve_rows_scored": 0,
        "reserve_content_parsed_by_verifier": False,
        "reserve_sha256": frozen["reserve_file"]["sha256"],
    }
    Path("docs/reports/finetuned-verification.json").write_bytes(canonical(output))
    print(
        json.dumps(
            {"status": "verified", "predictions": len(predictions), "reserve_rows_scored": 0}
        )
    )


if __name__ == "__main__":
    main()
