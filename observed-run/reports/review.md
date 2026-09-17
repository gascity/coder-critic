# Independent review of the first `summary.py`

- **Code under review:** `summary.py`
- **SHA-256:** `205ce8dfaa73ec6794a6b79d6ac4ac166fea5d7f272191881452421826b4155e`
  (byte-identical to `reports/first-summary.py`, same digest — the snapshot is honest)
- **Reviewed by:** critic-1 (bead `ci-6g5`)
- **Runtime observed:** CPython 3.14.7 · `csv.field_size_limit()` = 131072 · `decimal` default prec 28, `MAX_PREC` 999999999999999999
- **Method:** read `BRIEF.md` and `summary.py`, derived expectations from the brief
  alone, then exercised `summarize()` against 38 hand-built inputs. Code, tests and
  scripts were not modified and `scripts/check.py` was not run (that is the tester's
  bead). Large-magnitude and memory-stress probes were deliberately not executed;
  finding 3 is reported from code inspection plus a small arithmetic repro.

## Verdict

The implementation is correct on every behaviour the brief actually specifies — I
could not break the counting, the trimming, the case-sensitivity, the BOM/CRLF/quoting
handling, the exact summation or the HALF_UP rounding. The precision-widening argument
in `_total` holds up under adversarial reading for realistic magnitudes, and the `-0.00`
normalisation and the `is_finite()` rejection of NaN/Infinity are both right and both
non-obvious. This is good work.

Three findings, all at the edge of the contract rather than inside it: one confirmed
exception that escapes the documented failure model, one confirmed inconsistency in
amount validation, and one resource concern. None require a redesign.

## Findings

### F1 — `_csv.Error` escapes `summarize()`, outside the documented failure model (confirmed)

`summarize()` documents exactly two outcomes for bad input: a `ValueError` for empty
input / missing / duplicate headers, and "count it in `invalid_rows` and continue" for
a malformed record. A third exists. A single field longer than `csv.field_size_limit()`
(131072 by default) aborts the entire call:

```python
big = 'x' * (csv.field_size_limit() + 1)
summarize('category,amount\n' + big + ',1.00\n')
# _csv.Error: field larger than field limit (131072)
# isinstance(err, ValueError) -> False
```

The realistic trigger is not a deliberately huge cell: an unterminated quote makes the
CSV parser accumulate the remainder of the file into one field, so any export over
~128 KB with one stray `"` reaches this limit. A caller that follows the docstring and
catches `ValueError` sees an unexpected exception type instead.

**Suggested revision.** Contain it at the iteration boundary in `_records` and re-raise
as `ValueError` with a message naming the cause. Recovering and continuing is not
honestly available — once the reader raises, its position in the input is lost — so
converting the exception type (and saying so in the docstring) is the truthful fix
rather than pretending the record can be skipped. Keep the header-stage `ValueError`s
distinguishable in the message.

### F2 — amount validation blocks `_` but allows non-ASCII digits (confirmed)

`_amount` special-cases `"_" in raw` on the stated principle that CSV data should not
inherit Python's numeric-literal leniency. `Decimal` is lenient in a second way that is
not blocked — it accepts any Unicode decimal digit:

```
category,amount
food,１          # U+FF11 FULLWIDTH DIGIT ONE
-> {'rows': 1, 'invalid_rows': 0, 'totals': {'food': '1.00'}}
```

Same class of leniency, opposite treatment. `１` is counted as a valid record and summed,
while `1_0` is counted invalid. Whichever rule is intended, both inputs should land on
the same side of it.

**Suggested revision.** Replace the ad-hoc `_` check with one explicit grammar check
before `Decimal(...)`, so the accepted form is reviewable in a single line:

```python
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
```

Use `[0-9]`, not `\d` — in `str` patterns `\d` matches fullwidth digits too and would
reproduce the same bug. One check then subsumes `_`, non-ASCII digits and `Decimal`'s
whitespace tolerance. The pattern above keeps exponent notation, which the brief neither
requires nor forbids; if the team would rather reject `1e2`, drop the exponent group and
record that decision in the docstring.

### F3 — `_total` sizes context precision from the input's own magnitude, with no ceiling (inspection)

