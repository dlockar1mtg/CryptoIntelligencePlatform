import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    if database.exists():
        backup = database.with_name(
            database.stem + "_before_v1_3" + database.suffix
        )
        if not backup.exists():
            shutil.copy2(database, backup)
            print(f"Database backup: {backup}")
        else:
            print(f"Backup already exists: {backup}")

    conn = connect(settings)
    conn.execute(MODULE2_SCHEMA)
    conn.execute(MODULE3_SCHEMA)
    conn.execute("DELETE FROM asset_signals_daily")
    conn.execute("DELETE FROM score_components")
    conn.close()

    print("Crypto Intelligence Platform v1.3 installed.")
    print("Module 1 observations were preserved.")
    print("Module 2 signals will be recalculated with confidence v2.2.")
    print("Module 3 portfolio, risk, correlation, DCA, and scenario tables were created.")

if __name__ == "__main__":
    main()
