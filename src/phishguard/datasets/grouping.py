"""Deterministic conservative template groups, not inferred campaign identities."""

import hashlib
import re
import unicodedata
from collections import Counter, defaultdict

from phishguard.contracts import EmailExample
from phishguard.datasets.source import DatasetError


def canonical(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def template(text: str) -> str:
    text = canonical(text)
    text = re.sub(r"<<[^<>]*>>|\[[^\[\]]*\]", " placeholder ", text)
    text = re.sub(r"https?://\S+|www\.\S+", " url ", text)
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\b", " email ", text)
    text = re.sub(r"\d+", " number ", text)
    return " ".join(text.split())


def related_components(records: list[EmailExample]) -> list[list[str]]:
    """Union exact text, subject, body template, near-body and declared lineage edges.

    Near-body edges use exact Jaccard >= 0.90 over word-trigram sets. A
    frequency-ordered prefix index prunes candidates without approximate hashes.
    Frequency ordering is used solely for deduplication, never as a model feature.
    """
    by_id = {r.example_id: r for r in records}
    if len(by_id) != len(records):
        raise DatasetError("duplicate_example_id")
    parent = {key: key for key in by_id}

    def root(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def union(a, b):
        a, b = root(a), root(b)
        parent[max(a, b)] = min(a, b)

    keys = {}
    shingles = {}
    for record in sorted(records, key=lambda r: r.example_id):
        rid = record.example_id
        subject = canonical(record.email.subject)
        body = template(record.email.body)
        record_keys = [("exact", canonical(record.email.text))]
        if len(subject) >= 15 and len(subject.split()) >= 3:
            record_keys.append(("subject", subject))
        words = body.split()
        if len(words) >= 10:
            record_keys.append(("body", body))
            shingles[rid] = {tuple(words[i : i + 3]) for i in range(len(words) - 2)}
        for key in record_keys:
            if key in keys:
                union(rid, keys[key])
            else:
                keys[key] = rid
        if record.parent_id:
            if record.parent_id not in by_id:
                raise DatasetError("missing_parent")
            union(rid, record.parent_id)

    # A parent chain must terminate, even when its members share the same split.
    finished = set()
    for rid in by_id:
        trail = set()
        current = rid
        while current is not None and current not in finished:
            if current in trail:
                raise DatasetError("cyclic_lineage")
            trail.add(current)
            current = by_id[current].parent_id
        finished.update(trail)

    frequency = Counter(s for values in shingles.values() for s in values)
    index = defaultdict(list)
    for rid in sorted(shingles, key=lambda key: (len(shingles[key]), key)):
        values = shingles[rid]
        length = len(values)
        ordered = sorted(values, key=lambda s: (frequency[s], s))
        prefix = ordered[: length - (9 * length + 9) // 10 + 1]
        candidates = {other for s in prefix for other in index[s]}
        for other in sorted(candidates):
            other_values = shingles[other]
            if 10 * len(other_values) < 9 * length:
                continue
            common = len(values & other_values)
            if 10 * common >= 9 * (length + len(other_values) - common):
                union(rid, other)
        for shingle in prefix:
            index[shingle].append(rid)

    components = defaultdict(list)
    for rid in sorted(by_id):
        components[root(rid)].append(rid)
    return sorted(components.values())


def group_identifier(members: list[str]) -> str:
    signature = "\n".join(sorted(members)).encode("ascii")
    return "group-" + hashlib.sha256(signature).hexdigest()[:24]
