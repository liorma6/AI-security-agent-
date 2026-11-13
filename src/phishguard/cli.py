"""Research CLI: contracts, frozen datasets and both classifier workflows."""

import argparse
import json
import sys
from pathlib import Path

from phishguard import __version__
from phishguard.contracts import CONTRACTS
from phishguard.datasets.preparation import prepare_source
from phishguard.datasets.source import DEFAULT_CACHE, DatasetError, fetch_source
from phishguard.datasets.verification import verify_dataset
from phishguard.validation import MAX_JSON_BYTES, ContractError, validate_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PhishGuard research-data tools.")
    parser.add_argument("--version", action="version", version=f"PhishGuard {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Check JSON without displaying its contents")
    validate.add_argument("kind", choices=CONTRACTS)
    validate.add_argument("--file", required=True, help="UTF-8 JSON file, or - for standard input")
    schema = commands.add_parser("schema", help="Print structural JSON Schema")
    schema.add_argument("kind", choices=CONTRACTS)
    data = commands.add_parser("data", help="Fetch, prepare or verify reviewed research data")
    actions = data.add_subparsers(dest="action", required=True)
    fetch = actions.add_parser("fetch", help="Download the pinned public source and license card")
    fetch.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    prepare = actions.add_parser("prepare", help="Create a new immutable output directory offline")
    prepare.add_argument("--source", type=Path, default=DEFAULT_CACHE / "ephishLLM.json")
    prepare.add_argument("--output", type=Path, default=Path("data/processed/ephishllm-v1"))
    prepare.add_argument("--seed", type=int, default=42)
    verify = actions.add_parser("verify", help="Verify file integrity and grouped split separation")
    verify.add_argument("--directory", type=Path, default=Path("data/processed/ephishllm-v1"))
    verify.add_argument("--reference", type=Path, help="Require the exact frozen manifest bytes")
    baseline = commands.add_parser("baseline", help="Train, evaluate or use the classical detector")
    baseline_actions = baseline.add_subparsers(dest="action", required=True)
    for action in ("train", "evaluate"):
        command = baseline_actions.add_parser(action)
        command.add_argument("--dataset", type=Path, default=Path("data/processed/ephishllm-v1"))
        command.add_argument(
            "--reference", type=Path, default=Path("data/manifests/ephishllm-v1.json")
        )
        default_output = "models/baseline-v1" if action == "train" else "artifacts/baseline-test-v1"
        command.add_argument("--output", type=Path, default=Path(default_output))
        if action == "evaluate":
            command.add_argument("--model", type=Path, default=Path("models/baseline-v1"))
    predict = baseline_actions.add_parser(
        "predict", help="Score a JSON email locally without storing it"
    )
    predict.add_argument("--model", type=Path, default=Path("models/baseline-v1"))
    predict.add_argument("--file", required=True, help="UTF-8 JSON email, or - for standard input")
    from phishguard.pretrained.source import DEFAULT_MODEL

    pretrained = commands.add_parser("pretrained", help="Compare the pinned external classifier")
    pretrained_actions = pretrained.add_subparsers(dest="action", required=True)
    for action in ("fetch", "verify", "select", "evaluate", "predict"):
        command = pretrained_actions.add_parser(action)
        command.add_argument("--model", type=Path, default=DEFAULT_MODEL)
        if action in ("select", "evaluate"):
            command.add_argument(
                "--dataset", type=Path, default=Path("data/processed/ephishllm-v1")
            )
            command.add_argument(
                "--reference", type=Path, default=Path("data/manifests/ephishllm-v1.json")
            )
            command.add_argument("--baseline-model", type=Path, default=Path("models/baseline-v1"))
            destination = (
                "artifacts/pretrained-selection-v1"
                if action == "select"
                else "artifacts/pretrained-test-v1"
            )
            command.add_argument("--output", type=Path, default=Path(destination))
        if action == "evaluate":
            command.add_argument(
                "--selection", type=Path, default=Path("artifacts/pretrained-selection-v1")
            )
            command.add_argument(
                "--baseline-report", type=Path, default=Path("docs/reports/baseline-test.json")
            )
        if action == "predict":
            command.add_argument("--selection", type=Path, help="Use a frozen validation threshold")
            command.add_argument("--file", required=True, help="UTF-8 JSON email, or - for stdin")
    from phishguard.audit.cli import register

    register(commands)
    from phishguard.refresh.cli import register as register_refresh

    register_refresh(commands)
    from phishguard.finetune.cli import register as register_finetune

    register_finetune(commands)
    args = parser.parse_args(argv)
    if args.command == "finetune":
        from phishguard.finetune.cli import run

        return run(args)
    if args.command == "refresh":
        from phishguard.refresh.cli import run

        return run(args)
    if args.command == "audit":
        from phishguard.audit.cli import run

        return run(args)
    if args.command == "pretrained":
        from phishguard.pretrained.cli import run

        return run(args)
    if args.command == "baseline":
        from phishguard.baseline.cli import run

        return run(args)
    if args.command == "data":
        return data_command(args)
    if args.command == "schema":
        print(json.dumps(CONTRACTS[args.kind].json_schema(), indent=2))
        return 0
    try:
        if args.file == "-":
            data = sys.stdin.buffer.read(MAX_JSON_BYTES + 1)
        else:
            with Path(args.file).open("rb") as stream:
                data = stream.read(MAX_JSON_BYTES + 1)
        record = validate_json(args.kind, data)
    except OSError:
        print(json.dumps({"status": "error", "code": "input_unreadable"}), file=sys.stderr)
        return 2
    except ContractError as error:
        print(json.dumps(error.to_dict()), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {"status": "valid", "contract": args.kind, "schema_version": record.schema_version}
        )
    )
    return 0


def data_command(args: argparse.Namespace) -> int:
    try:
        if args.action == "fetch":
            result = fetch_source(args.cache)
        elif args.action == "prepare":
            manifest = prepare_source(args.source, args.output, args.seed)
            result = {"status": "prepared", "partitions": manifest["partitions"]}
        else:
            result = verify_dataset(args.directory, args.reference)
    except DatasetError as error:
        print(json.dumps({"status": "error", "code": str(error)}), file=sys.stderr)
        return 1
    except OSError:
        print(json.dumps({"status": "error", "code": "dataset_io_error"}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0
