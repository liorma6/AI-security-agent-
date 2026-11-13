"""Local audit commands with text-free responses and an intentionally unscored reserve."""

import json
import sys
import tarfile
from pathlib import Path

from phishguard.audit.common import (
    DEFAULT_CACHE,
    DEFAULT_DATASET,
    DEFAULT_REFERENCE,
    AuditError,
    fetch,
)
from phishguard.audit.data import prepare
from phishguard.audit.runner import evaluate_external, internal_audit
from phishguard.baseline.common import BaselineError
from phishguard.datasets.source import DatasetError
from phishguard.pretrained.source import PretrainedError
from phishguard.validation import ContractError


def register(commands):
    actions = commands.add_parser(
        "audit", help="Audit generalization of the frozen baseline"
    ).add_subparsers(dest="action", required=True)
    fetch_command = actions.add_parser("fetch")
    fetch_command.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    prep = actions.add_parser("prepare")
    prep.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    prep.add_argument("--internal", type=Path, default=Path("data/processed/ephishllm-v1"))
    prep.add_argument(
        "--internal-reference", type=Path, default=Path("data/manifests/ephishllm-v1.json")
    )
    prep.add_argument("--output", type=Path, default=DEFAULT_DATASET)
    for name in ("internal", "evaluate"):
        command = actions.add_parser(name)
        command.add_argument("--model", type=Path, default=Path("models/baseline-v1"))
        command.add_argument(
            "--dataset",
            type=Path,
            default=(
                Path("data/processed/ephishllm-v1") if name == "internal" else DEFAULT_DATASET
            ),
        )
        command.add_argument(
            "--reference",
            type=Path,
            default=(
                Path("data/manifests/ephishllm-v1.json")
                if name == "internal"
                else DEFAULT_REFERENCE
            ),
        )
        command.add_argument(
            "--output",
            type=Path,
            default=Path(
                "artifacts/generalization-"
                + ("internal-v1" if name == "internal" else "external-v1")
            ),
        )
        if name == "internal":
            command.add_argument(
                "--baseline-report", type=Path, default=Path("docs/reports/baseline-test.json")
            )


def run(args):
    try:
        if args.action == "fetch":
            result = fetch(args.cache)
        elif args.action == "prepare":
            manifest = prepare(args.cache, args.internal, args.internal_reference, args.output)
            result = {
                "status": "prepared",
                "partitions": manifest["partitions"],
                "exclusions": manifest["exclusion_counts"],
            }
        elif args.action == "internal":
            report = internal_audit(
                args.dataset, args.reference, args.model, args.baseline_report, args.output
            )
            result = {
                "status": "audited",
                "metrics": report["metrics"],
                "broader_connected_test_rows": report["broader_connected_test_rows"],
            }
        else:
            report = evaluate_external(args.dataset, args.reference, args.model, args.output)
            result = {"status": "evaluated", "metrics": report["metrics"], "reserve_rows_scored": 0}
    except (AuditError, BaselineError, DatasetError, PretrainedError) as error:
        print(json.dumps({"status": "error", "code": str(error)}), file=sys.stderr)
        return 1
    except ContractError:
        print(json.dumps({"status": "error", "code": "invalid_audit_record"}), file=sys.stderr)
        return 1
    except (OSError, tarfile.TarError, UnicodeError, RecursionError):
        print(json.dumps({"status": "error", "code": "audit_io_or_parse_error"}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0
