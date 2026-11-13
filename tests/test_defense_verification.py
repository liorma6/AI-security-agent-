"""Hand-counted examples for the independent experiment-report adapter."""

from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "labels,scores,confusion,accuracy,recall,fpr",
    [
        ([1, 1, 0, 0], [0.8, 0.2, 0.7, 0.1], {"tp": 1, "fn": 1, "fp": 1, "tn": 1}, 0.5, 0.5, 0.5),
        ([0, 0], [0.1, 0.2], {"tp": 0, "fn": 0, "fp": 0, "tn": 2}, 1.0, None, 0.0),
    ],
)
def test_independent_recount_matches_report_contract(
    monkeypatch, labels, scores, confusion, accuracy, recall, fpr
):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    from verify_defense import recount

    result = recount(labels, scores, 0.5)
    assert result["confusion"] == confusion
    assert result["accuracy"] == accuracy
    assert result["recall"] == recall
    assert result["false_positive_rate"] == fpr
    assert "balanced_accuracy" not in result
