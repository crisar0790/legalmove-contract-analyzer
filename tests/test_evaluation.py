"""Tests for section metrics and empty-set conventions."""

import pytest

from evaluation.run_evaluation import section_metrics


@pytest.mark.parametrize(
    ("expected", "detected", "precision", "recall"),
    [
        (["Cláusula 3"], ["Cláusula 3"], 1.0, 1.0),
        (["Cláusula 3"], [], 0.0, 0.0),
        ([], [], 1.0, 1.0),
        ([], ["Cláusula 3"], 0.0, 1.0),
        (
            ["Cláusula 2", "Cláusula 4"],
            ["Cláusula 2", "Cláusula 7"],
            0.5,
            0.5,
        ),
    ],
)
def test_section_metrics(expected, detected, precision, recall):
    result = section_metrics(expected, detected)

    assert result["precision"] == precision
    assert result["recall"] == recall


def test_normalizes_case_and_whitespace():
    result = section_metrics(
        ["Cláusula 3"],
        ["  CLÁUSULA   3  "],
    )

    assert result["precision"] == 1.0
    assert result["recall"] == 1.0


def test_reports_false_positives_and_omissions():
    result = section_metrics(
        ["Cláusula 2", "Cláusula 4"],
        ["Cláusula 2", "Cláusula 7"],
    )

    assert result["false_positives"] == ["cláusula 7"]
    assert result["false_negatives"] == ["cláusula 4"]
