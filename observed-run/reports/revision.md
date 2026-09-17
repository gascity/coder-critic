# Revision of `summary.py`

- **Code before:** SHA-256 `205ce8dfaa73ec6794a6b79d6ac4ac166fea5d7f272191881452421826b4155e`
  (matches the SHA in `reports/review.md` and `reports/first-tests.json`, and
  `reports/first-summary.py` — all four agree, so review, tests and revision are
  about the same bytes)
- **Code after:** SHA-256 `1d32b350eb9ca9e9c54e0530ccb413d6aefed3c56ef1f8490d64fe23306cc78d`
- **Revised by:** reviser-1 (bead `ci-qo0`)
- **Runtime:** CPython 3.14.7 · `csv.field_size_limit()` = 131072 · decimal default
  prec 28, Emax 999999, Emin -999999
- **Tests:** `python3 scripts/check.py --record reports/revision-tests.json` —
  12/12 pass, `exit_code` 0, `unchanged_during_test` true.
- **Preserved / unchanged:** `reports/first-summary.py` still hashes to the baseline
  SHA. `tests/test_summary.py`, `scripts/check.py` and `scripts/verify.sh` were read
  but not modified.

## Summary

Three findings accepted and fixed, one minor note accepted, nothing rejected. The
baseline passed all 12 tests before and after, so none of this came from a test
failure — the tests do not reach any of these paths. All three findings are about
inputs the brief does not describe, and in each case the baseline's behaviour was
outside the two outcomes `summarize` documents.

One correction to the review is recorded under F3: the mechanism the critic
identified is real and I confirmed the arithmetic, but I did not confirm the
consequence they predicted, and I did not try to.

## Findings

### F1 — `_csv.Error` escaped `summarize()` — **accepted, fixed**

Reproduced on the baseline. A field over `csv.field_size_limit()` raised
`_csv.Error`, which is not a `ValueError`, from a function documenting exactly two
outcomes. I also reproduced the critic's realistic trigger: a single unterminated
quote in a ~160 KB file makes the parser sweep the rest of the file into one field
and hit the same limit.

**Fix.** `_records` now pulls from the reader explicitly and converts `csv.Error`
into `ValueError("malformed CSV input: ...")`. I took the critic's reasoning that
recovering is not honestly available — the reader's position is lost once it raises,
so the record cannot be skipped and counted the way a short row can. The message
prefix keeps it distinguishable from the three header-stage `ValueError`s.

After: both inputs raise `ValueError`, message `malformed CSV input: field larger
than field limit (131072)`.

### F2 — `_` rejected but non-ASCII digits accepted — **accepted, fixed**

Reproduced on the baseline: `１` (U+FF11) and `٤` (U+0664) were counted valid and
summed, while `1_0` was counted invalid — the same class of `Decimal` leniency
landing on opposite sides.

**Fix.** Replaced the ad-hoc `"_" in raw` test with one `fullmatch` against an
explicit ASCII grammar, written with `[0-9]` rather than `\d` exactly as the critic
warned, since `\d` matches fullwidth digits too and would have rebuilt the bug:

```python
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
```

One rule now covers underscores, non-ASCII digits, `Decimal`'s whitespace tolerance,
and the words `NaN`/`sNaN`/`Infinity`/`inf`. I kept exponent notation — the brief
neither requires nor forbids it, and the baseline accepted it, so keeping it is the
smaller behaviour change. That decision is recorded in the source comment.

After: `１`, `٤`, `1_0`, `NaN`, `sNaN`, `Infinity`, `-Infinity`, `inf`, `abc` and
blank all count invalid; `1.50`, `+1.005`, `.5`, `1.`, `1e2`, `-0` stay valid.

### F3 — `_total` precision sized from input magnitude with no ceiling — **accepted, fixed; one claim corrected**

The mechanism is confirmed. `_amount` accepted `Decimal("1E+999999999")` as finite,
and the precision expression evaluates to `1000000006`, which is below `MAX_PREC` and
so is accepted as a context precision. I verified that with integer arithmetic on the
parsed exponent, never materialising the number — the same method the critic used.
The upper end of the band is bounded as the critic said: `1E+9999999999999999999`
raises `InvalidOperation` in the constructor, so `_amount` returns `None` there.

