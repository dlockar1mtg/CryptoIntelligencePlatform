from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "crypto_platform" / "module39.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    require(count == 1, f"Expected exactly one {label}; found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")

    import_anchor = "from crypto_platform.module38 import MODULE38_SCHEMA\n"
    import_insert = (
        "from crypto_platform.module38 import MODULE38_SCHEMA\n"
        "from crypto_platform.module39_validation import (\n"
        "    apply_calibration,\n"
        "    build_true_replay_evidence,\n"
        ")\n"
    )
    if "from crypto_platform.module39_validation import" not in text:
        text = replace_once(text, import_anchor, import_insert, "Module 39 validation import anchor")

    schema_anchor = '''CREATE TABLE IF NOT EXISTS m39_feature_stability(\n'''
    gap_schema = '''CREATE TABLE IF NOT EXISTS m39_evidence_gaps(\n    run_id VARCHAR,\n    asset_id VARCHAR,\n    horizon_days INTEGER,\n    evidence_gap VARCHAR,\n    available_candidates INTEGER,\n    required_candidates INTEGER,\n    predictive_skill_certified BOOLEAN,\n    calculated_at_utc TIMESTAMPTZ,\n    PRIMARY KEY(run_id, asset_id, horizon_days, evidence_gap)\n);\n\nCREATE TABLE IF NOT EXISTS m39_feature_stability(\n'''
    if "CREATE TABLE IF NOT EXISTS m39_evidence_gaps" not in text:
        text = replace_once(text, schema_anchor, gap_schema, "evidence-gap schema anchor")

    view_anchor = '''CREATE OR REPLACE VIEW latest_m39_feature_stability AS\n'''
    gap_view = '''CREATE OR REPLACE VIEW latest_m39_evidence_gaps AS\nSELECT * FROM m39_evidence_gaps\nWHERE run_id=(SELECT run_id FROM module39_runs ORDER BY started_at_utc DESC LIMIT 1)\nORDER BY asset_id,horizon_days;\n\nCREATE OR REPLACE VIEW latest_m39_feature_stability AS\n'''
    if "CREATE OR REPLACE VIEW latest_m39_evidence_gaps" not in text:
        text = replace_once(text, view_anchor, gap_view, "evidence-gap view anchor")

    function_pattern = re.compile(
        r"    def calibration\(self,forecasts,validation\):.*?(?=    def stability\(self,attribution\):)",
        flags=re.S,
    )
    replacement = '''    def true_replay(self):\n        return build_true_replay_evidence(self.conn, self.settings)\n\n    def calibration(self, forecasts, replay_bundle):\n        evidence = replay_bundle["calibration"].copy()\n        specs = replay_bundle["calibration_specs"]\n        rows = []\n        calibrated = []\n        gap_keys = set()\n        gaps = replay_bundle["evidence_gaps"]\n        if not gaps.empty:\n            gap_keys = set(\n                zip(gaps["asset_id"], gaps["horizon_days"].astype(int))\n            )\n\n        for _, forecast in forecasts.iterrows():\n            asset = str(forecast["asset_id"])\n            horizon = int(forecast["horizon_days"])\n            key = (asset, horizon)\n            raw_probability = float(forecast["probability_positive"])\n            subset = evidence[\n                (evidence.asset_id == asset)\n                & (evidence.horizon_days == horizon)\n            ]\n\n            if key in gap_keys or subset.empty or key not in specs:\n                selected_method = "UNCALIBRATED_EVIDENCE_GAP"\n                calibrated_probability = raw_probability\n                raw_brier = calibrated_brier = np.nan\n                raw_ll = calibrated_ll = np.nan\n                observed_rate = np.nan\n                validation_rows = 0\n                improvement = 0.0\n            else:\n                row = subset.iloc[0]\n                selected_method = str(row["calibration_method"])\n                calibrated_probability = apply_calibration(\n                    specs[key], raw_probability\n                )\n                raw_brier = float(row["raw_brier_score"])\n                calibrated_brier = float(row["calibrated_brier_score"])\n                raw_ll = float(row["raw_log_loss"])\n                calibrated_ll = float(row["calibrated_log_loss"])\n                observed_rate = float(row["observed_positive_rate"])\n                validation_rows = int(row["validation_rows"])\n                improvement = float(row["calibration_improvement_pct"])\n\n            rows.append({\n                "run_id": self.run_id,\n                "asset_id": asset,\n                "horizon_days": horizon,\n                "calibration_method": selected_method,\n                "validation_rows": validation_rows,\n                "raw_brier_score": raw_brier,\n                "calibrated_brier_score": calibrated_brier,\n                "raw_log_loss": raw_ll,\n                "calibrated_log_loss": calibrated_ll,\n                "raw_mean_probability": raw_probability,\n                "calibrated_mean_probability": float(calibrated_probability),\n                "observed_positive_rate": observed_rate,\n                "calibration_improvement_pct": improvement,\n                "selected": True,\n                "calculated_at_utc": utcnow(),\n            })\n\n            validation = self.model_validation()\n            model_subset = validation[\n                (validation.asset_id == asset)\n                & (validation.horizon_days == horizon)\n            ]\n            residual_scale = (\n                float(model_subset["validation_rmse_pct"].median())\n                if not model_subset.empty\n                else float(\n                    forecast["upper_return_pct"]\n                    - forecast["lower_return_pct"]\n                ) / 2\n            )\n            alpha = float(self.cfg["conformal_alpha"])\n            multiplier = 1.645 if alpha <= 0.10 else 1.282\n            half_width = max(residual_scale * multiplier, 1.0)\n            lower = float(forecast["predicted_return_pct"] - half_width)\n            upper = float(forecast["predicted_return_pct"] + half_width)\n            calibrated.append({\n                "run_id": self.run_id,\n                "forecast_date": forecast["forecast_date"],\n                "asset_id": asset,\n                "horizon_days": horizon,\n                "predicted_return_pct": float(forecast["predicted_return_pct"]),\n                "raw_probability_positive": raw_probability,\n                "calibrated_probability_positive": float(\n                    np.clip(calibrated_probability, 0, 1)\n                ),\n                "conformal_lower_return_pct": lower,\n                "conformal_upper_return_pct": upper,\n                "interval_width_pct": upper - lower,\n                "calibration_method": selected_method,\n                "forecast_confidence": float(forecast["forecast_confidence"]),\n                "forecast_status": forecast["forecast_status"],\n                "calculated_at_utc": utcnow(),\n            })\n        return pd.DataFrame(rows), pd.DataFrame(calibrated)\n\n    def rolling_validation(self, replay_bundle):\n        rolling = replay_bundle["rolling"].copy()\n        if rolling.empty:\n            return rolling\n        rolling["run_id"] = self.run_id\n        rolling["calculated_at_utc"] = utcnow()\n        columns = [\n            "run_id", "asset_id", "horizon_days", "fold_number",\n            "training_rows", "testing_rows", "training_end_date",\n            "testing_start_date", "testing_end_date", "mae_pct",\n            "rmse_pct", "directional_accuracy_pct", "brier_score",\n            "interval_coverage_pct", "calculated_at_utc",\n        ]\n        return rolling[columns]\n\n'''
    text, count = function_pattern.subn(replacement, text, count=1)
    require(count == 1, f"Expected one calibration/rolling function block; replaced {count}")

    old_run = '''            calibration,calibrated=self.calibration(forecasts,validation)\n            rolling=self.rolling_validation(forecasts,validation)\n            stability=self.stability(attribution)\n'''
    new_run = '''            replay_bundle=self.true_replay()\n            calibration,calibrated=self.calibration(forecasts,replay_bundle)\n            rolling=self.rolling_validation(replay_bundle)\n            gaps=replay_bundle["evidence_gaps"].copy()\n            if not gaps.empty:\n                gaps["run_id"]=self.run_id\n                gaps["calculated_at_utc"]=utcnow()\n                gaps=gaps[[\n                    "run_id","asset_id","horizon_days","evidence_gap",\n                    "available_candidates","required_candidates",\n                    "predictive_skill_certified","calculated_at_utc",\n                ]]\n            stability=self.stability(attribution)\n'''
    text = replace_once(text, old_run, new_run, "run replay invocation")

    old_tables = '''                ("m39_rolling_origin_validation",rolling),\n                ("m39_feature_stability",stability),\n'''
    new_tables = '''                ("m39_rolling_origin_validation",rolling),\n                ("m39_evidence_gaps",gaps),\n                ("m39_feature_stability",stability),\n'''
    text = replace_once(text, old_tables, new_tables, "evidence-gap persistence")

    old_brier = '''            mean_brier=float(calibration["calibrated_brier_score"].mean())\n            coverage=float(rolling["interval_coverage_pct"].mean()) if not rolling.empty else 0.0\n            direction=float(rolling["directional_accuracy_pct"].mean()) if not rolling.empty else 0.0\n'''
    new_brier = '''            supported_calibration=calibration[calibration["validation_rows"]>0]\n            mean_brier=float(supported_calibration["calibrated_brier_score"].mean()) if not supported_calibration.empty else np.nan\n            coverage=float(rolling["interval_coverage_pct"].mean()) if not rolling.empty else 0.0\n            direction=float(rolling["directional_accuracy_pct"].mean()) if not rolling.empty else 0.0\n            model_minus_majority=float(replay_bundle["model_minus_majority_accuracy_pct_points"])\n'''
    text = replace_once(text, old_brier, new_brier, "truthful replay summary metrics")

    old_evidence = '''                and calibration["validation_rows"].sum()\n                >=int(\n'''
    new_evidence = '''                and supported_calibration["validation_rows"].sum()\n                >=int(\n'''
    text = replace_once(text, old_evidence, new_evidence, "supported calibration evidence gate")

    old_pass = '''                and direction>=float(self.cfg["validation"]["minimum_directional_accuracy_pct"])\n                and current_drift!="CRITICAL"\n'''
    new_pass = '''                and direction>=float(self.cfg["validation"]["minimum_directional_accuracy_pct"])\n                and model_minus_majority>0\n                and gaps.empty\n                and current_drift!="CRITICAL"\n'''
    text = replace_once(text, old_pass, new_pass, "baseline-adjusted advancement gate")

    old_notes = '''                 "Probability calibration, conformal intervals, rolling validation, "\n                 "feature stability, drift monitoring, and realized scorecards completed.",\n'''
    new_notes = '''                 "True chronological point-in-time replay, realized-outcome probability calibration, "\n                 "explicit evidence gaps, conformal intervals, feature stability, drift monitoring, "\n                 f"and realized scorecards completed. Model-minus-majority directional accuracy: {model_minus_majority:.4f} pp.",\n'''
    text = replace_once(text, old_notes, new_notes, "truthful Module 39 run notes")

    TARGET.write_text(text, encoding="utf-8", newline="")
    print("CRYPTO_MODULE39_TRUE_REPLAY_SOURCE_REMEDIATION=PASS")
    print(f"UPDATED_FILE={TARGET}")
    print("PROXY_CALIBRATION_REMOVED=TRUE")
    print("PSEUDO_ROLLING_VALIDATION_REMOVED=TRUE")
    print("EXPLICIT_EVIDENCE_GAPS_PERSISTED=TRUE")
    print("BASELINE_ADJUSTED_ADVANCEMENT_GATE=TRUE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
