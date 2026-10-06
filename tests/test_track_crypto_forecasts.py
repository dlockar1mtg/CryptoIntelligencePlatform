"""Daily forecast log: legacy forecasts are logged once, scored on exact closes, and V4 failures never block."""
from __future__ import annotations

import csv
import json
from datetime import date, timedelta

import duckdb

import scripts.track_crypto_forecasts as tracker


def _database(path, closes_until: date):
    conn = duckdb.connect(str(path))
    conn.execute("CREATE TABLE canonical_market_daily (asset_id VARCHAR, observation_date DATE, price_usd DOUBLE)")
    conn.execute(
        "CREATE TABLE asset_market_daily (asset_id VARCHAR, observation_date DATE, price_usd DOUBLE, collected_at_utc TIMESTAMP)"
    )
    conn.execute(
        "CREATE TABLE m39_calibrated_forecasts (run_id VARCHAR, forecast_date DATE, asset_id VARCHAR, horizon_days INTEGER, "
        "predicted_return_pct DOUBLE, calibrated_probability_positive DOUBLE, conformal_lower_return_pct DOUBLE, "
        "conformal_upper_return_pct DOUBLE, forecast_confidence DOUBLE, calibration_method VARCHAR, "
        "forecast_status VARCHAR, calculated_at_utc TIMESTAMP)"
    )
    conn.execute(
        "CREATE TABLE m42_price_projections (run_id VARCHAR, recommendation_date DATE, asset_id VARCHAR, horizon_label VARCHAR, "
        "horizon_days INTEGER, horizon_months DOUBLE, projection_date DATE, current_price DOUBLE, bear_price DOUBLE, "
        "median_price DOUBLE, bull_price DOUBLE, bear_return_pct DOUBLE, median_return_pct DOUBLE, bull_return_pct DOUBLE, "
        "annualized_median_return_pct DOUBLE, projection_confidence DOUBLE, projection_method VARCHAR, "
        "evidence_status VARCHAR, calculated_at_utc TIMESTAMP)"
    )
    day, price = date(2026, 9, 1), 100.0
    while day <= closes_until:
        conn.execute("INSERT INTO canonical_market_daily VALUES ('bitcoin', ?, ?)", [day, price])
        conn.execute("INSERT INTO asset_market_daily VALUES ('bitcoin', ?, ?, now())", [day, price])
        day, price = day + timedelta(days=1), price + 1.0
    conn.close()


def _add_run(path, run_id: str, origin: date, calculated: str):
    conn = duckdb.connect(str(path))
    conn.execute(
        "INSERT INTO m39_calibrated_forecasts VALUES (?, ?, 'bitcoin', 7, 2.0, 0.6, -5.0, 9.0, 0.5, 'conformal', 'CALIBRATED', ?)",
        [run_id, origin, calculated],
    )
    conn.execute(
        "INSERT INTO m42_price_projections VALUES (?, ?, 'bitcoin', '1Y', 365, 12, ?, 100, 50, 150, 300, -50, 50, 200, 50, 0.4, 'mc', 'OK', ?)",
        [run_id, origin, origin + timedelta(days=365), calculated],
    )
    conn.close()


def _rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_logs_once_scores_exact_close_and_keeps_history(tmp_path):
    db = tmp_path / "crypto.duckdb"
    out = tmp_path / "tracking"
    _database(db, date(2026, 9, 20))
    _add_run(db, "run-1", date(2026, 9, 5), "2026-09-05 12:00:00")

    assert tracker.main(["--database", str(db), "--log", str(out / "forecast_log.csv"), "--output-dir", str(out), "--skip-v4"]) == 0
    rows = _rows(out / "forecast_log.csv")
    assert {(r["model"], r["horizon_days"]) for r in rows} == {("M39_CALIBRATED", "7"), ("M42_PROJECTION", "365")}
    m39 = next(r for r in rows if r["model"] == "M39_CALIBRATED")
    # origin 2026-09-05 close 104, target 2026-09-12 close 111 -> +6.73%, predicted +2% -> hit, inside -5..9 band
    assert m39["target_date"] == "2026-09-12"
    assert float(m39["outcome_price"]) == 111.0
    assert abs(float(m39["realized_return_pct"]) - (111 / 104 - 1) * 100) < 1e-9
    assert m39["direction_hit"] == "True"
    assert m39["inside_band"] == "True"
    m42 = next(r for r in rows if r["model"] == "M42_PROJECTION")
    assert m42["outcome_price"] == ""

    # a later run: the old forecast is kept unchanged, the new one is appended
    _add_run(db, "run-2", date(2026, 9, 19), "2026-09-19 12:00:00")
    assert tracker.main(["--database", str(db), "--log", str(out / "forecast_log.csv"), "--output-dir", str(out), "--skip-v4"]) == 0
    rows = _rows(out / "forecast_log.csv")
    assert len(rows) == 4
    newest = next(r for r in rows if r["model"] == "M39_CALIBRATED" and r["origin_date"] == "2026-09-19")
    assert newest["outcome_price"] == ""  # target 2026-09-26 has no close yet

    summary = json.loads((out / "forecast_tracking_summary.json").read_text())
    card = next(c for c in summary["scorecard"] if c["model"] == "M39_CALIBRATED")
    assert card["forecasts_logged"] == 2 and card["forecasts_scored"] == 1
    assert card["direction_hit_rate"] == 1.0
    assert card["next_target_date"] == "2026-09-26"
    assert summary["errors"] == []


def test_v4_failure_is_recorded_not_raised(tmp_path, monkeypatch):
    db = tmp_path / "crypto.duckdb"
    out = tmp_path / "tracking"
    _database(db, date(2026, 9, 20))

    def boom(database, asset):
        raise RuntimeError("features missing")

    monkeypatch.setattr(tracker, "v4_forecast", boom)
    assert tracker.main(["--database", str(db), "--log", str(out / "forecast_log.csv"), "--output-dir", str(out)]) == 0
    summary = json.loads((out / "forecast_tracking_summary.json").read_text())
    assert summary["v4_7d"]["forecasts"] == {}
    assert summary["v4_7d"]["status"] == "CONTEXT_ONLY"
    assert len(summary["errors"]) == 2 and "features missing" in summary["errors"][0]


def test_v4_forecast_is_logged_and_scored_by_probability(tmp_path, monkeypatch):
    db = tmp_path / "crypto.duckdb"
    out = tmp_path / "tracking"
    _database(db, date(2026, 9, 20))

    def fake(database, asset):
        return {"asset_id": asset, "origin_date": "2026-09-10", "target_date": "2026-09-17",
                "origin_price": 109.0, "probability_up": 0.3, "direction": "DOWN_OR_FLAT"}

    monkeypatch.setattr(tracker, "v4_forecast", fake)
    tracker.main(["--database", str(db), "--log", str(out / "forecast_log.csv"), "--output-dir", str(out)])
    rows = [r for r in _rows(out / "forecast_log.csv") if r["model"] == "V4_7D_EXTRA_TREES"]
    btc = next(r for r in rows if r["asset_id"] == "bitcoin")
    assert btc["status"] == "CONTEXT_ONLY"
    assert btc["direction_hit"] == "False"  # said down, price rose 109 -> 116
    eth = next(r for r in rows if r["asset_id"] == "ethereum")
    assert eth["outcome_price"] == ""  # no ethereum closes
