from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent

def load_database_path() -> Path:
    settings_path = PROJECT_ROOT / "config" / "settings.yaml"
    if not settings_path.exists():
        raise FileNotFoundError(f"Missing settings file: {settings_path}")
    settings = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    value = settings["platform"]["database_path"]
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()

def safe_count(conn: duckdb.DuckDBPyConnection, table: str) -> int:
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except Exception:
        return -1

def inspect_database(path: Path) -> dict:
    result = {
        "path": path,
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "research_market_daily": -1,
        "canonical_market_daily": -1,
        "asset_ohlcv": -1,
        "asset_market_daily": -1,
        "research_universe": -1,
        "latest_date": None,
        "error": None,
    }
    try:
        conn = duckdb.connect(str(path), read_only=True)
        try:
            tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
            for table in [
                "research_market_daily",
                "canonical_market_daily",
                "asset_ohlcv",
                "asset_market_daily",
                "research_universe",
            ]:
                if table in tables:
                    result[table] = safe_count(conn, table)
            for table in [
                "research_market_daily",
                "canonical_market_daily",
                "asset_market_daily",
            ]:
                if result[table] > 0:
                    try:
                        date_value = conn.execute(
                            f"SELECT MAX(observation_date) FROM {table}"
                        ).fetchone()[0]
                        if date_value is not None:
                            result["latest_date"] = str(date_value)
                            break
                    except Exception:
                        pass
        finally:
            conn.close()
    except Exception as exc:
        result["error"] = str(exc)
    return result

def score(item: dict) -> tuple:
    research = max(0, item["research_market_daily"])
    canonical = max(0, item["canonical_market_daily"])
    raw = max(0, item["asset_ohlcv"]) + max(0, item["asset_market_daily"])
    universe = max(0, item["research_universe"])
    return (
        research + canonical,
        research,
        canonical,
        raw,
        universe,
        item["size_bytes"],
    )

def print_report(items: list[dict], active: Path) -> None:
    print("\nCrypto DuckDB Recovery Report")
    print("=============================")
    print(f"Configured active database: {active}\n")
    header = (
        "Candidate",
        "Research",
        "Canonical",
        "OHLCV",
        "Market",
        "Universe",
        "Size MB",
        "Latest",
    )
    print(
        f"{header[0]:<48} {header[1]:>10} {header[2]:>10} "
        f"{header[3]:>10} {header[4]:>10} {header[5]:>9} "
        f"{header[6]:>9} {header[7]:>12}"
    )
    print("-" * 130)
    for item in sorted(items, key=score, reverse=True):
        marker = "*" if item["path"].resolve() == active.resolve() else " "
        print(
            f"{marker}{item['path'].name:<47} "
            f"{item['research_market_daily']:>10} "
            f"{item['canonical_market_daily']:>10} "
            f"{item['asset_ohlcv']:>10} "
            f"{item['asset_market_daily']:>10} "
            f"{item['research_universe']:>9} "
            f"{item['size_bytes']/1024/1024:>9.1f} "
            f"{str(item['latest_date'] or ''):>12}"
        )
        if item["error"]:
            print(f"  ERROR: {item['error']}")

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect and optionally restore the strongest Crypto DuckDB backup."
    )
    parser.add_argument(
        "--restore-best",
        action="store_true",
        help="Restore the candidate with the most historical warehouse rows.",
    )
    args = parser.parse_args()

    active = load_database_path()
    data_dir = active.parent
    candidates = sorted(data_dir.glob("*.duckdb"))
    if active not in candidates and active.exists():
        candidates.append(active)
    if not candidates:
        raise RuntimeError(f"No DuckDB files found in {data_dir}")

    items = [inspect_database(path) for path in candidates]
    print_report(items, active)

    valid = [
        item for item in items
        if item["error"] is None
        and item["path"].resolve() != active.resolve()
    ]
    if not valid:
        print("\nNo usable backup database was found.")
        return

    best = max(valid, key=score)
    best_history = (
        max(0, best["research_market_daily"])
        + max(0, best["canonical_market_daily"])
    )
    active_item = next(
        (item for item in items if item["path"].resolve() == active.resolve()),
        None,
    )
    active_history = (
        max(0, active_item["research_market_daily"])
        + max(0, active_item["canonical_market_daily"])
        if active_item else 0
    )

    print(f"\nBest backup candidate: {best['path'].name}")
    print(f"Historical warehouse rows: {best_history:,}")
    print(f"Active historical warehouse rows: {active_history:,}")

    if not args.restore_best:
        print("\nReview the report above.")
        print("To restore the best candidate, run:")
        print("    python recover_crypto_database.py --restore-best")
        return

    if best_history <= active_history:
        print("\nRestore skipped: no backup has more historical warehouse rows than the active database.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safety_backup = active.with_name(
        f"{active.stem}_before_recovery_{timestamp}{active.suffix}"
    )
    if active.exists():
        shutil.copy2(active, safety_backup)
        print(f"\nCurrent database safety backup: {safety_backup}")

    shutil.copy2(best["path"], active)
    print(f"Restored {best['path'].name} -> {active.name}")

    restored = inspect_database(active)
    print(
        "Restored row counts: "
        f"research={restored['research_market_daily']:,}, "
        f"canonical={restored['canonical_market_daily']:,}, "
        f"asset_ohlcv={restored['asset_ohlcv']:,}, "
        f"asset_market_daily={restored['asset_market_daily']:,}"
    )
    print("\nNext commands:")
    print("    python upgrade_to_v3_3.py")
    print("    python run_module13.py")
    print("    python inspect_module13.py")

if __name__ == "__main__":
    main()
