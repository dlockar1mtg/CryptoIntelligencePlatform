from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "scripts" / "preflight_predictive_horizon_recovery_v4_development.py"

OLD = 'EXPECTED_V4_MANIFEST_CONTENT_SHA256 = "4b42d66a6cea1949b956fc5fe57545cb21abfe6b8cdddb0fe7f933b75734ca02"'
NEW = 'EXPECTED_V4_MANIFEST_CONTENT_SHA256 = "dc0d37dcb932cf39e9b5affb19d578d7b57e4db457bd39b5233005f5a57a0de0"'


def main() -> int:
    text = PREFLIGHT.read_text(encoding="utf-8")
    if text.count(OLD) != 1:
        raise RuntimeError("Expected exactly one old V4 manifest content-hash constant in preflight.")
    if NEW in text:
        raise RuntimeError("Corrected V4 manifest content hash is already present.")
    updated = text.replace(OLD, NEW, 1)
    PREFLIGHT.write_text(updated, encoding="utf-8", newline="")
    verify = PREFLIGHT.read_text(encoding="utf-8")
    if verify.count(NEW) != 1 or OLD in verify:
        raise RuntimeError("V4 preflight manifest-hash update verification failed.")
    print("CRYPTO_V4_PREFLIGHT_CORRECTED_MANIFEST_HASH_UPDATE=PASS")
    print("OLD_MANIFEST_CONTENT_SHA256=4b42d66a6cea1949b956fc5fe57545cb21abfe6b8cdddb0fe7f933b75734ca02")
    print("NEW_MANIFEST_CONTENT_SHA256=dc0d37dcb932cf39e9b5affb19d578d7b57e4db457bd39b5233005f5a57a0de0")
    print("NEXT_GATE=COMMIT_HASH_UPDATE_AND_RERUN_FULL_V4_PREFLIGHT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
