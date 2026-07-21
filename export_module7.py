from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA

EXPORTS = {
    "latest_score_bin_performance": "SELECT * FROM latest_score_bin_performance",
    "score_bin_performance": "SELECT * FROM score_bin_performance",
    "latest_learned_signal_thresholds": "SELECT * FROM latest_learned_signal_thresholds",
    "learned_signal_thresholds": "SELECT * FROM learned_signal_thresholds",
    "latest_feature_importance": "SELECT * FROM latest_feature_importance",
    "feature_importance_results": "SELECT * FROM feature_importance_results",
    "latest_walk_forward_results": "SELECT * FROM latest_walk_forward_results",
    "walk_forward_results": "SELECT * FROM walk_forward_results",
    "walk_forward_predictions": "SELECT * FROM walk_forward_predictions",
    "latest_valuation_validation_summary": "SELECT * FROM latest_valuation_validation_summary",
    "valuation_validation_summary": "SELECT * FROM valuation_validation_summary",
    "latest_calibrated_signal_reliability": "SELECT * FROM latest_calibrated_signal_reliability",
    "calibrated_signal_reliability": "SELECT * FROM calibrated_signal_reliability",
    "module7_runs": "SELECT * FROM module7_runs",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    for schema in [
        MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
        MODULE6_SCHEMA, MODULE7_SCHEMA,
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
