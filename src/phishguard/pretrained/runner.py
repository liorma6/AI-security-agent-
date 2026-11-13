"""Freeze validation decisions before scoring the same held-out rows as the baseline."""

import json
import time
from importlib.metadata import version
from pathlib import Path

from phishguard.baseline.common import code_revision, environment, parse_json, read_bytes
from phishguard.baseline.data import FrozenDataset
from phishguard.baseline.metrics import metrics, select_threshold
from phishguard.baseline.model import load_model, text_hash
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.pretrained.adapter import load_classifier
from phishguard.pretrained.selection import Selection, load_selection, save_selection
from phishguard.pretrained.source import (
    PROTOCOL,
    PROTOCOL_SHA256,
    SOURCE,
    SOURCE_SHA256,
    PretrainedError,
)


def runtime() -> dict:
    return {
        **environment(),
        "pretrained_packages": {
            name: version(name) for name in (*PROTOCOL["runtime"], "tokenizers")
        },
        "pretrained_device": "cpu",
        "pretrained_dtype": "float32",
        "pretrained_batch_size": PROTOCOL["batch_size"],
    }


def identity(dataset) -> dict:
    return {
        "report_version": "1.0",
        "source": SOURCE,
        "source_sha256": SOURCE_SHA256,
        "protocol": PROTOCOL,
        "protocol_sha256": PROTOCOL_SHA256,
        "dataset_manifest_sha256": dataset.sha256,
        "environment": runtime(),
        "code": code_revision(),
    }


def row_ids(records) -> str:
    return digest(json_bytes(sorted(r.example_id for r in records)))


def select_pretrained(
    directory, reference, model_directory, baseline_directory, output, progress=None
):
    if output.exists():
        raise PretrainedError("output_already_exists")
    dataset = FrozenDataset(directory, reference)
    baseline = load_model(baseline_directory)
    if baseline.state.dataset_sha256 != dataset.sha256:
        raise PretrainedError("baseline_dataset_mismatch")
    records = dataset.load("validation")
    classifier = load_classifier(model_directory)
    scored = classifier.score([r.email for r in records], progress)
    labels = [SOURCE["label_mapping"][r.label] for r in records]
    threshold, candidates = select_threshold(labels, scored.scores)
    report = {
        **identity(dataset),
        "phase": "pretrained-validation",
        "weights_updated": False,
        "test_rows_used": 0,
        "baseline_revision": baseline.revision,
        "validation_ids_sha256": row_ids(records),
        "validation_at_default_threshold": metrics(labels, scored.scores, 0.5),
        "validation_at_selected_threshold": metrics(labels, scored.scores, threshold),
        "threshold_candidates": candidates,
        "tokens": scored.token_report(),
        "batch_inference_seconds": scored.elapsed_seconds,
    }
    selection = Selection(
        source_sha256=SOURCE_SHA256,
        protocol_sha256=PROTOCOL_SHA256,
        dataset_sha256=dataset.sha256,
        baseline_revision=baseline.revision,
        threshold=threshold,
        validation_report_sha256=digest(json_bytes(report)),
    )
    save_selection(output, selection, report)
    return report


def paired_correctness(labels, baseline_scores, baseline_threshold, scores, threshold) -> dict:
    counts = dict.fromkeys(("both_correct", "baseline_only", "pretrained_only", "both_wrong"), 0)
    keys = {
        (True, True): "both_correct",
        (True, False): "baseline_only",
        (False, True): "pretrained_only",
        (False, False): "both_wrong",
    }
    for label, left, right in zip(labels, baseline_scores, scores, strict=True):
        counts[keys[((left >= baseline_threshold) == label, (right >= threshold) == label)]] += 1
    return counts


