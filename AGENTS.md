# AGENTS.md

## Repository purpose

This repository processes supplier invoices, supports human review and validation, and posts approved receiving data to Stellar POS.

## Development rules

- Use Python 3.10 or later.
- Follow PEP 8.
- Add type hints and docstrings to new Python functions.
- Preserve existing public API behaviour unless the task explicitly changes it.
- Use structured logging.
- Never log credentials, API keys, authorization headers, invoice files, or full external API responses that may contain sensitive information.
- Never commit `.env` files, real invoices, supplier lists, location lists, API credentials, or UAT response dumps.
- Configure all external integrations through environment variables.
- Keep UAT and production configuration separate.
- Use dependency injection or mockable HTTP transports for external API clients.
- Add tests for success, validation failure, authentication failure, timeout, malformed response, and duplicate-post behaviour.
- Do not send requests to Stellar during the automated test suite.
- Do not change the Ursus Major repository as part of work in this repository unless the task explicitly requires it.

## Invoice workflow rules

- Human approval is required before posting an invoice to Stellar.
- Preserve the original invoice and extracted data for audit purposes.
- Store posting status, timestamps, sanitized external responses, and external references when available.
- Block duplicate successful posting of the same invoice.
- Make retry behaviour explicit and safe.
- Keep extraction, validation, workbook generation, and external posting as separate services.

## Stellar integration rules

- UAT and production endpoints must be independently configurable.
- Never hard-code Stellar credentials, tenant identifiers, supplier IDs, or location IDs.
- Supplier and location display names must never be sent in place of their Stellar IDs.
- Do not infer undocumented multipart field names or header names without clearly documenting the assumption.
- Keep the HTTP transport mockable and normalize external responses before returning them to application code.
- Use domain-specific exceptions for configuration errors, validation errors, authentication failures, timeouts, connection errors, and unexpected responses.
- Never include secret values in logs, exceptions, test snapshots, or user-facing messages.

## Stellar import workbook rules

The generated workbook must contain exactly these columns, in this order:

1. `SKU`
2. `Receiving Qty (UOM)`
3. `Confirmed total Cost`

Additional rules:

- Treat SKU as a string and preserve leading zeroes.
- Quantity must be numeric and greater than zero.
- `Confirmed total Cost` means the full invoice-line cost, not unit cost.
- Cost must be numeric and non-negative.
- Do not add an index column.
- Generate the workbook in memory unless a task explicitly requires a file on disk.
- Do not commit generated workbooks.

## Reference-data rules

- Store-to-Stellar location mappings must be explicit.
- Vendor-to-Stellar supplier mappings must be explicit and reviewable.
- Do not assume store or supplier matches based only on similar names.
- Local reference files should be placed under `.local/stellar/` and excluded from Git.
- Application startup and automated tests must not depend on local reference files being present.

## Testing expectations

- Use mocked HTTP responses for Stellar tests.
- Test successful upload, configuration failure, validation failure, 401/403 authentication failure, 409 conflict, server failure, timeout, connection failure, non-JSON response, and malformed success response.
- Test exact workbook column names and order, SKU text preservation, leading zeroes, numeric validation, empty invoice rejection, and workbook readability.
- Clearly separate pre-existing failures from failures introduced by the current change.

## Change-management rules

- Keep changes narrowly scoped and reversible.
- Prefer small, reviewable pull requests over broad rewrites.
- Do not remove the legacy Stellar implementation until the replacement has been proven in UAT and the task explicitly authorizes removal.
- Do not trigger a real UAT or production request automatically.
- Require an explicit execution flag for any manual script that can create a record in Stellar.
- Before finishing, review the diff for secrets, internal identifiers, generated files, and unrelated changes.
