"""Tests for deterministic invoice evaluation scoring."""

from evals.runner import summarize_result
from evals.schemas import EvalResult
from evals.scorer import score_invoice


def _expected_invoice():
    return {
        "vendor_name": "Example Supplier",
        "invoice_number": "INV-100",
        "date": "2026-09-01",
        "store_id": "quadra",
        "subtotal": 100.0,
        "tax_amount": 12.0,
        "deposit_amount": 0.0,
        "total_amount": 112.0,
        "line_items": [
            {
                "sku": "001234",
                "description": "Example Wine",
                "quantity": 12,
                "units_per_case": 12,
                "unit_cost": 8.33,
                "amount": 99.96,
            }
        ],
    }


def test_exact_match_is_straight_through_ready():
    expected = _expected_invoice()
    actual = _expected_invoice()

    score = score_invoice("case-1", expected, actual)

    assert score.straight_through_ready is True
    assert score.dangerous_false_clean is False
    assert score.metric("sku") == 1.0
    assert score.metric("quantity") == 1.0


def test_wrong_quantity_is_dangerous_false_clean():
    expected = _expected_invoice()
    actual = _expected_invoice()
    actual["line_items"][0]["quantity"] = 1

    score = score_invoice("case-1", expected, actual, candidate_marked_clean=True)

    assert score.straight_through_ready is False
    assert score.dangerous_false_clean is True
    assert score.metric("quantity") == 0.0


def test_missing_line_blocks_straight_through():
    expected = _expected_invoice()
    actual = _expected_invoice()
    actual["line_items"] = []

    score = score_invoice("case-1", expected, actual)

    assert score.straight_through_ready is False
    assert score.missing_line_count == 1


def test_sku_leading_zeroes_are_significant():
    expected = _expected_invoice()
    actual = _expected_invoice()
    actual["line_items"][0]["sku"] = "1234"

    score = score_invoice("case-1", expected, actual)

    assert score.metric("sku") == 0.0
    assert score.straight_through_ready is False


def test_summary_reports_operational_metrics():
    expected = _expected_invoice()
    exact = score_invoice("case-1", expected, _expected_invoice())

    wrong = _expected_invoice()
    wrong["line_items"][0]["quantity"] = 1
    failed = score_invoice("case-2", expected, wrong)

    result = EvalResult(pipeline_name="test", scores=[exact, failed])
    summary = summarize_result(result)

    assert summary["invoice_count"] == 2
    assert summary["clean_pass_rate"] == 0.5
    assert summary["false_clean_rate"] == 0.5
    assert summary["quantity_accuracy"] == 0.5
