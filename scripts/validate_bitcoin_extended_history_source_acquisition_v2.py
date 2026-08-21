from __future__ import annotations

import argparse
import ast
from pathlib import Path

REQUIRED_RUNNER_FRAGMENTS = (
    'community-api.coinmetrics.io/v4/timeseries/asset-metrics',
    'ReferenceRateUSD',
    'frequency": SOURCE_FREQUENCY',
    'paging_from": "start"',
    'page_size": "10000"',
    '2011-01-01',
    '2024-04-19',
    'Duplicate Coin Metrics UTC calendar date',
    'price > 0',
    'strict_vintage_point_in_time_claim_allowed": False',
    'canonical_database_modified": False',
    'production_policy_changed": False',
    'cycle_policy_authority_granted": False',
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
    'fit(',
    'fit_predict(',
    'cycle_policy_authority_granted": True',
    'production_policy_changed": True',
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--design', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    runner = Path(args.runner).resolve()
    design = Path(args.design).resolve()
    output = Path(args.output).resolve()

    require(runner.is_file(), f'Acquisition runner missing: {runner}')
    require(design.is_file(), f'V2 design missing: {design}')
    require(not output.exists(), 'Extended-history source snapshot already exists before acquisition')

    source = runner.read_text(encoding='utf-8')
    design_text = design.read_text(encoding='utf-8')
    ast.parse(source)

    for fragment in REQUIRED_RUNNER_FRAGMENTS:
        require(fragment in source, f'Acquisition runner missing required fragment: {fragment}')

    for fragment in PROHIBITED_RUNNER_FRAGMENTS:
        require(fragment not in source, f'Acquisition runner contains prohibited fragment: {fragment}')

    for fragment in (
        'BITCOIN_FOUR_YEAR_CYCLE_EXTENDED_HISTORY_V2',
        'Coin Metrics Community API',
        'ReferenceRateUSD',
        'EXTERNAL_HISTORICAL_RESEARCH_SNAPSHOT_NOT_STRICT_VINTAGE_POINT_IN_TIME',
        'not merged into `data/crypto_intelligence.duckdb`',
        'No synthetic prices, interpolation, nearest-date substitution, forward-fill, backward-fill, or zero imputation',
        '2012-11-28 -> 2016-07-09',
        '2016-07-09 -> 2020-05-11',
        '2020-05-11 -> 2024-04-20',
        'BUILD_AND_VALIDATE_EXTENDED_HISTORY_SOURCE_SNAPSHOT',
    ):
        require(fragment.lower() in design_text.lower(), f'V2 design missing required boundary: {fragment}')

    print('BITCOIN_EXTENDED_HISTORY_SOURCE_ACQUISITION_VALIDATION=PASS')
    print('SOURCE_PROVIDER=Coin Metrics Community API')
    print('SOURCE_ASSET=btc')
    print('SOURCE_METRIC=ReferenceRateUSD')
    print('SOURCE_FREQUENCY=1d')
    print('MINIMUM_REQUIRED_START_DATE=2011-01-01')
    print('MINIMUM_REQUIRED_END_DATE=2024-04-19')
    print('CANONICAL_DATABASE_WRITE_ALLOWED=FALSE')
    print('SYNTHETIC_PRICE_ALLOWED=FALSE')
    print('NEAREST_DATE_SUBSTITUTION_ALLOWED=FALSE')
    print('MODEL_FITTING_ALLOWED=FALSE')
    print('CYCLE_POLICY_AUTHORITY_GRANTED=FALSE')
    print('PRODUCTION_POLICY_CHANGE_ALLOWED=FALSE')
    print('SOURCE_ACQUISITION_PERFORMED=FALSE')
    print('NEXT_GATE=AUTHORIZE_EXTENDED_HISTORY_SOURCE_ACQUISITION')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
