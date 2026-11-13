"""Offline contract inspection; no classifier or model loader is invoked."""

import argparse
import json
import sys
from pathlib import Path

from phishguard import __version__
from phishguard.contracts import CONTRACTS
from phishguard.validation import MAX_JSON_BYTES, ContractError, validate_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate PhishGuard data contracts offline.")
    parser.add_argument("--version", action="version", version=f"PhishGuard {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Check JSON without displaying its contents")
    validate.add_argument("kind", choices=CONTRACTS)
    validate.add_argument("--file", required=True, help="UTF-8 JSON file, or - for standard input")
    schema = commands.add_parser("schema", help="Print structural JSON Schema")
    schema.add_argument("kind", choices=CONTRACTS)
    args = parser.parse_args(argv)
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
