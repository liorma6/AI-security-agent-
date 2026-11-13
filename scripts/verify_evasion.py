"""Independently recount fixed experiments and hash preserved inputs, not reserve text."""

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from verify_refresh import assert_metrics, digest, read, recount


def records(path):
    return [json.loads(line) for line in Path(path).read_bytes().splitlines()]


def check_asr(rows, model, threshold, expected, operation=None):
    eligible = [
        r for r in rows if r["label"] == "phishing" and r["clean_scores"][model] >= threshold
    ]
    covered = success = queries = 0
    for row in eligible:
        values = [
            c["scores"][model]
            for c in row["candidates"]
            if operation is None or c["operation"] == operation
        ]
        covered += bool(values)
        success += bool(values) and min(values) < threshold
        queries += len(values)
    assert expected["eligible_clean_detected_phishing"] == len(eligible)
    assert expected["eligible_with_candidates"] == covered
    assert expected["eligible_without_candidates"] == len(eligible) - covered
    assert expected["constraint_pass_successes"] == success
    assert expected["candidate_asr"] == (success / len(eligible) if eligible else None)
    assert expected["candidate_asr_among_covered"] == (success / covered if covered else None)
    assert expected["coverage"] == (covered / len(eligible) if eligible else None)
    assert expected["candidate_queries_on_eligible"] == queries


