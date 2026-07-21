import shutil

from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module30 import MODULE30_SCHEMA
from crypto_platform.ml.registry import EXPERIMENT_REGISTRY_SCHEMA


def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    backup = database.with_name(
        database.stem
        + "_before_v8_1_1"
        + database.suffix
    )
    if database.exists() and not backup.exists():
        shutil.copy2(database, backup)
        print(f"Database backup: {backup}")

    conn = connect(settings)
    conn.execute(EXPERIMENT_REGISTRY_SCHEMA)
    conn.execute(MODULE30_SCHEMA)

    # Close any stale RUNNING records left by interrupted runs.
    conn.execute("""
        UPDATE module30_runs
        SET status='FAILED',
            completed_at_utc=COALESCE(
                completed_at_utc,
                CURRENT_TIMESTAMP
            ),
            notes=COALESCE(notes,'')
                || '; Marked failed during v8.1.1 stabilization.'
        WHERE status='RUNNING'
    """)
    conn.execute("""
        UPDATE ml_experiment_registry
        SET status='FAILED',
            completed_at_utc=COALESCE(
                completed_at_utc,
                CURRENT_TIMESTAMP
            ),
            notes=COALESCE(notes,'')
                || '; Marked failed during v8.1.1 stabilization.'
        WHERE status='RUNNING'
          AND module_name='Module 30 Clean Regime Engine'
    """)
    conn.close()

    print("Crypto Intelligence Platform v8.1.1 installed.")
    print("Canonical class ordering is enforced.")
    print("sklearn 1.9 logistic API warnings are corrected.")
    print("Model-disagreement diagnostics are installed.")
    print("Existing v8.1.0 observations remain preserved.")


if __name__ == "__main__":
    main()
