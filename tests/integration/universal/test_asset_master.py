from __future__ import annotations

from datetime import (
    date,
    datetime,
    timezone,
)
from pathlib import Path

from crypto_platform.integration.universal import (
    ExportContext,
    SourceAsset,
    build_asset_master,
    transform_asset,
)


def test_transform_asset() -> None:
    context = ExportContext.create(
        source_database=Path(
            "source.duckdb"
        ),
        output_directory=Path(
            "output"
        ),
        run_id="adapter-run-001",
        generated_at_utc=datetime(
            2026,
            7,
            21,
            12,
            0,
            tzinfo=timezone.utc,
        ),
    )

    source = SourceAsset(
        asset_id="bitcoin",
        symbol="btc",
        asset_name="Bitcoin",
        asset_tier="core",
        portfolio_enabled=True,
        research_enabled=True,
        native_chain="bitcoin",
        active=True,
        coingecko_id="bitcoin",
        first_available_date=date(
            2013,
            4,
            28,
        ),
        last_updated_at_utc=datetime(
            2026,
            7,
            16,
            18,
            6,
            30,
            tzinfo=timezone.utc,
        ),
    )

    record = transform_asset(
        source,
        context,
    )

    assert (
        record.contract_version
        == "1.0.0"
    )

    assert record.platform_id == "crypto"
    assert record.run_id == "adapter-run-001"

    assert (
        record.universal_asset_id
        == "crypto:bitcoin"
    )

    assert record.platform_asset_id == "bitcoin"
    assert record.asset_symbol == "BTC"
    assert record.asset_class == "crypto"

    assert (
        record.asset_subclass
        == "large_cap_crypto"
    )

    assert record.investable is True
    assert record.liquidity_tier == "high"
    assert record.data_source == "CoinGecko"


def test_build_asset_master_is_sorted() -> None:
    context = ExportContext.create(
        source_database=Path(
            "source.duckdb"
        ),
        output_directory=Path(
            "output"
        ),
        run_id="adapter-run-001",
        generated_at_utc=datetime(
            2026,
            7,
            21,
            tzinfo=timezone.utc,
        ),
    )

    updated = datetime(
        2026,
        7,
        16,
        tzinfo=timezone.utc,
    )

    records = build_asset_master(
        [
            SourceAsset(
                asset_id="ethereum",
                symbol="ETH",
                asset_name="Ethereum",
                asset_tier="core",
                portfolio_enabled=True,
                research_enabled=True,
                native_chain="ethereum",
                active=True,
                coingecko_id="ethereum",
                first_available_date=None,
                last_updated_at_utc=updated,
            ),
            SourceAsset(
                asset_id="bitcoin",
                symbol="BTC",
                asset_name="Bitcoin",
                asset_tier="core",
                portfolio_enabled=True,
                research_enabled=True,
                native_chain="bitcoin",
                active=True,
                coingecko_id="bitcoin",
                first_available_date=None,
                last_updated_at_utc=updated,
            ),
        ],
        context,
    )

    assert [
        item.universal_asset_id
        for item in records
    ] == [
        "crypto:bitcoin",
        "crypto:ethereum",
    ]