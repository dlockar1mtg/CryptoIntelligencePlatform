from __future__ import annotations

import argparse
import ast
from pathlib import Path

REQUIRED_RUNNER_FRAGMENTS = (
    'BITCOIN_FOUR_YEAR_CYCLE_EXTENDED_HISTORY_V2',
    'EXPECTED_SNAPSHOT_SHA256 = "549bc0172dbefaf9936705df9da58ead29cd583141c5eaf294dd2fed5a693961"',
    'PriceUSD',
    'Coin Metrics Community API',
    'HALVINGS = (',
    'date(2012, 11, 28)',
    'date(2016, 7, 9)',
    'date(2020, 5, 11)',
    'date(2024, 4, 20)',
    'HORIZONS = (365, 730, 1095)',
    'endpoint = origin + timedelta(days=horizon)',
    'endpoint_price = prices.get(endpoint)',
    'POST_HALVING_YEAR_2',
    'PRE_HALVING_YEAR',
    'post_halving_expansion_peak_date',
    'reset_trough_date',
    'refined_expansion_reset_ordering_match',
    'adequately_covered_completed_cycle_count',
    'PATTERN_SUPPORTED_DESCRIPTIVELY',
    'PATTERN_PARTIALLY_SUPPORTED',
    'PATTERN_NOT_SUPPORTED',
    'INSUFFICIENT_EXTENDED_HISTORY',
    'cycle_policy_authority_granted": False',
    'calendar_only_execution_allowed": False',
    'v1_result_modified": False',
    'v4_model_selection_affected": False',
    'production_policy_changed": False',
    'autonomous_execution_allowed": False',
    'canonical_database_modified": False',
)

PROHIBITED_RUNNER_FRAGMENTS = (
    'duckdb.connect',
    'INSERT INTO',
    'UPDATE ',
    'DELETE FROM',
    'fillna(',
    'interpolate(',
    "method='nearest'",
    'method="nearest"',
    "direction='nearest'",
    'direction="nearest"',
    'fit(',
    'fit_predict(',
    'choose_winner',
    'cycle_policy_authority_granted": True',
    'calendar_only_execution_allowed": True',
    'production_policy_changed": True',
    'canonical_database_modified": True',
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--design', required=True)
    parser.add_argument('--recovery-addendum', required=True)
    parser.add_argument('--mandate-contract', required=True)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    runner = Path(args.runner).resolve()
    design = Path(args.design).resolve()
    recovery = Path(args.recovery_addendum).resolve()
    mandate = Path(args.mandate_contract).resolve()
    snapshot = Path(args.snapshot).resolve()
    output = Path(args.output).resolve()

    for name, path in {
        'runner': runner,
        'design': design,
        'recovery_addendum': recovery,
        'mandate_contract': mandate,
        'snapshot': snapshot,
    }.items():
        require(path.is_file(), f'Required V2 input missing: {name}={path}')
    require(not output.exists(), 'V2 study output already exists before execution')

    source = runner.read_text(encoding='utf-8')
    design_text = design.read_text(encoding='utf-8')
    recovery_text = recovery.read_text(encoding='utf-8')
    mandate_text = mandate.read_text(encoding='utf-8')
    ast.parse(source)

    for fragment in REQUIRED_RUNNER_FRAGMENTS:
        require(fragment in source, f'V2 runner missing required fragment: {fragment}')

    for fragment in PROHIBITED_RUNNER_FRAGMENTS:
        require(fragment not in source, f'V2 runner contains prohibited fragment: {fragment}')

    for fragment in (
        'BITCOIN_FOUR_YEAR_CYCLE_EXTENDED_HISTORY_V2',
        'POST_HALVING_EXPANSION_PEAK',
        'RESET_TROUGH',
        'PRE_HALVING_RECOVERY',
        'exact 1095-calendar-day forward return',
        'all three completed halving intervals have adequate source coverage',
        'at least two of three completed cycles match the refined expansion -> reset ordering',
        'PATTERN_SUPPORTED_DESCRIPTIVELY',
    ):
        require(fragment.lower() in design_text.lower(), f'V2 design missing boundary: {fragment}')

    for fragment in (
        'ReferenceRateUSD',
        'PriceUSD',
        'source substitution',
        'research-only',
    ):
        require(fragment.lower() in recovery_text.lower(), f'V2 recovery addendum missing boundary: {fragment}')

    for fragment in (
        'long-duration accumulation assets',
        'approximately three-year intended holding period',
        'not automatic sell signals',
        'No one feature, including calendar year or halving distance, may independently force a BUY or SELL',
    ):
        require(fragment.lower() in mandate_text.lower(), f'Mandate contract missing boundary: {fragment}')

    print('BITCOIN_FOUR_YEAR_CYCLE_EXTENDED_HISTORY_V2_RUNNER_VALIDATION=PASS')
    print('STUDY_SCOPE=BITCOIN_THREE_COMPLETED_HALVING_CYCLE_EXTENDED_HISTORY_STUDY')
    print('SOURCE_PROVIDER=Coin Metrics Community API')
    print('SOURCE_METRIC=PriceUSD')
    print('SOURCE_SNAPSHOT_SHA256=549bc0172dbefaf9936705df9da58ead29cd583141c5eaf294dd2fed5a693961')
    print('COMPLETED_CYCLES_REQUIRED=3')
    print('FORWARD_HORIZONS=365,730,1095')
    print('PRIMARY_HOLDING_DIAGNOSTIC_DAYS=1095')
    print('EXACT_CALENDAR_ENDPOINT_LOOKUP=REQUIRED')
    print('NEAREST_DATE_SUBSTITUTION_ALLOWED=FALSE')
    print('INDEPENDENT_EVIDENTIARY_UNIT=COMPLETED_HALVING_CYCLE')
    print('MODEL_FITTING_ALLOWED=FALSE')
    print('RECOMMENDATION_THRESHOLD_OPTIMIZATION_ALLOWED=FALSE')
    print('CYCLE_POLICY_AUTHORITY_GRANTED=FALSE')
    print('CALENDAR_ONLY_EXECUTION_ALLOWED=FALSE')
    print('V1_RESULT_MODIFICATION_ALLOWED=FALSE')
    print('V4_MODEL_SELECTION_CHANGE_ALLOWED=FALSE')
    print('PRODUCTION_POLICY_CHANGE_ALLOWED=FALSE')
    print('AUTONOMOUS_EXECUTION_ALLOWED=FALSE')
    print('CANONICAL_DATABASE_WRITE_ALLOWED=FALSE')
    print('STUDY_EXECUTION_PERFORMED=FALSE')
    print('NEXT_GATE=AUTHORIZE_BITCOIN_CYCLE_STUDY_V2_EXECUTION')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
