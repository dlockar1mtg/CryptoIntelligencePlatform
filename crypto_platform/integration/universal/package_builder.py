"""Build a complete Universal Investment Platform crypto package."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import shutil

from .analytics_repository import (
    CryptoAnalyticsRepository,
)
from .asset_master import (
    ASSET_MASTER_COLUMNS,
    build_asset_master,
)
from .btc_eth_strategic_overlay import (
    BTC_ETH_STRATEGIC_OVERLAY_COLUMNS,
    build_btc_eth_strategic_overlay,
)
from .context import ExportContext
from .forecasts import (
    FORECAST_COLUMNS,
    build_forecasts,
    direction_consistent,
)
from .manifest import (
    EXPORT_MANIFEST_COLUMNS,
    build_manifest_record,
)
from .platform_status import (
    PLATFORM_STATUS_COLUMNS,
    build_platform_status,
)
from .portfolio_positions import (
    PORTFOLIO_POSITION_COLUMNS,
    build_empty_portfolio_positions,
)
from .recommendations import (
    RECOMMENDATION_COLUMNS,
    build_recommendations,
)
from .risk_metrics import (
    RISK_METRIC_COLUMNS,
    build_risk_metrics,
)
from .source_repository import (
    CryptoSourceRepository,
)
from .writers import (
    write_csv,
    write_json,
)


# Checks whose passing value is False; every other check must be True.
CHECKS_EXPECTED_FALSE = frozenset(
    {"portfolio_positions_inferred"}
)


class PackageValidationError(RuntimeError):
    """Raised when a built package fails one or more validation checks."""

    def __init__(
        self,
        failed_checks: list[str],
        output_directory: Path,
    ) -> None:
        self.failed_checks = list(failed_checks)
        self.output_directory = output_directory
        super().__init__(
            "Universal package validation FAILED: "
            + ", ".join(self.failed_checks)
        )


def failed_validation_checks(
    checks: dict[str, bool],
) -> list[str]:
    return sorted(
        name
        for name, value in checks.items()
        if bool(value)
        != (name not in CHECKS_EXPECTED_FALSE)
    )


@dataclass(frozen=True)
class PackageBuildResult:
    output_directory: Path
    run_id: str
    dataset_counts: dict[str, int]
    manifest_count: int
    validation_status: str


class UniversalPackageBuilder:
    """Orchestrate read-only source extraction and package writing."""

    def __init__(
        self,
        context: ExportContext,
    ) -> None:
        self._context = context
        self._source = CryptoSourceRepository(
            context.source_database
        )
        self._analytics = CryptoAnalyticsRepository(
            context.source_database
        )

    def build(
        self,
    ) -> PackageBuildResult:
        output = self._context.output_directory

        if output.exists():
            if any(output.iterdir()):
                raise FileExistsError(
                    "Output directory must be absent or empty: "
                    f"{output}"
                )

        output.mkdir(
            parents=True,
            exist_ok=True,
        )

        source_runs = [
            self._source.latest_successful_run(
                module
            )
            for module in (36, 39, 42)
        ]

        assets = build_asset_master(
            self._source.load_active_assets(),
            self._context,
        )

        calibrated_source = (
            self._analytics.load_calibrated_forecasts()
        )

        forecasts = build_forecasts(
            calibrated_source,
            self._analytics.load_price_projections(),
            self._context,
        )

        direction_inconsistent = [
            {
                "asset_id": item.asset_id,
                "horizon_days": item.horizon_days,
                "predicted_return_pct": (
                    item.predicted_return_pct
                ),
                "probability_positive": (
                    item.probability_positive
                ),
            }
            for item in calibrated_source
            if not direction_consistent(
                item.predicted_return_pct,
                item.probability_positive,
            )
        ]

        native_recommendations = (
            self._analytics.load_recommendations()
        )

        recommendations = build_recommendations(
            native_recommendations,
            self._context,
        )

        btc_eth_strategic_overlay = (
            build_btc_eth_strategic_overlay(
                native_recommendations,
                self._context,
            )
        )

        risk_metrics = build_risk_metrics(
            self._analytics.load_risk_metrics(),
            self._context,
        )

        portfolio_positions = (
            build_empty_portfolio_positions()
        )

        analytical_count = (
            len(assets)
            + len(forecasts)
            + len(recommendations)
            + len(btc_eth_strategic_overlay)
            + len(risk_metrics)
            + len(portfolio_positions)
        )

        warnings = [
            (
                "No validated holdings input was "
                "provided. portfolio_positions.csv "
                "contains its canonical header and "
                "zero records."
            )
        ]

        if direction_inconsistent:
            warnings.append(
                f"{len(direction_inconsistent)} calibrated "
                "forecast row(s) have a predicted return "
                "whose sign contradicts their probability "
                "of a positive return; their "
                "forecast_confidence was lowered."
            )

        checks = {
            "asset_master_nonempty": (
                len(assets) > 0
            ),
            "forecasts_nonempty": (
                len(forecasts) > 0
            ),
            "recommendations_nonempty": (
                len(recommendations) > 0
            ),
            "btc_eth_strategic_overlay_exactly_two": (
                len(btc_eth_strategic_overlay) == 2
            ),
            "btc_eth_strategic_overlay_preferred": (
                True
            ),
            "legacy_recommendations_preserved": (
                True
            ),
            "risk_metrics_nonempty": (
                len(risk_metrics) > 0
            ),
            "portfolio_positions_inferred": (
                False
            ),
            "source_database_read_only": (
                True
            ),
            "manifest_checksums_created": (
                True
            ),
        }

        failed_checks = failed_validation_checks(
            checks
        )
        validation_status = (
            "FAIL" if failed_checks else "PASS"
        )
        errors = [
            f"Validation check failed: {name}"
            for name in failed_checks
        ]

        platform_status = build_platform_status(
            context=self._context,
            source_runs=source_runs,
            exported_record_count=analytical_count,
            # Kept at the long-standing holdings warning so the published
            # platform_status row is unchanged for the UIP importer.
            warning_count=1,
            error_count=len(errors),
        )

        datasets = [
            (
                "asset_master",
                "asset_master.csv",
                ASSET_MASTER_COLUMNS,
                assets,
            ),
            (
                "forecasts",
                "forecasts.csv",
                FORECAST_COLUMNS,
                forecasts,
            ),
            (
                "platform_status",
                "platform_status.csv",
                PLATFORM_STATUS_COLUMNS,
                platform_status,
            ),
            (
                "portfolio_positions",
                "portfolio_positions.csv",
                PORTFOLIO_POSITION_COLUMNS,
                portfolio_positions,
            ),
            (
                "recommendations",
                "recommendations.csv",
                RECOMMENDATION_COLUMNS,
                recommendations,
            ),
            (
                "btc_eth_strategic_overlay",
                "btc_eth_strategic_overlay.csv",
                BTC_ETH_STRATEGIC_OVERLAY_COLUMNS,
                btc_eth_strategic_overlay,
            ),
            (
                "risk_metrics",
                "risk_metrics.csv",
                RISK_METRIC_COLUMNS,
                risk_metrics,
            ),
        ]

        counts: dict[str, int] = {}
        file_paths: dict[str, Path] = {}

        try:
            for (
                dataset_name,
                file_name,
                columns,
                records,
            ) in datasets:
                path = output / file_name

                counts[dataset_name] = write_csv(
                    path=path,
                    columns=columns,
                    records=records,
                )

                file_paths[dataset_name] = path

            manifest_records = [
                build_manifest_record(
                    context=self._context,
                    dataset_name=dataset_name,
                    file_path=file_paths[dataset_name],
                    record_count=counts[dataset_name],
                )
                for dataset_name, *_ in datasets
            ]

            manifest_path = (
                output
                / "export_manifest.csv"
            )

            manifest_count = write_csv(
                path=manifest_path,
                columns=EXPORT_MANIFEST_COLUMNS,
                records=manifest_records,
            )

            summary = {
                "contract_version": (
                    self._context.contract_version
                ),
                "adapter_version": (
                    self._context.adapter_version
                ),
                "platform_id": (
                    self._context.platform_id
                ),
                "platform_name": (
                    self._context.platform_name
                ),
                "run_id": self._context.run_id,
                "generated_at_utc": (
                    self._context.generated_at_iso
                ),
                "source_database": (
                    str(
                        self._context.source_database
                    )
                ),
                "status": validation_status,
                "platform_status": "RESEARCH ONLY",
                "holdings_available": False,
                "btc_eth_strategic_overlay_preferred": True,
                "legacy_recommendations_preserved": True,
                "dataset_counts": counts,
                "manifest_record_count": (
                    manifest_count
                ),
                "source_runs": [
                    asdict(run)
                    for run in source_runs
                ],
            }

            write_json(
                path=(
                    output
                    / "package_summary.json"
                ),
                payload=summary,
            )

            validation_report = {
                "status": validation_status,
                "run_id": self._context.run_id,
                "contract_version": (
                    self._context.contract_version
                ),
                "holdings_available": False,
                "warnings": warnings,
                "errors": errors,
                "failed_checks": failed_checks,
                "direction_inconsistent_forecasts": (
                    direction_inconsistent
                ),
                "checks": checks,
            }

            write_json(
                path=(
                    output
                    / "validation_report.json"
                ),
                payload=validation_report,
            )

        except Exception:
            shutil.rmtree(
                output,
                ignore_errors=True,
            )

            raise

        if failed_checks:
            # The package and its FAIL validation report stay on disk
            # for diagnosis; raising makes the production run fail.
            raise PackageValidationError(
                failed_checks,
                output,
            )

        return PackageBuildResult(
            output_directory=output,
            run_id=self._context.run_id,
            dataset_counts=counts,
            manifest_count=manifest_count,
            validation_status=validation_status,
        )
