import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module22 import MODULE22_SCHEMA

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    backup = database.with_name(
        database.stem + "_before_v5_1" + database.suffix
    )
    if database.exists() and not backup.exists():
        shutil.copy2(database, backup)
        print(f"Database backup: {backup}")
    conn = connect(settings)
    conn.execute(MODULE22_SCHEMA)
    conn.close()
    print("Crypto Intelligence Platform v5.1 installed.")
    print("Intelligence expansion and six-asset shadow allocation are ready.")
    print("Module 13 live recommendations remain unchanged.")

if __name__ == "__main__":
    main()
