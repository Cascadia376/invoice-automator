"""Deterministic scoring for invoice extraction evaluations."""

from __future__ import annotations

from math import isclose
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .schemas import FieldScore, InvoiceScore, LineItemScore

HEADER_FIELDS = (
    "vendor_name",
    "invoice_number",
    "date",
    "store_id",
    "subtotal",
    "tax_amount",
    "deposit_amount",
    "total_amount",
)

CRITICAL_HEADER_FIELDS = {
    "vendor_name",
    "invoice_number",
    "store_id",
    "total_amount",
}

LINE_FIELDS = (
    "sku",
    "quantity",
    "units_per_case",
    "unit_cost",
    "amount",
)

CRITICAL_LINE_FIELDS = {"sku", "quantity", "amount"}


def _normalized_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    return " ".join(str(value).strip().lower().split())


def _numbers_match(expected: Any, actual: Any, tolerance: float) -> bool:
    try:
        expected_number = float(expected)
        actual_number = float(actual)
    except (TypeError, ValueError):
        return False
    return isclose(expected_number, actual_number, abs_tol=tolerance, rel_tol=0.0)


def _field_matches(field_name: str, expected: Any, actual: Any) -> bool:
    if expected in (None, "") and actual in (None, ""):
        return True

    if field_name in {
        "subtotal",
        "tax_amount",
        "deposit_amount",
        "total_amount",
        "unit_cost",
        "amount",
    }:
        return _numbers_match(expected, actual, tolerance=0.01)

    if field_name in {"quantity", "units_per_case"}:
        return _numbers_match(expected, actual, tolerance=0.0001)

    if field_name == "sku":
        expected_sku = "" if expected is None else str(expected).strip()
        actual_sku = "" if actual is None else str(actual).strip()
        return expected_sku == actual_sku

    return _normalized_text(expected) == _normalized_text(actual)


def _score_fields(
    expected: Dict[str, Any],
    actual: Dict[str, Any],
    fields: Iterable[str],
    critical_fields: set[str],
) -> List[FieldScore]:
    return [
        FieldScore(
            field_name=field_name,
            expected=expected.get(field_name),
            actual=actual.get(field_name),
            matched=_field_matches(
                field_name,
                expected.get(field_name),
                actual.get(field_name),
            ),
            critical=field_name in critical_fields,
        )
        for field_name in fields
        if field_name in expected or field_name in actual
    ]


def _line_key(line: Dict[str, Any]) -> Tuple[str, str]:
    """Return a stable line key, preferring SKU and falling back to description."""
    sku = "" if line.get("sku") is None else str(line.get("sku")).strip()
    description = _normalized_text(line.get("description")) or ""
    return sku, description


def _match_line_items(
    expected_lines: List[Dict[str, Any]],
    actual_lines: List[Dict[str, Any]],
) -> Tuple[List[Tuple[int, Optional[int]]], int]:
    """Match expected lines to actual lines, preferring exact SKU matches."""
    unmatched_actual = set(range(len(actual_lines)))
    matches: List[Tuple[int, Optional[int]]] = []

    for expected_index, expected_line in enumerate(expected_lines):
        expected_sku = _line_key(expected_line)[0]
        actual_index: Optional[int] = None

        if expected_sku:
            for candidate_index in list(unmatched_actual):
                candidate_sku = _line_key(actual_lines[candidate_index])[0]
                if candidate_sku == expected_sku:
                    actual_index = candidate_index
                    break

        if actual_index is None:
            expected_description = _line_key(expected_line)[1]
            if expected_description:
                for candidate_index in list(unmatched_actual):
                    candidate_description = _line_key(actual_lines[candidate_index])[1]
                    if candidate_description == expected_description:
                        actual_index = candidate_index
                        break

        if actual_index is None and expected_index in unmatched_actual:
            actual_index = expected_index

        if actual_index is not None:
            unmatched_actual.discard(actual_index)

        matches.append((expected_index, actual_index))

    return matches, len(unmatched_actual)


def score_invoice(
    case_id: str,
    expected: Dict[str, Any],
    actual: Dict[str, Any],
    candidate_marked_clean: bool = True,
) -> InvoiceScore:
    """Compare one candidate extraction to approved ground truth.

    The function intentionally uses deterministic comparisons. LLMs can explain
    failures later, but they do not decide whether an invoice passed evaluation.
    """
    header_scores = _score_fields(
        expected,
        actual,
        HEADER_FIELDS,
        CRITICAL_HEADER_FIELDS,
    )

    expected_lines = list(expected.get("line_items") or [])
    actual_lines = list(actual.get("line_items") or [])
    line_matches, extra_line_count = _match_line_items(expected_lines, actual_lines)

    line_item_scores: List[LineItemScore] = []
    missing_line_count = 0
    for expected_index, actual_index in line_matches:
        expected_line = expected_lines[expected_index]
        actual_line = actual_lines[actual_index] if actual_index is not None else {}
        if actual_index is None:
            missing_line_count += 1

        line_item_scores.append(
            LineItemScore(
                expected_index=expected_index,
                actual_index=actual_index,
                sku=(
                    None
                    if expected_line.get("sku") is None
                    else str(expected_line.get("sku"))
                ),
                field_scores=_score_fields(
                    expected_line,
                    actual_line,
                    LINE_FIELDS,
                    CRITICAL_LINE_FIELDS,
                ),
            )
        )

    all_field_scores = list(header_scores)
    for line_item_score in line_item_scores:
        all_field_scores.extend(line_item_score.field_scores)

    critical_failure = any(
        score.critical and not score.matched for score in all_field_scores
    )
    has_structural_failure = missing_line_count > 0 or extra_line_count > 0
    straight_through_ready = not critical_failure and not has_structural_failure

    return InvoiceScore(
        case_id=case_id,
        header_scores=header_scores,
        line_item_scores=line_item_scores,
        missing_line_count=missing_line_count,
        extra_line_count=extra_line_count,
        straight_through_ready=straight_through_ready,
        dangerous_false_clean=(
            candidate_marked_clean
            and not straight_through_ready
            and (critical_failure or has_structural_failure)
        ),
    )
