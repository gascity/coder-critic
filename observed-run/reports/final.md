# Final verification of `summary.py`

- **Code verified:** `summary.py` — SHA-256
  `1d32b350eb9ca9e9c54e0530ccb413d6aefed3c56ef1f8490d64fe23306cc78d`
- **Baseline compared against:** `reports/first-summary.py` — SHA-256
  `205ce8dfaa73ec6794a6b79d6ac4ac166fea5d7f272191881452421826b4155e`
- **Verified by:** verifier-1 (bead `ci-wjd`)
- **Runtime:** CPython 3.14.7 · `csv.field_size_limit()` = 131072 · decimal default
  prec 28, Emax 999999, Emin -999999
- **Test record:** `reports/final-tests.json`
- **Method:** ran `scripts/check.py`, compared the four recorded runs, read
  `reports/review.md` and `reports/revision.md`, then re-executed the load-bearing
  claims of both against the two versions side by side. No code, test, script or
  other bead's report was modified. The baseline suite was re-run from a scratchpad
  copy, not by restoring `summary.py`.

## Verdict

**The final artifact passes.** `python3 scripts/check.py --record reports/final-tests.json`
reports 12/12 tests passing, `exit_code` 0, `unchanged_during_test` true.

**The first and final hashes differ, but the original already passed all 12 tests.**
No test failure was fixed, because there was none to fix. The suite passed at
`205ce8df` and passes at `1d32b350`, so it provides no evidence of a quality
improvement in either direction, and this report does not claim one. What the
revision did is change behaviour on inputs the brief does not describe and the tests
do not reach. Those changes are real and I reproduced every one of them; whether they
are improvements is a judgment the brief does not settle.

## The recorded runs

| Record | Code SHA-256 | Exit | Result |
| --- | --- | --- | --- |
| `before-implementation.json` | `None` (no file) | 1 | `ModuleNotFoundError: No module named 'summary'` — 1 error |
| `first-tests.json` | `205ce8df…` | 0 | **12/12 OK** |
| `revision-tests.json` | `1d32b350…` | 0 | 12/12 OK |
| `controller-check.json` | `1d32b350…` | 0 | 12/12 OK |
| `final-tests.json` (this bead) | `1d32b350…` | 0 | 12/12 OK |

All five records report `unchanged_during_test: true`, so each run tested the bytes
it names. The chain is intact: `reports/first-summary.py` still hashes to
`205ce8df…`, which is the SHA named by `implementation.md`, `review.md`,
`first-tests.json` and the "before" line of `revision.md` — five artifacts agreeing
on one set of bytes.

**The baseline's pass was independently re-confirmed, not taken from the record.** I
copied `reports/first-summary.py` and `tests/test_summary.py` into a scratchpad
directory and ran `python3 -m unittest discover -s tests` there: `Ran 12 tests … OK`.
The city's `summary.py` was never replaced to do this.

## What actually changed between the hashes

`diff reports/first-summary.py summary.py`: three behavioural edits and one cosmetic
one, all in `_records` and `_amount`. `_total`'s arithmetic is untouched (two comment
lines added), and `summarize`'s structure is unchanged apart from its docstring.

I loaded both versions into one process and called them on the same 24 inputs — the
brief's specified behaviours plus the inputs the review and revision are about.
**6 of 24 differ. All 6 are outside what the brief specifies; all 18 brief-specified
behaviours are byte-identical between the two versions.**

| Input | Baseline `205ce8df` | Final `1d32b350` |
| --- | --- | --- |
| Field over `field_size_limit()` | `_csv.Error` | `ValueError: malformed CSV input: …` |
| Unterminated quote in a >128 KB file | `_csv.Error` | `ValueError: malformed CSV input: …` |
| `１` (U+FF11 fullwidth one) | valid, summed as 1 | invalid record |
| `٤` (U+0664 arabic-indic four) | valid, summed as 4 | invalid record |
| `1E+100001` | valid, summed | invalid record |
| `1E-100001` | valid, summed | invalid record |
| *18 others* — trimming, case sensitivity, HALF_UP after the sum, negative-zero, quoted comma, BOM+CRLF, header-only, empty input, duplicate headers, missing column, reordered/extra columns, short row, blank category, `1_0`, ` 1.50 `, `1e2`, `NaN`, `Infinity` | — | **identical** |

So the revision preserved every behaviour the brief and the tests pin down, and its
changes land entirely in the undescribed margin.

## Claims checked against the code

**F1 — `_csv.Error` escaping `summarize()`: confirmed on the baseline, fixed in the
final.** Both the deliberate oversized cell and the critic's realistic trigger (one
stray `"` in a large export) raise `_csv.Error` — not a `ValueError` — from the
baseline, and `ValueError("malformed CSV input: field larger than field limit
(131072)")` from the final. The reasoning that the record cannot honestly be skipped
holds: `csv.reader` loses its position once it raises, so counting it in
`invalid_rows` would be a fabricated recovery. Converting the type is the truthful
fix, and the docstring was updated to match.

**F2 — inconsistent amount leniency: confirmed, fixed.** The baseline counted `1_0`
invalid while summing `１` and `٤` as ordinary numbers. The `_NUMBER` grammar now
rejects all three together. The `[0-9]`-not-`\d` warning is real and was heeded — I
checked the compiled pattern; `\d` would have re-admitted the fullwidth digits.

