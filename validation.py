from datetime import date
from decimal import Decimal, InvalidOperation

from flask import request


class ValidationError(ValueError):
    pass


def text(name, maximum=100, *, optional=False):
    value = request.form.get(name, "").strip()
    if not value and not optional:
        raise ValidationError(f"{name.replace('_', ' ').title()} is required.")
    if len(value) > maximum:
        raise ValidationError(f"{name.replace('_', ' ').title()} must be at most {maximum} characters.")
    return value


def integer(name, minimum=1, maximum=2147483647, *, default=None):
    raw = request.form.get(name)
    if raw in (None, "") and default is not None:
        return default
    try:
        value = int(raw)
        if not minimum <= value <= maximum:
            raise ValueError
        return value
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name.replace('_', ' ').title()} must be between {minimum} and {maximum}.") from exc


def money(name, *, minimum=Decimal("0.01"), maximum=Decimal("99999999.99")):
    try:
        value = Decimal(request.form.get(name, ""))
        if not value.is_finite() or not minimum <= value <= maximum or value != value.quantize(Decimal("0.01")):
            raise InvalidOperation
        return value
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{name.replace('_', ' ').title()} must be between {minimum} and {maximum}, with at most two decimal places.") from exc


def choice(name, options):
    value = request.form.get(name, "")
    if value not in options:
        raise ValidationError(f"Choose a valid {name.replace('_', ' ')}.")
    return value


def day(name):
    try:
        return date.fromisoformat(request.form.get(name, ""))
    except ValueError as exc:
        raise ValidationError(f"Enter a valid {name.replace('_', ' ')}.") from exc
