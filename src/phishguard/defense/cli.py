"""Local defense research commands; research text is never echoed."""

import json
import sys
import time
from pathlib import Path

from phishguard.audit.common import AuditError
from phishguard.baseline.common import BaselineError
from phishguard.contracts import UnavailablePrediction
from phishguard.datasets.source import DatasetError
from phishguard.defense.common import (
    AUGMENTATION,
    AUGMENTATION_REFERENCE,
    FRESH_BANK,
    FRESH_REFERENCE,
    MODEL,
    MODEL_ID,
    REVIEW_REFERENCE,
    SELECTION_REFERENCE,
    DefenseError,
)
from phishguard.evasion.common import BANK, BANK_REFERENCE, EvasionError
from phishguard.finetune.common import MODEL_DIRECTORY, FineTuneError
from phishguard.finetune.common import SELECTION_REFERENCE as PARENT_SELECTION
from phishguard.pretrained.source import PretrainedError
from phishguard.refresh.common import DATA, REFERENCE
from phishguard.validation import MAX_JSON_BYTES, ContractError, validate_json


def register(commands):
    actions = commands.add_parser(
        "defense", help="Train and compare the separate augmentation defense"
    ).add_subparsers(dest="action", required=True)
    for action in ("prepare", "train", "prepare-fresh", "evaluate", "predict"):
        parser = actions.add_parser(action)
        if action != "predict":
            parser.add_argument("--dataset", type=Path, default=DATA)
            parser.add_argument("--reference", type=Path, default=REFERENCE)
            default = {
                "prepare": AUGMENTATION,
                "train": MODEL,
                "prepare-fresh": FRESH_BANK,
                "evaluate": Path("artifacts/defense-evaluation-v1"),
            }[action]
            parser.add_argument("--output", type=Path, default=default)
        if action in {"train", "evaluate"}:
            parser.add_argument("--parent-model", type=Path, default=MODEL_DIRECTORY)
            parser.add_argument("--parent-selection", type=Path, default=PARENT_SELECTION)
        if action == "train":
            parser.add_argument("--augmentation", type=Path, default=AUGMENTATION)
            parser.add_argument(
                "--augmentation-reference", type=Path, default=AUGMENTATION_REFERENCE
            )
            parser.add_argument("--review-reference", type=Path, default=REVIEW_REFERENCE)
        if action in {"evaluate", "predict"}:
            parser.add_argument("--model", type=Path, default=MODEL)
        if action == "evaluate":
            parser.add_argument("--baseline-model", type=Path, default=Path("models/baseline-v2"))
            parser.add_argument("--fixed-bank", type=Path, default=BANK)
            parser.add_argument("--fixed-reference", type=Path, default=BANK_REFERENCE)
            parser.add_argument("--fresh-bank", type=Path, default=FRESH_BANK)
            parser.add_argument("--fresh-reference", type=Path, default=FRESH_REFERENCE)
            parser.add_argument("--selection-reference", type=Path, default=SELECTION_REFERENCE)
        if action == "predict":
            parser.add_argument(
                "--file", required=True, help="JSON email file, or - for standard input"
            )


def run(args):
    last_progress = 0.0

    def progress(event):
        nonlocal last_progress
        if event["status"] == "epoch_complete" or time.monotonic() - last_progress >= 20:
            print(json.dumps(event), file=sys.stderr, flush=True)
            last_progress = time.monotonic()

    try:
        if args.action in {"prepare", "prepare-fresh"}:
            from phishguard.defense.data import prepare, prepare_fresh

            function = prepare if args.action == "prepare" else prepare_fresh
            manifest = function(args.dataset, args.reference, args.output)
            result = {
                "status": "prepared",
                "version": manifest["version"],
                "partitions": manifest.get("partitions"),
                "variants": manifest.get("variants"),
            }
        elif args.action == "train":
            from phishguard.defense.training import train

            report = train(
                args.dataset,
                args.reference,
                args.parent_model,
                args.parent_selection,
                args.augmentation,
                args.augmentation_reference,
                args.review_reference,
                args.output,
                progress,
            )
            result = {
                "status": "trained",
                "selection": report["selection"],
                "validation_clean": report["validation_clean"],
                "validation_perturbed": report["validation_perturbed"],
            }
        elif args.action == "evaluate":
            from phishguard.defense.evaluation import evaluate

            report = evaluate(
                args.dataset,
                args.reference,
                args.fixed_bank,
                args.fixed_reference,
                args.fresh_bank,
                args.fresh_reference,
                args.baseline_model,
                args.parent_model,
                args.parent_selection,
                args.model,
                args.selection_reference,
                args.output,
                progress,
            )
            result = {
                "status": "evaluated",
                "predictions_sha256": report["predictions_sha256"],
                "reserve_rows_scored": 0,
            }
        else:
            from phishguard.defense.model import load_detector

            if args.file == "-":
                payload = sys.stdin.buffer.read(MAX_JSON_BYTES + 1)
            else:
                with Path(args.file).open("rb") as stream:
                    payload = stream.read(MAX_JSON_BYTES + 1)
            result = load_detector(args.model).predict(validate_json("email", payload))
    except (
        DefenseError,
        EvasionError,
        FineTuneError,
        BaselineError,
        AuditError,
        DatasetError,
        PretrainedError,
        ContractError,
        OSError,
        ModuleNotFoundError,
        RuntimeError,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        code = (
            str(error)
            if isinstance(
                error,
                (
                    DefenseError,
                    EvasionError,
                    FineTuneError,
                    BaselineError,
                    AuditError,
                    DatasetError,
                    PretrainedError,
                ),
            )
            else "defense_input_or_runtime_error"
        )
        if isinstance(error, ModuleNotFoundError):
            code = "defense_dependencies_missing"
        if args.action == "predict":
            print(
                UnavailablePrediction(
                    reason="model_load_failed", model_id=MODEL_ID
                ).model_dump_json()
            )
        print(json.dumps({"status": "error", "code": code}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0
