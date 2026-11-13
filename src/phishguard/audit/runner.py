"""Read-only diagnosis and external evaluation of the exact stage-3 classifier."""

import json
import re
import time
from collections import Counter, defaultdict
from importlib.metadata import version
from pathlib import Path

import numpy as np

from phishguard.audit.common import PROTOCOL, PROTOCOL_SHA256, SOURCE, SOURCE_SHA256, AuditError
from phishguard.audit.data import load_audit
from phishguard.audit.similarity import relations
from phishguard.baseline.common import code_revision, environment, parse_json, read_bytes
from phishguard.baseline.data import FrozenDataset
from phishguard.baseline.metrics import metrics
from phishguard.baseline.model import load_model
from phishguard.baseline.preprocessing import preprocess
from phishguard.datasets.grouping import related_components
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest


def frozen_model(directory):
    model = load_model(directory)
    if (
        model.revision != PROTOCOL["baseline_revision"]
        or model.state.threshold != PROTOCOL["baseline_threshold"]
        or model.state.dataset_sha256 != PROTOCOL["internal_manifest_sha256"]
    ):
        raise AuditError("frozen_baseline_mismatch")
    return model


def measures(rows, scores, threshold):
    result = metrics([int(r.label == "phishing") for r in rows], scores, threshold)
    c = result["confusion"]
    specificity = c["tn"] / (c["tn"] + c["fp"]) if c["tn"] + c["fp"] else None
    result["balanced_accuracy"] = (
        (result["recall"] + specificity) / 2
        if result["recall"] is not None and specificity is not None
        else None
    )
    return result


def intervals(rows, scores, threshold):
    groups = defaultdict(lambda: np.zeros(4, dtype=np.int64))
    for row, score in zip(rows, scores, strict=True):
        actual, predicted = row.label == "phishing", score >= threshold
        index = {(True, True): 0, (False, True): 1, (False, False): 2, (True, False): 3}
        groups[row.group_id][index[(actual, predicted)]] += 1
    matrix = np.array([groups[gid] for gid in sorted(groups)])
    if len(matrix) < 2:
        return {"groups": len(matrix), "intervals": None, "reason": "insufficient_groups"}
    rng = np.random.default_rng(PROTOCOL["bootstrap"]["seed"])
    samples = defaultdict(list)
    for _ in range(PROTOCOL["bootstrap"]["repetitions"]):
        tp, fp, tn, fn = matrix[rng.integers(0, len(matrix), size=len(matrix))].sum(axis=0)
        samples["accuracy"].append((tp + tn) / (tp + fp + tn + fn))
        if tp + fn:
            samples["recall"].append(tp / (tp + fn))
        if fp + tn:
            samples["false_positive_rate"].append(fp / (fp + tn))
        if tp + fn and fp + tn:
            samples["balanced_accuracy"].append((tp / (tp + fn) + tn / (tn + fp)) / 2)
    return {
        "groups": len(matrix),
        "repetitions": PROTOCOL["bootstrap"]["repetitions"],
        "seed": PROTOCOL["bootstrap"]["seed"],
        "method": "whole-group percentile bootstrap 95%",
        "intervals": {
            key: {
                "lower": float(np.quantile(values, 0.025)),
                "upper": float(np.quantile(values, 0.975)),
                "valid_resamples": len(values),
            }
            for key, values in samples.items()
        },
        "limitation": (
            "Conditional on this corpus and heuristic groups; "
            "not protection against source bias or label errors."
        ),
    }


def identity(model):
    return {
        "report_version": "1.0",
        "protocol": PROTOCOL,
        "protocol_sha256": PROTOCOL_SHA256,
        "model_revision": model.revision,
        "threshold": model.state.threshold,
        "internal_manifest_sha256": model.state.dataset_sha256,
        "weights_updated": False,
        "threshold_updated": False,
        "environment": {
            **environment(),
            "audit_packages": {name: version(name) for name in PROTOCOL["runtime"]},
        },
        "code": code_revision(),
    }


def save(output, report, predictions=None):
    output.mkdir(parents=True, exist_ok=False)
    if predictions is not None:
        payload = b"".join((json.dumps(row, sort_keys=True) + "\n").encode() for row in predictions)
        report["predictions_sha256"] = digest(payload)
        (output / "predictions.jsonl").write_bytes(payload)
    (output / "report.json").write_bytes(json_bytes(report))
    return report


