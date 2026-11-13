"""Text-free profiles of all previous audit errors and deterministic correct controls."""

import json
import re
import unicodedata
from collections import Counter

from phishguard.audit.common import AuditError
from phishguard.audit.data import load_audit
from phishguard.audit.runner import save
from phishguard.baseline.common import parse_json, read_bytes
from phishguard.datasets.source import digest
from phishguard.refresh.common import PROTOCOL
from phishguard.refresh.text import HTML_ROOT, PLACEHOLDER


def indicators(email):
    text = email.text
    flags = {
        "short_body_under_80": len(email.body.strip()) < 80,
        "plain_placeholder": bool(PLACEHOLDER.fullmatch(email.body.strip())),
        "html_root_in_body": bool(HTML_ROOT.search(email.body)),
        "unicode_format_character": any(unicodedata.category(c) == "Cf" for c in text),
        "url": bool(re.search(r"https?://", text, re.I)),
        "quoted_reply": bool(re.search(r"(?m)^\s*>", email.body)),
        "technical_or_list_words": bool(
            re.search(
                r"\b(?:linux|kernel|mailing.list|rpm|sourceforge|debug|gcc|unsubscribe)\b",
                text,
                re.I,
            )
        ),
        "financial_words": bool(
            re.search(r"\b(?:invoice|payment|bank|purchase|refund|billing)\b", text, re.I)
        ),
        "account_words": bool(
            re.search(r"\b(?:account|password|login|verify|verification|security)\b", text, re.I)
        ),
    }
    return [name for name, active in flags.items() if active]


def diagnose(directory, reference, predictions_path, report_path, output):
    if output.exists():
        raise AuditError("output_already_exists")
    rows, _, sha = load_audit(directory, reference)
    payload = read_bytes(predictions_path)
    previous = parse_json(read_bytes(report_path))
    if (
        sha != PROTOCOL["external_manifest_sha256"]
        or previous["model_revision"] != PROTOCOL["old_model_revision"]
        or previous["predictions_sha256"] != digest(payload)
    ):
        raise AuditError("previous_audit_mismatch")
    predictions = [json.loads(line) for line in payload.splitlines()]
    by_id = {p["example_id"]: p for p in predictions}
    if (
        len(by_id) != len(rows)
        or len(predictions) != len(rows)
        or set(by_id) != {r.example_id for r in rows}
    ):
        raise AuditError("previous_prediction_membership_mismatch")
    if any(by_id[r.example_id]["label"] != r.label for r in rows):
        raise AuditError("previous_prediction_label_mismatch")
    errors = [r for r in rows if by_id[r.example_id]["decision"] != r.label]
    controls = sorted(
        [r for r in rows if by_id[r.example_id]["decision"] == r.label],
        key=lambda r: digest(("stage4b-controls:" + r.example_id).encode()),
    )[:24]
    profiles = []
    for row in errors + controls:
        profiles.append(
            {
                "example_id": row.example_id,
                "source_id": row.source_id,
                "label": row.label,
                "decision": by_id[row.example_id]["decision"],
                "kind": "control" if row in controls else "error",
                "body_characters": len(row.email.body),
                "indicators": indicators(row.email),
            }
        )
    report = {
        "phase": "stage4b-old-error-diagnosis",
        "audit_manifest_sha256": sha,
        "predictions_sha256": digest(payload),
        "error_rows": len(errors),
        "control_rows": len(controls),
        "reserve_rows_read": 0,
        "counts": {
            kind: dict(
                Counter(flag for p in profiles if p["kind"] == kind for flag in p["indicators"])
            )
            for kind in ("error", "control")
        },
        "profiles": profiles,
        "limitations": [
            "Indicators are overlapping text associations, not causal diagnoses.",
            "Excerpt triage does not independently validate whole-message labels.",
        ],
    }
    return save(output, report)
