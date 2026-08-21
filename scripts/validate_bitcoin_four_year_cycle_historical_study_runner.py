from __future__ import annotations

import argparse
import ast
from pathlib import Path


REQUIRED_FRAGMENTS = (
    'BITCOIN_FOUR_YEAR_CYCLE_HISTORICAL_STUDY_V1',
    'duckdb.connect(str(database), read_only=True)',
    "asset_id='bitcoin'",
    'timedelta(days=horizon)',
    'endpoint_price = prices.get(endpoint)',
    'HORIZONS = (365, 730, 1095)',
    'POST_HALVING_YEAR_2',
    'PRE_HALVING_YEAR',
    'monthly_anchor_dates',
    'drawdown_from_high',
    'PATTERN_SUPPORTED_DESCRIPTIVELY',
    'PATTERN_PARTIALLY_SUPPORTED',
    'PATTERN_NOT_SUPPORTED',
    'INSUFFICIENT_CANONICAL_HISTORY',
    'cycle_policy_authority_granted": False',
    'v4_model_selection_affected": False',
    'production_policy_changed": False',
    'autonomous_execution_allowed": False',
    'source_database_modified": False',
)

PROHIBITED_FRAGMENTS = (
    'fit(',
    'fit_predict(',
    'choose_winner',
    'fillna(0',
    'interpolate(',
    "method='nearest'",
    'method="nearest"',
    "direction='nearest'",
    'direction="nearest"',
    "get_indexer([endpoint], method='nearest')",
    'get_indexer([endpoint], method="nearest")',
    'read_only=False',
    'production_policy_changed": True',
    'cycle_policy_authority_granted": True',
    'autonomous_execution_allowed": True',
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--design', required=True)
    parser.add_argument('--mandate-contract', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    runner = Path(args.runner).resolve()
    design = Path(args.design).resolve()
    mandate = Path(args.mandate_contract).resolve()
    output = Path(args.output).resolve()

    for name, path in {'runner': runner, 'design': design, 'mandate': mandate}.items():
        require(path.is_file(), f'Required input missing: {name}={path}')
    require(not output.exists(), 'Study output already exists before execution')

    source = runner.read_text(encoding='utf-8')
    design_text = design.read_text(encoding='utf-8')
    mandate_text = mandate.read_text(encoding='utf-8')
    ast.parse(source)

    for fragment in REQUIRED_FRAGMENTS:
        require(fragment in source, f'Runner missing required fragment: {fragment}')
    for fragment in PROHIBITED_FRAGMENTS:
        require(fragment not in source, f'Runner contains prohibited fragment: {fragment}')

    for fragment in (
        'BITCOIN_FOUR_YEAR_CYCLE_HISTORICAL_STUDY_V1',
        'exact 1095-calendar-day forward return',
        'monthly anchor',
        'No nearest-date endpoint',
        'HISTORICAL_CANONICAL_PRICE_STUDY_NOT_STRICT_VINTAGE_POINT_IN_TIME',
        'INSUFFICIENT_EVIDENCE_FOR_POLICY_SKILL',
    ):
        require(fragment.lower() in design_text.lower(), f'Design missing required boundary: {fragment}')

    for fragment in (
        'long-duration accumulation assets',
        'approximately three-year intended holding period',
        'Short-term forecasts are primarily tactical entry-timing evidence',
        'not automatic sell signals',
        'four-year halving cycle is a research hypothesis',
        'These year labels are not deterministic execution rules',
        'No autonomous purchase or sale execution is authorized',
    ):
        require(fragment.lower() in mandate_text.lower(), f'Mandate missing required boundary: {fragment}')

    print('BITCOIN_FOUR_YEAR_CYCLE_HISTORICAL_STUDY_RUNNER_VALIDATION=PASS')
    print('STUDY_SCOPE=BITCOIN_ONLY_FOUR_YEAR_CYCLE_HISTORICAL_STUDY')
    print('DATABASE_OPEN_MODE=READ_ONLY')
    print('EXACT_CALENDAR_ENDPOINT_LOOKUP=REQUIRED')
    print('NEAREST_DATE_SUBSTITUTION_ALLOWED=FALSE')
    print('FORWARD_HORIZONS=365,730,1095')
    print('PRIMARY_HOLDING_DIAGNOSTIC_DAYS=1095')
    print('MONTHLY_ANCHOR_ROBUSTNESS=REQUIRED')
    print('MODEL_FITTING_ALLOWED=FALSE')
    print('RECOMMENDATION_THRESHOLD_OPTIMIZATION_ALLOWED=FALSE')
    print('CYCLE_POLICY_AUTHORITY_GRANTED=FALSE')
    print('PRODUCTION_POLICY_CHANGE_ALLOWED=FALSE')
    print('AUTONOMOUS_EXECUTION_ALLOWED=FALSE')
    print('STUDY_EXECUTION_PERFORMED=FALSE')
    print('NEXT_GATE=AUTHORIZE_BITCOIN_FOUR_YEAR_CYCLE_HISTORICAL_STUDY_EXECUTION')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
