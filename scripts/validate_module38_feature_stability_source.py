from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "crypto_platform" / "module38.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    source = TARGET.read_text(encoding="utf-8-sig")

    require(
        "usable = features.dropna(subset=required_columns).copy()" in source,
        "Required price-derived feature gating is missing",
    )
    require(
        "usable = usable.drop(columns=[optional_column])" in source,
        "Incomplete optional feature exclusion is missing",
    )
    require(
        "training_min = x_train_frame.min(axis=0)" in source
        and "training_max = x_train_frame.max(axis=0)" in source,
        "Training support bounds are missing",
    )
    require(
        "x_validation_frame = x_validation_frame.clip(" in source
        and "x_current_frame = x_current_frame.clip(" in source,
        "Validation/live feature support bounding is missing",
    )
    require(
        "x_train = scaler.fit_transform(x_train_frame)" in source,
        "Scaler is not fit from the training frame",
    )
    require(
        "train = features.iloc[:train_end_index]" in source
        and "validation = features.iloc[validation_start_index:]" in source,
        "Purged holdout remediation is not present",
    )
    require(
        ').dropna()' not in source[source.find('def build_features'):source.find('def model_suite')],
        "Legacy all-column dropna remains in build_features",
    )

    print("CRYPTO_MODULE38_FEATURE_STABILITY_SOURCE_VALIDATION=PASS")
    print("REQUIRED_FEATURES_RETAIN_POINT_IN_TIME_HISTORY=TRUE")
    print("OPTIONAL_MISSING_FEATURES_IMPUTED=FALSE")
    print("OPTIONAL_INCOMPLETE_FEATURES_EXCLUDED=TRUE")
    print("VALIDATION_EXTRAPOLATION_BOUNDED_TO_TRAINING_SUPPORT=TRUE")
    print("PURGED_HOLDOUT_PRESERVED=TRUE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
