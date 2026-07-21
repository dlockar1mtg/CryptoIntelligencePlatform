from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA

EXPORTS = {
    "latest_ml_predictions": "SELECT * FROM latest_ml_predictions",
    "ml_predictions_current": "SELECT * FROM ml_predictions_current",
    "latest_ml_feature_importance":
        "SELECT * FROM latest_ml_feature_importance",
    "ml_feature_importance": "SELECT * FROM ml_feature_importance",
    "latest_ml_shap_explanations":
        "SELECT * FROM latest_ml_shap_explanations",
    "ml_shap_explanations": "SELECT * FROM ml_shap_explanations",
    "latest_ml_walk_forward_results":
        "SELECT * FROM latest_ml_walk_forward_results",
    "ml_walk_forward_results": "SELECT * FROM ml_walk_forward_results",
    "latest_ml_regime_validation":
        "SELECT * FROM latest_ml_regime_validation",
    "ml_walk_forward_regime_results":
        "SELECT * FROM ml_walk_forward_regime_results",
    "latest_ensemble_validation":
        "SELECT * FROM latest_ensemble_validation",
    "ensemble_validation_summary":
        "SELECT * FROM ensemble_validation_summary",
    "ml_model_registry": "SELECT * FROM ml_model_registry",
    "module8_runs": "SELECT * FROM module8_runs",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    for schema in [
        MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
        MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
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
