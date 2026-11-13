"""Reproduce text-free IDs/counts for the completed post-score excerpt review."""

import hashlib
import json
from pathlib import Path

# Observations from the bounded local excerpt review, after checkpoint/score freeze.
# These are descriptive hypotheses, not verified labels or causal attributions.
OBSERVATIONS = {
    "meajor-trec5-021213": "Routine personal/corporate account transfer discussion; truncated.",
    "meajor-trec5-039720": "Ordinary ID setup notice mentions passwords and an attachment.",
    "nazario-2007-001139": (
        "Promotional selling-service content; text alone is ambiguous; truncated."
    ),
    "nazario-2007-000498": "Subscription/payment discussion with repeated padding; truncated.",
    "nazario-2007-001868": "Account-verification lure with markup and a long redirect; truncated.",
    "meajor-trec5-017924": "Correct legitimate payment discussion, despite financial vocabulary.",
    "nazario-2007-000316": "Correct phishing account-update notice with a suspension threat.",
    "meajor-trec6-064346": "Correct legitimate research announcement; truncated.",
    "zenodo-v3-1617": "Routine revised-document attachment and feedback message.",
    "zenodo-v3-0532": "Routine report attachment and meeting feedback request.",
    "zenodo-v3-0560": "Routine travel confirmation with attachment mention.",
    "zenodo-v3-1956": "Missed gift-card purchase request impersonating a colleague.",
    "zenodo-v3-0699": "Missed secure-message/transaction login lure.",
    "zenodo-v3-0172": "Missed overdue-invoice/payment-link lure.",
    "zenodo-v3-0500": "Correct urgent-payment/service-disconnection lure.",
    "zenodo-v3-1072": "Correct legitimate meeting-minutes attachment notice.",
    "zenodo-v3-0798": "Correct prize/gift-card claim lure.",
}


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def main():
    directory = Path("artifacts/finetuned-evaluation-v1")
    report = json.loads((directory / "report.json").read_bytes())
    selection = json.loads(Path("data/manifests/finetuned-v1-selection.json").read_bytes())
    assert report["selection"] == selection
    payload = (directory / "predictions.jsonl").read_bytes()
    assert digest(payload) == report["predictions_sha256"]
    rows = [json.loads(line) for line in payload.splitlines()]

    def category(row):
        predicted = row["finetuned_score"] >= selection["threshold"]
        truth = row["label"] == "phishing"
        if predicted == truth:
            return "correct"
        return "false_positive" if predicted else "false_negative"

    sample, counts = [], {}
    for cohort in ("test", "challenge"):
        counts[cohort] = {}
        for kind in ("false_positive", "false_negative", "correct"):
            eligible = [r for r in rows if r["cohort"] == cohort and category(r) == kind]
            counts[cohort][kind] = {
                "rows": len(eligible),
                "truncated_rows": sum(r["original_tokens"] > 256 for r in eligible),
            }
            chosen = sorted(
                eligible,
                key=lambda r: digest(("stage5-review:" + r["example_id"]).encode()),
            )[:3]
            for row in chosen:
                sample.append(
                    {**row, "category": kind, "observation": OBSERVATIONS[row["example_id"]]}
                )
    assert {row["example_id"] for row in sample} == set(OBSERVATIONS)
    result = {
        "phase": "post-freeze post-score error review",
        "review_date": "2026-11-14",
        "reviewer": "AI-assisted local excerpt review; individual student review remains open",
        "selection": selection,
        "predictions_sha256": digest(payload),
        "sampling": "First 3 per cohort/category by SHA256(stage5-review:<ID>); all if fewer",
        "sample_rows": len(sample),
        "review_scope": "Subject and first 1400 body characters; full short challenge texts",
        "counts": counts,
        "sample": sample,
        "raw_text_published": False,
        "reserve_rows_reviewed_or_scored": 0,
        "labels_weights_thresholds_changed": False,
        "limitations": [
            "A bounded descriptive sample, not exhaustive error or label adjudication.",
            "Publisher labels retained; sender, attachment and link authenticity not verified.",
            "Truncation/error associations are not causal evidence.",
            "Correct controls share topics with errors, so keyword explanations are insufficient.",
            "Retrospective benchmarks cannot become fresh final evidence through this review.",
        ],
    }
    Path("docs/reports/finetuned-error-review.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"reviewed_ids_reproduced": len(sample), "raw_email_files_opened": 0}))


if __name__ == "__main__":
    main()
