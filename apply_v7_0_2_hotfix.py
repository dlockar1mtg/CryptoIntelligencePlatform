from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "crypto_platform" / "module25.py"
TARGET = ROOT / "crypto_platform" / "module25.py"

def main():
    # This overlay already places the corrected file at the active path.
    # Create a backup only when the previous v7.0.1 file exists beside it
    # during extraction/merge.
    backup = TARGET.with_name("module25_before_v7_0_2_hotfix.py")
    if TARGET.exists() and not backup.exists():
        shutil.copy2(TARGET, backup)
        print(f"Backup created: {backup}")

    print("v7.0.2 Module 25 feature-matrix hotfix is in place.")
    print("The clustering matrix now includes btc_drawdown_180d.")
    print("rule_scores() now tolerates optional missing fields.")
    print("Next command: python run_module25.py")

if __name__ == "__main__":
    main()
