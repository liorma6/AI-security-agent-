"""Same-cohort, clean-input comparison; validation selection never loads held-out text."""

import json
import sys
import time
from pathlib import Path

from phishguard.audit.runner import intervals, measures, save
from phishguard.baseline.common import code_revision, parse_json, read_bytes
from phishguard.baseline.metrics import select_threshold
from phishguard.baseline.model import load_model, text_hash
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.finetune.common import STUDY, partition, study
from phishguard.pretrained.selection import Selection, load_selection, save_selection
from phishguard.pretrained.source import PROTOCOL_SHA256, SOURCE_SHA256, PretrainedError

SELECTION = Path("artifacts/pretrained-real-selection-v1")
REFERENCE = Path("data/manifests/pretrained-real-selection-v1.json")
MODEL = Path("models/pretrained/dima806-310a5602")
DATA = Path("data/processed/real-mail-v2")
DATA_REFERENCE = Path("data/manifests/real-mail-v2.json")
BASELINE = Path("models/baseline-v2")
PROTOCOL = {
    "version": "same-cohort-clean-v1",
    "cohorts": {"test": 423, "challenge": 2000},
    "validation_rows": 745,
    "dataset_sha256": STUDY["dataset_sha256"],
    "inference": "Preserve stage-4 pinned weights, tokenizer, 512-token limit and one CPU thread.",
    "selection": "Validation only; baseline F1 grid/ties; commit selection before scoring.",
    "comparison": "Re-score the three preserved current models on identical clean IDs and labels.",
    "diagnostics": "Also report pretrained at 0.50 and old synthetic-validation threshold 0.05.",
    "reserve": "Never open or score reserve text. No new training or model selection.",
    "interpretation": "Retrospective clean transfer comparison, not an attack or final evaluation.",
}
PROTOCOL_DIGEST = digest(json_bytes(PROTOCOL))


def frozen_baseline(frozen):
    baseline = load_model(BASELINE)
    if (
        baseline.revision != STUDY["baseline_v2_revision"]
        or baseline.state.dataset_sha256 != frozen.sha256
        or baseline.state.threshold != STUDY["baseline_v2_threshold"]
    ):
        raise PretrainedError("comparison_baseline_mismatch")
    return baseline


def ids(rows):
    return digest(json_bytes(sorted(r.example_id for r in rows)))


def select(output, progress=None):
    from phishguard.pretrained.adapter import load_classifier
    from phishguard.pretrained.runner import identity

    if output.exists():
        raise PretrainedError("output_already_exists")
    frozen = study(DATA, DATA_REFERENCE)
    baseline = frozen_baseline(frozen)
    rows = partition(frozen, "validation")
    scored = load_classifier(MODEL).score([r.email for r in rows], progress)
    threshold, candidates = select_threshold(
        [int(r.label == "phishing") for r in rows], scored.scores
    )
    report = {
        **identity(frozen),
        "phase": "pretrained-real-validation",
        "comparison_protocol": PROTOCOL,
        "comparison_protocol_sha256": PROTOCOL_DIGEST,
        "validation_ids_sha256": ids(rows),
        "weights_updated": False,
        "test_challenge_reserve_rows_used": 0,
        "validation_at_selected_threshold": measures(rows, scored.scores, threshold),
        "threshold_candidates": candidates,
        "tokens": scored.token_report(),
        "inference_seconds": scored.elapsed_seconds,
    }
    decision = Selection(
        source_sha256=SOURCE_SHA256,
        protocol_sha256=PROTOCOL_SHA256,
        dataset_sha256=frozen.sha256,
        baseline_revision=baseline.revision,
        threshold=threshold,
        validation_report_sha256=digest(json_bytes(report)),
    )
    save_selection(output, decision, report)
    return report


def checked_selection(directory=SELECTION, reference=REFERENCE):
    selected = load_selection(directory)
    if read_bytes(directory / "selection.json") != read_bytes(reference):
        raise PretrainedError("comparison_selection_reference_mismatch")
    report = parse_json(read_bytes(directory / "validation-report.json"))
    if (
        selected.dataset_sha256 != STUDY["dataset_sha256"]
        or selected.baseline_revision != STUDY["baseline_v2_revision"]
        or report.get("comparison_protocol_sha256") != PROTOCOL_DIGEST
        or report.get("test_challenge_reserve_rows_used") != 0
    ):
        raise PretrainedError("comparison_selection_scope_mismatch")
    return selected


