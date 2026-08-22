from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE39 = ROOT / "crypto_platform" / "module39.py"
VALIDATION = ROOT / "crypto_platform" / "module39_validation.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    module39 = MODULE39.read_text(encoding="utf-8")
    validation = VALIDATION.read_text(encoding="utf-8")

    ast.parse(module39)
    ast.parse(validation)

    required_module39 = [
        "from crypto_platform.module39_validation import",
        "def true_replay(self):",
        "build_true_replay_evidence(self.conn, self.settings)",
        "UNCALIBRATED_EVIDENCE_GAP",
        "CREATE TABLE IF NOT EXISTS m39_evidence_gaps",
        "CREATE OR REPLACE VIEW latest_m39_evidence_gaps",
        "model_minus_majority>0",
        "and gaps.empty",
        '("m39_evidence_gaps",gaps)',
    ]
    for marker in required_module39:
        require(marker in module39, f"Missing Module 39 remediation marker: {marker}")

    prohibited_module39 = [
        'observed=(directional>=0.5).astype(int).to_numpy()',
        'raw=np.repeat(float(forecast["probability_positive"]),len(subset))',
        'training_end_date":pd.Timestamp(forecasts["forecast_date"].max()).date()',
        'testing_start_date":pd.Timestamp(forecasts["forecast_date"].max()).date()',
    ]
    for marker in prohibited_module39:
        require(marker not in module39, f"Legacy proxy validation remains: {marker}")

    required_validation = [
        "def point_in_time_prediction(",
        "dates + pd.to_timedelta(horizon, unit=\"D\") <= origin_date",
        "train_end = validation_start - int(horizon)",
        "StandardScaler()",
        "training_min = train_x.min(axis=0)",
        "training_max = train_x.max(axis=0)",
        "def calibration_evidence(",
        "train = rows.iloc[:15].copy()",
        "selection = rows.iloc[15:20].copy()",
        "test = rows.iloc[20:30].copy()",
        "def build_true_replay_evidence(conn, settings)",
        '"INSUFFICIENT_POINT_IN_TIME_REPLAY_HISTORY"',
        '"model_minus_majority_accuracy_pct_points"',
    ]
    for marker in required_validation:
        require(marker in validation, f"Missing replay validation marker: {marker}")

    require("minimum_training_rows = int(m38_cfg.get(\"absolute_minimum_training_rows\", 90))" in validation,
            "Replay minimum training standard changed unexpectedly")
    require("TEST_ORIGINS_PER_FOLD = 10" in validation,
            "Replay evidence density changed unexpectedly")

    print("CRYPTO_MODULE39_TRUE_REPLAY_SOURCE_VALIDATION=PASS")
    print("TRUE_POINT_IN_TIME_REPLAY_PRESENT=TRUE")
    print("MATURED_LABEL_GATE_PRESENT=TRUE")
    print("PURGED_HOLDOUT_PRESERVED=TRUE")
    print("REALIZED_OUTCOME_CALIBRATION_PRESENT=TRUE")
    print("CALIBRATION_FINAL_TEST_PEEKING_REMOVED=TRUE")
    print("EXPLICIT_EVIDENCE_GAPS_PRESENT=TRUE")
    print("PROXY_CALIBRATION_PRESENT=FALSE")
    print("PSEUDO_ROLLING_VALIDATION_PRESENT=FALSE")
    print("PREDICTIVE_SKILL_AUTO_CERTIFICATION=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
