"""Execution context for the universal crypto export adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from . import (
    ADAPTER_VERSION,
    CONTRACT_VERSION,
    PLATFORM_ID,
    PLATFORM_NAME,
)


@dataclass(frozen=True)
class ExportContext:
    """Immutable metadata shared by every exported dataset."""

    run_id: str
    generated_at_utc: datetime
    source_database: Path
    output_directory: Path
    contract_version: str = CONTRACT_VERSION
    adapter_version: str = ADAPTER_VERSION
    platform_id: str = PLATFORM_ID
    platform_name: str = PLATFORM_NAME

    @classmethod
    def create(
        cls,
        *,
        source_database: Path,
        output_directory: Path,
        run_id: str | None = None,
        generated_at_utc: datetime | None = None,
    ) -> "ExportContext":
        timestamp = (
            generated_at_utc
            if generated_at_utc is not None
            else datetime.now(timezone.utc)
        )

        if timestamp.tzinfo is None:
            raise ValueError(
                "generated_at_utc must be timezone-aware."
            )

        resolved_run_id = (
            run_id
            if run_id is not None
            else str(uuid4())
        )

        if not resolved_run_id.strip():
            raise ValueError(
                "run_id must not be empty."
            )

        return cls(
            run_id=resolved_run_id,
            generated_at_utc=timestamp.astimezone(
                timezone.utc
            ),
            source_database=source_database.resolve(),
            output_directory=output_directory.resolve(),
        )

    @property
    def generated_at_iso(self) -> str:
        """Return a normalized UTC ISO-8601 timestamp."""

        return (
            self.generated_at_utc
            .astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )