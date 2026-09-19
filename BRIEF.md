# CSV expense summary

Implement `summary.py` using only the Python standard library. Export
`summarize(text: str) -> dict`. Input is CSV with required headers `category,amount`
(extra columns are allowed). Return `{"rows": N, "invalid_rows": M, "totals": {...}}`.

- Count valid data records in rows; invalid records in invalid_rows.
- Trim category and amount. Blank category/amount, missing/extra fields, invalid
  numbers, NaN and Infinity are invalid records; skip them and continue.
- Parse amounts with Decimal. Sum exactly; output totals as decimal strings with
  exactly two places, rounded HALF_UP at the end of each category's sum.
- Negative amounts and zero are valid. Categories are case-sensitive.
- Support quoted commas, CRLF and a UTF-8 BOM. Ignore completely empty lines.
- Empty input or headers missing category/amount raise ValueError.
- Duplicate column headers raise ValueError.
- Header-only input returns zero counts and empty totals.

## Shared module contracts

Two coding workers implement these modules independently. The interfaces are
fixed before either starts so their work can proceed in parallel.

- `records.py`: `parse_records(text: str) -> list[tuple[str, str] | None]`.
  Validate headers and CSV syntax; raise ValueError for bad headers or malformed
  quoting. Strip the BOM and field whitespace. Every nonempty data row becomes
  either a `(category, amount_text)` pair or `None` for a missing/extra field or
  blank required value. Ignore completely empty lines. Leave numeric validation
  to the other module. Extra declared columns are allowed.
- `totals.py`: `aggregate(records) -> dict`. Consume those pairs/None values.
  Count None and invalid/nonfinite Decimal amounts as invalid_rows. Accumulate
  exact totals and round once per category, HALF_UP to two places. This module
  has no dependency on records.py and can be tested independently.
- `summary.py`: `summarize(text)` composes the two functions, preserving the
  public API above. Its task starts only after both module beads close.

Use standard-library tools and bounded inputs. The fixed tests are the acceptance
contract, not a production-security certification. Reports go in reports/parse.md,
reports/aggregate.md and reports/integrate.md. Keep tests, scripts and this brief
unchanged. Each task may edit only its assigned module until integration, when
both prerequisite workers have finished. No installation, publishing or commits.
