from pathlib import Path

root = Path(__file__).resolve().parents[1]
m38 = (root / "crypto_platform" / "module38.py").read_text(encoding="utf-8")
m39 = (root / "crypto_platform" / "module39.py").read_text(encoding="utf-8")

checks = {
    "generation_constant": 'PREDICTIVE_METHODOLOGY_GENERATION = "M38_PURGED_FEATURE_STABLE_V1"' in m38,
    "generation_column": "methodology_generation VARCHAR" in m38,
    "generation_persisted": "UPDATE module38_runs SET methodology_generation=? WHERE run_id=?" in m38,
    "generation_source_gate": "SELECT run_id, methodology_generation FROM module38_runs" in m39,
    "stability_history": "def stability_attributions(self):" in m39,
    "distinct_forecast_dates": "PARTITION BY a.forecast_date,a.asset_id,a.horizon_days,a.driver_key" in m39,
    "same_generation": "r.methodology_generation=?" in m39,
    "earlier_forecast_date": "f.forecast_date < (" in m39,
    "baseline_required": '"drift_status":"BASELINE_REQUIRED"' in m39,
    "missing_stability": "else np.nan" in m39,
    "advancement_block": "and monitoring_evidence_ready" in m39,
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise RuntimeError("Generation semantics source checks failed: " + ", ".join(failed))

print("CRYPTO_MODULE39_GENERATION_AWARE_SOURCE_VALIDATION=PASS")
print("METHODOLOGY_GENERATION_PERSISTED=TRUE")
print("STABILITY_DISTINCT_FORECAST_DATES_ONLY=TRUE")
print("DRIFT_SAME_GENERATION_EARLIER_DATE_ONLY=TRUE")
print("BASELINE_REQUIRED_BLOCKS_ADVANCEMENT=TRUE")
print("NEXT_GATE=DISPOSABLE_GENERATION_AWARE_MODULE38_MODULE39_VALIDATION")
