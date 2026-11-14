"""Precommitted final reserve evaluation with no fitting or adaptive experiment choices."""

import json
import subprocess
import sys
import time
from collections import Counter, defaultdict
from importlib.resources import files
from pathlib import Path

import numpy as np

from phishguard.audit.common import PROTOCOL_SHA256 as AUDIT_PROTOCOL_SHA256
from phishguard.audit.common import SOURCE, SOURCE_SHA256
from phishguard.audit.data import cohort_stats
from phishguard.audit.runner import intervals, measures, save
from phishguard.baseline.common import code_revision, environment, parse_json, read_bytes
from phishguard.baseline.model import text_hash
from phishguard.datasets.preparation import json_bytes
from phishguard.datasets.source import checked_bytes, digest
from phishguard.validation import validate_json

PROTOCOL = json.loads(
    files("phishguard").joinpath("final_protocol.json").read_text(encoding="utf-8")
)
PROTOCOL_SHA256 = digest(json_bytes(PROTOCOL))
FREEZE = Path("data/manifests/final-evaluation-freeze-v1.json")
DATA = Path("data/processed/external-mail-v1")
REFERENCE = Path("data/manifests/external-mail-v1.json")
OUTPUT = Path("artifacts/final-evaluation-v1")


class FinalError(ValueError):
    """Fixed error codes without email content."""


def preserved(snapshot):
    for name, meta in snapshot.items():
        checked_bytes(Path(name), meta)


def check_freeze(reference=FREEZE):
    payload = read_bytes(reference)
    frozen = parse_json(payload)
    if frozen["protocol_sha256"] != PROTOCOL_SHA256:
        raise FinalError("final_protocol_changed")
    committed = subprocess.run(
        ["git", "show", f"HEAD:{reference.as_posix()}"], capture_output=True, check=True
    ).stdout
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True, check=True
    ).stdout
    if committed != payload or status.strip():
        raise FinalError("final_freeze_not_committed_or_worktree_dirty")
    for name, expected in frozen["code_and_references"].items():
        if digest(read_bytes(Path(name))) != expected:
            raise FinalError("final_code_or_reference_changed")
    preserved(frozen["preserved_inputs"])
    return frozen


def load_reserve(directory=DATA, reference=REFERENCE):
    payload = read_bytes(directory / "manifest.json")
    if payload != read_bytes(reference):
        raise FinalError("final_reserve_manifest_mismatch")
    manifest = parse_json(payload)
    if (
        manifest["source_sha256"] != SOURCE_SHA256
        or manifest["protocol_sha256"] != AUDIT_PROTOCOL_SHA256
        or manifest["source"] != SOURCE
        or manifest["files"]["reserve.jsonl"] != PROTOCOL["reserve_file"]
    ):
        raise FinalError("final_reserve_identity_mismatch")
    members = {}
    groups = set()
    for group in manifest["groups"]:
        if group["group_id"] in groups or group["cohort"] not in {"audit", "reserve"}:
            raise FinalError("final_invalid_membership")
        groups.add(group["group_id"])
        for rid in group["members"]:
            if rid in members:
                raise FinalError("final_invalid_membership")
            members[rid] = (group["group_id"], group["cohort"])
    data = checked_bytes(directory / "reserve.jsonl", PROTOCOL["reserve_file"])
    rows = [validate_json("example", line) for line in data.splitlines()]
    expected = {rid for rid, (_, cohort) in members.items() if cohort == "reserve"}
    if len(rows) != len(expected) or {r.example_id for r in rows} != expected:
        raise FinalError("final_invalid_membership")
    sources = {v["source_id"]: v for v in SOURCE["files"].values() if "source_id" in v}
    for row in rows:
        source = sources[row.source_id]
        if (
            row.split != "unassigned"
            or members[row.example_id] != (row.group_id, "reserve")
            or row.label != source["label"]
            or row.license != source["license"]
            or row.source_revision != source["sha256"]
        ):
            raise FinalError("final_invalid_membership")
    stats = cohort_stats(rows)
    if stats != manifest["partitions"]["reserve"] or any(
        stats[k] != PROTOCOL[k] for k in ("rows", "groups", "labels")
    ):
        raise FinalError("final_invalid_counts")
    return rows, manifest


def prepare_bank(rows, development):
    from phishguard.contracts import EmailInput
    from phishguard.evasion.perturbations import generate

    if any(text_hash(row.email) in development for row in rows):
        raise FinalError("final_original_development_overlap")
    # Keep the reserve file unmodified; the shared library accepts a test-role view.
    views = [row.model_copy(update={"split": "test"}) for row in rows]
    variants = []
    for row in views:
        for variant in generate(row, "test", seed=PROTOCOL["attack_seed"]):
            variant["cohort"] = PROTOCOL["cohort"]
            if text_hash(EmailInput.model_validate(variant["email"])) in development:
                raise FinalError("final_candidate_development_overlap")
            variants.append(variant)
    return views, variants


