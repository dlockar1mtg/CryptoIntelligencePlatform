"""Keep a daily, self-scoring log of the Crypto forecasts and the 7-day V4 context forecast.

Each production run:

1. adds the latest legacy forecasts to the log: the M39 calibrated return forecasts and the
   M42 price projections (the forecasts exported to the UIP);
2. adds a 7-day forecast from the frozen V4 winner (V4_7D_VOLATILITY_STATE_EXTRA_TREES) for
   Bitcoin and Ethereum, using the contract-preserving operational refit authorized by
   docs/bitcoin_live_input_refresh_and_v4_operationalization_governance_v1.md (same family,
   features, split policy, exclusions and random state; no tuning; only data known on the
   forecast date);
3. scores every logged forecast whose target date now has an exact canonical close
   (no nearest-date substitution);
4. writes a summary with the scorecard and the latest 7-day context forecast.

The log is append-only: a forecast already logged is never rewritten except to fill in its
outcome. The database is opened read-only. The workflow commits the extended log to
data/forecast_tracking/ so its history outlives the cached database and the 30-day artifacts.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUTPUT_DIR = ROOT / "data" / "operations" / "crypto" / "forecast_tracking"  # run evidence (uploaded as an artifact)
COMMITTED_LOG = ROOT / "data" / "forecast_tracking" / "forecast_log.csv"  # durable history, committed after each run
LOG_NAME = "forecast_log.csv"
SUMMARY_NAME = "forecast_tracking_summary.json"

V4_WINNER = "V4_7D_VOLATILITY_STATE_EXTRA_TREES"
V4_HORIZON = 7
V4_ASSETS = ("bitcoin", "ethereum")
CORE_ASSETS = ("bitcoin", "ethereum", "solana", "chainlink", "xrp", "avalanche")
V4_MANIFESTS = {
    "v2": ROOT / "docs" / "predictive_model_improvement_v2_holdout_manifest.json",
    "v3": ROOT / "docs" / "predictive_model_tournament_v3_final_holdout_manifest.json",
    "v4": ROOT / "docs" / "predictive_horizon_recovery_v4_final_holdout_manifest.json",
}
V4_HOLDOUT_EVIDENCE = {
    "final_holdout_rows": 60,
    "directional_accuracy": 0.50,
    "majority_baseline_accuracy": 0.3667,
    "bitcoin_ethereum_correct": "17 of 20",
    "source": "docs/predictive_horizon_recovery_v4_7d_final_holdout_closeout.md",
}
V4_LABEL = (
    "Context only. The 7-day direction model passed one final holdout (60 forecasts, 50% right "
    "against a 37% baseline). That sample is small, the 30- and 365-day versions did not qualify, "
    "and no buy or sell rule has been shown to work with it."
)

MODEL_M39 = "M39_CALIBRATED"
MODEL_M42 = "M42_PROJECTION"
MODEL_V4 = "V4_7D_EXTRA_TREES"

LOG_FIELDS = [
    "model", "asset_id", "origin_date", "horizon_days", "target_date", "logged_on",
    "source_run_id", "status", "origin_price", "predicted_return_pct", "lower_return_pct",
    "upper_return_pct", "probability_positive", "outcome_price", "realized_return_pct",
    "direction_hit", "inside_band", "scored_on",
]


def _date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _num(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value)


def _key(row: dict) -> tuple:
    return (row["model"], row["asset_id"], row["origin_date"], str(row["horizon_days"]))


def read_log(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_log(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda r: (r["origin_date"], r["model"], r["asset_id"], int(r["horizon_days"])))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LOG_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in ordered:
            writer.writerow({field: _fmt(row.get(field)) for field in LOG_FIELDS})


def _tables(conn) -> set[str]:
    return {str(row[0]) for row in conn.execute("SHOW TABLES").fetchall()}


def load_closes(conn) -> dict[str, dict[date, float]]:
    """Exact daily canonical closes per asset."""

    closes: dict[str, dict[date, float]] = {}
    if "canonical_market_daily" not in _tables(conn):
        return closes
    for asset_id, observed, price in conn.execute(
        "SELECT asset_id, observation_date, price_usd FROM canonical_market_daily "
        "WHERE price_usd IS NOT NULL AND price_usd > 0"
    ).fetchall():
        day = _date(observed)
        if day is not None:
            closes.setdefault(str(asset_id), {})[day] = float(price)
    return closes


def _latest_run(conn, table: str) -> str | None:
    row = conn.execute(f"SELECT run_id FROM {table} ORDER BY calculated_at_utc DESC NULLS LAST LIMIT 1").fetchone()
    return None if row is None else str(row[0])


def _forecast_price(conn, tables: set[str], asset_id: str, origin: date, closes) -> float | None:
    """The price a forecast was made from: the exporter's latest market price on or before its date."""

    if "asset_market_daily" in tables:
        row = conn.execute(
            "SELECT price_usd FROM asset_market_daily WHERE asset_id = ? AND observation_date <= ? "
            "AND price_usd IS NOT NULL ORDER BY observation_date DESC, collected_at_utc DESC LIMIT 1",
            [asset_id, origin],
        ).fetchone()
        if row is not None and _num(row[0]):
            return float(row[0])
    return closes.get(asset_id, {}).get(origin)


