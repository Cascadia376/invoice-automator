# Invoice extraction evaluations

This package provides deterministic evaluation of invoice extraction pipelines against approved ground truth.

## Dataset layout

Each evaluation case is a directory containing the source invoice and expected approved data:

```text
backend/evals/datasets/cascadia-v1/
  case-001/
    source.pdf
    expected.json
    metadata.json
```

`expected.json` should contain the approved values used for receiving. Preserve SKU values as strings, including leading zeroes.

Example:

```json
{
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
      "description": "Example Product",
      "quantity": 12,
      "units_per_case": 12,
      "unit_cost": 8.33,
      "amount": 99.96
    }
  ]
}
```

`metadata.json` is optional and can label useful cohorts without affecting ground truth:

```json
{
  "supplier_type": "wine",
  "document_type": "native_pdf",
  "pages": 2
}
```

Do not commit real supplier invoices or confidential supplier/reference data. Keep production evaluation datasets in approved private storage and materialize them only for controlled evaluation runs.

## Extractor contract

An evaluation extractor is any callable accepting:

```python
extractor(source_path: pathlib.Path, metadata: dict) -> dict
```

It must return the normalized invoice object to compare with `expected.json`.

An extractor may include the private key `_candidate_marked_clean` in its returned object. Set it to `false` when the pipeline correctly flagged the invoice for human review. The runner removes this key before field scoring.

## Run an evaluation

From `backend`:

```bash
python -m evals.runner \
  --dataset evals/datasets/cascadia-v1 \
  --pipeline current-parser \
  --extractor evals.pipelines.current_parser:extract
```

Optionally persist the summary:

```bash
python -m evals.runner \
  --dataset evals/datasets/cascadia-v1 \
  --pipeline current-parser \
  --extractor evals.pipelines.current_parser:extract \
  --output eval-results/current-parser.json
```

## Primary metrics

The first release reports:

- clean pass rate
- false clean rate
- supplier accuracy
- invoice-number accuracy
- store accuracy
- SKU accuracy
- quantity accuracy
- line-cost accuracy
- invoice-total accuracy
- missing lines
- extra lines

`false_clean_rate` is the most important safety metric. A candidate pipeline that silently marks an incorrect invoice as clean should not replace the production pipeline, even if its average extraction accuracy is higher.

## Evaluation principle

Models may extract and explain. Deterministic code decides whether the candidate matched the approved result.
