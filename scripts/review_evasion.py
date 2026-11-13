"""Select bounded successful-candidate IDs; verify separately recorded review decisions."""

import argparse
import hashlib
import json
from pathlib import Path

from verify_refresh import digest, read


def selection():
    report = read("artifacts/evasion-evaluation-v1/report.json")
    payload = Path("artifacts/evasion-evaluation-v1/predictions.jsonl").read_bytes()
    assert digest(payload) == report["predictions_sha256"]
    rows = [json.loads(line) for line in payload.splitlines()]
    policy = report["protocol"]
    chosen = []
    for cohort in ("test", "challenge"):
        for model, threshold in (
            ("baseline_v2", policy["baseline_threshold"]),
            ("finetuned", policy["finetuned_threshold"]),
        ):
            for operation in policy["operations"]:
                eligible = []
                for row in rows:
                    if (
                        row["cohort"] != cohort
                        or row["label"] != "phishing"
                        or row["clean_scores"][model] < threshold
                    ):
                        continue
                    for candidate in row["candidates"]:
                        if (
                            candidate["operation"] == operation
                            and candidate["scores"][model] < threshold
                        ):
                            eligible.append(
                                {
                                    "cohort": cohort,
                                    "model": model,
                                    "operation": operation,
                                    "parent_id": row["example_id"],
                                    "group_id": row["group_id"],
                                    "variant_id": candidate["variant_id"],
                                    "clean_score": row["clean_scores"][model],
                                    "variant_score": candidate["scores"][model],
                                    "threshold": threshold,
                                }
                            )
                eligible.sort(
                    key=lambda r: hashlib.sha256(
                        f"stage6-postreview:{cohort}:{model}:{operation}:{r['variant_id']}".encode()
                    ).hexdigest()
                )
                chosen.extend(eligible[:2])
    return report, chosen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("select", "verify"))
    args = parser.parse_args()
    report, chosen = selection()
    if args.action == "select":
        output = Path("artifacts/evasion-review-v1")
        output.mkdir(parents=True, exist_ok=False)
        (output / "sample.json").write_text(
            json.dumps(chosen, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "review_cases": len(chosen),
                    "distinct_variants": len({r["variant_id"] for r in chosen}),
                }
            )
        )
        return
    review = read("docs/reports/evasion-label-review.json")
    assert review["predictions_sha256"] == report["predictions_sha256"]
    assert (
        [{k: r[k] for k in chosen[0]} for r in review["cases"]] == chosen
        if chosen
        else not review["cases"]
    )
    counts = {}
    for cohort, results in report["cohorts"].items():
        counts[cohort] = {}
        for model, values in results["models"].items():
            cases = [r for r in review["cases"] if r["cohort"] == cohort and r["model"] == model]
            for row in cases:
                assert row["decision"] in {"supported", "ambiguous", "invalid"}
                assert row["observation"].strip()
            supported = {r["parent_id"] for r in cases if r["decision"] == "supported"}
            eligible = values["evasion"]["eligible_clean_detected_phishing"]
            counts[cohort][model] = {
                "review_cases": len(cases),
                "supported_cases": sum(r["decision"] == "supported" for r in cases),
                "ambiguous_cases": sum(r["decision"] == "ambiguous" for r in cases),
                "invalid_cases": sum(r["decision"] == "invalid" for r in cases),
                "distinct_supported_phishing_originals": len(supported),
                "eligible_clean_detected_phishing": eligible,
                "review_supported_asr_lower_bound": len(supported) / eligible if eligible else None,
                "status": "Bounded AI-assisted contextual review; not exhaustive human certification",
            }
    output = {
        "status": "verified",
        "cases": len(chosen),
        "counts": counts,
        "predictions_sha256": report["predictions_sha256"],
        "selection_policy": "First two SHA256-ranked successes per cohort/model/operation",
        "labels_models_thresholds_or_protocol_changed": False,
        "reserve_rows_reviewed_or_scored": 0,
    }
    Path("docs/reports/evasion-reviewed-evidence.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
