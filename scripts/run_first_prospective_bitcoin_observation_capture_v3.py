from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def relative(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--records-dir", required=True)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--v4-operationalization", required=True)
    parser.add_argument("--macro-evidence", required=True)
    parser.add_argument("--v2-result", required=True)
    parser.add_argument("--extended-history", required=True)
    parser.add_argument("--capture", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    database = Path(args.database).resolve()
    manifest = Path(args.manifest).resolve()
    records_dir = Path(args.records_dir).resolve()
    authorization = Path(args.authorization).resolve()
    v4 = Path(args.v4_operationalization).resolve()
    macro = Path(args.macro_evidence).resolve()
    v2_result = Path(args.v2_result).resolve()
    extended_history = Path(args.extended_history).resolve()
    v2_runner = repo_root / "scripts" / "run_first_prospective_bitcoin_observation_capture_v2.py"

    for name, path in {
        "repo_root": repo_root,
        "database": database,
        "manifest": manifest,
        "authorization": authorization,
        "v4_operationalization": v4,
        "macro_evidence": macro,
        "v2_result": v2_result,
        "extended_history": extended_history,
        "v2_runner": v2_runner,
    }.items():
        require(path.exists(), f"Required input missing: {name}={path}")

    manifest_obj = json.loads(manifest.read_text(encoding="utf-8"))
    require(int(manifest_obj.get("record_count", -1)) == 0, "First capture requires manifest record_count=0")
    existing_records = sorted(records_dir.rglob("*.json")) if records_dir.exists() else []
    require(len(existing_records) == 0, "First capture requires no existing observation records")

    database_hash_before = sha256(database)
    manifest_hash_before = sha256(manifest)

    with tempfile.TemporaryDirectory(prefix="btc_first_observation_v3_") as temp_dir_text:
        temp_dir = Path(temp_dir_text)
        temp_manifest = temp_dir / "manifest.json"
        temp_records = temp_dir / "records"
        shutil.copy2(manifest, temp_manifest)

        command = [
            sys.executable,
            str(v2_runner),
            "--database", str(database),
            "--manifest", str(temp_manifest),
            "--records-dir", str(temp_records),
            "--authorization", str(authorization),
            "--v4-operationalization", str(v4),
            "--macro-evidence", str(macro),
            "--v2-result", str(v2_result),
            "--extended-history", str(extended_history),
            "--capture",
        ]
        proc = subprocess.run(command, cwd=repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        print(proc.stdout, end="")
        require(proc.returncode == 0, "Validated V2 capture engine failed in temporary ledger")

        temp_record_files = sorted(temp_records.glob("*.json"))
        require(len(temp_record_files) == 1, "Temporary capture did not produce exactly one record")
        record = json.loads(temp_record_files[0].read_text(encoding="utf-8"))

        source = record.get("source_authorities", {})
        source["capture_authorization"]["path"] = relative(repo_root, authorization)
        source["v4_operationalization"]["path"] = relative(repo_root, v4)
        source["fred_macro_refresh"]["path"] = relative(repo_root, macro)

        record_bytes = canonical_bytes(record)
        record_hash = hashlib.sha256(record_bytes).hexdigest()
        filename = temp_record_files[0].name
        final_record = records_dir / filename
        require(not final_record.exists(), "Final observation record already exists")

        if not args.capture:
            print("FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_CAPTURE_V3_PREFLIGHT=PASS")
            print(f"PROPOSED_OBSERVATION_ID={record['observation_id']}")
            print(f"PROPOSED_RECORD_SHA256={record_hash}")
            print("PORTABLE_REPOSITORY_RELATIVE_PATHS=TRUE")
            print("FIRST_PROSPECTIVE_OBSERVATION_CAPTURED=FALSE")
            print("NEXT_GATE=EXECUTE_AUTHORIZED_FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_CAPTURE_V3")
            return 0

        records_dir.mkdir(parents=True, exist_ok=True)
        temp_record = final_record.with_suffix(final_record.suffix + ".tmp")
        temp_manifest_out = manifest.with_suffix(manifest.suffix + ".tmp")
        require(not temp_record.exists(), "Temporary final record path already exists")
        require(not temp_manifest_out.exists(), "Temporary manifest path already exists")

        temp_record.write_bytes(record_bytes)
        require(sha256(temp_record) == record_hash, "Sanitized temporary record hash mismatch")

        updated_manifest = dict(manifest_obj)
        updated_manifest["record_count"] = 1
        updated_manifest["first_observation_id"] = record["observation_id"]
        updated_manifest["first_observation_file"] = relative(repo_root, final_record)
        updated_manifest["first_observation_sha256"] = record_hash
        updated_manifest["last_observation_id"] = record["observation_id"]
        updated_manifest["last_observation_sha256"] = record_hash
        updated_manifest["next_gate"] = "PRESERVE_AND_REVIEW_FIRST_PROSPECTIVE_BITCOIN_OBSERVATION"
        temp_manifest_out.write_bytes(canonical_bytes(updated_manifest))

        os.replace(temp_record, final_record)
        os.replace(temp_manifest_out, manifest)

    require(sha256(final_record) == record_hash, "Final observation record hash mismatch")
    final_manifest = json.loads(manifest.read_text(encoding="utf-8"))
    require(int(final_manifest.get("record_count", -1)) == 1, "Manifest record count was not updated to one")
    require(final_manifest.get("first_observation_id") == record["observation_id"], "Manifest first observation id mismatch")
    require(final_manifest.get("first_observation_file") == relative(repo_root, final_record), "Manifest observation path is not repository-relative")
    require(final_manifest.get("first_observation_sha256") == record_hash, "Manifest first observation hash mismatch")
    require(sha256(database) == database_hash_before, "Canonical database changed during capture")
    require(sha256(manifest) != manifest_hash_before, "Manifest did not change during capture")

    all_paths = json.dumps(record.get("source_authorities", {}), sort_keys=True)
    require(str(repo_root) not in all_paths, "Machine-specific repository path leaked into observation record")

    print("FIRST_PROSPECTIVE_BITCOIN_OBSERVATION_CAPTURE_V3=PASS")
    print(f"OBSERVATION_ID={record['observation_id']}")
    print(f"OBSERVATION_FILE={relative(repo_root, final_record)}")
    print(f"OBSERVATION_SHA256={record_hash}")
    print("PORTABLE_REPOSITORY_RELATIVE_PATHS=TRUE")
    print("STRATEGIC_STATE=INSUFFICIENT_EVIDENCE")
    print("TACTICAL_NEW_CAPITAL_STATE=INSUFFICIENT_EVIDENCE")
    print("EXISTING_POSITION_STATE=INSUFFICIENT_EVIDENCE")
    print("LEDGER_RECORD_COUNT=1")
    print("CANONICAL_DATABASE_MODIFIED=FALSE")
    print("PRODUCTION_POLICY_CHANGED=FALSE")
    print("AUTONOMOUS_EXECUTION_AUTHORIZED=FALSE")
    print("NEXT_GATE=PRESERVE_AND_REVIEW_FIRST_PROSPECTIVE_BITCOIN_OBSERVATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
