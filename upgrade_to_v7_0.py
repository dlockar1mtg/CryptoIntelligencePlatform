import shutil
from datetime import datetime
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module25 import MODULE25_SCHEMA

PHYSICAL_TABLES = [
    "m25_regime_features",
    "m25_regime_probabilities",
    "m25_regime_daily",
    "m25_regime_transitions",
    "m25_regime_durations",
    "m25_regime_validation",
    "m25_regime_contributions",
]

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    backup = database.with_name(
        database.stem + "_before_v7_0_1_hotfix" + database.suffix
    )
    if database.exists() and not backup.exists():
        shutil.copy2(database, backup)
        print(f"Database backup: {backup}")

    conn = connect(settings)

    # Clean up only partially created v7.0 views. Legacy physical tables from
    # older modules are deliberately preserved.
    for view_name in [
        "latest_market_regime_features",
        "latest_market_regime_probabilities",
        "latest_market_regime_daily",
        "latest_market_regime_transitions",
        "latest_market_regime_durations",
        "latest_market_regime_validation",
        "latest_market_regime_contributions",
    ]:
        conn.execute(f"DROP VIEW IF EXISTS {view_name}")

    conn.execute(MODULE25_SCHEMA)

    created = []
    for table_name in PHYSICAL_TABLES:
        exists = conn.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE lower(table_name)=lower(?)
            """,
            [table_name],
        ).fetchone()[0]
        if exists:
            created.append(table_name)

    conn.close()

    if len(created) != len(PHYSICAL_TABLES):
        missing = sorted(set(PHYSICAL_TABLES) - set(created))
        raise RuntimeError(f"Module 25 schema incomplete. Missing: {missing}")

    print("Crypto Intelligence Platform v7.0.1 hotfix installed.")
    print("Module 25 now uses collision-safe m25_* physical tables.")
    print("Older regime tables from Modules 21-24 were preserved.")
    print("Next command: python run_module25.py")

if __name__ == "__main__":
    main()
