from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA

def show(conn, title, sql):
    print(f"\n{title}")
    print("-" * len(title))
    frame = conn.execute(sql).fetchdf()
    print(frame.to_string(index=False) if not frame.empty else "No data.")

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE2_SCHEMA)
    conn.execute(MODULE3_SCHEMA)

    show(conn, "LATEST MODULE 3 RUNS", '''
        SELECT started_at_utc,completed_at_utc,status,signal_date,
               assets_analyzed,monthly_contribution_usd,cash_weight,notes
        FROM module3_runs ORDER BY started_at_utc DESC LIMIT 10
    ''')
    show(conn, "PORTFOLIO RECOMMENDATION", '''
        SELECT asset_id,asset_role,module2_score,confidence,risk_level,
               target_weight,monthly_dca_usd,target_units,action,rationale
        FROM latest_portfolio_recommendations
        ORDER BY target_weight DESC
    ''')
    show(conn, "PORTFOLIO SUMMARY", '''
        SELECT * FROM latest_portfolio_summary
    ''')
    show(conn, "RISK-ADJUSTED RANKING", '''
        SELECT asset_id,risk_adjusted_rank,annualized_return_pct,
               annualized_volatility_pct,downside_volatility_pct,
               sharpe_ratio,sortino_ratio,beta_to_btc,
               correlation_to_btc,max_drawdown_pct,calmar_ratio
        FROM latest_risk_metrics ORDER BY risk_adjusted_rank
    ''')
    show(conn, "VALUATION ZONES", '''
        SELECT asset_id,current_price_usd,fair_value_usd,buy_below_usd,
               strong_buy_below_usd,trim_above_usd,
               overextended_above_usd,upside_to_fair_value_pct,
               valuation_label
        FROM latest_valuation_zones
        ORDER BY upside_to_fair_value_pct DESC
    ''')
    show(conn, "REBALANCE RECOMMENDATIONS", '''
        SELECT asset_id,current_weight,target_weight,weight_difference,
               dollar_adjustment,action,priority,rationale
        FROM latest_rebalance_recommendations
        ORDER BY priority,ABS(weight_difference) DESC
    ''')
    show(conn, "POSITION RISK CONTRIBUTIONS", '''
        SELECT asset_id,target_weight,marginal_volatility_contribution,
               percent_of_portfolio_risk,maximum_recommended_weight,
               risk_budget_status
        FROM latest_position_risk_contributions
        ORDER BY percent_of_portfolio_risk DESC
    ''')
    show(conn, "ONE-YEAR SCENARIOS", '''
        SELECT asset_id,scenario,annual_return_assumption_pct,
               projected_price_usd,projected_multiple
        FROM latest_scenario_projections
        WHERE horizon_years=1
        ORDER BY asset_id,
          CASE scenario WHEN 'BEAR' THEN 1 WHEN 'BASE' THEN 2 ELSE 3 END
    ''')
    conn.close()

if __name__ == "__main__":
    main()
