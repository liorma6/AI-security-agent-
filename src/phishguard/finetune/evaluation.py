"""Read only frozen benchmark partitions after the model selection is committed."""

import time
from collections import Counter

from phishguard.audit.runner import intervals, measures, save
from phishguard.baseline.common import parse_json, read_bytes
from phishguard.baseline.model import load_model, text_hash
from phishguard.datasets.source import digest
from phishguard.finetune.common import STUDY, FineTuneError, partition, study
from phishguard.finetune.model import load_detector, token_report
from phishguard.finetune.training import run_identity


def evaluate(
    directory,
    reference,
    model_directory,
    baseline_directory,
    selection_reference,
    output,
    progress=None,
):
    if output.exists():
        raise FineTuneError("output_already_exists")
    frozen = study(directory, reference)
    selection_payload = read_bytes(model_directory / "selection.json")
    if selection_payload != read_bytes(selection_reference):
        raise FineTuneError("finetuned_selection_reference_mismatch")
    selection = parse_json(selection_payload)
    if selection["manifest_sha256"] != digest(read_bytes(model_directory / "manifest.json")):
        raise FineTuneError("finetuned_selection_manifest_mismatch")
    detector = load_detector(model_directory)
    baseline = load_model(baseline_directory)
    if (
        baseline.revision != STUDY["baseline_v2_revision"]
        or baseline.state.threshold != STUDY["baseline_v2_threshold"]
        or baseline.state.dataset_sha256 != frozen.sha256
        or any(
            selection.get(k) != detector.manifest[k]
            for k in (
                "model_revision",
                "threshold",
                "selected_epoch",
                "protocol_sha256",
                "study_sha256",
                "dataset_sha256",
            )
        )
    ):
        raise FineTuneError("finetuned_comparison_identity_mismatch")
    report = {
        **run_identity(),
        "phase": "retrospective-finetuned-comparison",
        "selection": selection,
        "baseline_revision": baseline.revision,
        "baseline_threshold": baseline.state.threshold,
        "model_weights_updated": False,
        "thresholds_updated": False,
        "development_or_reserve_files_opened": False,
        "cohorts": {},
        "limitations": [
            STUDY["benchmark_status"],
            "Source, era and publisher processing remain confounded.",
            "Challenge is mainly synthetic; original subset provenance is unverified.",
            "Transformer right-truncates at 256 tokens; baseline can use the full accepted text.",
            "No adversarial robustness or production-readiness claim.",
        ],
    }
    predictions = []
    for split in ("test", "challenge"):
        rows = partition(frozen, split)
        hashes = {text_hash(r.email) for r in rows}
        if hashes & (
            set(detector.manifest["development_text_hashes"])
            | set(baseline.state.development_text_hashes)
        ):
            raise FineTuneError("finetuned_benchmark_text_leakage")
        result = detector.score([r.email for r in rows], progress)
        started = time.perf_counter()
        baseline_scores = baseline.scores([r.email for r in rows])
        baseline_time = time.perf_counter() - started
        models = {}
        for name, scores, threshold in (
            ("baseline_v2", baseline_scores, baseline.state.threshold),
            ("finetuned", result["scores"], selection["threshold"]),
        ):
            per_source = {}
            for source in sorted({r.source_id for r in rows}):
                indices = [i for i, r in enumerate(rows) if r.source_id == source]
                per_source[source] = measures(
                    [rows[i] for i in indices], [scores[i] for i in indices], threshold
                )
            models[name] = {
                "metrics": measures(rows, scores, threshold),
                "per_source": per_source,
                "group_bootstrap": intervals(rows, scores, threshold),
            }
        paired = Counter()
        for row, a, b, tokens in zip(
            rows, baseline_scores, result["scores"], result["token_counts"], strict=True
        ):
            truth = row.label == "phishing"
            key = {
                (True, True): "both_correct",
                (False, False): "both_wrong",
                (True, False): "baseline_only_correct",
                (False, True): "finetuned_only_correct",
            }[((a >= baseline.state.threshold) == truth, (b >= selection["threshold"]) == truth)]
            paired[key] += 1
            predictions.append(
                {
                    "cohort": split,
                    "example_id": row.example_id,
                    "group_id": row.group_id,
                    "source_id": row.source_id,
                    "label": row.label,
                    "baseline_score": a,
                    "finetuned_score": b,
                    "original_tokens": tokens,
                }
            )
        report["cohorts"][split] = {
            "rows": len(rows),
            "groups": len({r.group_id for r in rows}),
            "results": models,
            "paired_correctness": dict(paired),
            "finetuned_at_default_threshold": measures(rows, result["scores"], 0.5),
            "tokens": token_report(result["token_counts"]),
            "timing_seconds": {
                "baseline_v2": baseline_time,
                "finetuned": result["elapsed_seconds"],
            },
        }
    if load_model(baseline_directory).revision != baseline.revision:
        raise FineTuneError("baseline_changed_during_comparison")
    return save(output, report, predictions)
