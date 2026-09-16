"""Command-line runner for invoice extraction evaluations."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

from .schemas import EvalCase, EvalResult
from .scorer import score_invoice

Extractor = Callable[[Path, Dict[str, Any]], Dict[str, Any]]


def discover_cases(dataset_dir: Path) -> List[EvalCase]:
    """Discover evaluation cases under a dataset directory."""
    cases: List[EvalCase] = []
    for case_dir in sorted(path for path in dataset_dir.iterdir() if path.is_dir()):
        source_candidates = [
            path for path in case_dir.iterdir()
            if path.name.startswith("source.")
        ]
        expected_path = case_dir / "expected.json"
        metadata_path = case_dir / "metadata.json"

        if not source_candidates or not expected_path.exists():
            continue

        cases.append(
            EvalCase(
                case_id=case_dir.name,
                source_path=sorted(source_candidates)[0],
                expected_path=expected_path,
                metadata_path=metadata_path if metadata_path.exists() else None,
            )
        )
    return cases


def load_json(path: Path) -> Dict[str, Any]:
    """Load a UTF-8 JSON object from disk."""
    with path.open("r", encoding="utf-8") as file_handle:
        data = json.load(file_handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def import_extractor(import_path: str) -> Extractor:
    """Import an extractor function using module:function syntax."""
    if ":" not in import_path:
        raise ValueError("Extractor must use module:function syntax")

    module_name, function_name = import_path.split(":", 1)
    module = importlib.import_module(module_name)
    extractor = getattr(module, function_name)
    if not callable(extractor):
        raise TypeError(f"Extractor {import_path} is not callable")
    return extractor


def run_eval(
    dataset_dir: Path,
    pipeline_name: str,
    extractor: Extractor,
) -> EvalResult:
    """Run one extractor against every discovered case in a dataset."""
    scores = []
    for case in discover_cases(dataset_dir):
        expected = load_json(case.expected_path)
        metadata = load_json(case.metadata_path) if case.metadata_path else {}
        actual = extractor(case.source_path, metadata)
        candidate_marked_clean = bool(actual.pop("_candidate_marked_clean", True))
        scores.append(
            score_invoice(
                case_id=case.case_id,
                expected=expected,
                actual=actual,
                candidate_marked_clean=candidate_marked_clean,
            )
        )

    return EvalResult(
        pipeline_name=pipeline_name,
        scores=scores,
        metadata={"dataset": str(dataset_dir)},
    )


def _mean_metric(result: EvalResult, metric_name: str) -> float:
    values = [
        value for value in (score.metric(metric_name) for score in result.scores)
        if value is not None
    ]
    if not values:
        return 0.0
    return sum(values) / len(values)


def summarize_result(result: EvalResult) -> Dict[str, Any]:
    """Convert an evaluation result into JSON-serializable metrics."""
    return {
        "pipeline": result.pipeline_name,
        "invoice_count": len(result.scores),
        "clean_pass_rate": result.clean_pass_rate,
        "false_clean_rate": result.false_clean_rate,
        "vendor_accuracy": _mean_metric(result, "vendor_name"),
        "invoice_number_accuracy": _mean_metric(result, "invoice_number"),
        "store_accuracy": _mean_metric(result, "store_id"),
        "sku_accuracy": _mean_metric(result, "sku"),
        "quantity_accuracy": _mean_metric(result, "quantity"),
        "line_cost_accuracy": _mean_metric(result, "amount"),
        "total_accuracy": _mean_metric(result, "total_amount"),
        "missing_lines": sum(score.missing_line_count for score in result.scores),
        "extra_lines": sum(score.extra_line_count for score in result.scores),
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Run the CLI."""
    parser = argparse.ArgumentParser(description="Run invoice extraction evaluations")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--pipeline", required=True)
    parser.add_argument(
        "--extractor",
        required=True,
        help="Python import path in module:function form",
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args(list(argv) if argv is not None else None)

    extractor = import_extractor(arguments.extractor)
    result = run_eval(arguments.dataset, arguments.pipeline, extractor)
    summary = summarize_result(result)
    payload = json.dumps(summary, indent=2, sort_keys=True)

    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
