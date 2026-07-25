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

    @property
    def runnable(self) -> bool:
        return self.status == "active" and bool(self.runner)

    def runner_path(self, repository_root: Path) -> Path | None:
        if self.runner is None:
            return None
        return repository_root / self.runner


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

    return errors
