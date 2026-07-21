import shutil

from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module38 import MODULE38_SCHEMA


def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    backup = database.with_name(
        database.stem
        + "_before_v10_0_1"
        + database.suffix
    )

    if database.exists() and not backup.exists():
        shutil.copy2(database, backup)
        print(f"Database backup: {backup}")

    conn = connect(settings)
    conn.execute(MODULE38_SCHEMA)
    conn.execute(
        """
        UPDATE module38_runs
        SET status='FAILED',
            completed_at_utc=COALESCE(
                completed_at_utc,
                CURRENT_TIMESTAMP
            ),
            notes=COALESCE(notes,'')
                || '; Closed during v10.0.1 adaptive-history hotfix.'
        WHERE status='RUNNING'
        """
    )
    conn.close()

    print("Crypto Intelligence Platform v10.0.1 installed.")
    print("Module 38 now uses adaptive training and validation windows.")
    print("Live forecasts now use the latest available feature row.")
    print("Modules 25-37 and existing data remain unchanged.")


if __name__ == "__main__":
    main()
