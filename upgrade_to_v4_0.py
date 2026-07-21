import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module15 import MODULE15_SCHEMA

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    if database.exists():
        backup = database.with_name(
            database.stem + "_before_v4_0" + database.suffix
        )
        if not backup.exists():
            shutil.copy2(database, backup)
            print(f"Database backup: {backup}")
        else:
            print(f"Backup already exists: {backup}")

    conn = connect(settings)
    conn.execute(MODULE15_SCHEMA)
    conn.close()

    print("Crypto Intelligence Platform v4.0 installed.")
    print("Five strategy variants and walk-forward calibration are ready.")
    print("No live methodology has been changed automatically.")

if __name__ == "__main__":
    main()
