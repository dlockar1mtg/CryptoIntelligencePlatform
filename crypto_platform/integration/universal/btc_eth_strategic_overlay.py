"""BTC/ETH long-duration strategic overlay for UIP exports."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
import hashlib
import json
from pathlib import Path

from .analytics_models import SourceRecommendation
from .context import ExportContext
from .normalization import universal_crypto_asset_id


BTC_ETH_STRATEGIC_OVERLAY_COLUMNS = [
    "contract_version",
    "platform_id",
    "run_id",
    "universal_asset_id",
    "asset_role",
    "observation_id",
    "observation_timestamp",
    "operating_date",
    "observed_price_usd",
    "strategic_state",
    "tactical_new_capital_state",
    "existing_position_state",
    "evidence_status",
    "module42_context_available",
    "module42_native_action",
    "module42_recommendation_date",
    "module42_native_investment_score",
    "module42_final_authority",
    "bitcoin_cycle_context_role",
    "bitcoin_cycle_descriptive_phase",
    "bitcoin_days_since_halving",
    "most_recent_bitcoin_halving_date",
    "bitcoin_calendar_only_action_authorized",
    "btc_eth_recommendation_policy_skill_certified",
    "production_policy_change_authorized",
    "autonomous_execution_authorized",
    "target_weight",
    "source_observation_sha256",
    "generated_at_utc",
]


@dataclass(frozen=True)
class BtcEthStrategicOverlayRecord:
    contract_version: str
    platform_id: str
    run_id: str
    universal_asset_id: str
    asset_role: str
    observation_id: str
    observation_timestamp: str
    operating_date: object
    observed_price_usd: float
    strategic_state: str
    tactical_new_capital_state: str
    existing_position_state: str
    evidence_status: str
    module42_context_available: bool
    module42_native_action: str | None
    module42_recommendation_date: object | None
    module42_native_investment_score: float | None
    module42_final_authority: bool
    bitcoin_cycle_context_role: str
    bitcoin_cycle_descriptive_phase: str | None
    bitcoin_days_since_halving: int | None
    most_recent_bitcoin_halving_date: object | None
    bitcoin_calendar_only_action_authorized: bool
    btc_eth_recommendation_policy_skill_certified: bool
    production_policy_change_authorized: bool
    autonomous_execution_authorized: bool
    target_weight: float | None
    source_observation_sha256: str
    generated_at_utc: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_root(context: ExportContext) -> Path:
    database = context.source_database.resolve()
    if database.name != "crypto_intelligence.duckdb":
        raise ValueError("Unexpected Crypto source database name.")
    if database.parent.name != "data":
        raise ValueError("Crypto source database is not under repository data/.")
    return database.parent.parent


def _observation_from_manifest(
    repo_root: Path,
    manifest_relative: str,
) -> tuple[dict[str, object], str]:
    manifest_path = repo_root / manifest_relative
    manifest = _read_json(manifest_path)

    if int(manifest.get("record_count", 0)) < 1:
        raise ValueError(f"Prospective ledger has no observations: {manifest_relative}")

    observation_relative = (
        manifest.get("last_observation_file")
        or manifest.get("first_observation_file")
    )
    if not observation_relative:
        raise ValueError(f"Prospective manifest has no observation path: {manifest_relative}")

    observation_path = repo_root / str(observation_relative)
    if not observation_path.is_file():
        raise FileNotFoundError(observation_path)

    actual_hash = _sha256(observation_path)
    expected_hash = str(
        manifest.get("last_observation_sha256")
        or manifest.get("first_observation_sha256")
        or ""
    ).lower()
    if actual_hash != expected_hash:
        raise ValueError(f"Prospective observation hash mismatch: {observation_relative}")

    return _read_json(observation_path), actual_hash


def _native_context(
    asset_id: str,
    native_recommendations: list[SourceRecommendation],
) -> SourceRecommendation | None:
    matches = [item for item in native_recommendations if item.asset_id == asset_id]
    if len(matches) > 1:
        raise ValueError(f"Multiple native recommendations found for {asset_id}.")
    return matches[0] if matches else None


def _date_or_none(value: object) -> object | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value
    return str(value)


def _bitcoin_record(
    observation: dict[str, object],
    observation_hash: str,
    native: SourceRecommendation | None,
    context: ExportContext,
) -> BtcEthStrategicOverlayRecord:
    decisions = dict(observation["decision_layers"])
    cycle = dict(observation["cycle_context"])
    policy = dict(observation["policy_authority"])
    price = dict(observation["observed_bitcoin_price"])

    return BtcEthStrategicOverlayRecord(
        contract_version=context.contract_version,
        platform_id=context.platform_id,
        run_id=context.run_id,
        universal_asset_id=universal_crypto_asset_id("bitcoin"),
        asset_role="PRIMARY_LONG_DURATION_CRYPTO_ASSET",
        observation_id=str(observation["observation_id"]),
        observation_timestamp=str(observation["observation_timestamp"]),
        operating_date=observation["operating_date"],
        observed_price_usd=float(price["price_usd"]),
        strategic_state=str(decisions["strategic_state"]),
        tactical_new_capital_state=str(decisions["tactical_new_capital_state"]),
        existing_position_state=str(decisions["existing_position_state"]),
        evidence_status="INSUFFICIENT_EVIDENCE",
        module42_context_available=(native is not None),
        module42_native_action=(None if native is None else native.best_action),
        module42_recommendation_date=(None if native is None else native.recommendation_date),
        module42_native_investment_score=(None if native is None else native.investment_score),
        module42_final_authority=False,
        bitcoin_cycle_context_role="DIRECT_BITCOIN_STRATEGIC_CONTEXT",
        bitcoin_cycle_descriptive_phase=(None if cycle.get("descriptive_phase") is None else str(cycle["descriptive_phase"])),
        bitcoin_days_since_halving=(None if cycle.get("days_since_halving") is None else int(cycle["days_since_halving"])),
        most_recent_bitcoin_halving_date=_date_or_none(cycle.get("most_recent_halving_date")),
        bitcoin_calendar_only_action_authorized=bool(cycle.get("calendar_only_action_authorized", False)),
        btc_eth_recommendation_policy_skill_certified=False,
        production_policy_change_authorized=bool(policy.get("production_policy_change_authorized", False)),
        autonomous_execution_authorized=bool(policy.get("autonomous_execution_authorized", False)),
        target_weight=None,
        source_observation_sha256=observation_hash,
        generated_at_utc=context.generated_at_iso,
    )


def _ethereum_record(
    observation: dict[str, object],
    observation_hash: str,
    native: SourceRecommendation | None,
    context: ExportContext,
) -> BtcEthStrategicOverlayRecord:
    decisions = dict(observation["decision_layers"])
    cycle = dict(observation["bitcoin_cycle_context"])
    policy = dict(observation["policy_authority"])
    price = dict(observation["observed_ethereum_price"])

    return BtcEthStrategicOverlayRecord(
        contract_version=context.contract_version,
        platform_id=context.platform_id,
        run_id=context.run_id,
        universal_asset_id=universal_crypto_asset_id("ethereum"),
        asset_role="SECONDARY_LONG_DURATION_CRYPTO_ASSET",
        observation_id=str(observation["observation_id"]),
        observation_timestamp=str(observation["observation_timestamp"]),
        operating_date=observation["operating_date"],
        observed_price_usd=float(price["price_usd"]),
        strategic_state=str(decisions["strategic_state"]),
        tactical_new_capital_state=str(decisions["tactical_new_capital_state"]),
        existing_position_state=str(decisions["existing_position_state"]),
        evidence_status="INSUFFICIENT_EVIDENCE",
        module42_context_available=(native is not None),
        module42_native_action=(None if native is None else native.best_action),
        module42_recommendation_date=(None if native is None else native.recommendation_date),
        module42_native_investment_score=(None if native is None else native.investment_score),
        module42_final_authority=False,
        bitcoin_cycle_context_role=str(cycle["context_role"]),
        bitcoin_cycle_descriptive_phase=(None if cycle.get("bitcoin_descriptive_phase") is None else str(cycle["bitcoin_descriptive_phase"])),
        bitcoin_days_since_halving=(None if cycle.get("bitcoin_days_since_halving_at_btc_observation") is None else int(cycle["bitcoin_days_since_halving_at_btc_observation"])),
        most_recent_bitcoin_halving_date=_date_or_none(cycle.get("most_recent_bitcoin_halving_date")),
        bitcoin_calendar_only_action_authorized=bool(cycle.get("bitcoin_calendar_only_action_authorized", False)),
        btc_eth_recommendation_policy_skill_certified=bool(policy.get("btc_eth_recommendation_policy_skill_certified", False)),
        production_policy_change_authorized=bool(policy.get("production_policy_change_authorized", False)),
        autonomous_execution_authorized=bool(policy.get("autonomous_execution_authorized", False)),
        target_weight=None,
        source_observation_sha256=observation_hash,
        generated_at_utc=context.generated_at_iso,
    )


def build_btc_eth_strategic_overlay(
    native_recommendations: list[SourceRecommendation],
    context: ExportContext,
) -> list[BtcEthStrategicOverlayRecord]:
    repo_root = _repo_root(context)

    bitcoin, bitcoin_hash = _observation_from_manifest(
        repo_root,
        "data/research/bitcoin_strategic_regime_forward_evidence_v1/manifest.json",
    )
    ethereum, ethereum_hash = _observation_from_manifest(
        repo_root,
        "data/research/ethereum_strategic_regime_forward_evidence_v1/manifest.json",
    )

    records = [
        _bitcoin_record(
            bitcoin,
            bitcoin_hash,
            _native_context("bitcoin", native_recommendations),
            context,
        ),
        _ethereum_record(
            ethereum,
            ethereum_hash,
            _native_context("ethereum", native_recommendations),
            context,
        ),
    ]

    if {record.asset_role for record in records} != {
        "PRIMARY_LONG_DURATION_CRYPTO_ASSET",
        "SECONDARY_LONG_DURATION_CRYPTO_ASSET",
    }:
        raise ValueError("BTC/ETH strategic asset roles are incomplete.")

    for record in records:
        if record.module42_final_authority:
            raise ValueError("Module42 cannot be final BTC/ETH overlay authority.")
        if record.target_weight is not None:
            raise ValueError("BTC/ETH overlay may not invent target weights.")
        if record.production_policy_change_authorized:
            raise ValueError("BTC/ETH overlay may not authorize production policy changes.")
        if record.autonomous_execution_authorized:
            raise ValueError("BTC/ETH overlay may not authorize autonomous execution.")
        if record.btc_eth_recommendation_policy_skill_certified:
            raise ValueError("BTC/ETH recommendation policy skill is not certified.")

    return records
