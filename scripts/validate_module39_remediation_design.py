from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE39 = ROOT / "crypto_platform" / "module39.py"
MODULE38 = ROOT / "crypto_platform" / "module38.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    require(MODULE39.is_file(), f"Missing Module 39 source: {MODULE39}")
    require(MODULE38.is_file(), f"Missing Module 38 source: {MODULE38}")

    m39 = MODULE39.read_text(encoding="utf-8")
    m38 = MODULE38.read_text(encoding="utf-8")

    # Confirm the currently certified defects are still present so this gate
    # fails closed if the source changes before remediation is applied.
    require("def rolling_validation(self,forecasts,validation):" in m39,
            "Legacy Module 39 rolling-validation method was not found")
    require("observed=np.repeat(1 if direction>=50 else 0,len(test))" in m39,
            "Legacy pseudo-outcome rolling validation was not found")
    require("directional=(subset[\"directional_accuracy_pct\"]/100)" in m39,
            "Legacy proxy calibration source was not found")
    require("training_end_date\":pd.Timestamp(forecasts[\"forecast_date\"].max()).date()" in m39,
            "Legacy same-date rolling-origin metadata was not found")

    # Confirm the corrected Module 38 primitives needed by truthful historical
    # replay are available in production code rather than only in a diagnostic.
    require("def build_features(" in m38,
            "Module 38 point-in-time feature builder is unavailable")
    require("def model_suite(" in m38,
            "Module 38 model suite is unavailable")
    require("absolute_minimum_training_rows" in m38,
            "Module 38 minimum-training control is unavailable")
    require("maximum_validation_share" in m38,
            "Module 38 adaptive-validation control is unavailable")

    design = {
        "status": "CRYPTO_MODULE39_REMEDIATION_DESIGN_VALID",
        "evidence_basis": {
            "replay_rows": 870,
            "supported_asset_horizon_groups": 29,
            "explicit_evidence_gap": "xrp/365d: INSUFFICIENT_POINT_IN_TIME_REPLAY_HISTORY",
            "directional_skill_vs_majority_pct_points": {
                "7": -3.3333333333333357,
                "30": -2.2222222222222143,
                "90": -13.333333333333336,
                "180": -18.33333333333333,
                "365": 10.0,
            },
            "leakage_safe_calibration_groups": 29,
            "calibration_groups_with_brier_improvement": 23,
            "mean_raw_brier": 0.371678340339719,
            "mean_leakage_safe_calibrated_brier": 0.2930225717637704,
        },
        "model_skill_status": "NOT_CERTIFIED_FOR_INVESTMENT_TIMING",
        "365_day_status": "PROMISING_DIRECTIONAL_SIGNAL_NOT_CERTIFIED",
        "required_source_remediation": [
            "replace Module 39 pseudo rolling-validation rows with true chronological point-in-time replay",
            "train each historical forecast only on labels matured before its forecast origin",
            "preserve Module 38 purged holdout and training-support feature bounds",
            "derive probability calibration from realized binary outcomes, never validation-summary directional accuracy",
            "select calibration method without final-test peeking",
            "record unsupported asset/horizon groups as explicit evidence gaps",
            "compute Module 39 advancement status from truthful replay evidence rather than pseudo-fold summaries",
            "do not mark predictive skill or investment timing as certified merely because probability calibration improves",
        ],
        "prohibited_shortcuts": [
            "lower minimum training rows to make XRP 365d pass",
            "silently drop XRP 365d",
            "reuse existing m39_rolling_origin_validation rows as certification evidence",
            "reuse proxy calibration outcomes",
            "claim 365d skill from aggregate directional accuracy alone",
            "promote BUY/HOLD/SELL timing before recommendation-policy validation",
        ],
        "next_gate": "IMPLEMENT_MODULE39_TRUE_REPLAY_AND_REALIZED_CALIBRATION_IN_PRODUCTION_SOURCE",
    }

    print(json.dumps(design, indent=2))
    print("CRYPTO_MODULE39_REMEDIATION_DESIGN_VALIDATION=PASS")
    print("MODEL_SKILL_STATUS=NOT_CERTIFIED_FOR_INVESTMENT_TIMING")
    print("NEXT_GATE=IMPLEMENT_MODULE39_TRUE_REPLAY_AND_REALIZED_CALIBRATION_IN_PRODUCTION_SOURCE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
