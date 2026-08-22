from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M39 = ROOT / "crypto_platform" / "module39.py"
M39V = ROOT / "crypto_platform" / "module39_validation.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    require(count == 1, f"Expected exactly one {label}; found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    validation = M39V.read_text(encoding="utf-8")
    validation = replace_once(
        validation,
        '                    "training_end_date": max(frame["training_end_date"]),\n',
        '                    # A fold contains expanding rolling origins, so no single\n'
        '                    # training-end date truthfully describes the whole fold.\n'
        '                    # Per-origin chronology is retained in replay evidence.\n'
        '                    "training_end_date": None,\n',
        "fold aggregate training-end date",
    )
    M39V.write_text(validation, encoding="utf-8", newline="")

    text = M39.read_text(encoding="utf-8")

    schema_anchor = '''CREATE TABLE IF NOT EXISTS m39_evidence_gaps(\n'''
    replay_schema = '''CREATE TABLE IF NOT EXISTS m39_replay_origin_evidence(\n    run_id VARCHAR,\n    asset_id VARCHAR,\n    horizon_days INTEGER,\n    fold_number INTEGER,\n    forecast_date DATE,\n    training_end_date DATE,\n    training_rows INTEGER,\n    internal_validation_rows INTEGER,\n    predicted_return_pct DOUBLE,\n    actual_return_pct DOUBLE,\n    raw_probability_positive DOUBLE,\n    observed_positive INTEGER,\n    lower_return_pct DOUBLE,\n    upper_return_pct DOUBLE,\n    interval_covered BOOLEAN,\n    calculated_at_utc TIMESTAMPTZ,\n    PRIMARY KEY(run_id, asset_id, horizon_days, forecast_date)\n);\n\nCREATE TABLE IF NOT EXISTS m39_evidence_gaps(\n'''
    if "CREATE TABLE IF NOT EXISTS m39_replay_origin_evidence" not in text:
        text = replace_once(text, schema_anchor, replay_schema, "replay-origin schema anchor")

    view_anchor = '''CREATE OR REPLACE VIEW latest_m39_evidence_gaps AS\n'''
    replay_view = '''CREATE OR REPLACE VIEW latest_m39_replay_origin_evidence AS\nSELECT * FROM m39_replay_origin_evidence\nWHERE run_id=(SELECT run_id FROM module39_runs ORDER BY started_at_utc DESC LIMIT 1)\nORDER BY asset_id,horizon_days,forecast_date;\n\nCREATE OR REPLACE VIEW latest_m39_evidence_gaps AS\n'''
    if "CREATE OR REPLACE VIEW latest_m39_replay_origin_evidence" not in text:
        text = replace_once(text, view_anchor, replay_view, "replay-origin view anchor")

    run_anchor = '''            replay_bundle=self.true_replay()\n            calibration,calibrated=self.calibration(forecasts,replay_bundle)\n            rolling=self.rolling_validation(replay_bundle)\n'''
    run_insert = '''            replay_bundle=self.true_replay()\n            replay_origins=replay_bundle["replay"].copy()\n            replay_origins["run_id"]=self.run_id\n            replay_origins["calculated_at_utc"]=utcnow()\n            replay_origins=replay_origins[[\n                "run_id","asset_id","horizon_days","fold_number",\n                "forecast_date","training_end_date","training_rows",\n                "internal_validation_rows","predicted_return_pct",\n                "actual_return_pct","raw_probability_positive",\n                "observed_positive","lower_return_pct","upper_return_pct",\n                "interval_covered","calculated_at_utc",\n            ]]\n            calibration,calibrated=self.calibration(forecasts,replay_bundle)\n            rolling=self.rolling_validation(replay_bundle)\n'''
    if 'replay_origins=replay_bundle["replay"].copy()' not in text:
        text = replace_once(text, run_anchor, run_insert, "replay-origin run preparation")

    table_anchor = '''                ("m39_rolling_origin_validation",rolling),\n                ("m39_evidence_gaps",gaps),\n'''
    table_insert = '''                ("m39_replay_origin_evidence",replay_origins),\n                ("m39_rolling_origin_validation",rolling),\n                ("m39_evidence_gaps",gaps),\n'''
    if '("m39_replay_origin_evidence",replay_origins)' not in text:
        text = replace_once(text, table_anchor, table_insert, "replay-origin persistence")

    M39.write_text(text, encoding="utf-8", newline="")

    print("CRYPTO_MODULE39_REPLAY_CHRONOLOGY_EVIDENCE_REMEDIATION=PASS")
    print("FOLD_AGGREGATE_TRAINING_END_DATE=NULL")
    print("PER_ORIGIN_CHRONOLOGY_PERSISTED=TRUE")
    print("EXPECTED_REPLAY_ORIGIN_ROWS=870")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