def evaluate_pretrained(
    directory: Path,
    reference: Path,
    model_directory: Path,
    baseline_directory: Path,
    selection_directory: Path,
    baseline_report: Path,
    output: Path,
    progress=None,
) -> dict:
    if output.exists():
        raise PretrainedError("output_already_exists")
    selection = load_selection(selection_directory)
    dataset = FrozenDataset(directory, reference)
    baseline = load_model(baseline_directory)
    if (
        selection.dataset_sha256 != dataset.sha256
        or baseline.state.dataset_sha256 != dataset.sha256
    ):
        raise PretrainedError("baseline_dataset_mismatch")
    if baseline.revision != selection.baseline_revision:
        raise PretrainedError("baseline_revision_mismatch")
    records = dataset.load("test")
    if {text_hash(r.email) for r in records} & set(baseline.state.development_text_hashes):
        raise PretrainedError("preprocessed_test_leakage")
    emails = [r.email for r in records]
    labels = [SOURCE["label_mapping"][r.label] for r in records]
    started = time.perf_counter()
    baseline_scores = baseline.scores(emails)
    baseline_seconds = time.perf_counter() - started
    baseline_metrics = metrics(labels, baseline_scores, baseline.state.threshold)
    prior = parse_json(read_bytes(baseline_report))
    if (
        prior.get("model_revision") != baseline.revision
        or prior.get("dataset_manifest_sha256") != dataset.sha256
        or prior.get("test_ids_sha256") != row_ids(records)
        or prior.get("metrics") != baseline_metrics
    ):
        raise PretrainedError("baseline_report_mismatch")
    classifier = load_classifier(model_directory)
    scored = classifier.score(emails, progress)
    report = {
        **identity(dataset),
        "phase": "pretrained-final-test",
        "weights_updated": False,
        "selection_sha256": digest(read_bytes(selection_directory / "selection.json")),
        "validation_report_sha256": selection.validation_report_sha256,
        "baseline_revision": baseline.revision,
        "baseline_report_sha256": digest(read_bytes(baseline_report)),
        "test_ids_sha256": row_ids(records),
        "metrics": {
            "baseline": baseline_metrics,
            "pretrained_default": metrics(labels, scored.scores, 0.5),
            "pretrained_selected": metrics(labels, scored.scores, selection.threshold),
        },
        "paired_correctness": {
            name: paired_correctness(
                labels, baseline_scores, baseline.state.threshold, scored.scores, threshold
            )
            for name, threshold in (("default", 0.5), ("selected", selection.threshold))
        },
        "tokens": scored.token_report(),
        "timing": {
            "baseline_seconds": baseline_seconds,
            "pretrained_seconds": scored.elapsed_seconds,
            "baseline_amortized_ms": baseline_seconds * 1000 / len(records),
            "pretrained_amortized_ms": scored.elapsed_seconds * 1000 / len(records),
            "scope": "CPU one numeric thread, preprocessing/tokenization/scoring; excludes loading "
            "and disk I/O. Pretrained batches of 8, baseline one sparse batch. "
            "Not single-request latency; no peak RAM measurement.",
        },
        "limitations": [
            "Synthetic publisher-English benchmark, not real-inbox performance.",
            "Baseline fitted this corpus; pretrained weights fitted external data. "
            "This does not isolate the effect of model architecture.",
            "Full upstream training membership is unavailable; overlap cannot be excluded.",
            "Reconstructed cased tokenizer; inputs over 512 tokens are right-truncated.",
            "Publisher labels can require missing context; grouping cannot prove independence.",
            "Threshold selection is not probability calibration. No evasion robustness measured.",
        ],
    }
    predictions = b"".join(
        (
            json.dumps(
                {
                    "example_id": row.example_id,
                    "label": row.label,
                    "baseline_score": left,
                    "pretrained_score": right,
                    "original_tokens": tokens,
                    "truncated": tokens > PROTOCOL["max_tokens"],
                },
                sort_keys=True,
            )
            + "\n"
        ).encode()
        for row, left, right, tokens in zip(
            records, baseline_scores, scored.scores, scored.token_counts, strict=True
        )
    )
    report["predictions_sha256"] = digest(predictions)
    output.mkdir(parents=True, exist_ok=False)
    (output / "predictions.jsonl").write_bytes(predictions)
    (output / "report.json").write_bytes(json_bytes(report))
    return report
