"""Authoritative production ownership and execution registry."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ProductionStage(str, Enum):
    COLLECTION = "collection"
    CORE_ANALYTICS = "core_analytics"
    FEATURE_RESEARCH = "feature_research"
    REGIME_VALIDATION = "regime_validation"
    DECISION_INTELLIGENCE = "decision_intelligence"
    GOVERNANCE = "governance"
    UNIVERSAL_EXPORT = "universal_export"


@dataclass(frozen=True)
class ModuleSpec:
    number: int
    stage: ProductionStage
    runner: str | None
    status: str = "active"
    authoritative_outputs: tuple[str, ...] = ()
    required: bool = True
    reason: str = ""
    # "daily": on the UIP delivery chain, runs every cycle.
    # "weekly": research only (nothing the UIP delivery reads depends on it), so with the
    # weekly-research option it runs on the Sunday full refresh, or when its last
    # successful run is missing or older than seven days.
    cadence: str = "daily"
    # The module's own run table, used to find its last successful run.
    run_table: str | None = None

    @property
    def weekly(self) -> bool:
        return self.cadence == "weekly"

    @property
    def runnable(self) -> bool:
        return self.status == "active" and bool(self.runner)

    def runner_path(self, repository_root: Path) -> Path | None:
        if self.runner is None:
            return None
        return repository_root / self.runner


# Modules that the UIP delivery does not depend on. Verified from the table reads and
# writes in each module: the delivery reads m36_asset_risk, m39_calibrated_forecasts,
# m42_price_projections, m42_asset_recommendations, the module 36/39/42 run tables,
# assets, asset_market_daily, asset_ohlcv and canonical_market_daily (plus the module 1
# collection and provider-health tables for the hosted readiness check). Those come only
# from modules 1, 6, 17, 25, 27-42. Module 18 writes STABLECOIN_SUPPLY_USD rows into
# external_feature_observations, which module 17 reads, but module 17 only uses the
# FEAR_GREED_INDEX and US_SPOT_CRYPTO_ETF_NET_FLOW_USD keys from that table, so module 18
# does not change crypto_features_daily.
RESEARCH_ONLY_MODULES: frozenset[int] = frozenset(
    {2, 3, 5, *range(7, 17), *range(18, 25), 26, 43, 44}
)

# The modules the UIP delivery depends on, in run order. Every one runs every cycle.
UIP_DELIVERY_MODULES: tuple[int, ...] = (1, 6, 17, 25, *range(27, 43))

_RUN_TABLES: dict[int, str] = {16: "optimization_runs"}


def _module(
    number: int,
    stage: ProductionStage,
    *,
    outputs: tuple[str, ...] = (),
    required: bool = True,
) -> ModuleSpec:
    return ModuleSpec(
        number=number,
        stage=stage,
        runner=f"run_module{number}.py",
        authoritative_outputs=outputs,
        required=required,
        cadence="weekly" if number in RESEARCH_ONLY_MODULES else "daily",
        run_table=_RUN_TABLES.get(number, f"module{number}_runs"),
    )


MODULE_REGISTRY: tuple[ModuleSpec, ...] = (
    _module(1, ProductionStage.COLLECTION, outputs=("provider_collection",)),
    _module(2, ProductionStage.CORE_ANALYTICS, outputs=("asset_scores", "market_regime")),
    _module(3, ProductionStage.CORE_ANALYTICS, outputs=("portfolio_research",), required=False),
    ModuleSpec(
        number=4,
        stage=ProductionStage.CORE_ANALYTICS,
        runner=None,
        status="retired",
        required=False,
        reason=(
            "No implementation or runner exists. The historical numbering gap is "
            "formally retired; downstream production must not depend on Module 4."
        ),
    ),
    *tuple(_module(n, ProductionStage.CORE_ANALYTICS) for n in range(5, 17)),
    *tuple(_module(n, ProductionStage.FEATURE_RESEARCH) for n in range(17, 25)),
    *tuple(_module(n, ProductionStage.REGIME_VALIDATION) for n in range(25, 33)),
    *tuple(_module(n, ProductionStage.DECISION_INTELLIGENCE) for n in range(33, 39)),
    _module(39, ProductionStage.DECISION_INTELLIGENCE, outputs=("calibrated_forecasts",)),
    *tuple(_module(n, ProductionStage.DECISION_INTELLIGENCE) for n in range(40, 42)),
    _module(42, ProductionStage.DECISION_INTELLIGENCE, outputs=("recommendations", "price_projections")),
    _module(43, ProductionStage.GOVERNANCE, outputs=("forward_prediction_registry",)),
    _module(44, ProductionStage.GOVERNANCE, outputs=("economic_value_validation",)),
)


def active_modules() -> tuple[ModuleSpec, ...]:
    return tuple(spec for spec in MODULE_REGISTRY if spec.runnable)


def weekly_modules() -> tuple[ModuleSpec, ...]:
    return tuple(spec for spec in MODULE_REGISTRY if spec.runnable and spec.weekly)


def retired_modules() -> tuple[ModuleSpec, ...]:
    return tuple(spec for spec in MODULE_REGISTRY if spec.status == "retired")


def validate_registry(repository_root: Path) -> list[str]:
    errors: list[str] = []
    numbers = [spec.number for spec in MODULE_REGISTRY]
    if numbers != list(range(1, 45)):
        errors.append("Registry must contain each module number from 1 through 44 exactly once.")

    for spec in active_modules():
        path = spec.runner_path(repository_root)
        if path is None or not path.is_file():
            errors.append(f"Module {spec.number} runner is missing: {path}")

    module4 = MODULE_REGISTRY[3]
    if module4.number != 4 or module4.status != "retired":
        errors.append("Module 4 must remain explicitly retired unless formally implemented.")

    for spec in active_modules():
        if spec.cadence not in {"daily", "weekly"}:
            errors.append(f"Module {spec.number} has an unknown cadence: {spec.cadence}")
    for number in UIP_DELIVERY_MODULES:
        spec = next((item for item in MODULE_REGISTRY if item.number == number), None)
        if spec is None or spec.weekly or not spec.runnable:
            errors.append(f"Module {number} feeds the UIP delivery and must run daily.")

    return errors