def legacy_forecasts(conn, closes: dict[str, dict[date, float]]) -> list[dict]:
    """The latest M39 calibrated forecasts and M42 price projections, as log rows."""

    tables = _tables(conn)
    rows: list[dict] = []
    if "m39_calibrated_forecasts" in tables:
        run_id = _latest_run(conn, "m39_calibrated_forecasts")
        for (asset_id, origin, horizon, predicted, probability, lower, upper, status) in conn.execute(
            "SELECT asset_id, forecast_date, horizon_days, predicted_return_pct, calibrated_probability_positive, "
            "conformal_lower_return_pct, conformal_upper_return_pct, forecast_status "
            "FROM m39_calibrated_forecasts WHERE run_id = ?",
            [run_id],
        ).fetchall():
            origin_day, horizon_days = _date(origin), int(horizon)
            if origin_day is None or horizon_days <= 0:
                continue
            rows.append({
                "model": MODEL_M39, "asset_id": str(asset_id), "origin_date": origin_day.isoformat(),
                "horizon_days": horizon_days, "target_date": (origin_day + timedelta(days=horizon_days)).isoformat(),
                "source_run_id": run_id, "status": status or "",
                "origin_price": _forecast_price(conn, tables, str(asset_id), origin_day, closes),
                "predicted_return_pct": _num(predicted), "lower_return_pct": _num(lower),
                "upper_return_pct": _num(upper), "probability_positive": _num(probability),
            })
    if "m42_price_projections" in tables:
        run_id = _latest_run(conn, "m42_price_projections")
        for (asset_id, origin, horizon, target, current, median, bear, bull, status) in conn.execute(
            "SELECT asset_id, recommendation_date, horizon_days, projection_date, current_price, "
            "median_return_pct, bear_return_pct, bull_return_pct, evidence_status "
            "FROM m42_price_projections WHERE run_id = ?",
            [run_id],
        ).fetchall():
            origin_day, target_day = _date(origin), _date(target)
            if origin_day is None or target_day is None or target_day <= origin_day:
                continue
            horizon_days = int(horizon) if horizon is not None else (target_day - origin_day).days
            rows.append({
                "model": MODEL_M42, "asset_id": str(asset_id), "origin_date": origin_day.isoformat(),
                "horizon_days": horizon_days, "target_date": target_day.isoformat(),
                "source_run_id": run_id, "status": status or "",
                "origin_price": _num(current) or closes.get(str(asset_id), {}).get(origin_day),
                "predicted_return_pct": _num(median), "lower_return_pct": _num(bear),
                "upper_return_pct": _num(bull), "probability_positive": None,
            })
    return rows


