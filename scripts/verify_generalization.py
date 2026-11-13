"""Independently recount saved predictions and compare two frozen audit runs.

Run from the repository root after the reproduction commands in the audit guide.
Uses the standard library only; never fits, scores or prints email content.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def main():
    dataset = Path("data/processed/external-mail-v1")
    repeated = Path("data/processed/external-mail-reproduction")
    experiment = Path("artifacts/generalization-external-v1")
    rerun = Path("artifacts/generalization-external-reproduction")
    manifest_bytes = Path("data/manifests/external-mail-v1.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    for name in ("manifest.json", "audit.jsonl", "reserve.jsonl"):
        content = (dataset / name).read_bytes()
        assert content == (repeated / name).read_bytes(), name
        if name == "manifest.json":
            assert content == manifest_bytes
        else:
            assert digest(content) == manifest["files"][name]["sha256"]
    # Reserve bytes are hashed for integrity only, never parsed or passed to a model.
    payload = (experiment / "predictions.jsonl").read_bytes()
    assert payload == (rerun / "predictions.jsonl").read_bytes()
    report = json.loads((experiment / "report.json").read_bytes())
    second = json.loads((rerun / "report.json").read_bytes())
    for key in ("metrics", "per_source", "group_bootstrap", "audit_ids_sha256"):
        assert report[key] == second[key], key
    assert report["predictions_sha256"] == digest(payload)
    assert report["external_manifest_sha256"] == digest(manifest_bytes)
    assert report["model_revision"] == digest(Path("models/baseline-v1/model.json").read_bytes())
    assert report["threshold"] == manifest["protocol"]["baseline_threshold"]
    assert report["weights_updated"] is False and report["threshold_updated"] is False
    assert report["reserve_rows_scored"] == second["reserve_rows_scored"] == 0
    predictions = [json.loads(line) for line in payload.splitlines()]
    predicted_ids = [r["example_id"] for r in predictions]
    audit_ids = {rid for g in manifest["groups"] if g["cohort"] == "audit" for rid in g["members"]}
    reserve_ids = {
        rid for g in manifest["groups"] if g["cohort"] == "reserve" for rid in g["members"]
    }
    assert len(predicted_ids) == len(set(predicted_ids))
    assert set(predicted_ids) == audit_ids and not set(predicted_ids) & reserve_ids
    counts = Counter()
    for row in predictions:
        predicted = "phishing" if row["score"] >= report["threshold"] else "legitimate"
        assert row["decision"] == predicted
        key = {
            ("phishing", "phishing"): "tp",
            ("phishing", "legitimate"): "fn",
            ("legitimate", "phishing"): "fp",
            ("legitimate", "legitimate"): "tn",
        }[(row["label"], predicted)]
        counts[key] += 1
    assert dict(counts) == report["metrics"]["confusion"]
    assert report["metrics"]["accuracy"] == (counts["tp"] + counts["tn"]) / len(predictions)
    result = {
        "status": "verified",
        "independent_confusion": dict(sorted(counts.items())),
        "preparation_byte_identical": True,
        "prediction_byte_identical": True,
        "metrics_and_intervals_identical": True,
        "frozen_model_unchanged": True,
        "reserve_rows_scored": 0,
        "reserve_integrity_verified_without_parsing": True,
        "reserve_rows": len(reserve_ids),
        "audit_rows": len(audit_ids),
        "model_revision": report["model_revision"],
        "threshold": report["threshold"],
        "external_manifest_sha256": digest(manifest_bytes),
        "predictions_sha256": digest(payload),
        "evaluation_code": report["code"],
    }
    destination = Path("docs/reports/generalization-verification.json")
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
