from datetime import datetime, timezone
from pathlib import Path
import shutil
from crypto_platform.platform import load_all, connect

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"crypto_platform"/"module13.py"
TARGET=ROOT/"crypto_platform"/"module13.py"

def main():
    if not TARGET.exists():
        raise FileNotFoundError(f"Missing target: {TARGET}")
    backup=TARGET.with_name("module13_before_v3_3_2_hotfix.py")
    if not backup.exists():
        shutil.copy2(TARGET,backup)
        print(f"Backup created: {backup}")
    shutil.copy2(SOURCE,TARGET)
    print(f"Patched: {TARGET}")

    settings,_=load_all()
    conn=connect(settings)
    try:
        tables={row[0] for row in conn.execute("SHOW TABLES").fetchall()}
        if "module13_runs" in tables:
            conn.execute("""
                UPDATE module13_runs
                SET status='FAILED',completed_at_utc=?,
                    notes=COALESCE(notes,'') ||
                          CASE WHEN COALESCE(notes,'')='' THEN '' ELSE '; ' END ||
                          'Marked failed by v3.3.2 hotfix.'
                WHERE status='RUNNING'
                   OR (status='SUCCESS' AND assets_analyzed=0)
            """,[datetime.now(timezone.utc)])
        for table_name in ("research_market_daily","canonical_market_daily"):
            if table_name in tables:
                count=conn.execute(
                    f"SELECT COUNT(*) FROM {table_name}"
                ).fetchone()[0]
                columns=[
                    row[1] for row in conn.execute(
                        f"PRAGMA table_info('{table_name}')"
                    ).fetchall()
                ]
                print(f"{table_name}: {count} rows")
                print(f"{table_name} columns: {', '.join(columns)}")
            else:
                print(f"{table_name}: table not present")
    finally:
        conn.close()
    print("v3.3.2 hotfix applied successfully.")
    print("Next command: python run_module13.py")

if __name__=="__main__":
    main()
