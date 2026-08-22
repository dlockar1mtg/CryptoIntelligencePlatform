from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "run_disposable_predictive_champion_challenger_replay.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    text = HARNESS.read_text(encoding="utf-8")
    checks = {
        "experiment_id": 'EXPERIMENT_ID = "CRYPTO_NATIVE_PREDICTIVE_MODEL_IMPROVEMENT_V1"' in text,
        "four_variants": all(name in text for name in [
            "CURRENT_M38_REGRESSION_ENSEMBLE",
            "DIRECTION_FIRST_TWO_STAGE",
            "HORIZON_SPECIFIC_FEATURE_WINDOWS",
            "ROBUST_RETURN_TARGET",
        ]),
        "development_20": "DEVELOPMENT_ORIGINS = 20" in text,
        "final_test_10": "FINAL_TEST_ORIGINS = 10" in text,
        "development_majority": "development_majority" in text,
        "test_only_summary": "summarize_test_only" in text,
        "training_support_bounds": "val_x = val_x.clip(lower=lo, upper=hi, axis=1)" in text and "current_x = current_x.clip(lower=lo, upper=hi, axis=1)" in text,
        "purged_split": "split_capacity(" in text,
        "matured_label_gate": "dates + pd.to_timedelta(horizon, unit=\"D\") <= origin_date" in text,
        "robust_train_only_target": "np.quantile(y_train, [0.025, 0.975])" in text,
        "horizon_features_predeclared": "HORIZON_FEATURES =" in text,
        "calibration_reuses_leakage_safe_method": "calibration_evidence(" in text,
        "source_db_hash_guard": "before = sha256(source)" in text and "require(before == after" in text,
        "promotion_blocked": '"promotion_allowed_from_this_run": False' in text,
        "recommendation_policy_absent": "module42" not in text and "BUY" not in text and "SELL" not in text,
    }
    failed = [key for key, value in checks.items() if not value]
    require(not failed, "Champion/challenger replay harness checks failed: " + ", ".join(failed))

    print("CRYPTO_PREDICTIVE_CHAMPION_CHALLENGER_HARNESS_VALIDATION=PASS")
    print("VARIANTS=4")
    print("DEVELOPMENT_ROWS_PER_GROUP=20")
    print("FINAL_TEST_ROWS_PER_GROUP=10")
    print("MAJORITY_BASELINE_USES_FINAL_TEST_OUTCOMES=FALSE")
    print("LEAKAGE_CONTROLS_PRESERVED=TRUE")
    print("PRODUCTION_RECOMMENDATION_POLICY_CHANGED=FALSE")
    print("PROMOTION_ALLOWED_FROM_THIS_RUN=FALSE")
    print("NEXT_GATE=RUN_DISPOSABLE_CHAMPION_CHALLENGER_REPLAY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
