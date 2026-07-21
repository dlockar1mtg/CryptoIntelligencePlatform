"""Universal asset-master transformation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

from .context import ExportContext
from .normalization import (
    normalize_asset_subclass,
    normalize_liquidity_tier,
    normalize_platform_asset_id,
    universal_crypto_asset_id,
)
from .source_models import SourceAsset


ASSET_MASTER_COLUMNS = [
    "contract_version",
    "platform_id",
    "run_id",
    "universal_asset_id",
    "platform_asset_id",
    "asset_name",
    "asset_symbol",
    "asset_class",
    "asset_subclass",
    "currency",
    "market_or_region",
    "is_active",
    "investable",
    "liquidity_tier",
    "data_source",
    "first_available_date",
    "last_updated_at_utc",
]


@dataclass(frozen=True)
class UniversalAssetRecord:
    contract_version: str
    platform_id: str
    run_id: str
    universal_asset_id: str
    platform_asset_id: str
    asset_name: str
    asset_symbol: str | None
    asset_class: str
    asset_subclass: str
    currency: str
    market_or_region: str
    is_active: bool
    investable: bool
    liquidity_tier: str
    data_source: str
    first_available_date: date | None
    last_updated_at_utc: str

    def to_dict(
        self,
    ) -> dict[str, object]:
        return asdict(self)


def transform_asset(
    source: SourceAsset,
    context: ExportContext,
) -> UniversalAssetRecord:
    platform_asset_id = (
        normalize_platform_asset_id(
            source.asset_id
        )
    )

    source_name = (
        "CoinGecko"
        if source.coingecko_id
        else "Crypto Intelligence Platform"
    )

    return UniversalAssetRecord(
        contract_version=context.contract_version,
        platform_id=context.platform_id,
        run_id=context.run_id,
        universal_asset_id=(
            universal_crypto_asset_id(
                platform_asset_id
            )
        ),
        platform_asset_id=platform_asset_id,
        asset_name=source.asset_name.strip(),
        asset_symbol=(
            None
            if source.symbol is None
            else source.symbol.strip().upper()
        ),
        asset_class="crypto",
        asset_subclass=(
            normalize_asset_subclass(
                source.asset_tier
            )
        ),
        currency="USD",
        market_or_region="global",
        is_active=source.active,
        investable=source.portfolio_enabled,
        liquidity_tier=(
            normalize_liquidity_tier(
                source.asset_tier
            )
        ),
        data_source=source_name,
        first_available_date=(
            source.first_available_date
        ),
        last_updated_at_utc=(
            source.last_updated_at_utc
            .isoformat()
        ),
    )


def build_asset_master(
    source_assets: list[SourceAsset],
    context: ExportContext,
) -> list[UniversalAssetRecord]:
    records = [
        transform_asset(
            source,
            context,
        )
        for source in source_assets
    ]

    records.sort(
        key=lambda record: (
            record.universal_asset_id
        )
    )

    identifiers = [
        record.universal_asset_id
        for record in records
    ]

    if len(identifiers) != len(
        set(identifiers)
    ):
        raise ValueError(
            "Duplicate universal asset IDs detected."
        )

    return records