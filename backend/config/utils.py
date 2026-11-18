"""Shared helpers: money rounding and safe query-parameter parsing."""

import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from rest_framework.exceptions import ValidationError

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value):
    """Decimal-কে ২ দশমিক ঘরে রাউন্ড করে (টাকার হিসাবের জন্য)।"""
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def parse_bool(value, field):
    if value is None or value == "":
        return None
    v = value.strip().lower()
    if v in ("1", "true", "yes"):
        return True
    if v in ("0", "false", "no"):
        return False
    raise ValidationError({field: "Must be true or false."})


def parse_int(value, field):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError({field: "Must be a whole number."})


def parse_decimal(value, field):
    if value is None or value == "":
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({field: "Must be a valid number."})


def parse_date(value, field):
    if value is None or value == "":
        return None
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError({field: "Use the format YYYY-MM-DD."})
