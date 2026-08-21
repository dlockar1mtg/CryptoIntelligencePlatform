from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb

INSPECTION_ID = "BITCOIN_LIVE_INPUT_AUTHORITY_RESOLUTION_V1"
TZ = ZoneInfo("America/Chicago")

SEARCH_TERMS = {
    "price_refresh": [
        "canonical_market_daily",
        "latest_asset_market",
        "coingecko",
        "coinbase",
        "market data",
        "refresh",
        "asset_market_daily",
    ],
    "v4": [
        "V4_7D_VOLATILITY_STATE_EXTRA_TREES",
        "predictive_horizon_recovery_v4",
        "VOLATILITY_STATE_EXTRA_TREES",
        "ExtraTrees",
    ],
}

MACRO_TABLES = ["latest_macro_observations", "latest_macro_regime", "macro_observations", "macro_regime_daily"]
MODULE42_TABLES = ["latest_m42_asset_recommendations", "latest_m42_portfolio_plan"]
PRICE_TABLES = ["latest_asset_market", "canonical_market_daily", "asset_market_daily"]

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache"}
TEXT_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".ps1", ".sql"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_search(root: Path, terms: list[str], max_hits: int = 100) -> list[dict]:
    hits: list[dict] = []
    for path in root.rglob("*"):
        if len(hits) >= max_hits:
            break
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        low = text.lower()
        matched = [term for term in terms if term.lower() in low or term.lower() in rel.lower()]
        if matched:
            snippets = []
            for term in matched[:4]:
                m = re.search(re.escape(term), text, flags=re.IGNORECASE)
                if m:
                    start = max(0, m.start() - 180)
                    end = min(len(text), m.end() + 300)
                    snippets.append(text[start:end].replace("\r", " ").replace("\n", " "))
            hits.append({"path": rel, "matched_terms": matched, "snippets": snippets})
    return hits


def table_exists(con, name: str) -> bool:
    return con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='main' AND table_name=?",
        [name],
    ).fetchone()[0] > 0


def columns(con, name: str) -> list[str]:
    return [r[1] for r in con.execute(f"PRAGMA table_info('{name}')").fetchall()]


def latest_table_summary(con, name: str) -> dict:
    if not table_exists(con, name):
        return {"table": name, "exists": False}
    cols = columns(con, name)
    result = {"table": name, "exists": True, "columns": cols, "row_count": con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]}
    date_col = next((c for c in ["observation_date", "recommendation_date", "forecast_date", "calculated_at_utc", "collected_at_utc", "completed_at_utc"] if c in cols), None)
    result["date_column"] = date_col
    if date_col:
        result["latest_value"] = con.execute(f'SELECT MAX("{date_col}") FROM "{name}"').fetchone()[0]
    if "asset_id" in cols:
        result["bitcoin_rows"] = con.execute(f'SELECT COUNT(*) FROM "{name}" WHERE asset_id=?', ["bitcoin"]).fetchone()[0]
        if date_col:
            rows = con.execute(f'SELECT * FROM "{name}" WHERE asset_id=? ORDER BY "{date_col}" DESC LIMIT 3', ["bitcoin"]).fetchdf()
            result["latest_bitcoin_rows"] = json.loads(rows.to_json(orient="records", date_format="iso"))
    else:
        if date_col:
            rows = con.execute(f'SELECT * FROM "{name}" ORDER BY "{date_col}" DESC LIMIT 5').fetchdf()
            result["latest_rows"] = json.loads(rows.to_json(orient="records", date_format="iso"))
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", required=True)
    p.add_argument("--database", required=True)
    p.add_argument("--preserved-gap-review", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--records-dir", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    root = Path(args.repo_root).resolve()
    db = Path(args.database).resolve()
    gap_review = Path(args.preserved_gap_review).resolve()
    manifest = Path(args.manifest).resolve()
    records_dir = Path(args.records_dir).resolve()
    output = Path(args.output).resolve()

    for path in [root, db, gap_review, manifest]:
        if not path.exists():
            raise RuntimeError(f"Required path missing: {path}")
    if output.exists():
        raise RuntimeError("Output already exists; refusing overwrite")

    manifest_json = json.loads(manifest.read_text(encoding="utf-8"))
    if int(manifest_json.get("record_count", -1)) != 0:
        raise RuntimeError("Ledger record_count must remain zero")
    record_files = list(records_dir.rglob("*.json")) if records_dir.exists() else []
    if record_files:
        raise RuntimeError("Observation ledger is not empty")

    db_hash_before = sha256(db)
    gap_hash = sha256(gap_review)

    price_hits = repo_search(root, SEARCH_TERMS["price_refresh"])
    v4_hits = repo_search(root, SEARCH_TERMS["v4"])

    con = duckdb.connect(str(db), read_only=True)
    try:
        price_tables = [latest_table_summary(con, t) for t in PRICE_TABLES]
        module42_tables = [latest_table_summary(con, t) for t in MODULE42_TABLES]
        macro_tables = [latest_table_summary(con, t) for t in MACRO_TABLES]
    finally:
        con.close()

    db_hash_after = sha256(db)
    if db_hash_after != db_hash_before:
        raise RuntimeError("Canonical database changed during read-only authority resolution")

    payload = {
        "inspection_id": INSPECTION_ID,
        "inspection_timestamp": datetime.now(TZ).isoformat(),
        "operating_timezone": "America/Chicago",
        "database_read_only": True,
        "canonical_database_modified": False,
        "capture_performed": False,
        "ledger_record_count": 0,
        "missing_evidence_synthesized": False,
        "outcome_peeking_allowed": False,
        "preserved_gap_review_sha256": gap_hash,
        "database_sha256": db_hash_before,
        "repository_search": {
            "price_refresh_hits": price_hits,
            "v4_hits": v4_hits,
        },
        "database_authorities": {
            "price": price_tables,
            "module42": module42_tables,
            "macro": macro_tables,
        },
        "authority_decisions_deferred": True,
        "first_prospective_observation_captured": False,
        "production_policy_changed": False,
        "autonomous_execution_authorized": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    print("BITCOIN_LIVE_INPUT_AUTHORITY_RESOLUTION=PASS")
    print(f"PRICE_REFRESH_REPOSITORY_HITS={len(price_hits)}")
    print(f"V4_REPOSITORY_HITS={len(v4_hits)}")
    print("DATABASE_ACCESS=READ_ONLY")
    print("LEDGER_RECORD_COUNT=0")
    print("FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE")
    print("MISSING_EVIDENCE_SYNTHESIZED=FALSE")
    print("OUTCOME_PEEKING_ALLOWED=FALSE")
    print("CANONICAL_DATABASE_MODIFIED=FALSE")
    print("AUTHORITY_DECISIONS_DEFERRED=TRUE")
    print("NEXT_GATE=REVIEW_BITCOIN_LIVE_INPUT_AUTHORITY_RESOLUTION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
