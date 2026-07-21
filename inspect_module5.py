from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA

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
    conn.execute(MODULE5_SCHEMA)

    show(conn, "MULTI-HORIZON RETURNS", '''
        SELECT asset_id,cagr_1y_pct,cagr_3y_pct,cagr_5y_pct,
               cagr_since_inception_pct,blended_cagr_pct,
               available_weight,history_days
        FROM latest_multi_horizon_returns
        ORDER BY blended_cagr_pct DESC NULLS LAST
    ''')
    show(conn, "CYCLE ANALYTICS", '''
        SELECT asset_id,cycle_phase,days_since_ath,ath_drawdown_pct,
               drawdown_percentile,price_percentile_3y,
               momentum_percentile,volatility_percentile,
               macd_histogram,adx_14
        FROM latest_cycle_analytics
        ORDER BY asset_id
    ''')
    show(conn, "EXPECTED RETURNS", '''
        SELECT asset_id,blended_cagr_pct,valuation_score,momentum_score,
               trend_quality_score,macro_score,market_regime_score,
               expected_return_1y_pct,confidence
        FROM latest_expected_returns
        ORDER BY expected_return_1y_pct DESC
    ''')
    show(conn, "RISK-OPTIMIZED ALLOCATIONS", '''
        SELECT asset_id,pre_risk_weight,post_risk_weight,
               risk_contribution_pct,risk_budget_pct,adjustment,status
        FROM latest_optimized_allocations
        ORDER BY post_risk_weight DESC
    ''')
    conn.close()

if __name__ == "__main__":
    main()
