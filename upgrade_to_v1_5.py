import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    if database.exists():
        backup = database.with_name(
            database.stem + "_before_v1_5" + database.suffix
        )
        if not backup.exists():
            shutil.copy2(database, backup)
            print(f"Database backup: {backup}")
        else:
            print(f"Backup already exists: {backup}")

    conn = connect(settings)
    conn.execute(MODULE2_SCHEMA)
    conn.execute(MODULE3_SCHEMA)
    conn.execute(MODULE5_SCHEMA)
    conn.execute("DELETE FROM multi_horizon_returns")
    conn.execute("DELETE FROM cycle_analytics")
    conn.execute("DELETE FROM expected_returns")
    conn.execute("DELETE FROM optimized_allocations")
    conn.close()

    print("Crypto Intelligence Platform v1.5 installed.")
    print("Modules 1-3 data were preserved.")
    print("Module 5 analytics were initialized.")

if __name__ == "__main__":
    main()
