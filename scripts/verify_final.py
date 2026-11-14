"""Independent final-run recount and complete numerical reproduction verification."""

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from verify_evasion import check_asr
from verify_refresh import assert_metrics, recount


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def lines(path):
    return [json.loads(line) for line in Path(path).read_bytes().splitlines()]


def metrics(labels, scores, threshold):
    return recount(
        [{"label": label, "x_score": score} for label, score in zip(labels, scores, strict=True)],
        "x",
        threshold,
    )


def main():
    primary = Path("artifacts/final-evaluation-v1")
    repeated = Path("artifacts/final-evaluation-repeat-v1")
    report = read(primary / "report.json")
    repeat = read(repeated / "report.json")
    preregistration = "77c4a17777d92abf653d7fd13746ba4e384eeb5a"
    assert (
        report["code"]
        == repeat["code"]
        == {
            "commit": preregistration,
            "working_tree_dirty": False,
        }
    )
    for name, key in [("predictions.jsonl", "predictions_sha256"), ("bank.jsonl", None)]:
        payload = (primary / name).read_bytes()
        assert payload == (repeated / name).read_bytes(), name
        expected = report[key] if key else report["bank"]["sha256"]
        assert hashlib.sha256(payload).hexdigest() == expected
    rows = lines(primary / "predictions.jsonl")
    bank = lines(primary / "bank.jsonl")
    original = {r["example_id"]: r for r in lines("data/processed/external-mail-v1/reserve.jsonl")}
    assert len(rows) == len(original) == 703
    assert len({r["example_id"] for r in rows}) == 703
    assert {r["example_id"] for r in rows} == set(original)
    assert len({r["group_id"] for r in rows}) == 432
    assert Counter(r["label"] for r in rows) == {"legitimate": 479, "phishing": 224}
    bank_by_id = {v["variant_id"]: v for v in bank}
    assert len(bank_by_id) == len(bank) == report["bank"]["variants"]
    for p in rows:
        parent = original[p["example_id"]]
        assert all(p[k] == parent[k] for k in ("label", "group_id", "source_id"))
        assert parent["split"] == "unassigned" and p["split"] == "test"
        assert len(p["candidates"]) <= 12
        for c in p["candidates"]:
            v = bank_by_id[c["variant_id"]]
            assert v["parent_id"] == p["example_id"]
            assert all(v[k] == p[k] for k in ("label", "group_id", "source_id", "cohort", "split"))
            assert v["candidate_index"] == c["candidate_index"]
            assert v["seed"] == 9042 and len(v["edits"]) == v["changed_words"] <= 3
            assert v["changed_words"] <= math.floor(v["body_words"] * 0.1)
            assert v["email"]["subject"] == parent["email"]["subject"]
            body = parent["email"]["body"]
            boundary = len(body) + 1
            for edit in reversed(v["edits"]):
                a, b = edit["start"], edit["end"]
                assert 0 <= a < b <= min(1500, boundary)
                assert body[a:b] == edit["before"]
                body = body[:a] + edit["after"] + body[b:]
                boundary = a
            assert body == v["email"]["body"]
    labels = [r["label"] for r in rows]
    summary = report["robustness"]
    counts = {}
    for name, identity in report["model_revisions_and_thresholds"].items():
        threshold = identity["threshold"]
        values = [r["clean_scores"][name] for r in rows]
        actual = metrics(labels, values, threshold)
        assert_metrics(actual, report["clean"][name]["metrics"])
        counts[name] = {"clean": actual["confusion"]}
        assert report["clean"][name]["group_bootstrap"] == repeat["clean"][name]["group_bootstrap"]
        for source, wanted in report["clean"][name]["per_source"].items():
            subset = [r for r in rows if r["source_id"] == source]
            assert_metrics(
                metrics(
                    [r["label"] for r in subset],
                    [r["clean_scores"][name] for r in subset],
                    threshold,
                ),
                wanted,
            )
        if name == "pretrained":
            assert report["clean"][name]["tokens"]["truncated_rows"] == sum(
                r["pretrained_original_tokens"] > 512 for r in rows
            )
            continue
        model = summary["models"][name]
        for view, values in {
            "clean": [r["clean_scores"][name] for r in rows],
            "fixed_perturbation": [
                r["candidates"][0]["scores"][name] if r["candidates"] else r["clean_scores"][name]
                for r in rows
            ],
            "phishing_only_worst_of_budget": [
                min([r["clean_scores"][name]] + [v["scores"][name] for v in r["candidates"]])
                if r["label"] == "phishing"
                else r["clean_scores"][name]
                for r in rows
            ],
        }.items():
            expected = metrics(labels, values, threshold)
            expected.pop("balanced_accuracy")
            assert_metrics(expected, model[view])
            counts[name][view] = expected["confusion"]
        check_asr(rows, name, threshold, model["evasion"])
        for op, wanted in model["evasion_by_operation"].items():
            check_asr(rows, name, threshold, wanted, op)
        for source, wanted in model["per_source"].items():
            check_asr([r for r in rows if r["source_id"] == source], name, threshold, wanted)
        assert model["actual_queries"] == 703 + len(bank)
        assert model["maximum_queries_per_original"] <= 13
        assert (
            report["clean"][name]["tokens"]["truncated_rows"]
            == sum(r["clean_neural_inputs"][name]["original_tokens"] > 256 for r in rows)
            if name != "baseline_v2"
            else True
        )
    for key, names in [
        ("common_clean_detected_phishing", ["baseline_v2", "finetuned", "defended"]),
        ("parent_defense_common_detected", ["finetuned", "defended"]),
    ]:
        subset = [
            r
            for r in rows
            if r["label"] == "phishing"
            and all(
                r["clean_scores"][m] >= report["model_revisions_and_thresholds"][m]["threshold"]
                for m in names
            )
        ]
        assert len(subset) == summary[key]["rows"]
        for name in names:
            check_asr(
                subset,
                name,
                report["model_revisions_and_thresholds"][name]["threshold"],
                summary[key]["models"][name],
            )

    def strip_runtime(value):
        if isinstance(value, dict):
            return {
                k: strip_runtime(v)
                for k, v in value.items()
                if k not in {"code", "environment", "inference_seconds", "scoring_seconds"}
            }
        if isinstance(value, list):
            return [strip_runtime(v) for v in value]
        return value

    assert strip_runtime(report) == strip_runtime(repeat)
    frozen = read("data/manifests/final-evaluation-freeze-v1.json")
    for name, meta in frozen["preserved_inputs"].items():
        path = Path(name)
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        assert path.stat().st_size == meta["bytes"] and actual == meta["sha256"]
    result = {
        "status": "verified",
        "evaluation_code_commit": preregistration,
        "both_run_worktrees_clean": True,
        "reserve_rows": 703,
        "reserve_groups": 432,
        "predictions_identical": True,
        "candidate_bank_identical": True,
        "repeated_metrics_intervals_and_review_selection_identical": True,
        "preserved_files": len(frozen["preserved_inputs"]),
        "counts": counts,
        "bank_variants": len(bank),
        "queries_per_robustness_model": 703 + len(bank),
        "maximum_queries_per_parent": max(1 + len(r["candidates"]) for r in rows),
        "predictions_sha256": report["predictions_sha256"],
        "bank_sha256": report["bank"]["sha256"],
        "models_or_thresholds_updated": False,
        "scope": "Independent counts, lineage/replay, query caps, exact full-run repeat and "
        "file preservation; not new independent data or semantic certification.",
    }
    Path("artifacts/final-independent-verification.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
