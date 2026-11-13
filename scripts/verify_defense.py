"""Independent frozen-run recount and byte verification; never parse the reserve."""

import hashlib
import json
from pathlib import Path

from verify_evasion import check_asr, records
from verify_refresh import assert_metrics, digest, read
from verify_refresh import recount as recount_rows


def recount(labels, scores, threshold):
    rows = [
        {"label": "phishing" if label else "legitimate", "checked_score": score}
        for label, score in zip(labels, scores, strict=True)
    ]
    return recount_rows(rows, "checked", threshold)


def main():
    preserved = read("data/manifests/defense-preserved-inputs-v1.json")
    for name, meta in preserved.items():
        path = Path(name)
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        assert path.stat().st_size == meta["bytes"] and actual == meta["sha256"], name
    pairs = [
        (
            "artifacts/defense-augmentation-v1",
            "artifacts/defense-augmentation-reproduction-v1",
            ["copies.jsonl", "manifest.json", "review-samples.jsonl"],
        ),
        (
            "models/defended-v1",
            "models/defended-reproduction-v1",
            ["model.safetensors", "vocab.txt", "config.json", "manifest.json", "selection.json"],
        ),
        (
            "artifacts/defense-fresh-bank-v1",
            "artifacts/defense-fresh-bank-reproduction-v1",
            ["variants.jsonl", "manifest.json"],
        ),
        (
            "artifacts/defense-evaluation-v1",
            "artifacts/defense-reproduction-v1",
            ["predictions.jsonl"],
        ),
    ]
    for first, second, names in pairs:
        for name in names:
            assert (Path(first) / name).read_bytes() == (Path(second) / name).read_bytes(), name
    for directory, reference in [
        ("artifacts/defense-augmentation-v1", "data/manifests/defense-augmentation-v1.json"),
        ("artifacts/defense-fresh-bank-v1", "data/manifests/defense-fresh-bank-v1.json"),
    ]:
        assert (Path(directory) / "manifest.json").read_bytes() == Path(reference).read_bytes()
    assert (
        Path("models/defended-v1/selection.json").read_bytes()
        == Path("data/manifests/defended-v1-selection.json").read_bytes()
    )
    training = read("models/defended-v1/training-report.json")
    repeated_training = read("models/defended-reproduction-v1/training-report.json")
    for key in (
        "epochs",
        "selection",
        "training_metrics",
        "validation_clean",
        "validation_perturbed",
        "initial_state_sha256",
        "final_encoder_sha256",
    ):
        assert training[key] == repeated_training[key], key
    assert (
        training["selected_epoch"]
        == min(training["epochs"], key=lambda e: e["validation_mixed_mean_loss"])["epoch"]
    )
    assert training["encoder_updated"] and not training["test_challenge_or_reserve_files_opened"]
    report = read("artifacts/defense-evaluation-v1/report.json")
    repeated = read("artifacts/defense-reproduction-v1/report.json")
    payload = Path("artifacts/defense-evaluation-v1/predictions.jsonl").read_bytes()
    assert digest(payload) == report["predictions_sha256"] == repeated["predictions_sha256"]
    rows = records("artifacts/defense-evaluation-v1/predictions.jsonl")
    stage6 = {
        r["example_id"]: r for r in records("artifacts/evasion-evaluation-v1/predictions.jsonl")
    }
    thresholds = report["thresholds"]
    counts = {}
    for bank, cohorts in report["banks"].items():
        counts[bank] = {}
        for cohort, summary in cohorts.items():
            subset = [r for r in rows if r["bank"] == bank and r["cohort"] == cohort]
            assert len(subset) == summary["rows"]
            assert len({r["example_id"] for r in subset}) == len(subset)
            labels = [int(r["label"] == "phishing") for r in subset]
            counts[bank][cohort] = {}
            for name, threshold in thresholds.items():
                model = summary["models"][name]
                clean = [r["clean_scores"][name] for r in subset]
                fixed = [
                    r["candidates"][0]["scores"][name]
                    if r["candidates"]
                    else r["clean_scores"][name]
                    for r in subset
                ]
                attacked = [
                    min([r["clean_scores"][name]] + [c["scores"][name] for c in r["candidates"]])
                    if r["label"] == "phishing"
                    else r["clean_scores"][name]
                    for r in subset
                ]
                views = {
                    "clean": clean,
                    "fixed_perturbation": fixed,
                    "phishing_only_worst_of_budget": attacked,
                }
                counts[bank][cohort][name] = {}
                for view, values in views.items():
                    actual = recount(labels, values, threshold)
                    assert_metrics(actual, model[view])
                    counts[bank][cohort][name][view] = actual
                check_asr(subset, name, threshold, model["evasion"])
                for op, expected in model["evasion_by_operation"].items():
                    check_asr(subset, name, threshold, expected, op)
                for source, expected in model["per_source"].items():
                    check_asr(
                        [r for r in subset if r["source_id"] == source], name, threshold, expected
                    )
                assert model["actual_queries"] == sum(1 + len(r["candidates"]) for r in subset)
                assert (
                    model["maximum_queries_per_original"]
                    == max(1 + len(r["candidates"]) for r in subset)
                    <= 13
                )
                assert model == repeated["banks"][bank][cohort]["models"][name]
            for common_key, models in [
                ("common_clean_detected_phishing", list(thresholds)),
                ("parent_defense_common_detected", ["finetuned", "defended"]),
            ]:
                common = [
                    r
                    for r in subset
                    if r["label"] == "phishing"
                    and all(r["clean_scores"][m] >= thresholds[m] for m in models)
                ]
                assert summary[common_key]["rows"] == len(common)
                for name in models:
                    check_asr(common, name, thresholds[name], summary[common_key]["models"][name])
            transfer = []
            for row in subset:
                chosen = None
                if row["label"] == "phishing":
                    chosen = min(
                        [None] + row["candidates"],
                        key=lambda c: (
                            row["clean_scores"]["finetuned"]
                            if c is None
                            else c["scores"]["finetuned"]
                        ),
                    )
                transfer.append(row["clean_scores"] if chosen is None else chosen["scores"])
            for name, threshold in thresholds.items():
                assert_metrics(
                    recount(labels, [v[name] for v in transfer], threshold),
                    summary["parent_selected_transfer"]["models"][name],
                )
            for row in subset:
                earlier = stage6[row["example_id"]]
                assert (row["group_id"], row["label"], row["split"]) == (
                    earlier["group_id"],
                    earlier["label"],
                    earlier["split"],
                )
                for name in ("baseline_v2", "finetuned"):
                    assert row["clean_scores"][name] == earlier["clean_scores"][name]
                if bank == "fixed":
                    assert [v["variant_id"] for v in row["candidates"]] == [
                        v["variant_id"] for v in earlier["candidates"]
                    ]
                    for now, before in zip(row["candidates"], earlier["candidates"], strict=True):
                        for name in ("baseline_v2", "finetuned"):
                            assert now["scores"][name] == before["scores"][name]
    result = {
        "status": "verified",
        "preserved_files": len(preserved),
        "augmentation_model_bank_predictions_byte_identical": True,
        "training_history_and_validation_selection_identical": True,
        "prior_fixed_bank_scores_match_stage6_exactly": True,
        "independent_confusion_asr_common_transfer_query_recounts_match": True,
        "repeated_group_intervals_match": True,
        "reserve_parsed_or_scored": False,
        "prediction_records_across_two_banks": len(rows),
        "counts": counts,
    }
    Path("docs/reports/defense-verification.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "counts"}))


if __name__ == "__main__":
    main()
