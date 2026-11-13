"""Identical label-independent cleanup for training and inference."""

import re

from phishguard.baseline.common import PROTOCOL, BaselineError

MARKER = re.compile(r"<<.*?>>", re.DOTALL)
WORD = re.compile(PROTOCOL["vectorizer"]["token_pattern"])


def preprocess(text: str) -> str:
    cleaned = " ".join(MARKER.sub(" ", text).split())
    if not WORD.search(cleaned):
        raise BaselineError("no_usable_text")
    return cleaned
