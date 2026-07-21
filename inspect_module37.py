from crypto_platform.platform import load_all, connect
from crypto_platform.module37 import MODULE37_SCHEMA


def show(conn, title, sql):
    print(f"\n{title}")
    print("-" * len(title))
    frame = conn.execute(sql).fetchdf()
    print(
        frame.to_string(index=False)
        if not frame.empty
        else "No data."
    )


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE37_SCHEMA)

    show(conn, "PORTFOLIO STATISTICS", """
        SELECT *
        EXCLUDE(run_id, calculated_at_utc)
        FROM latest_m37_portfolio_statistics
    """)

    show(conn, "OPTIMIZED ALLOCATIONS", """
        SELECT asset_id,
               prior_weight,
               optimized_weight,
               risk_adjusted_weight,
               trade_weight,
               marginal_risk_contribution_pct,
               allocation_status
        FROM latest_m37_optimized_allocations
    """)

    show(conn, "EXPECTED RETURN MODEL", """
        SELECT asset_id,
               historical_return_pct,
               regime_return_pct,
               shrinkage_prior_pct,
               blended_expected_return_pct,
               current_regime_probability,
               confidence_weight
        FROM latest_m37_expected_returns
    """)

    show(conn, "OPTIMIZER CANDIDATES", """
        SELECT candidate_id,
               method,
               expected_return_pct,
               expected_volatility_pct,
               expected_sharpe,
               diversification_ratio,
               risky_sleeve_effective_assets,
               risky_sleeve_concentration_pct,
               cash_weight,
               turnover_pct,
               maximum_asset_weight,
               minimum_asset_weight,
               objective_score,
               optimization_success,
               selected
        FROM latest_m37_optimizer_candidates
    """)

    show(conn, "RISK DECOMPOSITION", """
        SELECT asset_id,
               weight,
               standalone_volatility_pct,
               marginal_contribution,
               component_risk_contribution_pct,
               diversification_benefit_pct
        FROM latest_m37_risk_decomposition
    """)

    show(conn, "EFFICIENT FRONTIER", """
        SELECT frontier_id,
               target_return_pct,
               expected_return_pct,
               expected_volatility_pct,
               expected_sharpe,
               diversification_ratio,
               concentration_pct
        FROM latest_m37_efficient_frontier
    """)

    show(conn, "LATEST RUNS", """
        SELECT started_at_utc,
               completed_at_utc,
               status,
               candidate_rows,
               allocation_rows,
               frontier_rows,
               risk_contribution_rows,
               selected_candidate_id,
               selected_method,
               expected_return_pct,
               expected_volatility_pct,
               expected_sharpe,
               diversification_ratio,
               effective_assets,
               concentration_score,
               cash_weight,
               turnover_pct,
               validation_status,
               recommendation,
               notes
        FROM module37_runs
        ORDER BY started_at_utc DESC
        LIMIT 10
    """)

    conn.close()


if __name__ == "__main__":
    main()
