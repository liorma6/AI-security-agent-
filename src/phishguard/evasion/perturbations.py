"""Model-independent edits with replayable offsets and inherited lineage."""

import math
import re

from phishguard.baseline.preprocessing import preprocess
from phishguard.contracts import EmailInput
from phishguard.datasets.source import digest
from phishguard.evasion.common import PROTOCOL, EvasionError

WORD = re.compile(r"(?<![\w'-])[a-zA-Z]+(?![\w'-])")
PROTECTED = re.compile(
    r"https?://[^\s<>\"']+|www\.[^\s<>\"']+|[\w.+-]+@[\w.-]+\.[a-z]{2,}"
    r"|(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/[^\s<>\"']*)?"
    r"|<[^>]*>|&(?:#x?[0-9a-f]+|\w+);|\b\d[\w:/.-]*\b",
    re.IGNORECASE,
)


def rank(*values):
    return digest(":".join(map(str, (PROTOCOL["seed"], *values))).encode())


def text_digest(email):
    return digest(email.text.encode())


def eligible_words(email, operation):
    body = email.body
    spans = [m.span() for m in PROTECTED.finditer(body)]
    words = []
    for match in WORD.finditer(body):
        word = match.group()
        start, end = match.span()
        if (
            end > PROTOCOL["editable_body_prefix_characters"]
            or not word.islower()
            or len(word) > PROTOCOL["maximum_word_length"]
            or word in PROTOCOL["protected_words"]
            or any(start < right and end > left for left, right in spans)
        ):
            continue
        if operation == "substitute_word":
            allowed = word in PROTOCOL["substitutions"]
        else:
            allowed = len(word) >= PROTOCOL["minimum_typo_word_length"]
        if allowed:
            words.append((start, end, word))
    return words


def apply_edits(email, edits):
    """Replay original-body offsets; reject overlap, tampering and invalid results."""
    body, previous = email.body, len(email.body) + 1
    for edit in reversed(edits):
        start, end = edit["start"], edit["end"]
        if (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start < end <= len(email.body)
            or end > previous
            or email.body[start:end] != edit["before"]
        ):
            raise EvasionError("invalid_edit_trace")
        body = body[:start] + edit["after"] + body[end:]
        previous = start
    return EmailInput(subject=email.subject, body=body)


def replacement(word, operation, key):
    if operation == "substitute_word":
        return PROTOCOL["substitutions"][word]
    if operation == "duplicate_letter":
        position = 1 + int(rank(key, word), 16) % (len(word) - 2)
        return word[:position] + word[position] + word[position:]
    positions = [p for p in range(1, len(word) - 2) if word[p] != word[p + 1]]
    if not positions:
        return word
    position = min(positions, key=lambda p: rank(key, word, p))
    return word[:position] + word[position + 1] + word[position] + word[position + 2 :]


def generate(row, cohort, *, max_candidates=None, max_edits=None):
    """Each candidate starts at the original; no model access or cross-split assignment."""
    cap = PROTOCOL["max_candidates"] if max_candidates is None else max_candidates
    edit_cap = PROTOCOL["max_edits"] if max_edits is None else max_edits
    if (
        type(cap) is not int
        or not 0 <= cap <= PROTOCOL["max_candidates"]
        or type(edit_cap) is not int
        or not 0 <= edit_cap <= PROTOCOL["max_edits"]
        or cohort not in {"train", "test", "challenge"}
        or row.split != ("test" if cohort == "challenge" else cohort)
    ):
        raise EvasionError("invalid_perturbation_scope_or_budget")
    count = len(WORD.findall(row.email.body))
    limit = min(edit_cap, math.floor(count * PROTOCOL["max_changed_word_fraction"]))
    if not cap or not limit:
        return []
    variants, seen = [], {text_digest(row.email)}
    for proposal in range(PROTOCOL["proposals_per_operation"]):
        for operation in PROTOCOL["operations"]:
            words = sorted(
                eligible_words(row.email, operation),
                key=lambda w: rank(row.example_id, operation, proposal, w[0]),
            )
            edits = []
            for start, end, word in words:
                after = replacement(word, operation, (row.example_id, proposal, start))
                if after == word:
                    continue
                edits.append({"start": start, "end": end, "before": word, "after": after})
                if len(edits) == min(limit, PROTOCOL["candidate_edit_counts"][proposal]):
                    break
            if not edits:
                continue
            edits.sort(key=lambda e: e["start"])
            try:
                email = apply_edits(row.email, edits)
            except ValueError:
                continue  # Includes character-limit violations; never silently truncate.
            fingerprint = text_digest(email)
            if fingerprint in seen or preprocess(email.text) == preprocess(row.email.text):
                continue
            seen.add(fingerprint)
            variants.append(
                {
                    "schema_version": "1.0",
                    "variant_id": "ev6-" + rank(cohort, row.example_id, fingerprint)[:24],
                    "parent_id": row.example_id,
                    "group_id": row.group_id,
                    "split": row.split,
                    "cohort": cohort,
                    "label": row.label,
                    "source_id": row.source_id,
                    "operation": operation,
                    "seed": PROTOCOL["seed"],
                    "proposal": proposal,
                    "candidate_index": len(variants) + 1,
                    "original_sha256": text_digest(row.email),
                    "variant_sha256": fingerprint,
                    "changed_words": len(edits),
                    "body_words": count,
                    "constraint_status": "passed_not_semantically_certified",
                    "edits": edits,
                    "email": email.model_dump(),
                }
            )
            if len(variants) == cap:
                return variants
    return variants
