"""Score a precommitted bank once per fixed model, without fitting or adaptation."""

import time
from collections import defaultdict
from importlib.metadata import version

from phishguard.baseline.common import parse_json, read_bytes
from phishguard.baseline.metrics import metrics
from phishguard.baseline.model import load_model, text_hash
from phishguard.contracts import EmailInput
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import digest
from phishguard.evasion.common import PROTOCOL, EvasionError, identity, lines_bytes
from phishguard.evasion.data import verify
from phishguard.evasion.metrics import summarize


def file_snapshot(baseline_directory, model_directory):
    paths = {
        "baseline/" + name: baseline_directory / name for name in ("model.json", "manifest.json")
    }
    paths.update(
        {
            "finetuned/" + name: model_directory / name
            for name in (
                "model.safetensors",
                "config.json",
                "vocab.txt",
                "manifest.json",
                "selection.json",
            )
        }
    )
    return {name: digest(read_bytes(path, 64 * 1024 * 1024)) for name, path in paths.items()}


def load_pair(baseline_directory, model_directory, selection_reference, dataset_sha256):
    from phishguard.finetune.model import load_detector

    baseline = load_model(baseline_directory)
    detector = load_detector(model_directory)
    selected_payload = read_bytes(selection_reference)
    selection = parse_json(selected_payload)
    if (
        read_bytes(model_directory / "selection.json") != selected_payload
        or digest(read_bytes(model_directory / "manifest.json")) != selection["manifest_sha256"]
        or baseline.revision != PROTOCOL["baseline_revision"]
        or baseline.state.threshold != PROTOCOL["baseline_threshold"]
        or baseline.state.dataset_sha256 != dataset_sha256
        or detector.manifest["model_revision"] != PROTOCOL["finetuned_revision"]
        or detector.manifest["threshold"] != PROTOCOL["finetuned_threshold"]
        or detector.manifest["dataset_sha256"] != dataset_sha256
        or any(
            selection[k] != detector.manifest[k]
            for k in (
                "model_revision",
                "threshold",
                "dataset_sha256",
                "protocol_sha256",
                "study_sha256",
            )
        )
    ):
        raise EvasionError("evasion_model_or_threshold_mismatch")
    return baseline, detector


def neural_score(detector, emails):
    from phishguard.finetune.model import runtime

    with runtime():
        encoded, counts = detector.encode(emails)
        scores, _ = detector.score_encoded(encoded)
    return scores, counts, [digest(json_bytes(record)) for record in encoded]


