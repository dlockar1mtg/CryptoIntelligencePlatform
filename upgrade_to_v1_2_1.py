import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    if database.exists():
        backup = database.with_name(
            database.stem + "_before_v1_2_1" + database.suffix
        )
        if not backup.exists():
            shutil.copy2(database, backup)
            print(f"Database backup: {backup}")
        else:
            print(f"Backup already exists: {backup}")

    conn = connect(settings)
    conn.execute(MODULE2_SCHEMA)
    # Recalculate regimes and signals under v2.1 definitions on next run.
    conn.execute("DELETE FROM market_regime_daily")
    conn.execute("DELETE FROM asset_signals_daily")
    conn.execute("DELETE FROM score_components")
    conn.close()

    print("Crypto Intelligence Platform v1.2.1 installed.")
    print("Module 1 observations and macro data were preserved.")
    print("Prior Module 2 signals were cleared for clean v2.1 recalculation.")
    print("Market regime now uses tracked-universe history.")
    print("Confidence now includes data depth, liquidity, freshness, and provider agreement.")

if __name__ == "__main__":
    main()
