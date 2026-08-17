from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "run_v2_native_context_holdout_evaluation.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    require("import shutil" in text and "import tempfile" in text, "Disposable DB imports missing")
    require('with tempfile.TemporaryDirectory(prefix="crypto_v2_holdout_") as tmp:' in text, "Temporary directory missing")
    require("shutil.copy2(source, temp_db)" in text, "Source database is not copied before evaluation")
    require('os.environ["CRYPTO_DATABASE_PATH"] = str(temp_db)' in text, "Evaluator is not redirected to disposable database")
    require('os.environ["CRYPTO_DATABASE_PATH"] = str(source)' not in text, "Evaluator still redirects connection to source database")
    require('require(sha256(source) == before_db, "Source database changed during V2 holdout evaluation")' in text, "Source DB immutability check missing")
    require('require(sha256(manifest_path) == before_manifest, "Frozen V2 manifest changed during evaluation")' in text, "Manifest immutability check missing")
    print("CRYPTO_V2_EVALUATOR_DISPOSABLE_DATABASE_SOURCE_VALIDATION=PASS")
    print("SOURCE_DATABASE_CONNECTION_TARGET=DISPOSABLE_COPY")
    print("SOURCE_DATABASE_IMMUTABILITY_CHECK=TRUE")
    print("FROZEN_MANIFEST_IMMUTABILITY_CHECK=TRUE")
    print("NEXT_GATE=RERUN_FROZEN_V2_NATIVE_CONTEXT_HOLDOUT_EVALUATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
