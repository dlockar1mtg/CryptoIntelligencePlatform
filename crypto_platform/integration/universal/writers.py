"""Deterministic universal export file writers."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .serialization import (
    serialize_records,
    serialize_value,
)


def write_csv(
    *,
    path: Path,
    columns: list[str],
    records: list[Any],
) -> int:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    serialized = serialize_records(records)

    for index, record in enumerate(serialized):
        missing = [
            column
            for column in columns
            if column not in record
        ]

        extra = [
            key
            for key in record
            if key not in columns
        ]

        if missing or extra:
            raise ValueError(
                f"CSV record {index} does not match "
                f"the declared columns. "
                f"Missing={missing}; Extra={extra}"
            )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            extrasaction="raise",
            lineterminator="\n",
        )

        writer.writeheader()

        for record in serialized:
            writer.writerow(
                {
                    column: (
                        ""
                        if record[column] is None
                        else record[column]
                    )
                    for column in columns
                }
            )

    return len(serialized)


def write_json(
    *,
    path: Path,
    payload: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_payload = serialize_value(payload)

    path.write_text(
        json.dumps(
            safe_payload,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )