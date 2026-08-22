from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb


def fetchall_dicts(conn: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    cur = conn.execute(sql)
    cols = [item[0] for item in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def table_exists(conn: duckdb.DuckDBPyConnection, name: str) -> bool:
    return bool(
        conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='main' AND table_name=?",
            [name],
        ).fetchone()[0]
    )


def scalar(conn: duckdb.DuckDBPyConnection, sql: str) -> Any:
    return conn.execute(sql).fetchone()[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    db_path = Path(args.database).resolve()
    if not db_path.is_file():
        raise FileNotFoundError(db_path)

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        required = [
            "signal_validation_summary",
            "signal_forward_performance",
            "m39_forecast_scorecard",
            "m39_rolling_origin_validation",
            "m40_forecast_memory",
            "m42_asset_recommendations",
            "m44_decision_outcomes",
            "decision_shadow_summary",
            "audited_backtest_summary",
            "portfolio_backtest_summary",
        ]
        missing = [name for name in required if not table_exists(conn, name)]
        if missing:
            raise RuntimeError(f"Missing predictive-validation tables: {missing}")

        signal_summary = fetchall_dicts(
            conn,
            """
            SELECT historical_signal, horizon_days, sample_count,
                   positive_rate_pct, average_forward_return_pct,
                   median_forward_return_pct, average_excess_vs_btc_pct,
                   btc_outperformance_rate_pct
            FROM latest_signal_validation_summary
            ORDER BY historical_signal, horizon_days
            """,
        )

        completed_signal_rows = int(
            scalar(conn, "SELECT COUNT(*) FROM signal_forward_performance WHERE completed=TRUE")
        )
        signal_dates = fetchall_dicts(
            conn,
            """
            SELECT MIN(signal_date) AS min_signal_date,
                   MAX(signal_date) AS max_signal_date,
                   COUNT(DISTINCT signal_date) AS distinct_signal_dates,
                   COUNT(DISTINCT asset_id) AS distinct_assets
            FROM signal_forward_performance
            WHERE completed=TRUE
            """,
        )[0]

        m39_latest = fetchall_dicts(
            conn,
            """
            SELECT asset_id, horizon_days, forecasts_evaluated,
                   mean_absolute_error_pct, root_mean_squared_error_pct,
                   directional_accuracy_pct, calibrated_brier_score,
                   interval_coverage_pct, mean_interval_width_pct,
                   realized_sharpe, scorecard_status
            FROM latest_m39_forecast_scorecard
            ORDER BY asset_id, horizon_days
            """,
        )
        m39_rollup = fetchall_dicts(
            conn,
            """
            SELECT horizon_days,
                   SUM(testing_rows) AS testing_rows,
                   AVG(mae_pct) AS mean_mae_pct,
                   AVG(rmse_pct) AS mean_rmse_pct,
                   AVG(directional_accuracy_pct) AS mean_directional_accuracy_pct,
                   AVG(brier_score) AS mean_brier_score,
                   AVG(interval_coverage_pct) AS mean_interval_coverage_pct
            FROM latest_m39_rolling_origin_validation
            GROUP BY horizon_days
            ORDER BY horizon_days
            """,
        )

        forecast_memory = fetchall_dicts(
            conn,
            """
            SELECT horizon_days,
                   COUNT(*) AS forecasts,
                   SUM(CASE WHEN outcome_status='MATURED' THEN 1 ELSE 0 END) AS matured,
                   SUM(CASE WHEN outcome_status='MATURED' AND direction_correct THEN 1 ELSE 0 END) AS direction_correct,
                   AVG(CASE WHEN outcome_status='MATURED' THEN absolute_error_pct END) AS mean_absolute_error_pct,
                   AVG(CASE WHEN outcome_status='MATURED' THEN realized_return_pct END) AS mean_realized_return_pct
            FROM m40_forecast_memory
            GROUP BY horizon_days
            ORDER BY horizon_days
            """,
        )

        recommendation_history = fetchall_dicts(
            conn,
            """
            SELECT best_action,
                   COUNT(*) AS recommendations,
                   MIN(recommendation_date) AS first_date,
                   MAX(recommendation_date) AS last_date,
                   AVG(investment_score) AS mean_investment_score,
                   AVG(forecast_confidence) AS mean_forecast_confidence,
                   AVG(reliability_score) AS mean_reliability_score
            FROM m42_asset_recommendations
            GROUP BY best_action
            ORDER BY best_action
            """,
        )

        m44_status = fetchall_dicts(
            conn,
            """
            SELECT outcome_status, COUNT(*) AS rows
            FROM m44_decision_outcomes
            GROUP BY outcome_status
            ORDER BY outcome_status
            """,
        )
        m44_matured = fetchall_dicts(
            conn,
            """
            SELECT best_action, horizon_days,
                   COUNT(*) AS matured_outcomes,
                   AVG(realized_return_pct) AS mean_realized_return_pct,
                   AVG(strategy_return_pct) AS mean_strategy_return_pct,
                   AVG(buy_hold_return_pct) AS mean_buy_hold_return_pct,
                   AVG(excess_vs_cash_pct) AS mean_excess_vs_cash_pct,
                   AVG(excess_vs_buy_hold_pct) AS mean_excess_vs_buy_hold_pct,
                   100.0*AVG(CASE WHEN direction_correct THEN 1.0 ELSE 0.0 END) AS direction_accuracy_pct,
                   100.0*AVG(CASE WHEN economic_value_positive THEN 1.0 ELSE 0.0 END) AS economic_value_positive_pct
            FROM m44_decision_outcomes
            WHERE outcome_status='MATURED'
            GROUP BY best_action, horizon_days
            ORDER BY best_action, horizon_days
            """,
        )

        decision_shadow = fetchall_dicts(
            conn,
            """
            SELECT start_date, end_date, periods, total_return_pct,
                   annualized_return_pct, annualized_volatility_pct,
                   sharpe_ratio, maximum_drawdown_pct,
                   btc_total_return_pct, btc_annualized_return_pct,
                   btc_excess_pct, information_ratio,
                   benchmark_win_rate_pct, average_btc_weight_pct,
                   average_turnover_pct, transaction_cost_drag_pct,
                   promotion_status, promotion_reason
            FROM latest_decision_shadow_summary
            """,
        )
        audited_backtest = fetchall_dicts(
            conn,
            """
            SELECT start_date, end_date, periods,
                   corrected_total_return_pct, corrected_annualized_return_pct,
                   corrected_annualized_volatility_pct, corrected_sharpe_ratio,
                   corrected_maximum_drawdown_pct, btc_total_return_pct,
                   btc_excess_pct, equal_weight_core_total_return_pct,
                   btc_cash_60_40_total_return_pct,
                   inverse_volatility_total_return_pct, information_ratio,
                   benchmark_win_rate_pct, average_cash_weight_pct,
                   average_turnover_pct, transaction_cost_drag_pct,
                   critical_findings, warning_findings,
                   audit_status, promotion_status, promotion_reason
            FROM latest_audited_backtest_summary
            """,
        )
        portfolio_backtest = fetchall_dicts(
            conn,
            """
            SELECT start_date, end_date, rebalance_periods,
                   total_return_pct, annualized_return_pct,
                   annualized_volatility_pct, sharpe_ratio,
                   maximum_drawdown_pct, benchmark_total_return_pct,
                   benchmark_annualized_return_pct, excess_return_pct,
                   information_ratio, average_turnover_pct,
                   transaction_cost_drag_pct, positive_period_rate_pct,
                   benchmark_win_rate_pct, promoted, promotion_reason
            FROM latest_portfolio_backtest_summary
            """,
        )

        leakage_guard = {
            "source_commit": args.source_commit,
            "read_only": True,
            "note": (
                "This audit summarizes persisted native evidence only. It does not certify that historical labels, "
                "features, or recommendations were available point-in-time unless their producing modules' anti-lookahead "
                "and replay semantics are separately verified."
            ),
        }

        result = {
            "status": "CRYPTO_NATIVE_PREDICTIVE_SKILL_AUDIT_COMPLETE",
            "source_commit": args.source_commit,
            "database": str(db_path),
            "read_only": True,
            "historical_signal_validation": {
                "completed_forward_rows": completed_signal_rows,
                "coverage": signal_dates,
                "summary": signal_summary,
            },
            "forecast_validation": {
                "latest_scorecards": m39_latest,
                "rolling_origin_rollup": m39_rollup,
                "persisted_forecast_memory": forecast_memory,
            },
            "recommendation_validation": {
                "module42_history": recommendation_history,
                "module44_outcome_status": m44_status,
                "module44_matured_by_action_horizon": m44_matured,
            },
            "strategy_validation": {
                "decision_shadow": decision_shadow,
                "audited_backtest": audited_backtest,
                "portfolio_backtest": portfolio_backtest,
            },
            "interpretation_guard": leakage_guard,
            "next_gate": "VERIFY_POINT_IN_TIME_SEMANTICS_AND_INTERPRET_NATIVE_PREDICTIVE_SKILL",
        }
        print(json.dumps(result, indent=2, default=str))
        print("CRYPTO_NATIVE_PREDICTIVE_SKILL_AUDIT=COMPLETE")
        print(f"COMPLETED_SIGNAL_FORWARD_ROWS={completed_signal_rows}")
        print(f"M44_MATURED_GROUPS={len(m44_matured)}")
        print(f"M39_SCORECARD_ROWS={len(m39_latest)}")
        print("DATABASE_MODIFIED=FALSE")
        print("NEXT_GATE=VERIFY_POINT_IN_TIME_SEMANTICS_AND_INTERPRET_NATIVE_PREDICTIVE_SKILL")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
