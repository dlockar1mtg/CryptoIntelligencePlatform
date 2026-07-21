from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import MODULE10_SCHEMA
from crypto_platform.module11 import MODULE11_SCHEMA

EXPORTS = {
    "latest_symbol_map": "SELECT * FROM latest_symbol_map",
    "exchange_symbol_map": "SELECT * FROM exchange_symbol_map",
    "historical_provider_health": "SELECT * FROM historical_provider_health",
    "latest_history_quality": "SELECT * FROM latest_history_quality",
    "research_history_quality": "SELECT * FROM research_history_quality",
    "research_asset_taxonomy": "SELECT * FROM research_asset_taxonomy",
    "latest_sector_snapshot": "SELECT * FROM latest_sector_snapshot",
    "sector_market_snapshot": "SELECT * FROM sector_market_snapshot",
    "latest_derivatives_status": "SELECT * FROM latest_derivatives_status",
    "derivatives_collection_status": "SELECT * FROM derivatives_collection_status",
    "probability_calibration_registry": "SELECT * FROM probability_calibration_registry",
    "latest_robust_calibrated_predictive": "SELECT * FROM latest_robust_calibrated_predictive",
    "robust_calibrated_predictive_current": "SELECT * FROM robust_calibrated_predictive_current",
    "module11_runs": "SELECT * FROM module11_runs",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    for schema in [
        MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
        MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
        MODULE9_SCHEMA, MODULE10_SCHEMA, MODULE11_SCHEMA,
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