`_amount` accepts any finite `Decimal`, and `_total` then derives precision from it:

```python
ctx.prec = max(ctx.prec, high - low + len(str(len(values))) + 4)
```

For a 13-character field `1E+999999999` — finite, so `_amount` returns it — that
expression evaluates to `1000000006`. That is *below* `MAX_PREC`, so it is accepted as a
context precision rather than rejected, and the following `quantize` to two places has
room to produce a result of roughly a billion digits, which `str()` then renders. One
short cell therefore drives GB-scale allocation and a very long computation instead of
returning a total.

Reported from inspection: I evaluated the same expression on the parsed exponent with
plain integer arithmetic and never materialised the number. Note the band is bounded on
one side already — `Decimal('1E+9999999999999999999')` raises `InvalidOperation` in the
constructor, so `_amount` correctly returns `None` there. The exposed range is the one
the constructor accepts.

**Suggested revision.** Add a magnitude ceiling in `_amount` — reject values whose
`adjusted()` exponent exceeds a documented bound and count the record invalid — which
keeps the brief's "skip it and continue" model and leaves `_total` unchanged. The brief
sets no range for amounts, so whatever bound is chosen belongs in the docstring.

## Checked and found correct

Observed against this SHA; each behaviour was predicted from the brief before running.

| Area | Inputs exercised | Result |
| --- | --- | --- |
| Counting | valid/short/long rows, blank category, blank amount | `rows` + `invalid_rows` = data records, every time |
| Trimming | spaces and tabs around category and amount | trimmed; `\t1.50\t` → `1.50` |
| Case sensitivity | `Food` vs `food` | kept as separate categories |
| Invalid numbers | `NaN`, `nan`, `sNaN`, `Infinity`, `-Infinity`, `inf`, `INF`, `1,50` | all counted invalid, parsing continued |
| Exact sum + HALF_UP | `1.005` + `1.005` → `2.01`; ties `0.005` → `0.01`, `-0.005` → `-0.01` | rounds once, at the end, away from zero |
| Negative zero | `-0` → `0.00`; `-0.001` → `0.00`; `-1.5` + `1.5` → `0.00` | never `-0.00` |
| Errors | `""`, `"\n\n\n"`, `Category,Amount`, `cat,amount`, duplicate and duplicate-blank headers | `ValueError` in all cases |
| Header-only | with and without CRLF, with BOM | `rows` 0, `invalid_rows` 0, `totals` `{}` |
| Quoting / endings | quoted comma, quoted newline, CRLF, bare CR, no trailing newline | all handled; quoted newline kept in the key |
| BOM | leading BOM stripped; BOM mid-header not stripped | correct — only a leading BOM is a BOM |
| Blank lines | before the header, between records | ignored, header still found |
| Columns | extra column, reordered `note,amount,category`, one trailing blank header | resolved by name |

The precision widening also survives adversarial reading at sane magnitudes: cancelling
values (`1E+30`, `-1E+30`, `0.005`), wide spreads (`1E+30` with `1E-30`) and large
`n` all get enough digits, because `len(str(n))` bounds the carries from summing `n`
terms and `high - low` covers the significant range. F3 is a ceiling problem, not an
error in the formula.

## The coder's five listed judgment calls

1. **Case-sensitive, exact header names** — accepted. The brief names the headers
   literally and folding would make duplicate detection ambiguous.
2. **Whitespace-only line is an invalid record** — accepted. The brief says *completely*
   empty; `"   "` is not.
3. **`_` rejected, exponent accepted** — this is where F2 lands. The principle is right;
   it is applied to one form and not another.
4. **Duplicate detection covers every repeated name, including blanks** — accepted,
   matches the brief literally.
5. **Zero totals normalised to `0.00`** — accepted, and worth keeping.

## Minor note

`_BOM` is a literal U+FEFF in the source (`'_BOM = "﻿"'`), invisible in every
editor. Writing it as `"﻿"` would remove a real maintenance hazard — an invisible
character can be deleted or mangled without anyone seeing it in a diff. Cosmetic only;
the behaviour is correct.

## Scope

Findings are for the revision task (`ci-qo0` / `ci-9oa`). No code, test or script was
changed in this review, and no report file belonging to another bead was written.
