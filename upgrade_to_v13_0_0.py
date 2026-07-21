import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module44 import MODULE44_SCHEMA


def main():
    s, _ = load_all()
    db = path_for(s, "database_path")
    backup = db.with_name(db.stem + "_before_v13_0_0" + db.suffix)
    if db.exists() and not backup.exists():
        shutil.copy2(db, backup)
        print(f"Database backup: {backup}")
    c = connect(s)
    c.execute(MODULE44_SCHEMA)
    c.close()
    print("Crypto Intelligence Platform v13.0.0 installed.")
    print("Module 44 Economic Value & Strategy Validation is ready.")
    print("Modules 38-43 and all existing forecast memory remain unchanged.")


if __name__ == "__main__":
    main()
