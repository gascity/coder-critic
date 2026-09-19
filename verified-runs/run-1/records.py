"""Split CSV expense text into (category, amount) text pairs.

Numeric validation belongs to totals.py; this module only reports the shape of
each row: a pair of trimmed strings, or None when the row cannot supply one.
"""

import csv
import io

BOM = "﻿"
CATEGORY = "category"
AMOUNT = "amount"


def parse_records(text):
    """Return one (category, amount) pair or None per nonempty data row.

    Raises ValueError for empty input, headers missing 'category' or 'amount',
    duplicate headers, and malformed quoting.
    """
    header = None
    indexes = ()
    records = []
    for row in _read_rows(text):
        if not row:  # completely empty line
            continue
        if header is None:
            header = [field.strip() for field in row]
            indexes = _required_indexes(header)
            continue
        if len(row) != len(header):  # missing or extra field
            records.append(None)
            continue
        category, amount = (row[i].strip() for i in indexes)
        records.append((category, amount) if category and amount else None)
    if header is None:
        raise ValueError("input has no header row")
    return records


def _read_rows(text):
    """Parse the whole text, converting csv's quoting errors to ValueError."""
    if text.startswith(BOM):
        text = text[len(BOM):]
    # newline="" keeps CRLF and quoted newlines intact for csv to interpret;
    # strict=True turns unterminated quotes into an error instead of a field.
    try:
        return list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except csv.Error as exc:
        raise ValueError(f"malformed CSV: {exc}") from exc


def _required_indexes(header):
    """Return the (category, amount) column positions of a valid header."""
    seen = set()
    for name in header:
        if name in seen:
            raise ValueError(f"duplicate column header: {name!r}")
        seen.add(name)
    missing = [name for name in (CATEGORY, AMOUNT) if name not in seen]
    if missing:
        raise ValueError(f"header is missing required column(s): {', '.join(missing)}")
    return header.index(CATEGORY), header.index(AMOUNT)
