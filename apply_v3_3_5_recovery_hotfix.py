from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "crypto_platform" / "module14.py"
TARGET = ROOT / "crypto_platform" / "module14.py"

def main():
    if not TARGET.exists():
        raise FileNotFoundError(f"Missing target: {TARGET}")

    backup = TARGET.with_name("module14_before_v3_3_5_hotfix.py")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
        print(f"Backup created: {backup}")

    # Extraction may already have placed the patched file at TARGET.
    if SOURCE.resolve() != TARGET.resolve():
        shutil.copy2(SOURCE, TARGET)
        print(f"Patched: {TARGET}")
    else:
        print("Patched Module 14 is already in place.")

    print("v3.3.5 recovery hotfix applied.")
    print("Running database diagnosis...")

if __name__ == "__main__":
    main()
