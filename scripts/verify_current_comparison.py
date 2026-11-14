"""Independent count/identity/preservation checks; never parse the final reserve."""

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from phishguard.comparison import DATA, DATA_REFERENCE, checked_selection
from phishguard.finetune.common import partition, study


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify(root=Path("artifacts/comparison-v1")):
    report = read(root / "report.json")
    payload = (root / "predictions.jsonl").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == report["predictions_sha256"]
    predictions = [json.loads(line) for line in payload.splitlines()]
    assert len(predictions) == 2423
    selection = checked_selection()
    assert report["selection"]["threshold"] == selection.threshold
    frozen = study(DATA, DATA_REFERENCE)
    prior = read("docs/reports/finetuned-evaluation.json")
    defense = read("docs/reports/defense-evaluation.json")
    outcomes = {}
    for cohort in ("test", "challenge"):
        rows = {r.example_id: r for r in partition(frozen, cohort)}
        scored = [r for r in predictions if r["cohort"] == cohort]
        assert len(scored) == len(rows)
        assert {r["example_id"] for r in scored} == set(rows)
        assert len({r["example_id"] for r in scored}) == len(scored)
        for p in scored:
            row = rows[p["example_id"]]
            assert all(p[k] == getattr(row, k) for k in ("label", "group_id", "source_id"))
        outcomes[cohort] = {}
        for name, result in report["cohorts"][cohort]["results"].items():
            m = result["metrics"]
            counts = Counter()
            for p in scored:
                score = p["scores"][name]
                assert math.isfinite(score) and 0 <= score <= 1
                positive = score >= m["threshold"]
                truth = p["label"] == "phishing"
                counts[
                    "tp" if truth and positive else "fn" if truth else "fp" if positive else "tn"
                ] += 1
            counts = {k: counts[k] for k in ("tp", "fp", "tn", "fn")}
            assert counts == m["confusion"]
            assert m["accuracy"] == (counts["tp"] + counts["tn"]) / len(scored)
            assert m["recall"] == counts["tp"] / (counts["tp"] + counts["fn"])
            assert m["false_positive_rate"] == counts["fp"] / (counts["fp"] + counts["tn"])
            assert m["f1"] == 2 * counts["tp"] / (2 * counts["tp"] + counts["fp"] + counts["fn"])
            if name in {"baseline_v2", "finetuned"}:
                assert m == prior["cohorts"][cohort]["results"][name]["metrics"]
            elif name == "defended":
                old = defense["banks"]["fixed"][cohort]["models"][name]["clean"]
                assert {k: m[k] for k in old} == old
            outcomes[cohort][name] = counts
        tokens = report["cohorts"][cohort]["pretrained_tokens"]
        assert tokens["truncated_rows"] == sum(
            r["original_tokens"]["pretrained"] > 512 for r in scored
        )
    snapshot = read("data/manifests/demo-preserved-inputs-v1.json")
    for name, meta in snapshot.items():
        path = Path(name)
        assert path.stat().st_size == meta["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == meta["sha256"]
    result = {
        "status": "verified",
        "rows": len(predictions),
        "confusion_counts": outcomes,
        "prior_three_models_clean_metrics_reproduced": True,
        "preserved_files": len(snapshot),
        "reserve_text_parsed_or_scored": False,
        "predictions_sha256": report["predictions_sha256"],
        "scope": "Independent counts and preservation; not a second full pretrained inference run.",
    }
    Path("docs/reports/current-comparison-verification.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
