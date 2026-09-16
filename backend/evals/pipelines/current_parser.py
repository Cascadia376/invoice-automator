"""Eval adapter for the repository's current invoice parser."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from services import parser


def extract(source_path: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Run the current production parser for one evaluation case.

    `metadata.json` must contain `org_id`. Optional `s3_key` and `s3_bucket`
    values allow the existing Textract branch to run for scanned documents.
    """
    org_id = metadata.get("org_id")
    if not org_id:
        raise ValueError("Current parser eval cases require metadata.org_id")

    results = parser.extract_invoice_data(
        str(source_path),
        org_id=str(org_id),
        s3_key=metadata.get("s3_key"),
        s3_bucket=metadata.get("s3_bucket"),
    )

    if not isinstance(results, list) or len(results) != 1:
        raise ValueError(
            "Current parser eval adapter expects exactly one invoice per source file"
        )

    result = results[0]
    if not isinstance(result, dict):
        raise ValueError("Current parser returned a non-object invoice result")

    return result
