from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "preflight_predictive_horizon_recovery_v4_development.py"

OLD_HASH = "dc0d37dcb932cf39e9b5affb19d578d7b57e4db457bd39b5233005f5a57a0de0"
NEW_HASH = "510d121e1e4e8ea7e2079b1f61883b2ca01dfb6ce2c6baf6b9ba601eadeafd42"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    require(count == 1, f"Expected exactly one {label} replacement target, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    require(TARGET.is_file(), f"Missing target preflight: {TARGET}")
    original = TARGET.read_text(encoding="utf-8")
    text = original

    text = replace_once(
        text,
        f'EXPECTED_V4_MANIFEST_CONTENT_SHA256 = "{OLD_HASH}"',
        f'EXPECTED_V4_MANIFEST_CONTENT_SHA256 = "{NEW_HASH}"',
        "V4 manifest content hash",
    )

    text = replace_once(
        text,
        "EXPECTED_FINAL_HOLDOUT_ORIGINS = 10\n",
        "EXPECTED_FINAL_HOLDOUT_ORIGINS = 10\nEXPECTED_AVALANCHE365_FINAL_HOLDOUT_ORIGINS = 9\n",
        "Avalanche365 holdout constant insertion",
    )

    old_manifest_guards = '''    require(v4.get("v3_final_holdout_reused") is False, "V3 final holdout was reused by V4")\n    require(v4.get("manifest_content_sha256") == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "Unexpected V4 manifest content hash")\n'''
    new_manifest_guards = '''    require(v4.get("v3_final_holdout_reused") is False, "V3 final holdout was reused by V4")\n    require(int(v4.get("manifest_revision", 0)) == 2, "Unexpected corrected V4 manifest revision")\n    require(v4.get("exact_calendar_target_availability_required") is True, "Corrected V4 manifest does not require exact calendar targets")\n    require(v4.get("strict_final_holdout_after_development_required") is True, "Corrected V4 manifest does not enforce strict final-holdout chronology")\n    require(v4.get("holdout_outcome_values_read_during_rebuild") is False, "V4 holdout outcome values were read during corrected rebuild")\n    require(v4.get("holdout_outcome_signs_read_during_rebuild") is False, "V4 holdout outcome signs were read during corrected rebuild")\n    require(v4.get("holdout_outcome_magnitudes_read_during_rebuild") is False, "V4 holdout outcome magnitudes were read during corrected rebuild")\n    require(int(v4.get("avalanche365_final_holdout_origins", 0)) == EXPECTED_AVALANCHE365_FINAL_HOLDOUT_ORIGINS, "Unexpected Avalanche365 governed holdout count")\n    require(v4.get("avalanche365_exception_governed") is True, "Avalanche365 holdout exception is not governed")\n    require(v4.get("manifest_content_sha256") == EXPECTED_V4_MANIFEST_CONTENT_SHA256, "Unexpected V4 manifest content hash")\n'''
    text = replace_once(text, old_manifest_guards, new_manifest_guards, "corrected manifest guards")

    old_group_check = '''                require(len(dev_dates) == EXPECTED_DEVELOPMENT_ORIGINS, f"Unexpected V4 development-origin count for {asset} {horizon}d")\n                require(len(holdout_dates) == EXPECTED_FINAL_HOLDOUT_ORIGINS, f"Unexpected V4 holdout-origin count for {asset} {horizon}d")\n'''
    new_group_check = '''                expected_holdout_origins = (\n                    EXPECTED_AVALANCHE365_FINAL_HOLDOUT_ORIGINS\n                    if asset == "avalanche" and horizon == 365\n                    else EXPECTED_FINAL_HOLDOUT_ORIGINS\n                )\n                require(len(dev_dates) == EXPECTED_DEVELOPMENT_ORIGINS, f"Unexpected V4 development-origin count for {asset} {horizon}d")\n                require(len(holdout_dates) == expected_holdout_origins, f"Unexpected V4 holdout-origin count for {asset} {horizon}d")\n                require(int(group.get("development_origin_count", len(dev_dates))) == EXPECTED_DEVELOPMENT_ORIGINS, f"Manifest development-origin metadata mismatch for {asset} {horizon}d")\n                require(int(group.get("final_holdout_origin_count", len(holdout_dates))) == expected_holdout_origins, f"Manifest holdout-origin metadata mismatch for {asset} {horizon}d")\n'''
    text = replace_once(text, old_group_check, new_group_check, "per-group governed holdout check")

    require(text != original, "No preflight changes were produced")
    TARGET.write_text(text, encoding="utf-8", newline="")

    print("CRYPTO_V4_CORRECTED_MEMBERSHIP_PREFLIGHT_CONTRACT_PATCH=PASS")
    print(f"TARGET={TARGET.relative_to(ROOT).as_posix()}")
    print(f"EXPECTED_V4_MANIFEST_CONTENT_SHA256={NEW_HASH}")
    print("EXPECTED_STANDARD_FINAL_HOLDOUT_ORIGINS=10")
    print("EXPECTED_AVALANCHE365_FINAL_HOLDOUT_ORIGINS=9")
    print("EXACT_CALENDAR_TARGET_AVAILABILITY_REQUIRED=TRUE")
    print("STRICT_FINAL_HOLDOUT_AFTER_DEVELOPMENT_REQUIRED=TRUE")
    print("HOLDOUT_OUTCOME_VALUES_READ_DURING_REBUILD=FALSE")
    print("NEXT_GATE=COMPILE_COMMIT_AND_RERUN_V4_DEVELOPMENT_PREFLIGHT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
