"""Predetermined text-free review IDs; contextual decisions remain a separate review."""

import argparse
import hashlib
import json
from pathlib import Path


def sample():
    report = json.loads(Path("artifacts/defense-evaluation-v1/report.json").read_bytes())
    rows = [
        json.loads(line)
        for line in Path("artifacts/defense-evaluation-v1/predictions.jsonl")
        .read_bytes()
        .splitlines()
    ]
    threshold = report["thresholds"]["defended"]
    selected = []
    for cohort in ("test", "challenge"):
        for operation in ("duplicate_letter", "swap_letters", "substitute_word"):
            candidates = []
            for row in rows:
                if (
                    row["bank"] != "fresh"
                    or row["cohort"] != cohort
                    or row["label"] != "phishing"
                    or row["clean_scores"]["defended"] < threshold
                ):
                    continue
                candidates.extend(
                    {
                        "cohort": cohort,
                        "parent_id": row["example_id"],
                        "variant_id": v["variant_id"],
                        "operation": operation,
                    }
                    for v in row["candidates"]
                    if v["operation"] == operation and v["scores"]["defended"] < threshold
                )
            selected.extend(
                sorted(
                    candidates,
                    key=lambda v: hashlib.sha256(
                        f"postreview:{cohort}:{operation}:{v['variant_id']}".encode()
                    ).hexdigest(),
                )[:2]
            )
    return selected, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["select", "verify"])
    args = parser.parse_args()
    selected, report = sample()
    if args.action == "select":
        path = Path("artifacts/defense-review-v1")
        path.mkdir(parents=True, exist_ok=False)
        (path / "sample.json").write_text(json.dumps(selected, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"selected": len(selected)}))
        return
    review = json.loads(Path("docs/reports/defense-label-review.json").read_bytes())
    assert review["predictions_sha256"] == report["predictions_sha256"]
    assert [
        {k: r[k] for k in ("cohort", "parent_id", "variant_id", "operation")}
        for r in review["decisions"]
    ] == selected
    assert all(r["decision"] in {"supported", "ambiguous", "invalid"} for r in review["decisions"])
    result = {
        "status": "verified",
        "reviewed_variants": len(selected),
        "cohorts": {},
        "limitation": "Bounded AI-assisted contextual review, "
        "not exhaustive human semantic certification.",
    }
    for cohort in ("test", "challenge"):
        supported = {
            r["parent_id"]
            for r in review["decisions"]
            if r["cohort"] == cohort and r["decision"] == "supported"
        }
        denominator = report["banks"]["fresh"][cohort]["models"]["defended"]["evasion"][
            "eligible_clean_detected_phishing"
        ]
        result["cohorts"][cohort] = {
            "distinct_supported_originals": len(supported),
            "eligible_clean_detected_phishing": denominator,
            "review_supported_lower_bound": len(supported) / denominator if denominator else None,
        }
    Path("docs/reports/defense-reviewed-evidence.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
