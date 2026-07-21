from datetime import datetime, timezone
from pathlib import Path
import shutil
from crypto_platform.platform import load_all, connect

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"crypto_platform"/"module12.py"
TARGET=ROOT.parent/"crypto_platform"/"module12.py"

def main():
    backup=TARGET.with_name("module12_before_v3_2_1_hotfix.py")
    if not backup.exists():
        shutil.copy2(TARGET,backup)
        print(f"Backup created: {backup}")
    shutil.copy2(SOURCE,TARGET)
    print(f"Patched: {TARGET}")
    settings,_=load_all()
    conn=connect(settings)
    try:
        tables={row[0] for row in conn.execute("SHOW TABLES").fetchall()}
        if "module12_runs" in tables:
            conn.execute(
                """
                UPDATE module12_runs
                SET status='FAILED',completed_at_utc=?,
                    notes=COALESCE(notes,'') ||
                    CASE WHEN COALESCE(notes,'')='' THEN '' ELSE '; ' END ||
                    'Marked failed by v3.2.1 hotfix.'
                WHERE status='RUNNING'
                """,
                [datetime.now(timezone.utc)]
            )
            print("Stale Module 12 RUNNING rows marked FAILED.")
    finally:
        conn.close()
    print("v3.2.1 hotfix applied successfully.")
    print("Next command: python run_module12.py")

if __name__=="__main__":
    main()
