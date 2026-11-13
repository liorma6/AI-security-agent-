"""Data refresh commands with separate development and evaluation boundaries."""

import csv
import json
import sys
import tarfile
from pathlib import Path

from pydantic import ValidationError

from phishguard.audit.common import DEFAULT_CACHE, DEFAULT_DATASET, DEFAULT_REFERENCE, AuditError
from phishguard.baseline.common import BaselineError
from phishguard.datasets.source import DatasetError
from phishguard.pretrained.source import PretrainedError
from phishguard.refresh.common import CACHE, DATA, REFERENCE, fetch
from phishguard.refresh.data import prepare
from phishguard.refresh.diagnosis import diagnose
from phishguard.refresh.runner import evaluate, train
from phishguard.validation import ContractError


def register(commands):
    actions = commands.add_parser(
        "refresh", help="Improve data and re-evaluate the classical baseline"
    ).add_subparsers(dest="action", required=True)
    fetch_command = actions.add_parser("fetch")
    fetch_command.add_argument("--cache", type=Path, default=CACHE)
    prep = actions.add_parser("prepare")
    prep.add_argument("--cache", type=Path, default=CACHE)
    prep.add_argument("--internal", type=Path, default=Path("data/processed/ephishllm-v1"))
    prep.add_argument(
        "--internal-reference", type=Path, default=Path("data/manifests/ephishllm-v1.json")
    )
    prep.add_argument("--audit", type=Path, default=DEFAULT_DATASET)
    prep.add_argument("--audit-reference", type=Path, default=DEFAULT_REFERENCE)
    prep.add_argument("--audit-cache", type=Path, default=DEFAULT_CACHE)
    prep.add_argument("--output", type=Path, default=DATA)
    diagnosis = actions.add_parser("diagnose")
    diagnosis.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    diagnosis.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    diagnosis.add_argument(
        "--predictions",
        type=Path,
        default=Path("artifacts/generalization-external-v1/predictions.jsonl"),
    )
    diagnosis.add_argument(
        "--report", type=Path, default=Path("docs/reports/generalization-external.json")
    )
    diagnosis.add_argument("--output", type=Path, default=Path("artifacts/refresh-error-diagnosis"))
    for name in ("train", "evaluate"):
        command = actions.add_parser(name)
        command.add_argument("--dataset", type=Path, default=DATA)
        command.add_argument("--reference", type=Path, default=REFERENCE)
        command.add_argument(
            "--output",
            type=Path,
            default=Path(
                "models/baseline-v2" if name == "train" else "artifacts/real-mail-v2-evaluation"
            ),
        )
        if name == "evaluate":
            command.add_argument("--model", type=Path, default=Path("models/baseline-v2"))
            command.add_argument("--old-model", type=Path, default=Path("models/baseline-v1"))
            command.add_argument(
                "--selection-reference",
                type=Path,
                default=Path("data/manifests/baseline-v2-selection.json"),
            )


def run(args):
    try:
        if args.action == "fetch":
            result = fetch(args.cache)
        elif args.action == "prepare":
            report = prepare(
                args.cache,
                args.internal,
                args.internal_reference,
                args.audit,
                args.audit_reference,
                args.audit_cache,
                args.output,
            )
            result = {
                "status": "prepared",
                "partitions": report["partitions"],
                "exclusions": report["exclusion_counts"],
            }
        elif args.action == "diagnose":
            report = diagnose(
                args.dataset, args.reference, args.predictions, args.report, args.output
            )
            result = {
                "status": "diagnosed",
                "error_rows": report["error_rows"],
                "control_rows": report["control_rows"],
            }
        elif args.action == "train":
            report = train(args.dataset, args.reference, args.output)
            result = {
                "status": "trained",
                "validation_metrics": report["validation_metrics"],
                "selection": report["selection"],
            }
        else:
            report = evaluate(
                args.dataset,
                args.reference,
                args.model,
                args.old_model,
                args.selection_reference,
                args.output,
            )
            result = {
                "status": "evaluated",
                "metrics": {
                    s: {m: r["metrics"] for m, r in c["results"].items()}
                    for s, c in report["cohorts"].items()
                },
                "reserve_rows_scored": 0,
            }
    except (AuditError, BaselineError, DatasetError, PretrainedError) as error:
        print(json.dumps({"status": "error", "code": str(error)}), file=sys.stderr)
        return 1
    except (
        OSError,
        UnicodeError,
        csv.Error,
        tarfile.TarError,
        KeyError,
        TypeError,
        ValidationError,
        ContractError,
        RecursionError,
        ValueError,
    ):
        print(json.dumps({"status": "error", "code": "refresh_input_or_io_error"}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0
