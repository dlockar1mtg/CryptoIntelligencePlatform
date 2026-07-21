"""Typed source records used by the universal adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class SourceRun:
    module_number: int
    table_name: str
    run_id: str
    status: str
    started_at_utc: datetime | None
    completed_at_utc: datetime | None
    platform_version: str | None


@dataclass(frozen=True)
class SourceAsset:
    asset_id: str
    symbol: str | None
    asset_name: str
    asset_tier: str | None
    portfolio_enabled: bool
    research_enabled: bool
    native_chain: str | None
    active: bool
    coingecko_id: str | None
    first_available_date: date | None
    last_updated_at_utc: datetime