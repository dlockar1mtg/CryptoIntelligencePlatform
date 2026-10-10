"""Dependency-ordered production orchestration with durable run summaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Iterable
import uuid

from .registry import MODULE_REGISTRY, ModuleSpec, ProductionStage, validate_registry


# Longest a single module runner may take before it is stopped and recorded as FAIL.
MODULE_TIMEOUT_SECONDS = 40 * 60

# With the weekly-research option, a research-only module runs again once its last
# successful run is older than this.
WEEKLY_MAX_AGE_DAYS = 7.0

SKIPPED_WEEKLY = "SKIPPED_WEEKLY"


@dataclass(frozen=True)
class PipelineOptions:
    repository_root: Path
    output_root: Path
    stages: tuple[ProductionStage, ...] = tuple(ProductionStage)
    start_module: int | None = None
    end_module: int | None = None
    continue_on_optional_failure: bool = True
    resume: bool = False
    full_refresh: bool = False
    skip_coingecko: bool = False
    export_universal: bool = True
    source_database: Path | None = None
    # Run research-only (weekly-cadence) modules only on a full refresh, or when their
    # last successful run is missing or older than weekly_max_age_days.
    weekly_research: bool = False
    weekly_max_age_days: float = WEEKLY_MAX_AGE_DAYS


@dataclass
class ModuleRunResult:
    module: int
    stage: str
    runner: str
    required: bool
    status: str
    started_at_utc: str
    completed_at_utc: str
    duration_seconds: float
    return_code: int | None
    stdout_log: str
    stderr_log: str
    error: str = ""


@dataclass
class PipelineSummary:
    run_id: str
    status: str
    started_at_utc: str
    completed_at_utc: str
    repository_root: str
    run_directory: str
    requested_stages: list[str]
    full_refresh: bool
    resume: bool
    weekly_research: bool = False
    module_results: list[dict] = field(default_factory=list)
    retired_modules: list[dict] = field(default_factory=list)
    universal_export: dict = field(default_factory=dict)


class ProductionOrchestrator:
    def __init__(self, options: PipelineOptions) -> None:
        self.options = options
        self.root = options.repository_root.resolve()
        self.output_root = options.output_root.resolve()
        self.run_id = os.getenv("CRYPTO_PRODUCTION_RUN_ID", "").strip() or (
            "crypto-prod-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "-" + uuid.uuid4().hex[:8]
        )
        self.run_directory = self.output_root / self.run_id
        self.logs_directory = self.run_directory / "logs"
        self.summary_path = self.run_directory / "run_summary.json"

    @staticmethod
    def _iso_now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _selected_modules(self) -> Iterable[ModuleSpec]:
        selected_stages = set(self.options.stages)
        for spec in MODULE_REGISTRY:
            if not spec.runnable or spec.stage not in selected_stages:
                continue
            if self.options.start_module is not None and spec.number < self.options.start_module:
                continue
            if self.options.end_module is not None and spec.number > self.options.end_module:
                continue
            yield spec

    def _existing_successes(self) -> set[int]:
        if not self.options.resume or not self.summary_path.exists():
            return set()
        payload = json.loads(self.summary_path.read_text(encoding="utf-8"))
        return {
            int(item["module"])
            for item in payload.get("module_results", [])
            if item.get("status") == "PASS"
        }

    def _database_path(self) -> Path:
        # An unset or empty CRYPTO_DATABASE_PATH falls back to the default path.
        # (Path("") is truthy, so it must not be built from an empty value.)
        env_database = os.getenv("CRYPTO_DATABASE_PATH", "").strip()
        source_database = (
            self.options.source_database
            or (Path(env_database) if env_database else None)
            or self.root / "data" / "crypto_intelligence.duckdb"
        )
        if not source_database.is_absolute():
            source_database = (self.root / source_database).resolve()
        return source_database

    def _last_success_epoch(self, spec: ModuleSpec) -> float | None:
        """Seconds since the epoch of the module's last successful run, or None."""
        database = self._database_path()
        if not spec.run_table or not database.is_file():
            return None
        import duckdb

        connection = duckdb.connect(str(database), read_only=True)
        try:
            exists = connection.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
                [spec.run_table],
            ).fetchone()[0]
            if not exists:
                return None
            value = connection.execute(
                f'SELECT epoch(MAX(completed_at_utc)) FROM "{spec.run_table}" '
                "WHERE UPPER(status) = 'SUCCESS' AND completed_at_utc IS NOT NULL"
            ).fetchone()[0]
        finally:
            connection.close()
        return None if value is None else float(value)

    def _weekly_skip(self, spec: ModuleSpec) -> dict | None:
        """Return the skip record for a weekly module that is not due, else None (run it)."""
        if not (self.options.weekly_research and spec.weekly) or self.options.full_refresh:
            return None
        try:
            last_success = self._last_success_epoch(spec)
        except Exception as exc:  # Unknown state: run the module, as before this option.
            print(f"Module {spec.number}: could not read its last run ({exc}); running it.")
            return None
        if last_success is None:
            return None
        age_days = (time.time() - last_success) / 86400.0
        if age_days >= self.options.weekly_max_age_days:
            return None
        last_iso = datetime.fromtimestamp(last_success, timezone.utc).isoformat().replace("+00:00", "Z")
        now = self._iso_now()
        return {
            "module": spec.number,
            "stage": spec.stage.value,
            "runner": spec.runner,
            "required": spec.required,
            "status": SKIPPED_WEEKLY,
            "started_at_utc": now,
            "completed_at_utc": now,
            "duration_seconds": 0.0,
            "return_code": None,
            "last_success_at_utc": last_iso,
            "last_success_age_days": round(age_days, 3),
            "reason": (
                "Research-only module; runs weekly (Sunday full refresh, or when its last "
                f"successful run is older than {self.options.weekly_max_age_days:g} days)."
            ),
        }

    def _write_summary(self, summary: PipelineSummary) -> None:
        self.run_directory.mkdir(parents=True, exist_ok=True)
        temp = self.summary_path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
        temp.replace(self.summary_path)

    def _run_module(self, spec: ModuleSpec) -> ModuleRunResult:
        runner = spec.runner_path(self.root)
        assert runner is not None
        stdout_path = self.logs_directory / f"module_{spec.number:02d}.stdout.log"
        stderr_path = self.logs_directory / f"module_{spec.number:02d}.stderr.log"
        started = self._iso_now()
        started_clock = time.monotonic()

        command = [sys.executable, str(runner)]
        if spec.number == 1 and self.options.full_refresh:
            command.append("--full-refresh")
        if spec.number == 1 and self.options.skip_coingecko:
            command.append("--skip-coingecko")

        env = os.environ.copy()
        env["CRYPTO_PRODUCTION_RUN_ID"] = self.run_id
        env["CRYPTO_PRODUCTION_STAGE"] = spec.stage.value
        env["CRYPTO_PRODUCTION_MODULE"] = str(spec.number)

        timed_out = False
        with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr_handle:
            try:
                completed = subprocess.run(
                    command,
                    cwd=self.root,
                    env=env,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    text=True,
                    check=False,
                    timeout=MODULE_TIMEOUT_SECONDS,
                )
                return_code = completed.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                return_code = None

        status = "PASS" if return_code == 0 else "FAIL"
        if timed_out:
            error = f"Runner timed out after {MODULE_TIMEOUT_SECONDS} seconds."
        elif status == "PASS":
            error = ""
        else:
            error = f"Runner exited with code {return_code}."
        return ModuleRunResult(
            module=spec.number,
            stage=spec.stage.value,
            runner=spec.runner or "",
            required=spec.required,
            status=status,
            started_at_utc=started,
            completed_at_utc=self._iso_now(),
            duration_seconds=round(time.monotonic() - started_clock, 3),
            return_code=return_code,
            stdout_log=str(stdout_path.relative_to(self.run_directory)),
            stderr_log=str(stderr_path.relative_to(self.run_directory)),
            error=error,
        )

    def _run_universal_export(self) -> dict:
        if not self.options.export_universal:
            return {"status": "SKIPPED", "reason": "Disabled by command option."}

        source_database = self._database_path()
        if not source_database.is_file():
            return {
                "status": "FAIL",
                "reason": f"Source database not found: {source_database}",
            }

        from crypto_platform.integration.universal import ExportContext, UniversalPackageBuilder
        from crypto_platform.integration.universal.package_builder import PackageValidationError

        package_dir = self.run_directory / "universal_package"
        context = ExportContext.create(
            source_database=source_database,
            output_directory=package_dir,
            run_id=self.run_id,
            generated_at_utc=datetime.now(timezone.utc),
        )
        try:
            result = UniversalPackageBuilder(context).build()
        except PackageValidationError as exc:
            return {
                "status": "FAIL",
                "reason": str(exc),
                "failed_checks": exc.failed_checks,
                "output_directory": str(exc.output_directory),
            }
        return {
            "status": result.validation_status,
            "output_directory": str(result.output_directory),
            "dataset_counts": result.dataset_counts,
            "manifest_count": result.manifest_count,
        }

    def run(self) -> PipelineSummary:
        registry_errors = validate_registry(self.root)
        if registry_errors:
            raise RuntimeError("Production registry is invalid: " + " | ".join(registry_errors))

        self.logs_directory.mkdir(parents=True, exist_ok=True)
        started = self._iso_now()
        summary = PipelineSummary(
            run_id=self.run_id,
            status="RUNNING",
            started_at_utc=started,
            completed_at_utc="",
            repository_root=str(self.root),
            run_directory=str(self.run_directory),
            requested_stages=[stage.value for stage in self.options.stages],
            full_refresh=self.options.full_refresh,
            resume=self.options.resume,
            weekly_research=self.options.weekly_research,
            retired_modules=[
                {"module": spec.number, "reason": spec.reason}
                for spec in MODULE_REGISTRY
                if spec.status == "retired"
            ],
        )
        self._write_summary(summary)
        prior_successes = self._existing_successes()

        for spec in self._selected_modules():
            if spec.number in prior_successes:
                summary.module_results.append(
                    {
                        "module": spec.number,
                        "stage": spec.stage.value,
                        "runner": spec.runner,
                        "required": spec.required,
                        "status": "RESUMED_PASS",
                    }
                )
                continue

            skipped = self._weekly_skip(spec)
            if skipped is not None:
                summary.module_results.append(skipped)
                self._write_summary(summary)
                continue

            result = self._run_module(spec)
            summary.module_results.append(asdict(result))
            self._write_summary(summary)

            if result.status == "FAIL":
                if spec.required or not self.options.continue_on_optional_failure:
                    summary.status = "FAIL"
                    summary.completed_at_utc = self._iso_now()
                    self._write_summary(summary)
                    return summary

        summary.universal_export = self._run_universal_export()
        export_status = summary.universal_export.get("status")
        summary.status = "PASS" if export_status in {"PASS", "SKIPPED"} else "FAIL"
        summary.completed_at_utc = self._iso_now()
        self._write_summary(summary)
        return summary
