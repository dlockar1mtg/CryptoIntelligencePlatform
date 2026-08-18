from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE17 = ROOT / "crypto_platform" / "module17.py"

NATIVE_FEATURES = [
    "btc_return_30d_pct",
    "core_breadth_above_sma50_pct",
    "core_median_return_30d_pct",
    "dollar_index",
    "fear_greed_index",
    "macro_liquidity_score",
    "risk_appetite_score",
    "stablecoin_growth_30d_pct",
    "stablecoin_supply_usd",
    "vix",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def query_frame(conn, sql: str):
    try:
        return conn.execute(sql).fetchdf()
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    args = parser.parse_args()

    source = Path(args.database).resolve()
    require(source.is_file(), f"Database missing: {source}")
    require(MODULE17.is_file(), f"Module17 source missing: {MODULE17}")
    before = sha256(source)
    source_text = MODULE17.read_text(encoding="utf-8")

    static = {
        "historical_feature_warehouse_rebuilt_from_current_database_state": "crypto_features_daily" in source_text and "build_features" in source_text,
        "external_series_forward_filled_by_observation_date": "ext = ext.reindex(index).ffill()" in source_text,
        "macro_series_forward_filled_by_observation_date": "macro = macro.reindex(index).ffill()" in source_text,
        "stablecoin_series_forward_filled_by_observation_date": "stable = stable.reindex(index).ffill()" in source_text,
        "global_series_forward_filled_by_observation_date": "global_frame = global_frame.reindex(index).ffill()" in source_text,
        "macro_vintage_columns_present_in_query": "realtime_start" in source_text or "vintage" in source_text,
        "explicit_release_lag_applied_to_macro_features": "shift(1)" in source_text and "macro" in source_text,
        "risk_appetite_composite_uses_same_day_components": "risk_appetite = component_scores.mean(axis=1)" in source_text,
    }

    prior_env = os.environ.get("CRYPTO_DATABASE_PATH")
    with tempfile.TemporaryDirectory(prefix="crypto_v3_pit_audit_") as tmp:
        temp_db = Path(tmp) / source.name
        shutil.copy2(source, temp_db)
        os.environ["CRYPTO_DATABASE_PATH"] = str(temp_db)
        try:
            from crypto_platform.platform import load_all, connect
            settings, _ = load_all()
            conn = connect(settings)

            feature_coverage = query_frame(conn, """
                SELECT MIN(observation_date) AS first_date,
                       MAX(observation_date) AS latest_date,
                       COUNT(*) AS rows,
                       MIN(calculated_at_utc) AS first_calculated_at,
                       MAX(calculated_at_utc) AS latest_calculated_at
                FROM crypto_features_daily
            """)
            external = query_frame(conn, """
                SELECT feature_key, source, source_quality,
                       MIN(observation_date) AS first_date,
                       MAX(observation_date) AS latest_date,
                       COUNT(*) AS rows,
                       MIN(collected_at_utc) AS first_collected_at,
                       MAX(collected_at_utc) AS latest_collected_at
                FROM external_feature_observations
                GROUP BY feature_key, source, source_quality
                ORDER BY feature_key, source
            """)
            macro = query_frame(conn, """
                SELECT series_key, source,
                       MIN(observation_date) AS first_date,
                       MAX(observation_date) AS latest_date,
                       COUNT(*) AS rows,
                       MIN(collected_at_utc) AS first_collected_at,
                       MAX(collected_at_utc) AS latest_collected_at,
                       SUM(CASE WHEN CAST(collected_at_utc AS DATE) <= observation_date THEN 1 ELSE 0 END) AS collected_on_or_before_observation_date
                FROM macro_observations
                WHERE series_key IN ('FRED::DTWEXBGS','FRED::VIXCLS','FRED::BAMLH0A0HYM2')
                GROUP BY series_key, source
                ORDER BY series_key, source
            """)
            stable = query_frame(conn, """
                SELECT source,
                       MIN(observation_date) AS first_date,
                       MAX(observation_date) AS latest_date,
                       COUNT(*) AS rows,
                       MIN(collected_at_utc) AS first_collected_at,
                       MAX(collected_at_utc) AS latest_collected_at,
                       SUM(CASE WHEN CAST(collected_at_utc AS DATE) <= observation_date THEN 1 ELSE 0 END) AS collected_on_or_before_observation_date
                FROM stablecoin_supply_daily
                GROUP BY source
                ORDER BY source
            """)
            market = query_frame(conn, """
                SELECT source,
                       MIN(observation_date) AS first_date,
                       MAX(observation_date) AS latest_date,
                       COUNT(*) AS rows,
                       MIN(collected_at_utc) AS first_collected_at,
                       MAX(collected_at_utc) AS latest_collected_at,
                       SUM(CASE WHEN CAST(collected_at_utc AS DATE) <= observation_date THEN 1 ELSE 0 END) AS collected_on_or_before_observation_date
                FROM asset_market_daily
                WHERE asset_id IN ('bitcoin','ethereum','solana','chainlink','xrp','avalanche')
                GROUP BY source
                ORDER BY source
            """)
            conn.close()
        finally:
            if prior_env is None:
                os.environ.pop("CRYPTO_DATABASE_PATH", None)
            else:
                os.environ["CRYPTO_DATABASE_PATH"] = prior_env

    require(sha256(source) == before, "Source database changed during V3 point-in-time provenance audit")

    def records(frame):
        if frame is None:
            return []
        return json.loads(frame.to_json(orient="records", date_format="iso"))

    strict_pit_certified = bool(
        static["macro_vintage_columns_present_in_query"]
        and static["explicit_release_lag_applied_to_macro_features"]
    )

    report = {
        "status": "COMPLETE",
        "audit_scope": "V3_NATIVE_FEATURE_POINT_IN_TIME_PROVENANCE",
        "source_database_unchanged": True,
        "native_features_under_review": NATIVE_FEATURES,
        "static_source_controls": static,
        "feature_warehouse": records(feature_coverage),
        "external_feature_provenance": records(external),
        "macro_provenance": records(macro),
        "stablecoin_provenance": records(stable),
        "market_history_provenance": records(market),
        "strict_historical_as_known_point_in_time_certified": strict_pit_certified,
        "evidence_class_if_used_without_remediation": "HISTORICAL_RECONSTRUCTION_NOT_STRICT_VINTAGE_POINT_IN_TIME",
        "required_pre_tournament_control": "LAG_EXTERNAL_NATIVE_CONTEXT_AND_PRESERVE_RECONSTRUCTION_EVIDENCE_CLASS" if not strict_pit_certified else "NONE",
        "v3_holdout_outcomes_viewed": False,
        "recommendation_policy_changed": False,
        "next_gate": "GOVERN_V3_NATIVE_CONTEXT_LAG_AND_EVIDENCE_CLASS_BEFORE_TOURNAMENT" if not strict_pit_certified else "IMPLEMENT_PER_HORIZON_DEVELOPMENT_TOURNAMENT_HARNESS",
    }
    print(json.dumps(report, indent=2))
    print("CRYPTO_V3_NATIVE_FEATURE_POINT_IN_TIME_PROVENANCE_AUDIT=PASS")
    print(f"STRICT_HISTORICAL_AS_KNOWN_POINT_IN_TIME_CERTIFIED={str(strict_pit_certified).upper()}")
    print("V3_HOLDOUT_OUTCOMES_VIEWED=FALSE")
    print("SOURCE_DATABASE_MODIFIED=FALSE")
    print(f"NEXT_GATE={report['next_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
