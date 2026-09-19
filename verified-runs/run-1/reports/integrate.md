# summary.py — integration (bead p4-a15, integrate.iteration.1)

## Result

`python3 scripts/check_parts.py all` — **passed on the first attempt**, exit code 0.

```
tests_parts:  Ran 12 tests ... OK      (test_records 6 + test_totals 6)
tests:        Ran 12 tests ... OK      (test_summary 12)
```

`"unchanged_during_test": true` for all three modules. Machine-readable record:
`reports/controller-tests.json` is the controller's; this run wrote
`reports/all-tests.json`.

**No contract mismatch surfaced, so neither prerequisite module was modified.**
The task permitted fixing `records.py` or `totals.py` if integration exposed a
gap; nothing required it, and changing working modules without a failure to
justify it would only risk the other worker's verified result.

## The handoff

`summarize` is a one-line composition — `aggregate(parse_records(text))` — and
deliberately adds no rules of its own. That is the whole point of the split: each
rule in BRIEF.md lives in exactly one module, so there is no third place for the
two to disagree.

- **`records.py` owns shape.** Header validation (missing or duplicate columns),
  quoting, BOM, CRLF, trimming, empty lines, and missing/extra fields. It emits a
  `(category, amount_text)` pair per nonempty data row, or `None`.
- **`totals.py` owns numbers.** Which amount texts are finite Decimals, exact
  accumulation, and one HALF_UP rounding to two places per category.
- **Neither imports the other**, so both were testable independently while we
  worked in parallel, and `summary.py` is the only module that knows both exist.

The seam held because the two ends agreed on the one thing that crosses it: a
row that is structurally bad becomes `None` and a row that is structurally fine
but numerically junk becomes a pair with unvalidated text. `("x", "abc")` and
`("x", "NaN")` cross the boundary as *data*, and `totals.py` rejects them. Both
sides count as `invalid_rows` and the arithmetic stays in one place. Confirmed by
`test_invalid_records`: 4 rows rejected for shape, 4 for numerics, one valid — the
expected `{"rows": 1, "invalid_rows": 8}` requires both halves to agree on what
counts as a record.

`ValueError` propagates through the composition untouched, which the fixed tests
require of `summarize` for empty input, missing `category` or `amount`, duplicate
headers, and malformed quoting.

## Verification beyond the fixed tests

One bounded cross-module probe, to check the seam rather than either side:

```
'﻿note,amount,category\r\nok, 1.005 ,"food, drink"\r\n\r\nok,1.005,"food, drink"\r\nbad,,x\r\n'
  -> {'rows': 2, 'invalid_rows': 1, 'totals': {'food, drink': '2.01'}}
```

This exercises BOM, CRLF, a quoted comma, an extra column, **reordered headers**
(`category` last — resolved by name, not position), a blank line, whitespace
trimming, and a blank-amount rejection in one input. The total is the informative
part: `2.01`, not `2.02`. Rounding per row would have given `1.01 + 1.01`; the
exact sum `2.010` rounded once gives `2.01`, so round-once-per-category survives
composition. `ValueError` was also confirmed to reach the caller through
`summarize` for all three header/quoting failure classes.

## Notes for the controller

- Both prerequisite reports flag assumptions that integration does not change:
  Decimal's grammar also accepts exponent notation and underscores (`1_000`), and
  inputs near Decimal's exponent limits are out of scope per the brief's
  "bounded inputs". Tightening either would mean inventing a grammar or a cutoff
  the contract does not specify.
- `totals.py` normalizes a negative sum that rounds to zero as `0.00` rather than
  `-0.00`. Both satisfy "exactly two places"; no fixed test pins it.
- Tests, scripts, formulas, configuration and BRIEF.md are unchanged. Files
  written this iteration: `summary.py` and `reports/integrate.md`.
