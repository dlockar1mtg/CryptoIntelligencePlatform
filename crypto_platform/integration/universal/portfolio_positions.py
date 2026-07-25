"""Universal portfolio-position export support."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime


PORTFOLIO_POSITION_COLUMNS = [
    "contract_version",
    "portfolio_id",
    "universal_asset_id",
    "as_of_date",
    "quantity",
    "unit_value",
    "position_value",
    "cost_basis",
    "unrealized_gain_loss",
    "current_weight",
    "target_weight",
    "minimum_weight",
    "maximum_weight",
    "monthly_allocation_amount",
    "source_platform",
    "last_updated_at_utc",
]


@dataclass(frozen=True)
class UniversalPortfolioPositionRecord:
    contract_version: str
    portfolio_id: str
    universal_asset_id: str
    as_of_date: date
    quantity: float | None
    unit_value: float | None
    position_value: float
    cost_basis: float | None
    unrealized_gain_loss: float | None
    current_weight: float
    target_weight: float | None
    minimum_weight: float | None
    maximum_weight: float | None
    monthly_allocation_amount: float | None
    source_platform: str | None
    last_updated_at_utc: datetime

    def to_dict(
        self,
    ) -> dict[str, object]:
        return asdict(self)


def build_empty_portfolio_positions(
) -> list[UniversalPortfolioPositionRecord]:
    """Return no positions when holdings were not supplied."""

    return []
