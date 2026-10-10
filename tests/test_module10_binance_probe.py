"""Module 10 probes Binance once per host and skips the per-asset calls when it is unreachable."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
import requests
import yaml

from crypto_platform import module10
from crypto_platform.module10 import Module10Runner


ROOT = Path(__file__).resolve().parents[1]
FIXED_NOW = datetime(2026, 10, 10, 11, 30, tzinfo=timezone.utc)


class _Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"{self.status} Client Error")

    def json(self):
        return self.payload


class _Session:
    def __init__(self, binance_status: int):
        self.binance_status = binance_status
        self.urls: list[str] = []

    def get(self, url, params=None, timeout=None):
        self.urls.append(url)
        if "binance.com" in url:
            if self.binance_status >= 400:
                return _Response({"code": 0, "msg": "restricted location"}, self.binance_status)
            return _Response({} if url.endswith("/ping") else [])
        raise AssertionError(f"unexpected call {url}")


def _universe() -> pd.DataFrame:
    return pd.DataFrame([
        {"asset_id": asset, "symbol": symbol, "current_price_usd": price,
         "market_cap_usd": price * 1e7, "volume_24h_usd": price * 1e5}
        for asset, symbol, price in (
            ("bitcoin", "btc", 60000.0), ("ethereum", "eth", 3000.0),
            ("solana", "sol", 150.0), ("chainlink", "link", 15.0),
        )
    ])


def _runner(binance_status: int, *, enabled: bool = True) -> Module10Runner:
    settings = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    runner = object.__new__(Module10Runner)
    runner.config = copy.deepcopy(settings["module10"])
    runner.config["binance"]["enabled"] = enabled
    runner.session = _Session(binance_status)
    runner.written = {}
    runner.upsert = lambda table, frame: runner.written.setdefault(table, []).append(frame.copy())
    return runner


def _collect(runner: Module10Runner) -> dict:
    universe = _universe()
    counts = (runner.backfill_history(universe), runner.collect_derivatives(universe))
    return {"counts": counts, "written": runner.written}


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(module10.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(module10, "utcnow", lambda: FIXED_NOW)


def _assert_same_output(left: dict, right: dict) -> None:
    assert left["counts"] == right["counts"]
    assert left["written"].keys() == right["written"].keys()
    for table in left["written"]:
        for a, b in zip(left["written"][table], right["written"][table], strict=True):
            pd.testing.assert_frame_equal(a, b, check_exact=True)


def test_failed_probe_skips_calls_and_writes_the_same_rows_as_before(monkeypatch) -> None:
    # Old behaviour: no probe, every per-asset call fails after its retry.
    old = _runner(451)
    monkeypatch.setattr(old, "binance_available", lambda market: True, raising=False)
    old_output = _collect(old)
    old_calls = len(old.session.urls)

    new = _runner(451)
    new_output = _collect(new)

    _assert_same_output(old_output, new_output)
    history = new_output["written"]["research_market_daily"][0]
    assert set(history["source"]) == {"coingecko_snapshot"}
    assert len(history) == 4
    assert new_output["counts"] == (4, 0)
    # Two probes (spot and futures), each with its one retry, instead of 3 calls x 2 tries per asset.
    assert new.session.urls == [module10.BINANCE_PROBES["spot"]] * 2 + [module10.BINANCE_PROBES["futures"]] * 2
    assert old_calls == 4 * 3 * 2


def test_disabled_in_config_makes_no_binance_calls(monkeypatch) -> None:
    old = _runner(451)
    monkeypatch.setattr(old, "binance_available", lambda market: True, raising=False)
    old_output = _collect(old)

    disabled = _runner(451, enabled=False)
    output = _collect(disabled)

    assert disabled.session.urls == []
    _assert_same_output(old_output, output)


def test_working_binance_is_still_called_per_asset() -> None:
    runner = _runner(200)
    _collect(runner)
    urls = runner.session.urls
    assert urls[0] == module10.BINANCE_PROBES["spot"]
    assert urls.count("https://api.binance.com/api/v3/klines") == 4
    assert urls.count("https://fapi.binance.com/fapi/v1/fundingRate") == 4
    assert module10.BINANCE_PROBES["futures"] in urls
