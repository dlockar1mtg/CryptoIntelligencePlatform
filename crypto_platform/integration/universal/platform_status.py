"""Universal platform-status export records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from .context import ExportContext
from .source_models import SourceRun


PLATFORM_STATUS_COLUMNS = [
    "contract_version",
    "platform_id",
    "platform_name",
    "platform_version",
    "run_id",
    "run_started_at_utc",
    "run_completed_at_utc",
    "run_status",
    "data_as_of_date",
    "records_published",
    "warning_count",
    "error_count",
    "source_machine",
    "message",
]


@dataclass(frozen=True)
class UniversalPlatformStatusRecord:
    contract_version: str
    platform_id: str
    platform_name: str
    platform_version: str
    run_id: str
    run_started_at_utc: datetime
    run_completed_at_utc: datetime | None
    run_status: str
    data_as_of_date: object
    records_published: int
    warning_count: int
    error_count: int
    source_machine: str | None
    message: str

    def to_dict(
        self,
    ) -> dict[str, object]:
        return asdict(self)


def build_platform_status(
    *,
    context: ExportContext,
    source_runs: list[SourceRun],
    exported_record_count: int,
    warning_count: int = 1,
    error_count: int = 0,
    source_machine: str | None = None,
) -> list[UniversalPlatformStatusRecord]:
    if not source_runs:
        raise ValueError(
            "Platform status requires source-run lineage."
        )

    started_runs = [
        run
        for run in source_runs
        if run.started_at_utc is not None
    ]

    completed_runs = [
        run
        for run in source_runs
        if run.completed_at_utc is not None
    ]

    if not started_runs:
        raise ValueError(
            "Platform status requires source start times."
        )

    if not completed_runs:
        raise ValueError(
            "Platform status requires completed source runs."
        )

    run_started_at_utc = min(
        run.started_at_utc
        for run in started_runs
    )

    run_completed_at_utc = max(
        run.completed_at_utc
        for run in completed_runs
    )

    versions = sorted(
        {
            run.platform_version
            for run in source_runs
            if run.platform_version
        }
    )

    platform_version = (
        ", ".join(versions)
        if versions
        else "unknown"
    )

    module_lineage = ", ".join(
        (
            f"M{run.module_number}="
            f"{run.run_id}"
        )
        for run in sorted(
            source_runs,
            key=lambda item: item.module_number,
        )
    )

    message = (
        "RESEARCH ONLY. "
        "Actual portfolio holdings were not supplied; "
        "portfolio_positions.csv contains zero records. "
        f"Adapter version: {context.adapter_version}. "
        f"Source lineage: {module_lineage}"
    )

    return [
        UniversalPlatformStatusRecord(
            contract_version=context.contract_version,
            platform_id=context.platform_id,
            platform_name=context.platform_name,
            platform_version=platform_version,
            run_id=context.run_id,
            run_started_at_utc=run_started_at_utc,
            run_completed_at_utc=run_completed_at_utc,
            run_status="success",
            data_as_of_date=(
                run_completed_at_utc.date()
            ),
            records_published=exported_record_count,
            warning_count=warning_count,
            error_count=error_count,
            source_machine=source_machine,
            message=message,
        )
    ]