def paired_defense_interval(rows, parent_scores, defense_scores):
    """Paired whole-group contrast; never resample individual related messages."""
    grouped = defaultdict(lambda: np.zeros((2, 4), dtype=np.int64))
    for row, left, right in zip(rows, parent_scores, defense_scores, strict=True):
        for index, (score, name) in enumerate(((left, "finetuned"), (right, "defended"))):
            positive = score >= PROTOCOL["models"][name]["threshold"]
            truth = row.label == "phishing"
            column = 0 if truth and positive else 1 if positive else 3 if truth else 2
            grouped[row.group_id][index, column] += 1
    if len(grouped) < 2:
        return {"groups": len(grouped), "intervals": None}
    matrix = np.array([grouped[key] for key in sorted(grouped)])
    rng = np.random.default_rng(PROTOCOL["uncertainty"]["seed"])
    values = defaultdict(list)
    for _ in range(PROTOCOL["uncertainty"]["repetitions"]):
        totals = matrix[rng.integers(0, len(matrix), size=len(matrix))].sum(axis=0)
        metrics = []
        for tp, fp, tn, fn in totals:
            metrics.append(
                {
                    "accuracy": (tp + tn) / (tp + fp + tn + fn),
                    "recall": tp / (tp + fn) if tp + fn else None,
                    "false_positive_rate": fp / (fp + tn) if fp + tn else None,
                    "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
                }
            )
        for key, value in metrics[0].items():
            if value is not None and metrics[1][key] is not None:
                values[key].append(float(metrics[1][key] - value))
    return {
        **PROTOCOL["uncertainty"],
        "groups": len(grouped),
        "intervals": {
            key: {
                "lower": float(np.quantile(v, 0.025)),
                "upper": float(np.quantile(v, 0.975)),
                "valid_resamples": len(v),
            }
            for key, v in values.items()
        },
    }


def load_models():
    from phishguard.baseline.model import load_model
    from phishguard.comparison import checked_selection
    from phishguard.defense.model import load_detector, parent
    from phishguard.pretrained.adapter import load_classifier

    models = {
        "baseline_v2": load_model(Path("models/baseline-v2")),
        "finetuned": parent(
            Path("models/finetuned-v1"), Path("data/manifests/finetuned-v1-selection.json")
        ),
        "defended": load_detector(
            Path("models/defended-v1"), Path("data/manifests/defended-v1-selection.json")
        ),
    }
    for name, model in models.items():
        actual = (
            {"revision": model.revision, "threshold": model.state.threshold}
            if name == "baseline_v2"
            else {
                "revision": model.manifest["model_revision"],
                "threshold": model.manifest["threshold"],
            }
        )
        if actual != PROTOCOL["models"][name]:
            raise FinalError("final_model_or_threshold_changed")
    selected = checked_selection()
    if selected.threshold != PROTOCOL["models"]["pretrained"]["threshold"]:
        raise FinalError("final_pretrained_threshold_changed")
    pretrained = load_classifier(Path("models/pretrained/dima806-310a5602"))
    return models, pretrained


def review_ids(predictions):
    """Freeze a bounded post-score sample without inspecting or modifying labels."""
    clean, attacks = {}, []
    for model, info in PROTOCOL["models"].items():
        for label, kind in (("legitimate", "false_positive"), ("phishing", "false_negative")):
            candidates = [
                p
                for p in predictions
                if p["label"] == label
                and ((p["clean_scores"][model] >= info["threshold"]) != (label == "phishing"))
            ]
            clean[model + "/" + kind] = [
                p["example_id"]
                for p in sorted(
                    candidates,
                    key=lambda p: digest(("final-clean-review-v1:" + p["example_id"]).encode()),
                )[:2]
            ]
    from phishguard.evasion.common import PROTOCOL as ATTACK
    from phishguard.evasion.metrics import selected

    for operation in ATTACK["operations"]:
        for model in ("defended", "finetuned"):
            threshold = PROTOCOL["models"][model]["threshold"]
            successes = []
            for p in predictions:
                if p["label"] != "phishing" or p["clean_scores"][model] < threshold:
                    continue
                score, vid = selected(p, model, threshold)
                candidate = next((v for v in p["candidates"] if v["variant_id"] == vid), None)
                if score < threshold and candidate and candidate["operation"] == operation:
                    successes.append((p, candidate))
            if successes:
                for p, c in sorted(
                    successes,
                    key=lambda pair: digest(
                        ("final-attack-review-v1:" + pair[0]["example_id"]).encode()
                    ),
                )[:2]:
                    attacks.append(
                        {
                            "example_id": p["example_id"],
                            "variant_id": c["variant_id"],
                            "model": model,
                            "operation": operation,
                        }
                    )
                break
    return {"clean": clean, "attacks": attacks}


