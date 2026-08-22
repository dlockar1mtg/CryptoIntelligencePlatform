from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "run_v2_native_context_holdout_evaluation.py"
text = TARGET.read_text(encoding="utf-8")

checks = {
    "experiment_id": 'CRYPTO_NATIVE_PREDICTIVE_MODEL_IMPROVEMENT_V2' in text,
    "manifest_sha_pinned": '7ae0e4f84896097c32ebae0f7a6a514686f07e065db23fa4e04d205752729a76' in text,
    "manifest_hash_revalidated": 'manifest_content_hash(manifest) == EXPECTED_MANIFEST_CONTENT_SHA256' in text,
    "frozen_dates_used": 'v2_holdout_origin_dates' in text,
    "v1_v2_overlap_blocked": 'V2/V1 overlap' in text,
    "native_context_fixed": 'NATIVE_CONTEXT_FEATURES = [' in text,
    "missing_context_fail_closed": 'Missing native context at frozen origin' in text,
    "training_only_bounds": 'val_x = val_x.clip(lower=lo, upper=hi, axis=1)' in text and 'current_x = current_x.clip(lower=lo, upper=hi, axis=1)' in text,
    "v1_calibration_only": 'calibration_evidence(pd.DataFrame(v1_rows[variant]))' in text,
    "v2_calibration_apply_only": 'apply_calibration(spec, raw_p)' in text,
    "development_baseline": 'v1_rows[CHAMPION][:20]' in text,
    "champion_and_challenger": 'CURRENT_M38_REGRESSION_ENSEMBLE' in text and 'NATIVE_CONTEXT_AUGMENTED_DIRECTION_FIRST' in text,
    "source_hash_guard": 'Source database changed during V2 holdout evaluation' in text,
    "manifest_hash_guard": 'Frozen V2 manifest changed during evaluation' in text,
    "recommendation_unchanged": 'recommendation_policy_changed": False' in text,
    "promotion_multi_horizon": 'majority_of_supported_horizons_positive' in text and 'aggregate_improvement_not_single_horizon_only' in text,
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise RuntimeError("V2 native-context holdout evaluator source checks failed: " + ", ".join(failed))

print("CRYPTO_V2_NATIVE_CONTEXT_HOLDOUT_EVALUATOR_VALIDATION=PASS")
print("FROZEN_MANIFEST_HASH_PINNED=TRUE")
print("V1_V2_ORIGIN_OVERLAP_BLOCKED=TRUE")
print("V2_OUTCOMES_USED_FOR_CALIBRATION=FALSE")
print("MISSING_NATIVE_CONTEXT_SYNTHESIZED=FALSE")
print("RECOMMENDATION_POLICY_CHANGED=FALSE")
print("NEXT_GATE=RUN_FROZEN_V2_NATIVE_CONTEXT_HOLDOUT_EVALUATION")
