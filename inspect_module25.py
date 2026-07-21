from crypto_platform.platform import load_all, connect
from crypto_platform.module25 import MODULE25_SCHEMA

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
    conn.execute(MODULE25_SCHEMA)

    show(conn, "CURRENT MARKET REGIME", """
        SELECT observation_date,
               dominant_regime,
               secondary_regime,
               regime_confidence*100
                   AS regime_confidence_pct,
               model_agreement*100
                   AS model_agreement_pct,
               days_in_regime,
               expected_persistence_days,
               transition_risk*100
                   AS transition_risk_pct,
               liquidity_contribution,
               trend_contribution,
               risk_contribution,
               recovery_contribution,
               change_pressure
        FROM latest_market_regime_daily
        ORDER BY observation_date DESC
        LIMIT 1
    """)

    show(conn, "CURRENT REGIME PROBABILITIES", """
        SELECT observation_date,
               liquidity_expansion_probability*100
                   AS liquidity_expansion_pct,
               momentum_bull_probability*100
                   AS momentum_bull_pct,
               recovery_probability*100
                   AS recovery_pct,
               range_bound_probability*100
                   AS range_bound_pct,
               macro_stress_probability*100
                   AS macro_stress_pct,
               volatility_shock_probability*100
                   AS volatility_shock_pct,
               dominant_regime,
               secondary_regime,
               regime_confidence*100
                   AS confidence_pct,
               model_agreement*100
                   AS model_agreement_pct
        FROM latest_market_regime_probabilities
        ORDER BY observation_date DESC
        LIMIT 1
    """)

    show(conn, "CURRENT FEATURE CONTRIBUTIONS", """
        SELECT contribution_group,
               contribution_value,
               rank,
               explanation
        FROM latest_market_regime_contributions
        WHERE observation_date=(
            SELECT MAX(observation_date)
            FROM latest_market_regime_contributions
        )
        ORDER BY rank
    """)

    show(conn, "REGIME TRANSITION OUTLOOK", """
        SELECT from_regime,
               to_regime,
               transition_count,
               transition_probability*100
                   AS transition_probability_pct,
               average_days_before_transition,
               median_days_before_transition
        FROM latest_market_regime_transitions
        WHERE from_regime=(
            SELECT dominant_regime
            FROM latest_market_regime_daily
            ORDER BY observation_date DESC
            LIMIT 1
        )
        ORDER BY transition_probability DESC
    """)

    show(conn, "REGIME DURATION STATISTICS", """
        SELECT regime,
               episodes,
               average_duration_days,
               median_duration_days,
               minimum_duration_days,
               maximum_duration_days
        FROM latest_market_regime_durations
    """)

    show(conn, "VALIDATION RESULTS", """
        SELECT validation_key,
               validation_value,
               threshold_value,
               status,
               message
        FROM latest_market_regime_validation
    """)

    show(conn, "RECENT REGIME HISTORY", """
        SELECT observation_date,
               dominant_regime,
               secondary_regime,
               regime_confidence*100
                   AS confidence_pct,
               model_agreement*100
                   AS model_agreement_pct,
               days_in_regime,
               transition_risk*100
                   AS transition_risk_pct
        FROM latest_market_regime_daily
        ORDER BY observation_date DESC
        LIMIT 30
    """)

    show(conn, "LATEST MODULE 25 RUNS", """
        SELECT started_at_utc,
               completed_at_utc,
               status,
               feature_rows,
               classified_days,
               transitions,
               duration_rows,
               current_regime,
               current_confidence,
               reproducibility_match_pct,
               stability_score,
               validation_status,
               notes
        FROM module25_runs
        ORDER BY started_at_utc DESC
        LIMIT 10
    """)

    conn.close()

if __name__ == "__main__":
    main()
