"""Summarize CSV expense records by category.

Implements the contract in BRIEF.md using only the Python standard library.
``summarize(text)`` returns ``{"rows": int, "invalid_rows": int,
"totals": {category: "0.00"}}``.
"""

import csv
import io
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

__all__ = ["summarize"]

_BOM = chr(0xFEFF)  # by code point: a literal U+FEFF in the source is invisible
_CATEGORY = "category"
_AMOUNT = "amount"
_CENTS = Decimal("0.01")

# The whole accepted amount grammar, in one reviewable line.  Written with
# [0-9] rather than \d because in str patterns \d also matches non-ASCII
# decimal digits such as U+FF11, which is exactly the leniency this removes.
# It subsumes the underscores of Python numeric literals ("1_0"), Decimal's
# tolerance of surrounding whitespace, and the words NaN and Infinity.
# Exponent notation is kept: the brief neither requires nor forbids it.
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")

# Largest accepted magnitude, as a power of ten.  The brief sets no range for
# amounts and this is far past any real expense, but some bound is needed:
# _amount otherwise accepts any finite Decimal the constructor will build, and
# _total sizes its precision from the spread of what it is handed, so a
# 12-character cell like "1E+999999999" asks for a context precision near
# 10**9.  The bound also has to stay inside the decimal context's own exponent
# range (default Emax 999999, Emin -999999) with room for the carries of
# summing a column -- at 10**6, "1E+1000000" is accepted here and then raises
# Overflow in _total.  10**5 leaves an order of magnitude at both ends.
_MAX_ADJUSTED = 10 ** 5


def _records(text: str):
    """Yield CSV records, dropping completely empty lines.

    ``newline=""`` hands the csv module untranslated line endings, so CRLF
    input and quoted fields keep their exact contents.  A leading UTF-8 BOM
    is removed so it does not become part of the first header name.

    A ``csv.Error`` -- a field over ``csv.field_size_limit()``, most often the
    rest of the file swept into one cell by a single unterminated quote -- is
    re-raised as ``ValueError``.  The reader's position in the input is lost
    once it raises, so that record cannot honestly be skipped and counted as
    invalid; converting the type is what keeps ``summarize`` to the two
    outcomes its caller is told to expect.
    """
    if text.startswith(_BOM):
        text = text[len(_BOM):]
    reader = csv.reader(io.StringIO(text, newline=""))
    while True:
        try:
            record = next(reader)
        except StopIteration:
            return
        except csv.Error as err:
            raise ValueError(f"malformed CSV input: {err}") from err
        if record:  # csv yields [] for a completely empty line
            yield record


def _amount(raw: str):
    """Return the Decimal for *raw*, or None when it is not a valid amount.

    Only ``_NUMBER`` is accepted, so NaN, Infinity and every other form of
    Decimal's leniency are rejected together by one rule rather than one at a
    time.  Magnitudes past ``_MAX_ADJUSTED`` in either direction are rejected
    as out of range -- both directions matter, because ``_total`` sizes its
    precision from the spread between the largest and smallest value it is
    given, so a very small exponent is as expensive as a very large one.
    """
    if not _NUMBER.fullmatch(raw):
        return None
    try:
        value = Decimal(raw)
    except InvalidOperation:  # exponent too large for the constructor itself
        return None
    return value if abs(value.adjusted()) <= _MAX_ADJUSTED else None


def _total(values: list) -> Decimal:
    """Sum *values* without intermediate rounding, then round to two places."""
    low = min(min(v.as_tuple().exponent for v in values), _CENTS.as_tuple().exponent)
    high = max(v.adjusted() for v in values)
    with localcontext() as ctx:
        # Room for every digit of the widest input, the carries from summing
        # len(values) of them, and the two places the total is rounded to.
        # _amount bounds the exponents, and csv.field_size_limit() bounds the
        # digits per field, so this stays finite for any input we accept.
        ctx.prec = max(ctx.prec, high - low + len(str(len(values))) + 4)
        total = sum(values, Decimal(0))
        cents = total.quantize(_CENTS, rounding=ROUND_HALF_UP)
    # An input of "-0" would otherwise print as "-0.00".
    return cents.copy_abs() if cents.is_zero() else cents


def summarize(text: str) -> dict:
    """Total the ``amount`` column of a CSV text per ``category`` value.

    Raises ValueError for empty input, duplicate column headers, a header row
    without both required columns, or CSV the reader cannot parse.  Malformed
    data records -- wrong field count, blank category, or an amount that is
    not a finite in-range number -- are counted in ``invalid_rows`` and
    skipped.
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