def evaluate(output, selection_directory=SELECTION, selection_reference=REFERENCE, progress=None):
    from phishguard.defense.model import load_detector as load_defended
    from phishguard.finetune.model import load_detector
    from phishguard.pretrained.adapter import load_classifier
    from phishguard.pretrained.runner import identity, paired_correctness

    if output.exists():
        raise PretrainedError("output_already_exists")
    selected = checked_selection(selection_directory, selection_reference)
    frozen = study(DATA, DATA_REFERENCE)
    baseline = frozen_baseline(frozen)
    detectors = {
        "finetuned": load_detector(Path("models/finetuned-v1")),
        "defended": load_defended(Path("models/defended-v1")),
    }
    for name, detector in detectors.items():
        reference = parse_json(read_bytes(Path(f"data/manifests/{name}-v1-selection.json")))
        if any(detector.manifest[k] != reference[k] for k in ("model_revision", "threshold")):
            raise PretrainedError("comparison_model_identity_mismatch")
    pretrained = load_classifier(MODEL)
    report = {
        **identity(frozen),
        "phase": "same-cohort-clean-comparison",
        "comparison_protocol": PROTOCOL,
        "comparison_protocol_sha256": PROTOCOL_DIGEST,
        "selection": selected.model_dump(),
        "code": code_revision(),
        "weights_updated": False,
        "training_validation_reserve_text_opened": False,
        "model_revisions": {
            "baseline_v2": baseline.revision,
            **{name: model.manifest["model_revision"] for name, model in detectors.items()},
        },
        "cohorts": {},
        "limitations": [
            "Already-inspected retrospective cohorts, not untouched final evidence.",
            "External training membership is unknown; overlap cannot be excluded.",
            "Different upstream training and token budgets; not architecture-controlled.",
            "Source/era confounding and mainly synthetic challenge limit generalization.",
            "Threshold selection is not probability calibration; no pretrained attack test.",
        ],
    }
    predictions = []
    for split in PROTOCOL["cohorts"]:
        rows = partition(frozen, split)
        hashes = {text_hash(row.email) for row in rows}
        for development in [baseline.state.development_text_hashes] + [
            d.manifest["development_text_hashes"] for d in detectors.values()
        ]:
            if hashes & set(development):
                raise PretrainedError("comparison_development_overlap")
        emails = [r.email for r in rows]
        scores = {"baseline_v2": baseline.scores(emails)}
        thresholds = {"baseline_v2": baseline.state.threshold, "pretrained": selected.threshold}
        tokens = {}
        for name, detector in detectors.items():
            result = detector.score(emails)
            scores[name] = result["scores"]
            tokens[name] = result["token_counts"]
            thresholds[name] = detector.manifest["threshold"]
        result = pretrained.score(emails, progress)
        scores["pretrained"] = result.scores
        tokens["pretrained"] = result.token_counts
        results = {}
        for name, values in scores.items():
            results[name] = {
                "metrics": measures(rows, values, thresholds[name]),
                "group_bootstrap": intervals(rows, values, thresholds[name]),
                "per_source": {
                    source: measures(
                        [r for r in rows if r.source_id == source],
                        [s for r, s in zip(rows, values, strict=True) if r.source_id == source],
                        thresholds[name],
                    )
                    for source in sorted({r.source_id for r in rows})
                },
            }
        report["cohorts"][split] = {
            "rows": len(rows),
            "groups": len({r.group_id for r in rows}),
            "ids_sha256": ids(rows),
            "results": results,
            "pretrained_default": measures(rows, result.scores, 0.5),
            "pretrained_old_threshold": measures(rows, result.scores, 0.05),
            "pretrained_tokens": result.token_report(),
            "pretrained_seconds": result.elapsed_seconds,
            "paired_against_pretrained": {
                name: paired_correctness(
                    [int(r.label == "phishing") for r in rows],
                    values,
                    thresholds[name],
                    result.scores,
                    selected.threshold,
                )
                for name, values in scores.items()
                if name != "pretrained"
            },
        }
        predictions.extend(
            {
                "cohort": split,
                "example_id": row.example_id,
                "group_id": row.group_id,
                "source_id": row.source_id,
                "label": row.label,
                "scores": {name: values[i] for name, values in scores.items()},
                "original_tokens": {name: values[i] for name, values in tokens.items()},
            }
            for i, row in enumerate(rows)
        )
    return save(output, report, predictions)


def register(commands):
    actions = commands.add_parser(
        "compare", help="Compare four frozen models on current cohorts"
    ).add_subparsers(dest="action", required=True)
    select_command = actions.add_parser(
        "select", help="Freeze pretrained threshold on validation only"
    )
    select_command.add_argument("--output", type=Path, default=SELECTION)
    evaluate_command = actions.add_parser("evaluate", help="Score identical clean benchmark rows")
    evaluate_command.add_argument("--output", type=Path, default=Path("artifacts/comparison-v1"))
    evaluate_command.add_argument("--selection", type=Path, default=SELECTION)
    evaluate_command.add_argument("--selection-reference", type=Path, default=REFERENCE)


def run(args):
    last = 0.0

    def progress(done, total):
        nonlocal last
        if time.monotonic() - last >= 20 or done == total:
            print(json.dumps({"scored": done, "total": total}), file=sys.stderr, flush=True)
            last = time.monotonic()

    try:
        report = (
            select(args.output, progress)
            if args.action == "select"
            else evaluate(args.output, args.selection, args.selection_reference, progress)
        )
        result = report.get("validation_at_selected_threshold") or {
            split: {name: r["metrics"] for name, r in c["results"].items()}
            for split, c in report["cohorts"].items()
        }
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, RuntimeError, ImportError, KeyError, TypeError):
        print(json.dumps({"status": "unavailable", "error": "comparison_input_or_runtime_error"}))
        return 2
