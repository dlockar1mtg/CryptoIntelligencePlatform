from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REBUILD = ROOT / "scripts" / "rebuild_v4_membership_with_avalanche365_exception.py"
VALIDATOR = ROOT / "scripts" / "validate_v4_corrected_membership_manifest.py"

OLD_CONTENT_SHA256 = "dc0d37dcb932cf39e9b5affb19d578d7b57e4db457bd39b5233005f5a57a0de0"
OLD_FILE_SHA256 = "dcaf32dccb8ab1031f7a6bea884e676deb0732466dc73a499d75e7d792f61b57"


def replace_exact(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label}; found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    rebuild = REBUILD.read_text(encoding="utf-8")
    validator = VALIDATOR.read_text(encoding="utf-8")

    rebuild = replace_exact(
        rebuild,
        f'EXPECTED_SUPERSEDED_V4_FILE_SHA256 = "{OLD_FILE_SHA256}"',
        f'EXPECTED_SUPERSEDED_V4_CONTENT_SHA256 = "{OLD_CONTENT_SHA256}"',
        "rebuild superseded hash constant",
    )
    rebuild = replace_exact(
        rebuild,
        '    require(sha256(paths["superseded_v4"]) == EXPECTED_SUPERSEDED_V4_FILE_SHA256, "Unexpected superseded V4 manifest hash")\n',
        "",
        "rebuild physical-file hash gate",
    )
    rebuild = replace_exact(
        rebuild,
        '    old_v4 = json.loads(paths["superseded_v4"].read_text(encoding="utf-8"))\n',
        '    old_v4 = json.loads(paths["superseded_v4"].read_text(encoding="utf-8"))\n'
        '    require(old_v4.get("manifest_content_sha256") == EXPECTED_SUPERSEDED_V4_CONTENT_SHA256, "Unexpected superseded V4 manifest content hash")\n'
        '    require(canonical_hash(old_v4) == EXPECTED_SUPERSEDED_V4_CONTENT_SHA256, "Superseded V4 manifest canonical content hash mismatch")\n'
        '    require(old_v4.get("membership_rule_generation") == "EXACT_CALENDAR_TARGET_AVAILABILITY_V2", "Unexpected superseded V4 membership generation")\n',
        "rebuild old-manifest load",
    )
    rebuild = replace_exact(
        rebuild,
        '        "supersedes_manifest_file_sha256": EXPECTED_SUPERSEDED_V4_FILE_SHA256,',
        '        "supersedes_manifest_content_sha256": EXPECTED_SUPERSEDED_V4_CONTENT_SHA256,',
        "rebuild supersession payload field",
    )

    validator = replace_exact(
        validator,
        f'EXPECTED_SUPERSEDED_FILE_SHA256 = "{OLD_FILE_SHA256}"',
        f'EXPECTED_SUPERSEDED_CONTENT_SHA256 = "{OLD_CONTENT_SHA256}"',
        "validator superseded hash constant",
    )
    validator = replace_exact(
        validator,
        '    require(payload.get("supersedes_manifest_file_sha256") == EXPECTED_SUPERSEDED_FILE_SHA256, "Unexpected superseded manifest hash")',
        '    require(payload.get("supersedes_manifest_content_sha256") == EXPECTED_SUPERSEDED_CONTENT_SHA256, "Unexpected superseded manifest content hash")',
        "validator supersession field gate",
    )

    REBUILD.write_text(rebuild, encoding="utf-8", newline="")
    VALIDATOR.write_text(validator, encoding="utf-8", newline="")

    rebuild_verify = REBUILD.read_text(encoding="utf-8")
    validator_verify = VALIDATOR.read_text(encoding="utf-8")
    if OLD_FILE_SHA256 in rebuild_verify or OLD_FILE_SHA256 in validator_verify:
        raise RuntimeError("Obsolete physical-file supersession hash remains after patch")
    if rebuild_verify.count(OLD_CONTENT_SHA256) != 1:
        raise RuntimeError("Corrected rebuild content-hash constant count is not one")
    if validator_verify.count(OLD_CONTENT_SHA256) != 1:
        raise RuntimeError("Corrected validator content-hash constant count is not one")
    if "supersedes_manifest_file_sha256" in rebuild_verify or "supersedes_manifest_file_sha256" in validator_verify:
        raise RuntimeError("Obsolete supersedes_manifest_file_sha256 field remains")
    if "supersedes_manifest_content_sha256" not in rebuild_verify or "supersedes_manifest_content_sha256" not in validator_verify:
        raise RuntimeError("Content-based supersession field missing after patch")

    print("CRYPTO_V4_AVALANCHE365_SUPERSESSION_CONTRACT_FIX=PASS")
    print(f"SUPERSEDED_MANIFEST_CONTENT_SHA256={OLD_CONTENT_SHA256}")
    print("PHYSICAL_FILE_HASH_DEPENDENCY_REMOVED=TRUE")
    print("EXACT_TARGET_CORRECTED_GENERATION_REQUIRED=TRUE")
    print("NEXT_GATE=COMMIT_SUPERSESSION_CONTRACT_FIX_AND_RERUN_CORRECTED_MEMBERSHIP_REBUILD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
