"""Data models for repeatable invoice extraction evaluations."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EvalCase:
    """One source invoice and its approved ground-truth result."""

    case_id: str
    source_path: Path
    expected_path: Path
    metadata_path: Optional[Path] = None


@dataclass
class FieldScore:
    """Comparison result for one invoice field."""

    field_name: str
    expected: Any
    actual: Any
    matched: bool
    critical: bool = False


@dataclass
class LineItemScore:
    """Comparison result for one expected line item."""

    expected_index: int
    actual_index: Optional[int]
    sku: Optional[str]
    field_scores: List[FieldScore] = field(default_factory=list)

    @property
    def matched(self) -> bool:
        """Return True when all compared line-item fields matched."""
        return bool(self.field_scores) and all(
            field_score.matched for field_score in self.field_scores
        )


@dataclass
class InvoiceScore:
    """Deterministic score for one candidate invoice extraction."""

    case_id: str
    header_scores: List[FieldScore] = field(default_factory=list)
    line_item_scores: List[LineItemScore] = field(default_factory=list)
    missing_line_count: int = 0
    extra_line_count: int = 0
    straight_through_ready: bool = False
    dangerous_false_clean: bool = False

    def metric(self, field_name: str) -> Optional[float]:
        """Return match rate for a named field across header and line items."""
        comparisons: List[FieldScore] = [
            score for score in self.header_scores
            if score.field_name == field_name
        ]
        for line_item_score in self.line_item_scores:
            comparisons.extend(
                score for score in line_item_score.field_scores
                if score.field_name == field_name
            )

        if not comparisons:
            return None
        return sum(score.matched for score in comparisons) / len(comparisons)


@dataclass
class EvalResult:
    """Summary for a complete evaluation run."""

    pipeline_name: str
    scores: List[InvoiceScore]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def clean_pass_rate(self) -> float:
        """Return share of invoices safe for straight-through processing."""
        if not self.scores:
            return 0.0
        ready_count = sum(score.straight_through_ready for score in self.scores)
        return ready_count / len(self.scores)

    @property
    def false_clean_rate(self) -> float:
        """Return share of invoices incorrectly treated as clean."""
        if not self.scores:
            return 0.0
        false_clean_count = sum(score.dangerous_false_clean for score in self.scores)
        return false_clean_count / len(self.scores)
