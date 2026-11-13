"""Separate training/threshold selection from immutable final evaluation."""

import json
import time
from pathlib import Path

from phishguard.baseline.common import (
    MODEL_ID,
    PROTOCOL,
    PROTOCOL_SHA256,
    BaselineError,
    code_revision,
    environment,
)
from phishguard.baseline.data import FrozenDataset
from phishguard.baseline.metrics import metrics
from phishguard.baseline.model import fit_baseline, load_model, save_model, text_hash
from phishguard.baseline.preprocessing import MARKER, preprocess
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest


def shortcut_diagnostic(records) -> dict:
    labels = [PROTOCOL["label_mapping"][r.label] for r in records]
    flags = [int(bool(MARKER.search(r.email.text))) for r in records]
    return {
        "marker_rows_by_label": {
            label: sum(flag for r, flag in zip(records, flags, strict=True) if r.label == label)
            for label in PROTOCOL["label_mapping"]
        },
        "marker_presence_rule": metrics(labels, flags, 0.5),
        "remaining_markers_after_preprocessing": sum(
            bool(MARKER.search(preprocess(r.email.text))) for r in records
        ),
    }


def train_baseline(directory: Path, reference: Path, output: Path) -> dict:
    if output.exists():
        raise BaselineError("output_already_exists")
    dataset = FrozenDataset(directory, reference)
    train = dataset.load("train")
    validation = dataset.load("validation")
    model, details = fit_baseline(train, validation, dataset.sha256)
    manifest = save_model(model, output)
    scores = details.pop("validation_scores")
    labels = [PROTOCOL["label_mapping"][r.label] for r in validation]
    report = {
        "report_version": "1.0",
        "phase": "train-validation",
        "protocol": PROTOCOL,
        "protocol_sha256": PROTOCOL_SHA256,
        "dataset_manifest_sha256": dataset.sha256,
        "model": manifest.model_dump(),
        "environment": environment(),
        "code": code_revision(),
        "fit_rows": len(train),
        "validation_rows": len(validation),
        "test_rows_used": 0,
        "fit_ids_sha256": digest(json_bytes(sorted(r.example_id for r in train))),
        "validation_ids_sha256": digest(json_bytes(sorted(r.example_id for r in validation))),
        "validation_at_selected_threshold": metrics(labels, scores, model.state.threshold),
        "validation_at_default_threshold": metrics(labels, scores, 0.5),
        "validation_training_majority_baseline": metrics(
            labels, [model.state.training_majority] * len(labels), 0.5
        ),
        "shortcut_diagnostics": {
            "train": shortcut_diagnostic(train),
            "validation": shortcut_diagnostic(validation),
        },
        **details,
    }
    (output / "training-report.json").write_bytes(json_bytes(report))
    return report


def evaluate_baseline(
    directory: Path, reference: Path, model_directory: Path, output: Path
) -> dict:
    if output.exists():
        raise BaselineError("output_already_exists")
    model = load_model(model_directory)
    dataset = FrozenDataset(directory, reference)
    if model.state.dataset_sha256 != dataset.sha256:
        raise BaselineError("model_dataset_mismatch")
    records = dataset.load("test")
    if {text_hash(r.email) for r in records} & set(model.state.development_text_hashes):
        raise BaselineError("preprocessed_test_leakage")
    started = time.perf_counter()
    scores = model.scores([r.email for r in records])
    elapsed = time.perf_counter() - started
    labels = [PROTOCOL["label_mapping"][r.label] for r in records]
    report = {
        "report_version": "1.0",
        "phase": "final-test",
        "model_id": MODEL_ID,
        "model_revision": model.revision,
        "protocol_sha256": PROTOCOL_SHA256,
        "dataset_manifest_sha256": dataset.sha256,
        "environment": environment(),
        "code": code_revision(),
        "metrics": metrics(labels, scores, model.state.threshold),
        "training_majority_baseline": metrics(
            labels, [model.state.training_majority] * len(labels), 0.5
        ),
        "batch_inference_seconds": elapsed,
        "amortized_ms_per_email": elapsed * 1000 / len(records),
        "timing_scope": (
            "One CPU batch: preprocessing, TF-IDF transform and scoring; excludes loading, "
            "imports and disk I/O. Not single-request latency."
        ),
        "test_ids_sha256": digest(json_bytes(sorted(r.example_id for r in records))),
        "limitations": [
            "Synthetic publisher-English benchmark, not real-inbox performance.",
            "Publisher labels can require missing sender/link/attachment context.",
            "Declared grouping does not prove complete campaign independence.",
            "Scores are uncalibrated; no adversarial robustness has been evaluated.",
        ],
    }
    predictions = b"".join(
        (
            json.dumps(
                {
                    "example_id": r.example_id,
                    "group_id": r.group_id,
                    "label": r.label,
                    "score": score,
                    "decision": "phishing" if score >= model.state.threshold else "legitimate",
                },
                sort_keys=True,
            )
            + "\n"
        ).encode()
        for r, score in zip(records, scores, strict=True)
    )
    report["predictions_sha256"] = digest(predictions)
    output.mkdir(parents=True, exist_ok=False)
    (output / "predictions.jsonl").write_bytes(predictions)
    (output / "report.json").write_bytes(json_bytes(report))
    return report
