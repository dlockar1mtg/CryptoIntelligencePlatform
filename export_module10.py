from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import MODULE10_SCHEMA

EXPORTS = {
    "latest_research_universe": "SELECT * FROM latest_research_universe",
    "research_universe": "SELECT * FROM research_universe",
    "research_market_daily": "SELECT * FROM research_market_daily",
    "latest_research_breadth": "SELECT * FROM latest_research_breadth",
    "research_market_breadth": "SELECT * FROM research_market_breadth",
    "latest_derivatives_funding": "SELECT * FROM latest_derivatives_funding",
    "derivatives_funding_daily": "SELECT * FROM derivatives_funding_daily",
    "derivatives_open_interest": "SELECT * FROM derivatives_open_interest",
    "latest_sentiment": "SELECT * FROM latest_sentiment",
    "crypto_sentiment_daily": "SELECT * FROM crypto_sentiment_daily",
    "latest_defi_snapshot": "SELECT * FROM latest_defi_snapshot",
    "defi_market_snapshot": "SELECT * FROM defi_market_snapshot",
    "calibrated_probability_models": "SELECT * FROM calibrated_probability_models",
    "latest_calibrated_predictive": "SELECT * FROM latest_calibrated_predictive",
    "calibrated_predictive_current": "SELECT * FROM calibrated_predictive_current",
    "module10_runs": "SELECT * FROM module10_runs",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    for schema in [
        MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
        MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
        MODULE9_SCHEMA, MODULE10_SCHEMA,
    ]:
        conn.execute(schema)
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
