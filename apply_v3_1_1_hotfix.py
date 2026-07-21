from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil

from crypto_platform.platform import load_all, connect

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "crypto_platform" / "module11.py"
TARGET = ROOT.parent / "crypto_platform" / "module11.py"

def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(f"Could not locate target file: {TARGET}")

    backup = TARGET.with_name("module11_before_v3_1_1_hotfix.py")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
        print(f"Backup created: {backup}")
    else:
        print(f"Backup already exists: {backup}")

    shutil.copy2(SOURCE, TARGET)
    print(f"Patched: {TARGET}")

    settings, _ = load_all()
    conn = connect(settings)
    try:
        tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
        if "module11_runs" in tables:
            result = conn.execute(
                """
                UPDATE module11_runs
                SET status='FAILED',
                    completed_at_utc=?,
                    notes=COALESCE(notes, '') ||
                          CASE WHEN COALESCE(notes, '')='' THEN '' ELSE '; ' END ||
                          'Marked failed by v3.1.1 hotfix after interrupted run.'
                WHERE status='RUNNING'
                """,
                [datetime.now(timezone.utc)],
            )
            print("Stale Module 11 RUNNING rows marked FAILED.")
    finally:
        conn.close()

    print("v3.1.1 hotfix applied successfully.")
    print("Next command: python run_module11.py")

if __name__ == "__main__":
    main()
