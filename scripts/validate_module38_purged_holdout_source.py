from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "crypto_platform" / "module38.py"

REQUIRED = (
    'features["target_return"] = (',
    'price.shift(-horizon) / price - 1',
    'validation_start_index = usable_rows - validation_rows',
    'purge_rows = int(horizon)',
    'train_end_index = validation_start_index - purge_rows',
    'train = features.iloc[:train_end_index]',
    'validation = features.iloc[validation_start_index:]',
    'scaler.fit_transform(',
    'train[columns]',
    'scaler.transform(',
    'validation[columns]',
)

FORBIDDEN = (
    'train = features.iloc[\n            :usable_rows - validation_rows\n        ]',
)


def main() -> int:
    source = TARGET.read_text(encoding="utf-8-sig")

    missing = [token for token in REQUIRED if token not in source]
    if missing:
        raise RuntimeError(
            "Module 38 purged holdout source validation failed; missing: "
            + ", ".join(missing)
        )

    present_forbidden = [token for token in FORBIDDEN if token in source]
    if present_forbidden:
        raise RuntimeError(
            "Legacy unpurged Module 38 split remains in source"
        )

    train_end = source.index('train_end_index = validation_start_index - purge_rows')
    train_slice = source.index('train = features.iloc[:train_end_index]')
    validation_slice = source.index('validation = features.iloc[validation_start_index:]')
    scaler_fit = source.index('x_train = scaler.fit_transform(')

    if not (train_end < train_slice < validation_slice < scaler_fit):
        raise RuntimeError("Module 38 purged holdout statements are out of expected order")

    print("CRYPTO_MODULE38_PURGED_HOLDOUT_SOURCE_VALIDATION=PASS")
    print("FORWARD_TARGET_PRESENT=TRUE")
    print("EXPLICIT_PURGE_PRESENT=TRUE")
    print("LEGACY_CONTIGUOUS_SPLIT_PRESENT=FALSE")
    print("SCALER_FIT_ON_PURGED_TRAIN_ONLY=TRUE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
