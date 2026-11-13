"""Contract inspection and reviewed data preparation; no model is invoked."""

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
    args = parser.parse_args(argv)
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
