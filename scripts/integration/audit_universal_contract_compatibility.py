from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


CRYPTO_ROOT = Path(
    r"C:\Users\DevonLockard\crypto"
)

PLATFORM_ROOT = Path(
    r"C:\Users\DevonLockard\InvestmentPlatform"
)

OUTPUT_PATH = (
    CRYPTO_ROOT
    / "docs"
    / "integration"
    / "universal"
    / "universal_contract_compatibility_audit.json"
)

SEARCH_ROOTS = [
    PLATFORM_ROOT / "schemas",
    PLATFORM_ROOT / "data" / "reference",
    PLATFORM_ROOT / "foundation",
    PLATFORM_ROOT / "docs",
]

TARGET_TERMS = [
    "asset_master",
    "market_price",
    "market_prices",
    "portfolio_position",
    "portfolio_positions",
    "forecast",
    "recommendation",
    "risk_metric",
    "risk_metrics",
    "allocation_target",
    "allocation_targets",
    "platform_status",
    "price_projection",
    "price_projections",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def read_csv_header(
    path: Path,
) -> list[str] | None:
    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            reader = csv.reader(handle)
            return next(reader, [])

    except Exception:
        return None


def read_json_shape(
    path: Path,
) -> dict[str, Any] | None:
    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8-sig"
            )
        )

    except Exception:
        return None

    result: dict[str, Any] = {
        "top_level_type": type(payload).__name__,
    }

    if isinstance(payload, dict):
        result["top_level_keys"] = sorted(
            str(key)
            for key in payload
        )

        properties = payload.get("properties")

        if isinstance(properties, dict):
            result["properties"] = sorted(
                str(key)
                for key in properties
            )

        required = payload.get("required")

        if isinstance(required, list):
            result["required"] = [
                str(value)
                for value in required
            ]

    return result


def relevant_file(path: Path) -> bool:
    text = str(path.relative_to(
        PLATFORM_ROOT
    )).lower()

    return any(
        term in text
        for term in TARGET_TERMS
    )


def inspect_file(
    path: Path,
) -> dict[str, Any]:
    relative_path = str(
        path.relative_to(PLATFORM_ROOT)
    ).replace("\\", "/")

    record: dict[str, Any] = {
        "relative_path": relative_path,
        "suffix": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }

    if path.suffix.lower() == ".csv":
        record["csv_header"] = (
            read_csv_header(path)
        )

    elif path.suffix.lower() == ".json":
        record["json_shape"] = (
            read_json_shape(path)
        )

    return record


def main() -> None:
    if not PLATFORM_ROOT.exists():
        raise FileNotFoundError(
            f"Universal platform repository "
            f"not found: {PLATFORM_ROOT}"
        )

    files: list[Path] = []

    for search_root in SEARCH_ROOTS:
        if not search_root.exists():
            continue

        for path in search_root.rglob("*"):
            if (
                path.is_file()
                and path.suffix.lower()
                in {
                    ".csv",
                    ".json",
                    ".yaml",
                    ".yml",
                    ".sql",
                    ".md",
                    ".py",
                }
                and relevant_file(path)
            ):
                files.append(path)

    files = sorted(
        set(files),
        key=lambda item: str(item).lower(),
    )

    output = {
        "platform_root": str(
            PLATFORM_ROOT.resolve()
        ),
        "target_terms": TARGET_TERMS,
        "matching_file_count": len(files),
        "files": [
            inspect_file(path)
            for path in files
        ],
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(
        "PASS: Universal contract "
        "compatibility inventory created."
    )
    print(
        f"Matching files: {len(files)}"
    )
    print(
        f"Output: {OUTPUT_PATH}"
    )
    print()

    for record in output["files"]:
        print(
            f"- {record['relative_path']}"
        )

        if record.get("csv_header"):
            print(
                "  CSV columns: "
                + ", ".join(
                    record["csv_header"]
                )
            )

        shape = record.get("json_shape")

        if shape:
            properties = shape.get(
                "properties",
                []
            )

            required = shape.get(
                "required",
                []
            )

            if properties:
                print(
                    "  JSON properties: "
                    + ", ".join(properties)
                )

            if required:
                print(
                    "  Required: "
                    + ", ".join(required)
                )


if __name__ == "__main__":
    main()