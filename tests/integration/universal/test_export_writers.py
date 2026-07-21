from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from crypto_platform.integration.universal.manifest import (
    build_manifest_record,
)
from crypto_platform.integration.universal.context import (
    ExportContext,
)
from crypto_platform.integration.universal.writers import (
    write_csv,
    write_json,
)


@dataclass(frozen=True)
class ExampleRecord:
    name: str
    score: float | None

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "name": self.name,
            "score": self.score,
        }


def test_write_csv(
    tmp_path: Path,
) -> None:
    path = tmp_path / "example.csv"

    count = write_csv(
        path=path,
        columns=["name", "score"],
        records=[
            ExampleRecord(
                name="bitcoin",
                score=75.0,
            ),
            ExampleRecord(
                name="ethereum",
                score=None,
            ),
        ],
    )

    assert count == 2

    with path.open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(
            csv.DictReader(handle)
        )

    assert rows == [
        {
            "name": "bitcoin",
            "score": "75.0",
        },
        {
            "name": "ethereum",
            "score": "",
        },
    ]


def test_write_header_only_csv(
    tmp_path: Path,
) -> None:
    path = tmp_path / "empty.csv"

    count = write_csv(
        path=path,
        columns=["one", "two"],
        records=[],
    )

    assert count == 0
    assert path.read_text(
        encoding="utf-8"
    ) == "one,two\n"


def test_write_csv_rejects_extra_fields(
    tmp_path: Path,
) -> None:
    path = tmp_path / "invalid.csv"

    with pytest.raises(ValueError):
        write_csv(
            path=path,
            columns=["name"],
            records=[
                {
                    "name": "bitcoin",
                    "extra": "not-allowed",
                }
            ],
        )


def test_write_json_is_strict(
    tmp_path: Path,
) -> None:
    path = tmp_path / "example.json"

    write_json(
        path=path,
        payload={
            "status": "PASS",
            "value": float("nan"),
        },
    )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert payload == {
        "status": "PASS",
        "value": None,
    }


def test_manifest_checksum(
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "data.csv"

    data_path.write_text(
        "column\nvalue\n",
        encoding="utf-8",
    )

    context = ExportContext.create(
        source_database=(
            tmp_path / "source.duckdb"
        ),
        output_directory=tmp_path,
        run_id="test-run",
    )

    record = build_manifest_record(
        context=context,
        dataset_name="example",
        file_path=data_path,
        record_count=1,
    )

    assert record.dataset_name == "example"
    assert record.record_count == 1
    assert record.file_size_bytes > 0
    assert len(record.sha256) == 64
    assert record.validation_status == "PASS"