**Correction.** The review states this "drives GB-scale allocation and a very long
computation instead of returning a total." I did not verify that, and I stopped
before doing so; the probe was out of proportion to this task. Reading the code, the
sum runs with the context's default `Emax` of 999999 and `Overflow` trapped, which
suggests the real outcome at that magnitude is a quick `decimal.Overflow` rather than
a large allocation — which would make F3 the same bug class as F1, an exception
outside the documented failure model, rather than a resource problem. **I am not
asserting that either**; it is unverified. What is verified is that the value is
accepted and the precision expression is unbounded, which is reason enough to fix it,
and the fix is the same under either reading.

**Fix.** A documented magnitude ceiling in `_amount`, per the critic's suggestion, so
out-of-range values count as invalid records and `_total` is left unchanged — the
brief's "skip it and continue" model rather than a new exception.

The ceiling is `_MAX_ADJUSTED = 10 ** 5`, and the value came from a measurement, not
from taste. I first set it to `10 ** 6` and observed that `1E+1000000` was then
accepted by `_amount` and raised `decimal.Overflow` inside `_total`, because the
ceiling sat above the context's default `Emax` of 999999. A ceiling has to leave room
for the carries of summing a whole column, not just for one value, so `10 ** 5` leaves
an order of magnitude at both ends.

Verified after the change, within that bounded range: `1E+100000`, `-1E+100000` and
`1E-100000` are valid and sum exactly; `1E+100001` and `1E-100001` count invalid;
100 records of `9E+100000` sum with carries and no `Overflow`; and `1E+100000`
cancelling `-1E+100000` alongside `0.005 + 0.005` still yields `0.01`, so the widest
accepted spread still rounds correctly.

### Minor note — invisible U+FEFF in the source — **accepted, fixed**

Confirmed: the baseline's `_BOM` line held a literal U+FEFF, the only non-ASCII
character in the file and invisible in any editor or diff.

Written now as `_BOM = chr(0xFEFF)`. I first tried a `"﻿"` escape twice and both
attempts landed wrong through my editing tools — once as a real U+FEFF again, once as
a doubled backslash that made `_BOM` a 6-character string and broke BOM stripping
outright. I caught the second by testing rather than by reading, `chr(0xFEFF)` avoids
escape handling altogether. The file is now pure ASCII and BOM stripping is verified
working.

## Rejected

None. All three findings and the minor note reproduced as described, apart from the
single unverified consequence corrected under F3.

## The review's "checked and found correct" list

Re-ran the behaviours the critic certified, to confirm the revision did not regress
anything it had cleared: trimming (spaces and tabs), case sensitivity, HALF_UP ties
in both directions, rounding once after the sum, negative-zero normalisation via
three routes, header-only with and without BOM/CRLF, quoted comma, quoted newline,
bare CR, missing trailing newline, blank lines around the header, whitespace-only
line counted invalid, reordered and extra columns, and `ValueError` for empty input,
`"\n\n\n"`, wrong-case headers, missing column and duplicate headers. All pass.

## Remaining limitations, honestly

Not fixed, and not in scope for this bead:

- **The ceiling is a policy choice, not a brief requirement.** The brief sets no range
  for amounts. `10 ** 5` is documented in the source, but a value past it is now
  counted invalid rather than summed — a real behaviour change from the baseline that
  no test covers either way.
- **`_total` still inherits the caller's decimal context.** The ceiling is safe against
  the *default* `Emax`/`Emin`. A caller who narrows the context before calling
  `summarize` could still push a large-magnitude sum into `decimal.Overflow`. The
  baseline had the same exposure; I did not change `_total`, per the review's advice.
- **Behaviour far past the ceiling is inferred, not measured** — see the F3 correction.
  Those inputs are now rejected at the boundary, so the question no longer affects
  results, but it is not a question I answered.
- **`1.` and `1e2` are accepted** as a deliberate, documented choice. If the team wants
  exponent notation rejected, drop the exponent group from `_NUMBER`.

This is a bounded revision against a 12-test suite and one review. It is not a
hardened CSV parser and should not be described as one.

## Scope

Only `summary.py` was modified. `reports/revision.md` and
`reports/revision-tests.json` were written by this bead. No test, script, city
configuration or other bead's report was touched, and nothing was published,
installed or committed.
