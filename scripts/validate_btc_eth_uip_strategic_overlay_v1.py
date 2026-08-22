from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def false_value(value: str) -> bool:
    return value.strip().lower() in {"false", "0"}


def blank_value(value: str) -> bool:
    return value.strip() == ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    database = Path(args.database).resolve()
    output_dir = Path(args.output_dir).resolve()

    require(database.is_file(), "Canonical Crypto database is missing")
    if output_dir.exists():
        require(not any(output_dir.iterdir()), "Validation output directory must be absent or empty")

    sys.path.insert(0, str(repo_root))

    from crypto_platform.integration.universal import (  # noqa: PLC0415
        ADAPTER_VERSION,
        CONTRACT_VERSION,
        ExportContext,
        UniversalPackageBuilder,
    )

    require(ADAPTER_VERSION == "1.1.0", "Unexpected Crypto adapter version")
    require(CONTRACT_VERSION == "1.0.0", "Unexpected universal contract version")

    database_hash_before = sha256(database)

    context = ExportContext.create(
        source_database=database,
        output_directory=output_dir,
        run_id="BTC_ETH_STRATEGIC_OVERLAY_VALIDATION_V1",
    )
    result = UniversalPackageBuilder(context).build()

    require(result.validation_status == "PASS", "Universal package builder did not pass")
    require(result.dataset_counts.get("btc_eth_strategic_overlay") == 2, "Strategic overlay count is not exactly two")

    overlay_path = output_dir / "btc_eth_strategic_overlay.csv"
    recommendations_path = output_dir / "recommendations.csv"
    manifest_path = output_dir / "export_manifest.csv"
    summary_path = output_dir / "package_summary.json"
    validation_path = output_dir / "validation_report.json"

    for path in (
        overlay_path,
        recommendations_path,
        manifest_path,
        summary_path,
        validation_path,
    ):
        require(path.is_file(), f"Expected UIP export file missing: {path.name}")

    rows = read_csv(overlay_path)
    require(len(rows) == 2, "Strategic overlay must contain exactly two rows")

    by_asset = {row["universal_asset_id"]: row for row in rows}
    require(len(by_asset) == 2, "Strategic overlay contains duplicate asset rows")

    bitcoin_key = next((key for key in by_asset if key.endswith("bitcoin")), None)
    ethereum_key = next((key for key in by_asset if key.endswith("ethereum")), None)
    require(bitcoin_key is not None, "Bitcoin strategic overlay row missing")
    require(ethereum_key is not None, "Ethereum strategic overlay row missing")

    bitcoin = by_asset[bitcoin_key]
    ethereum = by_asset[ethereum_key]

    require(bitcoin["asset_role"] == "PRIMARY_LONG_DURATION_CRYPTO_ASSET", "Bitcoin asset role mismatch")
    require(ethereum["asset_role"] == "SECONDARY_LONG_DURATION_CRYPTO_ASSET", "Ethereum asset role mismatch")

    for row in (bitcoin, ethereum):
        require(row["strategic_state"] == "INSUFFICIENT_EVIDENCE", "Unexpected strategic state")
        require(row["tactical_new_capital_state"] == "INSUFFICIENT_EVIDENCE", "Unexpected tactical state")
        require(row["existing_position_state"] == "INSUFFICIENT_EVIDENCE", "Unexpected existing-position state")
        require(row["evidence_status"] == "INSUFFICIENT_EVIDENCE", "Unexpected evidence status")
        require(false_value(row["module42_final_authority"]), "Module42 became final BTC/ETH authority")
        require(false_value(row["bitcoin_calendar_only_action_authorized"]), "Calendar-only Bitcoin action was authorized")
        require(false_value(row["btc_eth_recommendation_policy_skill_certified"]), "BTC/ETH policy skill was unexpectedly certified")
        require(false_value(row["production_policy_change_authorized"]), "Production policy change was unexpectedly authorized")
        require(false_value(row["autonomous_execution_authorized"]), "Autonomous execution was unexpectedly authorized")
        require(blank_value(row["target_weight"]), "Strategic overlay invented a target weight")
        require(len(row["source_observation_sha256"]) == 64, "Source observation SHA is missing")

    require(bitcoin["bitcoin_cycle_context_role"] == "DIRECT_BITCOIN_STRATEGIC_CONTEXT", "Bitcoin cycle role mismatch")
    require(
        ethereum["bitcoin_cycle_context_role"] == "CROSS_MARKET_CONTEXT_ONLY_NOT_ETH_ACTION_RULE",
        "Ethereum Bitcoin-cycle context role mismatch",
    )

    require(bitcoin["observation_id"] == "btc-prospective-ae5efdd0b4cb150f", "Unexpected Bitcoin observation id")
    require(ethereum["observation_id"] == "eth-prospective-4abf754f4b730bf4", "Unexpected Ethereum observation id")
    require(bitcoin["source_observation_sha256"] == "b43aaba705282e7b1ee630604623e2bd9bf1e582848270e085ed38cf3347725f", "Unexpected Bitcoin observation SHA")
    require(ethereum["source_observation_sha256"] == "99d2a4cad4a0faa8085f0b43968aca3a2c29d252a067bb32c6a5a9740f004986", "Unexpected Ethereum observation SHA")

    recommendation_rows = read_csv(recommendations_path)
    require(len(recommendation_rows) > 0, "Legacy recommendations dataset was removed")

    manifest_rows = read_csv(manifest_path)
    manifest_names = {row["dataset_name"] for row in manifest_rows}
    require("recommendations" in manifest_names, "Legacy recommendations missing from export manifest")
    require("btc_eth_strategic_overlay" in manifest_names, "Strategic overlay missing from export manifest")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    require(summary.get("adapter_version") == "1.1.0", "Package summary adapter version mismatch")
    require(summary.get("btc_eth_strategic_overlay_preferred") is True, "Package summary does not prefer BTC/ETH strategic overlay")
    require(summary.get("legacy_recommendations_preserved") is True, "Package summary does not preserve legacy recommendations")
    require(summary.get("dataset_counts", {}).get("btc_eth_strategic_overlay") == 2, "Package summary overlay count mismatch")

    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    checks = validation.get("checks", {})
    require(checks.get("btc_eth_strategic_overlay_exactly_two") is True, "Package validation did not confirm two strategic overlay rows")
    require(checks.get("btc_eth_strategic_overlay_preferred") is True, "Package validation did not prefer strategic overlay")
    require(checks.get("legacy_recommendations_preserved") is True, "Package validation did not preserve legacy recommendations")
    require(checks.get("source_database_read_only") is True, "Package validation lost read-only database guarantee")

    database_hash_after = sha256(database)
    require(database_hash_after == database_hash_before, "Canonical Crypto database changed during overlay validation")

    print("BTC_ETH_UIP_STRATEGIC_OVERLAY_V1_RUNTIME_VALIDATION=PASS")
    print(f"ADAPTER_VERSION={ADAPTER_VERSION}")
    print(f"CONTRACT_VERSION={CONTRACT_VERSION}")
    print("OVERLAY_RECORD_COUNT=2")
    print("BTC_ASSET_ROLE=PRIMARY_LONG_DURATION_CRYPTO_ASSET")
    print("ETH_ASSET_ROLE=SECONDARY_LONG_DURATION_CRYPTO_ASSET")
    print("BTC_CYCLE_ROLE=DIRECT_BITCOIN_STRATEGIC_CONTEXT")
    print("ETH_BTC_CYCLE_ROLE=CROSS_MARKET_CONTEXT_ONLY_NOT_ETH_ACTION_RULE")
    print("MODULE42_BTC_ETH_FINAL_AUTHORITY=FALSE")
    print("LEGACY_RECOMMENDATIONS_PRESERVED=TRUE")
    print("TARGET_WEIGHTS_INVENTED=FALSE")
    print("BTC_ETH_RECOMMENDATION_POLICY_SKILL_CERTIFIED=FALSE")
    print("PRODUCTION_POLICY_CHANGED=FALSE")
    print("AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE")
    print(f"CANONICAL_DATABASE_SHA256={database_hash_after}")
    print("CANONICAL_DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=VALIDATE_BTC_ETH_STRATEGIC_ALIGNMENT_CLOSEOUT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
