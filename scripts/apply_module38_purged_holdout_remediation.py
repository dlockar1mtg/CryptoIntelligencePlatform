from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "crypto_platform" / "module38.py"

OLD = '''        train = features.iloc[\n            :usable_rows - validation_rows\n        ]\n        validation = features.iloc[\n            usable_rows - validation_rows:\n        ]\n        scaler = StandardScaler()\n'''

NEW = '''        # Purge forward-label overlap at the train/validation boundary.\n        # build_features() defines target_return with price.shift(-horizon),\n        # so the final `horizon` training origins would otherwise use labels\n        # whose target prices fall inside the validation origin window.\n        validation_start_index = usable_rows - validation_rows\n        purge_rows = int(horizon)\n        train_end_index = validation_start_index - purge_rows\n\n        if train_end_index < absolute_minimum:\n            raise InsufficientForecastHistory(\n                asset_id=asset_id,\n                horizon_days=horizon,\n                usable_rows=usable_rows,\n                required_rows=(\n                    absolute_minimum\n                    + validation_rows\n                    + purge_rows\n                ),\n            )\n\n        train = features.iloc[:train_end_index]\n        validation = features.iloc[validation_start_index:]\n\n        if train.empty or validation.empty:\n            raise RuntimeError(\n                f"Purged holdout produced an empty split for "\n                f"{asset_id} horizon {horizon}."\n            )\n\n        last_train_origin = pd.Timestamp(\n            train["observation_date"].iloc[-1]\n        )\n        first_validation_origin = pd.Timestamp(\n            validation["observation_date"].iloc[0]\n        )\n        if not last_train_origin < first_validation_origin:\n            raise RuntimeError(\n                f"Purged holdout origin ordering failed for "\n                f"{asset_id} horizon {horizon}."\n            )\n\n        scaler = StandardScaler()\n'''


def main() -> int:
    source = TARGET.read_text(encoding="utf-8-sig")

    if NEW in source:
        print("CRYPTO_MODULE38_PURGED_HOLDOUT_REMEDIATION=ALREADY_APPLIED")
        print(f"UPDATED_FILE={TARGET}")
        return 0

    count = source.count(OLD)
    if count != 1:
        raise RuntimeError(
            "Expected exactly one Module 38 contiguous split block; "
            f"found {count}. Refusing non-deterministic edit."
        )

    source = source.replace(OLD, NEW, 1)
    TARGET.write_text(source, encoding="utf-8", newline="")

    updated = TARGET.read_text(encoding="utf-8")
    required = (
        "validation_start_index = usable_rows - validation_rows",
        "purge_rows = int(horizon)",
        "train_end_index = validation_start_index - purge_rows",
        "train = features.iloc[:train_end_index]",
        "validation = features.iloc[validation_start_index:]",
    )
    missing = [token for token in required if token not in updated]
    if missing:
        raise RuntimeError(
            "Module 38 purged holdout edit did not persist required tokens: "
            + ", ".join(missing)
        )

    if OLD in updated:
        raise RuntimeError("Legacy contiguous Module 38 split remains after edit")

    print("CRYPTO_MODULE38_PURGED_HOLDOUT_REMEDIATION=PASS")
    print("PURGE_UNIT=FORWARD_TARGET_ROWS")
    print("PURGE_ROWS=HORIZON_DAYS_VALUE")
    print("VALIDATION_ORIGINS_UNCHANGED=TRUE")
    print("MODEL_OUTPUT_SEMANTICS_CHANGED=FALSE")
    print(f"UPDATED_FILE={TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