def v4_forecast(database: Path, asset: str) -> dict:
    """One prospective frozen-contract V4 7-day forecast for an asset (mirrors the governed runner)."""

    import numpy as np
    import pandas as pd
    import yaml

    from crypto_platform.module38 import Module38Runner
    from scripts.audit_predictive_horizon_recovery_v4_fresh_evidence_capacity import selected_v3_origins_for_group
    from scripts.preflight_predictive_horizon_recovery_v4_development import v4_split_origin
    from scripts.run_predictive_horizon_recovery_v4_development import fit_predict
    from scripts.run_v3_per_horizon_development_tournament import build_relative_market as build_v3_relative_market
    from scripts.v4_horizon_recovery_model_spec import (
        EVIDENCE_CLASS,
        NATIVE_LAG_DAYS,
        attach_lagged_native,
        attach_relative,
        build_price_features,
        build_relative_market,
        candidate_features,
    )

    assets = ",".join(f"'{name}'" for name in CORE_ASSETS)
    with duckdb.connect(str(database), read_only=True) as conn:
        prices = conn.execute(
            "SELECT asset_id, observation_date, price_usd, market_cap_usd, volume_24h_usd FROM canonical_market_daily "
            f"WHERE asset_id IN ({assets}) AND price_usd IS NOT NULL ORDER BY observation_date, asset_id"
        ).fetchdf()
        context = pd.DataFrame(columns=["observation_date"] + list(NATIVE_LAG_DAYS))
        if "crypto_features_daily" in _tables(conn):
            context = conn.execute(
                "SELECT observation_date," + ",".join(NATIVE_LAG_DAYS) + " FROM crypto_features_daily ORDER BY observation_date"
            ).fetchdf()
    if prices.empty:
        raise RuntimeError("Canonical core price history is empty")
    prices["observation_date"] = pd.to_datetime(prices["observation_date"])
    if not context.empty:
        context["observation_date"] = pd.to_datetime(context["observation_date"])

    settings = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    runner = object.__new__(Module38Runner)
    runner.cfg = settings["module38"]
    random_state = int(runner.cfg["random_state"])

    manifests = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in V4_MANIFESTS.items()}
    v2_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v2_holdout_origin_dates"]) for g in manifests["v2"]["groups"]}
    v3_final_dates = {(g["asset_id"], int(g["horizon_days"])): set(g["v3_final_holdout_origin_dates"]) for g in manifests["v3"]["groups"]}
    v4_groups = {(g["asset_id"], int(g["horizon_days"])): g for g in manifests["v4"]["groups"]}
    if (asset, V4_HORIZON) not in v4_groups:
        raise RuntimeError(f"No V4 7d group for {asset}")
    holdout_dates = set(v4_groups[(asset, V4_HORIZON)]["v4_final_holdout_origin_dates"])

    relative_v4 = build_relative_market(prices)
    relative_v4["observation_date"] = pd.to_datetime(relative_v4["observation_date"])
    relative_v3 = build_v3_relative_market(prices)
    relative_v3["observation_date"] = pd.to_datetime(relative_v3["observation_date"])

    asset_prices = prices[prices["asset_id"] == asset].copy()
    v3_features = runner.build_features(asset_prices, V4_HORIZON).reset_index(drop=True)
    v3_mask = pd.to_datetime(v3_features["observation_date"]).dt.date.astype(str).isin(v3_final_dates[(asset, V4_HORIZON)])
    v3_features.loc[v3_mask, "target_return"] = np.nan
    selected_v3 = selected_v3_origins_for_group(
        v3_features, V4_HORIZON, runner, context, relative_v3, asset,
        v2_dates[(asset, V4_HORIZON)], v3_final_dates[(asset, V4_HORIZON)],
    )
    selected_v3_dates = {pd.Timestamp(v3_features.iloc[i]["observation_date"]).date().isoformat() for i in selected_v3}
    excluded = set(v2_dates[(asset, V4_HORIZON)]) | set(v3_final_dates[(asset, V4_HORIZON)]) | selected_v3_dates | holdout_dates

    features = build_price_features(asset_prices, V4_HORIZON).reset_index(drop=True)
    holdout_mask = pd.to_datetime(features["observation_date"]).dt.date.astype(str).isin(holdout_dates)
    features.loc[holdout_mask, ["target_return", "target_positive", "target_exceeds_15pct"]] = np.nan
    latest = pd.Timestamp(features["observation_date"].max())
    current_rows = features.index[pd.to_datetime(features["observation_date"]) == latest].tolist()
    if len(current_rows) != 1:
        raise RuntimeError(f"Could not resolve one current {asset} feature row")
    if latest.date().isoformat() in excluded:
        raise RuntimeError("Forecast date collides with a governed excluded origin")

    origin_date, train, validation, current = v4_split_origin(features, int(current_rows[0]), V4_HORIZON, runner, excluded)
    columns = candidate_features(V4_HORIZON, V4_WINNER)
    train_f = attach_relative(attach_lagged_native(train, context, columns), relative_v4, asset, columns)
    validation_f = attach_relative(attach_lagged_native(validation, context, columns), relative_v4, asset, columns)
    current_f = attach_relative(attach_lagged_native(current, context, columns), relative_v4, asset, columns)
    if len(current_f.dropna(subset=columns)) != 1:
        raise RuntimeError("Required current V4 features are missing; the forecast stays unavailable")
    probability, predicted_return = fit_predict(V4_HORIZON, V4_WINNER, train_f, validation_f, current_f, columns, random_state)
    if predicted_return is not None:
        raise RuntimeError("Frozen V4 7d classifier returned a regression prediction")
    complete_train = train_f.dropna(subset=columns + ["target_return"])
    complete_validation = validation_f.dropna(subset=columns + ["target_return"])
    origin = origin_date.date()
    return {
        "asset_id": asset,
        "winner": V4_WINNER,
        "horizon_days": V4_HORIZON,
        "origin_date": origin.isoformat(),
        "target_date": (origin + timedelta(days=V4_HORIZON)).isoformat(),
        "origin_price": float(asset_prices.loc[pd.to_datetime(asset_prices["observation_date"]) == latest, "price_usd"].iloc[0]),
        "probability_up": float(probability),
        "direction": "UP" if float(probability) >= 0.5 else "DOWN_OR_FLAT",
        "complete_training_rows": int(len(complete_train)),
        "complete_validation_rows": int(len(complete_validation)),
        "random_state": random_state,
        "evidence_class": EVIDENCE_CLASS,
        "contract_preserving_operational_refit": True,
        "model_selection_reopened": False,
        "post_holdout_tuning_performed": False,
    }


