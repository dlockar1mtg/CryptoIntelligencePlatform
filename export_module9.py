from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA

EXPORTS = {
    "latest_predictive_classifications":
        "SELECT * FROM latest_predictive_classifications",
    "predictive_classification_current":
        "SELECT * FROM predictive_classification_current",
    "latest_calibrated_walk_forward":
        "SELECT * FROM latest_calibrated_walk_forward",
    "calibrated_walk_forward_results":
        "SELECT * FROM calibrated_walk_forward_results",
    "latest_probability_calibration":
        "SELECT * FROM latest_probability_calibration",
    "probability_calibration_bins":
        "SELECT * FROM probability_calibration_bins",
    "latest_regime_model_validation":
        "SELECT * FROM latest_regime_model_validation",
    "regime_model_validation":
        "SELECT * FROM regime_model_validation",
    "latest_predictive_promotion":
        "SELECT * FROM latest_predictive_promotion",
    "predictive_promotion_summary":
        "SELECT * FROM predictive_promotion_summary",
    "module9_runs": "SELECT * FROM module9_runs",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    for schema in [
        MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
        MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
        MODULE9_SCHEMA,
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
