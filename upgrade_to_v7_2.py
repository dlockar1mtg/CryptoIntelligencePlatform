import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module27 import MODULE27_SCHEMA

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    backup = database.with_name(
        database.stem + "_before_v7_2" + database.suffix
    )
    if database.exists() and not backup.exists():
        shutil.copy2(database, backup)
        print(f"Database backup: {backup}")
    conn = connect(settings)
    conn.execute(MODULE27_SCHEMA)
    conn.close()
    print("Crypto Intelligence Platform v7.2 installed.")
    print("Module 27 Regime Representation & Optimization is ready.")
    print("Modules 25 and 26 remain unchanged.")

if __name__ == "__main__":
    main()