def v4_log_row(forecast: dict) -> dict:
    return {
        "model": MODEL_V4, "asset_id": forecast["asset_id"], "origin_date": forecast["origin_date"],
        "horizon_days": V4_HORIZON, "target_date": forecast["target_date"], "source_run_id": V4_WINNER,
        "status": "CONTEXT_ONLY", "origin_price": forecast["origin_price"],
        "predicted_return_pct": None, "lower_return_pct": None, "upper_return_pct": None,
        "probability_positive": forecast["probability_up"],
    }


def score(rows: list[dict], closes: dict[str, dict[date, float]], today: date) -> int:
    """Fill in outcomes for forecasts whose target date has an exact canonical close."""

    scored = 0
    for row in rows:
        if row.get("outcome_price"):
            continue
        target = _date(row.get("target_date"))
        origin_price = _num(row.get("origin_price"))
        if target is None or origin_price is None or origin_price <= 0:
            continue
        outcome = closes.get(row["asset_id"], {}).get(target)
        if outcome is None:
            continue
        realized = (outcome / origin_price - 1.0) * 100.0
        probability = _num(row.get("probability_positive"))
        predicted = _num(row.get("predicted_return_pct"))
        if row["model"] == MODEL_V4 and probability is not None:
            predicted_up = probability >= 0.5
        elif predicted is not None:
            predicted_up = predicted > 0
        else:
            predicted_up = None
        lower, upper = _num(row.get("lower_return_pct")), _num(row.get("upper_return_pct"))
        row["outcome_price"] = outcome
        row["realized_return_pct"] = realized
        row["direction_hit"] = "" if predicted_up is None else str(predicted_up == (realized > 0))
        row["inside_band"] = "" if lower is None or upper is None else str(lower <= realized <= upper)
        row["scored_on"] = today.isoformat()
        scored += 1
    return scored


