"""Optional pretrained commands; fixed error codes never echo email content."""

import json
import sys
import time
from pathlib import Path

from phishguard.baseline.common import BaselineError
from phishguard.contracts import UnavailablePrediction
from phishguard.pretrained.selection import load_selection
from phishguard.pretrained.source import SOURCE, PretrainedError, download_source, verify_source
from phishguard.validation import MAX_JSON_BYTES, ContractError, validate_json


def run(args) -> int:
    last_progress = 0.0

    def progress(done, total):
        nonlocal last_progress
        if time.monotonic() - last_progress >= 20 or done == total:
            print(
                json.dumps({"status": "scoring", "rows": done, "total": total}),
                file=sys.stderr,
                flush=True,
            )
            last_progress = time.monotonic()

    try:
        if args.action == "fetch":
            result = download_source(args.model)
        elif args.action == "verify":
            result = verify_source(args.model)
        else:
            from phishguard.pretrained.adapter import load_classifier
            from phishguard.pretrained.runner import evaluate_pretrained, select_pretrained

            if args.action == "predict":
                if args.file == "-":
                    payload = sys.stdin.buffer.read(MAX_JSON_BYTES + 1)
                else:
                    with Path(args.file).open("rb") as stream:
                        payload = stream.read(MAX_JSON_BYTES + 1)
                email = validate_json("email", payload)
                threshold = load_selection(args.selection).threshold if args.selection else 0.5
                result = load_classifier(args.model).predict(email, threshold)
            elif args.action == "select":
                report = select_pretrained(
                    args.dataset,
                    args.reference,
                    args.model,
                    args.baseline_model,
                    args.output,
                    progress,
                )
                result = {
                    "status": "selected",
                    "metrics": report["validation_at_selected_threshold"],
                }
            else:
                report = evaluate_pretrained(
                    args.dataset,
                    args.reference,
                    args.model,
                    args.baseline_model,
                    args.selection,
                    args.baseline_report,
                    args.output,
                    progress,
                )
                result = {
                    "status": "evaluated",
                    "metrics": report["metrics"],
                    "tokens": report["tokens"],
                    "timing": report["timing"],
                }
    except ContractError as error:
        print(json.dumps(error.to_dict()), file=sys.stderr)
        return 1
    except (PretrainedError, BaselineError, OSError, ModuleNotFoundError, RuntimeError) as error:
        if isinstance(error, ModuleNotFoundError):
            code = "pretrained_dependencies_missing"
        elif isinstance(error, (PretrainedError, BaselineError)):
            code = str(error)
        elif isinstance(error, RuntimeError):
            code = "model_inference_failed"
        else:
            code = "pretrained_io_error"
        if args.action == "predict":
            reason = (
                "model_not_loaded"
                if code in ("model_not_downloaded", "pretrained_dependencies_missing")
                else "model_load_failed"
            )
            print(
                UnavailablePrediction(reason=reason, model_id=SOURCE["model_id"]).model_dump_json()
            )
        print(json.dumps({"status": "error", "code": code}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0
