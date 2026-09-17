# First implementation of `summary.py`

- **Code under review:** `summary.py` (95 lines, standard library only)
- **SHA-256:** `205ce8dfaa73ec6794a6b79d6ac4ac166fea5d7f272191881452421826b4155e`
- **Snapshot:** `reports/first-summary.py` (byte-identical copy, same SHA-256)
- **Written by:** coder-1 (bead `ci-rn7`)

## Design choices

**Reading.** `csv.reader` over `io.StringIO(text, newline="")` rather than
`DictReader`. `newline=""` leaves line endings untranslated, so the csv module
itself handles CRLF, bare CR and newlines inside quoted fields. `DictReader` was
rejected because it silently pads short records with `None` and folds extra
fields into `restkey`, which would hide exactly the malformed records the brief
asks to count. A leading UTF-8 BOM is stripped once, before parsing, so it never
becomes part of the first header name. `csv` yields `[]` for a completely empty
line; those are dropped everywhere, including ahead of the header row.

**Header validation.** Header names are trimmed, then checked for duplicates
(`len(set(header)) != len(header)`) before the required-column check. Duplicates
are rejected for *any* repeated name, not just `category`/`amount`, matching
"Duplicate column headers raise ValueError" literally. Column positions come
from `header.index(...)`, so extra columns and reordered columns both work.
Header matching is exact and case-sensitive: the brief names the required
headers as `category,amount` and never asks for case folding, and folding would
make duplicate detection ambiguous (`Category,category`). Empty input — and
input with no non-empty line — raises `ValueError("input has no header row")`.

**Record validity.** A record is invalid when its field count differs from the
header's (missing *or* extra fields), when the trimmed category is blank, or
when the trimmed amount is not a finite number. Invalid records are counted and
skipped; parsing continues. Valid records are counted in `rows`.

**Amount parsing.** `Decimal(raw)` after trimming, then `value.is_finite()`,
which rejects `NaN`, `Infinity` and `-Infinity` — these parse successfully, so a
`try/except` alone would let them through. Strings containing `_` are rejected
before parsing: `Decimal("1_0")` is `10` because of Python's literal
underscore-grouping rule, which is not a property CSV data should inherit.
Exponent notation (`1e2`) and a leading `+` are accepted as ordinary decimal
literals. Negative amounts and zero are valid.

**Exact summation.** Amounts are collected per category and summed inside a
`localcontext()` whose precision is widened to `high - low + len(str(n)) + 4`,
where `high` is the largest `adjusted()` exponent, `low` the smallest input
exponent (floored at `-2`, the cents place) and `n` the number of values. This
is enough digits for every input digit, the carries from adding `n` of them, and
the two places rounded to, so no intermediate addition rounds. Rounding happens
once, at the end of each category's sum, via
`quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`.

The default 28-digit context is not sufficient and was measured failing: for
`9...9.995` (40 nines) plus `0.005`, it yields `1.000000000000000000000000000E+40`
and then raises `InvalidOperation` on `quantize`. The widened context returns
`10000000000000000000000000000000000000000.00`.

**Output.** Totals are decimal strings with exactly two places. A total of
exactly zero is emitted as `0.00`, never `-0.00`, via `copy_abs()` on a zero
result — an input of `-0` would otherwise carry the sign through `quantize`.
Category keys keep first-seen order (`dict` insertion order), which is
deterministic and mirrors the input.

## Evidence

Fixed suite, unmodified, run from the city root
(`python3 -m unittest discover -s tests -v`) — `scripts/` and `tests/` were not
touched, and `scripts/check.py` was not run so its report files stay free for
the tester's bead:

```
test_bad_headers (test_summary.SummaryTests.test_bad_headers) ... ok
test_basic (test_summary.SummaryTests.test_basic) ... ok
test_bom_crlf (test_summary.SummaryTests.test_bom_crlf) ... ok
test_exact_decimal (test_summary.SummaryTests.test_exact_decimal) ... ok
test_extra_columns (test_summary.SummaryTests.test_extra_columns) ... ok
test_half_up (test_summary.SummaryTests.test_half_up) ... ok
test_header_only (test_summary.SummaryTests.test_header_only) ... ok
test_invalid_records (test_summary.SummaryTests.test_invalid_records) ... ok
test_negative_zero (test_summary.SummaryTests.test_negative_zero) ... ok
test_quoted_comma (test_summary.SummaryTests.test_quoted_comma) ... ok
test_round_after_sum (test_summary.SummaryTests.test_round_after_sum) ... ok
test_trim_and_case (test_summary.SummaryTests.test_trim_and_case) ... ok

Ran 12 tests in 0.000s

OK
```

Ad-hoc checks beyond the fixed suite (observed output, run against this SHA):

| Input | Result |
| --- | --- |
| `x,-0` | `0.00` (no negative zero) |
| `x,-1.5` + `x,1.5` | `0.00` |
| `x,1_0` | invalid record |
| `x,1e2` | `100.00` |
| bare-CR line endings | 2 rows, `3.00` |
| blank lines before the header | header found, 1 row |
| whitespace-only data line | 1 invalid (not "completely empty") |
| newline inside a quoted field | kept in the category key |
| `x,1,` with a 2-column header | invalid (extra field) |
| no trailing newline | 1 row |
| `note,amount,category` header | columns resolved by name |
| 300 values near ±10^30 | matches an independent exact integer/HALF_UP computation |

## Known judgment calls for the critic

1. Case-sensitive, exact header names (`Category,Amount` raises `ValueError`).
2. A whitespace-only line is an invalid record, not an ignorable empty line.
3. `_` in an amount is rejected; exponent notation is accepted.
4. Duplicate detection covers every repeated header name, including blanks.
5. Zero totals are normalized to `0.00`.