def scorecard(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        groups.setdefault((row["model"], row["asset_id"], int(row["horizon_days"])), []).append(row)
    cards = []
    for (model, asset, horizon), items in sorted(groups.items()):
        done = [r for r in items if r.get("outcome_price") not in (None, "")]
        hits = [r["direction_hit"] == "True" for r in done if r.get("direction_hit") in ("True", "False")]
        bands = [r["inside_band"] == "True" for r in done if r.get("inside_band") in ("True", "False")]
        realized = [_num(r.get("realized_return_pct")) for r in done]
        realized = [x for x in realized if x is not None]
        brier = [
            (_num(r.get("probability_positive")) - (1.0 if (_num(r.get("realized_return_pct")) or 0) > 0 else 0.0)) ** 2
            for r in done if _num(r.get("probability_positive")) is not None and _num(r.get("realized_return_pct")) is not None
        ]
        cards.append({
            "model": model, "asset_id": asset, "horizon_days": horizon,
            "forecasts_logged": len(items), "forecasts_scored": len(done),
            "direction_hit_rate": (sum(hits) / len(hits)) if hits else None,
            "band_coverage": (sum(bands) / len(bands)) if bands else None,
            "mean_realized_return_pct": (sum(realized) / len(realized)) if realized else None,
            "brier_score": (sum(brier) / len(brier)) if brier else None,
            "first_origin_date": min(r["origin_date"] for r in items),
            "next_target_date": min((r["target_date"] for r in items if not r.get("outcome_price")), default=None),
        })
    return cards


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "crypto_intelligence.duckdb")
    parser.add_argument("--log", type=Path, default=COMMITTED_LOG, help="committed log to extend")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--skip-v4", action="store_true")
    args = parser.parse_args(argv)

    errors: list[str] = []
    today = datetime.now(timezone.utc).date()
    rows = read_log(args.log)
    have = {_key(row) for row in rows}

    with duckdb.connect(str(args.database), read_only=True) as conn:
        closes = load_closes(conn)
        try:
            new_rows = legacy_forecasts(conn, closes)
        except Exception as exc:  # the legacy log must never block the run
            new_rows = []
            errors.append(f"legacy forecasts: {type(exc).__name__}: {exc}")

    v4: dict[str, dict] = {}
    if not args.skip_v4:
        for asset in V4_ASSETS:
            try:
                v4[asset] = v4_forecast(args.database, asset)
                new_rows.append(v4_log_row(v4[asset]))
            except Exception as exc:
                errors.append(f"V4 7d {asset}: {type(exc).__name__}: {exc}")

    added = 0
    for row in new_rows:
        row["horizon_days"] = str(row["horizon_days"])
        if _key(row) in have:
            continue
        row["logged_on"] = today.isoformat()
        rows.append(row)
        have.add(_key(row))
        added += 1

    scored = score(rows, closes, today)
    latest_price_date = max((max(days) for days in closes.values() if days), default=None)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_log(args.output_dir / LOG_NAME, rows)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "latest_price_date": None if latest_price_date is None else latest_price_date.isoformat(),
        "log_rows": len(rows),
        "rows_added": added,
        "rows_scored_this_run": scored,
        "v4_7d": {
            "label": V4_LABEL,
            "status": "CONTEXT_ONLY",
            "holdout_evidence": V4_HOLDOUT_EVIDENCE,
            "forecasts": v4,
        },
        "scorecard": scorecard(rows),
        "errors": errors,
    }
    (args.output_dir / SUMMARY_NAME).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("latest_price_date", "log_rows", "rows_added", "rows_scored_this_run", "errors")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
