import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module14 import MODULE14_SCHEMA

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    if database.exists():
        backup = database.with_name(
            database.stem + "_before_v3_3_4" + database.suffix
        )
        if not backup.exists():
            shutil.copy2(database, backup)
            print(f"Database backup: {backup}")
        else:
            print(f"Backup already exists: {backup}")

    conn = connect(settings)
    conn.execute(MODULE14_SCHEMA)
    conn.close()

    print("Crypto Intelligence Platform v3.3.4 installed.")
    print("The inspection filter is corrected for XRP and Avalanche.")
    print("Historical scoring and portfolio validation are ready.")

if __name__ == "__main__":
    main()
