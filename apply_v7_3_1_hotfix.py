from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "crypto_platform" / "module28.py"
BACKUP = ROOT / "crypto_platform" / "module28_before_v7_3_1_hotfix.py"

REMOVED_SKLEARN_ARGUMENTS = [
    r"\bmulti_class\s*=",
    r"\bnormalize\s*=",
    r"\bbase_estimator\s*=",
    r"\baffinity\s*=",
]


def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(f"Missing Module 28 target: {TARGET}")

    if not BACKUP.exists():
        shutil.copy2(TARGET, BACKUP)
        print(f"Backup created: {BACKUP}")

    text = TARGET.read_text(encoding="utf-8")
    original = text

    # scikit-learn 1.9 removed LogisticRegression(multi_class=...).
    text, replacements = re.subn(
        r"\n\s*multi_class\s*=\s*[\"']auto[\"']\s*,?",
        "",
        text,
    )

    if replacements == 0 and "multi_class=" in original:
        raise RuntimeError(
            "Module 28 contains multi_class but the compatibility patch "
            "could not safely remove it."
        )

    TARGET.write_text(text, encoding="utf-8")

    remaining = []
    patched = TARGET.read_text(encoding="utf-8")
    for pattern in REMOVED_SKLEARN_ARGUMENTS:
        if re.search(pattern, patched):
            remaining.append(pattern)
    if remaining:
        raise RuntimeError(
            "Unsupported sklearn arguments remain in Module 28: "
            + ", ".join(remaining)
        )

    compile_result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(TARGET)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if compile_result.returncode != 0:
        raise RuntimeError(
            "Module 28 compilation failed:\n"
            + compile_result.stdout
            + compile_result.stderr
        )

    compatibility_result = subprocess.run(
        [sys.executable, "test_v7_3_1_sklearn_compatibility.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    print(compatibility_result.stdout, end="")
    if compatibility_result.returncode != 0:
        raise RuntimeError(
            "v7.3.1 compatibility test failed:\n"
            + compatibility_result.stderr
        )

    print("Crypto Intelligence Platform v7.3.1 hotfix applied successfully.")
    print(f"Removed obsolete sklearn arguments: {replacements}")
    print("Next command: python run_module28.py")


if __name__ == "__main__":
    main()
