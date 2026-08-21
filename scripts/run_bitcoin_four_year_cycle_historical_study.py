from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, median

import duckdb

STUDY_ID = "BITCOIN_FOUR_YEAR_CYCLE_HISTORICAL_STUDY_V1"
EVIDENCE_CLASS = "HISTORICAL_CANONICAL_PRICE_STUDY_NOT_STRICT_VINTAGE_POINT_IN_TIME"
HALVINGS = [
    date(2012, 11, 28),
    date(2016, 7, 9),
    date(2020, 5, 11),
    date(2024, 4, 20),
]
HORIZONS = (365, 730, 1095)
PHASES = (
    "HALVING_YEAR",
    "POST_HALVING_YEAR_1",
    "POST_HALVING_YEAR_2",
    "PRE_HALVING_YEAR",
    "OTHER_OR_INCOMPLETE",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def finite_or_none(value):
    if value is None:
        return None
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return value


def percentile(values: list[float], q: float):
    clean = sorted(float(v) for v in values if v is not None)
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    pos = (len(clean) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(clean) - 1)
    frac = pos - lo
    return clean[lo] * (1 - frac) + clean[hi] * frac


def numeric_summary(values: list[float]) -> dict:
    clean = [float(v) for v in values if v is not None]
    return {
        "observed_rows": len(clean),
        "mean": finite_or_none(mean(clean)) if clean else None,
        "median": finite_or_none(median(clean)) if clean else None,
        "positive_rate": finite_or_none(sum(v > 0 for v in clean) / len(clean)) if clean else None,
        "p25": finite_or_none(percentile(clean, 0.25)) if clean else None,
        "p75": finite_or_none(percentile(clean, 0.75)) if clean else None,
        "worst": finite_or_none(min(clean)) if clean else None,
        "best": finite_or_none(max(clean)) if clean else None,
    }


def phase_for_year(year: int) -> str:
    if year in {2012, 2016, 2020, 2024}:
        return "HALVING_YEAR"
    if year in {2013, 2017, 2021, 2025}:
        return "POST_HALVING_YEAR_1"
    if year in {2014, 2018, 2022, 2026}:
        return "POST_HALVING_YEAR_2"
    if year in {2015, 2019, 2023, 2027}:
        return "PRE_HALVING_YEAR"
    return "OTHER_OR_INCOMPLETE"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--mandate-contract", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    database = Path(args.database).resolve()
    design = Path(args.design).resolve()
    mandate = Path(args.mandate_contract).resolve()
    output = Path(args.output).resolve()

    for name, path in {
        "database": database,
        "design": design,
        "mandate_contract": mandate,
    }.items():
        require(path.is_file(), f"Required governed input missing: {name}={path}")
    require(not output.exists(), "Bitcoin cycle study output already exists; refusing overwrite")

    hashes_before = {
        "database": sha256(database),
        "design": sha256(design),
        "mandate_contract": sha256(mandate),
    }

    design_text = design.read_text(encoding="utf-8")
    mandate_text = mandate.read_text(encoding="utf-8")
    for required_text in (
        STUDY_ID,
        "exact 365-calendar-day forward return",
        "exact 730-calendar-day forward return",
        "exact 1095-calendar-day forward return",
        "monthly anchor",
        "read-only",
        "No nearest-date endpoint",
    ):
        require(required_text.lower() in design_text.lower(), f"Study design missing required boundary: {required_text}")
    for required_text in (
        "LONG_DURATION_ACCUMULATION",
        "APPROXIMATE_NEW_BTC_HOLDING_THESIS_YEARS=3",
        "SHORT_TERM_NEGATIVE_FORECAST_AUTOMATIC_SELL_ALLOWED=FALSE",
    ):
        require(required_text in mandate_text, f"Mandate contract missing required boundary: {required_text}")

    conn = duckdb.connect(str(database), read_only=True)
    try:
        table_exists = conn.execute(
            "SELECT count(*) FROM information_schema.tables WHERE lower(table_name)='canonical_market_daily'"
        ).fetchone()[0]
        require(int(table_exists) >= 1, "canonical_market_daily is unavailable")
        raw_rows = conn.execute(
            """
            SELECT observation_date, price_usd
            FROM canonical_market_daily
            WHERE asset_id='bitcoin' AND price_usd IS NOT NULL
            ORDER BY observation_date
            """
        ).fetchall()
    finally:
        conn.close()

    require(raw_rows, "No canonical Bitcoin price history is available")

    prices: dict[date, float] = {}
    for observation_date, price_usd in raw_rows:
        obs = observation_date if isinstance(observation_date, date) else datetime.fromisoformat(str(observation_date)[:10]).date()
        require(obs not in prices, f"Duplicate canonical Bitcoin price row: {obs.isoformat()}")
        price = float(price_usd)
        require(price > 0, f"Non-positive canonical Bitcoin price: {obs.isoformat()}")
        prices[obs] = price

    dates = sorted(prices)
    first_date = dates[0]
    last_date = dates[-1]

    running_peak = None
    drawdown_from_high: dict[date, float] = {}
    for obs in dates:
        price = prices[obs]
        running_peak = price if running_peak is None else max(running_peak, price)
        drawdown_from_high[obs] = 100.0 * (price / running_peak - 1.0)

    yearly = []
    by_year: dict[int, list[date]] = defaultdict(list)
    for obs in dates:
        by_year[obs.year].append(obs)

    for year in sorted(by_year):
        year_dates = by_year[year]
        first_obs = year_dates[0]
        last_obs = year_dates[-1]
        min_obs = min(year_dates, key=lambda d: prices[d])
        max_obs = max(year_dates, key=lambda d: prices[d])
        first_price = prices[first_obs]
        last_price = prices[last_obs]
        min_price = prices[min_obs]
        max_price = prices[max_obs]
        year_return = 100.0 * (last_price / first_price - 1.0)
        drawdown = min(drawdown_from_high[d] for d in year_dates)
        first_to_min = 100.0 * (min_price / first_price - 1.0)
        min_to_last = 100.0 * (last_price / min_price - 1.0)
        yearly.append({
            "calendar_year": year,
            "phase": phase_for_year(year),
            "observation_rows": len(year_dates),
            "first_observation_date": first_obs.isoformat(),
            "last_observation_date": last_obs.isoformat(),
            "first_price_usd": first_price,
            "last_price_usd": last_price,
            "calendar_year_return_pct": year_return,
            "minimum_price_usd": min_price,
            "minimum_price_date": min_obs.isoformat(),
            "maximum_price_usd": max_price,
            "maximum_price_date": max_obs.isoformat(),
            "maximum_drawdown_from_running_high_pct": drawdown,
            "first_to_minimum_return_pct": first_to_min,
            "minimum_to_last_return_pct": min_to_last,
        })

    completed_phase_years = [
        row for row in yearly
        if row["phase"] != "OTHER_OR_INCOMPLETE" and row["calendar_year"] < last_date.year
    ]
    phase_summary = {}
    for phase in PHASES[:-1]:
        scoped = [row for row in completed_phase_years if row["phase"] == phase]
        returns = [row["calendar_year_return_pct"] for row in scoped]
        drawdowns = [row["maximum_drawdown_from_running_high_pct"] for row in scoped]
        phase_summary[phase] = {
            "represented_years": [row["calendar_year"] for row in scoped],
            "independent_phase_years": len(scoped),
            "mean_calendar_year_return_pct": finite_or_none(mean(returns)) if returns else None,
            "median_calendar_year_return_pct": finite_or_none(median(returns)) if returns else None,
            "positive_year_rate": finite_or_none(sum(v > 0 for v in returns) / len(returns)) if returns else None,
            "minimum_calendar_year_return_pct": finite_or_none(min(returns)) if returns else None,
            "maximum_calendar_year_return_pct": finite_or_none(max(returns)) if returns else None,
            "mean_maximum_drawdown_pct": finite_or_none(mean(drawdowns)) if drawdowns else None,
            "median_maximum_drawdown_pct": finite_or_none(median(drawdowns)) if drawdowns else None,
        }

    interval_diagnostics = []
    adequate_completed_intervals = []
    for idx in range(len(HALVINGS) - 1):
        start = HALVINGS[idx]
        end = HALVINGS[idx + 1]
        interval_dates = [d for d in dates if start <= d < end]
        expected_days = (end - start).days
        coverage_ratio = len(interval_dates) / expected_days if expected_days > 0 else 0.0
        endpoint_near_start = bool(interval_dates and (interval_dates[0] - start).days <= 7)
        endpoint_near_end = bool(interval_dates and (end - interval_dates[-1]).days <= 7)
        adequate = coverage_ratio >= 0.90 and endpoint_near_start and endpoint_near_end
        row = {
            "halving_start": start.isoformat(),
            "next_halving": end.isoformat(),
            "expected_calendar_days": expected_days,
            "canonical_observation_rows": len(interval_dates),
            "coverage_ratio": coverage_ratio,
            "adequate_completed_interval": adequate,
        }
        if interval_dates:
            peak_date = max(interval_dates, key=lambda d: prices[d])
            post_peak_dates = [d for d in interval_dates if d >= peak_date]
            trough_date = min(post_peak_dates, key=lambda d: prices[d])
            peak_price = prices[peak_date]
            trough_price = prices[trough_date]
            row.update({
                "interval_peak_date": peak_date.isoformat(),
                "interval_peak_price_usd": peak_price,
                "interval_peak_phase": phase_for_year(peak_date.year),
                "post_peak_minimum_date": trough_date.isoformat(),
                "post_peak_minimum_price_usd": trough_price,
                "post_peak_minimum_phase": phase_for_year(trough_date.year),
                "peak_to_subsequent_minimum_drawdown_pct": 100.0 * (trough_price / peak_price - 1.0),
            })
        interval_diagnostics.append(row)
        if adequate:
            adequate_completed_intervals.append(row)

    def forward_rows(anchor_dates: list[date]) -> list[dict]:
        rows = []
        for origin in anchor_dates:
            origin_price = prices[origin]
            row = {
                "origin_date": origin.isoformat(),
                "origin_year": origin.year,
                "origin_phase": phase_for_year(origin.year),
                "origin_price_usd": origin_price,
                "drawdown_from_running_high_pct": drawdown_from_high[origin],
            }
            for horizon in HORIZONS:
                endpoint = origin + timedelta(days=horizon)
                endpoint_price = prices.get(endpoint)
                row[f"forward_{horizon}d_exact_endpoint_date"] = endpoint.isoformat()
                row[f"forward_{horizon}d_return_pct"] = (
                    100.0 * (endpoint_price / origin_price - 1.0)
                    if endpoint_price is not None else None
                )
            rows.append(row)
        return rows

    daily_forward = forward_rows(dates)

    monthly_anchor_dates = []
    seen_months = set()
    for obs in dates:
        key = (obs.year, obs.month)
        if key not in seen_months:
            seen_months.add(key)
            monthly_anchor_dates.append(obs)
    monthly_forward = forward_rows(monthly_anchor_dates)

    def forward_summary(rows: list[dict]) -> dict:
        output_summary = {}
        for phase in PHASES:
            scoped = [row for row in rows if row["origin_phase"] == phase]
            horizon_summary = {}
            for horizon in HORIZONS:
                key = f"forward_{horizon}d_return_pct"
                values = [row[key] for row in scoped if row[key] is not None]
                summary = numeric_summary(values)
                summary.update({
                    "eligible_origin_rows": len(scoped),
                    "exact_endpoint_observed_rows": len(values),
                    "missing_exact_endpoint_rows": len(scoped) - len(values),
                })
                horizon_summary[str(horizon)] = summary
            drawdowns = [row["drawdown_from_running_high_pct"] for row in scoped]
            output_summary[phase] = {
                "origin_rows": len(scoped),
                "drawdown_from_running_high_pct": numeric_summary(drawdowns),
                "forward_returns": horizon_summary,
            }
        return output_summary

    daily_summary = forward_summary(daily_forward)
    monthly_summary = forward_summary(monthly_forward)

    three_year = {}
    for phase in PHASES:
        summary = monthly_summary[phase]["forward_returns"]["1095"]
        three_year[phase] = {
            "monthly_anchor_rows": monthly_summary[phase]["origin_rows"],
            "exact_endpoint_observed_rows": summary["exact_endpoint_observed_rows"],
            "missing_exact_endpoint_rows": summary["missing_exact_endpoint_rows"],
            "mean_3y_return_pct": summary["mean"],
            "median_3y_return_pct": summary["median"],
            "positive_3y_return_rate": summary["positive_rate"],
            "worst_3y_return_pct": summary["worst"],
            "best_3y_return_pct": summary["best"],
        }

    sequence_matches = 0
    for row in adequate_completed_intervals:
        if (
            row.get("interval_peak_phase") == "POST_HALVING_YEAR_1"
            and row.get("post_peak_minimum_phase") == "POST_HALVING_YEAR_2"
        ):
            sequence_matches += 1

    accumulation_phases = ("POST_HALVING_YEAR_2", "PRE_HALVING_YEAR")
    accumulation_3y = [three_year[p]["median_3y_return_pct"] for p in accumulation_phases]
    accumulation_3y_observed = [v for v in accumulation_3y if v is not None]
    three_year_not_contradictory = bool(
        accumulation_3y_observed
        and all(v > 0 for v in accumulation_3y_observed)
    )

    if len(adequate_completed_intervals) < 2:
        interpretation = "INSUFFICIENT_CANONICAL_HISTORY"
    else:
        majority_sequence = sequence_matches > len(adequate_completed_intervals) / 2
        if majority_sequence and three_year_not_contradictory:
            interpretation = "PATTERN_SUPPORTED_DESCRIPTIVELY"
        elif majority_sequence or three_year_not_contradictory:
            interpretation = "PATTERN_PARTIALLY_SUPPORTED"
        else:
            interpretation = "PATTERN_NOT_SUPPORTED"

    result = {
        "study_id": STUDY_ID,
        "study_scope": "BITCOIN_ONLY_FOUR_YEAR_CYCLE_HISTORICAL_STUDY",
        "evidence_class": EVIDENCE_CLASS,
        "strict_vintage_point_in_time_claim_allowed": False,
        "canonical_source_table": "canonical_market_daily",
        "database_open_mode": "READ_ONLY",
        "halving_anchors": [d.isoformat() for d in HALVINGS],
        "canonical_coverage": {
            "first_observation_date": first_date.isoformat(),
            "last_observation_date": last_date.isoformat(),
            "unique_daily_observations": len(dates),
            "duplicate_rows_detected": False,
            "nonpositive_prices_detected": False,
            "represented_calendar_years": sorted(by_year),
        },
        "calendar_year_phase_statistics": yearly,
        "cross_cycle_phase_summary": phase_summary,
        "peak_reset_interval_diagnostics": interval_diagnostics,
        "adequate_completed_intervals": len(adequate_completed_intervals),
        "peak_reset_sequence_matches": sequence_matches,
        "daily_exact_endpoint_summary_by_phase": daily_summary,
        "monthly_anchor_exact_endpoint_summary_by_phase": monthly_summary,
        "three_year_accumulation_diagnostics": three_year,
        "interpretation_controls": {
            "majority_peak_in_post_halving_year_1_and_reset_in_post_halving_year_2": (
                sequence_matches > len(adequate_completed_intervals) / 2
                if adequate_completed_intervals else False
            ),
            "accumulation_phase_3y_medians_positive_where_observed": three_year_not_contradictory,
            "independent_cycle_sample_size_warning": True,
            "daily_forward_rows_are_overlapping": True,
            "monthly_forward_rows_can_still_overlap": True,
        },
        "study_interpretation": interpretation,
        "cycle_policy_authority_granted": False,
        "historical_recommendation_policy_skill_status": "INSUFFICIENT_EVIDENCE_FOR_POLICY_SKILL",
        "v4_model_selection_affected": False,
        "recommendation_thresholds_changed": False,
        "production_policy_changed": False,
        "autonomous_execution_allowed": False,
        "source_database_modified": False,
        "governed_source_hashes_before": hashes_before,
        "next_gate": "PRESERVE_AND_REVIEW_BITCOIN_FOUR_YEAR_CYCLE_HISTORICAL_STUDY",
    }

    hashes_after = {
        "database": sha256(database),
        "design": sha256(design),
        "mandate_contract": sha256(mandate),
    }
    require(hashes_after == hashes_before, "Governed source evidence or source database changed during Bitcoin cycle study")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("BITCOIN_FOUR_YEAR_CYCLE_HISTORICAL_STUDY=PASS")
    print(f"CANONICAL_FIRST_DATE={first_date.isoformat()}")
    print(f"CANONICAL_LAST_DATE={last_date.isoformat()}")
    print(f"CANONICAL_DAILY_ROWS={len(dates)}")
    print(f"ADEQUATE_COMPLETED_INTERVALS={len(adequate_completed_intervals)}")
    print(f"PEAK_RESET_SEQUENCE_MATCHES={sequence_matches}")
    print(f"STUDY_INTERPRETATION={interpretation}")
    for phase in ("POST_HALVING_YEAR_2", "PRE_HALVING_YEAR"):
        diag = three_year[phase]
        print(f"PHASE={phase}|3Y_MONTHLY_ANCHOR_OBSERVED={diag['exact_endpoint_observed_rows']}|3Y_MEDIAN_RETURN_PCT={diag['median_3y_return_pct']}|3Y_POSITIVE_RATE={diag['positive_3y_return_rate']}")
    print("CYCLE_POLICY_AUTHORITY_GRANTED=FALSE")
    print("V4_MODEL_SELECTION_AFFECTED=FALSE")
    print("PRODUCTION_POLICY_CHANGED=FALSE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=PRESERVE_AND_REVIEW_BITCOIN_FOUR_YEAR_CYCLE_HISTORICAL_STUDY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
