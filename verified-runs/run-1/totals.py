"""Exact per-category totals for the CSV expense summary.

``aggregate`` consumes the pairs produced by ``records.parse_records`` and owns
all numeric validation: it decides which amounts are real numbers, keeps every
category's running sum exact, and rounds each one only once, at the end.
"""

from decimal import ROUND_HALF_UP, Decimal, localcontext

CENTS = Decimal("0.01")
_DEFAULT_PRECISION = 28


def aggregate(records: list[tuple[str, str] | None]) -> dict:
    """Total ``(category, amount_text)`` pairs, skipping invalid records.

    ``None`` marks a record the parsing stage already rejected. An amount that
    Decimal cannot read, or that reads as NaN or an infinity, is rejected here.
    Categories are case-sensitive. Returns ``{"rows", "invalid_rows", "totals"}``
    where every total is a decimal string with exactly two places.
    """
    invalid_rows = 0
    valid: list[tuple[str, Decimal]] = []
    for record in records:
        amount = _amount(record)
        if amount is None:
            invalid_rows += 1
        else:
            valid.append((record[0], amount))

    sums: dict[str, Decimal] = {}
    with localcontext() as ctx:
        ctx.prec = _precision_for([amount for _, amount in valid])
        for category, amount in valid:
            running = sums.get(category)
            sums[category] = amount if running is None else running + amount
        totals = {category: str(_to_cents(total)) for category, total in sums.items()}

    return {"rows": len(valid), "invalid_rows": invalid_rows, "totals": totals}


def _amount(record: tuple[str, str] | None) -> Decimal | None:
    """Return the finite Decimal a record contributes, or None if it is invalid."""
    if record is None:
        return None
    _, text = record
    try:
        amount = Decimal(text)
    except (ArithmeticError, TypeError, ValueError):
        return None
    return amount if amount.is_finite() else None


def _precision_for(amounts: list[Decimal]) -> int:
    """Context precision wide enough that no running sum is ever rounded.

    The exact sum spans from the largest magnitude present -- plus the digits
    ``len(amounts)`` carries can add -- down to the smallest exponent present,
    and quantizing to cents can reach two places further down.
    """
    if not amounts:
        return _DEFAULT_PRECISION
    top = max(amount.adjusted() for amount in amounts) + len(str(len(amounts)))
    lowest = min(amount.as_tuple().exponent for amount in amounts)
    bottom = min(lowest, CENTS.as_tuple().exponent)
    return max(top - bottom + 1, _DEFAULT_PRECISION)


def _to_cents(total: Decimal) -> Decimal:
    """Round a category's exact sum to two places, HALF_UP, never as -0.00."""
    rounded = total.quantize(CENTS, rounding=ROUND_HALF_UP)
    return abs(rounded) if rounded == 0 else rounded
