# totals.py — exact decimal aggregation

**Bead:** p4-gij · **Files owned:** `totals.py`, `reports/aggregate.md`

## Result

`python3 scripts/check_parts.py aggregate` — **passed**, exit code 0, 6/6 tests
in `tests_parts/test_totals.py`, `unchanged_during_test: true`. Machine-readable
record: `reports/aggregate-tests.json`.

## Contract implemented

`aggregate(records) -> {"rows": N, "invalid_rows": M, "totals": {category: "d.dd"}}`,
consuming the `(category, amount_text)` pairs and `None` values that
`records.parse_records` produces. No import of `records.py` or `summary.py`, so
the module tests independently.

## Choices

- **Validation split.** `None` (a record the parsing stage already rejected) and
  any amount Decimal cannot read count as `invalid_rows`. `NaN`, `sNaN`,
  `Infinity` and `-Infinity` *do* construct as Decimals, so finiteness is checked
  explicitly with `is_finite()` rather than relying on a parse failure. Decimal
  signals `InvalidOperation`, a subclass of `ArithmeticError`; `TypeError` and
  `ValueError` are caught alongside it so a non-string amount is data, not a crash.
- **Exact sums, one rounding.** Decimal *arithmetic* obeys the active context, so
  the default 28-digit precision would silently round a long running total. All
  additions run inside a `localcontext()` whose precision is derived from the
  inputs: the largest magnitude present, plus the digits `len(records)` of carry
  can add, down to the smallest exponent present or the cents place, whichever is
  lower. Each category is then quantized once, `ROUND_HALF_UP`, to two places.
  Decimal *construction* from a string is context-free and already exact.
  Verified: `["1" + "0"*29, "0.01"]` totals `100000000000000000000000000000.01`,
  where a default-context sum yields `1.000000000000000000000000000E+29`. The
  ambient context is left untouched for the caller.
- **HALF_UP is away from zero**, which is what the contract wants: `1.005` → `1.01`
  and `-1.005` → `-1.01`.
- **Categories are kept verbatim** — case-sensitive, used as dict keys in order of
  first appearance. A category with no valid amount never enters `totals`.
- **Never `-0.00`.** A total that rounds to zero from a negative sum (e.g. a lone
  `-0.001`, or an amount written `-0`) prints as `0.00`. Decimal's own output would
  be `-0.00`, which reads as a defect on a money report; both satisfy the "exactly
  two places" rule. Exact cancellation (`1.5 + -1.5`) already yields `0.00`.

## Assumptions worth flagging

- **Decimal's grammar is the amount grammar**, per the brief's "parse amounts with
  Decimal". That grammar also accepts exponent notation (`1E+3` → `1000.00`),
  underscores (`1_000`) and surrounding whitespace. Whitespace is harmless — the
  parsing stage trims first — but `1_000` is accepted as a number rather than
  rejected. Rejecting it would mean inventing a numeric grammar the contract does
  not specify.
- **Bounded inputs**, as the brief states. Amounts near Decimal's default exponent
  limits (|exponent| ≳ 999999) would raise `Overflow` from the summation rather
  than being counted invalid, and the precision needed to hold them exactly is
  itself unbounded. No limit is imposed here because any cutoff would be invented.
