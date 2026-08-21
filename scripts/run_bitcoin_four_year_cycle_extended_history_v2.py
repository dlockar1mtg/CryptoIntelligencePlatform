from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, median

STUDY_ID = "BITCOIN_FOUR_YEAR_CYCLE_EXTENDED_HISTORY_V2"
EVIDENCE_CLASS = "EXTERNAL_HISTORICAL_RESEARCH_SNAPSHOT_NOT_STRICT_VINTAGE_POINT_IN_TIME"
EXPECTED_SNAPSHOT_ID = "BITCOIN_EXTENDED_HISTORY_COINMETRICS_PRICEUSD_V2"
EXPECTED_SNAPSHOT_SHA256 = "549bc0172dbefaf9936705df9da58ead29cd583141c5eaf294dd2fed5a693961"
HALVINGS = (
    date(2012, 11, 28),
    date(2016, 7, 9),
    date(2020, 5, 11),
    date(2024, 4, 20),
)
HORIZONS = (365, 730, 1095)
ACCUMULATION_PHASES = ("POST_HALVING_YEAR_2", "PRE_HALVING_YEAR")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_date(value: str) -> date:
    return datetime.fromisoformat(str(value)[:10]).date()


def finite_or_none(value):
    if value is None:
        return None
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


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


def forward_return(prices: dict[date, float], origin: date, horizon: int):
    endpoint = origin + timedelta(days=horizon)
    endpoint_price = prices.get(endpoint)
    if endpoint_price is None:
        return None
    return 100.0 * (endpoint_price / prices[origin] - 1.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--recovery-addendum", required=True)
    parser.add_argument("--mandate-contract", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    snapshot = Path(args.snapshot).resolve()
    design = Path(args.design).resolve()
    recovery = Path(args.recovery_addendum).resolve()
    mandate = Path(args.mandate_contract).resolve()
    output = Path(args.output).resolve()

    for name, path in {
        "snapshot": snapshot,
        "design": design,
        "recovery_addendum": recovery,
        "mandate_contract": mandate,
    }.items():
        require(path.is_file(), f"Required governed input missing: {name}={path}")
    require(not output.exists(), "V2 cycle-study output already exists; refusing overwrite")

    hashes_before = {
        "snapshot": sha256(snapshot),
        "design": sha256(design),
        "recovery_addendum": sha256(recovery),
        "mandate_contract": sha256(mandate),
    }
    require(hashes_before["snapshot"] == EXPECTED_SNAPSHOT_SHA256, "Frozen V2 snapshot hash mismatch")

    design_text = design.read_text(encoding="utf-8")
    recovery_text = recovery.read_text(encoding="utf-8")
    mandate_text = mandate.read_text(encoding="utf-8")

    for fragment in (
        STUDY_ID,
        "2012-11-28 -> 2016-07-09",
        "2016-07-09 -> 2020-05-11",
        "2020-05-11 -> 2024-04-20",
        "POST_HALVING_EXPANSION_PEAK",
        "RESET_TROUGH",
        "PRE_HALVING_RECOVERY",
        "exact 1095-calendar-day forward return",
        "PATTERN_SUPPORTED_DESCRIPTIVELY",
    ):
        require(fragment.lower() in design_text.lower(), f"V2 design missing required boundary: {fragment}")

    for fragment in (
        "ReferenceRateUSD",
        "PriceUSD",
        "source substitution",
        "research-only",
    ):
        require(fragment.lower() in recovery_text.lower(), f"V2 recovery addendum missing boundary: {fragment}")

    for fragment in (
        "long-duration accumulation assets",
        "approximately three-year intended holding period",
        "not automatic sell signals",
        "No one feature, including calendar year or halving distance, may independently force a BUY or SELL",
    ):
        require(fragment.lower() in mandate_text.lower(), f"Mandate contract missing required boundary: {fragment}")

    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    require(payload.get("snapshot_id") == EXPECTED_SNAPSHOT_ID, "Unexpected V2 snapshot id")
    require(payload.get("source_provider") == "Coin Metrics Community API", "Unexpected V2 source provider")
    require(payload.get("source_asset") == "btc", "Unexpected V2 source asset")
    require(payload.get("source_metric") == "PriceUSD", "Unexpected V2 source metric")
    require(payload.get("source_frequency") == "1d", "Unexpected V2 source frequency")
    require(payload.get("canonical_database_modified") is False, "Snapshot claims canonical database modification")
    require(payload.get("cycle_policy_authority_granted") is False, "Snapshot grants cycle authority")

    rows = payload.get("rows")
    require(isinstance(rows, list) and rows, "V2 snapshot has no rows")

    prices: dict[date, float] = {}
    for row in rows:
        obs = parse_date(row["observation_date"])
        require(obs not in prices, f"Duplicate V2 snapshot date: {obs.isoformat()}")
        price = float(row["price_usd"])
        require(price > 0, f"Non-positive V2 price: {obs.isoformat()}")
        prices[obs] = price

    dates = sorted(prices)
    require(dates[0] <= date(2011, 1, 1), "V2 snapshot does not reach required early history")
    require(dates[-1] >= date(2024, 4, 19), "V2 snapshot does not reach required completed-cycle end")

    running_peak = None
    drawdown_from_high: dict[date, float] = {}
    for obs in dates:
        price = prices[obs]
        running_peak = price if running_peak is None else max(running_peak, price)
        drawdown_from_high[obs] = 100.0 * (price / running_peak - 1.0)

    completed_cycles = []
    for idx in range(len(HALVINGS) - 1):
        start = HALVINGS[idx]
        end = HALVINGS[idx + 1]
        interval_dates = [d for d in dates if start <= d < end]
        expected_days = (end - start).days
        coverage_ratio = len(interval_dates) / expected_days if expected_days else 0.0
        adequate = bool(
            interval_dates
            and coverage_ratio >= 0.95
            and (interval_dates[0] - start).days <= 1
            and (end - interval_dates[-1]).days <= 1
        )

        first_post_year = start.year + 1
        second_post_year = start.year + 2
        pre_halving_year = end.year - 1

        expansion_end = min(date(first_post_year, 12, 31), end - timedelta(days=1))
        expansion_dates = [d for d in interval_dates if start <= d <= expansion_end]
        require(expansion_dates, f"No expansion-window observations for cycle starting {start}")
        expansion_peak_date = max(expansion_dates, key=lambda d: prices[d])

        reset_end = min(date(second_post_year, 12, 31), end - timedelta(days=1))
        reset_dates = [d for d in interval_dates if expansion_peak_date < d <= reset_end]
        require(reset_dates, f"No reset-window observations for cycle starting {start}")
        reset_trough_date = min(reset_dates, key=lambda d: prices[d])

        recovery_end = min(date(pre_halving_year, 12, 31), end - timedelta(days=1))
        require(recovery_end >= reset_trough_date, f"Recovery window invalid for cycle starting {start}")
        recovery_return = 100.0 * (prices[recovery_end] / prices[reset_trough_date] - 1.0) if recovery_end in prices else None

        ordering_match = (
            expansion_peak_date.year == first_post_year
            and reset_trough_date.year == second_post_year
            and reset_trough_date > expansion_peak_date
        )

        cycle_record = {
            "cycle_start_halving": start.isoformat(),
            "next_halving": end.isoformat(),
            "expected_calendar_days": expected_days,
            "observed_daily_rows": len(interval_dates),
            "coverage_ratio": coverage_ratio,
            "adequate_coverage": adequate,
            "post_halving_expansion_peak_date": expansion_peak_date.isoformat(),
            "post_halving_expansion_peak_price_usd": prices[expansion_peak_date],
            "reset_trough_date": reset_trough_date.isoformat(),
            "reset_trough_price_usd": prices[reset_trough_date],
            "peak_to_reset_drawdown_pct": 100.0 * (prices[reset_trough_date] / prices[expansion_peak_date] - 1.0),
            "pre_halving_recovery_endpoint_date": recovery_end.isoformat(),
            "pre_halving_recovery_return_pct": recovery_return,
            "refined_expansion_reset_ordering_match": ordering_match,
            "accumulation_phase_diagnostics": {},
        }

        for phase in ACCUMULATION_PHASES:
            phase_year = second_post_year if phase == "POST_HALVING_YEAR_2" else pre_halving_year
            phase_dates = [d for d in interval_dates if d.year == phase_year]
            monthly_dates = []
            seen_months = set()
            for obs in phase_dates:
                key = (obs.year, obs.month)
                if key not in seen_months:
                    seen_months.add(key)
                    monthly_dates.append(obs)

            returns_3y = []
            drawdowns = []
            monthly_rows = []
            for origin in monthly_dates:
                value = forward_return(prices, origin, 1095)
                monthly_rows.append({
                    "origin_date": origin.isoformat(),
                    "origin_price_usd": prices[origin],
                    "drawdown_from_running_high_pct": drawdown_from_high[origin],
                    "forward_1095d_exact_endpoint_date": (origin + timedelta(days=1095)).isoformat(),
                    "forward_1095d_return_pct": value,
                })
                if value is not None:
                    returns_3y.append(value)
                    drawdowns.append(drawdown_from_high[origin])

            cycle_record["accumulation_phase_diagnostics"][phase] = {
                "calendar_year": phase_year,
                "monthly_anchor_rows": len(monthly_dates),
                "exact_3y_outcomes": len(returns_3y),
                "missing_3y_outcomes": len(monthly_dates) - len(returns_3y),
                "median_3y_return_pct": finite_or_none(median(returns_3y)) if returns_3y else None,
                "mean_3y_return_pct": finite_or_none(mean(returns_3y)) if returns_3y else None,
                "positive_3y_return_rate": finite_or_none(sum(v > 0 for v in returns_3y) / len(returns_3y)) if returns_3y else None,
                "worst_3y_return_pct": finite_or_none(min(returns_3y)) if returns_3y else None,
                "best_3y_return_pct": finite_or_none(max(returns_3y)) if returns_3y else None,
                "median_origin_drawdown_from_running_high_pct": finite_or_none(median(drawdowns)) if drawdowns else None,
                "monthly_anchor_detail": monthly_rows,
            }

        completed_cycles.append(cycle_record)

    adequate_cycles = [c for c in completed_cycles if c["adequate_coverage"]]
    ordering_matches = sum(bool(c["refined_expansion_reset_ordering_match"]) for c in adequate_cycles)

    phase_cycle_positive = {}
    for phase in ACCUMULATION_PHASES:
        evidence = []
        for cycle in adequate_cycles:
            diag = cycle["accumulation_phase_diagnostics"][phase]
            if diag["exact_3y_outcomes"] > 0:
                evidence.append({
                    "cycle_start_halving": cycle["cycle_start_halving"],
                    "median_3y_return_pct": diag["median_3y_return_pct"],
                    "positive_3y_return_rate": diag["positive_3y_return_rate"],
                    "exact_3y_outcomes": diag["exact_3y_outcomes"],
                })
        phase_cycle_positive[phase] = evidence

    all_three_adequate = len(adequate_cycles) == 3
    ordering_gate = ordering_matches >= 2
    each_phase_positive_each_cycle = True
    positive_cycle_counts = {}
    for phase in ACCUMULATION_PHASES:
        evidence = phase_cycle_positive[phase]
        positive_count = sum(
            row["median_3y_return_pct"] is not None and row["median_3y_return_pct"] > 0
            for row in evidence
        )
        positive_cycle_counts[phase] = positive_count
        if len(evidence) != 3 or positive_count != len(evidence):
            each_phase_positive_each_cycle = False

    no_single_cycle_sole_positive_source = all(
        positive_cycle_counts[phase] >= 2 for phase in ACCUMULATION_PHASES
    )

    if not all_three_adequate:
        interpretation = "INSUFFICIENT_EXTENDED_HISTORY"
    elif ordering_gate and each_phase_positive_each_cycle and no_single_cycle_sole_positive_source:
        interpretation = "PATTERN_SUPPORTED_DESCRIPTIVELY"
    elif ordering_gate or no_single_cycle_sole_positive_source:
        interpretation = "PATTERN_PARTIALLY_SUPPORTED"
    else:
        interpretation = "PATTERN_NOT_SUPPORTED"

    result = {
        "study_id": STUDY_ID,
        "study_scope": "BITCOIN_THREE_COMPLETED_HALVING_CYCLE_EXTENDED_HISTORY_STUDY",
        "evidence_class": EVIDENCE_CLASS,
        "strict_vintage_point_in_time_claim_allowed": False,
        "source_snapshot_id": EXPECTED_SNAPSHOT_ID,
        "source_snapshot_sha256": hashes_before["snapshot"],
        "source_metric": "PriceUSD",
        "source_provider": "Coin Metrics Community API",
        "source_first_observation_date": dates[0].isoformat(),
        "source_last_observation_date": dates[-1].isoformat(),
        "source_unique_daily_rows": len(dates),
        "completed_cycle_count": len(completed_cycles),
        "adequately_covered_completed_cycle_count": len(adequate_cycles),
        "refined_expansion_reset_ordering_matches": ordering_matches,
        "completed_cycle_diagnostics": completed_cycles,
        "phase_cycle_positive_evidence": phase_cycle_positive,
        "interpretation_controls": {
            "all_three_completed_cycles_adequately_covered": all_three_adequate,
            "at_least_two_of_three_refined_ordering_matches": ordering_gate,
            "both_accumulation_phases_positive_median_in_each_cycle_where_available": each_phase_positive_each_cycle,
            "no_single_cycle_is_sole_positive_source": no_single_cycle_sole_positive_source,
            "independent_completed_cycle_sample_size": len(adequate_cycles),
            "small_sample_warning": True,
            "monthly_anchor_observations_are_overlapping": True,
        },
        "study_interpretation": interpretation,
        "cycle_policy_authority_granted": False,
        "cycle_policy_promotion_recommendation_allowed": interpretation == "PATTERN_SUPPORTED_DESCRIPTIVELY",
        "calendar_only_execution_allowed": False,
        "v1_result_modified": False,
        "v4_model_selection_affected": False,
        "recommendation_thresholds_changed": False,
        "production_policy_changed": False,
        "autonomous_execution_allowed": False,
        "canonical_database_modified": False,
        "governed_source_hashes_before": hashes_before,
        "next_gate": "PRESERVE_AND_REVIEW_BITCOIN_CYCLE_STUDY_V2",
    }

    hashes_after = {
        "snapshot": sha256(snapshot),
        "design": sha256(design),
        "recovery_addendum": sha256(recovery),
        "mandate_contract": sha256(mandate),
    }
    require(hashes_after == hashes_before, "Governed V2 source evidence changed during study")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("BITCOIN_FOUR_YEAR_CYCLE_EXTENDED_HISTORY_V2=PASS")
    print(f"SOURCE_SNAPSHOT_SHA256={hashes_before['snapshot']}")
    print(f"SOURCE_COVERAGE={dates[0].isoformat()}_TO_{dates[-1].isoformat()}")
    print(f"COMPLETED_CYCLES={len(completed_cycles)}")
    print(f"ADEQUATELY_COVERED_COMPLETED_CYCLES={len(adequate_cycles)}")
    print(f"REFINED_EXPANSION_RESET_ORDERING_MATCHES={ordering_matches}")
    print(f"STUDY_INTERPRETATION={interpretation}")
    for cycle in completed_cycles:
        print(
            "CYCLE=" + cycle["cycle_start_halving"] + "_TO_" + cycle["next_halving"]
            + "|ADEQUATE=" + str(cycle["adequate_coverage"]).upper()
            + "|EXPANSION_PEAK=" + cycle["post_halving_expansion_peak_date"]
            + "|RESET_TROUGH=" + cycle["reset_trough_date"]
            + "|ORDERING_MATCH=" + str(cycle["refined_expansion_reset_ordering_match"]).upper()
        )
        for phase in ACCUMULATION_PHASES:
            diag = cycle["accumulation_phase_diagnostics"][phase]
            print(
                "CYCLE_PHASE=" + cycle["cycle_start_halving"] + "|" + phase
                + "|YEAR=" + str(diag["calendar_year"])
                + "|3Y_OUTCOMES=" + str(diag["exact_3y_outcomes"])
                + "|3Y_MEDIAN_RETURN_PCT=" + str(diag["median_3y_return_pct"])
                + "|3Y_POSITIVE_RATE=" + str(diag["positive_3y_return_rate"])
                + "|3Y_WORST_RETURN_PCT=" + str(diag["worst_3y_return_pct"])
            )
    print("CYCLE_POLICY_AUTHORITY_GRANTED=FALSE")
    print("CALENDAR_ONLY_EXECUTION_ALLOWED=FALSE")
    print("V1_RESULT_MODIFIED=FALSE")
    print("V4_MODEL_SELECTION_AFFECTED=FALSE")
    print("PRODUCTION_POLICY_CHANGED=FALSE")
    print("CANONICAL_DATABASE_MODIFIED=FALSE")
    print("NEXT_GATE=PRESERVE_AND_REVIEW_BITCOIN_CYCLE_STUDY_V2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
