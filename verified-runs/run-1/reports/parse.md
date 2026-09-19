# records.py — CSV record parsing (bead p4-bub)

## Deliverable

`records.py` exporting `parse_records(text: str) -> list[tuple[str, str] | None]`,
per the shared contract in BRIEF.md. No other module was touched; `totals.py` and
`summary.py` belong to the other worker and the integration task.

## Decisions

- **`csv` with `strict=True`.** The only quoting case the tests demand is an
  unterminated quote (`'category,amount\n"unclosed,1\n'`). I probed the stdlib
  first: the default reader silently swallows it into a single field
  `['unclosed,1\n']`, which would have been misreported as a missing-field `None`
  instead of an error. `strict=True` raises `csv.Error: unexpected end of data`,
  and also catches text after a closing quote (`"a"b`). That removed the need for
  a hand-rolled quote state machine.
- **`csv.Error` → `ValueError`.** `csv.Error` derives from `Exception`, not
  `ValueError`, so `_read_rows` catches and re-raises it as a `ValueError` with
  the original chained — the contract specifies `ValueError` for malformed quoting.
- **`io.StringIO(text, newline="")`.** Feeding the whole text (rather than
  `splitlines()`) keeps CRLF and newlines inside quoted fields intact for csv to
  interpret, which is what the CRLF and quoted-comma cases require.
- **BOM.** Stripped once, only as a leading prefix, before parsing — not
  `lstrip`, which would eat a repeated BOM and is not what "strip the BOM" means.
- **Header resolution by position, not by fixed index.** `category` and `amount`
  are located via `header.index`, so extra declared columns (`category,amount,note`)
  and any column order both work. Header names are trimmed before matching.
- **Duplicate headers.** Checked across *all* columns, not just the two required
  ones, matching "Duplicate column headers raise ValueError".
- **Row shape vs. row content.** `len(row) != len(header)` is the missing/extra
  field test, so a short or long row yields `None`. After that, a blank trimmed
  category or amount yields `None`. Everything else becomes a pair — `("x", "abc")`
  included. Numeric validity, NaN/Infinity and rounding are deliberately left to
  `totals.py`, per the contract.
- **Empty lines.** Only rows csv reports as `[]` are skipped, and they are skipped
  before the header too, so leading blank lines do not become a bogus header. A
  line of spaces is *not* "completely empty"; it parses as a one-field row and is
  correctly `None`.
- **No header at all → `ValueError`.** Empty input produces zero rows, so the
  `header is None` check after the loop covers `""` without a special case.

## Test result (actual)

`python3 scripts/check_parts.py parse` — **passed**, exit code 0.

```
Ran 6 tests in 0.008s

OK
```

All six `tests_parts/test_records.py` cases pass: `test_basic`,
`test_quoting_and_bom`, `test_invalid_rows_and_empty_lines`, `test_headers`,
`test_malformed_quoting`, `test_header_only`. The run also recorded
`"unchanged_during_test": true` for `records.py`. Full machine-readable output is
in `reports/parse-tests.json` (written by the check script).

Tests, scripts, formulas, configuration and BRIEF.md are unchanged.
