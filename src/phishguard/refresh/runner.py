"""Separate real-mail fitting and frozen held-out comparisons; never score the reserve."""

import time
from collections import Counter

from phishguard.audit.common import AuditError
from phishguard.audit.runner import intervals, measures, save
from phishguard.baseline.common import code_revision, environment, parse_json, read_bytes
from phishguard.baseline.model import fit_baseline, load_model, save_model, text_hash
from phishguard.datasets.preparation import json_bytes
from phishguard.refresh.common import PROTOCOL, PROTOCOL_SHA256, SOURCE_SHA256
from phishguard.refresh.data import FrozenStudy


def identity(study):
    return {
        "report_version": "1.0",
        "protocol_sha256": PROTOCOL_SHA256,
        "source_sha256": SOURCE_SHA256,
        "dataset_manifest_sha256": study.sha256,
        "environment": environment(),
        "code": code_revision(),
        "reserve_rows_scored": 0,
    }


def train(directory, reference, output):
    if output.exists():
        raise AuditError("output_already_exists")
    study = FrozenStudy(directory, reference)
    training, validation = study.load("train"), study.load("validation")
    model, details = fit_baseline(training, validation, study.sha256)
    manifest = save_model(model, output)
    scores = details.pop("validation_scores")
    selection = {
        "dataset_sha256": study.sha256,
        "model_revision": model.revision,
        "protocol_sha256": PROTOCOL_SHA256,
        "threshold": model.state.threshold,
    }
    (output / "selection.json").write_bytes(json_bytes(selection))
    report = {
        **identity(study),
        "phase": "real-mail-train-validation",
        "model": manifest.model_dump(),
        "selection": selection,
        "fit_rows": len(training),
        "validation_rows": len(validation),
        "test_rows_used": 0,
        "challenge_rows_used": 0,
        "training_metrics": measures(
            training, model.scores([r.email for r in training]), model.state.threshold
        ),
        "validation_metrics": measures(validation, scores, model.state.threshold),
        "validation_at_default_threshold": measures(validation, scores, 0.5),
        **details,
    }
    (output / "training-report.json").write_bytes(json_bytes(report))
    return report


def evaluate(directory, reference, model_directory, old_directory, selection_reference, output):
    if output.exists():
        raise AuditError("output_already_exists")
    study = FrozenStudy(directory, reference)
    model, old = load_model(model_directory), load_model(old_directory)
    selection_bytes = read_bytes(model_directory / "selection.json")
    if selection_bytes != read_bytes(selection_reference):
        raise AuditError("selection_reference_mismatch")
    selection = parse_json(selection_bytes)
    expected = {
        "dataset_sha256": study.sha256,
        "model_revision": model.revision,
        "protocol_sha256": PROTOCOL_SHA256,
        "threshold": model.state.threshold,
    }
    if (
        selection != expected
        or model.state.dataset_sha256 != study.sha256
        or old.revision != PROTOCOL["old_model_revision"]
        or old.state.dataset_sha256 != PROTOCOL["internal_manifest_sha256"]
    ):
        raise AuditError("refresh_model_mismatch")
    report = {
        **identity(study),
        "phase": "real-mail-heldout-comparison",
        "selection": selection,
        "old_model_revision": old.revision,
        "old_threshold": old.state.threshold,
        "model_weights_updated": False,
        "thresholds_updated": False,
        "cohorts": {},
        "limitations": [
            "Historical sources remain confounded with class; no contemporary-inbox claim.",
            "Publisher labels and heuristic groups are not independently verified truth.",
            "Challenge is mainly templated synthetic text; "
            "original subset provenance is unverified.",
            "Results are stage-4b benchmarks, not untouched final project evidence.",
            "No transformer training, adversarial evaluation or calibrated probabilities.",
        ],
    }
    predictions = []
    for split in ("test", "challenge"):
        rows = study.load(split)  # Training and validation files are never opened here.
        hashes = {text_hash(r.email) for r in rows}
        if any(hashes & set(m.state.development_text_hashes) for m in (old, model)):
            raise AuditError("preprocessed_evaluation_leakage")
        results, all_scores = {}, {}
        for name, candidate in (("baseline_v1", old), ("baseline_v2", model)):
            started = time.perf_counter()
            scores = candidate.scores([r.email for r in rows])
            elapsed = time.perf_counter() - started
            threshold = candidate.state.threshold
            all_scores[name] = scores
            sources = {}
            for source in sorted({r.source_id for r in rows}):
                indices = [i for i, r in enumerate(rows) if r.source_id == source]
                sources[source] = measures(
                    [rows[i] for i in indices], [scores[i] for i in indices], threshold
                )
            results[name] = {
                "metrics": measures(rows, scores, threshold),
                "per_source": sources,
                "group_bootstrap": intervals(rows, scores, threshold),
                "threshold": threshold,
                "batch_inference_seconds": elapsed,
            }
        paired = Counter()
        for i, row in enumerate(rows):
            first = all_scores["baseline_v1"][i] >= old.state.threshold
            second = all_scores["baseline_v2"][i] >= model.state.threshold
            truth = row.label == "phishing"
            paired[
                {
                    (True, True): "both_correct",
                    (False, False): "both_wrong",
                    (True, False): "v1_only_correct",
                    (False, True): "v2_only_correct",
                }[(first == truth, second == truth)]
            ] += 1
            predictions.append(
                {
                    "cohort": split,
                    "example_id": row.example_id,
                    "group_id": row.group_id,
                    "source_id": row.source_id,
                    "label": row.label,
                    "v1_score": all_scores["baseline_v1"][i],
                    "v2_score": all_scores["baseline_v2"][i],
                }
            )
        report["cohorts"][split] = {
            "rows": len(rows),
            "groups": len({r.group_id for r in rows}),
            "results": results,
            "paired_correctness": dict(paired),
        }
    if (
        load_model(model_directory).revision != model.revision
        or load_model(old_directory).revision != old.revision
    ):
        raise AuditError("model_changed_during_evaluation")
    return save(output, report, predictions)
