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

The baseline implementation, review, test run, revision and final verification
are separate work items. Reports must identify the SHA-256 of summary.py they
examined. Keep tests and checking scripts unchanged. Work only in this demo city.
No publishing, network research, installation, or commits are needed.
