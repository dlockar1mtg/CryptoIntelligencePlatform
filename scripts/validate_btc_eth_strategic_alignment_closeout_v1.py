from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_DB_SHA256 = "0e5745889491c435d884cf7e3c9be080fb708d79dd9ba308f05006bcbb4657e3"
EXPECTED_BTC_ID = "btc-prospective-ae5efdd0b4cb150f"
EXPECTED_BTC_SHA256 = "b43aaba705282e7b1ee630604623e2bd9bf1e582848270e085ed38cf3347725f"
EXPECTED_ETH_ID = "eth-prospective-4abf754f4b730bf4"
EXPECTED_ETH_SHA256 = "99d2a4cad4a0faa8085f0b43968aca3a2c29d252a067bb32c6a5a9740f004986"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--database", required=True)
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    database = Path(args.database).resolve()

    closeout = repo / "docs/btc_eth_strategic_alignment_closeout_v1.md"
    governance = repo / "docs/btc_eth_strategic_alignment_uip_output_governance_v1.md"
    btc_manifest_path = repo / "data/research/bitcoin_strategic_regime_forward_evidence_v1/manifest.json"
    eth_manifest_path = repo / "data/research/ethereum_strategic_regime_forward_evidence_v1/manifest.json"
    overlay_module = repo / "crypto_platform/integration/universal/btc_eth_strategic_overlay.py"
    package_builder = repo / "crypto_platform/integration/universal/package_builder.py"
    universal_init = repo / "crypto_platform/integration/universal/__init__.py"
    runtime_validator = repo / "scripts/validate_btc_eth_uip_strategic_overlay_v1.py"

    for path in (
        database,
        closeout,
        governance,
        btc_manifest_path,
        eth_manifest_path,
        overlay_module,
        package_builder,
        universal_init,
        runtime_validator,
    ):
        require(path.exists(), f"Required closeout authority missing: {path}")

    require(sha256(database) == EXPECTED_DB_SHA256, "Canonical database hash mismatch")

    btc_manifest = read_json(btc_manifest_path)
    eth_manifest = read_json(eth_manifest_path)

    require(int(btc_manifest.get("record_count", -1)) == 1, "Bitcoin ledger record_count is not one")
    require(btc_manifest.get("first_observation_id") == EXPECTED_BTC_ID, "Bitcoin observation id mismatch")
    require(btc_manifest.get("first_observation_sha256") == EXPECTED_BTC_SHA256, "Bitcoin observation hash mismatch")

    require(int(eth_manifest.get("record_count", -1)) == 1, "Ethereum ledger record_count is not one")
    require(eth_manifest.get("first_observation_id") == EXPECTED_ETH_ID, "Ethereum observation id mismatch")
    require(eth_manifest.get("first_observation_sha256") == EXPECTED_ETH_SHA256, "Ethereum observation hash mismatch")

    btc_record = repo / str(btc_manifest.get("first_observation_file", ""))
    eth_record = repo / str(eth_manifest.get("first_observation_file", ""))
    require(btc_record.exists(), "Bitcoin observation file missing")
    require(eth_record.exists(), "Ethereum observation file missing")
    require(sha256(btc_record) == EXPECTED_BTC_SHA256, "Bitcoin observation file hash mismatch")
    require(sha256(eth_record) == EXPECTED_ETH_SHA256, "Ethereum observation file hash mismatch")

    btc = read_json(btc_record)
    eth = read_json(eth_record)

    for record, asset in ((btc, "bitcoin"), (eth, "ethereum")):
        require(record.get("asset_id") == asset, f"Unexpected asset in {asset} record")
        layers = record.get("decision_layers", {})
        require(layers.get("strategic_state") == "INSUFFICIENT_EVIDENCE", f"Unexpected {asset} strategic state")
        require(layers.get("tactical_new_capital_state") == "INSUFFICIENT_EVIDENCE", f"Unexpected {asset} tactical state")
        require(layers.get("existing_position_state") == "INSUFFICIENT_EVIDENCE", f"Unexpected {asset} existing-position state")
        outcomes = record.get("outcomes", {})
        for horizon in ("return_7d_exact", "return_30d_exact", "return_90d_exact", "return_180d_exact", "return_365d_exact", "return_1095d_exact"):
            require(outcomes.get(horizon) is None, f"{asset} outcome {horizon} is no longer unmatured/null")

    require(btc.get("cycle_context", {}).get("calendar_only_action_authorized") is False, "Bitcoin calendar-only action unexpectedly authorized")
    require(eth.get("bitcoin_cycle_context", {}).get("context_role") == "CROSS_MARKET_CONTEXT_ONLY_NOT_ETH_ACTION_RULE", "Ethereum Bitcoin-cycle context role mismatch")
    require(eth.get("evidence_quality", {}).get("synthetic_eth_halving_cycle_allowed") is False, "Synthetic Ethereum cycle unexpectedly allowed")
    require(eth.get("evidence_quality", {}).get("bitcoin_cycle_context_alone_can_select_eth_state") is False, "Bitcoin cycle can unexpectedly select Ethereum state")

    init_text = read_text(universal_init)
    package_text = read_text(package_builder)
    governance_text = read_text(governance)
    closeout_text = read_text(closeout)

    require('ADAPTER_VERSION = "1.1.0"' in init_text, "Adapter version is not 1.1.0")
    require('CONTRACT_VERSION = "1.0.0"' in init_text, "Universal contract version changed")
    require("btc_eth_strategic_overlay.csv" in package_text, "Strategic overlay is not wired into package")
    require("recommendations.csv" in package_text, "Legacy recommendations output missing")

    required_governance = (
        "MODULE42_BTC_ETH_FINAL_AUTHORITY=FALSE",
        "ETH_BITCOIN_CYCLE_ACTION_RULE_ALLOWED=FALSE",
        "SYNTHETIC_ETH_HALVING_CYCLE_ALLOWED=FALSE",
        "BTC_ETH_STRATEGIC_OVERLAY_REQUIRED=TRUE",
        "PRODUCTION_POLICY_CHANGE_AUTHORIZED=FALSE",
        "AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE",
    )
    for marker in required_governance:
        require(marker in governance_text, f"Missing governance marker: {marker}")

    required_closeout = (
        "BTC_ETH_STRATEGIC_ALIGNMENT_STRUCTURALLY_COMPLETE=TRUE",
        "BTC_ETH_RECOMMENDATION_POLICY_SKILL_CERTIFIED=FALSE",
        "MODULE42_BTC_ETH_FINAL_AUTHORITY=FALSE",
        "LEGACY_RECOMMENDATIONS_PRESERVED=TRUE",
        "BITCOIN_CYCLE_DIRECT_STRATEGIC_CONTEXT=TRUE",
        "ETH_BITCOIN_CYCLE_CONTEXT_ONLY=TRUE",
        "SYNTHETIC_ETH_HALVING_CYCLE_ALLOWED=FALSE",
        "FIXED_BTC_ETH_ALLOCATION_INVENTED=FALSE",
        "PRODUCTION_POLICY_CHANGED=FALSE",
        "AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE",
        "NEXT_GATE=PROSPECTIVE_OUTCOME_MATURATION_WHEN_EXACT_ENDPOINT_AVAILABLE",
    )
    for marker in required_closeout:
        require(marker in closeout_text, f"Missing closeout marker: {marker}")

    print("BTC_ETH_STRATEGIC_ALIGNMENT_CLOSEOUT_V1_VALIDATION=PASS")
    print("BTC_ETH_STRATEGIC_ALIGNMENT_STRUCTURALLY_COMPLETE=TRUE")
    print("BTC_LEDGER_RECORD_COUNT=1")
    print("ETH_LEDGER_RECORD_COUNT=1")
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
    print(f"CANONICAL_DATABASE_SHA256={EXPECTED_DB_SHA256}")
    print("CANONICAL_DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=PROSPECTIVE_OUTCOME_MATURATION_WHEN_EXACT_ENDPOINT_AVAILABLE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
