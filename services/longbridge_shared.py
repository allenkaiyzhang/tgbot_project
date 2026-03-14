"""Shared helpers for LongBridge service modules."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, List, Optional


def to_decimal(value: Optional[Any]) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def to_date(value: Optional[Any]) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"Unsupported date type: {type(value)}")


def to_datetime(value: Optional[Any]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace(" ", "T"))
    raise TypeError(f"Unsupported datetime type: {type(value)}")


def to_list(value: Optional[Iterable[Any]]) -> Optional[List[Any]]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def enum_from_name(enum_cls: Any, value: Optional[Any]) -> Optional[Any]:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    return getattr(enum_cls, value)


def enum_list(enum_cls: Any, values: Optional[Iterable[Any]]) -> Optional[List[Any]]:
    if values is None:
        return None
    return [enum_from_name(enum_cls, v) for v in values]


def serialize_sdk_value(value: Any, *, depth: int = 0, max_depth: int = 4) -> Any:
    """Convert SDK objects into JSON-serializable structures."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (Decimal, date, datetime)):
        return str(value)

    if isinstance(value, dict):
        return {
            str(k): serialize_sdk_value(v, depth=depth + 1, max_depth=max_depth)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [serialize_sdk_value(v, depth=depth + 1, max_depth=max_depth) for v in value]

    if depth >= max_depth:
        return str(value)

    attrs: dict[str, Any] = {}
    for name in dir(value):
        if name.startswith("_"):
            continue
        try:
            attr = getattr(value, name)
        except Exception:
            continue
        if callable(attr):
            continue
        attrs[name] = serialize_sdk_value(attr, depth=depth + 1, max_depth=max_depth)

    if attrs:
        return attrs
    return str(value)

