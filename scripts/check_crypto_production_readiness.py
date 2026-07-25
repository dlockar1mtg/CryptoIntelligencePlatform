"""Static and package-level production readiness checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto_platform.production.registry import MODULE_REGISTRY, validate_registry


REQUIRED_PACKAGE_FILES = {
    "asset_master.csv",
    "forecasts.csv",
    "platform_status.csv",
    "portfolio_positions.csv",
    "recommendations.csv",
    "risk_metrics.csv",
    "export_manifest.csv",
    "package_summary.json",
    "validation_report.json",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    checks: list[dict] = []

    registry_errors = validate_registry(ROOT)
    checks.append({
        "name": "module_registry",
        "status": "PASS" if not registry_errors else "FAIL",
        "details": registry_errors,
    })

    module4 = next(spec for spec in MODULE_REGISTRY if spec.number == 4)
    checks.append({
        "name": "module_4_governance",
        "status": "PASS" if module4.status == "retired" and not module4.runner else "FAIL",
        "details": [module4.reason],
    })

    workflow = ROOT / ".github" / "workflows" / "crypto-production-cycle.yml"
    checks.append({
        "name": "github_workflow",
        "status": "PASS" if workflow.is_file() else "FAIL",
        "details": [str(workflow)],
    })

    if args.package_root:
        package = args.package_root.resolve()
        existing = {path.name for path in package.iterdir() if path.is_file()} if package.is_dir() else set()
        missing = sorted(REQUIRED_PACKAGE_FILES - existing)
        package_status = "PASS" if not missing else "FAIL"
        if package_status == "PASS":
            validation = json.loads((package / "validation_report.json").read_text(encoding="utf-8"))
            summary = json.loads((package / "package_summary.json").read_text(encoding="utf-8"))
            if validation.get("status") != "PASS" or summary.get("status") != "PASS":
                package_status = "FAIL"
                missing.append("package status is not PASS")
        checks.append({
            "name": "universal_package",
            "status": package_status,
            "details": missing or [str(package)],
        })

    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    report = {"status": status, "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if status == "PASS" or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
