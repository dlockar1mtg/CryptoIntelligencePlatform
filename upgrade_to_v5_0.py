import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module21 import MODULE21_SCHEMA

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    backup = database.with_name(
        database.stem + "_before_v5_0" + database.suffix
    )
    if database.exists() and not backup.exists():
        shutil.copy2(database, backup)
        print(f"Database backup: {backup}")

    conn = connect(settings)
    conn.execute(MODULE21_SCHEMA)
    conn.close()

    print("Crypto Intelligence Platform v5.0 installed.")
    print("Investment Decision Engine is ready for shadow evaluation.")
    print("Module 13 live allocations remain unchanged.")

if __name__ == "__main__":
    main()