def evaluate(output=OUTPUT, progress=None):
    from phishguard.defense.evaluation import score_bank
    from phishguard.evasion.common import lines_bytes
    from phishguard.finetune.model import tensor_digest, token_report

    if output.exists():
        raise FinalError("output_already_exists")
    frozen = check_freeze()
    models, pretrained = load_models()
    neural = {**{k: m for k, m in models.items() if k != "baseline_v2"}, "pretrained": pretrained}
    tensors = {k: tensor_digest(m.network.state_dict()) for k, m in neural.items()}
    rows, manifest = load_reserve()
    development = set(models["baseline_v2"].state.development_text_hashes)
    for name in ("finetuned", "defended"):
        development.update(models[name].manifest["development_text_hashes"])
    views, variants = prepare_bank(rows, development)
    bank_bytes = lines_bytes(variants)
    thresholds = {name: PROTOCOL["models"][name]["threshold"] for name in models}
    if progress:
        progress({"status": "bank_fixed", "originals": len(rows), "variants": len(variants)})
    reports, predictions = score_bank(
        {PROTOCOL["cohort"]: views}, variants, models, thresholds, development, progress
    )

    def external_progress(done, total):
        if progress:
            progress({"status": "pretrained_clean", "rows": done, "total": total})

    scored = pretrained.score([r.email for r in rows], external_progress)
    for p, score, tokens in zip(predictions, scored.scores, scored.token_counts, strict=True):
        p["clean_scores"]["pretrained"] = score
        p["pretrained_original_tokens"] = tokens
    clean = {}
    for name, info in PROTOCOL["models"].items():
        scores = [p["clean_scores"][name] for p in predictions]
        clean[name] = {
            "metrics": measures(rows, scores, info["threshold"]),
            "group_bootstrap": intervals(rows, scores, info["threshold"]),
            "per_source": {
                source: measures(
                    [r for r in rows if r.source_id == source],
                    [s for r, s in zip(rows, scores, strict=True) if r.source_id == source],
                    info["threshold"],
                )
                for source in sorted({r.source_id for r in rows})
            },
        }
        if name in ("finetuned", "defended"):
            clean[name]["tokens"] = token_report(
                [p["clean_neural_inputs"][name]["original_tokens"] for p in predictions]
            )
    clean["pretrained"]["tokens"] = scored.token_report()
    clean["pretrained"]["inference_seconds"] = scored.elapsed_seconds
    preserved(frozen["preserved_inputs"])
    if tensors != {k: tensor_digest(m.network.state_dict()) for k, m in neural.items()}:
        raise FinalError("final_weights_changed_in_memory")
    report = {
        "phase": "frozen-final-reserve-evaluation",
        "protocol": PROTOCOL,
        "protocol_sha256": PROTOCOL_SHA256,
        "freeze_sha256": digest(read_bytes(FREEZE)),
        "code": code_revision(),
        "environment": environment(),
        "cohort": manifest["partitions"]["reserve"],
        "reserve_rows_scored": len(rows),
        "model_revisions_and_thresholds": PROTOCOL["models"],
        "clean": clean,
        "robustness": reports[PROTOCOL["cohort"]],
        "paired_defense_minus_parent": paired_defense_interval(
            rows,
            [p["clean_scores"]["finetuned"] for p in predictions],
            [p["clean_scores"]["defended"] for p in predictions],
        ),
        "bank": {
            "sha256": digest(bank_bytes),
            "variants": len(variants),
            "operations": dict(Counter(v["operation"] for v in variants)),
            "seed": PROTOCOL["attack_seed"],
        },
        "review_selection": review_ids(predictions),
        "weights_and_thresholds_updated": False,
        "development_mail_opened": False,
        "model_files_and_tensors_unchanged": True,
        "preserved_files": len(frozen["preserved_inputs"]),
        "limitations": PROTOCOL["limitations"],
    }
    save(output, report, predictions)
    (output / "bank.jsonl").write_bytes(bank_bytes)
    return report


def register(commands):
    actions = commands.add_parser(
        "final", help="Run the frozen final reserve evaluation"
    ).add_subparsers(dest="action", required=True)
    command = actions.add_parser("evaluate")
    command.add_argument("--output", type=Path, default=OUTPUT)


def run(args):
    last = 0.0

    def progress(event):
        nonlocal last
        if time.monotonic() - last >= 20 or event["status"] == "bank_fixed":
            print(json.dumps(event), file=sys.stderr, flush=True)
            last = time.monotonic()

    try:
        result = evaluate(args.output, progress)
        print(
            json.dumps(
                {
                    "status": "evaluated",
                    "reserve_rows_scored": result["reserve_rows_scored"],
                    "clean": {k: v["metrics"] for k, v in result["clean"].items()},
                },
                indent=2,
            )
        )
        return 0
    except (
        ValueError,
        OSError,
        RuntimeError,
        ImportError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ):
        print(json.dumps({"status": "unavailable", "error": "final_integrity_or_runtime_failure"}))
        return 2