def evaluate(
    directory,
    reference,
    bank,
    bank_reference,
    baseline_directory,
    model_directory,
    selection_reference,
    output,
    progress=None,
):
    from phishguard.finetune.model import tensor_digest

    if output.exists():
        raise EvasionError("output_already_exists")
    cohorts, variants, manifest = verify(directory, reference, bank, bank_reference)
    baseline, detector = load_pair(
        baseline_directory, model_directory, selection_reference, manifest["dataset_sha256"]
    )
    before = file_snapshot(baseline_directory, model_directory)
    tensor_before = tensor_digest(detector.network.state_dict())
    development = set(baseline.state.development_text_hashes) | set(
        detector.manifest["development_text_hashes"]
    )
    by_parent = defaultdict(list)
    for candidate in variants:
        by_parent[(candidate["cohort"], candidate["parent_id"])].append(candidate)
        if text_hash(EmailInput.model_validate(candidate["email"])) in development:
            raise EvasionError("evasion_candidate_development_overlap")
    thresholds = {
        "baseline_v2": baseline.state.threshold,
        "finetuned": detector.manifest["threshold"],
    }
    report = {
        **identity(),
        "phase": "retrospective-controlled-evasion",
        "dataset_sha256": manifest["dataset_sha256"],
        "bank_manifest_sha256": digest(read_bytes(bank_reference)),
        "model_file_digests_before": before,
        "neural_packages": {p: version(p) for p in ("torch", "transformers", "safetensors")},
        "training_validation_or_reserve_files_opened": False,
        "cohorts": {},
        "limitations": [
            "Candidate ASR assumes label preservation under constraints; review is partial.",
            "Finite model-independent search is not a robustness guarantee or strongest attack.",
            "Historical and challenge cohorts were already scored/reviewed in earlier stages.",
            "Source/era bias, synthetic templates and uncertain publisher labels persist.",
            "Directed-evasion full-cohort metrics leave legitimate originals clean by definition.",
            "Fixed-corruption metrics perturb both classes with the same first candidate.",
        ],
    }
    all_predictions = []
    for cohort, rows in cohorts.items():
        if any(text_hash(r.email) in development for r in rows):
            raise EvasionError("evasion_original_development_overlap")
        times = {model: 0.0 for model in thresholds}
        queries = {model: 0 for model in thresholds}
        started = time.perf_counter()
        clean_a = baseline.scores([r.email for r in rows])
        times["baseline_v2"] += time.perf_counter() - started
        started = time.perf_counter()
        clean_b, clean_counts, clean_encoded = neural_score(detector, [r.email for r in rows])
        times["finetuned"] += time.perf_counter() - started
        for model, scores in (("baseline_v2", clean_a), ("finetuned", clean_b)):
            metrics([0] * len(rows), scores, thresholds[model])  # Finite scores and count check.
            queries[model] += len(rows)
        predictions = []
        for start in range(0, len(rows), PROTOCOL["score_parent_batch_size"]):
            batch = rows[start : start + PROTOCOL["score_parent_batch_size"]]
            items = [v for r in batch for v in by_parent[(cohort, r.example_id)]]
            if any(
                len(by_parent[(cohort, r.example_id)]) > PROTOCOL["max_candidates"] for r in batch
            ):
                raise EvasionError("evasion_query_budget_exceeded")
            emails = [EmailInput.model_validate(v["email"]) for v in items]
            a, b, counts, encoded = [], [], [], []
            if emails:
                started = time.perf_counter()
                a = baseline.scores(emails)
                times["baseline_v2"] += time.perf_counter() - started
                started = time.perf_counter()
                b, counts, encoded = neural_score(detector, emails)
                times["finetuned"] += time.perf_counter() - started
            for model, scores in (("baseline_v2", a), ("finetuned", b)):
                metrics([0] * len(emails), scores, thresholds[model])
                queries[model] += len(emails)
            scored = {}
            for v, x, y, count, fingerprint in zip(items, a, b, counts, encoded, strict=True):
                scored[v["variant_id"]] = {
                    "variant_id": v["variant_id"],
                    "operation": v["operation"],
                    "candidate_index": v["candidate_index"],
                    "changed_words": v["changed_words"],
                    "scores": {"baseline_v2": x, "finetuned": y},
                    "finetuned_original_tokens": count,
                    "finetuned_input_sha256": fingerprint,
                }
            for index, row in enumerate(batch, start=start):
                predictions.append(
                    {
                        "cohort": cohort,
                        "example_id": row.example_id,
                        "group_id": row.group_id,
                        "split": row.split,
                        "label": row.label,
                        "source_id": row.source_id,
                        "clean_scores": {
                            "baseline_v2": clean_a[index],
                            "finetuned": clean_b[index],
                        },
                        "clean_finetuned_original_tokens": clean_counts[index],
                        "clean_finetuned_input_sha256": clean_encoded[index],
                        "candidates": [
                            scored[v["variant_id"]] for v in by_parent[(cohort, row.example_id)]
                        ],
                    }
                )
            if progress:
                progress(
                    {
                        "status": "scoring",
                        "cohort": cohort,
                        "originals": len(predictions),
                        "total": len(rows),
                        "model_queries_each": queries["finetuned"],
                    }
                )
        summary = summarize(predictions, thresholds)
        if any(summary["models"][m]["actual_queries"] != q for m, q in queries.items()):
            raise EvasionError("evasion_query_accounting_mismatch")
        summary["batch_scoring_seconds"] = times
        summary["finetuned_identical_effective_inputs"] = sum(
            c["finetuned_input_sha256"] == r["clean_finetuned_input_sha256"]
            for r in predictions
            for c in r["candidates"]
        )
        report["cohorts"][cohort] = summary
        all_predictions.extend(predictions)
    if before != file_snapshot(
        baseline_directory, model_directory
    ) or tensor_before != tensor_digest(detector.network.state_dict()):
        raise EvasionError("evasion_model_changed")
    report["model_files_and_neural_tensors_unchanged"] = True
    payload = lines_bytes(all_predictions)
    report["predictions_sha256"] = digest(payload)
    output.mkdir(parents=True, exist_ok=False)
    (output / "predictions.jsonl").write_bytes(payload)
    (output / "report.json").write_bytes(json_bytes(report))
    return report
