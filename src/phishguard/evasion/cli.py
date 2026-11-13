"""Fixed local experiment commands; no network or training actions."""

import json
import sys
import time
from pathlib import Path

from phishguard.audit.common import AuditError
from phishguard.baseline.common import BaselineError
from phishguard.datasets.source import DatasetError
from phishguard.evasion.common import BANK, BANK_REFERENCE, EvasionError
from phishguard.finetune.common import MODEL_DIRECTORY, SELECTION_REFERENCE, FineTuneError
from phishguard.refresh.common import DATA, REFERENCE


def register(commands):
    actions = commands.add_parser(
        "evasion", help="Bounded offline robustness experiments"
    ).add_subparsers(dest="action", required=True)
    for name in ("preview", "prepare", "verify", "evaluate"):
        command = actions.add_parser(name)
        command.add_argument("--dataset", type=Path, default=DATA)
        command.add_argument("--reference", type=Path, default=REFERENCE)
        if name != "verify":
            command.add_argument(
                "--output",
                type=Path,
                default={
                    "preview": Path("artifacts/evasion-preflight-v1"),
                    "prepare": BANK,
                    "evaluate": Path("artifacts/evasion-evaluation-v1"),
                }[name],
            )
        if name in {"verify", "evaluate"}:
            command.add_argument("--bank", type=Path, default=BANK)
            command.add_argument("--bank-reference", type=Path, default=BANK_REFERENCE)
        if name == "evaluate":
            command.add_argument("--baseline-model", type=Path, default=Path("models/baseline-v2"))
            command.add_argument("--model", type=Path, default=MODEL_DIRECTORY)
            command.add_argument("--selection-reference", type=Path, default=SELECTION_REFERENCE)


def run(args):
    from phishguard.evasion.data import prepare, preview, verify

    last_progress = 0.0

    def progress(event):
        nonlocal last_progress
        if time.monotonic() - last_progress >= 20:
            print(json.dumps(event), file=sys.stderr, flush=True)
            last_progress = time.monotonic()

    try:
        if args.action in {"preview", "prepare"}:
            report = {"preview": preview, "prepare": prepare}[args.action](
                args.dataset, args.reference, args.output
            )
            result = {
                "status": args.action,
                "samples": report.get("sample_count"),
                "variants": report.get("variants"),
                "cohorts": report.get("cohorts"),
            }
        elif args.action == "verify":
            _, _, manifest = verify(args.dataset, args.reference, args.bank, args.bank_reference)
            result = {"status": "verified", "variants": manifest["variants"]}
        else:
            from phishguard.evasion.runner import evaluate

            report = evaluate(
                args.dataset,
                args.reference,
                args.bank,
                args.bank_reference,
                args.baseline_model,
                args.model,
                args.selection_reference,
                args.output,
                progress,
            )
            result = {
                "status": "evaluated",
                "reserve_rows_scored": 0,
                "cohorts": {
                    s: {m: r["evasion"] for m, r in c["models"].items()}
                    for s, c in report["cohorts"].items()
                },
            }
    except (
        EvasionError,
        FineTuneError,
        BaselineError,
        AuditError,
        DatasetError,
        OSError,
        ValueError,
        RuntimeError,
        ImportError,
        KeyError,
        TypeError,
    ) as error:
        code = (
            str(error)
            if isinstance(
                error, (EvasionError, FineTuneError, BaselineError, AuditError, DatasetError)
            )
            else "evasion_input_or_runtime_error"
        )
        print(json.dumps({"status": "error", "code": code}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0
