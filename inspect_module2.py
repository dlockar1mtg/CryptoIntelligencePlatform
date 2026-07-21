from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA

def show(conn, title, sql):
    print(f"\n{title}")
    print("-" * len(title))
    frame = conn.execute(sql).fetchdf()
    print(frame.to_string(index=False) if not frame.empty else "No data.")

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE2_SCHEMA)
    show(conn, "LATEST MODULE 2 RUNS", '''
        SELECT started_at_utc, completed_at_utc, status, signal_date,
               assets_scored, assets_skipped, notes
        FROM module2_runs ORDER BY started_at_utc DESC LIMIT 10
    ''')
    show(conn, "LATEST ASSET SIGNALS", '''
        SELECT asset_id, observation_date, price_usd, overall_score,
               confidence, signal, risk_level, momentum_score, trend_score,
               liquidity_score, macro_score, risk_score,
               relative_value_score
        FROM latest_asset_signals
        ORDER BY overall_score DESC NULLS LAST
    ''')
    show(conn, "LATEST MACRO REGIME", '''
        SELECT observation_date, regime_label, macro_score, confidence,
               liquidity_score, risk_appetite_score, real_yield, vix,
               high_yield_spread, dollar_90d_change_pct, m2_yoy_pct,
               unemployment_6m_change
        FROM latest_macro_regime
    ''')
    show(conn, "LATEST MARKET REGIME", '''
        SELECT observation_date, regime_label, market_score, confidence,
               market_cap_30d_change_pct AS tracked_cap_30d_change_pct,
               volume_30d_change_pct AS tracked_volume_30d_change_pct,
               breadth_score AS positive_asset_breadth_pct,
               btc_dominance_30d_change AS alt_minus_btc_30d_return_pct,
               btc_dominance_pct, eth_dominance_pct,
               total_market_cap_usd, total_volume_usd
        FROM latest_market_regime
    ''')
    show(conn, "LATEST SCORE COMPONENTS", '''
        SELECT c.asset_id, c.component_name, c.raw_value,
               c.normalized_score, c.weight, c.weighted_score, c.explanation
        FROM score_components c
        JOIN (
            SELECT run_id FROM module2_runs
            ORDER BY started_at_utc DESC LIMIT 1
        ) r USING(run_id)
        ORDER BY c.asset_id, c.component_name
    ''')
    conn.close()

if __name__ == "__main__":
    main()
