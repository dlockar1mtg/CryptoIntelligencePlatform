from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb

EXPERIMENT_ID = "CRYPTO_BTC_ETH_RECOMMENDATION_POLICY_VALIDATION_V1"
INVENTORY_SCOPE = "BTC_ETH_RECOMMENDATION_POLICY_EVIDENCE_INVENTORY"
ASSETS = ("bitcoin", "ethereum")
HORIZONS = (7, 30, 90, 180)
EXPECTED_V4_7D_SHA256 = "fe82f2b8cdfe817bfbb825cd2d97eb7d02711c8d1a2d3e5b3daf6c17fe756a48"
EXPECTED_V4_365_AUX_SHA256 = "f6a57ac6adefe5a0b187d9a3310b6d1cb4a7af20068c1eea779ca9b9d1b97735"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iso_date(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--v4-7d-final-results", required=True)
    parser.add_argument("--v4-365d-aux-results", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    database = Path(args.database).resolve()
    design = Path(args.design).resolve()
    final7 = Path(args.v4_7d_final_results).resolve()
    aux365 = Path(args.v4_365d_aux_results).resolve()
    output = Path(args.output).resolve()

    governed = {
        "database": database,
        "design": design,
        "v4_7d_final_results": final7,
        "v4_365d_aux_results": aux365,
    }
    for name, path in governed.items():
        require(path.is_file(), f"Required governed input missing: {name}={path}")
    require(not output.exists(), "BTC/ETH recommendation inventory output already exists; refusing overwrite")

    hashes_before = {name: sha256(path) for name, path in governed.items()}
    require(hashes_before["v4_7d_final_results"] == EXPECTED_V4_7D_SHA256, "Unexpected V4 7d final result hash")
    require(hashes_before["v4_365d_aux_results"] == EXPECTED_V4_365_AUX_SHA256, "Unexpected V4 365d auxiliary result hash")

    design_text = design.read_text(encoding="utf-8")
    for required_text in (
        EXPERIMENT_ID,
        INVENTORY_SCOPE,
        "Module 44 diagnostic limitation",
        "exact calendar endpoint",
        "No policy score or threshold decision may be produced by the inventory step",
    ):
        require(required_text in design_text, f"Design missing required control: {required_text}")

    conn = duckdb.connect(str(database), read_only=True)
    try:
        table_names = {
            str(row[0]).lower()
            for row in conn.execute("SELECT table_name FROM information_schema.tables").fetchall()
        }
        require("canonical_market_daily" in table_names, "canonical_market_daily is required")

        prices = conn.execute(
            """
            SELECT asset_id, observation_date, price_usd
            FROM canonical_market_daily
            WHERE asset_id IN ('bitcoin','ethereum')
              AND price_usd IS NOT NULL
            ORDER BY asset_id, observation_date
            """
        ).fetchall()
        price_dates = defaultdict(set)
        for asset_id, observation_date, _ in prices:
            price_dates[str(asset_id)].add(observation_date if isinstance(observation_date, date) else datetime.fromisoformat(str(observation_date)[:10]).date())

        m42_runs = []
        if "module42_runs" in table_names:
            m42_runs = conn.execute(
                """
                SELECT run_id, source_module30_run_id, source_module37_run_id,
                       source_module38_run_id, source_module39_run_id,
                       source_module40_run_id, source_module41_run_id,
                       started_at_utc, completed_at_utc, status,
                       recommendation_rows, evidence_status
                FROM module42_runs
                ORDER BY started_at_utc
                """
            ).fetchall()

        recommendations = []
        if "m42_asset_recommendations" in table_names:
            recommendations = conn.execute(
                """
                SELECT run_id, recommendation_date, asset_id, current_price,
                       investment_score, best_action, current_portfolio_weight,
                       best_current_portfolio_pct, weight_change_pct,
                       suggested_timeline, entry_strategy, conviction,
                       forecast_confidence, reliability_score,
                       regime_alignment_score, risk_score,
                       short_term_signal, medium_term_signal, long_term_signal,
                       evidence_status
                FROM m42_asset_recommendations
                WHERE asset_id IN ('bitcoin','ethereum')
                ORDER BY recommendation_date, asset_id, run_id
                """
            ).fetchall()

        m44_outcomes = []
        if "m44_decision_outcomes" in table_names:
            m44_outcomes = conn.execute(
                """
                SELECT source_module42_run_id, recommendation_date, asset_id,
                       horizon_days, best_action, outcome_status,
                       outcome_due_date, realized_date, realized_return_pct
                FROM m44_decision_outcomes
                WHERE asset_id IN ('bitcoin','ethereum')
                ORDER BY recommendation_date, asset_id, horizon_days
                """
            ).fetchall()
    finally:
        conn.close()

    run_status_counts = Counter(str(row[9]) for row in m42_runs)
    successful_run_ids = {str(row[0]) for row in m42_runs if str(row[9]) == "SUCCESS"}

    rec_rows = []
    for row in recommendations:
        rec_date = row[1] if isinstance(row[1], date) else datetime.fromisoformat(str(row[1])[:10]).date()
        asset = str(row[2])
        exact_coverage = {}
        for horizon in HORIZONS:
            due = rec_date + timedelta(days=horizon)
            exact_coverage[str(horizon)] = {
                "outcome_due_date": due.isoformat(),
                "exact_price_available": due in price_dates[asset],
            }
        rec_rows.append({
            "run_id": str(row[0]),
            "recommendation_date": rec_date.isoformat(),
            "asset_id": asset,
            "current_price_present": row[3] is not None,
            "investment_score": None if row[4] is None else float(row[4]),
            "best_action": None if row[5] is None else str(row[5]),
            "current_portfolio_weight_present": row[6] is not None,
            "target_portfolio_pct_present": row[7] is not None,
            "weight_change_pct_present": row[8] is not None,
            "suggested_timeline_present": row[9] is not None,
            "entry_strategy_present": row[10] is not None,
            "conviction": None if row[11] is None else str(row[11]),
            "forecast_confidence": None if row[12] is None else float(row[12]),
            "reliability_score": None if row[13] is None else float(row[13]),
            "regime_alignment_score": None if row[14] is None else float(row[14]),
            "risk_score": None if row[15] is None else float(row[15]),
            "short_term_signal": None if row[16] is None else float(row[16]),
            "medium_term_signal": None if row[17] is None else float(row[17]),
            "long_term_signal": None if row[18] is None else float(row[18]),
            "evidence_status": None if row[19] is None else str(row[19]),
            "source_module42_run_successful": str(row[0]) in successful_run_ids,
            "exact_outcome_coverage": exact_coverage,
        })

    by_asset = {}
    for asset in ASSETS:
        scoped = [row for row in rec_rows if row["asset_id"] == asset]
        dates = [row["recommendation_date"] for row in scoped]
        actions = Counter(row["best_action"] for row in scoped if row["best_action"] is not None)
        evidence = Counter(row["evidence_status"] for row in scoped if row["evidence_status"] is not None)
        conviction = Counter(row["conviction"] for row in scoped if row["conviction"] is not None)
        exact = {}
        for horizon in HORIZONS:
            observed = sum(1 for row in scoped if row["exact_outcome_coverage"][str(horizon)]["exact_price_available"])
            exact[str(horizon)] = {
                "eligible_rows": len(scoped),
                "exact_outcome_rows": observed,
                "missing_exact_outcome_rows": len(scoped) - observed,
            }
        duplicate_date_count = sum(count - 1 for count in Counter(dates).values() if count > 1)
        by_asset[asset] = {
            "recommendation_rows": len(scoped),
            "first_recommendation_date": min(dates) if dates else None,
            "last_recommendation_date": max(dates) if dates else None,
            "distinct_recommendation_dates": len(set(dates)),
            "duplicate_recommendation_date_rows": duplicate_date_count,
            "action_counts": dict(sorted(actions.items())),
            "evidence_status_counts": dict(sorted(evidence.items())),
            "conviction_counts": dict(sorted(conviction.items())),
            "investment_score_present_rows": sum(row["investment_score"] is not None for row in scoped),
            "forecast_confidence_present_rows": sum(row["forecast_confidence"] is not None for row in scoped),
            "current_portfolio_weight_present_rows": sum(row["current_portfolio_weight_present"] for row in scoped),
            "target_portfolio_pct_present_rows": sum(row["target_portfolio_pct_present"] for row in scoped),
            "entry_strategy_present_rows": sum(row["entry_strategy_present"] for row in scoped),
            "successful_source_run_rows": sum(row["source_module42_run_successful"] for row in scoped),
            "exact_outcome_coverage": exact,
        }

    m44_by_asset = {}
    for asset in ASSETS:
        scoped = [row for row in m44_outcomes if str(row[2]) == asset]
        horizon_counts = Counter(int(row[3]) for row in scoped)
        matured_counts = Counter(int(row[3]) for row in scoped if str(row[5]) == "MATURED")
        m44_by_asset[asset] = {
            "rows": len(scoped),
            "horizon_rows": {str(k): v for k, v in sorted(horizon_counts.items())},
            "matured_rows": {str(k): v for k, v in sorted(matured_counts.items())},
            "certification_authority": False,
            "reason": "Existing Module44 action-position and date-lookup semantics are diagnostic only for this experiment.",
        }

    lineage_rows = []
    for row in m42_runs:
        lineage_rows.append({
            "run_id": str(row[0]),
            "source_module30_run_id": None if row[1] is None else str(row[1]),
            "source_module37_run_id": None if row[2] is None else str(row[2]),
            "source_module38_run_id": None if row[3] is None else str(row[3]),
            "source_module39_run_id": None if row[4] is None else str(row[4]),
            "source_module40_run_id": None if row[5] is None else str(row[5]),
            "source_module41_run_id": None if row[6] is None else str(row[6]),
            "started_at_utc": None if row[7] is None else str(row[7]),
            "completed_at_utc": None if row[8] is None else str(row[8]),
            "status": str(row[9]),
            "recommendation_rows": None if row[10] is None else int(row[10]),
            "evidence_status": None if row[11] is None else str(row[11]),
        })

    result = {
        "experiment_id": EXPERIMENT_ID,
        "inventory_scope": INVENTORY_SCOPE,
        "inventory_only": True,
        "policy_scoring_performed": False,
        "threshold_optimization_performed": False,
        "policy_winner_selected": False,
        "production_policy_changed": False,
        "source_database_modified": False,
        "evidence_class": "HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME",
        "strict_point_in_time_claim_allowed": False,
        "primary_assets": list(ASSETS),
        "exact_outcome_horizons_days": list(HORIZONS),
        "module42_runs_table_present": "module42_runs" in table_names,
        "module42_recommendations_table_present": "m42_asset_recommendations" in table_names,
        "module44_outcomes_table_present": "m44_decision_outcomes" in table_names,
        "module42_run_rows": len(m42_runs),
        "module42_successful_run_rows": len(successful_run_ids),
        "module42_run_status_counts": dict(sorted(run_status_counts.items())),
        "btc_eth_recommendation_rows": len(rec_rows),
        "by_asset": by_asset,
        "module44_diagnostic_inventory": m44_by_asset,
        "module42_lineage": lineage_rows,
        "recommendation_rows": rec_rows,
        "governed_source_hashes_before": hashes_before,
        "next_gate": "REVIEW_BTC_ETH_RECOMMENDATION_POLICY_EVIDENCE_INVENTORY_AND_DECIDE_SCORING_FEASIBILITY",
    }

    hashes_after = {name: sha256(path) for name, path in governed.items()}
    require(hashes_after == hashes_before, "Governed evidence or source database changed during inventory")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("CRYPTO_BTC_ETH_RECOMMENDATION_POLICY_EVIDENCE_INVENTORY=PASS")
    print(f"MODULE42_RUN_ROWS={len(m42_runs)}")
    print(f"MODULE42_SUCCESSFUL_RUN_ROWS={len(successful_run_ids)}")
    print(f"BTC_ETH_RECOMMENDATION_ROWS={len(rec_rows)}")
    for asset in ASSETS:
        summary = by_asset[asset]
        print(f"ASSET={asset}|RECOMMENDATION_ROWS={summary['recommendation_rows']}|DISTINCT_DATES={summary['distinct_recommendation_dates']}|FIRST={summary['first_recommendation_date']}|LAST={summary['last_recommendation_date']}")
        print(f"ASSET={asset}|ACTION_COUNTS={json.dumps(summary['action_counts'], sort_keys=True)}")
        for horizon in HORIZONS:
            coverage = summary["exact_outcome_coverage"][str(horizon)]
            print(f"ASSET={asset}|HORIZON={horizon}|EXACT_OUTCOME_ROWS={coverage['exact_outcome_rows']}|MISSING={coverage['missing_exact_outcome_rows']}")
    print("INVENTORY_ONLY=TRUE")
    print("POLICY_SCORING_PERFORMED=FALSE")
    print("THRESHOLD_OPTIMIZATION_PERFORMED=FALSE")
    print("POLICY_WINNER_SELECTED=FALSE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=REVIEW_BTC_ETH_RECOMMENDATION_POLICY_EVIDENCE_INVENTORY_AND_DECIDE_SCORING_FEASIBILITY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
