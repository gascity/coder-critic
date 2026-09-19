"""CSV expense summary — the public entry point.

The work is split across two independent modules: ``records.parse_records``
owns CSV shape (headers, quoting, trimming, missing or extra fields) and
``totals.aggregate`` owns the numbers (what is a finite Decimal, exact sums,
one HALF_UP rounding per category). ``summarize`` composes them and adds no
rules of its own.
"""

from records import parse_records
from totals import aggregate


def summarize(text: str) -> dict:
    """Summarize CSV expense text with required headers ``category,amount``.

    Returns ``{"rows": N, "invalid_rows": M, "totals": {category: "d.dd"}}``,
    counting valid data records in ``rows`` and skipped ones in ``invalid_rows``.
    Raises ValueError for empty input, headers missing ``category`` or
    ``amount``, duplicate headers, and malformed quoting.
    """
    return aggregate(parse_records(text))
