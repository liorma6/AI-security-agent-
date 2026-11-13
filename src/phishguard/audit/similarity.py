"""Exact prefix-index search for broader text/template relations; no fitted classifier."""

import re
from collections import Counter, defaultdict
from fractions import Fraction

from phishguard.audit.common import AuditError
from phishguard.baseline.preprocessing import MARKER, preprocess
from phishguard.datasets.grouping import canonical, template


def relations(records, threshold=0.70):
    if not 0 < threshold <= 1 or len(records) > 25000:
        raise AuditError("invalid_similarity_request")
    ids = [r.example_id for r in records]
    if len(set(ids)) != len(ids):
        raise AuditError("duplicate_example_id")
    parent = {rid: rid for rid in ids}
    edges, keys, shingles = [], {}, {}

    def root(rid):
        while parent[rid] != rid:
            parent[rid] = parent[parent[rid]]
            rid = parent[rid]
        return rid

    def connect(left, right, reason, similarity=1.0):
        a, b = root(left), root(right)
        parent[max(a, b)] = min(a, b)
        if len(edges) >= 500000:
            raise AuditError("similarity_edge_limit")
        edges.append((left, right, reason, similarity))

    for row in sorted(records, key=lambda r: r.example_id):
        rid = row.example_id
        subject = re.sub(r"^(?:(?:re|fwd?)\s*:\s*)+", "", canonical(row.email.subject))
        body = canonical(MARKER.sub(" ", row.email.body))
        masked = template(body)
        row_keys = [("exact_input", canonical(preprocess(row.email.text)))]
        if len(body) >= 20:
            row_keys.append(("exact_body", body))
        if len(subject) >= 15 and len(subject.split()) >= 3:
            row_keys.append(("subject", subject))
        words = masked.split()
        if len(words) >= 10:
            row_keys.append(("template", masked))
            shingles[rid] = set(zip(words, words[1:], words[2:], strict=False))
        for key in row_keys:
            if key in keys:
                connect(rid, keys[key], key[0])
            else:
                keys[key] = rid
    numerator, denominator = Fraction(str(threshold)).as_integer_ratio()
    frequency = Counter(s for values in shingles.values() for s in values)
    index = defaultdict(list)
    for rid in sorted(shingles, key=lambda key: (len(shingles[key]), key)):
        values = shingles[rid]
        length = len(values)
        required = (numerator * length + denominator - 1) // denominator
        prefix = sorted(values, key=lambda s: (frequency[s], s))[: length - required + 1]
        candidates = {other for shingle in prefix for other in index[shingle]}
        for other in sorted(candidates):
            other_values = shingles[other]
            if denominator * len(other_values) < numerator * length:
                continue
            common = len(values & other_values)
            union = length + len(other_values) - common
            if denominator * common >= numerator * union:
                connect(rid, other, "near_body", common / union)
        for shingle in prefix:
            index[shingle].append(rid)
    groups = defaultdict(list)
    for rid in sorted(ids):
        groups[root(rid)].append(rid)
    return sorted(groups.values()), edges
