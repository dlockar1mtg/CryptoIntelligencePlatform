from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

SOURCE_ENDPOINT = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
SOURCE_PROVIDER = "Coin Metrics Community API"
SOURCE_ASSET = "btc"
SOURCE_METRIC = "ReferenceRateUSD"
SOURCE_FREQUENCY = "1d"
EVIDENCE_CLASS = "EXTERNAL_HISTORICAL_RESEARCH_SNAPSHOT_NOT_STRICT_VINTAGE_POINT_IN_TIME"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_date(value: str) -> date:
    return datetime.fromisoformat(value[:10]).date()


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "UIP-Bitcoin-Cycle-Research/2.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        require(response.status == 200, f"Coin Metrics HTTP status {response.status}")
        payload = response.read()
    parsed = json.loads(payload.decode("utf-8"))
    require(isinstance(parsed, dict), "Coin Metrics response is not a JSON object")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--start-date", default="2011-01-01")
    parser.add_argument("--end-date", required=True)
    args = parser.parse_args()

    output = Path(args.output).resolve()
    require(not output.exists(), "Extended-history source snapshot already exists; refusing overwrite")

    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)
    require(start_date <= date(2011, 1, 1), "Start date must be no later than 2011-01-01")
    require(end_date >= date(2024, 4, 19), "End date must cover through at least 2024-04-19")

    base_params = {
        "assets": SOURCE_ASSET,
        "metrics": SOURCE_METRIC,
        "frequency": SOURCE_FREQUENCY,
        "start_time": start_date.isoformat(),
        "end_time": end_date.isoformat(),
        "paging_from": "start",
        "page_size": "10000",
    }

    all_records: list[dict] = []
    page_count = 0
    next_page_token = None

    while True:
        params = dict(base_params)
        if next_page_token:
            params["next_page_token"] = next_page_token
        url = SOURCE_ENDPOINT + "?" + urllib.parse.urlencode(params)
        response = fetch_json(url)
        page_count += 1

        data = response.get("data")
        require(isinstance(data, list), "Coin Metrics response missing data list")
        all_records.extend(data)

        next_page_token = response.get("next_page_token")
        if not next_page_token:
            break
        require(page_count < 100, "Unexpected Coin Metrics pagination depth")

    require(all_records, "Coin Metrics returned no Bitcoin ReferenceRateUSD observations")

    by_date: dict[date, float] = {}
    raw_time_by_date: dict[date, str] = {}
    for record in all_records:
        require(record.get("asset") == SOURCE_ASSET, "Unexpected asset in Coin Metrics response")
        raw_time = str(record.get("time", ""))
        require(raw_time, "Coin Metrics observation missing time")
        obs_date = parse_date(raw_time)
        value = record.get(SOURCE_METRIC)
        require(value is not None, f"Coin Metrics observation missing {SOURCE_METRIC}: {raw_time}")
        price = float(value)
        require(price > 0, f"Non-positive Coin Metrics Bitcoin reference rate: {raw_time}")
        require(obs_date not in by_date, f"Duplicate Coin Metrics UTC calendar date: {obs_date.isoformat()}")
        by_date[obs_date] = price
        raw_time_by_date[obs_date] = raw_time

    ordered_dates = sorted(by_date)
    require(ordered_dates[0] <= date(2011, 1, 1), "Extended source does not reach 2011-01-01 or earlier")
    require(ordered_dates[-1] >= date(2024, 4, 19), "Extended source does not reach 2024-04-19")

    required_halving_pre_dates = (
        date(2012, 11, 27),
        date(2016, 7, 8),
        date(2020, 5, 10),
        date(2024, 4, 19),
    )
    for required_date in required_halving_pre_dates:
        require(required_date in by_date, f"Required pre-halving exact date missing: {required_date.isoformat()}")

    normalized_rows = [
        {
            "observation_date": obs_date.isoformat(),
            "source_time": raw_time_by_date[obs_date],
            "reference_rate_usd": by_date[obs_date],
        }
        for obs_date in ordered_dates
    ]

    result = {
        "snapshot_id": "BITCOIN_EXTENDED_HISTORY_COINMETRICS_V2",
        "source_provider": SOURCE_PROVIDER,
        "source_endpoint": SOURCE_ENDPOINT,
        "source_asset": SOURCE_ASSET,
        "source_metric": SOURCE_METRIC,
        "source_frequency": SOURCE_FREQUENCY,
        "requested_start_date": start_date.isoformat(),
        "requested_end_date": end_date.isoformat(),
        "evidence_class": EVIDENCE_CLASS,
        "strict_vintage_point_in_time_claim_allowed": False,
        "canonical_database_modified": False,
        "production_policy_changed": False,
        "cycle_policy_authority_granted": False,
        "page_count": page_count,
        "raw_record_count": len(all_records),
        "normalized_unique_daily_rows": len(normalized_rows),
        "first_observation_date": ordered_dates[0].isoformat(),
        "last_observation_date": ordered_dates[-1].isoformat(),
        "duplicate_calendar_dates_detected": False,
        "nonpositive_prices_detected": False,
        "rows": normalized_rows,
        "next_gate": "VALIDATE_AND_PRESERVE_EXTENDED_HISTORY_SOURCE_SNAPSHOT",
    }

    encoded = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded)

    print("BITCOIN_EXTENDED_HISTORY_SOURCE_ACQUISITION=PASS")
    print(f"SOURCE_PROVIDER={SOURCE_PROVIDER}")
    print(f"SOURCE_METRIC={SOURCE_METRIC}")
    print(f"SOURCE_FREQUENCY={SOURCE_FREQUENCY}")
    print(f"FIRST_OBSERVATION_DATE={ordered_dates[0].isoformat()}")
    print(f"LAST_OBSERVATION_DATE={ordered_dates[-1].isoformat()}")
    print(f"NORMALIZED_UNIQUE_DAILY_ROWS={len(normalized_rows)}")
    print(f"SOURCE_SNAPSHOT_SHA256={sha256_bytes(encoded)}")
    print("CANONICAL_DATABASE_MODIFIED=FALSE")
    print("CYCLE_POLICY_AUTHORITY_GRANTED=FALSE")
    print("PRODUCTION_POLICY_CHANGED=FALSE")
    print("NEXT_GATE=VALIDATE_AND_PRESERVE_EXTENDED_HISTORY_SOURCE_SNAPSHOT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
