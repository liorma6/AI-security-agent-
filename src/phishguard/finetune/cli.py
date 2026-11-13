"""Optional neural commands with input-free output and bounded error handling."""

import json
import sys
import time
import urllib.error
from pathlib import Path

from phishguard.audit.common import AuditError
from phishguard.baseline.common import BaselineError
from phishguard.contracts import UnavailablePrediction
from phishguard.datasets.source import DatasetError
from phishguard.finetune.common import (
    MODEL_DIRECTORY,
    MODEL_ID,
    SELECTION_REFERENCE,
    SOURCE_DIRECTORY,
    FineTuneError,
    fetch,
    verify_source,
)
from phishguard.pretrained.source import PretrainedError
from phishguard.refresh.common import DATA, REFERENCE
from phishguard.validation import MAX_JSON_BYTES, ContractError, validate_json


def register(commands):
    actions = commands.add_parser(
        "finetune", help="Train and compare the frozen small transformer"
    ).add_subparsers(dest="action", required=True)
    for name in ("fetch", "verify", "train", "evaluate", "predict"):
        command = actions.add_parser(name)
        if name in {"fetch", "verify", "train"}:
            command.add_argument("--source", type=Path, default=SOURCE_DIRECTORY)
        if name in {"train", "evaluate"}:
            command.add_argument("--dataset", type=Path, default=DATA)
            command.add_argument("--reference", type=Path, default=REFERENCE)
            command.add_argument(
                "--output",
                type=Path,
                default=MODEL_DIRECTORY
                if name == "train"
                else Path("artifacts/finetuned-evaluation-v1"),
            )
        if name in {"evaluate", "predict"}:
            command.add_argument("--model", type=Path, default=MODEL_DIRECTORY)
        if name == "evaluate":
            command.add_argument("--baseline-model", type=Path, default=Path("models/baseline-v2"))
            command.add_argument("--selection-reference", type=Path, default=SELECTION_REFERENCE)
        if name == "predict":
            command.add_argument(
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
        if args.action == "fetch":
            result = fetch(args.source)
        elif args.action == "verify":
            result = verify_source(args.source)
        elif args.action == "train":
            from phishguard.finetune.training import train

            report = train(args.dataset, args.reference, args.source, args.output, progress)
            result = {
                "status": "trained",
                "selection": report["selection"],
                "validation_metrics": report["validation_metrics"],
            }
        elif args.action == "evaluate":
            from phishguard.finetune.evaluation import evaluate

            report = evaluate(
                args.dataset,
                args.reference,
                args.model,
                args.baseline_model,
                args.selection_reference,
                args.output,
                progress,
            )
            result = {
                "status": "evaluated",
                "metrics": {
                    s: {m: r["metrics"] for m, r in c["results"].items()}
                    for s, c in report["cohorts"].items()
                },
                "reserve_rows_scored": 0,
            }
        else:
            from phishguard.finetune.model import load_detector

            if args.file == "-":
                payload = sys.stdin.buffer.read(MAX_JSON_BYTES + 1)
            else:
                with Path(args.file).open("rb") as stream:
                    payload = stream.read(MAX_JSON_BYTES + 1)
            result = load_detector(args.model).predict(validate_json("email", payload))
    except (
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
        urllib.error.URLError,
    ) as error:
        code = (
            str(error)
            if isinstance(
                error, (FineTuneError, BaselineError, AuditError, DatasetError, PretrainedError)
            )
            else "finetuning_input_or_runtime_error"
        )
        if isinstance(error, ModuleNotFoundError):
            code = "finetuning_dependencies_missing"
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