def internal_audit(
    directory: Path, reference: Path, model_directory: Path, prior_report: Path, output: Path
):
    if output.exists():
        raise AuditError("output_already_exists")
    model = frozen_model(model_directory)
    dataset = FrozenDataset(directory, reference)
    if dataset.sha256 != model.state.dataset_sha256:
        raise AuditError("internal_dataset_mismatch")
    splits = {split: dataset.load(split) for split in ("train", "validation", "test")}
    scores = {split: model.scores([r.email for r in rows]) for split, rows in splits.items()}
    measured = {
        split: measures(rows, scores[split], model.state.threshold)
        for split, rows in splits.items()
    }
    prior = parse_json(read_bytes(prior_report))
    if (
        prior.get("model_revision") != model.revision
        or prior.get("dataset_manifest_sha256") != dataset.sha256
        or prior.get("test_ids_sha256")
        != digest(json_bytes(sorted(r.example_id for r in splits["test"])))
        or any(measured["test"][key] != value for key, value in prior["metrics"].items())
    ):
        raise AuditError("published_baseline_mismatch")
    all_rows = [r for rows in splits.values() for r in rows]
    by_id = {r.example_id: r for r in all_rows}
    declared = related_components(all_rows)
    declared_cross = [ids for ids in declared if len({by_id[rid].split for rid in ids}) > 1]
    components, edges = relations(all_rows)
    cross = [edge for edge in edges if by_id[edge[0]].split != by_id[edge[1]].split]
    connected_test = set()
    for ids in components:
        if any(by_id[rid].split in {"train", "validation"} for rid in ids):
            connected_test.update(rid for rid in ids if by_id[rid].split == "test")
    subset = [
        (r, s)
        for r, s in zip(splits["test"], scores["test"], strict=True)
        if r.example_id not in connected_test
    ]
    train_matrix = model.transform.transform([preprocess(r.email.text) for r in splits["train"]])
    order = sorted(range(len(model.state.terms)), key=lambda i: model.state.coefficients[i])
    terms = {}
    for direction, indices in (
        ("towards_legitimate", order[:12]),
        ("towards_phishing", list(reversed(order[-12:]))),
    ):
        terms[direction] = [
            {
                "term": model.state.terms[i],
                "coefficient": model.state.coefficients[i],
                "training_document_frequency": {
                    label: int(
                        train_matrix[
                            [j for j, r in enumerate(splits["train"]) if r.label == label], i
                        ].getnnz()
                    )
                    for label in ("legitimate", "phishing")
                },
            }
            for i in indices
        ]
    patterns = {
        "square_placeholder": r"\[[^\[\]]{1,80}\]",
        "html_markup": r"<[A-Za-z][^>]*>",
        "http_url": r"https?://",
        "urgency_word": r"\b(?:urgent|immediate|suspend|suspended)\b",
    }
    pattern_counts = {
        split: {
            label: {
                name: sum(
                    bool(re.search(pattern, preprocess(r.email.text), re.I))
                    for r in rows
                    if r.label == label
                )
                for name, pattern in patterns.items()
            }
            for label in ("legitimate", "phishing")
        }
        for split, rows in splits.items()
    }
    report = {
        **identity(model),
        "phase": "internal-generalization-audit",
        "metrics": measured,
        "declared_rule_cross_split_components": len(declared_cross),
        "broader_relation_cross_split_edges": len(cross),
        "broader_edges_by_reason": dict(Counter(edge[2] for edge in cross)),
        "broader_edges_by_split_pair": dict(
            Counter(":".join(sorted((by_id[a].split, by_id[b].split))) for a, b, _, _ in cross)
        ),
        "broader_connected_test_rows": len(connected_test),
        "test_without_broader_development_relatives": measures(
            [r for r, _ in subset], [s for _, s in subset], model.state.threshold
        ),
        "subset_interpretation": (
            "Post-hoc sensitivity subset, not a replacement test set "
            "or proof of semantic independence."
        ),
        "coefficient_associations": terms,
        "pattern_counts": pattern_counts,
        "pattern_definitions": patterns,
        "interpretation_limits": [
            "Small same-source accuracy gaps cannot establish cross-source generalization.",
            "Large coefficients and text patterns are associations, not causal evidence.",
            "The broader 0.70 relation rule is exploratory and may over-group unrelated text.",
        ],
    }
    if frozen_model(model_directory).revision != model.revision:
        raise AuditError("model_changed_during_audit")
    return save(output, report)


def evaluate_external(directory: Path, reference: Path, model_directory: Path, output: Path):
    if output.exists():
        raise AuditError("output_already_exists")
    model = frozen_model(model_directory)
    rows, manifest, manifest_sha = load_audit(directory, reference)
    started = time.perf_counter()
    scores = model.scores([r.email for r in rows])
    elapsed = time.perf_counter() - started
    matrix = model.transform.transform([preprocess(r.email.text) for r in rows])
    by_source = {}
    for source in sorted({r.source_id for r in rows}):
        indices = [i for i, r in enumerate(rows) if r.source_id == source]
        by_source[source] = measures(
            [rows[i] for i in indices], [scores[i] for i in indices], model.state.threshold
        )
    predictions = [
        {
            "example_id": row.example_id,
            "group_id": row.group_id,
            "source_id": row.source_id,
            "label": row.label,
            "score": score,
            "decision": "phishing" if score >= model.state.threshold else "legitimate",
        }
        for row, score in zip(rows, scores, strict=True)
    ]
    report = {
        **identity(model),
        "phase": "external-audit",
        "source": SOURCE,
        "source_sha256": SOURCE_SHA256,
        "external_manifest_sha256": manifest_sha,
        "audit_ids_sha256": digest(json_bytes(sorted(r.example_id for r in rows))),
        "reserve_rows_scored": 0,
        "reserved_cohort": manifest["partitions"]["reserve"],
        "metrics": measures(rows, scores, model.state.threshold),
        "per_source": by_source,
        "group_bootstrap": intervals(rows, scores, model.state.threshold),
        "zero_feature_rows": int(np.count_nonzero(matrix.getnnz(axis=1) == 0)),
        "batch_inference_seconds": elapsed,
        "amortized_ms_per_email": elapsed * 1000 / len(rows),
        "timing_scope": (
            "One CPU numerical thread; preprocessing, TF-IDF and scoring, "
            "excluding loading and I/O."
        ),
        "exclusions": manifest["exclusion_counts"],
        "limitations": SOURCE["limits"]
        + [
            "Observed class prevalence is determined by archive selection; "
            "report balanced accuracy and class-conditional errors.",
            "This scored cohort is now development evidence. "
            "Reserve remains unscored, but shares the same sources.",
            "No external result licenses claims about contemporary inboxes, "
            "calibrated probabilities or adversarial robustness.",
        ],
    }
    if frozen_model(model_directory).revision != model.revision:
        raise AuditError("model_changed_during_audit")
    return save(output, report, predictions)
