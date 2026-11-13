"""Privacy-preserving command boundaries for baseline operations."""

import json
import sys
from pathlib import Path

from phishguard.baseline.common import MODEL_ID, BaselineError
from phishguard.baseline.model import load_model
from phishguard.baseline.runner import evaluate_baseline, train_baseline
from phishguard.contracts import UnavailablePrediction
from phishguard.validation import MAX_JSON_BYTES, ContractError, validate_json


def run(args) -> int:
    try:
        if args.action == "train":
            report = train_baseline(args.dataset, args.reference, args.output)
            result = {
                "status": "trained",
                "model_revision": report["model"]["model_revision"],
                "validation": report["validation_at_selected_threshold"],
            }
        elif args.action == "evaluate":
            report = evaluate_baseline(args.dataset, args.reference, args.model, args.output)
            result = {
                "status": "evaluated",
                "model_revision": report["model_revision"],
                "metrics": report["metrics"],
            }
        else:
            if args.file == "-":
                payload = sys.stdin.buffer.read(MAX_JSON_BYTES + 1)
            else:
                with Path(args.file).open("rb") as stream:
                    payload = stream.read(MAX_JSON_BYTES + 1)
            email = validate_json("email", payload)
            try:
                model = load_model(args.model)
            except (BaselineError, OSError) as error:
                reason = "model_load_failed"
                if str(error) == "artifact_missing":
                    reason = "model_not_loaded"
                elif str(error) in {"artifact_integrity_mismatch", "artifact_manifest_mismatch"}:
                    reason = "manifest_mismatch"
                print(UnavailablePrediction(reason=reason, model_id=MODEL_ID).model_dump_json())
                return 1
            result = model.predict(email).model_dump()
    except BaselineError as error:
        print(json.dumps({"status": "error", "code": str(error)}), file=sys.stderr)
        return 1
    except ContractError as error:
        print(json.dumps(error.to_dict()), file=sys.stderr)
        return 1
    except OSError:
        print(json.dumps({"status": "error", "code": "baseline_io_error"}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0
