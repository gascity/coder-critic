"""Summarize CSV expense records by category.

Implements the contract in BRIEF.md using only the Python standard library.
``summarize(text)`` returns ``{"rows": int, "invalid_rows": int,
"totals": {category: "0.00"}}``.
"""

import csv
import io
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

__all__ = ["summarize"]

_BOM = "﻿"
_CATEGORY = "category"
_AMOUNT = "amount"
_CENTS = Decimal("0.01")


def _records(text: str):
    """Yield CSV records, dropping completely empty lines.

    ``newline=""`` hands the csv module untranslated line endings, so CRLF
    input and quoted fields keep their exact contents.  A leading UTF-8 BOM
    is removed so it does not become part of the first header name.
    """
    if text.startswith(_BOM):
        text = text[len(_BOM):]
    for record in csv.reader(io.StringIO(text, newline="")):
        if record:  # csv yields [] for a completely empty line
            yield record


def _amount(raw: str):
    """Return the Decimal for *raw*, or None when it is not a finite number."""
    if "_" in raw:  # Decimal() reads "1_0" as 10; CSV data should not.
        return None
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError):
        return None
    return value if value.is_finite() else None  # rejects NaN and +/-Infinity


def _total(values: list) -> Decimal:
    """Sum *values* without intermediate rounding, then round to two places."""
    low = min(min(v.as_tuple().exponent for v in values), _CENTS.as_tuple().exponent)
    high = max(v.adjusted() for v in values)
    with localcontext() as ctx:
        # Room for every digit of the widest input, the carries from summing
        # len(values) of them, and the two places the total is rounded to.
        ctx.prec = max(ctx.prec, high - low + len(str(len(values))) + 4)
        total = sum(values, Decimal(0))
        cents = total.quantize(_CENTS, rounding=ROUND_HALF_UP)
    # An input of "-0" would otherwise print as "-0.00".
    return cents.copy_abs() if cents.is_zero() else cents


def summarize(text: str) -> dict:
    """Total the ``amount`` column of a CSV text per ``category`` value.

    Raises ValueError for empty input, duplicate column headers, or a header
    row without both required columns.  Malformed data records are counted in
    ``invalid_rows`` and skipped.
    """
    records = _records(text)
    try:
        header = [name.strip() for name in next(records)]
    except StopIteration:
        raise ValueError("input has no header row") from None
    if len(set(header)) != len(header):
        raise ValueError(f"duplicate column header in {header!r}")
    missing = [name for name in (_CATEGORY, _AMOUNT) if name not in header]
    if missing:
        raise ValueError(f"missing required column(s): {', '.join(missing)}")
    category_at = header.index(_CATEGORY)
    amount_at = header.index(_AMOUNT)

    rows = 0
    invalid_rows = 0
    values: dict[str, list] = {}  # category -> amounts, in first-seen order
    for record in records:
        if len(record) != len(header):  # missing or extra fields
            invalid_rows += 1
            continue
        category = record[category_at].strip()
        amount = _amount(record[amount_at].strip())
        if not category or amount is None:
            invalid_rows += 1
            continue
        rows += 1
        values.setdefault(category, []).append(amount)

    totals = {category: str(_total(amounts)) for category, amounts in values.items()}
    return {"rows": rows, "invalid_rows": invalid_rows, "totals": totals}
