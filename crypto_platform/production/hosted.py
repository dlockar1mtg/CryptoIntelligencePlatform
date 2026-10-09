"""Hosted-operation validation and UIP delivery preparation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

import duckdb


ONLINE_PROVIDER_STATES = {"ONLINE", "AVAILABLE", "HEALTHY", "PASS"}

CRYPTO_CURRENT_PRICE_AUTHORITY_ID = "CRYPTO_CANONICAL_MARKET_DAILY_CURRENT_PRICE_V1"
CRYPTO_CURRENT_PRICE_SCHEMA_VERSION = "1.0.0"
CRYPTO_CURRENT_PRICE_METHODOLOGY_VERSION = "1.0.0"
CRYPTO_CURRENT_PRICE_SEMANTICS = "DAILY_CANONICAL_MARKET_CLOSE"
CRYPTO_CURRENT_PRICE_PRESENTATION_SEMANTICS = (
    "CURRENT_PRICE_FOR_PORTFOLIO_VALUATION_NOT_EXECUTION_QUOTE"
)
CRYPTO_CURRENT_PRICE_ASSETS = (
    "bitcoin",
    "ethereum",
    "solana",
    "chainlink",
    "xrp",
    "avalanche",
)
# A coin whose latest canonical daily price is older than this many days is left
# out of the current-price sidecar (with the reason recorded in its manifest).
CRYPTO_CURRENT_PRICE_MAX_AGE_DAYS = 3
# If any of these is older than the limit, the sidecar build fails instead.
CRYPTO_CURRENT_PRICE_REQUIRED_FRESH_ASSETS = ("bitcoin", "ethereum")


@dataclass(frozen=True)
class HostedThresholds:
    daily_market_max_age_hours: float = 72.0
    macro_max_age_days: float = 60.0
    collection_max_age_hours: float = 72.0
    max_failed_collectors: int = 0


@dataclass(frozen=True)
class HostedCheck:
    name: str
    status: str
    details: dict[str, Any]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _age_hours(value: Any) -> float | None:
    parsed = _as_utc_datetime(value)
    if parsed is None:
        return None
    return max(0.0, (_utc_now() - parsed.astimezone(timezone.utc)).total_seconds() / 3600.0)


def _table_exists(connection: duckdb.DuckDBPyConnection, name: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [name],
    ).fetchone()
    return bool(row and row[0])


def evaluate_hosted_database(
    database_path: Path,
    thresholds: HostedThresholds | None = None,
) -> dict[str, Any]:
    """Evaluate whether a Crypto DuckDB is safe to persist and deliver."""

    limits = thresholds or HostedThresholds()
    path = database_path.resolve()
    checks: list[HostedCheck] = []

    if not path.is_file():
        return {
            "status": "FAIL",
            "database_path": str(path),
            "checked_at_utc": _utc_now().isoformat().replace("+00:00", "Z"),
            "checks": [
                asdict(HostedCheck("database_exists", "FAIL", {"path": str(path)}))
            ],
        }

    checks.append(
        HostedCheck(
            "database_exists",
            "PASS",
            {"path": str(path), "size_bytes": path.stat().st_size},
        )
    )

    connection = duckdb.connect(str(path), read_only=True)
    try:
        required_tables = {
            "collection_runs",
            "provider_health",
            "asset_market_daily",
            "macro_observations",
        }
        missing = sorted(name for name in required_tables if not _table_exists(connection, name))
        checks.append(
            HostedCheck(
                "required_tables",
                "PASS" if not missing else "FAIL",
                {"missing": missing},
            )
        )

        if not missing:
            collection = connection.execute(
                """
                SELECT run_id, completed_at_utc, status,
                       COALESCE(successful_collectors, 0),
                       COALESCE(failed_collectors, 0)
                FROM collection_runs
                ORDER BY completed_at_utc DESC NULLS LAST
                LIMIT 1
                """
            ).fetchone()
            if collection is None:
                checks.append(HostedCheck("latest_collection", "FAIL", {"reason": "No collection run."}))
            else:
                age = _age_hours(collection[1])
                collection_ok = (
                    str(collection[2]).upper() in {"PASS", "SUCCESS", "COMPLETED"}
                    and int(collection[4]) <= limits.max_failed_collectors
                    and age is not None
                    and age <= limits.collection_max_age_hours
                )
                checks.append(
                    HostedCheck(
                        "latest_collection",
                        "PASS" if collection_ok else "FAIL",
                        {
                            "run_id": collection[0],
                            "completed_at_utc": str(collection[1]),
                            "age_hours": None if age is None else round(age, 3),
                            "status": collection[2],
                            "successful_collectors": int(collection[3]),
                            "failed_collectors": int(collection[4]),
                            "maximum_age_hours": limits.collection_max_age_hours,
                        },
                    )
                )

            providers = connection.execute(
                """
                SELECT provider_name, provider_group, status, checked_at_utc,
                       COALESCE(consecutive_failures, 0), error_message
                FROM latest_provider_health
                ORDER BY provider_name, provider_group
                """
            ).fetchall()
            unhealthy = [
                {
                    "provider_name": row[0],
                    "provider_group": row[1],
                    "status": row[2],
                    "checked_at_utc": str(row[3]),
                    "consecutive_failures": int(row[4]),
                    "error_message": row[5] or "",
                }
                for row in providers
                if str(row[2]).upper() not in ONLINE_PROVIDER_STATES
            ]
            checks.append(
                HostedCheck(
                    "provider_health",
                    "PASS" if providers and not unhealthy else "FAIL",
                    {"provider_count": len(providers), "unhealthy": unhealthy},
                )
            )

            market_date = connection.execute(
                "SELECT MAX(observation_date) FROM asset_market_daily"
            ).fetchone()[0]
            market_age = _age_hours(market_date)
            checks.append(
                HostedCheck(
                    "daily_market_freshness",
                    "PASS"
                    if market_age is not None and market_age <= limits.daily_market_max_age_hours
                    else "FAIL",
                    {
                        "latest_observation": str(market_date),
                        "age_hours": None if market_age is None else round(market_age, 3),
                        "maximum_age_hours": limits.daily_market_max_age_hours,
                    },
                )
            )

            macro_date = connection.execute(
                "SELECT MAX(observation_date) FROM macro_observations"
            ).fetchone()[0]
            macro_age_hours = _age_hours(macro_date)
            macro_age_days = None if macro_age_hours is None else macro_age_hours / 24.0
            checks.append(
                HostedCheck(
                    "macro_freshness",
                    "PASS"
                    if macro_age_days is not None and macro_age_days <= limits.macro_max_age_days
                    else "FAIL",
                    {
                        "latest_observation": str(macro_date),
                        "age_days": None if macro_age_days is None else round(macro_age_days, 3),
                        "maximum_age_days": limits.macro_max_age_days,
                    },
                )
            )
    finally:
        connection.close()

    status = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {
        "status": status,
        "database_path": str(path),
        "checked_at_utc": _utc_now().isoformat().replace("+00:00", "Z"),
        "thresholds": asdict(limits),
        "checks": [asdict(check) for check in checks],
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_crypto_current_price_sidecar(
    database_path: Path,
    output_csv: Path,
    output_manifest: Path,
) -> dict[str, Any]:
    """Export one governed latest daily price for each supported Crypto asset."""

    database = database_path.resolve()
    if not database.is_file():
        raise FileNotFoundError(f"Crypto database not found: {database}")

    connection = duckdb.connect(str(database), read_only=True)
    try:
        if not _table_exists(connection, "canonical_market_daily"):
            raise ValueError("canonical_market_daily is missing from the Crypto database.")
        placeholders = ", ".join("?" for _ in CRYPTO_CURRENT_PRICE_ASSETS)
        rows = connection.execute(
            f"""
            WITH ranked AS (
                SELECT
                    asset_id,
                    observation_date,
                    price_usd,
                    price_source,
                    source_priority,
                    collected_at_utc,
                    ROW_NUMBER() OVER (
                        PARTITION BY asset_id
                        ORDER BY observation_date DESC
                    ) AS rn
                FROM canonical_market_daily
                WHERE asset_id IN ({placeholders})
                  AND price_usd IS NOT NULL
            )
            SELECT
                asset_id,
                observation_date,
                price_usd,
                price_source,
                source_priority,
                collected_at_utc
            FROM ranked
            WHERE rn = 1
            ORDER BY asset_id
            """,
            list(CRYPTO_CURRENT_PRICE_ASSETS),
        ).fetchall()
    finally:
        connection.close()

    by_asset = {str(row[0]): row for row in rows}
    if set(by_asset) != set(CRYPTO_CURRENT_PRICE_ASSETS):
        missing = sorted(set(CRYPTO_CURRENT_PRICE_ASSETS) - set(by_asset))
        extra = sorted(set(by_asset) - set(CRYPTO_CURRENT_PRICE_ASSETS))
        raise ValueError(
            f"Crypto current-price authority asset set mismatch; missing={missing}, extra={extra}"
        )

    today = _utc_now().date()
    excluded_assets: list[dict[str, object]] = []
    for asset_id in CRYPTO_CURRENT_PRICE_ASSETS:
        observed = _as_utc_datetime(by_asset[asset_id][1])
        age_days = (today - observed.date()).days
        if age_days > CRYPTO_CURRENT_PRICE_MAX_AGE_DAYS:
            excluded_assets.append(
                {
                    "universal_asset_id": f"crypto:{asset_id}",
                    "asset_id": asset_id,
                    "observation_date": str(by_asset[asset_id][1]),
                    "age_days": age_days,
                    "reason": (
                        f"Latest canonical price is {age_days} days old; "
                        f"maximum is {CRYPTO_CURRENT_PRICE_MAX_AGE_DAYS} days."
                    ),
                }
            )
    stale_required = sorted(
        item["asset_id"]
        for item in excluded_assets
        if item["asset_id"] in CRYPTO_CURRENT_PRICE_REQUIRED_FRESH_ASSETS
    )
    if stale_required:
        raise ValueError(
            "Crypto current price is stale for required assets "
            f"{stale_required}: " + "; ".join(
                f"{item['asset_id']} {item['reason']}"
                for item in excluded_assets
                if item["asset_id"] in stale_required
            )
        )
    excluded_ids = {str(item["asset_id"]) for item in excluded_assets}

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = (
        "universal_asset_id",
        "asset_id",
        "observation_date",
        "current_price_usd",
        "price_source",
        "source_priority",
        "collected_at_utc",
        "source_table",
        "authority_id",
        "schema_version",
        "methodology_version",
        "price_semantics",
        "presentation_semantics",
    )
    written_rows: list[dict[str, object]] = []
    for asset_id in CRYPTO_CURRENT_PRICE_ASSETS:
        if asset_id in excluded_ids:
            continue
        row = by_asset[asset_id]
        price = float(row[2])
        if price <= 0:
            raise ValueError(f"Crypto current price must be positive: {asset_id}")
        price_source = str(row[3] or "").strip()
        if not price_source:
            raise ValueError(f"Crypto current price is missing price_source: {asset_id}")
        written_rows.append(
            {
                "universal_asset_id": f"crypto:{asset_id}",
                "asset_id": asset_id,
                "observation_date": str(row[1]),
                "current_price_usd": repr(price),
                "price_source": price_source,
                "source_priority": "" if row[4] is None else str(row[4]),
                "collected_at_utc": "" if row[5] is None else str(row[5]),
                "source_table": "canonical_market_daily",
                "authority_id": CRYPTO_CURRENT_PRICE_AUTHORITY_ID,
                "schema_version": CRYPTO_CURRENT_PRICE_SCHEMA_VERSION,
                "methodology_version": CRYPTO_CURRENT_PRICE_METHODOLOGY_VERSION,
                "price_semantics": CRYPTO_CURRENT_PRICE_SEMANTICS,
                "presentation_semantics": CRYPTO_CURRENT_PRICE_PRESENTATION_SEMANTICS,
            }
        )

    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(written_rows)

    manifest = {
        "status": "CRYPTO_CURRENT_PRICE_V1_PASS",
        "authority_id": CRYPTO_CURRENT_PRICE_AUTHORITY_ID,
        "schema_version": CRYPTO_CURRENT_PRICE_SCHEMA_VERSION,
        "methodology_version": CRYPTO_CURRENT_PRICE_METHODOLOGY_VERSION,
        "scope": "SIX_ASSET_LATEST_DAILY_CANONICAL_MARKET_PRICE",
        "source_table": "canonical_market_daily",
        "row_count": len(written_rows),
        "supported_assets": [f"crypto:{asset}" for asset in CRYPTO_CURRENT_PRICE_ASSETS],
        "price_semantics": CRYPTO_CURRENT_PRICE_SEMANTICS,
        "presentation_semantics": CRYPTO_CURRENT_PRICE_PRESENTATION_SEMANTICS,
        "max_price_age_days": CRYPTO_CURRENT_PRICE_MAX_AGE_DAYS,
        "excluded_assets": excluded_assets,
        "output_sha256": _sha256(output_csv),
        "forecast_input_reused_as_price_authority": False,
        "intraday_quote_claimed": False,
        "execution_authority_granted": False,
    }
    output_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def prepare_uip_delivery(
    run_summary_path: Path,
    output_root: Path,
    database_path: Path | None = None,
) -> dict[str, Any]:
    """Copy a validated universal package into a stable delivery directory."""

    summary_path = run_summary_path.resolve()
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise ValueError("Production run summary is not PASS.")

    export = payload.get("universal_export", {})
    if export.get("status") != "PASS":
        raise ValueError("Universal export is not PASS.")

    package_source = Path(export["output_directory"])
    if not package_source.is_absolute():
        package_source = (summary_path.parent / package_source).resolve()
    if not package_source.is_dir():
        raise FileNotFoundError(f"Universal package not found: {package_source}")

    required = {
        "asset_master.csv",
        "forecasts.csv",
        "platform_status.csv",
        "portfolio_positions.csv",
        "recommendations.csv",
        "risk_metrics.csv",
        "export_manifest.csv",
        "package_summary.json",
        "validation_report.json",
    }
    present = {path.name for path in package_source.iterdir() if path.is_file()}
    missing = sorted(required - present)
    if missing:
        raise ValueError(f"Universal package is incomplete: {missing}")

    run_id = str(payload["run_id"])
    root = output_root.resolve()
    delivery_dir = root / run_id
    if delivery_dir.exists():
        shutil.rmtree(delivery_dir)
    shutil.copytree(package_source, delivery_dir)

    current_price_manifest = None
    if database_path is not None:
        current_price_manifest = build_crypto_current_price_sidecar(
            database_path,
            delivery_dir / "crypto_current_price_v1.csv",
            delivery_dir / "crypto_current_price_v1_manifest.json",
        )

    files = []
    for path in sorted(delivery_dir.iterdir()):
        if path.is_file():
            files.append(
                {
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )

    manifest = {
        "status": "PASS",
        "delivery_contract": "uip-crypto-delivery-v1",
        "run_id": run_id,
        "prepared_at_utc": _utc_now().isoformat().replace("+00:00", "Z"),
        "source_run_summary": str(summary_path),
        "delivery_directory": str(delivery_dir),
        "files": files,
        "crypto_current_price_v1": current_price_manifest,
    }
    manifest_path = delivery_dir / "uip_delivery_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    latest = root / "latest.json"
    latest.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "delivery_directory": str(delivery_dir),
                "manifest": str(manifest_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest
