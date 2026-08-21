from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, median

import duckdb

EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_HORIZON_RECOVERY_V4"
DIAGNOSTIC_SCOPE = "365D_DEVELOPMENT_AUXILIARY_ONLY"
EXPECTED_DEVELOPMENT_RESULTS_SHA256 = "a44e237112bf6521c8a770de120d4a0104731c280d7009568e6618cca1c1fbfb"
EXPECTED_V4_MANIFEST_CONTENT_SHA256 = "6e68fcd60d179ba8d510554df75ebb9b96e77b1f1e14fbaefad494e694a734e2"
EXPECTED_V4_7D_FINAL_RESULTS_SHA256 = "fe82f2b8cdfe817bfbb825cd2d97eb7d02711c8d1a2d3e5b3daf6c17fe756a48"
SUPPORTED_365D_ASSETS = ("bitcoin", "ethereum", "solana", "chainlink", "avalanche")
NON_BTC_365D_ASSETS = ("ethereum", "solana", "chainlink", "avalanche")
EXPECTED_DEVELOPMENT_ORIGINS_PER_ASSET = 50
EXPECTED_TOTAL_DEVELOPMENT_ROWS = 250
EXPECTED_BTC_RELATIVE_ELIGIBLE_ROWS = 200


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_content_hash(payload: dict) -> str:
    body = dict(payload)
    body.pop("manifest_content_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def finite_or_none(value):
    if value is None:
        return None
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return value


def numeric_summary(values: list[float], include_worst: bool = False) -> dict:
    clean = [float(v) for v in values if v is not None]
    result = {
        "observed_rows": len(clean),
        "mean": finite_or_none(mean(clean)) if clean else None,
        "median": finite_or_none(median(clean)) if clean else None,
    }
    if include_worst:
        result["worst"] = finite_or_none(min(clean)) if clean else None
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--v4-manifest", required=True)
    parser.add_argument("--development-results", required=True)
    parser.add_argument("--v4-7d-final-results", required=True)
    parser.add_argument("--addendum", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    database = Path(args.database).resolve()
    manifest_path = Path(args.v4_manifest).resolve()
    development_results_path = Path(args.development_results).resolve()
    final7_path = Path(args.v4_7d_final_results).resolve()
    addendum_path = Path(args.addendum).resolve()
    output = Path(args.output).resolve()

    governed_paths = {
        "database": database,
        "v4_manifest": manifest_path,
        "development_results": development_results_path,
        "v4_7d_final_results": final7_path,
        "addendum": addendum_path,
    }
    for name, path in governed_paths.items():
        require(path.is_file(), f"Required governed input missing: {name}={path}")
    require(not output.exists(), "365d auxiliary diagnostic output already exists; refusing overwrite")

    hashes_before = {name: sha256(path) for name, path in governed_paths.items()}
    require(
        hashes_before["development_results"] == EXPECTED_DEVELOPMENT_RESULTS_SHA256,
        "Unexpected authoritative V4 development-results hash",
    )
    require(
        hashes_before["v4_7d_final_results"] == EXPECTED_V4_7D_FINAL_RESULTS_SHA256,
        "Unexpected preserved V4 7d final-holdout result hash",
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    development = json.loads(development_results_path.read_text(encoding="utf-8"))
    final7 = json.loads(final7_path.read_text(encoding="utf-8"))
    addendum_text = addendum_path.read_text(encoding="utf-8")

    require(manifest.get("experiment_id") == EXPERIMENT_ID, "Unexpected V4 manifest experiment id")
    require(
        manifest.get("manifest_content_sha256") == EXPECTED_V4_MANIFEST_CONTENT_SHA256,
        "Unexpected candidate-safe V4 manifest content hash field",
    )
    require(
        manifest_content_hash(manifest) == EXPECTED_V4_MANIFEST_CONTENT_SHA256,
        "Candidate-safe V4 manifest canonical content hash mismatch",
    )
    require(manifest.get("candidate_safe_membership_required") is True, "Candidate-safe membership control missing")
    require(manifest.get("exact_calendar_target_date_required") is True, "Exact-calendar target control missing")
    require(manifest.get("holdout_outcomes_viewed_before_freeze") is False, "V4 holdout was not sealed before freeze")
    require(manifest.get("holdout_outcome_values_read_during_membership_selection") is False, "V4 holdout values were read during membership selection")
    require(manifest.get("v3_final_holdout_reused") is False, "V3 final holdout was reused by V4")

    require(development.get("experiment_id") == EXPERIMENT_ID, "Unexpected development-results experiment id")
    require(development.get("v4_manifest_content_sha256") == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "Development results are not pinned to candidate-safe V4 manifest")
    require(development.get("selected_winners", {}).get("365") is None, "V4 365d development decision is not NO_QUALIFIED_WINNER")
    require(development.get("horizon_results", {}).get("365", {}).get("qualified_winner_exists") is False, "V4 365d qualified-winner sentinel is unexpected")
    require(development.get("v4_final_holdout_outcomes_viewed") is False, "Preserved development artifact says a V4 final holdout had been viewed before freeze")
    require(development.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout was viewed in development evidence")

    require(final7.get("experiment_id") == EXPERIMENT_ID, "Unexpected V4 7d final-holdout experiment id")
    require(final7.get("evaluation_scope") == "7D_FINAL_HOLDOUT_ONLY", "Preserved final result is not 7d-only")
    require(final7.get("v4_7d_final_holdout_outcomes_viewed") is True, "V4 7d final holdout is not recorded as consumed")
    require(final7.get("v4_30d_final_holdout_outcomes_viewed") is False, "V4 30d final holdout is unexpectedly marked viewed")
    require(final7.get("v4_365d_final_holdout_outcomes_viewed") is False, "V4 365d final holdout is unexpectedly marked viewed")
    require(final7.get("v3_final_holdout_outcomes_viewed") is False, "V3 final holdout is unexpectedly marked viewed")
    require(final7.get("post_holdout_tuning_allowed") is False, "Post-holdout tuning is unexpectedly allowed")
    require(final7.get("recommendation_policy_changed") is False, "Recommendation policy unexpectedly changed")
    require(final7.get("production_promotion_allowed") is False, "Production promotion unexpectedly allowed")

    for required_text in (
        "selection-neutral",
        "winner_gate_affected=false",
        "365D_DEVELOPMENT_AUXILIARY_ONLY",
        "NO_QUALIFIED_WINNER",
        "V4 365d final-holdout outcomes",
    ):
        require(required_text in addendum_text, f"Governance addendum missing required boundary text: {required_text}")

    groups = [
        group for group in manifest.get("groups", [])
        if int(group.get("horizon_days", -1)) == 365
    ]
    require(len(groups) == 5, "Expected exactly five supported V4 365d groups")
    group_by_asset = {str(group["asset_id"]): group for group in groups}
    require(set(group_by_asset) == set(SUPPORTED_365D_ASSETS), "Unexpected supported V4 365d asset set")

    development_dates: dict[str, list[date]] = {}
    final_holdout_dates: dict[str, set[date]] = {}
    for asset in SUPPORTED_365D_ASSETS:
        group = group_by_asset[asset]
        dev = [parse_date(value) for value in group.get("v4_development_origin_dates", [])]
        holdout = {parse_date(value) for value in group.get("v4_final_holdout_origin_dates", [])}
        require(len(dev) == EXPECTED_DEVELOPMENT_ORIGINS_PER_ASSET, f"Expected 50 development origins for {asset}")
        require(len(set(dev)) == EXPECTED_DEVELOPMENT_ORIGINS_PER_ASSET, f"Duplicate V4 365d development origin for {asset}")
        require(not (set(dev) & holdout), f"V4 365d development/holdout overlap for {asset}")
        development_dates[asset] = dev
        final_holdout_dates[asset] = holdout

    conn = duckdb.connect(str(database), read_only=True)
    try:
        table_exists = conn.execute(
            "SELECT count(*) FROM information_schema.tables WHERE lower(table_name)='canonical_market_daily'"
        ).fetchone()[0]
        require(int(table_exists) >= 1, "canonical_market_daily is unavailable")
        rows = conn.execute(
            """
            SELECT asset_id, observation_date, price_usd
            FROM canonical_market_daily
            WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','avalanche')
              AND price_usd IS NOT NULL
            ORDER BY asset_id, observation_date
            """
        ).fetchall()
    finally:
        conn.close()

    prices: dict[str, dict[date, float]] = {asset: {} for asset in SUPPORTED_365D_ASSETS}
    for asset_id, observation_date, price_usd in rows:
        asset = str(asset_id)
        if asset not in prices:
            continue
        obs = observation_date if isinstance(observation_date, date) else parse_date(str(observation_date)[:10])
        require(obs not in prices[asset], f"Duplicate canonical price row for {asset} {obs.isoformat()}")
        price = float(price_usd)
        require(price > 0, f"Non-positive canonical price for {asset} {obs.isoformat()}")
        prices[asset][obs] = price

    diagnostic_rows = []
    for asset in SUPPORTED_365D_ASSETS:
        for origin in development_dates[asset]:
            target = origin + timedelta(days=365)
            require(origin not in final_holdout_dates[asset], f"Refusing final-holdout origin for {asset} {origin}")
            origin_price = prices[asset].get(origin)
            target_price = prices[asset].get(target)

            actual_return = None
            exceeds_15 = None
            if origin_price is not None and target_price is not None:
                actual_return = 100.0 * (target_price / origin_price - 1.0)
                exceeds_15 = bool(actual_return > 15.0)

            btc_relative = None
            beat_bitcoin = None
            btc_return = None
            btc_relative_status = "not_applicable" if asset == "bitcoin" else "missing"
            if asset != "bitcoin":
                btc_origin = prices["bitcoin"].get(origin)
                btc_target = prices["bitcoin"].get(target)
                if actual_return is not None and btc_origin is not None and btc_target is not None:
                    btc_return = 100.0 * (btc_target / btc_origin - 1.0)
                    btc_relative = actual_return - btc_return
                    beat_bitcoin = bool(btc_relative > 0.0)
                    btc_relative_status = "observed"

            drawdown = None
            expected_dates = [origin + timedelta(days=offset) for offset in range(366)]
            path_prices = [prices[asset].get(day) for day in expected_dates]
            path_complete = bool(origin_price is not None and target_price is not None and all(value is not None for value in path_prices))
            if path_complete:
                drawdown = 100.0 * min((float(value) / origin_price - 1.0) for value in path_prices)

            diagnostic_rows.append({
                "asset_id": asset,
                "forecast_origin_date": origin.isoformat(),
                "exact_target_date": target.isoformat(),
                "actual_forward_365d_return_pct": finite_or_none(actual_return),
                "forward_return_exceeds_15pct": exceeds_15,
                "btc_relative_status": btc_relative_status,
                "bitcoin_forward_365d_return_pct": finite_or_none(btc_return),
                "btc_relative_forward_return_pct": finite_or_none(btc_relative),
                "beat_bitcoin": beat_bitcoin,
                "realized_forward_drawdown_pct": finite_or_none(drawdown),
                "drawdown_daily_path_complete": path_complete,
            })

    require(len(diagnostic_rows) == EXPECTED_TOTAL_DEVELOPMENT_ROWS, "Unexpected total V4 365d development diagnostic rows")
    require(all(row["asset_id"] != "xrp" for row in diagnostic_rows), "Unsupported XRP365 was synthesized")

    def asset_rows(asset: str) -> list[dict]:
        return [row for row in diagnostic_rows if row["asset_id"] == asset]

    return_observed = [row for row in diagnostic_rows if row["actual_forward_365d_return_pct"] is not None]
    exceed_observed = [row for row in diagnostic_rows if row["forward_return_exceeds_15pct"] is not None]
    btc_eligible = [row for row in diagnostic_rows if row["asset_id"] != "bitcoin"]
    btc_observed = [row for row in btc_eligible if row["btc_relative_forward_return_pct"] is not None]
    drawdown_observed = [row for row in diagnostic_rows if row["realized_forward_drawdown_pct"] is not None]

    plus15_by_asset = {}
    btc_by_asset = {"bitcoin": {"status": "not_applicable", "eligible_rows": 0, "observed_rows": 0, "missing_rows": 0}}
    drawdown_by_asset = {}
    for asset in SUPPORTED_365D_ASSETS:
        scoped = asset_rows(asset)
        plus_obs = [row for row in scoped if row["forward_return_exceeds_15pct"] is not None]
        plus_count = sum(1 for row in plus_obs if row["forward_return_exceeds_15pct"] is True)
        plus15_by_asset[asset] = {
            "eligible_rows": len(scoped),
            "observed_rows": len(plus_obs),
            "missing_rows": len(scoped) - len(plus_obs),
            "observed_exceedance_count": plus_count,
            "observed_exceedance_rate": finite_or_none(plus_count / len(plus_obs)) if plus_obs else None,
        }

        dd_obs = [row["realized_forward_drawdown_pct"] for row in scoped if row["realized_forward_drawdown_pct"] is not None]
        dd_summary = numeric_summary(dd_obs, include_worst=True)
        drawdown_by_asset[asset] = {
            "eligible_rows": len(scoped),
            "observed_rows": len(dd_obs),
            "missing_rows": len(scoped) - len(dd_obs),
            "mean_realized_forward_drawdown_pct": dd_summary["mean"],
            "median_realized_forward_drawdown_pct": dd_summary["median"],
            "worst_realized_forward_drawdown_pct": dd_summary["worst"],
        }

        if asset != "bitcoin":
            rel_obs = [row for row in scoped if row["btc_relative_forward_return_pct"] is not None]
            rel_values = [row["btc_relative_forward_return_pct"] for row in rel_obs]
            beat_count = sum(1 for row in rel_obs if row["beat_bitcoin"] is True)
            rel_summary = numeric_summary(rel_values)
            btc_by_asset[asset] = {
                "status": "applicable",
                "eligible_rows": len(scoped),
                "observed_rows": len(rel_obs),
                "missing_rows": len(scoped) - len(rel_obs),
                "beat_bitcoin_count": beat_count,
                "beat_bitcoin_rate": finite_or_none(beat_count / len(rel_obs)) if rel_obs else None,
                "mean_btc_relative_forward_return_pct": rel_summary["mean"],
                "median_btc_relative_forward_return_pct": rel_summary["median"],
            }

    exceed_count = sum(1 for row in exceed_observed if row["forward_return_exceeds_15pct"] is True)
    btc_beat_count = sum(1 for row in btc_observed if row["beat_bitcoin"] is True)
    btc_values = [row["btc_relative_forward_return_pct"] for row in btc_observed]
    btc_summary = numeric_summary(btc_values)
    dd_values = [row["realized_forward_drawdown_pct"] for row in drawdown_observed]
    dd_summary = numeric_summary(dd_values, include_worst=True)

    result = {
        "experiment_id": EXPERIMENT_ID,
        "diagnostic_scope": DIAGNOSTIC_SCOPE,
        "evidence_class": "HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME",
        "strict_point_in_time_claim_allowed": False,
        "selection_neutral": True,
        "winner_gate_affected": False,
        "v4_365d_development_decision": "NO_QUALIFIED_WINNER",
        "v4_365d_long_trend_reserved_as_v5_challenger": True,
        "v4_manifest_content_sha256": EXPECTED_V4_MANIFEST_CONTENT_SHA256,
        "development_results_sha256": hashes_before["development_results"],
        "v4_7d_final_holdout_results_sha256": hashes_before["v4_7d_final_results"],
        "v4_7d_final_holdout_outcomes_viewed": True,
        "v4_30d_final_holdout_outcomes_viewed": False,
        "v4_365d_final_holdout_outcomes_viewed": False,
        "v3_final_holdout_outcomes_viewed": False,
        "post_holdout_tuning_allowed": False,
        "recommendation_policy_changed": False,
        "production_promotion_allowed": False,
        "exact_calendar_target_required": True,
        "missing_values_synthesized": False,
        "supported_365d_assets": list(SUPPORTED_365D_ASSETS),
        "unsupported_assets_synthesized": [],
        "development_rows": EXPECTED_TOTAL_DEVELOPMENT_ROWS,
        "diagnostics": {
            "forward_return_exceeds_15pct": {
                "eligible_rows": EXPECTED_TOTAL_DEVELOPMENT_ROWS,
                "observed_rows": len(exceed_observed),
                "missing_rows": EXPECTED_TOTAL_DEVELOPMENT_ROWS - len(exceed_observed),
                "observed_exceedance_count": exceed_count,
                "observed_exceedance_rate": finite_or_none(exceed_count / len(exceed_observed)) if exceed_observed else None,
                "by_asset": plus15_by_asset,
            },
            "btc_relative_forward_return": {
                "eligible_non_bitcoin_rows": EXPECTED_BTC_RELATIVE_ELIGIBLE_ROWS,
                "observed_rows": len(btc_observed),
                "missing_rows": EXPECTED_BTC_RELATIVE_ELIGIBLE_ROWS - len(btc_observed),
                "beat_bitcoin_count": btc_beat_count,
                "beat_bitcoin_rate": finite_or_none(btc_beat_count / len(btc_observed)) if btc_observed else None,
                "mean_btc_relative_forward_return_pct": btc_summary["mean"],
                "median_btc_relative_forward_return_pct": btc_summary["median"],
                "by_asset": btc_by_asset,
            },
            "realized_forward_drawdown": {
                "eligible_rows": EXPECTED_TOTAL_DEVELOPMENT_ROWS,
                "observed_rows": len(drawdown_observed),
                "missing_rows": EXPECTED_TOTAL_DEVELOPMENT_ROWS - len(drawdown_observed),
                "mean_realized_forward_drawdown_pct": dd_summary["mean"],
                "median_realized_forward_drawdown_pct": dd_summary["median"],
                "worst_realized_forward_drawdown_pct": dd_summary["worst"],
                "complete_daily_path_required": True,
                "by_asset": drawdown_by_asset,
            },
        },
        "rows": diagnostic_rows,
        "governed_source_hashes_before": hashes_before,
        "source_database_modified": False,
        "next_gate": "PRESERVE_AND_REVIEW_SELECTION_NEUTRAL_V4_365D_AUXILIARY_DIAGNOSTICS",
    }

    hashes_after = {name: sha256(path) for name, path in governed_paths.items()}
    require(hashes_after == hashes_before, "Governed source evidence or source database changed during diagnostics")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("CRYPTO_V4_365D_AUXILIARY_DIAGNOSTICS=PASS")
    print(f"DEVELOPMENT_ROWS={EXPECTED_TOTAL_DEVELOPMENT_ROWS}")
    print(f"PLUS15_OBSERVED_ROWS={len(exceed_observed)}")
    print(f"PLUS15_EXCEEDANCE_RATE={result['diagnostics']['forward_return_exceeds_15pct']['observed_exceedance_rate']}")
    print(f"BTC_RELATIVE_OBSERVED_ROWS={len(btc_observed)}")
    print(f"BTC_RELATIVE_BEAT_RATE={result['diagnostics']['btc_relative_forward_return']['beat_bitcoin_rate']}")
    print(f"BTC_RELATIVE_MEAN_PCT={result['diagnostics']['btc_relative_forward_return']['mean_btc_relative_forward_return_pct']}")
    print(f"FORWARD_DRAWDOWN_OBSERVED_ROWS={len(drawdown_observed)}")
    print(f"FORWARD_DRAWDOWN_MEAN_PCT={result['diagnostics']['realized_forward_drawdown']['mean_realized_forward_drawdown_pct']}")
    print("SELECTION_NEUTRAL=TRUE")
    print("WINNER_GATE_AFFECTED=FALSE")
    print("V4_365D_DEVELOPMENT_DECISION=NO_QUALIFIED_WINNER")
    print("V4_7D_FINAL_HOLDOUT_OUTCOMES_VIEWED=TRUE")
    print("V4_30D_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V4_365D_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("V3_FINAL_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("POST_HOLDOUT_TUNING_ALLOWED=FALSE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=PRESERVE_AND_REVIEW_SELECTION_NEUTRAL_V4_365D_AUXILIARY_DIAGNOSTICS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
