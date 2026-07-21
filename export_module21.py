from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module21 import MODULE21_SCHEMA

EXPORTS = {
    "latest_decision_model_quality":
        "SELECT * FROM latest_decision_model_quality",
    "decision_model_quality":
        "SELECT * FROM decision_model_quality",
    "latest_market_regime_probabilities":
        "SELECT * FROM latest_market_regime_probabilities",
    "market_regime_probabilities":
        "SELECT * FROM market_regime_probabilities",
    "latest_investment_probabilities":
        "SELECT * FROM latest_investment_probabilities",
    "investment_probabilities":
        "SELECT * FROM investment_probabilities",
    "latest_investment_risk_snapshot":
        "SELECT * FROM latest_investment_risk_snapshot",
    "investment_risk_snapshot":
        "SELECT * FROM investment_risk_snapshot",
    "latest_investment_decision":
        "SELECT * FROM latest_investment_decision",
    "investment_decisions":
        "SELECT * FROM investment_decisions",
    "latest_investment_decision_rationale":
        "SELECT * FROM latest_investment_decision_rationale",
    "investment_decision_rationale":
        "SELECT * FROM investment_decision_rationale",
    "latest_decision_shadow_periods":
        "SELECT * FROM latest_decision_shadow_periods",
    "decision_shadow_periods":
        "SELECT * FROM decision_shadow_periods",
    "latest_decision_shadow_summary":
        "SELECT * FROM latest_decision_shadow_summary",
    "decision_shadow_summary":
        "SELECT * FROM decision_shadow_summary",
    "module21_runs":
        "SELECT * FROM module21_runs",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE21_SCHEMA)
    directory = path_for(settings, "export_directory")
    directory.mkdir(parents=True, exist_ok=True)

    for name, sql in EXPORTS.items():
        frame = conn.execute(sql).fetchdf()
        output = directory / f"{name}.csv"
        frame.to_csv(output, index=False)
        print(f"{name}: {len(frame)} rows -> {output}")

    conn.close()

if __name__ == "__main__":
    main()