**F3 — unbounded precision: mechanism confirmed, consequence still unverified.** I
re-derived the baseline's precision request with integer arithmetic on the parsed
exponent, materialising nothing: for `1E+999999999`, `low` = -2 (clamped by `_CENTS`),
`high` = 999999999, so `ctx.prec` = **1000000006** — below `MAX_PREC`
(999999999999999999) and therefore accepted as a context precision. That is exactly
the figure the review reported. The band's upper edge is where both reports put it:
`Decimal('1E+9999999999999999999')` raises `InvalidOperation` in the constructor. The
final rejects `1E+999999999` at `_amount`, so the path is closed.

The review's further claim — that this "drives GB-scale allocation" — **remains
unverified.** The reviser declined to test it and said so; I also did not test it, for
the same reason, and I am not asserting it either way. What I did observe is narrower:
`_total([Decimal('1E+1000000')])` raises `decimal.Overflow` and returns promptly. That
is one order of magnitude up from the ceiling, not the billion-digit case the review
describes, so it does not settle the question — it only confirms the reviser's
calibration (see below).

**The `_MAX_ADJUSTED = 10 ** 5` derivation: confirmed.** The reviser says `10 ** 6`
was tried first and admitted a value that then overflowed inside `_total`, because the
ceiling sat above the context's default `Emax` of 999999. Reproduced exactly:
`_total([Decimal('1E+1000000')])` → `decimal.Overflow`. At the chosen ceiling the
stated safety properties hold: 100 records of `9E+100000` sum with carries and no
overflow, and `1E+100000` cancelling `-1E+100000` alongside two `0.005` still yields
`0.01`, so the widest accepted spread still rounds correctly.

**The cosmetic fix: confirmed.** `summary.py` is now pure ASCII — `_BOM = chr(0xFEFF)`
— and BOM stripping still works (`﻿category,amount\r\nfood,1.50\r\n` → 1 row).

**The revision's honesty about its own limits: confirmed, including one I could
reproduce.** `_total` does inherit the caller's decimal context, and the exposure is
not hypothetical: under `ctx.Emax = 100`, `summarize` on two `9E+100` records raises
`decimal.Overflow`, which escapes as an exception outside the documented failure model
— the same class of problem as F1, in both versions. The revision left it alone and
listed it; that is the correct call for this bead's scope, and the report's
description of it is accurate.

## Scope and integrity

`tests/test_summary.py` (SHA-256 `6a92781b…`) and `scripts/check.py` (SHA-256
`520537a5…`) both still carry their 17:08 setup mtimes, as does `scripts/verify.sh`
and `BRIEF.md`; only `summary.py` (17:50) and the reports have later timestamps. This
bead wrote `reports/final-tests.json` and this file, and nothing else.

## Limitations

These bound what the pass above actually demonstrates.

1. **The suite cannot show an improvement, and does not.** It passed before and after.
   Reading the 12 tests, none contains a non-ASCII digit, an oversized field or a
   large exponent, so **no test reaches any line the revision changed.** The two
   versions are indistinguishable to this suite. Any claim that the code got better
   rests on the review's and revision's reasoning, not on test evidence — and none was
   added, because adding tests was out of scope for every bead here.
2. **The magnitude ceiling is a policy choice that changed behaviour.** `1E+100001`
   was summed by the baseline and is counted invalid by the final. The brief sets no
   range for amounts, so nothing in the specification or the tests says which is
   right. It is documented in the source, which is the most that could be asked here,
   but it is a change, not a correction.
3. **`1.` and `1e2` are accepted** by `_NUMBER`, deliberately and documented. The
   brief neither requires nor forbids exponent notation; this too is undecided rather
   than verified.
4. **The review's GB-allocation claim is unverified at the end of the chain.** The
   critic inferred it, the reviser corrected the assertion and did not test it, and I
   did not test it. It is now unreachable through `summarize`, so it no longer affects
   results — but it was never answered.
5. **A caller-narrowed decimal context still breaks the documented failure model** in
   both versions (repro above). Known, unfixed, out of scope.
6. **Integrity of tests and scripts is argued, not proved.** No baseline hash of
   `tests/test_summary.py` or `scripts/check.py` was recorded at setup, so the
   evidence is unchanged mtimes plus the hashes recorded here for future runs, not a
   cryptographic before/after.
7. **This verification is bounded.** 12 fixed tests plus 24 hand-built comparison
   inputs, on one CPython build with default `decimal` settings. That is enough to
   confirm the specific claims in `review.md` and `revision.md`; it is not a proof of
   correctness, and `summary.py` is not a hardened CSV parser.

## Conclusion

Final verification succeeds: 12/12 tests pass against
`1d32b350eb9ca9e9c54e0530ccb413d6aefed3c56ef1f8490d64fe23306cc78d`, recorded in
`reports/final-tests.json`. The code changed between the first and final hashes; the
review's three findings and its minor note all reproduced on the baseline and are all
addressed in the final, with brief-specified behaviour preserved exactly. The original
passed the suite too, so the change is a behaviour change in undescribed territory
rather than a demonstrated quality improvement, and the chain's one unverified claim
stayed unverified and labelled as such at every step.
