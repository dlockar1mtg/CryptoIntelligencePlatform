import shutil
from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module17 import MODULE17_SCHEMA

def main():
    s, _ = load_all()
    db = path_for(s, "database_path")
    if db.exists():
        backup = db.with_name(db.stem + "_before_v4_2" + db.suffix)
        if not backup.exists():
            shutil.copy2(db, backup)
            print(f"Database backup: {backup}")
    c = connect(s)
    c.execute(MODULE17_SCHEMA)
    c.close()
    print("Crypto Intelligence Platform v4.2 installed.")
    print("Feature warehouse and predictive validation are ready.")
    print("No live scoring or portfolio methodology was changed.")

if __name__ == "__main__":
    main()
