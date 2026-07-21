"""Serialization helpers for universal export packages."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
import math
from pathlib import Path
from typing import Any


def serialize_value(
    value: Any,
) -> Any:
    """Convert a Python value into a strict JSON/CSV-safe value."""

    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            return None

        return value

    if isinstance(value, (int, str)):
        return value

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, Path):
        return str(value)

    if is_dataclass(value):
        return serialize_mapping(
            asdict(value)
        )

    if isinstance(value, dict):
        return serialize_mapping(value)

    if isinstance(value, (list, tuple)):
        return [
            serialize_value(item)
            for item in value
        ]

    return str(value)


def serialize_mapping(
    mapping: dict[str, Any],
) -> dict[str, Any]:
    return {
        str(key): serialize_value(value)
        for key, value in mapping.items()
    }


def serialize_records(
    records: list[Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    for record in records:
        if hasattr(record, "to_dict"):
            mapping = record.to_dict()

        elif is_dataclass(record):
            mapping = asdict(record)

        elif isinstance(record, dict):
            mapping = record

        else:
            raise TypeError(
                "Export records must be dataclasses, "
                "dictionaries, or expose to_dict()."
            )

        result.append(
            serialize_mapping(mapping)
        )

    return result