def main():
    policy = read("src/phishguard/evasion/protocol.json")
    preserved = read("data/manifests/evasion-preserved-inputs-v1.json")
    for name, meta in preserved.items():
        path = Path(name)
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        assert path.stat().st_size == meta["bytes"] and actual == meta["sha256"], name
    bank = Path("artifacts/evasion-variants-v1")
    repeated_bank = Path("artifacts/evasion-variants-reproduction-v1")
    for name in ("variants.jsonl", "manifest.json"):
        assert (bank / name).read_bytes() == (repeated_bank / name).read_bytes(), name
    bank_manifest = Path("data/manifests/evasion-variants-v1.json").read_bytes()
    assert (bank / "manifest.json").read_bytes() == bank_manifest
    manifest = json.loads(bank_manifest)
    assert manifest["protocol"] == policy
    variant_payload = (bank / "variants.jsonl").read_bytes()
    assert digest(variant_payload) == manifest["files"]["variants.jsonl"]["sha256"]
    variants = {r["variant_id"]: r for r in records(bank / "variants.jsonl")}
    assert len(variants) == manifest["variants"]
    originals = {}
    for cohort in ("test", "challenge"):
        for row in records(f"data/processed/real-mail-v2/{cohort}.jsonl"):
            originals[(cohort, row["example_id"])] = row
    for variant in variants.values():
        row = originals[(variant["cohort"], variant["parent_id"])]
        assert (row["group_id"], row["split"], row["label"]) == (
            variant["group_id"],
            variant["split"],
            variant["label"],
        )
        before = row["email"]
        body = before["body"]
        last = len(body)
        for edit in reversed(variant["edits"]):
            assert 0 <= edit["start"] < edit["end"] <= last
            assert before["body"][edit["start"] : edit["end"]] == edit["before"]
            assert edit["end"] <= policy["editable_body_prefix_characters"]
            body = body[: edit["start"]] + edit["after"] + body[edit["end"] :]
            last = edit["start"]
        assert variant["email"]["body"] == body
        assert variant["email"]["subject"] == before["subject"]
        assert variant["changed_words"] == len(variant["edits"]) <= policy["max_edits"]
        assert len(variant["edits"]) <= math.floor(variant["body_words"] * 0.1)
    first, second = (
        Path("artifacts/evasion-evaluation-v1"),
        Path("artifacts/evasion-reproduction-v1"),
    )
    report, repeated = read(first / "report.json"), read(second / "report.json")
    payload = (first / "predictions.jsonl").read_bytes()
    assert payload == (second / "predictions.jsonl").read_bytes()
    assert digest(payload) == report["predictions_sha256"] == repeated["predictions_sha256"]
    assert report["bank_manifest_sha256"] == digest(bank_manifest)
    rows = records(first / "predictions.jsonl")
    earlier = {
        r["example_id"]: r for r in records("artifacts/finetuned-evaluation-v1/predictions.jsonl")
    }
    assert len(rows) == len(earlier) and {r["example_id"] for r in rows} == set(earlier)
    scored_variants = []
    maximum_clean_drift = 0.0
    for row in rows:
        old = earlier[row["example_id"]]
        assert (row["cohort"], row["group_id"], row["label"]) == (
            old["cohort"],
            old["group_id"],
            old["label"],
        )
        assert row["clean_scores"]["baseline_v2"] == old["baseline_score"]
        delta = abs(row["clean_scores"]["finetuned"] - old["finetuned_score"])
        assert delta <= 1e-6
        maximum_clean_drift = max(delta, maximum_clean_drift)
        assert 1 + len(row["candidates"]) <= policy["maximum_model_queries_per_parent"]
        for index, candidate in enumerate(row["candidates"], 1):
            scored_variants.append(candidate["variant_id"])
            variant = variants[candidate["variant_id"]]
            assert candidate["candidate_index"] == variant["candidate_index"] == index
            assert variant["parent_id"] == row["example_id"] and variant["cohort"] == row["cohort"]
            assert candidate["operation"] == variant["operation"]
            assert all(math.isfinite(v) and 0 <= v <= 1 for v in candidate["scores"].values())
    assert len(scored_variants) == len(set(scored_variants)) == len(variants)
    assert set(scored_variants) == set(variants)
    counts = {}
    thresholds = {
        "baseline_v2": policy["baseline_threshold"],
        "finetuned": policy["finetuned_threshold"],
    }
    for cohort, summary in report["cohorts"].items():
        subset = [r for r in rows if r["cohort"] == cohort]
        counts[cohort] = {}
        assert summary["models"] == repeated["cohorts"][cohort]["models"]
        assert (
            summary["common_clean_detected_phishing"]
            == repeated["cohorts"][cohort]["common_clean_detected_phishing"]
        )
        for model, threshold in thresholds.items():
            measured = summary["models"][model]
            views = {
                key: [] for key in ("clean", "fixed_perturbation", "phishing_only_worst_of_budget")
            }
            paired = Counter()
            for row in subset:
                clean = row["clean_scores"][model]
                candidates = [c["scores"][model] for c in row["candidates"]]
                fixed = candidates[0] if candidates else clean
                directed = min([clean, *candidates]) if row["label"] == "phishing" else clean
                for name, score in zip(views, (clean, fixed, directed), strict=True):
                    views[name].append({"label": row["label"], "value_score": score})
                truth = row["label"] == "phishing"
                pair = ((clean >= threshold) == truth, (fixed >= threshold) == truth)
                paired[
                    {
                        (True, True): "both_correct",
                        (False, False): "both_wrong",
                        (True, False): "clean_only_correct",
                        (False, True): "fixed_only_correct",
                    }[pair]
                ] += 1
            assert dict(paired) == measured["fixed_paired_correctness"]
            counts[cohort][model] = {}
            for name, records_ in views.items():
                recounted = recount(records_, "value", threshold)
                recounted.pop("balanced_accuracy")
                assert_metrics(recounted, measured[name])
                counts[cohort][model][name] = recounted
            check_asr(subset, model, threshold, measured["evasion"])
            for operation, expected in measured["evasion_by_operation"].items():
                check_asr(subset, model, threshold, expected, operation)
            for source, expected in measured["per_source"].items():
                check_asr(
                    [r for r in subset if r["source_id"] == source], model, threshold, expected
                )
            assert measured["actual_queries"] == len(subset) + sum(
                len(r["candidates"]) for r in subset
            )
            common = [
                r
                for r in subset
                if r["label"] == "phishing"
                and all(r["clean_scores"][m] >= t for m, t in thresholds.items())
            ]
            assert summary["common_clean_detected_phishing"]["rows"] == len(common)
            check_asr(
                common, model, threshold, summary["common_clean_detected_phishing"]["models"][model]
            )
    result = {
        "status": "passed",
        "originals": len(rows),
        "variants": len(variants),
        "candidate_bank_and_predictions_byte_identical": True,
        "independent_confusion_asr_coverage_paired_source_and_query_counts_match": True,
        "repeated_group_intervals_match": True,
        "parent_group_split_label_and_edit_replay_verified": True,
        "preserved_model_and_processed_data_files": len(preserved),
        "preserved_files_unchanged": True,
        "clean_baseline_scores_match_stage5": True,
        "maximum_clean_transformer_score_drift": maximum_clean_drift,
        "reserve_content_parsed": False,
        "reserve_rows_scored": 0,
        "counts": counts,
    }
    Path("docs/reports/evasion-verification.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "counts"}))


if __name__ == "__main__":
    main()
