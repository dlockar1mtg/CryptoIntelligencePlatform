from pathlib import Path
import shutil
from crypto_platform.platform import load_all, connect, path_for

def main():
    settings, _ = load_all()
    database = path_for(settings, "database_path")
    if database.exists():
        backup = database.with_name(database.stem + "_before_v1_1" + database.suffix)
        if not backup.exists():
            shutil.copy2(database, backup)
            print(f"Database backup: {backup}")
        else:
            print(f"Backup already exists: {backup}")
    conn = connect(settings)
    conn.close()
    print("v1.1 schema and views installed.")
    print("Existing v1.0 data was preserved.")

if __name__ == "__main__":
    main()
